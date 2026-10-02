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
        "метрика: ошибки=98 [источник: a]",
        "метрика: ошибки=97 [источник: a]",
    ]))
    out = run_p(capsys, p)
    assert "ПЛАТО" in out and "плато - требуй смены способа" in out
    p2 = journal(tmp_path, "метрика: м=10 [источник: a]\nметрика: м=10 [источник: a]\nметрика: м=10 [источник: a]\n")
    assert "ПЛАТО" in run_p(capsys, p2)
    p3 = journal(tmp_path, "метрика: м=10 [источник: a]\nметрика: м=9 [источник: a]\nметрика: м=8 [источник: a]\n")
    assert "ПЛАТО" not in run_p(capsys, p3)


def test_progress_growth(tmp_path, capsys):
    p = journal(tmp_path, "метрика: м=10 [источник: a]\nметрика: м=15 [источник: a]\n")
    out = run_p(capsys, p)
    assert "РОСТ" in out and "выясни причину" in out


def test_progress_goal_and_target(tmp_path, capsys):
    p = journal(tmp_path, "метрика: м=10 [источник: a]\nметрика: м=3 [источник: a]\n")
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
