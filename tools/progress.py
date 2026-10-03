#!/usr/bin/env python3
"""Прогресс по метрикам журнала ансамбля - для продюсера.

Запуск: python tools/progress.py <journal.md> [--stats stats.md] [--budget-usd X] [--target 0]
Разбирает строки:
  метрика: имя=число [источник: ...]
  отрезок N: [метрика] имя=число (было число) [источник], токены за отрезок=число, всего=число
Метрика должна уменьшаться до цели (по умолчанию 0). Только стандартная библиотека.
"""
from __future__ import annotations

import argparse
import math
import re
import statistics
import sys
from pathlib import Path

NUM = r"-?\d+(?:[.,]\d+)?"
SEG_RE = re.compile(r"^отрезок\s+(\d+)\s*:\s*(.*)$", re.I)
MET_RE = re.compile(r"^метрика\s*:\s*(.*)$", re.I)
KV_RE = re.compile(rf"([^\s=,:()\[\]]+)\s*=\s*({NUM})(?![\w.,])")
WAS_RE = re.compile(rf"\(\s*было\s*:?\s*({NUM})\s*\)", re.I)
SRC_RE = re.compile(r"\[[^\]]*источник[^\]]*\]", re.I)
TOK_RE = re.compile(r"токены\s+за\s+отрезок\s*=\s*(\d+)", re.I)
TARGET_RE = re.compile(rf"(?:цель|целев[а-яё]*|target)\s*(?:метрик[а-яё]*|значени[а-яё]*|диапазон)?\s*"
                       rf"(?:[:=]\s*)?(?:[^\s\d≤<=:]+\s*)?(?:≤|<=|=|<)?\s*({NUM})", re.I)
MIN_STEP = 0.035      # доля уменьшения, ниже которой шаг медленный
MIN_TOKENS = 50000    # плато только если на два последних шага ушло больше токенов
WALL_FACTOR = 3.0     # стена: потрачено >= factor x медиана токенов отрезка с прогрессом
WALL_TOKENS = 300000  # стена без истории прогресса: потрачено >= столько без заметного уменьшения
JUMP = 0.40           # скачок значения - информационный флаг
SKIP_NAMES = {"всего", "отрезок", "токены"}
# Haiku 4.5, USD за токен
P_IN, P_OUT, P_CR, P_CW = 1e-6, 5e-6, 0.10e-6, 1.25e-6


def num(s):
    return float(s.replace(",", "."))


def fmt(v):
    return str(int(v)) if float(v).is_integer() else f"{v:.2f}".rstrip("0").rstrip(".")


def parse_journal(text: str):
    """-> (точки, номера строк без источника). Точка: dict(name, value, was, src, seg, tokens, kind, line)."""
    pts, nosrc = [], []
    for ln, raw in enumerate(text.splitlines(), 1):
        line = raw.replace("*", "").strip().lstrip("-> \t").strip()
        seg = SEG_RE.match(line)
        met = MET_RE.match(line)
        if not (seg or met):
            continue
        body = (seg or met).group(2 if seg else 1)
        kv = next((m for m in KV_RE.finditer(body) if m.group(1).lower() not in SKIP_NAMES), None)
        if not kv:
            continue
        src = SRC_RE.search(body)
        was = WAS_RE.search(body)
        tok = TOK_RE.search(body)
        pts.append({"name": kv.group(1), "value": num(kv.group(2)),
                    "was": num(was.group(1)) if was else None,
                    "src": src.group(0).strip("[]") if src else None,
                    "seg": int(seg.group(1)) if seg else None,
                    "tokens": int(tok.group(1)) if tok else None,
                    "kind": "seg" if seg else "met", "line": ln})
        if not src:
            nosrc.append(ln)
    return pts, nosrc


def series(points):
    """Ряд метрики: строки «отрезок» главнее; без них - строки «метрика:».
    -> (точки ряда, шаги [(начало, конец)])."""
    segs = [p for p in points if p["kind"] == "seg"]
    use = segs or points
    # повтор того же значения с тем же источником - одна и та же проверка, не новая точка
    dedup = []
    for p in use:
        if dedup and p["src"] is not None and (p["value"], p["src"]) == (dedup[-1]["value"], dedup[-1]["src"]):
            continue
        dedup.append(p)
    use = dedup
    steps, step_tok, prev = [], [], None
    for p in use:
        # «(было X)» у первой точки создаёт шаг, только если X - число > 0 (пересчёт прошлой точки
        # в новом учёте); «(было 0)» и прочее шага не создаёт
        was_ok = p["was"] is not None and (prev is not None or p["was"] > 0)
        start = p["was"] if was_ok else prev
        if start is not None:
            steps.append((start, p["value"]))
            step_tok.append(p["tokens"])
        prev = p["value"]
    return use, steps, step_tok


def find_targets(text: str, target):
    """Целевые значения в журнале, отличные от --target."""
    found = []
    for line in text.splitlines():
        for m in TARGET_RE.finditer(line.replace("*", "")):
            if not re.search(r"[:=≤<]", m.group(0)):
                continue
            v = num(m.group(1))
            if v != target and v not in found:
                found.append(v)
    return found


def is_flat(start, end, min_step=MIN_STEP):
    dec = start - end
    if start < 20:
        return dec <= 0
    return dec < min_step * start


def is_jump(start, end):
    """Значение сменилось больше чем на 40 % (вверх или вниз)."""
    if start == 0:
        return end != 0
    return abs(end - start) / abs(start) > JUMP


def find_wall(steps, step_tok, min_step=MIN_STEP, wall_factor=WALL_FACTOR, wall_tokens=WALL_TOKENS):
    """Стена: много токенов потрачено с последнего заметного уменьшения, а метрика не сдвинулась.
    -> None или dict(spent, median, k). median/k = None, если истории с прогрессом нет."""
    last_good = max((i for i, (a, b) in enumerate(steps) if not is_flat(a, b, min_step)), default=-1)
    tail = step_tok[last_good + 1:]
    if len(tail) < 2:     # один дорогой шаг - ещё не стена
        return None
    spent = sum(t or 0 for t in tail)
    hist = [t for (a, b), t in zip(steps[:last_good + 1], step_tok[:last_good + 1])
            if a - b > 0 and t is not None]
    if hist:
        med = statistics.median(hist)
        if med > 0 and spent >= wall_factor * med:
            return {"spent": spent, "median": med, "k": spent / med}
        return None
    if spent >= wall_tokens:
        return {"spent": spent, "median": None, "k": None}
    return None


def analyze_metric(points, target, min_step=MIN_STEP, min_tokens=MIN_TOKENS,
                   wall_factor=WALL_FACTOR, wall_tokens=WALL_TOKENS):
    vals, steps, step_tok = series(points)
    last = vals[-1]["value"]
    flags = []
    if last <= target:
        flags.append("ЦЕЛЬ")
    else:
        if steps and steps[-1][1] > steps[-1][0]:
            flags.append("РОСТ")
        if len(steps) >= 2 and all(is_flat(a, b, min_step) for a, b in steps[-2:]):
            tk = step_tok[-2:]
            # токены неизвестны - порог считается выполненным
            if any(t is None for t in tk) or sum(tk) > min_tokens:
                flags.append("ПЛАТО")
    wall = None
    if last > target:
        wall = find_wall(steps, step_tok, min_step, wall_factor, wall_tokens)
        if wall:
            flags.append("СТЕНА")
    if any(is_jump(a, b) for a, b in steps):
        flags.append("СКАЧОК")
    if len(steps) <= 1 and last <= target and vals and (len(vals) <= 2):
        flags.append("НОЛЬ С ПЕРВОЙ")
    if any(p["src"] is None for p in points):
        flags.append("БЕЗ ИСТОЧНИКА")
    rate = None
    if steps:
        last2 = steps[-2:]
        rate = sum(a - b for a, b in last2) / len(last2)
    left = None
    if last > target and rate and rate > 0:
        left = math.ceil((last - target) / rate)
    return {"vals": vals, "steps": steps, "min_step": min_step, "wall": wall, "flags": flags, "last": last, "rate": rate, "left": left}


def parse_stats(text: str):
    """Из stats.md: токены (вывод, вход, кэш чтение/запись) и стоимость $ (если есть строка итога)."""
    t = {"out": 0, "in": 0, "cr": 0, "cw": 0}
    cost, found = 0.0, False
    for line in text.splitlines():
        m = re.match(r"\s*токены:\s*вывод\s+(\d+);\s*вход без кэша\s+(\d+);\s*вход через кэш:\s*"
                     r"чтение\s+(\d+),\s*запись\s+(\d+)", line)
        if m:
            found = True
            t["out"] += int(m.group(1))
            t["in"] += int(m.group(2))
            t["cr"] += int(m.group(3))
            t["cw"] += int(m.group(4))
        c = re.search(r"итог сессии.*стоимость\s*\$\s*(\d+(?:\.\d+)?)", line)
        if c:
            cost += float(c.group(1))
    return (t if found else None), (cost if cost > 0 else None)


def verdict(results, changed=None, target=0.0, min_step=MIN_STEP):
    # вывод - по текущей метрике; закрытые (переопределённые) в него не входят
    results = {n: r for n, r in results.items() if not r.get("closed")}
    if changed:
        return (f"цель метрики изменена в журнале (было {fmt(target)}, стало {', '.join(fmt(x) for x in changed)}) - "
                "менять цель может только принимающий по заданию; проверь, есть ли его решение.")
    if not results:
        return "метрики нет - команда идёт вслепую. Заведи строку «метрика: имя=число [источник: ...]»."
    if all("ЦЕЛЬ" in r["flags"] for r in results.values()):
        if any("НОЛЬ С ПЕРВОЙ" in r["flags"] for r in results.values()):
            return ("цель с первой проверки - подозрительно: попроси считающего показать список проверок "
                    "и проверить крайние случаи и каждый пример из задания/спецификации отдельной проверкой.")
        return "цель достигнута - проверь приёмку."
    act = [r for r in results.values() if "ЦЕЛЬ" not in r["flags"]]
    for r in act:
        w = r.get("wall")
        if w:
            how = (f"в {w['k']:.1f} раза больше обычного отрезка с прогрессом" if w["k"] is not None
                   else "истории прогресса нет")
            return (f"стена: потрачено {w['spent']} токенов с последнего прогресса ({how}), результата нет - "
                    "путь исчерпан; спроси владельца, можно ли иначе (другой инструмент, источник, доступ).")
    for r in act:
        if len(r["steps"]) == 1 and is_jump(*r["steps"][0]):
            return "скачок - проверь учёт, прежде чем считать прогрессом."
    if any("РОСТ" in r["flags"] for r in act):
        return "рост - выясни причину."
    if any("ПЛАТО" in r["flags"] for r in act):
        return "плато - требуй смены способа."
    def stalled(r):
        st = r["steps"]
        if not st:
            return False
        s, e = st[-1]
        small = s < 20
        return (e >= s) if small else (s - e) < min_step * s
    if any(stalled(r) for r in act):
        return "последний отрезок без заметного движения - ещё один такой отрезок будет плато; спроси команду, что мешает."
    if any("БЕЗ ИСТОЧНИКА" in r["flags"] for r in act):
        return "идёт, но у чисел нет источника - попроси считающего указывать, что проверял."
    return "идёт - продолжай."


def main(argv=None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description="Прогресс по метрикам журнала")
    ap.add_argument("journal")
    ap.add_argument("--stats", help="stats.md от session_stats.py")
    ap.add_argument("--budget-usd", type=float)
    ap.add_argument("--target", type=float, default=0.0)
    ap.add_argument("--min-step", type=float, default=MIN_STEP,
                    help="порог медленного шага: доля уменьшения (по умолчанию 0.035)")
    ap.add_argument("--min-tokens", type=int, default=MIN_TOKENS,
                    help="плато только если токенов за два последних шага больше (по умолчанию 50000)")
    ap.add_argument("--wall-factor", type=float, default=WALL_FACTOR,
                    help="стена: потрачено >= factor x медианы токенов отрезка с прогрессом (по умолчанию 3)")
    ap.add_argument("--wall-tokens", type=int, default=WALL_TOKENS,
                    help="стена без истории прогресса: потрачено токенов без уменьшения (по умолчанию 300000)")
    a = ap.parse_args(argv)
    try:
        text = Path(a.journal).read_text(encoding="utf-8", errors="replace")
    except OSError as e:
        print(f"Не могу прочитать журнал: {e}")
        return 1
    pts, nosrc = parse_journal(text)
    by = {}
    for p in pts:
        by.setdefault(p["name"], []).append(p)
    results = {n: analyze_metric(ps, a.target, a.min_step, a.min_tokens, a.wall_factor, a.wall_tokens) for n, ps in by.items()}
    # текущая метрика - с самой поздней строкой в журнале; остальные закрыты (переопределены)
    cur = max(results, key=lambda n: by[n][-1]["line"]) if results else None
    for n, r in results.items():
        if n != cur:
            r["closed"] = True
            r["flags"] = ["закрыта (переопределена)"] + (["СТЕНА"] if r.get("wall") else [])
    changed = find_targets(text, a.target)
    if changed:
        for r in results.values():
            if not r.get("closed"):
                r["flags"].append("ЦЕЛЬ ИЗМЕНЕНА")
    L = []
    if not results:
        L += ["!" * 60, "МЕТРИКИ НЕТ - КОМАНДА ИДЁТ ВСЛЕПУЮ", "!" * 60]
    for n, r in results.items():
        L.append(f"Метрика {n} (цель {fmt(a.target)}):")
        for p in r["vals"]:
            tag = f"отрезок {p['seg']}" if p["seg"] is not None else f"строка {p['line']}"
            L.append(f"  {tag}: {fmt(p['value'])}  [{p['src'] or 'нет источника'}]")
        for i, (s, e) in enumerate(r["steps"], 1):
            d = s - e
            pct = f"{d / s * 100:+.0f}%" if s else "н/д"
            note = "  [скачок - проверь, не сменился ли учёт]" if is_jump(s, e) else ""
            L.append(f"  шаг {i}: {fmt(s)} -> {fmt(e)}, уменьшение {fmt(d)} ({pct}){note}")
        L.append("  флаги: " + (", ".join(r["flags"]) or "нет"))
        if r.get("closed"):
            L.append("")
            continue
        if r["left"] is not None:
            L.append(f"  прогноз: при темпе {fmt(r['rate'])} за отрезок до цели ещё {r['left']} отрезк.")
        elif "ЦЕЛЬ" not in r["flags"]:
            L.append("  прогноз: цель не приближается (темп не больше нуля)")
        L.append("")
    walls = [n for n, r in results.items() if r.get("wall")]
    if walls:
        L.append("СТЕНА по метрикам: " + ", ".join(
            f"{n} ({results[n]['wall']['spent']} ток.)" + (" [закрыта]" if results[n].get("closed") else "")
            for n in walls))
    if nosrc:
        L.append("БЕЗ ИСТОЧНИКА: строки журнала " + ", ".join(map(str, nosrc[:10])))
    seg_tokens = sum(p["tokens"] or 0 for p in pts if p["kind"] == "seg")
    t, cost = None, None
    if a.stats:
        try:
            t, cost = parse_stats(Path(a.stats).read_text(encoding="utf-8", errors="replace"))
        except OSError:
            L.append(f"stats не прочитан: {a.stats}")
    est = False
    if cost is None and t:
        cost = t["out"] * P_OUT + t["in"] * P_IN + t["cr"] * P_CR + t["cw"] * P_CW
        est = True
    if t:
        L.append(f"Токены (числа из stats.md): вывод {t['out']}, вход {t['in']}, кэш чтение {t['cr']}, запись {t['cw']}")
        L.append("  подсказка: в строку отрезка бери токены и стоимость отсюда.")
    if seg_tokens:
        L.append(f"Токены по строкам отрезков: {seg_tokens}")
    if cost is not None:
        L.append(f"Стоимость: ${cost:.2f}" + (" (оценка по ценам Haiku 4.5)" if est else ""))
    if a.budget_usd is not None:
        main_r = results.get(cur) if cur and "ЦЕЛЬ" not in results[cur]["flags"] else None
        nseg = max([p["seg"] for p in pts if p["seg"]] + [len(r["vals"]) for r in results.values()] + [0])
        if cost is None:
            L.append("Бюджет: стоимость неизвестна - дай --stats.")
        elif main_r is None:
            L.append(f"Бюджет ${a.budget_usd:.2f}: цель достигнута, потрачено ${cost:.2f}.")
        elif main_r["left"] is None or not nseg:
            L.append(f"Бюджет ${a.budget_usd:.2f}: потрачено ${cost:.2f}; прогноза нет, цель не приближается.")
        else:
            per = cost / nseg
            need = per * main_r["left"]
            ok = cost + need <= a.budget_usd
            L.append(f"Бюджет ${a.budget_usd:.2f}: потрачено ${cost:.2f}, до цели ещё ~${need:.2f} "
                     f"({main_r['left']} отрезк. по ${per:.2f}) - " + ("хватит." if ok else "НЕ хватит."))
    L.append("вывод: " + verdict(results, changed, a.target, a.min_step))
    print("\n".join(L))
    return 0


if __name__ == "__main__":
    sys.exit(main())
