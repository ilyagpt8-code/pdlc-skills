#!/usr/bin/env python3
"""Сводка по журналам сессий Claude Code (JSONL) для агентов-наблюдателей.

Команды:
  summary роль=путь [роль=путь ...] [--since ISO] [--until ISO] [--json]
                  [--prices вход,вывод,чтение_кэша,запись_кэша]
  show роль#N путь          (или: show роль#N роль=путь)

Только стандартная библиотека. Два формата, определяются по содержимому файла:
  1) JSONL собственного журнала Claude Code (parse_line);
  2) JSON-ответ list_events (формат API сессий): {"data":[...]}, возможно в обёртке
     {"ccr":{...}}, либо список страниц ответов (parse_event).
Весь разбор формата - в parse_line()/parse_event()/read_journal().
Номер записи N - порядковый номер непустой строки журнала (JSONL) или события
в data[] (list_events), с 1.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone

import repeat_work as RW

# цены за 1 млн токенов по умолчанию: Haiku 4.5 (вход, вывод, чтение кэша, запись кэша)
DEFAULT_PRICES = (1.0, 5.0, 0.10, 1.25)
DEFAULT_PRICES_NAME = "Haiku 4.5"
# Цены по модели (message.model в журнале): подстрока имени модели -> (название, цены, примечание).
# Haiku 4.5 - прайс-лист. ДОПУЩЕНИЕ: для Opus 5.5 цены 4/20/0.2/8 не из прайса, а подобраны по
# журналам (сходятся с costUSD в cost-state на живом ансамбле). ДОПУЩЕНИЕ: для Sonnet 5.5 по
# заданию предполагалось 3/15/0.3/3.75, но по cost-state живого ансамбля стоимость в 1.5 раза ниже
# (4 сессии из 6 сходятся точно), поэтому взято 2/10/0.2/2.5; это тоже подбор, не прайс.
# Модели других версий (claude-opus-5 и т.п.) - те же цены линейки с пометкой; неизвестная -> Haiku 4.5.
MODEL_PRICES = (
    ("haiku", ("Haiku 4.5", (1.0, 5.0, 0.10, 1.25), "")),
    ("sonnet-5-5", ("Sonnet 5.5", (2.0, 10.0, 0.2, 2.5), "допущение, подобрано по cost-state")),
    ("opus-5-5", ("Opus 5.5", (4.0, 20.0, 0.2, 8.0), "допущение, подобрано по cost-state")),
    ("sonnet", ("Sonnet 5.5", (2.0, 10.0, 0.2, 2.5), "допущение, цены Sonnet 5.5 для другой версии")),
    ("opus", ("Opus 5.5", (4.0, 20.0, 0.2, 8.0), "допущение, цены Opus 5.5 для другой версии")),
)
COST_WARN = 0.25        # расхождение оценки и cost-state журнала, после которого предупреждаем


def model_prices(model):
    """(название, цены, примечание) по имени модели; неизвестная/пустая -> Haiku 4.5."""
    m = (model or "").lower()
    for key, val in MODEL_PRICES:
        if key in m:
            return val
    if m and not m.startswith("<"):
        return (DEFAULT_PRICES_NAME, DEFAULT_PRICES, f"нет цены для {model}, взяты Haiku 4.5")
    return (DEFAULT_PRICES_NAME, DEFAULT_PRICES, "")
IDLE_GAP = 300          # секунд; пауза длиннее не входит в «активную работу»
SHORT_LEN = 60          # реплика короче - кандидат в «пустую»
SHOW_LIMIT = 2000
EXAMPLE_LEN = 90

METRIC_RE = re.compile(r"^\s*(?:метрика\s*:|отрезок\s+\d+\s*:)", re.I)
EMPTY_RE = re.compile(
    r"^(ок|окей|ok|okay|хорошо|ладно|понял[аи]?|принято|принял[аи]?|ясно|спасибо|благодарю|"
    r"thanks|thank you|thx|got it|ack|roger|noted|done|готово|отлично|супер|great|good|"
    r"работаю|в работе|приступаю|продолжаю|working|on it|continuing|"
    r"как дела|как жизнь|how are you|how's it going|привет|hello|hi|да|yes|угу|"
    r"жду|ожидаю|waiting|standing by)\b", re.I)


# ---------------------------------------------------------------- разбор формата
def _parse_ts(v):
    if not isinstance(v, str):
        return None
    try:
        d = datetime.fromisoformat(v.replace("Z", "+00:00"))
    except ValueError:
        return None
    return d if d.tzinfo else d.replace(tzinfo=timezone.utc)


def _block_text(content) -> str:
    if isinstance(content, str):
        return content
    out = []
    if isinstance(content, list):
        for b in content:
            if isinstance(b, str):
                out.append(b)
            elif isinstance(b, dict) and b.get("type") == "text":
                out.append(str(b.get("text", "")))
    return "\n".join(out)


def parse_line(obj: dict, n: int):
    """Единственное место, знающее формат строки журнала.

    Возвращает dict записи или None (строка неизвестного вида).
    Поля: n, kind(user|assistant), ts, text, human(bool), tools[(id,name,input)],
    results[(tool_use_id,is_error,text)], msg_id, usage(dict|None), has_thinking.
    """
    if not isinstance(obj, dict):
        return None
    kind = obj.get("type")
    if kind == "result" and isinstance(obj.get("total_cost_usd"), (int, float)):
        # итог из журнала: только стоимость, токены берутся из assistant-строк
        return {"n": n, "kind": "logcost", "ts": _parse_ts(obj.get("timestamp")), "text": "",
                "human": False, "tools": [], "results": [], "msg_id": None, "usage": None,
                "has_thinking": False, "cost": float(obj["total_cost_usd"])}
    if kind == "cost-state" and isinstance(obj.get("totalCostUSD"), (int, float)):
        return {"n": n, "kind": "coststate", "ts": None, "text": "", "human": False, "tools": [],
                "results": [], "msg_id": None, "usage": None, "has_thinking": False,
                "cost": float(obj["totalCostUSD"])}
    if kind not in ("user", "assistant"):
        return None
    msg = obj.get("message")
    if not isinstance(msg, dict):
        return None
    content = msg.get("content")
    rec = {"n": n, "kind": kind, "ts": _parse_ts(obj.get("timestamp")),
           "text": "", "human": False, "tools": [], "results": [],
           "msg_id": msg.get("id"), "usage": None, "has_thinking": False,
           "model": msg.get("model") if isinstance(msg.get("model"), str) else None}
    texts = []
    if isinstance(content, str):
        texts.append(content)
    elif isinstance(content, list):
        for b in content:
            if isinstance(b, str):
                texts.append(b)
                continue
            if not isinstance(b, dict):
                continue
            t = b.get("type")
            if t == "text":
                texts.append(str(b.get("text", "")))
            elif t == "tool_use":
                rec["tools"].append((b.get("id"), str(b.get("name", "?")),
                                     b.get("input") if isinstance(b.get("input"), dict) else {}))
            elif t == "tool_result":
                rec["results"].append((b.get("tool_use_id"), bool(b.get("is_error")),
                                       _block_text(b.get("content"))))
            elif t == "thinking":
                rec["has_thinking"] = True
    rec["text"] = "\n".join(x for x in texts if x).strip()
    if kind == "user":
        rec["human"] = bool(rec["text"]) and not rec["results"] and not obj.get("isMeta")
    u = msg.get("usage")
    if kind == "assistant" and isinstance(u, dict):
        rec["usage"] = {k: int(u.get(k) or 0) for k in
                        ("input_tokens", "output_tokens",
                         "cache_read_input_tokens", "cache_creation_input_tokens")
                        if isinstance(u.get(k) or 0, (int, float))}
    return rec


def parse_event(ev, n: int):
    """Разбор одного события list_events -> запись (как parse_line) или None.

    Событие: {"created_at":..., "<вид>": {"uuid":..., "internal_anthropic_catchall": {...}}}.
    Нужны виды user, assistant, result; остальные (system, env_manager_log, ...) -> None.
    Для result запись имеет kind="result" и поле "result" с итогами хода.
    """
    if not isinstance(ev, dict):
        return None
    kind = next((k for k in ev if k != "created_at"), None)
    if kind not in ("user", "assistant", "result"):
        return None
    payload = ev.get(kind)
    if not isinstance(payload, dict):
        return None
    cc = payload.get("internal_anthropic_catchall")
    if not isinstance(cc, dict):
        cc = payload
    ts = ev.get("created_at") or cc.get("timestamp")
    if kind == "result":
        mu = cc.get("modelUsage") if isinstance(cc.get("modelUsage"), dict) else {}
        num = lambda v: v if isinstance(v, (int, float)) else 0
        tok = {"output_tokens": 0, "input_tokens": 0,
               "cache_read_input_tokens": 0, "cache_creation_input_tokens": 0}
        for m in mu.values():
            if not isinstance(m, dict):
                continue
            tok["output_tokens"] += int(num(m.get("outputTokens")))
            tok["input_tokens"] += int(num(m.get("inputTokens")))
            tok["cache_read_input_tokens"] += int(num(m.get("cacheReadInputTokens")))
            tok["cache_creation_input_tokens"] += int(num(m.get("cacheCreationInputTokens")))
        if not mu and isinstance(cc.get("usage"), dict):
            u = cc["usage"]
            for k in tok:
                tok[k] = int(num(u.get(k)))
        return {"n": n, "kind": "result", "ts": _parse_ts(ts), "text": "", "human": False,
                "tools": [], "results": [], "msg_id": None, "usage": None, "has_thinking": False,
                "result": {"tokens": tok, "models": sorted(mu),
                           "cost": cc.get("total_cost_usd") if isinstance(cc.get("total_cost_usd"), (int, float)) else None,
                           "duration_ms": cc.get("duration_ms") if isinstance(cc.get("duration_ms"), (int, float)) else None,
                           "num_turns": cc.get("num_turns") if isinstance(cc.get("num_turns"), (int, float)) else None}}
    if not isinstance(cc.get("message"), dict):
        return None
    return parse_line({"type": kind, "timestamp": ts, "message": cc["message"],
                       "isMeta": cc.get("isMeta")}, n)


def _unwrap_pages(doc):
    """list_events-ответ(ы) -> список событий или None, если это не list_events."""
    def events_of(x):
        if isinstance(x, dict) and isinstance(x.get("ccr"), dict):
            x = x["ccr"]
        if isinstance(x, dict) and isinstance(x.get("data"), list):
            return x["data"]
        return None
    ev = events_of(doc)
    if ev is not None:
        return ev
    if isinstance(doc, list) and doc:
        pages = [events_of(x) for x in doc]
        if all(p is not None for p in pages):
            return [e for p in pages for e in p]
        if all(isinstance(x, dict) and "created_at" in x for x in doc):
            return doc          # склеенный список событий
    return None


def _read_events(events):
    recs, seen, total, skipped = [], set(), 0, 0
    for e in events:
        uid = None
        if isinstance(e, dict):
            k = next((k for k in e if k != "created_at"), None)
            if k and isinstance(e.get(k), dict):
                uid = e[k].get("uuid")
        if uid:                       # страницы могли пересечься
            if uid in seen:
                continue
            seen.add(uid)
        total += 1
        r = parse_event(e, total)
        if r is None:
            skipped += 1
        else:
            recs.append(r)
    return recs, total, skipped


def read_journal(path: str):
    """Читает файл -> (records, total, skipped). Формат определяется по содержимому.

    total - число непустых строк (JSONL) или событий (list_events). Устойчив к мусору.
    """
    with open(path, encoding="utf-8", errors="replace") as f:
        text = f.read()
    st = text.lstrip()
    if st[:1] in "[{":
        try:
            events = _unwrap_pages(json.loads(st))
        except json.JSONDecodeError:
            events = None            # несколько JSON-строк подряд -> JSONL
        if events is not None:
            return _read_events(events)
    recs, total, skipped = [], 0, 0
    for line in text.split("\n"):
        line = line.strip()
        if not line:
            continue
        total += 1
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            skipped += 1
            continue
        r = parse_line(obj, total)
        if r is None:
            skipped += 1
        else:
            recs.append(r)
    return recs, total, skipped


# ---------------------------------------------------------------- анализ
def _norm_cmd(name: str, inp: dict) -> str:
    if name == "Bash" and "command" in inp:
        s = str(inp["command"])
    else:
        key = next((k for k in ("command", "file_path", "path", "pattern", "url", "query", "skill")
                    if k in inp), None)
        s = f"{name} {inp[key]}" if key else f"{name} {json.dumps(inp, sort_keys=True, ensure_ascii=False)}"
    s = re.sub(r"\s+", " ", s).strip()
    s = re.sub(r"\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b", "<uuid>", s, flags=re.I)
    return s


def _clip(s: str, n: int = EXAMPLE_LEN) -> str:
    s = re.sub(r"\s+", " ", s).strip()
    return s if len(s) <= n else s[: n - 1] + "…"


def _is_empty_msg(text: str) -> bool:
    t = text.strip()
    return 0 < len(t) < SHORT_LEN and bool(EMPTY_RE.match(t.lower().lstrip("-*•> ")))


def _addr_re(roles):
    names = "|".join(re.escape(r) for r in sorted(roles, key=len, reverse=True))
    return re.compile(rf"^\s*(?:(?P<a>{names})\s*:|(?:@|→\s*|->\s*)(?P<b>{names})\b)", re.I | re.M)


def analyze(role: str, recs, total, skipped, roles, since=None, until=None, prices=None):
    if since or until:
        recs = [r for r in recs if r["ts"] and (not since or r["ts"] >= since)
                and (not until or r["ts"] <= until)]
    ref = lambda n: f"{role}#{n}"
    res = {"роль": role, "строк": total, "пропущено": skipped, "записей": len(recs)}

    # токены: один раз на message.id (максимум по полям среди строк сообщения)
    by_id, model_of = {}, {}
    for r in recs:
        if r["kind"] == "assistant" and r["usage"] is not None:
            key = r["msg_id"] or f"_line{r['n']}"
            cur = by_id.setdefault(key, defaultdict(int))
            for k, v in r["usage"].items():
                cur[k] = max(cur[k], v)
            if r.get("model") and not r["model"].startswith("<"):
                model_of[key] = r["model"]
    tot = defaultdict(int)
    tok_by_model = defaultdict(lambda: defaultdict(int))     # название модели -> токены
    for key, u in by_id.items():
        mname = model_prices(model_of.get(key))
        for k, v in u.items():
            tot[k] += v
            tok_by_model[mname][k] += v
    # list_events: если есть событие result - итоги берём из него (usage в assistant промежуточный)
    rres = [r["result"] for r in recs if r["kind"] == "result"]
    if rres:
        tot = defaultdict(int)
        for x in rres:
            for k, v in x["tokens"].items():
                tot[k] += v
        known = lambda key: [x[key] for x in rres if x[key] is not None]
        res["итог_сессии"] = {
            "результатов": len(rres), "модели": sorted({m for x in rres for m in x["models"]}),
            "стоимость_usd": round(sum(known("cost")), 6) if known("cost") else None,
            "длительность_мс": int(sum(known("duration_ms"))) if known("duration_ms") else None,
            "ходов": int(sum(known("num_turns"))) if known("num_turns") else None}
    else:
        res["итог_сессии"] = None
    res["токены"] = {"вывод": tot["output_tokens"], "вход_без_кэша": tot["input_tokens"],
                     "вход_кэш_чтение": tot["cache_read_input_tokens"],
                     "вход_кэш_запись": tot["cache_creation_input_tokens"]}

    # стоимость: итог из журнала (result), если есть; иначе оценка по ценам модели за 1 млн токенов
    pr = tuple(prices) if prices else None
    logged = [r["cost"] for r in recs if r["kind"] == "logcost"]
    state = [r["cost"] for r in recs if r["kind"] == "coststate"]
    it = res["итог_сессии"]
    est_names = []
    if rres and not by_id:           # list_events: токены из result; модель - из modelUsage
        mods = sorted({m for x in rres for m in x["models"]})
        tok_by_model = {model_prices(mods[0] if mods else None): tot}
    if pr:
        cost = (tot["input_tokens"] * pr[0] + tot["output_tokens"] * pr[1]
                + tot["cache_read_input_tokens"] * pr[2]
                + tot["cache_creation_input_tokens"] * pr[3]) / 1e6
        est_names = ["заданным через --prices (" + ",".join(f"{x:g}" for x in pr) + ")"]
    else:
        cost = 0.0
        for (nm, mp, note), t in tok_by_model.items():
            if not any(t.values()):
                continue
            cost += (t["input_tokens"] * mp[0] + t["output_tokens"] * mp[1]
                     + t["cache_read_input_tokens"] * mp[2]
                     + t["cache_creation_input_tokens"] * mp[3]) / 1e6
            est_names.append(nm + (f" [{note}]" if note else ""))
        if not est_names:
            est_names = [DEFAULT_PRICES_NAME]
    estimate = cost
    if logged:
        cost, src = sum(logged), "из журнала"
    elif it and it["стоимость_usd"] is not None:
        cost, src = it["стоимость_usd"], "из журнала"
    else:
        src = "оценка"
    res["стоимость"] = {"usd": round(cost, 6), "источник": src}
    if src == "оценка":
        res["стоимость"]["цены"] = ", ".join(est_names)
    if state:                        # cost-state: накопительный итог сессии, берём последний
        j = state[-1]
        sc = res["стоимость"]
        sc["по_журналу"] = round(j, 6)
        sc["оценка"] = round(estimate, 6)
        if j > 0 and abs(estimate - j) / j > COST_WARN:
            sc["предупреждение"] = (f"оценка ${estimate:.2f} и журнал ${j:.2f} расходятся на "
                                    f"{abs(estimate - j) / j * 100:.0f}% (>{int(COST_WARN * 100)}%): "
                                    f"проверь цены модели или --prices; cost-state включает и "
                                    f"субагентов, чьих сообщений в этом журнале нет")

    res["ходы_пользователя"] = sum(1 for r in recs if r["human"])
    ids = {r["msg_id"] or f"_line{r['n']}" for r in recs if r["kind"] == "assistant"}
    res["ответы_модели"] = len(ids)

    # инструменты и ошибки
    names, tool_by_id, calls = Counter(), {}, defaultdict(list)
    for r in recs:
        for tid, name, inp in r["tools"]:
            names[name] += 1
            tool_by_id[tid] = name
            calls[_norm_cmd(name, inp)].append(r["n"])
    res["инструменты"] = names.most_common(5)
    edited = Counter()
    for r in recs:
        for _tid, name, inp in r["tools"]:
            if name in ("Write", "Edit", "NotebookEdit"):
                path = inp.get("file_path") or inp.get("notebook_path") or inp.get("path")
                if isinstance(path, str) and path:
                    edited[path] += 1
    res["изменённые_файлы"] = edited.most_common(8)
    res["вызовов_инструментов"] = sum(names.values())
    errs = []
    for r in recs:
        for tid, is_err, txt in r["results"]:
            if is_err:
                errs.append({"ref": ref(r["n"]), "инструмент": tool_by_id.get(tid, "?"),
                             "текст": _clip(txt, 70)})
    res["ошибки_инструментов"] = {"всего": len(errs), "примеры": errs[:3]}

    # время
    stamped = [r for r in recs if r["ts"]]
    active, gaps = 0.0, []
    for a, b in zip(stamped, stamped[1:]):
        g = (b["ts"] - a["ts"]).total_seconds()
        if g < 0:
            continue
        if g <= IDLE_GAP:
            active += g
        gaps.append((g, b["n"]))
    gaps.sort(reverse=True)
    res["время"] = {
        "начало": stamped[0]["ts"].isoformat() if stamped else None,
        "конец": stamped[-1]["ts"].isoformat() if stamped else None,
        "активно_сек": int(active),
        "паузы": [{"сек": int(g), "ref": ref(n)} for g, n in gaps[:3]],
    }

    # строки метрик + накопленные выходные токены
    out_by_id = {k: v["output_tokens"] for k, v in by_id.items()}
    cum, seen, metrics = 0, set(), []
    for r in recs:
        if r["kind"] == "assistant":
            key = r["msg_id"] or f"_line{r['n']}"
            if key in out_by_id and key not in seen:
                seen.add(key)
                cum += out_by_id[key]
            for line in r["text"].splitlines():
                if METRIC_RE.match(line):
                    metrics.append({"ref": ref(r["n"]), "время": r["ts"].isoformat() if r["ts"] else None,
                                    "токенов_вывода_накоплено": cum, "строка": line.strip()})
    res["метрики"] = metrics

    # пустые сообщения
    replies = [r for r in recs if r["text"] and (r["human"] or r["kind"] == "assistant")]
    empties = [r for r in replies if _is_empty_msg(r["text"])]
    res["пустые"] = {"всего_реплик": len(replies), "пустых": len(empties),
                     "доля": round(len(empties) / len(replies), 2) if replies else 0.0,
                     "примеры": [{"ref": ref(r["n"]), "текст": _clip(r["text"], 50)} for r in empties[:3]]}

    # повторы
    reps = [(c, ns) for c, ns in calls.items() if len(ns) >= 3]
    reps.sort(key=lambda x: -len(x[1]))
    res["повторы"] = [{"раз": len(ns), "команда": _clip(c, 100), "refs": [ref(n) for n in ns[:3]]}
                      for c, ns in reps[:5]]

    # адресаты: ответ модели роли R со строкой «X:» = R->X; реплика с «X:» в журнале R = X->R
    addr = Counter()
    if len(roles) > 1:
        rx = _addr_re(roles)
        low = {x.lower(): x for x in roles}
        for r in replies:
            for m in rx.finditer(r["text"]):
                other = low.get((m.group("a") or m.group("b")).lower())
                if not other or other == role:
                    continue
                if r["kind"] == "assistant":
                    addr[(role, other)] += 1
                else:
                    addr[(other, role)] += 1
    res["адресаты"] = [{"от": a, "кому": b, "раз": c} for (a, b), c in addr.items()]
    res["однообразная_работа"] = RW.find_repeats(recs, model_prices, pr)
    return res


# ---------------------------------------------------------------- вывод
def _dur(sec: int) -> str:
    h, rem = divmod(int(sec), 3600)
    m, s = divmod(rem, 60)
    return f"{h}ч {m:02d}м" if h else (f"{m}м {s:02d}с" if m else f"{s}с")


def render_text(results, prices_name=DEFAULT_PRICES_NAME) -> str:
    L = []
    for r in results:
        tk = r["токены"]
        L.append(f"== {r['роль']}: {r['записей']} записей из {r['строк']} строк/событий (пропущено неизвестных: {r['пропущено']}) ==")
        L.append(f"ходы пользователя (люди/другие агенты): {r['ходы_пользователя']}; ответов модели: {r['ответы_модели']}")
        L.append(f"токены: вывод {tk['вывод']}; вход без кэша {tk['вход_без_кэша']}; "
                 f"вход через кэш: чтение {tk['вход_кэш_чтение']}, запись {tk['вход_кэш_запись']}")
        it = r.get("итог_сессии")
        if it:
            bits = []
            if it["модели"]:
                bits.append("модель " + ", ".join(it["модели"]))
            if it["стоимость_usd"] is not None:
                bits.append(f"стоимость ${it['стоимость_usd']}")
            if it["длительность_мс"] is not None:
                bits.append(f"длительность {_dur(it['длительность_мс'] // 1000)}")
            if it["ходов"] is not None:
                bits.append(f"ходов модели {it['ходов']}")
            L.append("итог сессии (из события result, токены выше - оттуда же): " + "; ".join(bits))
        c = r["стоимость"]
        price_name = c.get("цены") or prices_name
        L.append(f"стоимость: ${c['usd']:.2f} (" + ("из журнала" if c["источник"] == "из журнала"
                 else f"оценка по ценам {price_name}") + ")")
        if "по_журналу" in c:
            L.append(f"  по журналу (cost-state): ${c['по_журналу']:.2f}; оценка по токенам: ${c['оценка']:.2f}")
        if c.get("предупреждение"):
            L.append("  ВНИМАНИЕ: " + c["предупреждение"])
        tools = ", ".join(f"{n} {c}" for n, c in r["инструменты"]) or "нет"
        L.append(f"инструменты (всего {r['вызовов_инструментов']}, топ-5): {tools}")
        ed = ", ".join(f"{p} ({c})" for p, c in r.get("изменённые_файлы", [])) or "нет"
        L.append(f"изменённые файлы: {ed}")
        e = r["ошибки_инструментов"]
        ex = "; ".join(f"{x['ref']} {x['инструмент']}" for x in e["примеры"])
        L.append(f"ошибки инструментов: {e['всего']}" + (f" (напр. {ex})" if ex else ""))
        tm = r["время"]
        pz = ", ".join(f"{_dur(p['сек'])} перед {p['ref']}" for p in tm["паузы"]) or "нет"
        L.append(f"активная работа: {_dur(tm['активно_сек'])} (паузы >{IDLE_GAP // 60} мин не считаются); "
                 f"длиннейшие паузы: {pz}")
        p = r["пустые"]
        pex = ", ".join(f"{x['ref']} «{x['текст']}»" for x in p["примеры"])
        L.append(f"пустые реплики: {p['пустых']} из {p['всего_реплик']} ({int(p['доля'] * 100)}%)"
                 + (f"; напр. {pex}" if pex else ""))
        if r["повторы"]:
            L.append("повторы команд (3+ раз, кандидаты в скрипт):")
            for x in r["повторы"]:
                L.append(f"  {x['раз']}x {x['команда']} ({', '.join(x['refs'])}...)")
        else:
            L.append("повторы команд (3+ раз): нет")
        rw = r.get("однообразная_работа")
        if rw:
            L.append(RW.render_role_line(r["роль"], rw))
            L.extend(RW.render_role_extra(r["роль"], rw))
            L.extend(RW.render_role_details(r["роль"], rw))
        m = r["метрики"]
        if m:
            L.append(f"строки метрик: {len(m)} (ряд: ссылка, накопленный вывод токенов, строка)")
            show = m if len(m) <= 8 else m[:4] + m[-4:]
            for i, x in enumerate(show):
                if len(m) > 8 and i == 4:
                    L.append(f"  ... (ещё {len(m) - 8})")
                L.append(f"  {x['ref']} [{x['токенов_вывода_накоплено']} ток.] {_clip(x['строка'], 110)}")
        else:
            L.append("строки метрик: нет")
        L.append("")
    L.extend(RW.render_candidates(results))
    L.append("")
    addr = [a for r in results for a in r["адресаты"]]
    L.append(f"ИТОГО стоимость ансамбля: ${sum(r['стоимость']['usd'] for r in results):.2f}")
    if addr:
        L.append("")
        agg = Counter()
        for a in addr:
            agg[(a["от"], a["кому"])] += a["раз"]
        L.append("кто кому писал (по строкам вида «роль:», «@роль», «→ роль»):")
        for (a, b), c in agg.most_common(12):
            L.append(f"  {a} -> {b}: {c}")
    return "\n".join(L).rstrip() + "\n"


def show_record(role: str, n: int, path: str) -> str:
    recs, total, _ = read_journal(path)
    for r in recs:
        if r["n"] == n:
            txt = r["text"]
            if len(txt) > SHOW_LIMIT:
                txt = txt[:SHOW_LIMIT] + f"… [обрезано, всего {len(r['text'])} симв.]"
            author = ("человек/агент" if r["human"] else
                      "результат инструмента" if r["kind"] == "user" else "модель")
            tools = ", ".join(name for _, name, _ in r["tools"]) or "нет"
            extra = ""
            if r["results"]:
                bad = sum(1 for x in r["results"] if x[1])
                extra = f"\nрезультатов инструментов: {len(r['results'])} (ошибок: {bad})"
                if not txt:
                    txt = "\n".join(_clip(x[2], 400) for x in r["results"][:3])
            return (f"{role}#{n} | время: {r['ts'].isoformat() if r['ts'] else 'нет'} | автор: {author}\n"
                    f"инструменты: {tools}{extra}\n---\n{txt or '(текста нет)'}\n")
    return f"{role}#{n}: записи нет (в журнале {total} непустых строк; не все строки - сообщения)\n"


def _split_role_path(arg: str):
    if "=" in arg:
        role, path = arg.split("=", 1)
        if role and not re.search(r"[\\/:]", role):
            return role, path
    return None, arg


def _iso(v):
    d = _parse_ts(v)
    if v and d is None:
        raise SystemExit(f"неверная дата ISO: {v}")
    return d


def main(argv=None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("summary")
    s.add_argument("items", nargs="+", help="роль=путь")
    s.add_argument("--since")
    s.add_argument("--until")
    s.add_argument("--json", action="store_true")
    s.add_argument("--prices", help="цены за 1 млн токенов: вход,вывод,чтение_кэша,запись_кэша "
                   "(по умолчанию - по модели из журнала, см. MODEL_PRICES; неизвестная - Haiku 4.5: 1,5,0.10,1.25)")
    sh = sub.add_parser("show")
    sh.add_argument("ref", help="роль#N")
    sh.add_argument("target", help="путь или роль=путь")
    a = ap.parse_args(argv)

    if a.cmd == "summary":
        pairs = []
        for it in a.items:
            role, path = _split_role_path(it)
            if not role:
                raise SystemExit(f"ожидалось роль=путь, получено: {it}")
            pairs.append((role, path))
        roles = [r for r, _ in pairs]
        since, until = _iso(a.since), _iso(a.until)
        prices, pname = None, DEFAULT_PRICES_NAME
        if a.prices:
            try:
                prices = tuple(float(x) for x in a.prices.split(","))
            except ValueError:
                prices = ()
            if len(prices) != 4:
                raise SystemExit("--prices: ожидалось 4 числа: вход,вывод,чтение_кэша,запись_кэша")
            pname = "заданным через --prices (" + a.prices + ")"
        results = []
        for role, path in pairs:
            recs, total, skipped = read_journal(path)
            results.append(analyze(role, recs, total, skipped, roles, since, until, prices))
        if a.json:
            tc = round(sum(r["стоимость"]["usd"] for r in results), 6)
            print(json.dumps({"роли": results, "total_cost_usd": tc}, ensure_ascii=False, indent=2))
        else:
            print(render_text(results, pname), end="")
        return 0

    m = re.fullmatch(r"(.*)#(\d+)", a.ref)
    if not m:
        raise SystemExit("ожидалось роль#N, например producer#42")
    role, n = m.group(1), int(m.group(2))
    r2, path = _split_role_path(a.target)
    print(show_record(role or r2 or "?", n, path), end="")
    return 0


if __name__ == "__main__":
    sys.exit(main())
