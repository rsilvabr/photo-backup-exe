# Bug tracking

Bugs of the **packaging** — the launcher, the build — newest first, one
numbered row each. A bug in what photo-backup itself does belongs to
[photo-backup's issues](https://github.com/rsilvabr/photo-backup/issues),
even when it was found while testing this program: those are listed at the
end of a round for reference, and reach this package with the photo-backup
release that fixes them.

**Next free number: #1.**

| Round | Date | Shipped in | Bugs |
|---|---|---|---|
| [Round 0 — the first package](#round-0--the-first-package-2026-11-10) | 2026-11-10 | v0.12.0-exe1 | none |

---

## Round 0 — the first package (2026-11-10)

The launcher follows jxl-photo-exe's and tiff-workflow-exe's, and three
things were handled before the first build:

- The menu starts each script as `[sys.executable, script.py, ...]`; in the
  program `sys.executable` is `photo-backup.exe`, so the launcher runs a
  `.py` of its own `scripts\` folder given as the first argument (and refuses
  any other).
- The scripts write their logs next to themselves by default, which would
  be the program folder: the launcher sends them to
  `%LOCALAPPDATA%\photo-backup\Logs`.
- The scripts are left out of the program itself, so an edit of a setting
  in `scripts\selective_backup.py` cannot be overridden by a frozen copy
  ([How it works](how_it_works.md#python-and-its-libraries)).

The battery's first run had one failure, in the battery itself: its
"folder not exported yet" was named `251224_not exported yet`, and any folder
whose name contains "export" is an export folder for photo-backup, as
designed. Renamed.
