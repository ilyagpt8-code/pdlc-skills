#!/usr/bin/env python3
"""Закономерности за дни - для наблюдателей (продюсер, хореограф).

Запуск: python tools/trends.py <папка снимка> [--days 7] [пороги...]
Папка - та, что строит observe.py: mail/ (первая строка письма - время), journal_times.txt
(или journal.md без времени), stats.md. Дни - UTC; последний день - день последнего письма.
Флаг ставится, только если условие держится несколько дней подряд или в нескольких днях.
Выводит раздел «Закономерности» (сработавшие флаги) и таблицу по дням. Содержания писем не выводит.
Только стандартная библиотека.
"""
from __future__ import annotations

import argparse
import re
import statistics
import sys
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import mail_stats as M  # noqa: E402
import progress as P  # noqa: E402

DEFAULTS = dict(
    days=7,
    queue_age_h=24.0,       # ждущим считается письмо не старше N часов на конец дня (старые - закрыты делом)
    queue_rise_days=3,      # очередь растёт столько дней подряд (шагов роста)
    owner_slow_h=4.0,       # ответ владельца дольше X часов (медиана за день)
    owner_slow_days=3,      # ... в стольких днях из последних
    burst_n=5,              # вопросов владельцу за час - «пачка»
    burst_days=2,           # пачки в стольких днях
    repeat_days=2,          # та же пара повторяется без ответа в стольких разных днях
    metric_flat_days=3,     # метрика не двигается столько дней / нет строк метрики столько дней
    spend_days=3,           # одна роль «тратит больше всех» столько дней подряд
    churn_share=0.5,        # доля текучки от писем дня
    churn_days=3,           # ... в стольких днях из последних
    churn_min_mails=10,     # день с меньшим числом писем в долю не считается
)


def day_of(ts):
    return ts.astimezone(timezone.utc).date()


def _days(msgs, n):
    last = max((m["ts"] for m in msgs if m.get("ts")), default=None)
    if last is None:
        return [], None
    end = day_of(last)
    return [end - timedelta(days=i) for i in range(n - 1, -1, -1)], last


def load_metrics(folder: Path):
    """[(ts|None, name, value)] из journal_times.txt; без него - journal.md (время неизвестно)."""
    out = []
    jt = folder / "journal_times.txt"
    if jt.is_file():
        for ln in jt.read_text(encoding="utf-8", errors="replace").splitlines():
            t, _, line = ln.partition("\t")
            try:
                ts = datetime.fromisoformat(t.replace("Z", "+00:00"))
            except ValueError:
                continue
            for p in P.parse_journal(line)[0]:
                out.append((ts, p["name"], p["value"]))
    else:
        j = folder / "journal.md"
        if j.is_file():
            for p in P.parse_journal(j.read_text(encoding="utf-8", errors="replace"))[0]:
                out.append((None, p["name"], p["value"]))
    return out


def is_churn(m):
    """Короткое подтверждение или отчёт без просьбы (как в mail_stats)."""
    if m["frm"] == M.OWNER or M.is_sub(m["frm"]):
        return False
    sig = M.signals_of(m["text"])
    if "вопрос" in sig:
        return False
    if len(m["text"]) <= M.SHORT and M.ACK_RE.search(m["text"]):
        return True
    return M.is_report(m["text"], sig)


def compute(msgs, roles_extra=(), **kw):
    c = {**DEFAULTS, **kw}
    days, last = _days(msgs, c["days"])
    res = {"days": days, "params": c, "flags": [], "note": []}
    if not days:
        res["note"].append("у писем нет времени - по дням считать нечего")
        return res
    stamped = [m for m in msgs if m.get("ts")]
    by_ts = {m["name"]: m for m in stamped}
    bday = defaultdict(list)
    for m in stamped:
        bday[day_of(m["ts"])].append(m)
    flags = res["flags"]

    # --- 1. очередь у узла
    a = M.analyze(msgs, list(roles_extra))
    cands = [it for it in a["wait_items"] if not it["report"] and it["name"] in by_ts]
    node_n = Counter()
    for it in cands:
        d = day_of(by_ts[it["name"]]["ts"])
        if days[0] <= d <= days[-1]:
            node_n[it["to"]] += 1
    node = node_n.most_common(1)[0][0] if node_n else None
    q = {}
    for d in days:
        end = datetime(d.year, d.month, d.day, tzinfo=timezone.utc) + timedelta(days=1)
        ages = [(end - by_ts[it["name"]]["ts"]).total_seconds() for it in cands
                if node and it["to"] == node and by_ts[it["name"]]["ts"] < end
                and (end - by_ts[it["name"]]["ts"]).total_seconds() <= c["queue_age_h"] * 3600]
        q[d] = (len(ages), max(ages) if ages else 0)
    res["queue_node"], res["queue"] = node, q
    if node:
        rise = 0
        for i in range(len(days) - 1, 0, -1):
            if q[days[i]][0] > q[days[i - 1]][0]:
                rise += 1
            else:
                break
        if rise >= c["queue_rise_days"]:
            seq = "→".join(str(q[d][0]) for d in days[-rise - 1:])
            flags.append(f"очередь у {node} растёт {rise} дней подряд (ждущих на конец дня: {seq}; "
                         f"самое долгое сейчас {M._age(q[days[-1]][1])})")

    # --- 2. владелец как узкое место
    owner = {d: {"n": 0, "waits": [], "open": 0} for d in days}
    qs = []
    for i, m in enumerate(msgs):
        if m["to"] == M.OWNER and m["frm"] != M.OWNER and not M.is_sub(m["frm"]) and m.get("ts") \
                and M.is_question(m["text"]):
            d = day_of(m["ts"])
            rep = next((x for x in msgs[i + 1:] if x["frm"] == M.OWNER and x["to"] == m["frm"]
                        and x.get("ts") and x["ts"] >= m["ts"]), None)
            qs.append(m)
            if d in owner:
                owner[d]["n"] += 1
                if rep:
                    owner[d]["waits"].append((rep["ts"] - m["ts"]).total_seconds())
                else:
                    owner[d]["open"] += 1
    res["owner"] = owner
    slow = [d for d in days if owner[d]["waits"] and statistics.median(owner[d]["waits"]) > c["owner_slow_h"] * 3600]
    if len(slow) >= c["owner_slow_days"]:
        meds = ", ".join(f"{d:%m-%d} {statistics.median(owner[d]['waits']) / 3600:.1f}" for d in slow)
        flags.append(f"ответ владельца дольше {c['owner_slow_h']:g} ч (медиана) в {len(slow)} из последних "
                     f"{len(days)} дней (часы по дням: {meds})")
    burst_days = []
    for d in days:
        ts = sorted(m["ts"] for m in qs if day_of(m["ts"]) == d)
        best, j = 0, 0
        for i in range(len(ts)):
            while ts[i] - ts[j] > timedelta(hours=1):
                j += 1
            best = max(best, i - j + 1)
        if best >= c["burst_n"]:
            burst_days.append((d, best))
    res["bursts"] = dict(burst_days)
    if len(burst_days) >= c["burst_days"]:
        flags.append(f"вопросы владельцу приходят пачками (≥{c['burst_n']} за час) в {len(burst_days)} днях: "
                     + ", ".join(f"{d:%m-%d} ({n})" for d, n in burst_days))

    # --- 3. повторы без ответа
    rep_by_day = {d: [] for d in days}
    for r in a["repeats"]:
        if r["replied"] or r["name"] not in by_ts:
            continue
        if r["frm"].startswith("other") or r["to"].startswith("other"):
            continue  # внешние сессии — не роли ансамбля, их повторы не закономерность команды
        d = day_of(by_ts[r["name"]]["ts"])
        if d in rep_by_day:
            rep_by_day[d].append((r["frm"], r["to"]))
    res["repeats"] = rep_by_day
    pair_days = defaultdict(set)
    for d, ps in rep_by_day.items():
        for p in ps:
            pair_days[p].add(d)
    for p, ds in sorted(pair_days.items(), key=lambda x: -len(x[1])):
        if len(ds) >= c["repeat_days"]:
            flags.append(f"повтор без ответа {p[0]} → {p[1]} в {len(ds)} разных днях ("
                         + ", ".join(f"{d:%m-%d}" for d in sorted(ds)) + ")")

    # --- 4. метрики
    mets = load_metrics(Path(c["folder"])) if c.get("folder") else []
    dated = [x for x in mets if x[0]]
    mday = {d: {} for d in days}
    for ts, name, v in sorted(dated, key=lambda x: x[0]):
        d = day_of(ts)
        if d in mday:
            mday[d][name] = v
    res["metrics"] = mday
    n = c["metric_flat_days"]
    tail = days[-n:]
    if not mets:
        flags.append(f"нет ни одной строки метрики за {len(days)} дней (в журнале метрик нет вовсе)")
        metric_flat = True
    elif not dated:
        res["note"].append("у строк метрик нет времени (journal.md без journal_times.txt) - по дням не считал")
        metric_flat = False
    elif not any(mday[d] for d in tail):
        flags.append(f"нет ни одной строки метрики за последние {n} дней")
        metric_flat = True
    else:
        metric_flat = False
        for name in sorted({x[1] for x in dated}):
            vals = []
            known = None
            for ts, nm, v in sorted(dated, key=lambda x: x[0]):
                if nm == name and day_of(ts) < tail[0]:
                    known = v
            for d in tail:
                known = mday[d].get(name, known)
                vals.append(known)
            if None not in vals and len(set(vals)) == 1 and \
                    sum(1 for ts, nm, _ in dated if nm == name and day_of(ts) >= tail[0]) >= 1:
                flags.append(f"метрика {name} не двигается {n} дней (значение {P.fmt(vals[0])})")
                metric_flat = True

    # --- 5. расход по ролям (прокси: письма, отправленные ролью за день)
    sent = {d: Counter(M.fold(m["frm"]) for m in bday[d] if m["frm"] != M.OWNER and not M.is_sub(m["frm"]))
            for d in days}
    res["spend"] = sent
    top = {d: (sent[d].most_common(1)[0][0] if sent[d] else None) for d in days}
    res["spend_top"] = top
    run_role, run = None, 0
    for d in days:
        if top[d] and top[d] == run_role:
            run += 1
        else:
            run_role, run = top[d], 1 if top[d] else 0
    if run_role and run >= c["spend_days"]:
        tail_txt = "; метрика не двигается" if mets and metric_flat else (
            "" if mets else " (метрики нет - вторая часть условия не проверялась)")
        # Без метрики «тратит больше всех» на узле — постоянный шум (узел всегда пишет больше всех);
        # флаг только когда у роли есть метрика и она стоит.
        if mets and metric_flat:
            flags.append(f"роль {run_role} тратит больше всех {run} дней подряд (по числу писем - прокси "
                         f"активности, не токены){tail_txt}")

    # --- 6. текучка
    churn = {}
    for d in days:
        ms = [m for m in bday[d] if m["frm"] != M.OWNER and not M.is_sub(m["frm"]) and m["to"] != M.OWNER]
        churn[d] = (len(ms), sum(1 for m in ms if is_churn(m)))
    res["churn"] = churn
    heavy = [d for d in days if churn[d][0] >= c["churn_min_mails"] and churn[d][1] / churn[d][0] >= c["churn_share"]]
    if len(heavy) >= c["churn_days"]:
        flags.append(f"текучка ≥{c['churn_share']:.0%} писем в {len(heavy)} из последних {len(days)} дней ("
                     + ", ".join(f"{d:%m-%d} {churn[d][1]}/{churn[d][0]}" for d in heavy) + ")")
    return res


def render(res) -> str:
    L = ["# Закономерности за дни (UTC)", ""]
    if res["note"]:
        L += [f"Примечание: {x}." for x in res["note"]] + [""]
    if not res["days"]:
        return "\n".join(L) + "\n"
    L.append("## Закономерности")
    L += [f"- {f}" for f in res["flags"]] or ["закономерностей нет"]
    L += ["", "## По дням", ""]
    node = res.get("queue_node") or "-"
    hdr = ["день", "писем", "текучка", f"ждут у {node} (долгое)", "вопр. влад.", "мед/макс ожид. влад., ч",
           "повторы без отв.", "метрики", "больше всех писал*"]
    L.append("| " + " | ".join(hdr) + " |")
    L.append("|" + "---|" * len(hdr))
    for d in res["days"]:
        n, ch = res["churn"][d]
        wq, wage = res["queue"][d]
        o = res["owner"][d]
        w = o["waits"]
        ow = f"{statistics.median(w) / 3600:.1f}/{max(w) / 3600:.1f}" if w else "-"
        if o["open"]:
            ow += f" (+{o['open']} без отв.)"
        met = ", ".join(f"{k}={P.fmt(v)}" for k, v in sorted(res["metrics"][d].items())) or "-"
        t = res["spend_top"][d]
        top = f"{t} ({res['spend'][d][t]})" if t else "-"
        L.append(f"| {d:%m-%d} | {n} | {ch} | {wq} ({M._age(wage) if wq else '-'}) | {o['n']} | {ow} | "
                 f"{len(res['repeats'][d])} | {met} | {top} |")
    L += ["", "* расход - прокси: число писем роли за день (не токены и не время сессии).",
          "Письма между ролями без владельца; текучка - короткие подтверждения и отчёты без просьбы.",
          "Ждущие на конец дня - кандидаты mail_stats (без отчётов), не старше "
          f"{res['params']['queue_age_h']:g} ч; ответ, пришедший после конца дня в окне 2 ч, не учтён."]
    return "\n".join(L) + "\n"


def main(argv=None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description="Закономерности за дни")
    ap.add_argument("folder")
    ap.add_argument("--days", type=int, default=DEFAULTS["days"])
    ap.add_argument("--roles", default="")
    for k, v in DEFAULTS.items():
        if k != "days":
            ap.add_argument("--" + k.replace("_", "-"), type=type(v), default=v)
    a = ap.parse_args(argv)
    msgs = M.load(Path(a.folder))
    if not msgs:
        print("Писем нет: папка mail пуста или не найдена.")
        return 0
    kw = {k: getattr(a, k) for k in DEFAULTS}
    res = compute(msgs, [x for x in a.roles.split(",") if x], folder=a.folder, **kw)
    print(render(res), end="")
    return 0


if __name__ == "__main__":
    sys.exit(main())
