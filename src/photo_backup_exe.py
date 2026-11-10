"""photo-backup.exe: photo-backup as a Windows program, no Python needed.

The photo-backup scripts ship unchanged in `scripts/` next to the program.
This launcher only routes:

    photo-backup.exe                           the interactive menu (photo_backup.py)
    photo-backup.exe --run-preset NAME ...     the menu, with its own options
    photo-backup.exe backup|manifest|restore|captureone ARGS
                                               one backend directly
    photo-backup.exe <scripts>\\<name>.py ARGS
                                               how the menu starts a backend: it
                                               runs [sys.executable, script, ...],
                                               and sys.executable is this program

Before running anything it sends the logs, unless PHOTOBACKUP_LOG_DIR is set,
to %LOCALAPPDATA%\\photo-backup\\Logs instead of the program folder.
"""

import os
import runpy
import sys
from pathlib import Path

BACKENDS = {
    "backup": "selective_backup.py",
    "manifest": "manifest_backup.py",
    "restore": "restore_backup.py",
    "captureone": "captureone_backup.py",
}
MENU = "photo_backup.py"


def _app_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent / "build" / "app"


APP = _app_dir()
SCRIPTS = APP / "scripts"


def _setup_environment() -> None:
    if not os.environ.get("PHOTOBACKUP_LOG_DIR"):
        base = Path(os.environ.get("LOCALAPPDATA") or Path.home())
        os.environ["PHOTOBACKUP_LOG_DIR"] = str(base / "photo-backup" / "Logs")
    # The scripts import each other (`import selective_backup as sb`): the
    # copies in scripts\ are the only ones (the build leaves them out of the
    # program itself), so an edit of their settings is what runs.
    sys.path.insert(0, str(SCRIPTS))


def _resolve(argv):
    """(script path, remaining arguments) for this command line."""
    if argv:
        first = argv[0]
        if first.lower() in BACKENDS:
            return SCRIPTS / BACKENDS[first.lower()], argv[1:]
        if first.lower().endswith(".py"):
            script = Path(first).resolve()
            # Only the bundled scripts: this is not a general Python launcher.
            if script.parent == SCRIPTS.resolve() and script.is_file():
                return script, argv[1:]
            sys.exit(f"photo-backup: not one of the bundled scripts: {first}")
    return SCRIPTS / MENU, argv


def main() -> None:
    # A redirected stdout falls back to the ANSI code page, where a path in
    # Japanese cannot be printed (the scripts do the same).
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass
    _setup_environment()
    script, args = _resolve(sys.argv[1:])
    sys.argv = [str(script)] + list(args)
    runpy.run_path(str(script), run_name="__main__")


if __name__ == "__main__":
    main()
