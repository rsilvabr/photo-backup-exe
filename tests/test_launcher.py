"""The launcher's routing and the environment it gives the scripts.

    python -m pytest tests/test_launcher.py
"""
import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
import photo_backup_exe as exe   # noqa: E402

SCRIPTS = ["photo_backup.py", "selective_backup.py", "manifest_backup.py",
           "restore_backup.py", "captureone_backup.py"]


@pytest.fixture
def app(tmp_path, monkeypatch):
    root = tmp_path / "伊豆沼 [app] 100% & co"
    (root / "scripts").mkdir(parents=True)
    for name in SCRIPTS:
        (root / "scripts" / name).write_text("", encoding="utf-8")
    monkeypatch.setattr(exe, "APP", root)
    monkeypatch.setattr(exe, "SCRIPTS", root / "scripts")
    monkeypatch.delenv("PHOTOBACKUP_LOG_DIR", raising=False)
    monkeypatch.setattr(sys, "path", list(sys.path))
    return root


@pytest.mark.parametrize("name, script", [
    ("backup", "selective_backup.py"),
    ("MANIFEST", "manifest_backup.py"),
    ("restore", "restore_backup.py"),
    ("captureone", "captureone_backup.py"),
])
def test_a_backend_by_name(app, name, script):
    path, args = exe._resolve([name, "--source", r"G:\伊豆沼 [FINAL]", "--dry-run"])
    assert path == app / "scripts" / script
    assert args == ["--source", r"G:\伊豆沼 [FINAL]", "--dry-run"]


@pytest.mark.parametrize("script", SCRIPTS[1:])
def test_the_menu_starts_a_backend_by_its_path(app, script):
    """photo_backup.py runs [sys.executable, <scripts>\\x.py, ...]."""
    full = str(app / "scripts" / script)
    path, args = exe._resolve([full, "--dest", r"H:\BACKUP", "--yes"])
    assert path == Path(full).resolve()
    assert args == ["--dest", r"H:\BACKUP", "--yes"]


def test_a_script_outside_the_package_is_refused(app, tmp_path):
    other = tmp_path / "evil.py"
    other.write_text("", encoding="utf-8")
    with pytest.raises(SystemExit) as e:
        exe._resolve([str(other)])
    assert "not one of the bundled scripts" in str(e.value.code)


def test_a_missing_bundled_script_is_refused(app):
    with pytest.raises(SystemExit):
        exe._resolve([str(app / "scripts" / "mobile_backup.py")])


@pytest.mark.parametrize("argv", [[], ["--run-preset", "NIGHTLY"], ["--list-presets"],
                                  ["--help"], ["--version"]])
def test_everything_else_goes_to_the_menu(app, argv):
    assert exe._resolve(argv) == (app / "scripts" / "photo_backup.py", argv)


def test_the_menu_runs_with_its_arguments(app, monkeypatch):
    seen = {}
    monkeypatch.setattr(exe.runpy, "run_path",
                        lambda path, run_name: seen.update(path=path, argv=list(sys.argv),
                                                           run_name=run_name))
    monkeypatch.setattr(sys, "argv", ["photo-backup.exe", "--run-preset", "NIGHTLY H"])
    exe.main()
    menu = str(app / "scripts" / "photo_backup.py")
    assert seen == {"path": menu, "argv": [menu, "--run-preset", "NIGHTLY H"],
                    "run_name": "__main__"}


def test_the_logs_go_to_localappdata(app, monkeypatch, tmp_path):
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "local"))
    exe._setup_environment()
    assert os.environ["PHOTOBACKUP_LOG_DIR"] == str(tmp_path / "local" / "photo-backup" / "Logs")
    assert sys.path[0] == str(app / "scripts")


def test_a_log_dir_already_set_is_kept(app, monkeypatch):
    monkeypatch.setenv("PHOTOBACKUP_LOG_DIR", r"D:\my logs")
    exe._setup_environment()
    assert os.environ["PHOTOBACKUP_LOG_DIR"] == r"D:\my logs"
