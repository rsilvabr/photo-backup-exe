"""Drives the built photo-backup.exe end to end, without Python on PATH.

    python tests/battery_on_exe.py [--app <folder>] [--work <folder>]
                                   [--real <photo folder>] [--keep]

--app is the unzipped package (default: the newest folder in dist/). The
program runs from a copy in a HOSTILE folder (Japanese, brackets, a space, %
and &) whose files all carry the "downloaded from the internet" mark
(Zone.Identifier, ZoneId=3) that Explorer gives the files of a downloaded zip.

Every photo is SYNTHETIC, in --work (default: a folder in %TEMP%), except
--real: a real photo folder that only gets a --dry-run (read-only, nothing is
written next to it). Capture One's folders are fake ones in --work too
(PHOTOBACKUP_C1_*), and the settings file is a temp one (PHOTOBACKUP_CONFIG):
nothing of this PC's Capture One or presets is read or changed.

Checks: each backend by name, a backup / re-run / verify / restore round trip
with bytes compared, a destination path past 260 characters, a manifest
(analyze, copy, verify), Capture One's own files (backup, verify, restore),
the menu (closed stdin, a preset run unattended, which goes through the
menu's [sys.executable, script.py] route), an edit of a setting in
scripts\\selective_backup.py reaching the backends that import it, where the
logs go, and that the source tree is byte for byte the same afterwards.

The report lands in AI_tools/ of this repo.
"""

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MOTW = "[ZoneTransfer]\r\nZoneId=3\r\n"
HOSTILE = "伊豆沼 [app] 100% & co"


class Battery:
    def __init__(self):
        self.results, self.skips, self.section_name = [], [], ""

    def section(self, name):
        self.section_name = name
        print(f"\n== {name}", flush=True)

    def check(self, label, ok, detail=""):
        self.results.append((self.section_name, label, bool(ok), detail))
        print(f"   {'PASS' if ok else 'FAIL'}  {label}" + (f"  ({detail})" if detail and not ok else ""),
              flush=True)
        return ok


def _mark_downloaded(folder):
    n = 0
    for f in folder.rglob("*"):
        if f.is_file():
            with open(str(f) + ":Zone.Identifier", "w", encoding="ascii") as fh:
                fh.write(MOTW)
            n += 1
    return n


def _write(path, size):
    path.parent.mkdir(parents=True, exist_ok=True)
    name = path.name.encode("utf-8")
    path.write_bytes((name * (size // len(name) + 1))[:size])


def _tree(root):
    """A session with Nikon / AdobeRGB / Canon / scan names, an export folder,
    Capture One and NX Studio edits, outtakes, a folder without export, and
    paths with Japanese, Portuguese, brackets, `～` and `%`."""
    s = root / "2025" / "251223_São Luís [FINAL]" / "02_D200 ～ 伊豆沼 100%"
    files = {
        "DSC_9360.NEF": 300_000, "DSC_9360.JPG": 90_000, "DSC_9360.xmp": 400,
        "_DSC6489.NEF": 310_000, "_DSC6489.xmp": 410,
        "IMG_0014.CR2": 280_000, "000037.tif": 150_000,
        "_EXPORT/16B_JXL/DSC_9360_ProPhoto-g22_v1.jxl": 120_000,
        "_EXPORT/sRGB/_DSC6489_sRGB_v1.jpg": 60_000,
        "_EXPORT/WEB/IMG_0014.jpg": 30_000,
        "_EXPORT/WEB/000037.jpg": 30_000,
        "CaptureOne/Settings166/DSC_9360.NEF.cos": 5_000,
        "CaptureOne/Cache/Proxies/DSC_9360.NEF.cop": 50_000,
        "NKSC_PARAM/_DSC6489.NEF.nksc": 3_000,
        "_OUTTAKES/DSC_9361.NEF": 300_000,
        "DSC_9999.NEF": 300_000,
    }
    for rel, size in files.items():
        _write(s / rel, size)
    deep = s / ("very long folder name " * 4).strip() / ("another long folder name " * 4).strip()
    _write(deep / "Lightroom_Export" / "DSC_0001.jpg", 20_000)
    _write(deep / "DSC_0001.NEF", 200_000)
    # Not "not exported yet": any folder name containing "export" IS an export folder.
    _write(root / "2025" / "251224_ainda sem edição" / "DSC_0100.NEF", 100_000)
    return s


def _snapshot(root):
    out = {}
    for f in sorted(Path(root).rglob("*")):
        if f.is_file():
            st = f.stat()
            out[str(f.relative_to(root))] = (st.st_size, st.st_mtime_ns,
                                             hashlib.sha256(f.read_bytes()).hexdigest())
    return out


def _env(work, extra=None):
    """No Python on PATH: only Windows' own folders."""
    system_root = os.environ.get("SystemRoot", r"C:\Windows")
    keep = {k: v for k, v in os.environ.items()
            if k.upper() not in ("PATH", "PYTHONPATH", "PYTHONHOME", "PHOTOBACKUP_LOG_DIR",
                                 "VIRTUAL_ENV")}
    keep["PATH"] = os.pathsep.join([str(Path(system_root) / "System32"), system_root,
                                    str(Path(system_root) / "System32" / "Wbem")])
    keep["LOCALAPPDATA"] = str(work / "localappdata")
    keep["PHOTOBACKUP_CONFIG"] = str(work / "config.json")
    keep["PHOTOBACKUP_C1_LOCALAPPDATA"] = str(work / "c1" / "local")
    keep["PHOTOBACKUP_C1_INSTALL"] = str(work / "c1" / "install")
    keep["PHOTOBACKUP_C1_WINDOWS_COLOR"] = str(work / "c1" / "color")
    keep.update(extra or {})
    return keep


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--app", help="the unzipped package (default: newest in dist/)")
    p.add_argument("--work", help="scratch folder (default: in %%TEMP%%)")
    p.add_argument("--real", help="a real photo folder: dry-run only")
    p.add_argument("--keep", action="store_true", help="keep the scratch folder")
    a = p.parse_args()

    if a.app:
        src_app = Path(a.app)
    else:
        found = sorted((d for d in (ROOT / "dist").glob("photo-backup-*-x64") if d.is_dir()),
                       key=lambda d: d.stat().st_mtime)
        if not found:
            sys.exit("no package in dist/: run build.py or pass --app")
        src_app = found[-1]
    work = Path(a.work) if a.work else Path(tempfile.mkdtemp(prefix="pb_exe_battery_"))
    if work.exists() and any(work.iterdir()):
        sys.exit(f"--work must be empty or new: {work}")
    work.mkdir(parents=True, exist_ok=True)
    b = Battery()
    started = time.time()

    app = work / HOSTILE
    shutil.copytree(src_app, app)
    marked = _mark_downloaded(app)
    exe = app / "photo-backup.exe"
    scripts = app / "scripts"
    version = re.search(r'^__version__ = "([^"]+)"',
                        (scripts / "photo_backup.py").read_text(encoding="utf-8"), re.M).group(1)
    env = _env(work)
    log_dir = work / "localappdata" / "photo-backup" / "Logs"
    logs = work / "_exe_logs"
    logs.mkdir()

    def run(tag, args, stdin=subprocess.DEVNULL, cwd=None, extra_env=None, timeout=1800):
        t = time.time()
        r = subprocess.run([str(exe)] + [str(x) for x in args], cwd=str(cwd or work),
                           env=_env(work, extra_env) if extra_env else env,
                           stdin=stdin, capture_output=True, text=True,
                           encoding="utf-8", errors="replace", timeout=timeout)
        out = (r.stdout or "") + (r.stderr or "")
        (logs / f"{tag}.log").write_text(f"$ photo-backup.exe {' '.join(map(str, args))}\n"
                                         f"rc={r.returncode} ({time.time() - t:.1f}s)\n\n{out}",
                                         encoding="utf-8")
        print(f"   [{tag}] rc={r.returncode} {time.time() - t:.1f}s", flush=True)
        b.check(f"{tag}: no Python traceback", "Traceback" not in out,
                out[out.find("Traceback"):][:300] if "Traceback" in out else "")
        return r.returncode, out

    # ---- the program itself ----------------------------------------------------
    b.section(f"the program ({src_app.name}, {marked} files marked as downloaded)")
    b.check("no python.exe on the PATH the program gets",
            shutil.which("python", path=env["PATH"]) is None)
    rc, out = run("version", ["--version"])
    b.check(f"--version: photo_backup.py {version}", rc == 0 and version in out, out.strip())
    rc, out = run("help", ["--help"])
    b.check("--help: the menu's own help", rc == 0 and "--run-preset" in out, f"rc={rc}")
    for name, prog in (("backup", "selective_backup.py"), ("manifest", "manifest_backup.py"),
                       ("restore", "restore_backup.py"), ("captureone", "captureone_backup.py")):
        rc, out = run(f"{name}-version", [name, "--version"])
        b.check(f"{name} --version: {prog} {version}",
                rc == 0 and prog in out and version in out, out.strip())
    rc, out = run("not-bundled", [str(work / "x.py")])
    b.check("a .py outside scripts\\ is refused", rc != 0 and "not one of the bundled" in out,
            f"rc={rc}")

    # ---- a backup round trip ---------------------------------------------------
    b.section("backup, re-run, verify, restore")
    g = work / "G"
    session = _tree(g)
    before = _snapshot(g)
    # A destination whose prefix pushes the longest path past 260 characters.
    dest = work / "H" / ("バックアップ [x] 5% " * 3).strip() / "PHOTO_BACKUP"
    dest.mkdir(parents=True)
    longest = max(len(str(dest)) + len(k) + 1 for k in before)
    common = ["--source", g / "2025", "--dest", dest, "--base", g]
    rc, out = run("backup-dry-run", ["backup", *common, "--dry-run"])
    m = re.search(r"Plan:\s+NEW (\d+) files", out)
    planned = int(m.group(1)) if m else 0
    b.check("dry-run: rc 0, a NEW count", rc == 0 and planned > 0, f"rc={rc} planned={planned}")
    b.check("dry-run wrote nothing to the destination", not any(dest.iterdir()))
    rc, out = run("backup-copy", ["backup", *common, "--yes"])
    b.check(f"copy: rc 0, 'copied {planned} files'",
            rc == 0 and f"copied {planned} files" in out, f"rc={rc}")
    copied = [f for f in dest.rglob("*") if f.is_file() and "_photo_backup" not in f.parts]
    b.check(f"the copies are on the disk ({len(copied)} files)", len(copied) == planned,
            f"{len(copied)} != {planned}")
    b.check(f"a destination path past 260 characters was written (longest {longest})",
            longest > 260 and any(len(str(f)) > 260 for f in copied))
    b.check("the Capture One cache is left out, the .cos and NKSC_PARAM are in",
            not any("Cache" in f.parts for f in copied)
            and any(f.suffix == ".cos" for f in copied) and any(f.suffix == ".nksc" for f in copied))
    b.check("_OUTTAKES and the unselected DSC_9999.NEF are left out",
            not any("_OUTTAKES" in f.parts or f.name == "DSC_9999.NEF" for f in copied))
    same = all(f.read_bytes() == (g / f.relative_to(dest)).read_bytes() for f in copied)
    b.check("every copy has the bytes of its source", same)
    rc, out = run("backup-again", ["backup", *common, "--yes"])
    b.check(f"re-run: UP_TO_DATE {planned}, nothing copied",
            rc == 0 and f"UP_TO_DATE {planned}" in out and "NEW 0 files" in out, f"rc={rc}")
    rc, out = run("verify-full", ["backup", *common, "--verify", "full"])
    b.check(f"verify full: OK {planned}", rc == 0 and f"OK {planned}" in out, f"rc={rc}")
    restored = work / "restored [伊豆沼]"
    rc, out = run("restore", ["restore", "--backup", dest, "--to", restored, "--yes"])
    b.check(f"restore: RESTORED {planned}", rc == 0 and f"RESTORED {planned}" in out, f"rc={rc}")
    back = [f for f in restored.rglob("*") if f.is_file()]
    b.check("every restored file has the bytes of its source",
            len(back) == planned and all(f.read_bytes() == (g / f.relative_to(restored)).read_bytes()
                                         for f in back), f"{len(back)} files")

    # ---- a manifest --------------------------------------------------------------
    b.section("manifest")
    manifest = work / "manifest [m].csv"
    manifest.write_text("Folder,Mode,Originals\n"
                        f"{g / '2025'},2+,raw+jpeg\n", encoding="utf-8")
    mdest = work / "H2"
    rc, out = run("manifest-analyze", ["manifest", "--manifest", manifest, "--analyze"])
    b.check("--analyze: rc 0", rc == 0, f"rc={rc}")
    rc, out = run("manifest-copy", ["manifest", "--manifest", manifest, "--dest", mdest, "--yes"])
    b.check("copy: rc 0", rc == 0, f"rc={rc}")
    b.check("mode 2+: the folder without an export is copied whole, DSC_9999 too",
            any(f.name == "DSC_0100.NEF" for f in mdest.rglob("*"))
            and any(f.name == "DSC_9999.NEF" for f in mdest.rglob("*")))
    rc, out = run("manifest-verify", ["manifest", "--manifest", manifest, "--dest", mdest,
                                      "--verify", "quick"])
    b.check("--verify quick: rc 0", rc == 0, f"rc={rc}")

    # ---- Capture One's own files (fake folders) ------------------------------------
    b.section("Capture One's own files (fake Capture One folders in the scratch folder)")
    _write(work / "c1" / "local" / "CaptureOne" / "Styles50" / "My style.costyle", 2_000)
    _write(work / "c1" / "local" / "Capture_One" / "settings.xml", 1_000)
    (work / "c1" / "install").mkdir(parents=True)
    (work / "c1" / "color").mkdir(parents=True)
    cdest = work / "H3"
    rc, out = run("captureone-copy", ["captureone", "--dest", cdest, "--yes"])
    style = list((cdest / "_captureone").rglob("My style.costyle"))
    b.check("backup: rc 0, the style is in _captureone", rc == 0 and len(style) == 1, f"rc={rc}")
    b.check("RESTORE_CAPTUREONE.cmd is generated",
            (cdest / "_captureone" / "RESTORE_CAPTUREONE.cmd").is_file())
    rc, out = run("captureone-verify", ["captureone", "--verify", cdest])
    b.check("--verify: rc 0", rc == 0, f"rc={rc}")
    cout = work / "c1 restored"
    rc, out = run("captureone-restore", ["captureone", "--restore-from", cdest, "--to", cout,
                                         "--yes"])
    b.check("restore --to: rc 0, the style is back",
            rc == 0 and len(list(cout.rglob("My style.costyle"))) == 1, f"rc={rc}")

    # ---- the menu ----------------------------------------------------------------------
    b.section("the menu")
    rc, out = run("menu-closed-stdin", [])
    b.check("double-click with no input: the main menu, then 'No more input', rc 2",
            rc == 2 and "No more input" in out and "[7]" in out, f"rc={rc}")
    pdest = work / "H4"
    pdest.mkdir()
    (work / "config.json").write_text(json.dumps({"presets": {"NIGHTLY 伊豆沼": {
        "kind": "backup", "sources": [str(g / "2025")], "dest": str(pdest),
        "captureone": False}}}, ensure_ascii=False), encoding="utf-8")
    rc, out = run("menu-list-presets", ["--list-presets"])
    b.check("--list-presets names the preset", rc == 0 and "NIGHTLY 伊豆沼" in out, f"rc={rc}")
    # From another folder, as the Task Scheduler would start it.
    rc, out = run("menu-run-preset", ["--run-preset", "NIGHTLY 伊豆沼"], cwd=work / "H")
    b.check("--run-preset: rc 0, the backend ran as a child process (menu -> exe -> script)",
            rc == 0 and "copied" in out and any(pdest.rglob("*.NEF")), f"rc={rc}")

    # ---- the settings at the top of the scripts are the ones that run -------------------
    b.section("an edited setting reaches every backend")
    sb = scripts / "selective_backup.py"
    text = sb.read_text(encoding="utf-8")
    m = re.search(r"^SPACE_MARGIN_GB = ([\d.]+)", text, re.M)
    b.check("SPACE_MARGIN_GB found in scripts\\selective_backup.py", m)
    if m:
        sb.write_text(text.replace(m.group(0), "SPACE_MARGIN_GB = 7.25", 1), encoding="utf-8")
        for name in ("backup", "manifest"):
            rc, out = run(f"edited-{name}-help", [name, "--help"])
            b.check(f"{name} --help shows the edited default 7.25", rc == 0 and "7.25" in out,
                    f"rc={rc}")
        sb.write_text(text, encoding="utf-8")

    # ---- a real folder, read only ---------------------------------------------------------
    if a.real:
        b.section("a real photo folder (dry-run only)")
        real = Path(a.real)
        real_before = _snapshot(real)
        rdest = work / "H5"
        rdest.mkdir()
        rc, out = run("real-dry-run", ["backup", "--source", real, "--dest", rdest, "--dry-run"])
        m = re.search(r"Plan:\s+NEW (\d+) files", out)
        b.check(f"dry-run: rc 0, NEW {m.group(1) if m else '?'} files",
                rc == 0 and m and int(m.group(1)) > 0, f"rc={rc}")
        b.check("nothing written to the destination", not any(rdest.iterdir()))
        b.check("the real folder is byte for byte the same", _snapshot(real) == real_before)
    else:
        b.skips.append("no --real folder: the real-photo dry-run was not run")

    # ---- what the program left -------------------------------------------------------------
    b.section("what the program left")
    b.check("the synthetic source tree is byte for byte the same", _snapshot(g) == before)
    b.check(f"logs in %LOCALAPPDATA%\\photo-backup\\Logs ({len(list(log_dir.glob('*')))} files)",
            log_dir.is_dir() and any(log_dir.glob("*.log")))
    b.check("nothing written into the program folder",
            not (scripts / "Logs").exists() and not (app / "Logs").exists()
            and not list(app.rglob("__pycache__")))

    # ---- report ------------------------------------------------------------------------------
    passed = sum(1 for r in b.results if r[2])
    total = len(b.results)
    stamp = datetime.now().strftime("%y%m%d")
    report = ROOT / "AI_tools" / f"{stamp}_exe_battery_report.md"
    report.parent.mkdir(exist_ok=True)
    lines = [f"# photo-backup.exe battery — {datetime.now():%Y-%m-%d %H:%M}", "",
             f"Package: `{src_app}`  ", f"photo-backup {version}; ran from `{app}` "
             f"({marked} files marked as downloaded), no Python on PATH.  ",
             f"Result: **{passed} of {total} checks passed** in {time.time() - started:.0f} s.", ""]
    section = None
    for sec, label, ok, detail in b.results:
        if sec != section:
            lines += ["", f"## {sec}", ""]
            section = sec
        lines.append(f"- {'PASS' if ok else '**FAIL**'} {label}" + (f" — {detail}" if detail and not ok else ""))
    if b.skips:
        lines += ["", "## Not run", ""] + [f"- {s}" for s in b.skips]
    report.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"\n{passed} of {total} checks passed. Report: {report}")
    if a.keep:
        print(f"kept: {work}")
    else:
        shutil.rmtree(work, onexc=lambda f, q, e: (os.chmod(q, 0o777), f(q)))
    sys.exit(0 if passed == total else 1)


if __name__ == "__main__":
    main()
