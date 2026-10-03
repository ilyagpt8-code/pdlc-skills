#!/usr/bin/env python3
"""Переходник: журналы сессий Claude Code -> почта ансамбля для mail_stats/progress.

Запуск:
  python tools/claude_mail.py <выходная_папка> роль=путь.jsonl [роль=путь.jsonl ...]
         [--since ISO] [--until ISO] [--anon] [--anon-words а,б,в]

Пишет:
  <выход>/mail/NNN-<от>-to-<кому>.md   (первая строка - время; каждое письмо один раз)
  <выход>/journal.md                   (строки «метрика: ...» из ответов агентов)
  <выход>/stats.md                     (session_stats summary по тем же журналам)

Входящее: блок <cross-session-message from=".." name=".."> (также атрибуты
from-session / from-name) в тексте пользовательской записи.
Исходящее: вызов SendMessage (to, message) или mcp__ccd_session_mgmt__send_message
(session_id, message). Одно письмо, видимое у отправителя и получателя, склеивается
по времени (±2 мин) и тексту. Неизвестные участники - роль other.
Только стандартная библиотека.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import session_stats as S  # noqa: E402

MERGE_SEC = 120
BLOCK_RE = re.compile(r"<cross-session-message\b([^>]*)>(.*?)</cross-session-message>", re.S)
ATTR_RE = re.compile(r'([\w-]+)\s*=\s*"([^"]*)"')
SEND_TOOLS = {"SendMessage": "to", "mcp__ccd_session_mgmt__send_message": "session_id"}
OTHER = "other"


def _sid(v) -> str:
    """Канонический id сессии: без префикса local_, в нижнем регистре."""
    v = str(v or "").strip().lower()
    return v[6:] if v.startswith("local_") else v


def _norm(t: str) -> str:
    return re.sub(r"\s+", " ", t or "").strip()


def journal_titles(path):
    """Все заголовки сессии из журнала (custom-title, agent-name, ai-title) - в нижнем регистре."""
    out = set()
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            for line in f:
                if '"-title"' not in line and '"agent-name"' not in line and '-title' not in line:
                    continue
                try:
                    o = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if isinstance(o, dict):
                    for k in ("customTitle", "agentName", "aiTitle"):
                        if isinstance(o.get(k), str) and o[k].strip():
                            out.add(_norm(o[k]).lower())
    except OSError:
        pass
    return out


def role_resolver(pairs, titles=None, aliases=None):
    """pairs [(роль, путь)] -> функция(идентификаторы...) -> роль или other.

    Идентификатор: id из имени файла журнала, имя роли, заголовок сессии (titles:
    роль -> множество заголовков) или выученный псевдоним id (aliases: id -> роль;
    у живых ансамблей id вида local_<uuid> не равен имени файла журнала, его связывают
    с ролью через name="..." входящего письма, равное заголовку сессии)."""
    by_id = {_sid(Path(p).stem): r for r, p in pairs}
    by_name = {r.lower(): r for r, _ in pairs}
    by_title = {t: r for r, ts in (titles or {}).items() for t in ts}
    aliases = aliases if aliases is not None else {}

    def resolve(*keys):
        for k in keys:
            if not k:
                continue
            sk, lk = _sid(k), _norm(str(k)).lower()
            for table, key in ((by_id, sk), (aliases, sk), (by_name, lk), (by_title, lk)):
                if key in table:
                    return table[key]
        return OTHER
    return resolve


def learn_aliases(recs_by_role, titles):
    """id отправителя -> роль, по совпадению name входящего письма с заголовком роли."""
    by_title = {t: r for r, ts in titles.items() for t in ts}
    al = {}
    for recs in recs_by_role.values():
        for r in recs:
            if r["kind"] != "user" or "cross-session-message" not in r["text"]:
                continue
            for m in BLOCK_RE.finditer(r["text"]):
                at = dict(ATTR_RE.findall(m.group(1)))
                role = by_title.get(_norm(at.get("from-name") or at.get("name") or "").lower())
                fid = _sid(at.get("from-session") or at.get("from"))
                if role and fid:
                    al[fid] = role
    return al


def extract(role, recs, resolve, since=None, until=None):
    """Письма одной сессии: список dict(ts, frm, to, text, side)."""
    out = []
    for r in recs:
        ts = r["ts"]
        if ts is None or (since and ts < since) or (until and ts > until):
            continue
        if r["kind"] == "user" and "cross-session-message" in r["text"]:
            for m in BLOCK_RE.finditer(r["text"]):
                at = dict(ATTR_RE.findall(m.group(1)))
                frm = resolve(at.get("from-session"), at.get("from"), at.get("from-name"), at.get("name"))
                out.append({"ts": ts, "frm": frm, "to": role, "text": m.group(2).strip(), "side": "in"})
        elif r["kind"] == "assistant":
            for _id, name, inp in r["tools"]:
                key = SEND_TOOLS.get(name)
                if not key:
                    continue
                msg = inp.get("message")
                if not isinstance(msg, str) or not msg.strip():
                    continue
                to = resolve(inp.get(key))
                out.append({"ts": ts, "frm": role, "to": to, "text": msg.strip(), "side": "out"})
    return out


def _same(a: str, b: str) -> bool:
    a, b = _norm(a), _norm(b)
    if not a or not b:
        return False
    if a == b or a in b or b in a:
        return True
    n = min(len(a), len(b), 200)
    return a[:n] == b[:n]


def merge(msgs):
    """Склеивает исходящее у отправителя и входящее у получателя; сортирует по времени."""
    kept = []
    for m in sorted(msgs, key=lambda x: x["ts"]):
        dup = None
        for k in reversed(kept):
            if (m["ts"] - k["ts"]).total_seconds() > MERGE_SEC:
                break
            if k["side"] != m["side"] and k["frm"] == m["frm"] and k["to"] == m["to"] \
                    and _same(k["text"], m["text"]):
                dup = k
                break
        if dup is None:
            kept.append(dict(m))
        else:
            dup["side"] = "both"
            if len(m["text"]) > len(dup["text"]):
                dup["text"] = m["text"]
    return kept


def anonymize(text, words):
    for w in sorted((w for w in words if w), key=len, reverse=True):
        text = re.sub(re.escape(w), "[скрыто]", text, flags=re.I)
    return text


def safe_role(r):
    return re.sub(r"[^\w.\-]+", "_", r) or OTHER


def metric_lines(recs, since=None, until=None):
    out = []
    for r in recs:
        ts = r["ts"]
        if r["kind"] != "assistant" or ts is None:
            continue
        if (since and ts < since) or (until and ts > until):
            continue
        out += [(ts, ln.strip()) for ln in r["text"].splitlines() if S.METRIC_RE.match(ln)]
    return out


def build(outdir, pairs, since=None, until=None, anon_words=None):
    """Основная работа; возвращает (число_писем, число_метрик)."""
    roles = [r for r, _ in pairs]
    data = {role: S.read_journal(path) for role, path in pairs}
    titles = {role: journal_titles(path) for role, path in pairs}
    resolve = role_resolver(pairs, titles, learn_aliases({r: d[0] for r, d in data.items()}, titles))
    allm, metrics, results = [], [], []
    for role, path in pairs:
        recs, total, skipped = data[role]
        allm += extract(role, recs, resolve, since, until)
        metrics += metric_lines(recs, since, until)
        results.append(S.analyze(role, recs, total, skipped, roles, since, until))
    mails = merge(allm)
    out = Path(outdir)
    mdir = out / "mail"
    mdir.mkdir(parents=True, exist_ok=True)
    for old in mdir.glob("*.md"):
        old.unlink()
    for i, m in enumerate(mails, 1):
        text = anonymize(m["text"], anon_words) if anon_words else m["text"]
        name = f"{i:03d}-{safe_role(m['frm'])}-to-{safe_role(m['to'])}.md"
        (mdir / name).write_text(f"{m['ts'].strftime('%Y-%m-%dT%H:%M:%SZ')}\n\n{text}\n", encoding="utf-8")
    metrics.sort(key=lambda x: x[0])
    (out / "journal.md").write_text(
        "# Журнал ансамбля (метрики из ответов агентов)\n\n" + "".join(f"{x}\n" for _, x in metrics),
        encoding="utf-8")
    (out / "stats.md").write_text(
        "# Сводка по журналам сессий\n\n```\n" + S.render_text(results) + "```\n", encoding="utf-8")
    return len(mails), len(metrics)


def main(argv=None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("outdir")
    ap.add_argument("items", nargs="+", help="роль=путь.jsonl")
    ap.add_argument("--since")
    ap.add_argument("--until")
    ap.add_argument("--anon", action="store_true", help="скрывать слова из --anon-words в письмах")
    ap.add_argument("--anon-words", default="", help="слова через запятую")
    a = ap.parse_args(argv)
    pairs = []
    for it in a.items:
        role, path = S._split_role_path(it)
        if not role:
            raise SystemExit(f"ожидалось роль=путь, получено: {it}")
        if not Path(path).is_file():
            raise SystemExit(f"нет файла журнала: {path}")
        pairs.append((role, path))
    words = [w.strip() for w in a.anon_words.split(",") if w.strip()] if a.anon else None
    nm, nt = build(a.outdir, pairs, S._iso(a.since), S._iso(a.until), words)
    print(f"писем: {nm}, строк метрик: {nt}; результат: {a.outdir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
