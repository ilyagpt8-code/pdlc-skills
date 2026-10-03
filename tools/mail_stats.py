#!/usr/bin/env python3
"""Сводка по почте ансамбля - для хореографа.

Запуск: python tools/mail_stats.py <папка ансамбля> [--last K] [--roles a,b,c] [--window-hours 2]
         [--max-age-hours 12] [--top 15]
Читает <папка>/mail/NNN-<от>-to-<кому>.md (кому = роль или all).
Только стандартная библиотека.
"""
from __future__ import annotations

import argparse
import re
import sys
from functools import lru_cache
from datetime import datetime, timezone
from pathlib import Path

NAME_RE = re.compile(r"^(\d+)-(.+?)-to-(.+)\.md$")
TS_RE = re.compile(r"^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d(?:\.\d+)?(?:Z|[+-]\d\d:?\d\d)?$")
# Признаки кандидата (только помечают, ничего не отбрасывают; судит хореограф).
# «ожидаем…», «не нужно» - не признаки.
SIGNALS = (
    ("вопрос", re.compile(r"\?(?=\s|$|[)»\"'])")),
    ("прошу", re.compile(r"\bпрош[уе]\w*|\bпросьб\w*|\bпросит\w*|\bпришл\w+|\bпопрос\w+|\bдайте\b|\bпредлага\w+", re.I)),
    # «жду оператора» - ждёт не адресата письма
    ("жду", re.compile(r"\bжд[уё]\b(?!\s+(?:(?:слова|ответа|решения|да)\s+)?(?:его\s+)?оператор)", re.I)),
    # влил/влит - уже сделано; ждёт ветка, готовая к слиянию
    ("на слияние", re.compile(r"на\s+слияни\w+|к\s+слияни\w+|(?:fast-?forward|ff)\s+возможен|на\s+merge", re.I)),
    ("BLOCKED", re.compile(r"\bBLOCKED\b|\bзаблокирован\w*", re.I)),
)
REPEAT_WORD = re.compile(r"\bповторя(?:ю|ем)\b|\bповторно\b|\bповторный\b", re.I)
REPORT_START = re.compile(r"^(?:готов\w*|принял\w*|принят\w*|принято|спасибо|благодар\w+|отч[её]т\w*)", re.I)
WINDOW_HOURS = 2.0  # решение владельца 2026-10-03: пропустить затор дороже, чем открыть лишние первые строки
TOP = 15
# письмо-подтверждение/ответ/закрытие: ответа не ждёт. Слова закрытия - в первых CONFIRM_HEAD знаках;
# слова «ответ…/подтверждаю/согласен» - только в самом начале (после обращения до 70 знаков).
CONFIRM_HEAD = 150
CONFIRM_ANY = re.compile(
    r"\b(?:принимаю|принял\w*|приняла|принят\w*|одобря\w+|влил\w*|влит\w*|спасибо|благодар\w+|"
    r"извин\w+|прости\w*|понял\w*)\b", re.I)
CONFIRM_START = re.compile(
    r"^[^.!?\n]{0,70}?\b(?:ответ(?!ь)\w*|отвеча\w+|подтвержда\w+|согласен|согласна|ок|окей|ясно)\b",
    re.I)
REPLY_WINDOW = 2 * 3600     # ответ, не названный явно, - первое письмо адресата в пределах 2 ч
REPEAT_MARKED_SIM = 0.4     # то же, если в письме есть «повторяю»
REPEAT_SIM = 0.75           # доля общих слов, с которой письмо считается повтором предыдущего
TOPIC_SIM = 0.05            # меньше - письма отправителя адресату по разным темам
ACK_RE = re.compile(r"\b(принял\w*|принято|спасибо|благодарю|работаю|в работе|ок|окей|ok|"
                    r"понял\w*|ясно|жду|готово|приступаю)\b", re.I)
SHORT = 200
WORD_RE = re.compile(r"\w{4,}")
SUB_RE = re.compile(r"_sub_[0-9a-zA-Z]+$")


def load(folder: Path):
    """Письма по порядку: dict(n, frm, to, name, text)."""
    mail = folder / "mail"
    if not mail.is_dir():
        mail = folder
    out = []
    for f in sorted(mail.glob("*.md")):
        m = NAME_RE.match(f.name)
        if not m:
            continue
        try:
            text = f.read_text(encoding="utf-8", errors="replace")
        except OSError:
            text = ""
        text = text.strip()
        first, _, rest = text.partition("\n")
        ts = None
        if TS_RE.match(first.strip()):          # первая строка письма - время (claude_mail)
            try:
                ts = datetime.fromisoformat(first.strip().replace("Z", "+00:00"))
                ts = ts if ts.tzinfo else ts.replace(tzinfo=timezone.utc)
                text = rest.strip()
            except ValueError:
                ts = None
        out.append({"n": int(m.group(1)), "frm": m.group(2), "to": m.group(3),
                    "name": f.name, "text": text, "ts": ts})
    out.sort(key=lambda x: (x["n"], x["name"]))
    return out


@lru_cache(maxsize=None)
def _has_letter_word(text):
    return "письм" in text.lower()


def _refers(text, m):
    """Ссылается ли text на письмо m: по имени файла или по явному «письмо NNN».
    Просто трёхзначное число ссылкой не считается."""
    stem = m["name"][:-3]
    if stem in text or m["name"] in text:
        return True
    if not _has_letter_word(text):
        return False
    return bool(re.search(rf"письм\w*\s*(?:№|N|#|no\.?)?\s*0*{m['n']}(?!\d)", text, re.I))


def _mentions_role(text, role):
    """Роль role названа в письме как просящая/ждущая («role просит/ждёт»)."""
    return bool(re.search(rf"\b{re.escape(role)}\w*\s+(?:\w+\s+)?(?:просит|ждёт|ждет|ждут|просят)", text, re.I))


def _words(text):
    return {w.lower() for w in WORD_RE.findall(text)}


def _similar(a, b):
    """Доля общих слов (по меньшему набору)."""
    wa, wb = _words(a), _words(b)
    if not wa or not wb:
        return 0.0
    return len(wa & wb) / min(len(wa), len(wb))


def _within(a, b, sec):
    """b не позже a + sec; если времени у писем нет, окно не применяется."""
    if a.get("ts") is None or b.get("ts") is None:
        return True
    return 0 <= (b["ts"] - a["ts"]).total_seconds() <= sec


def reply_index(msgs, i):
    """Индекс письма-ответа на msgs[i] или None.

    Ответ - письмо адресата ОТПРАВИТЕЛЮ (или всем), связанное с письмом: (а) оно ссылается на
    него по имени файла / «письмо NNN»; (б) это первое письмо адресата отправителю после письма
    в пределах REPLY_WINDOW (2 ч), если между ними отправитель не написал адресату письма по
    иной теме (письма по той же теме - повтор вопроса - ответ не отменяют); (в) письмо просило
    ответить третьему («Z просит»), и адресат написал Z (в тех же пределах)."""
    m = msgs[i]
    later = msgs[i + 1:]
    for j, x in enumerate(later, i + 1):
        if _refers(x["text"], m) and x["frm"] != m["frm"]:
            return j
    third = ({x["frm"] for x in msgs} | {x["to"] for x in msgs}) - {m["to"], "all", m["frm"]}
    pend = []
    for j, x in enumerate(later, i + 1):
        if m.get("ts") is not None and x.get("ts") is not None and not _within(m, x, REPLY_WINDOW):
            break
        if x["frm"] == m["frm"] and x["to"] == m["to"]:
            if _similar(m["text"], x["text"]) < TOPIC_SIM:
                pend.append(x)          # иная тема: ответ может идти на него, а не на m
            continue
        if x["frm"] == m["to"] and x["to"] in (m["frm"], "all"):
            # ответ достаётся письму, на которое он больше похож; m теряет его,
            # если ответ ближе к письму иной темы, написанному между ними
            if pend and max(_similar(x["text"], p["text"]) for p in pend) > _similar(x["text"], m["text"]):
                return None
            return j
    for z in third:                      # просьба «Z просит» -> адресат написал Z
        if _mentions_role(m["text"], z):
            for j, x in enumerate(later, i + 1):
                if x["frm"] == m["to"] and x["to"] == z and _within(m, x, REPLY_WINDOW):
                    return j
    return None


def answered(msgs, i):
    return reply_index(msgs, i) is not None


def signals_of(text):
    out = []
    for name, rx in SIGNALS:
        m = rx.search(text)
        if not m:
            continue
        if name == "готово" and not (m.start() < READY_HEAD or re.search(r"\bГОТОВО\b", text)):
            continue
        out.append(name)
    return out


def first_line(text, limit=100):
    """Первая содержательная строка письма (без разметки и одиночного обращения), до limit знаков."""
    for ln in text.splitlines():
        ln = re.sub(r"^[\s*_>#`\-—«\"'(]+", "", ln).strip()
        ln = re.sub(r"[*_`]+", "", ln)
        if len(ln) < 3 or re.fullmatch(r"[\w .\-]{1,25}[,:!]", ln):      # пусто или «tools,»
            continue
        return ln if len(ln) <= limit else ln[:limit - 1].rstrip() + "…"
    return ""


def is_report(text, sig):
    """Начинается с «готово/принял/спасибо/отчёт» и без вопроса: вероятно, отчёт, ответа не ждёт."""
    return "вопрос" not in sig and bool(REPORT_START.match(first_line(text, 60)))


def find_repeats(msgs):
    """Повтор: письмо m повторяет прежнее письмо p той же пары (в тексте «повторяю» и общих слов
    не меньше REPEAT_MARKED_SIM, либо почти тот же текст: REPEAT_SIM) в пределах 12 ч.
    replied - адресат между p и m отправителю писал (ответ был, но не сработал); если нет -
    «повтор без ответа». Возвращает [{frm, to, name, orig, gap, replied}]."""
    out = []
    for i, m in enumerate(msgs):
        if is_sub(m["frm"]) or is_sub(m["to"]):
            continue
        marked = bool(REPEAT_WORD.search(m["text"]))
        best, replied = None, False
        for k in range(i - 1, -1, -1):
            p = msgs[k]
            if m.get("ts") is not None and p.get("ts") is not None and (m["ts"] - p["ts"]).total_seconds() > 12 * 3600:
                break
            if p["frm"] == m["to"] and p["to"] == m["frm"] and best is None:
                replied = True              # адресат писал отправителю после ближайшего повтора
            if p["frm"] == m["frm"] and p["to"] == m["to"]:
                sim = _similar(p["text"], m["text"])
                if sim >= (REPEAT_MARKED_SIM if marked else REPEAT_SIM) and (best is None or sim > best[0]):
                    best = (sim, p, replied)
        if best:
            p = best[1]
            gap = (m["ts"] - p["ts"]).total_seconds() if m.get("ts") and p.get("ts") else None
            out.append({"frm": m["frm"], "to": m["to"], "name": m["name"], "orig": p["name"], "gap": gap,
                        "replied": best[2]})
    return out


def fold(r):
    """Субагенты одной роли (architect_sub_a1b2...) в статистике - одна строка architect_sub."""
    return SUB_RE.sub("_sub", r)


def is_sub(r):
    return bool(SUB_RE.search(r))


def analyze(msgs, roles_extra=(), last=5, window_h=WINDOW_HOURS):
    roles = sorted({fold(m["frm"]) for m in msgs} | {fold(m["to"]) for m in msgs if m["to"] != "all"}
                   | set(roles_extra))
    st = {r: {"sent": 0, "to_me": 0, "via_all": 0, "open": []} for r in roles}
    matrix = {}
    for i, m in enumerate(msgs):
        f, t = fold(m["frm"]), fold(m["to"])
        st[f]["sent"] += 1
        matrix[(f, t)] = matrix.get((f, t), 0) + 1
        if m["to"] == "all":
            for r in roles:
                if r != f:
                    st[r]["via_all"] += 1
        else:
            st[t]["to_me"] += 1
            if not answered(msgs, i):
                st[f]["open"].append(m)
    last_ts = max((m["ts"] for m in msgs if m.get("ts")), default=None)
    ens = set(roles_extra)          # явно названные роли; «other…» без этого - внешняя сессия
    cands = []
    for i, m in enumerate(msgs):
        y = m["to"]
        if is_sub(m["frm"]) or is_sub(y) or y == "all" or y == m["frm"]:
            continue                # субагенты отчитываются уведомлением и ответа не ждут
        if y.split("_")[0] == "other" and y not in ens:
            continue                # внешняя сессия - не роль ансамбля
        replied = False
        for x in msgs[i + 1:]:
            if x["frm"] == y and x["to"] == m["frm"]:
                if m.get("ts") is None or x.get("ts") is None or 0 <= (x["ts"] - m["ts"]).total_seconds() <= window_h * 3600:
                    replied = True
                    break
            if m.get("ts") is not None and x.get("ts") is not None and (x["ts"] - m["ts"]).total_seconds() > window_h * 3600:
                break
        if replied:
            continue
        sig = signals_of(m["text"])
        age = (last_ts - m["ts"]).total_seconds() if last_ts and m.get("ts") else None
        cands.append({"frm": m["frm"], "to": y, "name": m["name"], "age": age, "signals": sig,
                      "line": first_line(m["text"]), "report": is_report(m["text"], sig),
                      "fresh": age is not None and age < window_h * 3600})
    waits = {}
    for it in cands:
        if not it["report"]:
            waits.setdefault((it["frm"], it["to"]), []).append(it["name"])
    # с признаками выше, затем старые выше
    cands.sort(key=lambda x: (not x["signals"], -(x["age"] if x["age"] is not None else -1)))
    wait_items = cands
    repeats = find_repeats(msgs)
    never = [r for r in roles if st[r]["sent"] == 0]
    tail = {fold(m["frm"]) for m in msgs[-last:]}
    quiet = [r for r in roles if st[r]["sent"] > 0 and r not in tail]
    empty = [m["name"] for m in msgs if len(m["text"]) <= SHORT and ACK_RE.search(m["text"])]
    # круги: 3+ письма подряд между одной парой
    loops, i = [], 0
    while i < len(msgs):
        pair = frozenset((fold(msgs[i]["frm"]), fold(msgs[i]["to"])))
        j = i
        while j < len(msgs) and frozenset((fold(msgs[j]["frm"]), fold(msgs[j]["to"]))) == pair:
            j += 1
        if len(pair) == 2 and j - i >= 3:
            loops.append((sorted(pair), msgs[i]["name"], msgs[j - 1]["name"]))
        i = max(j, i + 1)
    return {"roles": roles, "st": st, "matrix": matrix, "waits": waits,
            "never": never, "quiet": quiet, "empty": empty, "loops": loops, "last": last,
            "wait_items": wait_items, "window_h": window_h, "repeats": repeats, "last_ts": last_ts}


def _age(sec):
    h, rem = divmod(int(sec), 3600)
    mi = rem // 60
    return f"{h // 24}д {h % 24}ч {mi:02d}м" if h >= 24 else (f"{h}ч {mi:02d}м" if h else f"{mi}м")


def render(a, total, max_age_h=None, top=TOP) -> str:
    roles, st = a["roles"], a["st"]
    L = [f"Писем всего: {total}. Роли: {', '.join(roles) or 'нет'}."]
    L.append("")
    L.append("По ролям:")
    for r in roles:
        s = st[r]
        line = (f"  {r}: отправлено {s['sent']}, получено {s['to_me'] + s['via_all']} "
                f"(адресно {s['to_me']}, через all {s['via_all']}), без ответа {len(s['open'])}")
        if s["open"]:
            line += f"; самое старое: {s['open'][0]['name']}"
        L.append(line)
    L.append("")
    items = a["wait_items"]
    win = a["window_h"]
    hidden = 0
    if max_age_h is not None:
        fresh = [it for it in items if it["age"] is None or it["age"] <= max_age_h * 3600]
        hidden, items = len(items) - len(fresh), fresh
    main_items = [it for it in items if not it["report"]]
    reports = [it for it in items if it["report"]]

    def line(it):
        age = f"возраст {_age(it['age'])}" if it["age"] is not None else "возраст ?"
        if it["fresh"]:
            age += f", окно {win:g} ч не истекло"
        sig = ", ".join(it["signals"]) or "нет"
        return f"  {it['frm']} -> {it['to']}: {it['name']} ({age}; признаки: {sig}) «{it['line']}»"

    if main_items:
        # Очередь у узла: к кому больше всего писем без ответа (живые ансамбли собираются вокруг одной роли).
        from collections import Counter
        q = Counter(it["to"] for it in main_items)
        top_role, n = q.most_common(1)[0]
        if n >= 2:
            oldest = max((it["age"] or 0) for it in main_items if it["to"] == top_role)
            L.append(f"Очередь у узла: {top_role} — {n} кандидатов, самый старый {_age(oldest)}.")
        L.append(f"Кандидаты на ожидание (письмо, на которое адресат не написал отправителю ни одного письма "
                 f"за {win:g} ч или окно ещё идёт; скрипт не решает, ждёт ли письмо ответа, — "
                 f"открой и реши сам; с признаками выше, затем старые; возраст - до последнего письма в почте):")
        L.extend(line(it) for it in main_items[:top])
        if len(main_items) > top:
            L.append(f"  (ещё {len(main_items) - top} кандидатов не показано)")
    else:
        L.append("Кандидаты на ожидание: нет.")
    if reports:
        L.append("Вероятно, отчёты (начинаются с «готово/принял/спасибо/отчёт», без вопроса; ответа, скорее всего, "
                 "не ждут, но проверь, не ждёт ли приёмки):")
        L.extend(line(it) for it in reports[:top])
        if len(reports) > top:
            L.append(f"  (ещё {len(reports) - top} не показано)")
    if hidden:
        L.append(f"  (ещё {hidden} кандидатов старше {max_age_h:g} ч скрыто — давние, вероятно, закрыты делом)")
    if a["repeats"]:
        L.append("Повтор вопроса (то же письмо отправлено снова; «без ответа» - адресат между ними не писал):")
        for x in a["repeats"]:
            gap = f", через {_age(x['gap'])}" if x["gap"] is not None else ""
            tag = "ответ между ними был" if x["replied"] else "повтор без ответа"
            L.append(f"  {x['frm']} -> {x['to']}: {x['name']} повторяет {x['orig']}{gap} ({tag})")
    L.append("Молчащие: " + (
        "не писали ни разу: " + ", ".join(a["never"]) if a["never"] else "все писали хотя бы раз")
        + (f"; нет писем в последних {a['last']}: " + ", ".join(a["quiet"]) if a["quiet"] else
           f"; в последних {a['last']} письмах писали все, кто писал"))
    L.append("Пустые (короткие подтверждения): " + (", ".join(a["empty"]) or "нет"))
    L.append("")
    cols = roles + (["all"] if any(k[1] == "all" for k in a["matrix"]) else [])
    w = max([len(c) for c in cols] + [6])
    L.append("Кто кому (строка пишет, столбец получает):")
    L.append("  " + "".join(["".ljust(w + 1)] + [c.ljust(w + 1) for c in cols]).rstrip())
    for r in roles:
        L.append("  " + r.ljust(w + 1) + "".join(
            (str(a["matrix"].get((r, c), 0)) if r != c else "-").ljust(w + 1) for c in cols).rstrip())
    L.append("")
    att = []
    if a["waits"]:
        pairs = "; ".join(f"{x} ждёт {y}" for (x, y) in sorted(a["waits"])[:3])
        att.append(f"кандидаты на ожидание: {pairs}. Открой письма и реши, ждут ли ответа.")
    if a["loops"]:
        p, f1, f2 = a["loops"][0]
        att.append(f"возможный круг: {p[0]} и {p[1]} пишут друг другу 3+ раза подряд ({f1} .. {f2}). "
                   f"Нужно решение или новый вопрос.")
    silent = a["never"] + a["quiet"]
    if silent:
        att.append(f"молчит: {', '.join(silent)}. Проверь, знает ли роль, что от неё ждут.")
    L.append("внимание:")
    L.extend("  " + x for x in att[:3]) if att else L.append("  явных сигналов нет.")
    return "\n".join(L) + "\n"


def main(argv=None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description="Сводка по почте ансамбля")
    ap.add_argument("folder", help="папка ансамбля (в ней mail/)")
    ap.add_argument("--last", type=int, default=5, help="K: окно «последние сообщения»")
    ap.add_argument("--roles", default="", help="все роли через запятую (чтобы найти ни разу не писавших)")
    ap.add_argument("--max-age-hours", type=float, default=None,
                    help="показывать кандидатов только моложе N часов (живые долгие ансамбли)")
    ap.add_argument("--window-hours", type=float, default=WINDOW_HOURS,
                    help="окно ответа: адресат не написал отправителю за N часов -> кандидат (по умолчанию 6)")
    ap.add_argument("--top", type=int, default=TOP, help="сколько кандидатов показывать (остальные - числом)")
    a = ap.parse_args(argv)
    msgs = load(Path(a.folder))
    if not msgs:
        print("Писем нет: папка mail пуста или не найдена.")
        return 0
    extra = [x.strip() for x in a.roles.split(",") if x.strip()]
    print(render(analyze(msgs, extra, a.last, a.window_hours), len(msgs), max_age_h=a.max_age_hours, top=a.top), end="")
    return 0


if __name__ == "__main__":
    sys.exit(main())
