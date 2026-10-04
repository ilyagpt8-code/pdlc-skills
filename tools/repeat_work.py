"""Поиск однообразной работы руками: повторяющиеся цепочки вызовов инструментов.

Используется из session_stats.py (summary): раздел «однообразная работа» по роли и
«Кандидаты в инструмент». Только стандартная библиотека; формат журнала не знает -
получает уже разобранные записи (см. session_stats.parse_line).
"""
from __future__ import annotations

import re
from collections import defaultdict

MIN_REPEATS = 3        # цепочка встретилась не реже
MAX_LEN = 4            # длина цепочки 1..MAX_LEN
ERR_LIMIT = 0.30       # доля ошибок, выше которой цепочка «ещё не отработана»
NOT_READY = "ещё не отработана — рано автоматизировать"

_UUID = re.compile(r"\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b", re.I)
_DATE = re.compile(r"\d{4}-\d{2}-\d{2}(?:[T_ ]\d{2}[:\-]\d{2}(?:[:\-]\d{2})?)?")
_HASH = re.compile(r"\b(?=[0-9a-f]*\d)(?=[0-9a-f]*[a-f])[0-9a-f]{7,64}\b", re.I)
_NUM = re.compile(r"\d+")


def _fill(s: str) -> str:
    """Числа, даты, uuid, хэши -> заполнители."""
    s = _UUID.sub("<uuid>", s)
    s = _DATE.sub("<date>", s)
    s = _HASH.sub("<hash>", s)
    return _NUM.sub("<N>", s)


# переписка, делегирование и поиск инструментов - не ручная работа: в цепочки не попадают
SKIP_TOOLS = {"Agent", "SendMessage", "ToolSearch", "TodoWrite", "TaskCreate", "TaskUpdate", "TaskList", "TaskGet"}
SHELL_TOOLS = {"Bash", "PowerShell"}


_PRELUDE = re.compile(
    r"^(?:\$[\w:{}]+\s*[+-]?=|\$env:|[A-Za-z_]\w*=|(?:cd|Set-Location|pushd|export|set|Write-Host|Write-Output|echo)\b|"
    r"\$ErrorActionPreference|\[Console\]|\[System\.|\$OutputEncoding|chcp\b)", re.I)
_SCRIPT_RUNNERS = re.compile(r"python[\d.]*|py|pwsh|powershell|node|bash|sh")
_KEYWORDS = {"if", "foreach", "for", "while", "try", "do", "switch", "function", "import", "from",
             "def", "class", "assert", "with", "else", "elif", "return", "print"}
_KW_CALL = re.compile(r"^(?:%s)(?=[({\[])" % "|".join(sorted(_KEYWORDS)), re.I)
_SPLIT = re.compile(r"\s*(?:&&|;|\n)\s*")


def _bash_shape(cmd: str, tool: str = "Bash") -> str:
    """Первая «содержательная» команда и подкоманда (для python/pwsh - имя скрипта).
    Присваивания переменных, cd/Set-Location, настройка окружения пропускаются."""
    stmts = []
    for x in _SPLIT.split(str(cmd).strip()):
        x = x.strip()
        m = re.match(r"\$[\w:]+\s*=\s*(.*)", x)
        if m and re.match(r"[A-Za-z&][\w.\/:-]*(\s|$)", m.group(1)):
            x = m.group(1)           # $x = Get-Content ... : команда после присваивания
        if x:
            stmts.append(x)
    core = next((x for x in stmts if not _PRELUDE.match(x)), None)
    if core is None:
        core = stmts[0] if stmts else ""
    core = re.sub(r"^(\S*git(?:\.exe)?)\s+-C\s+\S+", r"\1", core)
    core = re.sub(r"\s-ExecutionPolicy\s+\w+", "", core, flags=re.I)
    core = re.sub(r"^(?:&\s+|(?:sudo|time)\s+|timeout\s+\d+\s+)+", "", core)
    core = re.split(r"\s*\|\s*", core, maxsplit=1)[0]
    toks = re.split(r"\s+", core.strip())
    if not toks or not toks[0]:
        return tool
    first = toks[0].strip("'\"").replace("\\", "/").rsplit("/", 1)[-1]
    first = re.sub(r"\.exe$", "", first, flags=re.I)
    if first.startswith(("$", "(", "{")) or first.lower() in _KEYWORDS or _KW_CALL.match(first):
        return tool + " <скрипт>"
    rest = [t for t in toks[1:] if not t.startswith(("-", "$", "'", '"'))]
    rest_all = [t for t in toks[1:] if not t.startswith("-")]
    sub = ""
    if _SCRIPT_RUNNERS.fullmatch(first) and rest_all:
        r0 = rest_all[0].strip("'\"")
        if r0.startswith(("<<", "$")):
            sub = "<inline>"
        else:
            sub = r0.replace("\\", "/").rsplit("/", 1)[-1]
    elif re.fullmatch(r"[A-Z][a-z]+-[A-Z]\w*", first):
        pass                     # командлет PowerShell: подкоманды нет
    elif rest and re.fullmatch(r"[A-Za-z][\w-]*", rest[0]):
        sub = rest[0]
    return _fill(f"{tool} {first}" + (f" {sub}" if sub else ""))


def normalize_call(name: str, inp: dict) -> str:
    inp = inp if isinstance(inp, dict) else {}
    if name in SHELL_TOOLS:
        return _bash_shape(inp.get("command", ""), name)
    if name.startswith("mcp__"):
        return f"{name}({','.join(sorted(inp))})"
    if name in ("Edit", "Write", "NotebookEdit", "Read", "MultiEdit"):
        p = inp.get("file_path") or inp.get("notebook_path") or inp.get("path")
        if isinstance(p, str) and p:
            return f"{name} {_fill(p.replace(chr(92), '/'))}"
    return name


SEARCH_TOOLS = {"Grep", "Glob", "Read", "LS"}
SEARCH_CMDS = {"grep", "rg", "sed", "awk", "cat", "head", "tail", "ls", "find", "wc", "get-content",
               "select-string", "get-childitem"}
GIT_SEARCH = {"log", "show", "diff", "status"}


MAINT_CMDS = {"get-ciminstance", "get-process", "get-date", "get-service", "test-path", "pip"}
MAINT_SUB = {"git": {"fetch", "pull", "push", "add", "commit", "checkout", "branch", "stash", "merge"},
             "docker": {"ps", "logs"},
             "kubectl": {"get", "describe", "logs"}}
_NOTES_PATH = re.compile(r"/memory/|(?:^|/)(?:MEMORY|CLAUDE)\.md$")


def classify(norm: str) -> str:
    """'search' - общий поиск и чтение; 'anon' - безымянный скрипт; 'maint' - обслуживание и
    диагностика, ведение заметок; 'work' - остальное (только оно даёт кандидатов)."""
    parts = norm.split()
    head = parts[0] if parts else ""
    if head in SEARCH_TOOLS:
        return "search"
    if head in ("Edit", "Write", "MultiEdit", "NotebookEdit") and len(parts) > 1 and _NOTES_PATH.search(parts[1]):
        return "maint"
    if head in SHELL_TOOLS and len(parts) > 1:
        if parts[-1] in ("<скрипт>", "<inline>"):
            return "anon"
        first = parts[1].lower()
        sub = parts[2].lower() if len(parts) > 2 else ""
        if first in SEARCH_CMDS or (first == "git" and sub in GIT_SEARCH):
            return "search"
        if first in MAINT_CMDS or sub in MAINT_SUB.get(first, ()):
            return "maint"
    return "work"


def _usage_by_msg(recs):
    by_id, model_of = {}, {}
    for r in recs:
        if r["kind"] == "assistant" and r.get("usage") is not None:
            key = r["msg_id"] or f"_line{r['n']}"
            cur = by_id.setdefault(key, defaultdict(int))
            for k, v in r["usage"].items():
                cur[k] = max(cur[k], v)
            if r.get("model") and not r["model"].startswith("<"):
                model_of[key] = r["model"]
    return by_id, model_of


def _is_run(g):
    """Цепочка - повтор более короткой (AA, ABAB): учитывается как короткая."""
    n = len(g)
    return any(n % p == 0 and g == g[:p] * (n // p) for p in range(1, n))


def find_repeats(recs):
    """-> {"chains": [...], "role_tokens": int, "covered_tokens": int, "covered_pct": float,
    "covered_chains": int, "calls": int}. Цепочки отсортированы по токенам убыванию."""
    by_id, _ = _usage_by_msg(recs)
    err_of = {}
    for r in recs:
        for tid, is_err, _t in r["results"]:
            err_of[tid] = err_of.get(tid, False) or is_err
    calls = []          # (norm, msg_key, rec_n, is_err)
    for r in recs:
        if r["kind"] != "assistant":
            continue
        key = r["msg_id"] or f"_line{r['n']}"
        for tid, name, inp in r["tools"]:
            if name in SKIP_TOOLS:
                continue
            calls.append((normalize_call(name, inp), key, r["n"], bool(err_of.get(tid))))
    kinds = [classify(c[0]) for c in calls]
    # цепочки строятся по work-вызовам; прочие классы (поиск, скрипты, обслуживание) из ряда
    # выпадают: одиночный повтор считается по всем вхождениям в роли, цепочки 2-4 - подряд среди work
    widx = [i for i, k in enumerate(kinds) if k == "work"]
    wcalls = [calls[i] for i in widx]
    seq = [c[0] for c in wcalls]
    msg_kinds = defaultdict(set)
    for c, k in zip(calls, kinds):
        msg_kinds[c[1]].add(k)

    def tok(key):
        u = by_id.get(key)
        return sum(u.values()) if u else 0

    found = {}          # gram -> [start, ...] без перекрытий
    for n in range(1, MAX_LEN + 1):
        last, occ = {}, defaultdict(list)
        for i in range(len(seq) - n + 1):
            g = tuple(seq[i:i + n])
            if i >= last.get(g, 0):
                occ[g].append(i)
                last[g] = i + n
        for g, st in occ.items():
            if len(st) >= MIN_REPEATS and not _is_run(g):
                found[g] = st

    def inside(c, d):
        return len(d) > len(c) and any(d[i:i + len(c)] == c for i in range(len(d) - len(c) + 1))

    grams = list(found)
    keep = [c for c in grams if not any(len(found[d]) == len(found[c]) and inside(c, d) for d in grams)]

    chains, all_keys = [], set()
    for g in keep:
        st, n = found[g], len(g)
        keys, errs, total = set(), 0, 0
        for s in st:
            for c in wcalls[s:s + n]:
                keys.add(c[1])
                errs += c[3]
                total += 1
        all_keys |= keys
        ec = errs / total if total else 0.0
        chains.append({
            "цепочка": list(g), "раз": len(st), "вызовов": total, "доля_ошибок": round(ec, 3),
            "не_отработана": ec > ERR_LIMIT,
            "токенов": sum(tok(k) for k in keys),
            "ответов_модели": len(keys), "ключи": sorted(keys), "первый_n": wcalls[st[0]][2],
            "refs_n": [wcalls[s][2] for s in st[:3]]})
    chains.sort(key=lambda c: (-c["токенов"], -c["раз"]))
    role_tok = sum(sum(u.values()) for u in by_id.values())
    cov = sum(tok(k) for k in all_keys)
    search_keys = {k for k, v in msg_kinds.items() if v == {"search"}}
    search_tok = sum(tok(k) for k in search_keys)
    maint_keys = {k for k, v in msg_kinds.items() if v == {"maint"}}
    maint_tok = sum(tok(k) for k in maint_keys)
    return {"chains": chains, "role_tokens": role_tok, "covered_tokens": cov,
            "covered_pct": round(100 * cov / role_tok, 1) if role_tok else 0.0,
            "covered_chains": len(chains), "calls": len(calls),
            "search_calls": kinds.count("search"), "search_tokens": search_tok,
            "search_pct": round(100 * search_tok / role_tok, 1) if role_tok else 0.0,
            "anon_calls": kinds.count("anon"),
            "maint_calls": kinds.count("maint"), "maint_tokens": maint_tok,
            "maint_pct": round(100 * maint_tok / role_tok, 1) if role_tok else 0.0}


def _label(chain, limit=110):
    s = " → ".join(chain)
    return s if len(s) <= limit else s[:limit - 1] + "…"


def render_role_extra(role, rep):
    """Строки «поиск и чтение» и «безымянные скрипты» (вне доли однообразной работы)."""
    return [f"поиск и чтение: {rep.get('search_pct', 0):g} % токенов роли ({rep.get('search_calls', 0)} вызовов; "
            f"не кандидаты в инструмент)",
            f"обслуживание и диагностика: {rep.get('maint_pct', 0):g} % токенов роли ({rep.get('maint_calls', 0)} вызовов; "
            f"Get-CimInstance/Get-Date, git, pip, docker/kubectl, правки заметок; не кандидаты)",
            f"безымянные скрипты: {rep.get('anon_calls', 0)} (разные скрипты слиплись, не кандидаты)"]


def render_role_line(role, rep):
    ch = rep["chains"]
    if not ch:
        return f"однообразная работа: нет цепочек с {MIN_REPEATS}+ повторами"
    top = ", ".join(f"{_label(c['цепочка'], 70)} ×{c['раз']}" for c in ch[:3])
    return (f"однообразная работа: {rep['covered_pct']:g} % токенов роли в {rep['covered_chains']} "
            f"цепочках (топ-3: {top})")


def render_role_details(role, rep, limit=8):
    out = []
    for i, c in enumerate(rep["chains"][:limit], 1):
        flag = f" — {NOT_READY}" if c["не_отработана"] else ""
        out.append(f"  {_label(c['цепочка'])} ×{c['раз']}: ошибок {int(c['доля_ошибок'] * 100)} %, "
                   f"{c['токенов']} ток., пример {role}#{c['первый_n']}{flag}")
    return out


def candidates(results, top=8):
    """Кандидаты в инструмент: цепочки всех ролей без пометки «не отработана», топ по токенам."""
    rows, skipped = [], 0
    for r in results:
        rep = r.get("однообразная_работа") or {}
        for c in rep.get("chains", []):
            if c["не_отработана"]:
                skipped += 1
            else:
                rows.append((r["роль"], c))
    rows.sort(key=lambda x: -x[1]["токенов"])
    # одни и те же ответы модели не считаем дважды: цепочка, у которой >= половины ответов уже
    # вошли в более крупную цепочку той же роли, - её вариант, в список не идёт
    picked, used = [], defaultdict(set)
    for role, c in rows:
        ks = set(c.get("ключи") or ())
        if ks and len(ks & used[role]) * 2 >= len(ks):
            continue
        used[role] |= ks
        picked.append((role, c))
    return picked[:top], skipped


def render_candidates(results, top=8):
    rows, skipped = candidates(results, top)
    L = ["Кандидаты в инструмент (скрипт или MCP; топ по токенам ответов модели вокруг цепочки):"]
    if not rows:
        L.append("  нет цепочек с 3+ повторами")
    for i, (role, c) in enumerate(rows, 1):
        L.append(f"  {i}. {role}: {_label(c['цепочка'])} ×{c['раз']}, "
                 f"ошибок {int(c['доля_ошибок'] * 100)} %, пример {role}#{c['первый_n']}")
    # Второй взгляд: по числу повторов. Токены ответов вокруг цепочки завышены у долгих
    # сессий с большим контекстом; число повторов показывает, сколько вызовов заменит инструмент.
    shown = {(role, tuple(c["цепочка"])) for role, c in rows}
    by_count, used = [], defaultdict(set)
    allrows = []
    for r in results:
        for c in (r.get("однообразная_работа") or {}).get("chains", []):
            if not c["не_отработана"]:
                allrows.append((r["роль"], c))
    allrows.sort(key=lambda x: -x[1]["раз"])
    for role, c in allrows:
        ks = set(c.get("ключи") or ())
        if ks and len(ks & used[role]) * 2 >= len(ks):
            continue
        used[role] |= ks
        if (role, tuple(c["цепочка"])) not in shown:
            by_count.append((role, c))
        if len(by_count) >= top:
            break
    if by_count:
        L.append("  ещё — по числу повторов (сколько вызовов заменит инструмент):")
        for role, c in by_count:
            L.append(f"   - {role}: {_label(c['цепочка'])} ×{c['раз']}, "
                     f"ошибок {int(c['доля_ошибок'] * 100)} %, пример {role}#{c['первый_n']}")
    if skipped:
        L.append(f"  не включены: {skipped} цепочек с ошибками > {int(ERR_LIMIT * 100)} % ({NOT_READY})")
    return L
