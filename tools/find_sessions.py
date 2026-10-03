"""
Найти журналы сессий Claude Code по заголовку — чтобы составить файл ролей ансамбля.

  python tools/find_sessions.py [подстрока заголовка ...] [--days 14]

Без подстрок — все сессии с активностью за последние --days дней. Печатает:
префикс id (8 знаков — его и пишут в файл ролей), заголовок, последнюю активность,
размер журнала и рабочую папку сессии (туда кладут скиллы). Заголовок берётся из записей custom-title (имя,
которое дал владелец) или ai-title (сгенерированное).
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path


def cwd_of(path: str) -> str:
    """Рабочая папка сессии — поле cwd первой записи, где оно есть."""
    with open(path, encoding="utf-8", errors="replace") as fh:
        for line in fh:
            if '"cwd"' in line:
                try:
                    return json.loads(line).get("cwd", "")
                except ValueError:
                    continue
    return ""


def title_of(path: str) -> str:
    """Последний заголовок сессии: custom-title важнее ai-title."""
    custom = ai = ""
    with open(path, encoding="utf-8", errors="replace") as fh:
        for line in fh:
            if '"custom-title"' not in line and '"ai-title"' not in line:
                continue
            try:
                d = json.loads(line)
            except ValueError:
                continue
            if d.get("type") == "custom-title":
                custom = d.get("customTitle") or custom
            elif d.get("type") == "ai-title":
                ai = d.get("aiTitle") or d.get("title") or ai
    return custom or ai


def main(argv=None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description="Найти журналы сессий по заголовку")
    ap.add_argument("needles", nargs="*", help="подстроки заголовка (без учёта регистра)")
    ap.add_argument("--days", type=float, default=14, help="только сессии с активностью за N дней")
    a = ap.parse_args(argv)
    base = Path(os.path.expanduser("~")) / ".claude" / "projects"
    cutoff = time.time() - a.days * 86400
    rows = []
    for p in glob.glob(str(base / "*" / "*.jsonl")):
        mtime = os.path.getmtime(p)
        if mtime < cutoff:
            continue
        t = title_of(p)
        if a.needles and not any(n.lower() in t.lower() for n in a.needles):
            continue
        rows.append((mtime, Path(p).stem[:8], t or "(без заголовка)", os.path.getsize(p), cwd_of(p) or Path(p).parent.name))
    rows.sort(reverse=True)
    if not rows:
        print("ничего не найдено" + (" по заголовку" if a.needles else ""))
        return 1
    for mtime, pref, t, size, proj in rows:
        print(f"{pref}  {datetime.fromtimestamp(mtime):%Y-%m-%d %H:%M}  {size / 1e6:6.1f} МБ  {t}  [{proj}]")
    return 0


if __name__ == "__main__":
    sys.exit(main())
