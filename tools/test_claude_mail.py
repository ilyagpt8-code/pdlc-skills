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


def tr(i, text):
    return {"type": "tool_result", "tool_use_id": i, "content": text}


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
                          "003-anna-to-other_stranger.md", "004-other_x-to-boris.md"]
    t = (out / "mail" / "001-anna-to-boris.md").read_text(encoding="utf-8")
    assert t.splitlines()[0] == "2026-01-01T10:01:00Z"
    assert "сделай X" in t


def test_incoming_only_and_outgoing_only(tmp_path):
    out = run(tmp_path)
    assert "Привет от чужого" in (out / "mail" / "004-other_x-to-boris.md").read_text(encoding="utf-8")
    assert "Кто ты" in (out / "mail" / "003-anna-to-other_stranger.md").read_text(encoding="utf-8")


def test_from_session_attribute_and_name(tmp_path):
    resolve = C.role_resolver([("anna", f"{AID}.jsonl"), ("boris", f"{BID}.jsonl")])
    assert resolve("zzz", "anna") == "anna"       # по имени роли
    assert resolve(AID) == "anna" and resolve(f"local_{BID}") == "boris"
    assert resolve("неизвестно") == "other"


def test_dedupe_requires_time_window(tmp_path):
    a = write(tmp_path, f"{AID}.jsonl", [send("2026-01-01T10:00:00Z", f"local_{BID}", "то же", "x")])
    b = write(tmp_path, f"{BID}.jsonl", [incoming("2026-01-02T11:00:00Z", f"local_{AID}", "то же")])
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
    assert names(out) == ["001-other_x-to-boris.md"]


def test_anon(tmp_path):
    out = run(tmp_path, ["--anon", "--anon-words", "Иванов,борис"])
    allt = "".join((out / "mail" / n).read_text(encoding="utf-8") for n in names(out))
    assert "Иванов" not in allt and "Борис" not in allt and "[скрыто]" in allt
    out2 = tmp_path / "o2"
    a, b = make(tmp_path)
    C.main([str(out2), f"anna={a}", f"boris={b}", "--anon-words", "Иванов"])   # без --anon слова не трогаются
    assert "Иванов" in (out2 / "mail" / "003-anna-to-other_stranger.md").read_text(encoding="utf-8")


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


# ---------------------------------------------------------------- доработки по живому ансамблю
UDS = "uds:\\.\pipe\LOCAL\cc-msg-0123456789abcdef0123456789abcdef"
XID = "local_dddddddd-4444-4444-8444-dddddddddddd"
TITLE = {"type": "custom-title", "customTitle": "Сессия Анны", "sessionId": "s"}


def incoming_v2(ts, frm_uds, frm_sess, name, text):
    """Формат с from (uds-канал), from-session (local_<uuid>), from-name."""
    return U(ts, f'<cross-session-message from="{frm_uds}" from-session="{frm_sess}" '
                 f'from-name="{name}" from-mode="prompting">\n{text}\n</cross-session-message>')


def queue_op(ts, content, op="enqueue"):
    return {"type": "queue-operation", "operation": op, "timestamp": ts, "content": content}


def attach(ts, prompt):
    return {"type": "attachment", "timestamp": ts, "attachment": {"type": "queued_command", "prompt": prompt}}


def block(frm, name, text):
    return f'<cross-session-message from="{frm}" name="{name}">{text}</cross-session-message>'


def test_id_table_uds_and_local_to_role(tmp_path):
    """Таблица id -> роль из from/from-session/from-name: uds-канал и local_<uuid> - одна роль,
    исходящее по такому адресу не уходит в other."""
    tb = {"type": "custom-title", "customTitle": "Сессия Бориса", "sessionId": "s"}
    a = write(tmp_path, f"{AID}.jsonl", [incoming_v2("2026-01-01T10:00:00Z", UDS, XID, "Сессия Бориса", "Вопрос?"),
                                         send_mcp("2026-01-01T10:10:00Z", UDS, "Отвечаю по X", "r1"),
                                         send_mcp("2026-01-01T10:20:00Z", XID, "И ещё Y", "r2")])
    b = write(tmp_path, f"{BID}.jsonl", [tb])
    out = tmp_path / "o"
    C.main([str(out), f"anna={a}", f"boris={b}"])
    assert names(out) == ["001-boris-to-anna.md", "002-anna-to-boris.md", "003-anna-to-boris.md"]


def test_id_table_function(tmp_path):
    titles = {"anna": {"сессия анны"}}
    recs = {"boris": [{"kind": "user", "ts": None, "tools": [], "results": [], "text":
                       incoming_v2("t", UDS, XID, "Сессия Анны", "q")["message"]["content"]}]}
    al = C.learn_aliases(recs, titles)
    assert al[C._sid(UDS)] == "anna" and al[C._sid(XID)] == "anna"
    resolve = C.role_resolver([("anna", f"{AID}.jsonl")], titles, al)
    assert resolve(UDS) == "anna" and resolve(XID) == "anna"


def test_queue_operation_and_attachment_are_read_and_deduped(tmp_path):
    msg = block(f"local_{AID}", "Анна", "Привет из очереди")
    b = write(tmp_path, f"{BID}.jsonl", [
        queue_op("2026-01-01T10:00:00Z", msg),              # поставлено в очередь
        queue_op("2026-01-01T10:09:00Z", msg, op="remove"),  # remove не письмо
        attach("2026-01-01T10:09:01Z", msg),                # доставлено (queued_command)
        incoming("2026-01-01T10:09:02Z", f"local_{AID}", "Привет из очереди", "Анна"),   # запись user
    ])
    a = write(tmp_path, f"{AID}.jsonl", [TITLE])
    out = tmp_path / "o"
    C.main([str(out), f"anna={a}", f"boris={b}"])
    assert len(names(out)) == 1                              # три копии - одно письмо
    t = (out / "mail" / names(out)[0]).read_text(encoding="utf-8")
    assert t.splitlines()[0] == "2026-01-01T10:00:00Z" and "Привет из очереди" in t


def test_only_queue_operation_is_not_lost(tmp_path):
    b = write(tmp_path, f"{BID}.jsonl", [queue_op("2026-01-01T10:00:00Z", block(f"local_{AID}", "Анна", "Только очередь"))])
    a = write(tmp_path, f"{AID}.jsonl", [])
    out = tmp_path / "o"
    C.main([str(out), f"anna={a}", f"boris={b}"])
    assert names(out) == ["001-anna-to-boris.md"]


def test_merge_out_and_in_up_to_12_hours(tmp_path):
    a = write(tmp_path, f"{AID}.jsonl", [send_mcp("2026-01-01T10:00:00Z", f"local_{BID}", "Долгая доставка", "d")])
    b = write(tmp_path, f"{BID}.jsonl", [incoming("2026-01-01T10:10:00Z", f"local_{AID}", "Долгая доставка")])
    out = tmp_path / "o"
    C.main([str(out), f"anna={a}", f"boris={b}"])
    assert names(out) == ["001-anna-to-boris.md"]            # 10 минут - одно письмо (раньше: два)
    a2 = write(tmp_path, f"{AID}.jsonl", [send_mcp("2026-01-01T10:00:00Z", f"local_{BID}", "Повтор", "d1"),
                                          send_mcp("2026-01-01T10:30:00Z", f"local_{BID}", "Повтор", "d2")])
    b2 = write(tmp_path, f"{BID}.jsonl", [incoming("2026-01-01T10:01:00Z", f"local_{AID}", "Повтор"),
                                          incoming("2026-01-01T10:31:00Z", f"local_{AID}", "Повтор")])
    out2 = tmp_path / "o2"
    C.main([str(out2), f"anna={a2}", f"boris={b2}"])
    assert len(names(out2)) == 2                              # два настоящих письма не слиплись


def test_subagent_address_and_notification(tmp_path):
    AG = "a0123456789abcdef"
    launch = A("2026-01-01T10:00:00Z", [{"type": "tool_use", "id": "tA", "name": "Agent",
                                         "input": {"description": "d", "prompt": "p"}}], "g1")
    res = U("2026-01-01T10:00:01Z", [tr("tA", f"Async agent launched successfully.\nagentId: {AG} (internal ID)")])
    notif = f"<task-notification>\n<task-id>{AG}</task-id>\n<status>completed</status>\n" \
            f"<result>Итоги работы субагента</result>\n</task-notification>"
    bg = f"<task-notification>\n<task-id>bzzzzzzzz</task-id>\n<result>фоновая команда</result>\n</task-notification>"
    a = write(tmp_path, f"{AID}.jsonl", [launch, res,
                                         send("2026-01-01T10:05:00Z", AG, "Уточни пункт 2", "s1"),
                                         queue_op("2026-01-01T10:20:00Z", notif),
                                         attach("2026-01-01T10:20:01Z", notif),
                                         queue_op("2026-01-01T10:21:00Z", bg)])
    out = tmp_path / "o"
    C.main([str(out), f"anna={a}"])
    assert names(out) == ["001-anna-to-anna_sub_a01234567.md", "002-anna_sub_a01234567-to-anna.md"]
    t = (out / "mail" / names(out)[1]).read_text(encoding="utf-8")
    assert "Итоги работы субагента" in t and "фоновая" not in "".join(
        (out / "mail" / n).read_text(encoding="utf-8") for n in names(out))


def test_external_session_without_journal_named(tmp_path):
    b = write(tmp_path, f"{BID}.jsonl", [
        incoming_v2("2026-01-01T10:00:00Z", UDS, XID, "Внешняя сессия", "Привет"),
        send_mcp("2026-01-01T10:05:00Z", XID, "Ответ внешней", "e1"),
        send("2026-01-01T10:06:00Z", "Другая внешняя", "Привет другой", "e2")])
    out = tmp_path / "o"
    C.main([str(out), f"boris={b}"])
    assert names(out) == ["001-other_Внешняя_сессия-to-boris.md", "002-boris-to-other_Внешняя_сессия.md",
                          "003-boris-to-other_Другая_внешняя.md"]


def test_failed_send_and_empty_notify_are_not_letters(tmp_path):
    a = write(tmp_path, f"{AID}.jsonl", [
        send("2026-01-01T10:00:00Z", "ghost", "Не дошло", "f1"),
        U("2026-01-01T10:00:01Z", [tr("tf1", '{"success":false,"message":"No agent named ghost is reachable."}')]),
        send("2026-01-01T10:01:00Z", "ghost", "", "f2"),                  # notify_when_idle без текста
        send("2026-01-01T10:02:00Z", "ghost", "Дошло", "f3")])
    out = tmp_path / "o"
    C.main([str(out), f"anna={a}"])
    assert len(names(out)) == 1
    assert "Дошло" in (out / "mail" / names(out)[0]).read_text(encoding="utf-8")
