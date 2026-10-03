import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import claude_mail as C  # noqa: E402

AID = "aaaaaaaa-1111-4111-8111-aaaaaaaaaaaa"
BID = "bbbbbbbb-2222-4222-8222-bbbbbbbbbbbb"


def U(ts, text):
    return {"type": "user", "timestamp": ts, "message": {"role": "user", "content": text}}


def A(ts, blocks, mid="m"):
    return {"type": "assistant", "timestamp": ts, "message": {"role": "assistant", "id": mid, "content": blocks}}


def send(ts, to, text, mid):
    return A(ts, [{"type": "tool_use", "id": "t" + mid, "name": "SendMessage",
                   "input": {"to": to, "message": text}}], mid)


def send_mcp(ts, sid, text, mid):
    return A(ts, [{"type": "tool_use", "id": "t" + mid, "name": "mcp__ccd_session_mgmt__send_message",
                   "input": {"session_id": sid, "message": text}}], mid)


def incoming(ts, frm, text, name="x"):
    return U(ts, f'Another Claude session sent a message:\n<cross-session-message from="{frm}" '
                 f'name="{name}">{text}</cross-session-message>')


def write(tmp, name, rows):
    p = tmp / name
    p.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\nмусор\n", encoding="utf-8")
    return str(p)


def make(tmp):
    a = write(tmp, f"{AID}.jsonl", [
        U("2026-01-01T10:00:00Z", "задание"),
        send_mcp("2026-01-01T10:01:00Z", f"local_{BID}", "Привет, Борис, сделай X?", "a1"),
        incoming("2026-01-01T10:05:00Z", f"local_{BID}", "Сделал X.", "Борис"),
        send("2026-01-01T10:06:00Z", "stranger", "Кто ты, Иванов?", "a2"),
        A("2026-01-01T10:07:00Z", [{"type": "text", "text": "ответ\nметрика: тесты=5 [источник: pytest]\nпрочее"}], "a3"),
    ])
    b = write(tmp, f"{BID}.jsonl", [
        incoming("2026-01-01T10:01:30Z", f"local_{AID}", "Привет, Борис, сделай X?", "Анна"),
        send_mcp("2026-01-01T10:04:50Z", f"local_{AID}", "Сделал X.", "b1"),
        incoming("2026-01-01T10:20:00Z", "local_cccccccc-3333-4333-8333-cccccccccccc", "Привет от чужого"),
    ])
    return a, b


def run(tmp, extra=()):
    a, b = make(tmp)
    out = tmp / "out"
    assert C.main([str(out), f"anna={a}", f"boris={b}", *extra]) == 0
    return out


def names(out):
    return sorted(p.name for p in (out / "mail").glob("*.md"))


def test_merge_roles_and_files(tmp_path):
    out = run(tmp_path)
    assert names(out) == ["001-anna-to-boris.md", "002-boris-to-anna.md",
                          "003-anna-to-other.md", "004-other-to-boris.md"]
    t = (out / "mail" / "001-anna-to-boris.md").read_text(encoding="utf-8")
    assert t.splitlines()[0] == "2026-01-01T10:01:00Z"
    assert "сделай X" in t


def test_incoming_only_and_outgoing_only(tmp_path):
    out = run(tmp_path)
    assert "Привет от чужого" in (out / "mail" / "004-other-to-boris.md").read_text(encoding="utf-8")
    assert "Кто ты" in (out / "mail" / "003-anna-to-other.md").read_text(encoding="utf-8")


def test_from_session_attribute_and_name(tmp_path):
    resolve = C.role_resolver([("anna", f"{AID}.jsonl"), ("boris", f"{BID}.jsonl")])
    assert resolve("zzz", "anna") == "anna"       # по имени роли
    assert resolve(AID) == "anna" and resolve(f"local_{BID}") == "boris"
    assert resolve("неизвестно") == "other"


def test_dedupe_requires_time_window(tmp_path):
    a = write(tmp_path, f"{AID}.jsonl", [send("2026-01-01T10:00:00Z", f"local_{BID}", "то же", "x")])
    b = write(tmp_path, f"{BID}.jsonl", [incoming("2026-01-01T11:00:00Z", f"local_{AID}", "то же")])
    out = tmp_path / "o"
    C.main([str(out), f"anna={a}", f"boris={b}"])
    assert len(names(out)) == 2


def test_metrics_stats_and_mail_stats(tmp_path):
    out = run(tmp_path)
    j = (out / "journal.md").read_text(encoding="utf-8")
    assert "метрика: тесты=5 [источник: pytest]" in j and "прочее" not in j
    assert "anna" in (out / "stats.md").read_text(encoding="utf-8")
    import mail_stats
    assert len(mail_stats.load(out)) == 4


def test_since_until(tmp_path):
    a, b = make(tmp_path)
    out = tmp_path / "o"
    C.main([str(out), f"anna={a}", f"boris={b}", "--since", "2026-01-01T10:10:00Z"])
    assert names(out) == ["001-other-to-boris.md"]


def test_anon(tmp_path):
    out = run(tmp_path, ["--anon", "--anon-words", "Иванов,борис"])
    allt = "".join((out / "mail" / n).read_text(encoding="utf-8") for n in names(out))
    assert "Иванов" not in allt and "Борис" not in allt and "[скрыто]" in allt
    out2 = tmp_path / "o2"
    a, b = make(tmp_path)
    C.main([str(out2), f"anna={a}", f"boris={b}", "--anon-words", "Иванов"])   # без --anon слова не трогаются
    assert "Иванов" in (out2 / "mail" / "003-anna-to-other.md").read_text(encoding="utf-8")


def test_alias_by_title(tmp_path):
    """Живой случай: id local_X не равен имени файла; связь через заголовок сессии."""
    X = "local_dddddddd-4444-4444-8444-dddddddddddd"
    hdr = {"type": "custom-title", "customTitle": "Сессия Анны", "sessionId": "s"}
    a = write(tmp_path, f"{AID}.jsonl", [hdr])
    b = write(tmp_path, f"{BID}.jsonl", [incoming("2026-01-01T10:00:00Z", X, "Вопрос?", "Сессия Анны"),
                                         send_mcp("2026-01-01T10:01:00Z", X, "Ответ", "r")])
    out = tmp_path / "o"
    C.main([str(out), f"anna={a}", f"boris={b}"])
    assert names(out) == ["001-anna-to-boris.md", "002-boris-to-anna.md"]
