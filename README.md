# photo-backup-exe — photo-backup as a Windows program

[photo-backup](https://github.com/rsilvabr/photo-backup) packaged as
`photo-backup.exe`: no Python to install. Unzip and run.

> **If you can use Python, use the Python version.**
> [photo-backup](https://github.com/rsilvabr/photo-backup) itself is what its
> author runs on their own photo archive, so it is by far the more tested of
> the two. The program here is a newer way of packaging the same scripts,
> meant for people who would rather not install Python.

**Current version: v0.12.0-exe1** (2026-11-10) · packages photo-backup
[v0.12.0](https://github.com/rsilvabr/photo-backup/releases/tag/v0.12.0) ·
[All releases](docs/version_history.md) · [How it works](docs/how_it_works.md) ·
[Bug tracking](docs/bug_tracking.md)

---

## Contents

- [What it is](#what-it-is)
- [Download and first run](#download-and-first-run) · [Verifying a download](#verifying-a-download)
- [Command line](#command-line)
- [Where settings, presets and logs go](#where-settings-presets-and-logs-go)
- [Changing a setting](#changing-a-setting)
- [Updating and removing](#updating-and-removing)
- [What is in the folder](#what-is-in-the-folder)
- [Good to know](#good-to-know)
- [Testing](#testing)
- [Building from source](#building-from-source)
- [License](#license) · [Acknowledgments](#acknowledgments)

---

## What it is

photo-backup is a selective backup for photographers' archives: it backs up
the photos you exported — the exports, the RAW / camera JPEG / edited TIFF
and sidecars they came from, and your Capture One and NX Studio edits — and
leaves the outtakes behind. The source is read-only and nothing on the
destination is ever deleted. Everything it does is described in its own
[README](https://github.com/rsilvabr/photo-backup#readme); this repository
only packages it:

- The menu (`photo_backup.py`) and the four scripts it starts
  (`selective_backup.py`, `manifest_backup.py`, `restore_backup.py`,
  `captureone_backup.py`) are **byte-for-byte** those of the photo-backup
  release named above, with the modes table (`backup_modes.csv`) and the
  example manifest. No feature is added or removed.
- A small launcher starts them and sends the logs to your user folder
  ([below](#where-settings-presets-and-logs-go)).
- Each version of this package names the photo-backup version it carries
  (`v0.12.0-exe1` = photo-backup v0.12.0, first package of it).

Not included: `mobile_backup.py`, a separate tool that the menu does not
start and that needs ExifTool.

## Download and first run

1. Download `photo-backup-<version>-x64.zip` from
   [Releases](https://github.com/rsilvabr/photo-backup-exe/releases).
2. Unzip it to a folder of your own, for example `D:\Programs\photo-backup`.
   Do not run it from inside the zip.
3. Double-click **`photo-backup.exe`**. The menu opens in a console window
   and asks what to back up and where to.

The first time, Windows SmartScreen may say *"Windows protected your PC"*:
the program is not code-signed. Choose **More info → Run anyway**.

## Verifying a download

Releases are built by GitHub Actions from the tagged code
([workflow](.github/workflows/release.yml)), not on the author's PC, and
GitHub records a build attestation for the zip and `photo-backup.exe`. With
the [GitHub CLI](https://cli.github.com/):

```
gh attestation verify photo-backup-0.12.0-exe1-x64.zip --repo rsilvabr/photo-backup-exe
```

It names the commit and the workflow run the file came from, and fails for a
file that was not built there.

## Command line

From a terminal (`cmd` or PowerShell) in the program's folder:

```
photo-backup.exe                                  the interactive menu
photo-backup.exe --run-preset "NIGHTLY H"         a preset saved in the menu, unattended
photo-backup.exe --list-presets
photo-backup.exe backup     --source G:\2025 --dest H:\PHOTO_BACKUP --dry-run   (selective_backup.py)
photo-backup.exe manifest   --manifest D:\backup_manifest.csv --analyze        (manifest_backup.py)
photo-backup.exe restore    --backup H:\PHOTO_BACKUP --to D:\Restored          (restore_backup.py)
photo-backup.exe captureone --dest H:\PHOTO_BACKUP                             (captureone_backup.py)
```

Each `backup`/`manifest`/`restore`/`captureone` line takes exactly what the
matching script takes: photo-backup's documentation applies word for word —
replace `python selective_backup.py` with `photo-backup.exe backup`, and so
on. Exit codes are the scripts' own (0 = everything fine, 1 = problems
found, 2 = refused before starting).

Where photo-backup's menu or its files print a `python <script>.py` command
line (the hint after saving a preset, `WHERE_EACH_FOLDER_GOES.txt` in a
Capture One backup), use the line above instead.

A preset can be run from a scheduled task or a shortcut:

```
"D:\Programs\photo-backup\photo-backup.exe" --run-preset "NIGHTLY H"
```

## Where settings, presets and logs go

| What | Where |
|---|---|
| Remembered choices and presets | `%USERPROFILE%\.photo_backup_config.json` — the same file the Python version uses, so both see the same presets. A preset holds only the choices (sources, destination, formats, ...), never a script path: it runs the scripts of the program that starts it |
| Logs | `%LOCALAPPDATA%\photo-backup\Logs` (the Python version writes them to `Logs\` next to its scripts). Set `PHOTOBACKUP_LOG_DIR` to send them elsewhere |
| The backup itself | where you point it: the catalog lives in `_photo_backup\` on the destination, and is the same for both versions — a backup made by one is continued, verified and restored by the other |
| Your manifest | anywhere you like. The menu suggests `scripts\backup_manifest.csv` in the program folder; a manifest outside the program folder survives an update into a new folder untouched |

Nothing goes to the Windows registry.

## Changing a setting

photo-backup keeps every setting at the top of its scripts
(`SPACE_MARGIN_GB`, `EXPORT_FORMATS`, ... in `selective_backup.py`). In the
program they are in `scripts\selective_backup.py` and the other files of
`scripts\`: open one in a text editor (Notepad is fine), change the value,
save. The program runs those files, so the change applies from the next
start. Keep a note of what you changed: an update brings the files of the
new release.

## Updating and removing

- **Update:** unzip the new version over the old folder, or into a new one.
  Presets and the logs are kept either way; settings you edited in
  `scripts\` are replaced by the release's (see above), and a manifest kept
  in `scripts\` must be copied across to a new folder.
- **Remove:** delete the folder. The settings file and the logs stay in the
  places above until you delete them too. Your backups are never touched.

## What is in the folder

| Path | What |
|---|---|
| `photo-backup.exe`, `_internal\` | Python 3.12 and the library the menu uses for colours (rich) |
| `scripts\` | The photo-backup menu and its four scripts, unchanged, with `backup_modes.csv` and `backup_manifest.example.csv` |
| `licenses\` | The licenses of everything above, Python's included |

photo-backup calls no outside program except two that are part of Windows
(`tasklist`, to see whether Capture One is open; `robocopy`, only inside the
`RESTORE_CAPTUREONE.cmd` it writes into a backup).

## Good to know

- **Antivirus:** some engines flag unsigned programs built with PyInstaller.
  This package uses the one-folder layout, the one they object to least; if
  yours quarantines a file, restore it and add the folder as an exception.
- **Size:** about 25 MB unzipped (12 MB zipped).
- **Speed:** the copy runs exactly as fast as with Python (the same scripts
  do it).
- **Paths:** folders with Japanese or Portuguese names, brackets, spaces,
  `%`, `&` and paths past 260 characters are supported and tested, for the
  photos, the backup and the program's own folder.
- **No network:** the program reads the folders you point it at and writes
  only to the destination you choose and its own log folder.
- **Bugs:** a problem with what photo-backup *does* (what is selected, a
  copy, a verify, a restore) belongs in
  [photo-backup's issues](https://github.com/rsilvabr/photo-backup/issues);
  a problem with the program itself (it does not start, a script is missing)
  belongs [here](https://github.com/rsilvabr/photo-backup-exe/issues).

## Testing

`python tests/test_launcher.py` (pytest) checks the launcher's routing.
`python tests/battery_on_exe.py` drives the built program end to end, with
**no Python on `PATH`**, from a copy in a folder named
`伊豆沼 [app] 100% & co` whose files all carry the "downloaded from the
internet" mark, as after unzipping a download in Explorer:

- each script by name, and a `.py` outside the package refused;
- a backup of a synthetic archive (Nikon, Canon and film-scan names, an
  export folder, Capture One and NX Studio edits, outtakes, Japanese and
  Portuguese paths, `～`, `%`) to a destination whose paths pass 260
  characters: dry-run, copy, re-run, `--verify full`, restore, every byte
  compared, and the source tree unchanged byte for byte;
- a manifest (`--analyze`, copy, `--verify`), Capture One's own files
  (backup, verify, restore) on fake Capture One folders;
- the menu: started with no input, a preset run unattended (the menu starts
  each script through `photo-backup.exe` itself);
- a setting edited in `scripts\selective_backup.py` reaching the scripts
  that import it, and where the logs go;
- with `--real <folder>`, a dry-run (read-only) on a real photo folder.

Each release runs it against the zip GitHub built, before the release is
published; the release notes give the result.

## Building from source

Needs Python 3.12 on `PATH` and an internet connection:

```
python build.py
```

It creates a virtual environment in `.venv` (pinned packages and
PyInstaller), downloads the photo-backup tag, and writes
`dist\photo-backup-<version>-x64\` plus its zip. The photo-backup tag is a
setting at the top of `build.py`. Releases run the same `build.py` on GitHub
Actions when a `v*-exe*` tag is pushed.
Details: [How it works](docs/how_it_works.md).

## License

MIT for this packaging (see [LICENSE](LICENSE)). The package also contains
photo-backup (MIT) and Python with rich (PSF and MIT). They are listed in
`licenses\` and in the PyInstaller-collected notices under `_internal\`.

## Acknowledgments

- [PyInstaller](https://pyinstaller.org), which makes the Python program a
  Windows one
- [Claude](https://www.anthropic.com/claude) (Anthropic), among other AI tools,
  for code assistance, reviews and technical discussion
