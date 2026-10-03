import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent))
import mail_stats as M  # noqa: E402
import progress as P  # noqa: E402

REAL = Path(__file__).resolve().parent.parent / "runs" / "002" / "spec"


def mk_mail(tmp_path, letters):
    d = tmp_path / "mail"
    d.mkdir()
    for name, text in letters:
        (d / name).write_text(text, encoding="utf-8")
    return tmp_path


def run_mail(path, *extra):
    msgs = M.load(path)
    return M.render(M.analyze(msgs, [x for x in extra], 5), len(msgs))


def test_mail_unanswered_and_waits(tmp_path):
    f = mk_mail(tmp_path, [
        ("001-a-to-b.md", "Реши, пожалуйста, как быть?"),
        ("002-b-to-c.md", "Другое письмо без вопросов, просто сообщаю результат работы над задачей."),
        ("003-c-to-all.md", "Всем привет, итог готов."),
    ])
    out = run_mail(f)
    assert "a -> b: 001-a-to-b.md" in out and "признаки: вопрос" in out
    assert "b -> c: 002-b-to-c.md" in out and "признаки: нет" in out       # без признаков - тоже кандидат
    assert "-> all" not in out                                             # рассылка - не адресное письмо
    assert "a: отправлено 1, получено 1 (адресно 0, через all 1), без ответа 1" in out
    assert "c: отправлено 1, получено 1 (адресно 1, через all 0), без ответа 0" in out
    assert "b: отправлено 1, получено 2 (адресно 1, через all 1)" in out


def test_mail_any_letter_back_closes_candidate(tmp_path):
    f = mk_mail(tmp_path, [
        ("001-a-to-b.md", "Что думаешь?"),
        ("002-b-to-a.md", "Думаю, надо делать так, а не иначе, потому что это проще и надёжнее. " * 5),
    ])
    out = run_mail(f)
    assert "a -> b" not in out and "b -> a: 002-b-to-a.md" in out          # ответ сам ждёт ответа


def test_mail_silent_empty_and_loop(tmp_path):
    f = mk_mail(tmp_path, [
        ("001-a-to-b.md", "Привет"),
        ("002-b-to-a.md", "Принял, работаю."),
        ("003-a-to-b.md", "Ещё деталь"),
        ("004-b-to-a.md", "Ок"),
        ("005-a-to-b.md", "Спасибо"),
    ])
    out = run_mail(f, "z")
    assert "не писали ни разу: z" in out
    assert "002-b-to-a.md" in out.split("Пустые")[1]
    assert "возможный круг" in out
    assert "молчит: z" in out


def test_mail_quiet_in_last_k(tmp_path):
    letters = [("001-q-to-a.md", "первое")]
    letters += [(f"{i:03d}-a-to-b.md", "x") for i in range(2, 9)]
    f = mk_mail(tmp_path, letters)
    a = M.analyze(M.load(f), (), 3)
    assert "q" in a["quiet"]


def test_mail_empty_folder(tmp_path, capsys):
    assert M.main([str(tmp_path)]) == 0
    assert "Писем нет" in capsys.readouterr().out


def test_mail_real_folder(capsys):
    assert M.main([str(REAL)]) == 0
    out = capsys.readouterr().out
    assert "Писем всего: 5" in out
    assert "внимание:" in out
    assert "003-choreographer-to-expert.md" in out


# ---------------------------------------------------------------- progress
def journal(tmp_path, text):
    p = tmp_path / "journal.md"
    p.write_text(text, encoding="utf-8")
    return p


def run_p(capsys, *args):
    assert P.main([str(a) for a in args]) == 0
    return capsys.readouterr().out


def test_progress_going(tmp_path, capsys):
    p = journal(tmp_path, "\n".join([
        "отрезок 1: метрика ошибки=100 [источник: pytest]",
        "отрезок 2: метрика ошибки=60 (было 100) [источник: pytest], токены за отрезок=500, всего=500",
        "отрезок 3: метрика ошибки=30 (было 60) [источник: pytest]",
    ]))
    out = run_p(capsys, p)
    assert "уменьшение 30 (+50%)" in out
    assert "до цели ещё 1 отрезк." in out  # темп (40+30)/2=35
    assert out.strip().splitlines()[-1].startswith("вывод: идёт")


def test_progress_plateau_big_and_small(tmp_path, capsys):
    p = journal(tmp_path, "\n".join([
        "метрика: ошибки=100 [источник: a]",
        "метрика: ошибки=98 [источник: b]",
        "метрика: ошибки=97 [источник: c]",
    ]))
    out = run_p(capsys, p)
    assert "ПЛАТО" in out and "плато - требуй смены способа" in out
    p2 = journal(tmp_path, "метрика: м=10 [источник: a]\nметрика: м=10 [источник: b]\nметрика: м=10 [источник: c]\n")
    assert "ПЛАТО" in run_p(capsys, p2)
    p3 = journal(tmp_path, "метрика: м=10 [источник: a]\nметрика: м=9 [источник: b]\nметрика: м=8 [источник: c]\n")
    assert "ПЛАТО" not in run_p(capsys, p3)


def test_progress_growth(tmp_path, capsys):
    p = journal(tmp_path, "метрика: м=10 [источник: a]\nметрика: м=12 [источник: a]\n")
    out = run_p(capsys, p)
    assert "РОСТ" in out and "выясни причину" in out


def test_progress_goal_and_target(tmp_path, capsys):
    p = journal(tmp_path, "метрика: м=10 [источник: a]\nметрика: м=8 [источник: b]\nметрика: м=3 [источник: c]\n")
    assert "ЦЕЛЬ" in run_p(capsys, p, "--target", 5)
    assert "проверь приёмку" in run_p(capsys, p, "--target", 5)
    assert "ЦЕЛЬ" not in run_p(capsys, p)


def test_progress_no_data(tmp_path, capsys):
    p = journal(tmp_path, "# Журнал\nпросто текст\n")
    out = run_p(capsys, p)
    assert "метрики нет" in out.lower() and "вслепую" in out
    assert out.strip().splitlines()[-1].startswith("вывод: метрики нет")


def test_progress_no_source(tmp_path, capsys):
    p = journal(tmp_path, "метрика: м=10\nметрика: м=5 [источник: x]\n")
    out = run_p(capsys, p)
    assert "БЕЗ ИСТОЧНИКА" in out


def test_progress_budget(tmp_path, capsys):
    j = journal(tmp_path, "отрезок 1: м=100 (было 120) [источник: a]\nотрезок 2: м=80 (было 100) [источник: a]\n")
    s = tmp_path / "stats.md"
    s.write_text("== a: 1 ==\nтокены: вывод 1000000; вход без кэша 0; вход через кэш: чтение 0, запись 0\n"
                 "итог сессии (из события result): стоимость $2.0; ходов 3\n", encoding="utf-8")
    out = run_p(capsys, j, "--stats", s, "--budget-usd", 3)
    assert "Стоимость: $2.00" in out and "НЕ хватит" in out
    out = run_p(capsys, j, "--stats", s, "--budget-usd", 100)
    assert "хватит." in out and "НЕ" not in out.split("Бюджет")[1]


def test_progress_budget_estimate(tmp_path, capsys):
    j = journal(tmp_path, "метрика: м=10 [источник: a]\nметрика: м=5 [источник: a]\n")
    s = tmp_path / "stats.md"
    s.write_text("токены: вывод 1000000; вход без кэша 1000000; вход через кэш: чтение 1000000, запись 1000000\n",
                 encoding="utf-8")
    out = run_p(capsys, j, "--stats", s, "--budget-usd", 50)
    assert "$7.35" in out and "оценка" in out


def test_progress_real(capsys):
    out = run_p(capsys, REAL / "journal.md", "--stats", REAL / "stats.md", "--budget-usd", 5)
    assert "вопросов_без_ответа" in out
    assert out.strip().splitlines()[-1].startswith("вывод:")


# ---------------------------------------------------------------- доработки по итогам 003
def test_mail_reply_to_third_party_does_not_close(tmp_path):
    """Закрывает только письмо адресата САМОМУ отправителю: письмо третьему - нет (высокая полнота)."""
    p = mk_mail(tmp_path, [
        ("001-ch-to-ex.md", "Привет! Producer просит тебя проверить спецификацию?"),
        ("002-ex-to-producer.md", "Проверил, вот результат."),
    ])
    assert "ch -> ex: 001-ch-to-ex.md" in run_mail(p)


def test_mail_real_003_runs():
    r003 = Path(__file__).resolve().parent.parent / "runs" / "003" / "spec"
    if not r003.is_dir():
        pytest.skip("нет runs/003")
    assert "внимание:" in run_mail(r003)


def L(ts, text):
    return f"2026-01-01T{ts}Z\n\n{text}\n"


def waits_of(tmp_path, letters):
    p = mk_mail(tmp_path, letters)
    return M.analyze(M.load(p), (), 5)


def test_bare_three_digit_number_is_not_a_reference(tmp_path):
    p = mk_mail(tmp_path, [
        ("001-a-to-b.md", "Прошу сделать X?"),
        ("002-b-to-c.md", "Тест прошёл за 001 секунд, версия 001."),
    ])
    assert "a ждёт b" in run_mail(p)                       # раньше любое «001» считалось ссылкой


def test_reply_window(tmp_path):
    a = waits_of(tmp_path, [
        ("001-a-to-b.md", L("10:00:00", "Прошу сделать X?")),
        ("002-b-to-a.md", L("11:59:00", "Сделал, вот результат.")),
    ])
    assert ("a", "b") not in a["waits"]                      # ответ в пределах окна (по умолчанию 2 ч)
    d = tmp_path / "late"
    d.mkdir()
    msgs = [("001-a-to-b.md", L("10:00:00", "Прошу сделать X?")),
            ("002-b-to-a.md", L("12:30:00", "Сделал, вот результат."))]
    assert ("a", "b") in waits_of(d, msgs)["waits"]          # позже окна - письмо кандидат
    assert ("a", "b") in M.analyze(M.load(d), (), 5, window_h=2)["waits"]
    assert ("a", "b") not in M.analyze(M.load(d), (), 5, window_h=3)["waits"]


def test_fresh_candidate_inside_window(tmp_path):
    a = waits_of(tmp_path, [
        ("001-a-to-b.md", L("10:00:00", "Сделай X.")),
        ("002-x-to-y.md", L("10:30:00", "Привет, просто сообщаю.")),
    ])
    it = [i for i in a["wait_items"] if i["name"] == "001-a-to-b.md"][0]
    assert it["fresh"] and it["age"] == 1800
    assert "окно 2 ч не истекло" in M.render(a, 2)


def test_reply_must_go_to_sender(tmp_path):
    a = waits_of(tmp_path, [
        ("001-a-to-b.md", L("10:00:00", "Прошу сделать X?")),
        ("002-b-to-c.md", L("10:05:00", "Сделал, вот результат.")),
    ])
    assert ("a", "b") in a["waits"]                          # b ответил не отправителю


def test_other_topic_reply_still_closes(tmp_path):
    """Письмо адресата по любой теме в окне закрывает кандидата: скрипт не угадывает тему."""
    a = waits_of(tmp_path, [
        ("001-a-to-b.md", L("10:00:00", "Прошу собрать отчёт по продажам за квартал?")),
        ("002-b-to-a.md", L("10:10:00", "Права доступа к репозиторию кластера проверил, всё работает.")),
    ])
    assert ("a", "b") not in a["waits"]


def test_signals_only_mark(tmp_path):
    cases = {"На слияние: ветка x, 3c62c17.": "на слияние", "Прогон — BLOCKED на prepare.": "BLOCKED",
             "Жду твоего решения.": "жду", "Сколько это займёт?": "вопрос", "Пришли кандидат.": "прошу",
             "Попросите владельца.": "прошу", "Дайте доступ.": "прошу", "Предлагаю так.": "прошу",
             "Прошу проверить.": "прошу"}
    for text, sig in cases.items():
        assert sig in M.signals_of(text), text
    assert M.signals_of("Ожидаем результата сборки.") == []             # «ожидаем» - не признак
    assert M.signals_of("Ничего делать не нужно.") == []                # «не нужно» - не признак
    assert "жду" not in M.signals_of("Жду слова оператора.")             # ждёт не адресата
    # признаков нет, а письмо всё равно кандидат
    a = waits_of(tmp_path, [("001-a-to-b.md", L("10:00:00", "Влил fast-forward, всё закрыто."))])
    assert a["wait_items"][0]["signals"] == []


def test_reports_go_to_separate_tail(tmp_path):
    letters = [("001-a-to-b.md", L("10:01:00", "Готово: сделал X, коммит abc1234.")),
               ("002-a-to-b.md", L("10:02:00", "Принял, спасибо.")),
               ("003-a-to-b.md", L("10:03:00", "Готово ли это? Что дальше?")),     # с вопросом - не отчёт
               ("004-c-to-b.md", L("10:04:00", "Прошу проверить Y."))]
    a = waits_of(tmp_path, letters)
    rep = {i["name"] for i in a["wait_items"] if i["report"]}
    assert rep == {"001-a-to-b.md", "002-a-to-b.md"}
    out = M.render(a, 4)
    assert "Вероятно, отчёты" in out
    assert out.index("004-c-to-b.md") < out.index("Вероятно, отчёты") < out.index("001-a-to-b.md (")


def test_first_line_and_signals_in_output(tmp_path):
    p = mk_mail(tmp_path, [("001-a-to-b.md", L("10:00:00", "tools,\n\n**Сделай X** и пришли результат. " + "и ещё слова " * 20))])
    out = M.render(M.analyze(M.load(p), (), 5), 1)
    line = [x for x in out.splitlines() if "->" in x and "001-a-to-b.md" in x][0]
    assert "признаки: прошу" in line and "«Сделай X и пришли результат." in line
    assert line.count("…") == 1 and len(line.split("«")[1]) <= 102


def test_signals_sort_first_then_age(tmp_path):
    a = waits_of(tmp_path, [
        ("001-a-to-b.md", L("10:00:00", "Просто сообщаю.")),
        ("002-c-to-b.md", L("10:30:00", "Прошу сделать Y.")),
        ("003-d-to-b.md", L("10:40:00", "Прошу сделать Z.")),
    ])
    assert [i["name"] for i in a["wait_items"]] == ["002-c-to-b.md", "003-d-to-b.md", "001-a-to-b.md"]


def test_top_limit_and_queue_at_node(tmp_path):
    p = mk_mail(tmp_path, [(f"{i:03d}-a{i}-to-hub.md", L(f"10:{i:02d}:00", "Прошу ответить?")) for i in range(1, 8)])
    a = M.analyze(M.load(p), (), 5)
    out = M.render(a, 7, top=3)
    assert "Очередь у узла: hub — 7 кандидатов" in out
    assert out.count("-> hub: ") == 3 and "(ещё 4 кандидатов не показано)" in out


def test_external_session_is_not_a_candidate_target(tmp_path):
    a = waits_of(tmp_path, [("001-a-to-other_Чужая_сессия.md", L("10:00:00", "Прошу ответить?"))])
    assert not a["wait_items"]


def test_age_and_order_in_waits(tmp_path):
    p = mk_mail(tmp_path, [
        ("001-a-to-b.md", L("10:00:00", "Прошу сделать X.")),
        ("002-c-to-b.md", L("10:30:00", "Прошу сделать Y.")),
        ("003-x-to-y.md", L("13:00:00", "Привет, просто сообщаю.")),
    ])
    a = M.analyze(M.load(p), (), 5)
    assert [i["name"] for i in a["wait_items"] if i["to"] == "b"] == ["001-a-to-b.md", "002-c-to-b.md"]   # старые сверху
    assert a["wait_items"][0]["age"] == 3 * 3600
    out = M.render(a, 3)
    assert "001-a-to-b.md (возраст 3ч 00м" in out and "возраст 2ч 30м" in out
    assert out.index("001-a-to-b.md (возраст") < out.index("002-c-to-b.md (возраст")


def test_repeat_signal(tmp_path):
    q = "Один вопрос о стыке ПЛК и робота перед окном карточки двойника: гаснет ли STOPMESS сам, или нужен импульс CONF_MESS?"
    a = waits_of(tmp_path, [
        ("001-a-to-b.md", L("10:00:00", q)),
        ("002-a-to-b.md", L("10:03:00", "Повторяю вопрос после перезапуска. " + q)),
    ])
    assert [(r["name"], r["orig"], r["replied"]) for r in a["repeats"]] == [("002-a-to-b.md", "001-a-to-b.md", False)]
    out = M.render(a, 2)
    assert "повтор без ответа" in out and "002-a-to-b.md повторяет 001-a-to-b.md" in out
    # просто похожие слова без «повторяю» и без почти полного совпадения - не повтор
    d = tmp_path / "x"
    d.mkdir()
    a2 = waits_of(d, [("001-a-to-b.md", L("10:00:00", q)),
                      ("002-a-to-b.md", L("10:03:00", "Прошу сообщить статус сборки образа и тестов?"))])
    assert not a2["repeats"]


def test_subagents_folded_and_never_wait(tmp_path):
    a = waits_of(tmp_path, [
        ("001-a-to-a_sub_a1b2c3d4e.md", L("10:00:00", "Прошу уточнить пункт 2?")),
        ("002-a_sub_a9f8e7d6c-to-a.md", L("10:05:00", "Итоги работы, жду приёмки.")),
    ])
    assert not a["waits"]
    assert "a_sub" in a["roles"] and not any("_sub_" in r for r in a["roles"])
