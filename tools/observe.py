"""
Снимок живого ансамбля для наблюдателя (продюсера или хореографа) одной командой.

  python tools/observe.py <файл ролей> <выходная папка> [--max-age-hours 12]

Файл ролей — строки `роль=префикс_uuid_журнала` (журналы Claude Code ищутся в
~/.claude/projects/*/). Скрипт находит журналы, строит почту ансамбля
(claude_mail.py), сводку расхода (session_stats.py, в т. ч. «Кандидаты в
инструмент»), сводку почты (mail_stats.py) и прогресс по метрикам (progress.py),
и кладёт всё в выходную папку: mail/, stats.md, mail_stats.md, progress.md, trends.md
(закономерности за дни: trends.py).
Данные живого ансамбля остаются локально — выходную папку не коммитить.
"""
from __future__ import annotations

import argparse
import glob
import os
import subprocess
import sys
from pathlib import Path

TOOLS = Path(__file__).resolve().parent


def find_journal(prefix: str) -> str:
    base = Path(os.path.expanduser("~")) / ".claude" / "projects"
    hits = sorted(glob.glob(str(base / "*" / f"{prefix}*.jsonl")), key=os.path.getsize, reverse=True)
    if not hits:
        raise SystemExit(f"журнал с префиксом {prefix} не найден в {base}")
    return hits[0]


def run(args: list[str], out: Path) -> None:
    res = subprocess.run([sys.executable, *args], capture_output=True, text=True, encoding="utf-8",
                         env={**os.environ, "PYTHONIOENCODING": "utf-8"})
    out.write_text(res.stdout + (f"\n[ошибка]\n{res.stderr}" if res.returncode else ""), encoding="utf-8")


def main(argv=None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description="Снимок живого ансамбля для наблюдателя")
    ap.add_argument("roles_file")
    ap.add_argument("outdir")
    ap.add_argument("--max-age-hours", type=float, default=12)
    a = ap.parse_args(argv)
    pairs = []
    for line in Path(a.roles_file).read_text(encoding="utf-8").splitlines():
        line = line.split("#", 1)[0].strip()
        if "=" in line:
            role, prefix = (x.strip() for x in line.split("=", 1))
            pairs.append((role, find_journal(prefix)))
    out = Path(a.outdir)
    out.mkdir(parents=True, exist_ok=True)
    items = [f"{r}={p}" for r, p in pairs]
    roles = ",".join(r for r, _ in pairs)
    subprocess.run([sys.executable, str(TOOLS / "claude_mail.py"), str(out), *items], check=True,
                   capture_output=True, env={**os.environ, "PYTHONIOENCODING": "utf-8"})
    run([str(TOOLS / "session_stats.py"), "summary", *items], out / "stats.md")
    run([str(TOOLS / "mail_stats.py"), str(out), "--roles", roles, "--max-age-hours", str(a.max_age_hours)],
        out / "mail_stats.md")
    run([str(TOOLS / "progress.py"), str(out / "journal.md"), "--stats", str(out / "stats.md")], out / "progress.md")
    run([str(TOOLS / "trends.py"), str(out), "--roles", roles], out / "trends.md")
    sys.path.insert(0, str(TOOLS))
    from find_sessions import title_of
    for r, p in pairs:
        print(f"  {r} = {Path(p).stem[:8]} «{title_of(p) or '(без заголовка)'}»")
    print(f"снимок готов: {out} (роли: {roles}) — сверь заголовки выше с составом ансамбля")
    return 0


if __name__ == "__main__":
    sys.exit(main())
