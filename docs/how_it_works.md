# How it works

## One program, a menu and four scripts

photo-backup is a menu (`photo_backup.py`) and four scripts it starts as
separate processes: `selective_backup.py` (the backup, the verify and every
safety rule), `manifest_backup.py` (a mode per folder), `restore_backup.py`
and `captureone_backup.py`. The menu starts a script as
`[sys.executable, <script>.py, ...]`, and the scripts import
`selective_backup.py` from their own folder (`import selective_backup as sb`).

The launcher (`src/photo_backup_exe.py`) routes its command line:

| Command line | Runs |
|---|---|
| `photo-backup.exe [options]` | `scripts\photo_backup.py` (the menu), through `runpy` as `__main__`, exactly as `python photo_backup.py` would run it |
| `photo-backup.exe backup\|manifest\|restore\|captureone ...` | `scripts\selective_backup.py`, `manifest_backup.py`, `restore_backup.py` or `captureone_backup.py`, the same way |
| `photo-backup.exe <scripts>\<name>.py ...` | that script. In the program `sys.executable` is `photo-backup.exe`, so this is how the menu's `[sys.executable, script, ...]` reaches a script. Only the files of `scripts\` are accepted: this is not a general Python launcher |

The menu finds its scripts next to itself (`scripts\`), so nothing in
photo-backup is modified.

## Python and its libraries

PyInstaller builds a one-folder program: `photo-backup.exe` plus
`_internal\` with Python 3.12, rich and every standard-library module the
scripts import (`sqlite3` for the catalog among them). To find those modules
the build analyses the five scripts as modules (`hiddenimports` in
`photo-backup.spec`) and collects rich completely.

The scripts themselves are then removed from the program (`a.pure` in the
spec): the `.py` files in `scripts\` are the only copy. photo-backup keeps
every setting at the top of its scripts and the owner is expected to edit
them; with a second, frozen copy inside the program, an edit could be
ignored by the scripts that `import selective_backup`. The launcher also
puts `scripts\` first on `sys.path`. A control build without the filter
showed the `.py` already winning through that order; the filter keeps it so
whatever the import order. The battery edits `SPACE_MARGIN_GB` in the
program's `scripts\selective_backup.py` and checks that both
`backup --help` and `manifest --help` show the new value.

## Logs

The scripts write their logs to `PHOTOBACKUP_LOG_DIR`, or to `Logs\` next to
themselves when it is not set. Next to themselves would be the program
folder, which an update replaces or which may not be writable, and a backup
refuses to start without a log. So the launcher sets `PHOTOBACKUP_LOG_DIR` to
`%LOCALAPPDATA%\photo-backup\Logs` unless it is already set; every script
the menu starts inherits it.

## Settings and presets

The menu keeps its choices and presets in
`%USERPROFILE%\.photo_backup_config.json` (or `PHOTOBACKUP_CONFIG`), the
file the Python version uses. A preset stores the choices only, never the
path of a script, so a preset saved by either version runs the scripts of
whichever program starts it.

## The build

`build.py`:

1. creates `.venv` with the pinned packages (rich) and PyInstaller;
2. downloads the photo-backup tag `PHOTOBACKUP_TAG` from GitHub, takes the
   five scripts, `backup_modes.csv`, `backup_manifest.example.csv` and the
   license, and checks that the `__version__` of every script matches the
   tag;
3. runs PyInstaller with `photo-backup.spec` (the Windows version
   information is written from the tag);
4. assembles `dist\photo-backup-<version>-exe<N>-x64\` and zips it.

`python build.py --scripts-from <photo-backup checkout>` takes the scripts
from a local folder instead of the tag, for a test build before a tag
exists; the version check still applies. Releases never use it.

Packaging a new photo-backup release: change `PHOTOBACKUP_TAG` (and set
`PACKAGE_REVISION` back to 1), push a `vX.Y.Z-exe1` tag (GitHub Actions
builds the zip with an attestation and creates a draft release), run
`tests/battery_on_exe.py --app` on that zip, unzipped; publish only when
every check passes.
