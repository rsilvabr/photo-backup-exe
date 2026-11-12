"""Builds dist/photo-backup-<version>-x64.zip: photo-backup.exe and the scripts
of a published photo-backup tag.

    python build.py            (Python 3.12 on PATH; first run ~2 minutes)

Everything downloaded is pinned: the photo-backup scripts come from the tag
below (the `__version__` of each script must match it). A virtual environment
in .venv holds the pinned Python packages and PyInstaller, so the system
Python is not touched. photo-backup calls no outside tool (robocopy and
tasklist are part of Windows), so nothing else is bundled.

    python build.py --scripts-from <folder>

takes the scripts from a local photo-backup checkout instead of the tag (a
test build before the tag exists; the versions must still match it).
Releases never use it.
"""

import os
import re
import shutil
import subprocess
import sys
import urllib.request
import zipfile
from pathlib import Path

# --- settings --------------------------------------------------------------
PHOTOBACKUP_TAG = "v0.13.2"
# Package revision for this photo-backup tag: v0.13.2 + 1 -> release "v0.13.2-exe1".
PACKAGE_REVISION = 1
REQUIREMENTS = ["rich==15.0.0", "pyinstaller==6.22.2"]
# ---------------------------------------------------------------------------

ROOT = Path(__file__).resolve().parent
DEPS, BUILD, DIST = ROOT / "deps", ROOT / "build", ROOT / "dist"
VENV = ROOT / ".venv"
# The menu and the four backends it starts, each with `__version__`. Left out:
# mobile_backup.py (a separate tool, not reached from the menu, that needs
# ExifTool) and the tests.
SCRIPT_NAMES = ["photo_backup.py", "selective_backup.py", "manifest_backup.py",
                "restore_backup.py", "captureone_backup.py"]
# Read by the scripts from their own folder: the modes table and the example
# manifest the README points at.
DATA_NAMES = ["backup_modes.csv", "backup_manifest.example.csv"]


def rmtree(path):
    """shutil.rmtree that also removes read-only files."""
    def _clear(func, p, _exc):
        os.chmod(p, 0o666)
        func(p)
    shutil.rmtree(path, onexc=_clear)


def step(msg):
    print(f"\n== {msg}", flush=True)


def fetch(url, dest):
    if not dest.exists():
        print(f"   downloading {url}")
        DEPS.mkdir(exist_ok=True)
        with urllib.request.urlopen(url, timeout=300) as r:
            data = r.read()
        dest.write_bytes(data)
    return dest


def venv_python():
    py = VENV / "Scripts" / "python.exe"
    if not py.exists():
        step("Python environment (.venv)")
        subprocess.run([sys.executable, "-m", "venv", str(VENV)], check=True)
    subprocess.run([str(py), "-m", "pip", "install", "--quiet", "--disable-pip-version-check"]
                   + REQUIREMENTS, check=True)
    return py


def get_scripts(app, local=None):
    dest = app / "scripts"
    dest.mkdir(parents=True)
    out_license = app / "licenses" / "LICENSE.photo-backup"
    names = SCRIPT_NAMES + DATA_NAMES
    if local:
        step(f"photo-backup scripts from {local} (test build, not the tag)")
        for name in names:
            shutil.copy2(Path(local) / name, dest / name)
        shutil.copy2(Path(local) / "LICENSE", out_license)
    else:
        step(f"photo-backup {PHOTOBACKUP_TAG} scripts")
        z = fetch(f"https://github.com/rsilvabr/photo-backup/archive/refs/tags/"
                  f"{PHOTOBACKUP_TAG}.zip", DEPS / f"photo-backup-{PHOTOBACKUP_TAG}.zip")
        with zipfile.ZipFile(z) as zf:
            top = zf.namelist()[0].split("/")[0]
            for name in names:
                (dest / name).write_bytes(zf.read(f"{top}/{name}"))
            out_license.write_bytes(zf.read(f"{top}/LICENSE"))
    version = PHOTOBACKUP_TAG.lstrip("v")
    for name in SCRIPT_NAMES:
        text = (dest / name).read_text(encoding="utf-8")
        m = re.search(r'^__version__ = "([^"]+)"', text, re.M)
        if not m or m.group(1) != version:
            sys.exit(f"{name}: __version__ {m and m.group(1)} != tag {PHOTOBACKUP_TAG}")
    return version


def version_info(version):
    nums = (version.split(".") + ["0", "0", "0"])[:3] + ["0"]
    (BUILD / "version_info.txt").write_text(f"""VSVersionInfo(
  ffi=FixedFileInfo(filevers=({','.join(nums)}), prodvers=({','.join(nums)})),
  kids=[StringFileInfo([StringTable('040904B0', [
    StringStruct('CompanyName', 'rsilvabr'),
    StringStruct('FileDescription', 'photo-backup - selective photo archive backup'),
    StringStruct('FileVersion', '{version}'),
    StringStruct('ProductName', 'photo-backup'),
    StringStruct('ProductVersion', '{version}'),
    StringStruct('LegalCopyright', 'MIT License')])]),
  VarFileInfo([VarStruct('Translation', [1033, 1200])])])
""", encoding="utf-8")


def main():
    local = None
    if "--scripts-from" in sys.argv[1:]:
        i = sys.argv.index("--scripts-from")
        if i + 1 >= len(sys.argv):
            sys.exit("--scripts-from needs a folder")
        local = sys.argv[i + 1]
    py = venv_python()
    if BUILD.exists():
        rmtree(BUILD)
    app = BUILD / "app"
    (app / "licenses").mkdir(parents=True)
    version = get_scripts(app, local)
    version_info(version)

    step("PyInstaller")
    subprocess.run([str(py), "-m", "PyInstaller", "--noconfirm", "--clean",
                    "--distpath", str(BUILD / "pyi_dist"), "--workpath", str(BUILD / "pyi_work"),
                    str(ROOT / "photo-backup.spec")], check=True, cwd=ROOT)

    step("assemble")
    out = DIST / f"photo-backup-{version}-exe{PACKAGE_REVISION}-x64"
    if out.exists():
        rmtree(out)
    old = out.parent / (out.name + ".zip")    # not with_suffix: the name has dots
    if old.exists():
        old.unlink()
    shutil.copytree(BUILD / "pyi_dist" / "photo-backup", out)
    for sub in ("scripts", "licenses"):
        shutil.copytree(app / sub, out / sub)
    shutil.copy2(ROOT / "LICENSE", out / "licenses" / "LICENSE.photo-backup-exe")
    # PyInstaller bundles the Python runtime but not its license (PSF).
    shutil.copy2(Path(sys.base_prefix) / "LICENSE.txt", out / "licenses" / "LICENSE.python.txt")
    shutil.copy2(ROOT / "README.md", out / "README.md")
    # No read-only files or folders in the package: an update unzips over the
    # old folder, and a copy must be deletable.
    for f in out.rglob("*"):
        os.chmod(f, 0o666 if f.is_file() else 0o777)
    z = shutil.make_archive(str(out), "zip", out.parent, out.name)
    size = sum(f.stat().st_size for f in out.rglob("*") if f.is_file())
    print(f"\nBuilt {out} ({size / 1e6:.0f} MB) and {Path(z).name} "
          f"({Path(z).stat().st_size / 1e6:.0f} MB)")


if __name__ == "__main__":
    main()
