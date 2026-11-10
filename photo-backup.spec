# PyInstaller spec for photo-backup.exe (a one-folder build). Run through
# build.py, which first puts the photo-backup scripts in build/app/scripts.
import os
from PyInstaller.utils.hooks import collect_all

SCRIPTS = os.path.join("build", "app", "scripts")

# The scripts are analysed as modules so PyInstaller bundles everything they
# use (rich and the standard library, sqlite3 and their function-level imports
# included). The scripts themselves are then taken OUT of the program: they
# ship as plain .py files in scripts/, and that is the only copy. They import
# each other (`import selective_backup as sb`) and the owner edits the
# settings at their top: with a second, frozen copy inside the program, an
# edit could be silently ignored. The launcher puts scripts/ first on
# sys.path, which already makes the .py win (checked with a build without this
# filter, 2026-11-10); the filter keeps it true whatever the import order.
SCRIPT_MODULES = ["photo_backup", "selective_backup", "manifest_backup",
                  "restore_backup", "captureone_backup"]
hidden = list(SCRIPT_MODULES)
datas, binaries = [], []
d, b, h = collect_all("rich")
datas += d
binaries += b
hidden += h

a = Analysis(
    [os.path.join("src", "photo_backup_exe.py")],
    pathex=[SCRIPTS],
    binaries=binaries,
    datas=datas,
    hiddenimports=hidden,
    excludes=["tkinter", "matplotlib", "IPython", "pytest", "numpy"],
)
a.pure = [entry for entry in a.pure if entry[0] not in SCRIPT_MODULES]
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name="photo-backup",
          console=True, version=os.path.join("build", "version_info.txt"),
          icon=None, upx=False)
coll = COLLECT(exe, a.binaries, a.datas, name="photo-backup", upx=False)
