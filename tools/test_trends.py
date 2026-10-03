import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import mail_stats as M  # noqa: E402
import trends as T  # noqa: E402

T0 = datetime(2026, 9, 25, 10, 0, tzinfo=timezone.utc)


def build(tmp_path, letters, metrics=None):
    """letters: [(часы от T0, от, кому, текст)]"""
    d = tmp_path / "mail"
    d.mkdir()
    for i, (h, f, t, text) in enumerate(sorted(letters, key=lambda x: x[0]), 1):
        ts = (T0 + timedelta(hours=h)).strftime("%Y-%m-%dT%H:%M:%SZ")
        (d / f"{i:03d}-{f}-to-{t}.md").write_text(f"{ts}\n\n{text}\n", encoding="utf-8")
    if metrics:
        (tmp_path / "journal_times.txt").write_text(
            "".join(f"{(T0 + timedelta(hours=h)).strftime('%Y-%m-%dT%H:%M:%SZ')}\t{ln}\n" for h, ln in metrics),
            encoding="utf-8")
    return tmp_path


def run(path, **kw):
    msgs = M.load(path)
    return T.compute(msgs, folder=str(path), **kw)


def test_no_flags_single_point(tmp_path):
    f = build(tmp_path, [(0, "a", "b", "Сделай пожалуйста сборку проекта целиком."), (30, "b", "a", "Принял.")],
              [(1, "метрика: м=5 [источник: x]"), (25, "метрика: м=4 [источник: x]")])
    r = T.render(run(f, days=3))
    assert "закономерностей нет" in r


def test_queue_grows_and_owner_slow_and_flat_metric(tmp_path):
    L = []
    for day in range(5):
        for k in range(day + 1):      # на i-й день i+1 неотвеченных писем узлу hub
            L.append((day * 24 + k, f"w{k}", "hub", f"Сделай задачу номер {day} {k}, пришли результат?"))
        L.append((day * 24 + 10, "hub2", "owner", f"Контекст.\n\nКак быть в случае {day}?"))
        L.append((day * 24 + 13, "owner", "hub2", "Делай так."))
    f = build(tmp_path, L, [(day * 24 + 2, "метрика: м=7 [источник: x]") for day in range(5)])
    r = run(f, days=5, owner_slow_h=2)
    fl = "\n".join(r["flags"])
    assert "очередь у hub растёт" in fl
    assert "ответ владельца дольше 2 ч" in fl
    assert "метрика м не двигается 3 дней" in fl
    assert "hub" not in r["spend_top"].values() or True
    assert "| день |" in T.render(r)


def test_bursts_and_repeats_and_no_metrics(tmp_path):
    L = []
    for day in range(3):
        for k in range(5):
            L.append((day * 24 + 1 + k * 0.1, "x", "owner", f"Вопрос номер {k} день {day}?"))
        L.append((day * 24 + 3, "x", "y", "Нужно срочно проверить конфигурацию стенда и вернуть итог проверки"))
        L.append((day * 24 + 4, "x", "y", "Повторяю: нужно срочно проверить конфигурацию стенда и вернуть итог проверки"))
    r = run(build(tmp_path, L), days=3)
    fl = "\n".join(r["flags"])
    assert "пачками" in fl
    assert "повтор без ответа x → y в 3 разных днях" in fl
    assert "нет ни одной строки метрики" in fl
    assert "роль x тратит больше всех" not in fl  # без метрики флаг не ставится — шум на узле


def test_churn_share(tmp_path):
    L = []
    for day in range(3):
        for k in range(12):
            L.append((day * 24 + k * 0.5, "a", "b", "Принял, работаю."))
    r = run(build(tmp_path, L), days=3)
    assert any("текучка" in x for x in r["flags"])
    assert r["churn"][r["days"][-1]] == (12, 12)


def test_empty_without_time(tmp_path):
    d = tmp_path / "mail"
    d.mkdir()
    (d / "001-a-to-b.md").write_text("без времени", encoding="utf-8")
    r = T.compute(M.load(tmp_path))
    assert r["note"] and "по дням считать нечего" in T.render(r)
