import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import claude_mail as C  # noqa: E402

AID = "aaaaaaaa-1111-4111-8111-aaaaaaaaaaaa"
BID = "bbbbbbbb-2222-4222-8222-bbbbbbbbbbbb"


def U(ts, text):
    """Служебная запись user (isMeta): не реплика владельца."""
    return {"type": "user", "timestamp": ts, "isMeta": True, "message": {"role": "user", "content": text}}


def H(ts, text, origin="human", **extra):
    """Запись user нового формата: origin.kind (human - живая реплика)."""
    r = {"type": "user", "timestamp": ts, "message": {"role": "user", "content": text}}
    if origin:
        r["origin"] = {"kind": origin}
    r.update(extra)
    return r


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


# ---------------------------------------------------------------- псевдонимы и дубли
def test_name_with_bracket_suffix_is_same_role(tmp_path):
    """«Название [e7f7e9]» - то же имя, что заголовок журнала роли; id local_ из такого письма -
    тоже эта роль; отправка по имени с суффиксом идёт роли, а не other_."""
    hdr = {"type": "custom-title", "customTitle": "Поиск устройств", "sessionId": "s"}
    a = write(tmp_path, f"{AID}.jsonl", [
        hdr,
        send("2026-01-01T10:01:00Z", "Борис сессия [e7f7e9]", "Вопрос к Борису?", "a1")])
    b = write(tmp_path, f"{BID}.jsonl", [
        {"type": "custom-title", "customTitle": "Борис сессия", "sessionId": "s2"},
        incoming("2026-01-01T10:05:00Z", XID2, "Привет от Анны", "Поиск устройств [e7f7e9]"),
        send_mcp("2026-01-01T10:06:00Z", XID2, "Ответ Анне", "b1")])
    out = tmp_path / "o"
    C.main([str(out), f"anna={a}", f"boris={b}"])
    assert names(out) == ["001-anna-to-boris.md", "002-anna-to-boris.md", "003-boris-to-anna.md"] or \
        not any("other" in n for n in names(out))
    assert not any("other" in n for n in names(out))


XID2 = "local_eeeeeeee-5555-4555-8555-eeeeeeeeeeee"


def test_restart_id_joins_role_by_name(tmp_path):
    """После перезапуска у сессии новый local_<uuid>; во входящих он идёт с тем же именем."""
    NEW = "local_ffffffff-6666-4666-8666-ffffffffffff"
    a = write(tmp_path, f"{AID}.jsonl", [{"type": "custom-title", "customTitle": "Сессия Анны", "sessionId": "s"}])
    b = write(tmp_path, f"{BID}.jsonl", [
        incoming("2026-01-01T10:00:00Z", XID2, "До перезапуска", "Сессия Анны [abc123]"),
        incoming("2026-01-01T11:00:00Z", NEW, "После перезапуска", "Сессия Анны [abc123]"),
        send_mcp("2026-01-01T11:05:00Z", NEW, "Ответ", "r")])
    out = tmp_path / "o"
    C.main([str(out), f"anna={a}", f"boris={b}"])
    assert names(out) == ["001-anna-to-boris.md", "002-anna-to-boris.md", "003-boris-to-anna.md"]


def test_duplicate_send_record_with_same_tool_use_id_is_one_letter(tmp_path):
    row = send("2026-01-01T10:01:00Z", "boris", "Сделай X?", "a1")
    dup = send("2026-01-01T10:01:00Z", "boris", "Сделай X?", "a1")        # тот же tool_use id
    other = {"type": "assistant", "timestamp": "2026-01-01T10:01:30Z", "message": {"role": "assistant", "content": [
        {"type": "tool_use", "id": "tother", "name": "SendMessage", "input": {"to": "boris", "message": "Сделай X?"}}]}}
    a = write(tmp_path, f"{AID}.jsonl", [row, dup])
    b = write(tmp_path, f"{BID}.jsonl", [{"type": "custom-title", "customTitle": "boris", "sessionId": "s"}])
    out = tmp_path / "o"
    C.main([str(out), f"anna={a}", f"boris={b}"])
    assert names(out) == ["001-anna-to-boris.md"]
    a2 = write(tmp_path, "x.jsonl", [row, other])                         # разные id - два письма
    out2 = tmp_path / "o2"
    C.main([str(out2), f"anna={a2}", f"boris={b}"])
    assert len(names(out2)) == 2


def test_duplicate_incoming_record_same_time_is_one_letter(tmp_path):
    rec = incoming("2026-01-01T10:05:00Z", f"local_{AID}", "Привет", "Анна")
    a = write(tmp_path, f"{AID}.jsonl", [])
    b = write(tmp_path, f"{BID}.jsonl", [rec, rec])
    out = tmp_path / "o"
    C.main([str(out), f"anna={a}", f"boris={b}"])
    assert names(out) == ["001-anna-to-boris.md"]


def _owner(tmp, rows):
    p = write(tmp, f"{AID}.jsonl", rows)
    C.build(tmp / "out", [("arch", p)])
    return sorted((tmp / "out" / "mail").glob("*.md"))


def test_owner_replies_are_mail(tmp_path):
    files = _owner(tmp_path, [
        H("2026-01-01T10:00:00Z", "Держать положение, уровнем"),
        H("2026-01-01T10:01:00Z", "<system-reminder>x</system-reminder> Да, делай"),
        H("2026-01-01T10:02:00Z", "<system-reminder>The user started</system-reminder>"),
        H("2026-01-01T10:03:00Z", "[Request interrupted by user]", origin=None),
        H("2026-01-01T10:04:00Z", "<task-notification><task-id>x</task-id></task-notification>", "task-notification"),
        H("2026-01-01T10:05:00Z", "Another Claude session sent a message: <cross-session-message from=\"z\">hi</cross-session-message>", "peer", isMeta=True),
        H("2026-01-01T10:06:00Z", "This session is being continued from a previous", origin=None, isCompactSummary=True),
        H("2026-01-01T10:07:00Z", "# Autonomous loop check", origin=None, isMeta=True),
        H("2026-01-01T10:08:00Z", "<local-command-stdout>ok</local-command-stdout>", origin=None),
        H("2026-01-01T10:09:00Z", "ответ после перерыва", "human"),
        {"type": "user", "timestamp": "2026-01-01T10:10:00Z", "origin": {"kind": "human"},
         "message": {"role": "user", "content": [tr("t1", "результат")]}},
    ])
    names = [f.name for f in files]
    assert len(files) == 3 and all(n.endswith("-owner-to-arch.md") for n in names), names
    texts = [f.read_text(encoding="utf-8") for f in files]
    assert "Держать" in texts[0] and "Да, делай" in texts[1] and "<system-reminder>" not in texts[1]
    assert "ответ после" in texts[2]


def test_owner_strict_when_origin_present_and_fallback_without(tmp_path):
    # в журнале есть origin: запись без него (прерывание, служебное) - не владелец
    assert len(_owner(tmp_path, [H("2026-01-01T10:00:00Z", "один", "human"),
                                 H("2026-01-01T10:01:00Z", "два", origin=None)])) == 1
    # старый журнал без origin вообще: обычная реплика - владелец, isMeta/служебный текст - нет
    t2 = tmp_path / "b"
    t2.mkdir()
    assert len(_owner(t2, [H("2026-01-01T10:00:00Z", "обычная", origin=None),
                           H("2026-01-01T10:01:00Z", "мета", origin=None, isMeta=True),
                           H("2026-01-01T10:02:00Z", "The app was quit while", origin=None)])) == 1


def test_owner_answer_to_ask_user_question(tmp_path):
    ask = A("2026-01-01T10:00:00Z", [{"type": "tool_use", "id": "q1", "name": "AskUserQuestion",
                                      "input": {"questions": []}}], "q")
    ans = {"type": "user", "timestamp": "2026-01-01T12:00:00Z", "message": {"role": "user", "content": [
        tr("q1", 'Your questions have been answered: "Как?"="Уровнем". You can now continue with these answers in mind.')]}}
    other = {"type": "user", "timestamp": "2026-01-01T12:01:00Z", "message": {"role": "user", "content": [
        tr("zz", 'Your questions have been answered: "x"="y"')]}}
    files = _owner(tmp_path, [ask, ans, other])
    assert len(files) == 1 and "Уровнем" in files[0].read_text(encoding="utf-8")
    assert "continue with these" not in files[0].read_text(encoding="utf-8")
