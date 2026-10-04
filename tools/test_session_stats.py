import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import session_stats as S  # noqa: E402


def U(ts, content, **kw):
    return {"type": "user", "timestamp": ts, "message": {"role": "user", "content": content}, **kw}


def A(ts, blocks, mid, usage=None):
    m = {"role": "assistant", "id": mid, "content": blocks}
    if usage:
        m["usage"] = usage
    return {"type": "assistant", "timestamp": ts, "message": m}


def tu(i, cmd, name="Bash"):
    return {"type": "tool_use", "id": i, "name": name, "input": {"command": cmd}}


def tr(i, text, err=False):
    return {"type": "tool_result", "tool_use_id": i, "content": text, "is_error": err}


def write(tmp_path, name, rows, junk=True):
    p = tmp_path / name
    lines = [json.dumps(r, ensure_ascii=False) for r in rows]
    if junk:
        lines.insert(1, "не json")
        lines.insert(2, json.dumps({"type": "queue-operation"}))
        lines.insert(3, "")
    p.write_text("\n".join(lines), encoding="utf-8")
    return str(p)


def make_prod(tmp_path):
    u1 = {"input_tokens": 10, "output_tokens": 5, "cache_read_input_tokens": 100, "cache_creation_input_tokens": 20}
    u2 = {"input_tokens": 10, "output_tokens": 50, "cache_read_input_tokens": 100, "cache_creation_input_tokens": 20}
    rows = [
        U("2026-01-01T10:00:00Z", "Сделай задачу по плану, подробно и аккуратно, пожалуйста, без спешки"),
        A("2026-01-01T10:00:05Z", [{"type": "text", "text": "метрика: файлов=3 тестов=10\nхореограф: проверь"}], "m1", u1),
        A("2026-01-01T10:00:06Z", [tu("t1", "ls  -la")], "m1", u2),  # тот же id
        U("2026-01-01T10:00:07Z", [tr("t1", "boom", err=True)]),
        A("2026-01-01T10:00:08Z", [tu("t2", "ls -la")], "m2", u1),
        U("2026-01-01T10:00:09Z", [tr("t2", "ok")]),
        A("2026-01-01T10:00:10Z", [tu("t3", "ls -la")], "m3", u1),
        U("2026-01-01T10:00:11Z", [tr("t3", "ok")]),
        A("2026-01-01T10:20:00Z", [{"type": "text", "text": "отрезок 2: готово 5 из 8"}], "m4", u1),
        U("2026-01-01T10:20:05Z", "ок"),
        A("2026-01-01T10:20:10Z", [{"type": "text", "text": "Работаю"}], "m5", u1),
    ]
    return write(tmp_path, "prod.jsonl", rows)


def analyze_prod(tmp_path, **kw):
    recs, t, s = S.read_journal(make_prod(tmp_path))
    return S.analyze("p", recs, t, s, ["p"], **kw)


def test_usage_counted_once_per_message_id(tmp_path):
    recs, total, skipped = S.read_journal(make_prod(tmp_path))
    assert skipped == 2 and total == 13
    r = S.analyze("продюсер", recs, total, skipped, ["продюсер"])
    # m1 один раз (максимум по строкам: 50), m2..m5 по 5
    assert r["токены"]["вывод"] == 50 + 5 * 4
    assert r["токены"]["вход_без_кэша"] == 50
    assert r["токены"]["вход_кэш_чтение"] == 500
    assert r["ответы_модели"] == 5
    assert r["ходы_пользователя"] == 2


def test_tool_errors_and_tools(tmp_path):
    r = analyze_prod(tmp_path)
    assert r["ошибки_инструментов"]["всего"] == 1
    assert r["ошибки_инструментов"]["примеры"][0]["инструмент"] == "Bash"
    assert r["инструменты"][0] == ("Bash", 3)


def test_metrics_series_with_cumulative_tokens(tmp_path):
    m = analyze_prod(tmp_path)["метрики"]
    assert [x["строка"] for x in m] == ["метрика: файлов=3 тестов=10", "отрезок 2: готово 5 из 8"]
    assert m[0]["токенов_вывода_накоплено"] == 50
    assert m[1]["токенов_вывода_накоплено"] == 50 + 5 + 5 + 5
    assert m[0]["ref"].startswith("p#")


def test_empty_messages(tmp_path):
    e = analyze_prod(tmp_path)["пустые"]
    assert e["пустых"] == 2  # «ок» и «Работаю»
    assert e["всего_реплик"] == 5
    assert not S._is_empty_msg("Принято, но сначала нужно разобрать архитектуру и сделать длинный план работ")


def test_repeats_normalized(tmp_path):
    rep = analyze_prod(tmp_path)["повторы"]
    assert len(rep) == 1 and rep[0]["раз"] == 3 and rep[0]["команда"] == "ls -la"


def test_time_and_pauses(tmp_path):
    tm = analyze_prod(tmp_path)["время"]
    assert tm["паузы"][0]["сек"] == 1189  # 10:00:11 -> 10:20:00
    assert tm["активно_сек"] < 60


def test_since_filter(tmp_path):
    r = analyze_prod(tmp_path, since=S._parse_ts("2026-01-01T10:10:00Z"))
    assert r["ответы_модели"] == 2


def test_address_matrix(tmp_path):
    a = write(tmp_path, "a.jsonl", [U("2026-01-01T10:00:00Z", "x"),
              A("2026-01-01T10:00:01Z", [{"type": "text", "text": "хореограф: сделай\n→ хореограф ещё"}], "1")], junk=False)
    b = write(tmp_path, "b.jsonl", [U("2026-01-01T10:00:00Z", "продюсер: привет, смотри"),
              A("2026-01-01T10:00:01Z", [{"type": "text", "text": "@продюсер принято"}], "1")], junk=False)
    roles = ["продюсер", "хореограф"]
    ra = S.analyze("продюсер", *S.read_journal(a), roles)
    rb = S.analyze("хореограф", *S.read_journal(b), roles)
    assert {"от": "продюсер", "кому": "хореограф", "раз": 2} in ra["адресаты"]
    assert {"от": "продюсер", "кому": "хореограф", "раз": 1} in rb["адресаты"] or \
        {"от": "хореограф", "кому": "продюсер", "раз": 1} in rb["адресаты"]


def test_show_and_cli(tmp_path, capsys):
    p = make_prod(tmp_path)
    assert S.main(["show", "продюсер#5", p]) == 0
    out = capsys.readouterr().out
    assert out.startswith("продюсер#5 |") and "время:" in out
    S.main(["show", "продюсер#1", f"продюсер={p}"])
    assert "Сделай задачу" in capsys.readouterr().out
    long = write(tmp_path, "l.jsonl", [U("2026-01-01T10:00:00Z", "я" * 5000)], junk=False)
    S.main(["show", "x#1", long])
    assert "обрезано" in capsys.readouterr().out
    S.main(["show", "x#99", long])
    assert "записи нет" in capsys.readouterr().out


def test_summary_text_and_json(tmp_path, capsys):
    p = make_prod(tmp_path)
    assert S.main(["summary", f"продюсер={p}"]) == 0
    out = capsys.readouterr().out
    assert "ошибки инструментов: 1" in out and len(out.splitlines()) < 30
    assert S.main(["summary", f"продюсер={p}", "--json"]) == 0
    data = json.loads(capsys.readouterr().out)
    assert data["роли"][0]["токены"]["вывод"] == 70
    assert data["total_cost_usd"] == data["роли"][0]["стоимость"]["usd"]


# ---------------------------------------------------------------- формат list_events
def EV(ts, kind, cc, uid):
    return {"created_at": ts, kind: {"uuid": uid, "internal_anthropic_catchall": cc}}


def EA(ts, blocks, mid, uid, usage=None):
    m = {"role": "assistant", "id": mid, "content": blocks}
    if usage:
        m["usage"] = usage
    return EV(ts, "assistant", {"message": m}, uid)


def EU(ts, content, uid):
    return EV(ts, "user", {"message": {"role": "user", "content": content}}, uid)


def make_events(with_result=True):
    us = {"input_tokens": 10, "output_tokens": 2, "cache_read_input_tokens": 100, "cache_creation_input_tokens": 20}
    ev = [
        {"created_at": "2026-01-01T10:00:00Z", "control_request": {"request_id": "x"}},
        EU("2026-01-01T10:00:01Z", "Стартовое задание для исполнителя, достаточно длинное для проверки", "u1"),
        {"created_at": "2026-01-01T10:00:02Z", "env_manager_log": {"uuid": "e1", "internal_anthropic_catchall": {"data": 1}}},
        EA("2026-01-01T10:00:03Z", [{"type": "thinking", "thinking": "", "signature": "s"}], "m1", "a1", us),
        EA("2026-01-01T10:00:04Z", [{"type": "text", "text": "метрика: файлов=1\nхореограф: смотри"}], "m1", "a2", us),
        EA("2026-01-01T10:00:05Z", [tu("t1", "ls -la")], "m1", "a3", us),
        EU("2026-01-01T10:00:06Z", [tr("t1", "boom", err=True)], "u2"),
        EA("2026-01-01T10:00:07Z", [tu("t2", "ls -la")], "m2", "a4", us),
        EU("2026-01-01T10:00:08Z", [tr("t2", "ok")], "u3"),
        EA("2026-01-01T10:00:09Z", [tu("t3", "ls -la")], "m3", "a5", us),
        EU("2026-01-01T10:00:10Z", [tr("t3", "ok")], "u4"),
        EA("2026-01-01T10:20:00Z", [{"type": "text", "text": "Работаю"}], "m4", "a6", us),
    ]
    if with_result:
        ev.append(EV("2026-01-01T10:20:01Z", "result", {
            "modelUsage": {"claude-x": {"inputTokens": 40, "outputTokens": 900, "cacheReadInputTokens": 5000,
                                        "cacheCreationInputTokens": 70, "costUSD": 0.5}},
            "total_cost_usd": 0.5, "duration_ms": 61000, "num_turns": 4}, "r1"))
    return ev


def write_json(tmp_path, name, doc):
    p = tmp_path / name
    p.write_text(json.dumps(doc, ensure_ascii=False), encoding="utf-8")
    return str(p)


def test_list_events_format_detected_and_numbered(tmp_path):
    p = write_json(tmp_path, "e.json", {"data": make_events(), "first_id": "a", "last_id": "b"})
    recs, total, skipped = S.read_journal(p)
    assert total == 13 and skipped == 2          # control_request, env_manager_log
    assert [r["n"] for r in recs][:2] == [2, 4]  # порядковый номер события
    r = S.analyze("исп", recs, total, skipped, ["исп"])
    assert r["ходы_пользователя"] == 1 and r["ответы_модели"] == 4
    assert r["ошибки_инструментов"]["всего"] == 1
    assert r["повторы"][0]["раз"] == 3 and r["повторы"][0]["команда"] == "ls -la"
    assert r["пустые"]["пустых"] == 1
    assert r["метрики"][0]["ref"] == "исп#5"
    assert r["время"]["паузы"][0]["сек"] == 1190
    assert r["время"]["паузы"][0]["ref"] == "исп#12"


def test_list_events_tokens_from_result(tmp_path):
    p = write_json(tmp_path, "e.json", {"ccr": {"data": make_events()}})
    r = S.analyze("исп", *S.read_journal(p), ["исп"])
    assert r["токены"]["вывод"] == 900 and r["токены"]["вход_кэш_чтение"] == 5000
    it = r["итог_сессии"]
    assert it["стоимость_usd"] == 0.5 and it["длительность_мс"] == 61000 and it["ходов"] == 4
    assert "итог сессии" in S.render_text([r])


def test_list_events_tokens_without_result_unique_message_id(tmp_path):
    p = write_json(tmp_path, "e.json", {"data": make_events(with_result=False)})
    r = S.analyze("исп", *S.read_journal(p), ["исп"])
    assert r["итог_сессии"] is None
    assert r["токены"]["вывод"] == 2 * 4          # 4 message.id, не 6 событий
    assert r["токены"]["вход_кэш_чтение"] == 400
    assert "итог сессии" not in S.render_text([r])


def test_list_events_pages_and_show(tmp_path, capsys):
    ev = make_events()
    pages = [{"data": ev[:5]}, {"data": ev[4:]}]   # страницы пересекаются
    p = write_json(tmp_path, "pages.json", pages)
    recs, total, _ = S.read_journal(p)
    assert total == 13
    merged = write_json(tmp_path, "flat.json", ev)
    assert S.read_journal(merged)[1] == 13
    assert S.main(["show", "исп#2", p]) == 0
    assert "Стартовое задание" in capsys.readouterr().out
    assert S.main(["summary", f"исп={p}", "--json"]) == 0
    assert json.loads(capsys.readouterr().out)["роли"][0]["итог_сессии"]["ходов"] == 4


def test_edited_files_line(tmp_path):
    def edit(i, name, path):
        return {"type": "tool_use", "id": i, "name": name, "input": {"file_path": path}}
    rows = [U("2026-01-01T00:00:00Z", "старт"),
            A("2026-01-01T00:00:05Z", [edit("1", "Write", "/x/a.md"), edit("2", "Edit", "/x/a.md"),
                                       edit("3", "Edit", "/x/b.md"), tu("4", "ls")], "m1")]
    p = write(tmp_path, "r.jsonl", rows)
    recs, total, skipped = S.read_journal(str(p))
    res = S.analyze("r", recs, total, skipped, ["r"])
    assert res["изменённые_файлы"] == [("/x/a.md", 2), ("/x/b.md", 1)]
    assert "изменённые файлы: /x/a.md (2), /x/b.md (1)" in S.render_text([res])


def test_cost_estimate_line_total_and_prices_flag(tmp_path, capsys):
    p = make_prod(tmp_path)
    # токены: вывод 70, вход 50, чтение кэша 500, запись кэша - см. analyze
    r = S.analyze("p", *S.read_journal(p), ["p"])
    tk = r["токены"]
    exp = (tk["вход_без_кэша"] * 1 + tk["вывод"] * 5 + tk["вход_кэш_чтение"] * 0.10
           + tk["вход_кэш_запись"] * 1.25) / 1e6
    assert abs(r["стоимость"]["usd"] - exp) < 1e-9 and r["стоимость"]["источник"] == "оценка"
    assert S.main(["summary", f"продюсер={p}"]) == 0
    out = capsys.readouterr().out
    assert "стоимость: $0.00 (оценка по ценам Haiku 4.5)" in out
    assert "ИТОГО стоимость ансамбля: $0.00" in out
    assert S.main(["summary", f"продюсер={p}", "--json", "--prices", "1000000,0,0,0"]) == 0
    data = json.loads(capsys.readouterr().out)
    assert abs(data["total_cost_usd"] - 50) < 1e-9


def test_cost_from_log_result_line(tmp_path):
    rows = [json.loads(x) for x in open(make_prod(tmp_path), encoding="utf-8") if x.strip().startswith("{")]
    rows.append({"type": "result", "total_cost_usd": 1.5})
    p = write(tmp_path, "withcost.jsonl", rows, junk=False)
    r = S.analyze("p", *S.read_journal(p), ["p"])
    assert r["стоимость"] == {"usd": 1.5, "источник": "из журнала"}
    assert "стоимость: $1.50 (из журнала)" in S.render_text([r])


# ---------------------------------------------------------------- цены по модели, cost-state
def model_journal(tmp_path, model, name="m.jsonl", extra=(), usage=None):
    u = usage or {"input_tokens": 1_000_000, "output_tokens": 1_000_000,
                  "cache_read_input_tokens": 1_000_000, "cache_creation_input_tokens": 1_000_000}
    a = A("2026-01-01T10:00:05Z", [{"type": "text", "text": "ответ"}], "m1", u)
    if model:
        a["message"]["model"] = model
    return write(tmp_path, name, [U("2026-01-01T10:00:00Z", "задание достаточно длинное для проверки"), a, *extra], junk=False)


def cost_of(path, **kw):
    recs, t, s = S.read_journal(path)
    return S.analyze("p", recs, t, s, ["p"], **kw)["стоимость"]


def test_price_table_by_message_model(tmp_path):
    # на 1 млн токенов каждого вида: вход + вывод + чтение кэша + запись кэша
    assert cost_of(model_journal(tmp_path, "claude-haiku-4-5-20251001"))["usd"] == 1 + 5 + 0.10 + 1.25
    assert cost_of(model_journal(tmp_path, "claude-opus-5-5", "o.jsonl"))["usd"] == 4 + 20 + 0.2 + 8
    assert cost_of(model_journal(tmp_path, "claude-sonnet-5-5", "s.jsonl"))["usd"] == 2 + 10 + 0.2 + 2.5
    c = cost_of(model_journal(tmp_path, "claude-opus-5-5", "o2.jsonl"))
    assert "Opus 5.5" in c["цены"] and "допущение" in c["цены"]
    # без модели и неизвестная модель - Haiku 4.5 (поведение журналов прогонов)
    assert cost_of(model_journal(tmp_path, None, "n.jsonl"))["usd"] == 7.35
    assert "нет цены для claude-fable-9" in cost_of(model_journal(tmp_path, "claude-fable-9", "f.jsonl"))["цены"]


def test_price_table_mixed_models_and_prices_flag(tmp_path):
    u = {"input_tokens": 1_000_000, "output_tokens": 0, "cache_read_input_tokens": 0, "cache_creation_input_tokens": 0}
    b = A("2026-01-01T10:00:06Z", [{"type": "text", "text": "второй"}], "m2", u)
    b["message"]["model"] = "claude-opus-5-5"
    p = model_journal(tmp_path, "claude-haiku-4-5", "mix.jsonl", extra=[b], usage=u)
    assert cost_of(p)["usd"] == 1 + 4                         # Haiku 1 + Opus 4 за 1 млн входа
    assert cost_of(p, prices=(10, 0, 0, 0))["usd"] == 20       # --prices перекрывает таблицу


def test_prices_flag_still_overrides_cli(tmp_path, capsys):
    p = model_journal(tmp_path, "claude-opus-5-5")
    assert S.main(["summary", f"p={p}", "--json", "--prices", "1,1,1,1"]) == 0
    assert json.loads(capsys.readouterr().out)["total_cost_usd"] == 4


def test_cost_state_shown_and_warning(tmp_path):
    cs = {"type": "cost-state", "sessionId": "s", "totalCostUSD": 5.0}
    cs2 = {"type": "cost-state", "sessionId": "s", "totalCostUSD": 100.0}
    p = model_journal(tmp_path, "claude-opus-5-5", extra=[cs, cs2])     # оценка 32.2, журнал 100 (последний)
    c = cost_of(p)
    assert c["по_журналу"] == 100.0 and c["usd"] == 32.2 and "предупреждение" in c
    recs, t, s = S.read_journal(p)
    out = S.render_text([S.analyze("p", recs, t, s, ["p"])])
    assert "по журналу (cost-state): $100.00" in out and "ВНИМАНИЕ" in out
    # расхождение в пределах 25% - без предупреждения
    ok = model_journal(tmp_path, "claude-opus-5-5", "ok.jsonl",
                       extra=[{"type": "cost-state", "sessionId": "s", "totalCostUSD": 30.0}])
    c2 = cost_of(ok)
    assert c2["по_журналу"] == 30.0 and "предупреждение" not in c2



def test_background_tasks_hanging_and_done(tmp_path):
    rows = [
        A("2026-09-21T10:00:00Z", [tu("t1", "pytest -q"), tu("t2", "long gate")], "m1"),
        U("2026-09-21T10:00:01Z", [tr("t1", "Command running in background with ID: b1"),
                                   tr("t2", "Command running in background with ID: b2")]),
        U("2026-09-21T10:30:00Z", "<task-notification>\n<task-id>b1</task-id>\n<tool-use-id>t1</tool-use-id>\n"
                                  "<status>failed</status>\n</task-notification>"),
        A("2026-09-21T12:00:00Z", [{"type": "text", "text": "жду"}], "m2"),
    ]
    p = write(tmp_path, "bg.jsonl", rows, junk=False)
    out = S.read_journal(p)
    recs = out[0] if isinstance(out, tuple) else out
    bg = S.background_tasks(recs, lambda n: f"x#{n}")
    assert bg["запущено"] == 2
    assert bg["завершено"] == {"failed": 1}
    assert len(bg["висят"]) == 1 and bg["висят"][0]["сек"] == 7200
    assert "long gate" in bg["висят"][0]["что"]
