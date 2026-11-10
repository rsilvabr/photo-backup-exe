# Version history

A package version names the photo-backup release it carries: `v0.12.0-exe1`
is the first package of photo-backup v0.12.0. What changed in photo-backup
itself is in [its version history](https://github.com/rsilvabr/photo-backup/blob/main/docs/version_history.md).

| Version | Date | photo-backup | Highlights |
|---------|------|--------------|------------|
| **[v0.12.1-exe1](#v0121-exe1)** | 2026-11-11 | v0.12.1 | photo-backup v0.12.1 |
| [v0.12.0-exe1](#v0120-exe1) | 2026-11-10 | v0.12.0 | First package |

---

## v0.12.1-exe1

*2026-11-11*

- Packages photo-backup
  [v0.12.1](https://github.com/rsilvabr/photo-backup/releases/tag/v0.12.1)
  (a bug sweep: every file under a source is in the plan or counted, a bigger
  mode never copies less, a source that cannot be read is not a source that is
  gone, a destination that stops taking writes stops the backup). The launcher
  and the build are unchanged.

## v0.12.0-exe1

*2026-11-10*

- First package: photo-backup
  [v0.12.0](https://github.com/rsilvabr/photo-backup/releases/tag/v0.12.0)
  as `photo-backup.exe`, built by GitHub Actions with a build attestation.
- `photo-backup.exe` opens the menu; `--run-preset` / `--list-presets` work
  as in the Python version, and `backup`, `manifest`, `restore` and
  `captureone` run one script directly.
- The logs go to `%LOCALAPPDATA%\photo-backup\Logs`.
