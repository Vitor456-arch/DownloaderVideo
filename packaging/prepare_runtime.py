"""Fetch a pinned Windows FFmpeg build, verify SHA256, prepare redistribution."""
from hashlib import sha256
import json
from pathlib import Path
import shutil
import sys
import urllib.request
import zipfile

TAG = "autobuild-2026-11-15-12-40"
ASSET = "ffmpeg-n8.1.3-35-gf1acb0a266-win64-lgpl-8.1.zip"
SHA256 = "272140baa96cbb9553eb57c03590e0b8d2c93ce352aa7f876c34fbc657536836"
URL = f"https://github.com/FFmpeg-Builds/FFmpeg-Builds/releases/download/{TAG}/{ASSET}"


def main():
    root = Path(sys.argv[1]).resolve()
    root.mkdir(parents=True, exist_ok=True)
    archive = root / ASSET
    with urllib.request.urlopen(URL, timeout=120) as response, archive.open("wb") as output:
        shutil.copyfileobj(response, output)
    digest = sha256(archive.read_bytes()).hexdigest()
    if digest != SHA256:
        raise RuntimeError(f"FFmpeg checksum mismatch: expected {SHA256}, received {digest}")
    extracted = root / "extracted"
    with zipfile.ZipFile(archive) as package:
        for item in package.infolist():
            path = (extracted / item.filename).resolve()
            if not path.is_relative_to(extracted.resolve()):
                raise RuntimeError("Unsafe archive member")
        package.extractall(extracted)
    ffmpeg = next(extracted.rglob("ffmpeg.exe"))
    ffprobe = ffmpeg.with_name("ffprobe.exe")
    if not ffprobe.is_file():
        raise RuntimeError("ffprobe missing from verified archive")
    notices = root / "notices"
    notices.mkdir(exist_ok=True)
    upstream = ffmpeg.parent.parent
    for item in upstream.iterdir():
        if item.name == "bin":
            continue
        target = notices / item.name
        if item.is_dir():
            shutil.copytree(item, target, dirs_exist_ok=True)
        else:
            shutil.copy2(item, target)
    (notices / "SOURCES.md").write_text(
        "# FFmpeg bundled runtime\n\n"
        f"Verified binary: {URL}\nSHA256: {SHA256}\n\n"
        "FFmpeg sources at the build revision:\n"
        "https://github.com/FFmpeg/FFmpeg/archive/f1acb0a266.tar.gz\n\n"
        f"Build scripts, dependency source URLs and license configuration:\nhttps://github.com/FFmpeg-Builds/FFmpeg-Builds/tree/{TAG}\n"
        f"https://github.com/FFmpeg-Builds/FFmpeg-Builds/archive/refs/tags/{TAG}.tar.gz\n\n"
        "This is the LGPL build, not the GPL/nonfree build. FFmpeg and FFprobe are separate executables. "
        "The original notices and documentation are included unchanged.\n", encoding="utf-8")
    config = {"binary_dir": str(ffmpeg.parent), "notices_dir": str(notices), "url": URL, "sha256": digest}
    (root / "runtime.json").write_text(json.dumps(config, indent=2), encoding="utf-8")
    print(json.dumps(config))


if __name__ == "__main__":
    main()
