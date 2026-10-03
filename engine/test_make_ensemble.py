import json
import pathlib
import subprocess
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import make_ensemble as me  # noqa: E402

EX = pathlib.Path(__file__).resolve().parent / "examples"


def gen(tmp_path, name="tempconv-spec.toml", **over):
    spec = me.load_spec(EX / name)
    spec.update(over)
    me.generate(spec, tmp_path)
    return tmp_path / "runs" / spec["run"]


def test_layout_006(tmp_path):
    base = gen(tmp_path)
    for X in ("A1", "A2", "A3", "B1", "B2", "B3"):
        for f in ("TASK.md", "COMMON.md", "journal.md", "mail/.keep"):
            assert (base / X / f).exists()
    assert (base / "A1/control.md").exists()
    assert not (base / "B1/control.md").exists()
    assert (base / "SCHEDULE-A.md").exists() and (base / "SCHEDULE-B.md").exists()


def test_task_placeholders(tmp_path):
    t = (gen(tmp_path) / "B2/TASK.md").read_text(encoding="utf-8")
    assert "`out/006-B2/tempconv.md`" in t
    assert "{out}" not in t and "{X}" not in t
    assert "producer" not in t and "Компас" not in t


def test_compass_line(tmp_path):
    t = (gen(tmp_path, compass="specs/compass.md") / "A1/TASK.md").read_text(encoding="utf-8")
    assert "Компас проекта — specs/compass.md: что важно пользователям и правила компромиссов." in t


def test_owner_questions(tmp_path):
    off = (gen(tmp_path / "a") / "A1/COMMON.md").read_text(encoding="utf-8")
    on = (gen(tmp_path / "b", owner_questions=True) / "A1/COMMON.md").read_text(encoding="utf-8")
    assert "owner-questions" not in off
    assert ".claude/skills/owner-questions/SKILL.md" in on and "runs/006/A1/questions.md" in on


def test_accept_role(tmp_path):
    a = (gen(tmp_path) / "A1/COMMON.md").read_text(encoding="utf-8")
    b = (gen(tmp_path) / "B1/COMMON.md").read_text(encoding="utf-8")
    assert "когда продюсер пишет в журнал строку `ГОТОВО" in a
    assert "когда эксперт принял спецификацию и записал" in b
    spec = me.load_spec(EX / "tempconv-spec.toml")
    spec["accept_role"] = "expert"
    me.generate(spec, tmp_path / "x")
    c = (tmp_path / "x/runs/006/A1/COMMON.md").read_text(encoding="utf-8")
    assert "когда эксперт принял" in c


def test_budget_rounds(tmp_path):
    base = gen(tmp_path, budget_usd=2.5, max_rounds=8)
    c = (base / "A1/COMMON.md").read_text(encoding="utf-8")
    s = (base / "SCHEDULE-A.md").read_text(encoding="utf-8")
    assert "$2.5 и не больше 8 кругов" in c
    assert "«ИТОГО» > $2.5" in s and "кругов 2…8" in s and "прошло 8 кругов" in s


def test_schedule_order_and_checks(tmp_path):
    base = gen(tmp_path, "tempconv-app-spec.toml")
    a = (base / "SCHEDULE-A.md").read_text(encoding="utf-8")
    b = (base / "SCHEDULE-B.md").read_text(encoding="utf-8")
    assert "круга 1**: expert, tester, executor, producer, choreographer" in a
    assert "кругов 2…12**: producer, choreographer, tester, expert, executor" in a
    assert "в журналах tester, producer и choreographer есть Read их `SKILL.md`" in a
    assert "кругов 2…12**: tester, expert, executor" in b
    assert "в журнале tester есть Read его `SKILL.md`" in b
    assert "дай продюсеру и хореографу ход" in a and "дай продюсеру" not in b
    assert "python -m pytest out/007-X/tests -q" in a
    assert "sanitize_journal.py" in a and "ИТОГО" in a


def test_no_skilled_roles_no_check(tmp_path):
    spec = me.load_spec(EX / "tempconv-spec.toml")
    s = me.render_schedule(spec, spec["ensembles"][1])
    assert "проверка" not in s and "pytest" not in s
    assert "круга 1**: expert, executor." in s


def test_control_only_with_system_roles(tmp_path):
    base = gen(tmp_path)
    assert "Управление: control.md" in (base / "A1/COMMON.md").read_text(encoding="utf-8")
    assert "control.md" not in (base / "B1/COMMON.md").read_text(encoding="utf-8")


def test_json_spec(tmp_path):
    import tomllib
    d = tomllib.loads((EX / "tempconv-spec.toml").read_text(encoding="utf-8"))
    p = tmp_path / "s.json"
    p.write_text(json.dumps(d, ensure_ascii=False), encoding="utf-8")
    spec = me.load_spec(p)
    assert spec["run"] == "006" and len(spec["ensembles"]) == 2


@pytest.mark.parametrize("mut", [
    lambda s: s.pop("task"),
    lambda s: s["ensembles"][0]["roles"].append("ghost"),
    lambda s: s["roles"]["producer"].pop("skill"),
])
def test_bad_spec(mut):
    import tomllib
    d = tomllib.loads((EX / "tempconv-spec.toml").read_text(encoding="utf-8"))
    mut(d)
    with pytest.raises(me.SpecError):
        me.normalize(d)


def test_cli(tmp_path):
    r = subprocess.run([sys.executable, str(pathlib.Path(me.__file__)), str(EX / "tempconv-spec.toml"),
                        "--root", str(tmp_path)], capture_output=True, text=True)
    assert r.returncode == 0 and (tmp_path / "runs/006/A1/TASK.md").exists()
    r = subprocess.run([sys.executable, str(pathlib.Path(me.__file__)), str(tmp_path / "nope.toml")],
                       capture_output=True, text=True)
    assert r.returncode == 2


REPO = pathlib.Path(__file__).resolve().parent.parent


GOLDEN = pathlib.Path(__file__).resolve().parent / "golden" / "006"


def test_matches_run_006(tmp_path):
    # Эталон — тексты проверенного прогона 006 (engine/golden/006): генератор их воспроизводит.
    base = gen(tmp_path)
    for rel in ("A1/TASK.md", "A1/COMMON.md", "A1/control.md", "B1/TASK.md", "B1/COMMON.md",
                "SCHEDULE-A.md", "SCHEDULE-B.md"):
        want = (GOLDEN / rel).read_text(encoding="utf-8").replace("\r\n", "\n")
        assert (base / rel).read_text(encoding="utf-8") == want, rel
