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
from-session / from-name) в тексте пользовательской записи, в queue-operation (enqueue)
и в attachment (queued_command); один блок из разных записей - одно письмо.
Исходящее: вызов SendMessage (to, message) или mcp__ccd_session_mgmt__send_message
(session_id, message). Одно письмо, видимое у отправителя и получателя, склеивается
по (отправитель, получатель, текст) в пределах 12 ч (доставка может ждать в очереди).
Адресат - id/uds-канал/local_<uuid>: роль берётся из таблицы «id -> роль», собранной по полям
from, from-session, from-name, name всех входящих. Субагент (agentId из записи запуска Agent)
- роль "<роль>/sub:<id>"; его <task-notification> - письмо от него. Внешняя сессия без журнала
- other:<заголовок>. Неизвестные участники - other.
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

MERGE_SEC = 12 * 3600      # доставка ждёт в очереди 4-10 мин, иногда часы
BLOCK_RE = re.compile(r"<cross-session-message\b([^>]*)>(.*?)</cross-session-message>", re.S)
ID_RE = re.compile(r"^(?:(?:local_)?[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}|uds:\S+)$", re.I)
AGENT_ID_RE = re.compile(r"^a[0-9a-f]{16}$")
AGENT_RES_RE = re.compile(r"agentId:\s*(a[0-9a-f]{16})")
# ответ инструмента отправки: письмо не доставлено (адресат недоступен, лимит, сбой канала)
FAILED_RE = re.compile(r'"success"\s*:\s*false|^\s*Not delivered|Failed to send to', re.I)
STUB_RE = re.compile(r"report was delivered to you as a message from", re.I)   # заглушка без содержания
NOTIF_RE = re.compile(r"<task-notification>(.*?)</task-notification>", re.S)
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
    роль -> множество заголовков) или выученный псевдоним id (aliases: id -> роль; у живых
    ансамблей id вида local_<uuid> и uds-канал не равны имени файла журнала, их связывают
    с ролью через name/from-name входящего письма, равное заголовку сессии; субагент -
    через agentId -> "<роль>/sub:<id>"; внешняя сессия - "other:<имя>")."""
    by_id = {_sid(Path(p).stem): r for r, p in pairs}
    by_name = {r.lower(): r for r, _ in pairs}
    by_title = {t: r for r, ts in (titles or {}).items() for t in ts}
    aliases = aliases if aliases is not None else {}

    def resolve(*keys):
        other = None
        for k in keys:
            if not k:
                continue
            sk, lk = _sid(k), _norm(str(k)).lower()
            for table, key in ((by_id, sk), (aliases, sk), (by_name, lk), (by_title, lk)):
                if key in table:
                    v = table[key]
                    if v.startswith(OTHER + ":"):
                        other = other or v      # внешняя: ищем роль по остальным ключам
                        continue
                    return v
        return other or OTHER
    return resolve


def _blocks(text):
    """Блоки <cross-session-message ...> текста: [(атрибуты, тело)]; цитаты без id пропущены."""
    out = []
    for m in BLOCK_RE.finditer(text or ""):
        at = dict(ATTR_RE.findall(m.group(1)))
        if ID_RE.match(at.get("from-session") or at.get("from") or ""):
            out.append((at, m.group(2).strip()))
    return out


def learn_aliases(recs_by_role, titles):
    """Таблица «id -> роль» по всем входящим всех журналов.

    Поля from (uds-канал), from-session (local_<uuid>) и имя (from-name или name) одного блока
    называют одного отправителя: имя равно заголовку сессии роли -> все его id = эта роль;
    имя ансамблю неизвестно -> other:<имя> (внешняя сессия без журнала). Роль не затирается
    значением other."""
    by_title = {t: r for r, ts in titles.items() for t in ts}
    al = {}
    for recs in recs_by_role.values():
        for r in recs:
            if r["kind"] != "user" or "cross-session-message" not in r["text"]:
                continue
            for at, _body in _blocks(r["text"]):
                name = _norm(at.get("from-name") or at.get("name") or "")
                if not name:
                    continue
                role = by_title.get(name.lower()) or f"{OTHER}:{name}"
                for k in ("from", "from-session"):
                    fid = _sid(at.get(k))
                    if not (fid and ID_RE.match(fid)):
                        continue
                    if role.startswith(OTHER + ":") and al.get(fid, OTHER + ":").split(":")[0] != OTHER:
                        continue
                    al[fid] = role
    return al


def learn_agents(recs_by_role):
    """agentId -> "<роль>/sub:<id>" по записям запуска Agent в журналах отправителей."""
    out = {}
    for role, recs in recs_by_role.items():
        for r in recs:
            for _tid, _err, txt in r.get("results", ()):
                for aid in AGENT_RES_RE.findall(txt or ""):
                    out[aid] = f"{role}/sub:{aid[:9]}"
    return out


def raw_mail_items(path):
    """Входящие из queue-operation (enqueue) и attachment (queued_command) JSONL-журнала
    как записи вида user (src=queue/attachment). Для не-JSONL (list_events) - пусто."""
    out = []
    try:
        f = open(path, encoding="utf-8", errors="replace")
    except OSError:
        return out
    with f:
        for line in f:
            if "cross-session-message" not in line and "<task-notification>" not in line:
                continue
            if '"queue-operation"' not in line and '"queued_command"' not in line:
                continue
            try:
                o = json.loads(line)
            except json.JSONDecodeError:
                continue
            if not isinstance(o, dict):
                continue
            if o.get("type") == "queue-operation" and o.get("operation") == "enqueue":
                text, src = o.get("content"), "queue"
            elif o.get("type") == "attachment" and isinstance(o.get("attachment"), dict) \
                    and o["attachment"].get("type") == "queued_command":
                text, src = S._block_text(o["attachment"].get("prompt")), "attachment"
            else:
                continue
            ts = S._parse_ts(o.get("timestamp"))
            if isinstance(text, str) and ts is not None:
                out.append({"kind": "user", "ts": ts, "text": text, "tools": [], "results": [], "src": src})
    return out


def extract(role, recs, resolve, since=None, until=None):
    """Письма одной сессии: список dict(ts, frm, to, text, side, src)."""
    out = []
    failed = {tid for r in recs for tid, err, txt in r.get("results", ()) if err or FAILED_RE.search(txt or "")}
    for r in recs:
        ts = r["ts"]
        if ts is None or (since and ts < since) or (until and ts > until):
            continue
        if r["kind"] == "user":
            src = r.get("src", "user")
            if "cross-session-message" in r["text"]:
                for at, body in _blocks(r["text"]):
                    frm = resolve(at.get("from-session"), at.get("from"), at.get("from-name"), at.get("name"))
                    out.append({"ts": ts, "frm": frm, "to": role, "text": body, "side": "in", "src": src})
            if "<task-notification>" in r["text"]:
                for m in NOTIF_RE.finditer(r["text"]):
                    tid = re.search(r"<task-id>\s*(\S+?)\s*</task-id>", m.group(1))
                    frm = resolve(tid.group(1)) if tid else OTHER
                    if "/sub:" not in frm:
                        continue            # не субагент (фоновая команда и т.п.) - не письмо
                    body = re.search(r"<result>(.*?)</result>", m.group(1), re.S) \
                        or re.search(r"<summary>(.*?)</summary>", m.group(1), re.S)
                    if body and body.group(1).strip() and not STUB_RE.search(body.group(1)):
                        out.append({"ts": ts, "frm": frm, "to": role, "text": body.group(1).strip(),
                                    "side": "in", "src": src})
        elif r["kind"] == "assistant":
            for _id, name, inp in r["tools"]:
                key = SEND_TOOLS.get(name)
                if not key or _id in failed:       # недоставленное - не письмо
                    continue
                msg = inp.get("message")
                if not isinstance(msg, str) or not msg.strip():
                    continue
                to = resolve(inp.get(key))
                raw_to = _norm(str(inp.get(key) or ""))
                if to == OTHER and raw_to and not ID_RE.match(raw_to) and not AGENT_ID_RE.match(raw_to):
                    to = f"{OTHER}:{raw_to}"        # внешняя сессия, названная заголовком
                out.append({"ts": ts, "frm": role, "to": to, "text": msg.strip(), "side": "out", "src": "out"})
    return out


def _same(a: str, b: str) -> bool:
    a, b = _norm(a), _norm(b)
    if not a or not b:
        return False
    if a == b or a in b or b in a:
        return True
    n = min(len(a), len(b), 200)
    # копии одного письма отличаются мелочью; разной длины (повторный отчёт) - разные письма
    return a[:n] == b[:n] and min(len(a), len(b)) >= 0.9 * max(len(a), len(b))


def merge(msgs):
    """Склеивает копии одного письма: исходящее у отправителя и входящее у получателя
    (из записи пользователя, queue-operation, attachment) - по (отправитель, получатель, текст)
    без точного окна: в пределах MERGE_SEC. Каждый канал даёт копию письма не больше одного
    раза, поэтому два одинаковых письма подряд остаются двумя. Сортировка по времени."""
    clusters = []
    for m in sorted(msgs, key=lambda x: x["ts"]):
        ch = m.get("src") or ("out" if m["side"] == "out" else "user")
        best = None
        for k in clusters:
            if ch in k["chans"] or k["frm"] != m["frm"] or k["to"] != m["to"]:
                continue
            gap = abs((m["ts"] - k["ts"]).total_seconds())
            if gap > MERGE_SEC or not _same(k["text"], m["text"]):
                continue
            if best is None or gap < best[0]:
                best = (gap, k)
        if best is None:
            clusters.append({"ts": m["ts"], "frm": m["frm"], "to": m["to"], "text": m["text"],
                             "chans": {ch}, "sides": {m["side"]}})
        else:
            k = best[1]
            k["chans"].add(ch)
            k["sides"].add(m["side"])
            k["ts"] = min(k["ts"], m["ts"])
            if len(m["text"]) > len(k["text"]):
                k["text"] = m["text"]
    out = []
    for k in clusters:
        side = "both" if len(k["sides"]) > 1 else next(iter(k["sides"]))
        out.append({"ts": k["ts"], "frm": k["frm"], "to": k["to"], "text": k["text"], "side": side})
    out.sort(key=lambda x: x["ts"])
    return out


def anonymize(text, words):
    for w in sorted((w for w in words if w), key=len, reverse=True):
        text = re.sub(re.escape(w), "[скрыто]", text, flags=re.I)
    return text


def safe_role(r):
    return re.sub(r"[^\w.\-]+", "_", r).strip("_")[:48] or OTHER


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
    mailrecs = {r: data[r][0] + raw_mail_items(p) for r, p in pairs}   # + queue-operation, attachment
    titles = {role: journal_titles(path) for role, path in pairs}
    aliases = learn_aliases(mailrecs, titles)
    aliases.update(learn_agents({r: d[0] for r, d in data.items()}))
    resolve = role_resolver(pairs, titles, aliases)
    allm, metrics, results = [], [], []
    for role, path in pairs:
        recs, total, skipped = data[role]
        allm += extract(role, mailrecs[role], resolve, since, until)
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
        lab = (lambda x: anonymize(x, anon_words)) if anon_words else (lambda x: x)
        name = f"{i:03d}-{safe_role(lab(m['frm']))}-to-{safe_role(lab(m['to']))}.md"
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
