import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import repeat_work as RW  # noqa: E402
import session_stats as S  # noqa: E402

U1 = {"input_tokens": 10, "output_tokens": 100, "cache_read_input_tokens": 1000, "cache_creation_input_tokens": 0}


def mk(tmp_path, steps, name="j.jsonl"):
    """steps: список (имя, input, is_error); каждый вызов - отдельный ответ модели."""
    rows = []
    for i, (nm, inp, err) in enumerate(steps):
        ts = f"2026-01-01T10:{i // 60:02d}:{i % 60:02d}Z"
        rows.append({"type": "assistant", "timestamp": ts, "message": {
            "role": "assistant", "id": f"m{i}", "model": "claude-haiku-4-5", "usage": U1,
            "content": [{"type": "tool_use", "id": f"t{i}", "name": nm, "input": inp}]}})
        rows.append({"type": "user", "timestamp": ts, "message": {"role": "user", "content": [
            {"type": "tool_result", "tool_use_id": f"t{i}", "content": "x", "is_error": err}]}})
    p = tmp_path / name
    p.write_text("\n".join(json.dumps(r) for r in rows), encoding="utf-8")
    return str(p)


def run(tmp_path, steps, **kw):
    recs, t, s = S.read_journal(mk(tmp_path, steps))
    return S.analyze("r", recs, t, s, ["r"], **kw)


def test_normalize():
    n = RW.normalize_call
    assert n("Bash", {"command": "cd /x && python tools/run_12.py --a 5"}) == "Bash python run_<N>.py"
    assert n("Bash", {"command": "git -C /r log -3"}) == "Bash git log"
    assert n("PowerShell", {"command": "$r='D:\\p'; Set-Location $r; Get-Content a.txt"}) == "PowerShell Get-Content"
    assert n("Edit", {"file_path": "/a/rep_2026-01-02_v3.md"}) == "Edit /a/rep_<date>_v<N>.md"
    assert n("Edit", {"file_path": "/a/9f86d081884c7d65.md"}) == "Edit /a/<hash>.md"
    assert n("mcp__t__sim", {"b": 1, "a": 2}) == "mcp__t__sim(a,b)"
    assert n("Read", {"file_path": "/a/550e8400-e29b-41d4-a716-446655440000.txt"}) == "Read /a/<uuid>.txt"


def test_chain_found_and_nested_removed(tmp_path):
    steps = []
    for i in range(4):
        steps += [("mcp__t__get", {"a": 1}, False),
                  ("Edit", {"file_path": "/a/x.py"}, False)]
    r = run(tmp_path, steps + [("Glob", {"pattern": "z"}, False)])
    ch = r["однообразная_работа"]["chains"]
    labels = [" → ".join(c["цепочка"]) for c in ch]
    assert "mcp__t__get(a) → Edit /a/x.py" in labels
    pair = next(c for c in ch if len(c["цепочка"]) == 2)
    assert pair["раз"] == 4 and pair["ответов_модели"] == 8
    # get и Edit по отдельности вложены в пару с теми же повторами - убраны
    assert not any(len(c["цепочка"]) == 1 for c in ch)
    assert pair["usd"] > 0 and pair["токенов"] == 8 * 1110
    assert "Glob" not in " ".join(labels)


def test_run_of_same_call_is_one_chain(tmp_path):
    r = run(tmp_path, [("mcp__t__status", {}, False)] * 10)
    ch = r["однообразная_работа"]["chains"]
    assert len(ch) == 1 and ch[0]["раз"] == 10 and len(ch[0]["цепочка"]) == 1
    assert r["однообразная_работа"]["covered_pct"] == 100.0


def test_below_threshold(tmp_path):
    r = run(tmp_path, [("Grep", {"pattern": "a"}, False)] * 2)
    assert r["однообразная_работа"]["chains"] == []
    assert "нет цепочек" in RW.render_role_line("r", r["однообразная_работа"])


def test_errors_flag_and_candidates(tmp_path):
    steps = [("Bash", {"command": "make build"}, i < 2) for i in range(4)]       # 50 % ошибок
    steps += [("Bash", {"command": "make test"}, False) for _ in range(4)]
    r = run(tmp_path, steps)
    ch = {c["цепочка"][0]: c for c in r["однообразная_работа"]["chains"]}
    assert ch["Bash make build"]["не_отработана"] and ch["Bash make build"]["доля_ошибок"] == 0.5
    assert not ch["Bash make test"]["не_отработана"]
    text = S.render_text([r])
    assert "Кандидаты в инструмент" in text and "однообразная работа:" in text
    assert RW.NOT_READY in text
    rows, skipped = RW.candidates([r])
    assert [c["цепочка"][0] for _, c in rows] == ["Bash make test"] and skipped == 1
    assert "r#" in text


def test_skip_tools_and_json(tmp_path):
    steps = [("SendMessage", {"to": "a"}, False)] * 5 + [("mcp__t__st", {}, False)] * 3
    r = run(tmp_path, steps)
    assert [c["цепочка"] for c in r["однообразная_работа"]["chains"]] == [["mcp__t__st()"]]
    json.dumps(r, ensure_ascii=False)
    # заданные --prices тоже работают
    r2 = run(tmp_path, steps, prices=(0, 0, 0, 0))
    assert r2["однообразная_работа"]["chains"][0]["usd"] == 0


def test_search_and_anon_not_candidates(tmp_path):
    steps = [("Grep", {"pattern": "a"}, False)] * 5
    steps += [("Bash", {"command": "grep -r x ."}, False), ("PowerShell", {"command": "Get-Content a"}, False),
              ("Bash", {"command": "git log -3"}, False), ("Read", {"file_path": "/a/b"}, False)] * 2
    steps += [("PowerShell", {"command": "foreach ($x in 1..3) { }"}, False)] * 4
    steps += [("mcp__t__get", {"a": 1}, False)] * 3
    r = run(tmp_path, steps)
    rw = r["однообразная_работа"]
    assert [c["цепочка"] for c in rw["chains"]] == [["mcp__t__get(a)"]]
    assert rw["search_calls"] == 13 and rw["anon_calls"] == 4
    assert rw["search_pct"] == round(100 * 13 / 20, 1) and rw["covered_pct"] == 15.0
    text = S.render_text([r])
    assert "поиск и чтение: 65 %" in text and "безымянные скрипты: 4" in text
    assert RW.classify("Bash git rebase") == "work" and RW.classify("Bash python <inline>") == "anon"


def test_single_repeats_count_across_separators(tmp_path):
    # одиночный вызов считается по всем вхождениям, поиск/скрипты/обслуживание между ними не мешают
    sep = [("Grep", {"pattern": "a"}, False), ("Bash", {"command": "python <<EOF"}, False),
           ("PowerShell", {"command": "Get-Date"}, False)]
    steps = []
    for _ in range(4):
        steps += [("mcp__t__get", {"a": 1}, False)] + sep
    r = run(tmp_path, steps)
    ch = r["однообразная_работа"]["chains"]
    assert [(c["цепочка"], c["раз"]) for c in ch] == [(["mcp__t__get(a)"], 4)]
    assert r["однообразная_работа"]["maint_calls"] == 4


def test_maint_and_notes_not_candidates():
    for n in ("PowerShell Get-CimInstance", "PowerShell git fetch", "Bash pip install", "Bash docker logs",
              "Bash kubectl describe", "PowerShell Test-Path", "Edit C:/u/.claude/projects/x/memory/a.md",
              "Edit D:/p/CLAUDE.md", "Write D:/p/MEMORY.md"):
        assert RW.classify(n) == "maint", n
    assert RW.classify("Edit D:/p/win_proxy.py") == "work" and RW.classify("Bash docker build") == "work"
