# Run from repository root: python -m PyInstaller packaging/DownloaderVideo.spec
from pathlib import Path
import os
import ssl
from PyInstaller.utils.hooks import collect_all, copy_metadata

root = Path(SPECPATH).parent
all_datas, all_binaries, all_hidden = collect_all("yt_dlp")
for package in ("yt_dlp_ejs", "mutagen", "certifi"):
    d, b, h = collect_all(package)
    all_datas += d
    all_binaries += b
    all_hidden += h
for filename in ("README.md", "LICENSE", "THIRD_PARTY_NOTICES.md"):
    all_datas.append((str(root / filename), "."))
all_datas += copy_metadata("yt-dlp")
# Managed Python may carry an additional CA distrust resource used by ssl.py.
# Preserve that trust policy in local builds; standard Windows Python has none.
trust_resource = Path(ssl.__file__).parent / "codex-rejected-cas.pem"
if trust_resource.is_file():
    all_datas.append((str(trust_resource), "."))
qt_root = Path(next(iter(__import__("PySide6").__path__)))
if (qt_root / "Qt" / "licenses").exists():
    all_datas.append((str(qt_root / "Qt" / "licenses"), "licenses/Qt"))
all_datas.append((str(root / "packaging" / "licenses"), "licenses"))
ffmpeg = os.environ.get("DOWNLOADERVIDEO_FFMPEG_DIR")
if ffmpeg:
    for binary in ("ffmpeg.exe", "ffprobe.exe"):
        all_binaries.append((str(Path(ffmpeg) / binary), "ffmpeg"))
    all_datas.append((os.environ["DOWNLOADERVIDEO_FFMPEG_NOTICES"], "licenses/FFmpeg"))
a = Analysis([str(root / "packaging" / "entry.py")], pathex=[str(root / "src")],
             binaries=all_binaries, datas=all_datas, hiddenimports=all_hidden,
             excludes=["PySide6.QtWebEngineCore", "PySide6.QtWebEngineWidgets", "PySide6.QtPdf", "tkinter"],
             noarchive=False)
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name="DownloaderVideo",
          debug=False, bootloader_ignore_signals=False, strip=False, upx=False, console=False)
coll = COLLECT(exe, a.binaries, a.datas, strip=False, upx=False, name="DownloaderVideo")
