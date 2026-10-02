#!/usr/bin/env python3
"""Сводка по почте ансамбля - для хореографа.

Запуск: python tools/mail_stats.py <папка ансамбля> [--last K] [--roles a,b,c]
Читает <папка>/mail/NNN-<от>-to-<кому>.md (кому = роль или all).
Только стандартная библиотека.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

NAME_RE = re.compile(r"^(\d+)-(.+?)-to-(.+)\.md$")
ASK_RE = re.compile(r"\?|\bпрошу\b|\bнужно\b|\bреши\w*|\bответь\w*|\bпроверь\w*", re.I)
ACK_RE = re.compile(r"\b(принял\w*|принято|спасибо|благодарю|работаю|в работе|ок|окей|ok|"
                    r"понял\w*|ясно|жду|готово|приступаю)\b", re.I)
SHORT = 200


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
        out.append({"n": int(m.group(1)), "frm": m.group(2), "to": m.group(3),
                    "name": f.name, "text": text.strip()})
    out.sort(key=lambda x: (x["n"], x["name"]))
    return out


def _refers(text, m):
    """Ссылается ли text на письмо m по имени файла или по номеру («004-...», «письмо 004»)."""
    stem = m["name"][:-3]
    if stem in text or m["name"] in text:
        return True
    return bool(re.search(rf"(?<!\d){m['n']:03d}(?![\d])", text))


def _mentions_role(text, role):
    """Роль role названа в письме как просящая/ждущая («role просит/ждёт»)."""
    return bool(re.search(rf"\b{re.escape(role)}\w*\s+(?:\w+\s+)?(?:просит|ждёт|ждет|ждут|просят)", text, re.I))


def answered(msgs, i):
    """Письмо i отвечено, если после него адресат: написал автору; ИЛИ любое письмо
    ссылается на это письмо по номеру/имени файла; ИЛИ (письмо просило ответить третьему:
    «Z просит/ждёт») адресат написал Z."""
    m = msgs[i]
    later = msgs[i + 1:]
    for x in later:
        if x["frm"] == m["to"] and x["to"] in (m["frm"], "all"):
            return True
        if _refers(x["text"], m):
            return True
    third = {x["frm"] for x in msgs} | {x["to"] for x in msgs}
    for z in third - {m["to"], "all"}:
        if z != m["frm"] and _mentions_role(m["text"], z) and any(
                x["frm"] == m["to"] and x["to"] == z for x in later):
            return True
    return False


def analyze(msgs, roles_extra=(), last=5):
    roles = sorted({m["frm"] for m in msgs} | {m["to"] for m in msgs if m["to"] != "all"}
                   | set(roles_extra))
    st = {r: {"sent": 0, "to_me": 0, "via_all": 0, "open": []} for r in roles}
    matrix = {}
    for i, m in enumerate(msgs):
        st[m["frm"]]["sent"] += 1
        matrix[(m["frm"], m["to"])] = matrix.get((m["frm"], m["to"]), 0) + 1
        if m["to"] == "all":
            for r in roles:
                if r != m["frm"]:
                    st[r]["via_all"] += 1
        else:
            st[m["to"]]["to_me"] += 1
            if not answered(msgs, i):
                st[m["frm"]]["open"].append(m)
    waits = {}
    for r in roles:
        for m in st[r]["open"]:
            if ASK_RE.search(m["text"]):
                waits.setdefault((r, m["to"]), []).append(m["name"])
    never = [r for r in roles if st[r]["sent"] == 0]
    tail = {m["frm"] for m in msgs[-last:]}
    quiet = [r for r in roles if st[r]["sent"] > 0 and r not in tail]
    empty = [m["name"] for m in msgs if len(m["text"]) <= SHORT and ACK_RE.search(m["text"])]
    # круги: 3+ письма подряд между одной парой
    loops, i = [], 0
    while i < len(msgs):
        pair = frozenset((msgs[i]["frm"], msgs[i]["to"]))
        j = i
        while j < len(msgs) and frozenset((msgs[j]["frm"], msgs[j]["to"])) == pair:
            j += 1
        if len(pair) == 2 and j - i >= 3:
            loops.append((sorted(pair), msgs[i]["name"], msgs[j - 1]["name"]))
        i = max(j, i + 1)
    return {"roles": roles, "st": st, "matrix": matrix, "waits": waits,
            "never": never, "quiet": quiet, "empty": empty, "loops": loops, "last": last}


def render(a, total) -> str:
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
    if a["waits"]:
        L.append("Ждут (вопрос или поручение без ответа):")
        for (x, y), names in sorted(a["waits"].items()):
            L.append(f"  {x} ждёт {y}: {', '.join(names)}")
    else:
        L.append("Ждут: никто.")
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
        att.append(f"неотвеченные поручения: {pairs}. Проверь, что адресат письмо увидел.")
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
    a = ap.parse_args(argv)
    msgs = load(Path(a.folder))
    if not msgs:
        print("Писем нет: папка mail пуста или не найдена.")
        return 0
    extra = [x.strip() for x in a.roles.split(",") if x.strip()]
    print(render(analyze(msgs, extra, a.last), len(msgs)), end="")
    return 0


if __name__ == "__main__":
    sys.exit(main())
