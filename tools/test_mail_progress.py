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
    assert "a ждёт b: 001-a-to-b.md" in out
    assert "a: отправлено 1, получено 1 (адресно 0, через all 1), без ответа 1" in out
    # all не считается неотвеченным; b получил через all
    assert "c: отправлено 1, получено 1 (адресно 1, через all 0), без ответа 0" in out
    assert "b: отправлено 1, получено 2 (адресно 1, через all 1)" in out


def test_mail_answer_clears_wait(tmp_path):
    f = mk_mail(tmp_path, [
        ("001-a-to-b.md", "Что думаешь?"),
        ("002-b-to-a.md", "Думаю, надо делать так, а не иначе, потому что это проще и надёжнее. " * 5),
    ])
    out = run_mail(f)
    assert "Ждут: никто." in out
    assert "явных сигналов нет" in out


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
def test_mail_answered_by_reference(tmp_path):
    p = mk_mail(tmp_path, [
        ("001-a-to-b.md", "Прошу сделать X?"),
        ("002-b-to-c.md", "Сделал по письму 001-a-to-b.md"),
    ])
    assert "a ждёт b" not in run_mail(p)


def test_mail_answered_by_number(tmp_path):
    p = mk_mail(tmp_path, [
        ("001-a-to-b.md", "Прошу сделать X?"),
        ("002-b-to-c.md", "Закрыл вопрос из письма 001."),
    ])
    assert "a ждёт b" not in run_mail(p)


def test_mail_answered_third_party(tmp_path):
    p = mk_mail(tmp_path, [
        ("001-ch-to-ex.md", "Привет! Producer просит тебя проверить спецификацию?"),
        ("002-ex-to-producer.md", "Проверил, вот результат."),
    ])
    assert "ch ждёт ex" not in run_mail(p)


def test_mail_third_party_not_written_still_waits(tmp_path):
    p = mk_mail(tmp_path, [
        ("001-ch-to-ex.md", "Привет! Producer просит тебя проверить спецификацию?"),
        ("002-ex-to-other.md", "Занят."),
    ])
    assert "ch ждёт ex" in run_mail(p)


def test_mail_real_003_choreographer_not_waiting():
    r003 = Path(__file__).resolve().parent.parent / "runs" / "003" / "spec"
    if not r003.is_dir():
        pytest.skip("нет runs/003")
    assert "choreographer ждёт expert" not in run_mail(r003)


def test_progress_was_without_prior_point(tmp_path, capsys):
    j = journal(tmp_path, "\n".join([
        "метрика: q=8 (было 0) [источник: проверка 1]",
        "метрика: q=2 [источник: проверка 2]"]))
    out = run_p(capsys, j)
    assert "0 -> 8" not in out and "шаг 1: 8 -> 2" in out


def test_progress_duplicate_same_source_not_point(tmp_path, capsys):
    j = journal(tmp_path, "\n".join([
        "метрика: q=8 [источник: проверка 1]",
        "метрика: q=8 [источник: проверка 1]",
        "метрика: q=2 [источник: проверка 2]"]))
    out = run_p(capsys, j)
    assert "шаг 2" not in out and "шаг 1: 8 -> 2" in out and "ПЛАТО" not in out


def test_progress_same_value_other_source_is_point(tmp_path, capsys):
    j = journal(tmp_path, "\n".join([
        "метрика: q=8 [источник: проверка 1]",
        "метрика: q=8 [источник: проверка 2]"]))
    assert "шаг 1: 8 -> 8" in run_p(capsys, j)


def test_progress_zero_from_first(tmp_path, capsys):
    j = journal(tmp_path, "метрика: q=0 [источник: проверка 1]")
    out = run_p(capsys, j)
    assert "НОЛЬ С ПЕРВОЙ" in out
    assert "цель с первой проверки - подозрительно" in out.strip().splitlines()[-1]


def test_progress_no_zero_from_first_when_gradual(tmp_path, capsys):
    j = journal(tmp_path, "\n".join([
        "метрика: q=5 [источник: a]", "метрика: q=3 [источник: b]", "метрика: q=0 [источник: c]"]))
    out = run_p(capsys, j)
    assert "НОЛЬ С ПЕРВОЙ" not in out and "цель достигнута" in out


def test_progress_target_changed(tmp_path, capsys):
    for i, txt in enumerate(["цель ≤4", "target ≤4", "целевой=4", "целевая метрика: q≤4"]):
        j = journal(tmp_path, f"метрика: q=8 [источник: a]\n{txt}\nметрика: q=2 [источник: b]")
        out = run_p(capsys, j)
        assert "ЦЕЛЬ ИЗМЕНЕНА" in out, txt
        assert "(было 0, стало 4)" in out.strip().splitlines()[-1], txt


def test_progress_target_same_not_changed(tmp_path, capsys):
    j = journal(tmp_path, "цель ≤4\nметрика: q=8 [источник: a]\nметрика: q=6 [источник: b]")
    assert "ЦЕЛЬ ИЗМЕНЕНА" not in run_p(capsys, j, "--target", 4)


def test_progress_tokens_hint(tmp_path, capsys):
    j = journal(tmp_path, "метрика: q=8 [источник: a]")
    s = tmp_path / "stats.md"
    s.write_text("токены: вывод 10; вход без кэша 20; вход через кэш: чтение 30, запись 40\n", encoding="utf-8")
    out = run_p(capsys, j, "--stats", s)
    assert "числа из stats.md" in out and "в строку отрезка бери токены и стоимость отсюда" in out


def test_progress_real_003(capsys):
    base = Path(__file__).resolve().parent.parent / "runs" / "003"
    if not base.is_dir():
        pytest.skip("нет runs/003")
    out = run_p(capsys, base / "spec" / "journal.md")
    assert "0 -> 8" not in out and "ЦЕЛЬ ИЗМЕНЕНА" in out
    out = run_p(capsys, base / "app" / "journal.md")
    assert "НОЛЬ С ПЕРВОЙ" in out


# ---------------------------------------------------------------- доработки по проверке на истории ансамбля
def seg(n, name, v, src, was=None, tok=None):
    w = f" (было {was})" if was is not None else ""
    t = f", токены за отрезок={tok}" if tok is not None else ""
    return f"отрезок {n}: метрика {name}={v}{w} [источник: {src}]{t}"


def test_progress_verdict_by_current_metric(tmp_path, capsys):
    j = journal(tmp_path, "\n".join([
        seg(1, "старая", 100, "a"), seg(2, "старая", 100, "b", 100), seg(3, "старая", 100, "c", 100),
        seg(4, "новая", 80, "d"), seg(5, "новая", 60, "e", 80)]))
    out = run_p(capsys, j)
    assert "закрыта (переопределена)" in out
    assert out.strip().splitlines()[-1].startswith("вывод: идёт")
    assert out.count("ПЛАТО") == 0


def test_progress_was_positive_creates_step_for_first_point(tmp_path, capsys):
    out = run_p(capsys, journal(tmp_path, seg(1, "q", 90, "a", 100)))
    assert "шаг 1: 100 -> 90" in out
    for was in ("0", "N/A", "неизвестно"):
        out = run_p(capsys, journal(tmp_path, f"отрезок 1: метрика q=8 (было {was}) [источник: a]"))
        assert "шаг 1" not in out and "0 -> 8" not in out


def test_progress_plateau_needs_tokens(tmp_path, capsys):
    lines = lambda tok: "\n".join([seg(1, "q", 1000, "a", tok=0), seg(2, "q", 1000, "b", 1000, tok),
                                    seg(3, "q", 1000, "c", 1000, tok)])
    assert "ПЛАТО" not in run_p(capsys, journal(tmp_path, lines(20000)))
    assert "ПЛАТО" in run_p(capsys, journal(tmp_path, lines(30000)))
    assert "ПЛАТО" not in run_p(capsys, journal(tmp_path, lines(30000)), "--min-tokens", 100000)
    # токены неизвестны - порог выполнен
    j = journal(tmp_path, "\n".join([seg(1, "q", 1000, "a"), seg(2, "q", 1000, "b"), seg(3, "q", 1000, "c")]))
    assert "ПЛАТО" in run_p(capsys, j)


def test_progress_min_step(tmp_path, capsys):
    j = journal(tmp_path, "\n".join([seg(1, "q", 1000, "a"), seg(2, "q", 960, "b"), seg(3, "q", 925, "c")]))
    assert "ПЛАТО" not in run_p(capsys, j)  # 4 % и 3.6 % - не медленные при 0.035
    assert "ПЛАТО" in run_p(capsys, j, "--min-step", 0.05)
    j2 = journal(tmp_path, "\n".join([seg(1, "q", 10, "a"), seg(2, "q", 10, "b"), seg(3, "q", 10, "c")]))
    assert "ПЛАТО" in run_p(capsys, j2, "--min-step", 0.0)  # правило «меньше 20» не меняется


def test_progress_jump_flag(tmp_path, capsys):
    j = journal(tmp_path, "\n".join([seg(1, "q", 100, "a"), seg(2, "q", 50, "b"), seg(3, "q", 45, "c")]))
    out = run_p(capsys, j)
    assert "СКАЧОК" in out and out.strip().splitlines()[-1].startswith("вывод: идёт")
    out = run_p(capsys, journal(tmp_path, "\n".join([seg(1, "q", 10, "a"), seg(2, "q", 5, "b")])))
    assert out.strip().splitlines()[-1] == "вывод: скачок - проверь учёт, прежде чем считать прогрессом."
    out = run_p(capsys, journal(tmp_path, "\n".join([seg(1, "q", 100, "a"), seg(2, "q", 60, "b")])))
    assert "СКАЧОК" not in out  # ровно 40 % - не скачок
