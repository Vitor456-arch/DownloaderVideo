"""Test packaged pipes, extractors, analysis, video download and MP3 conversion."""
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
from tempfile import TemporaryDirectory
import threading

binary = Path(sys.argv[1]).resolve()


def request(payload):
    environment = dict(os.environ)
    if os.name == "nt" and "--bundled" in sys.argv[2:]:
        # Windows releases must work without a separately installed FFmpeg.
        environment["PATH"] = str(Path(environment.get("SystemRoot", "C:/Windows")) / "System32")
    result = subprocess.run([str(binary), "--worker"], env=environment, input=json.dumps(payload) + "\n", capture_output=True, text=True, timeout=90, encoding="utf-8")
    assert result.returncode == 0, (result.returncode, result.stdout, result.stderr)
    event = json.loads(result.stdout.splitlines()[-1])
    assert event["type"] == "result", event
    return event["result"]


data = request({"action": "about"})
assert len(data["extractors"]) > 1000
print("Frozen worker OK:", data["dependencies"])
ffmpeg = shutil.which("ffmpeg")
if not ffmpeg:
    print("Video/audio package integration NOT RUN: FFmpeg absent from build host PATH.")
    raise SystemExit(0)
with TemporaryDirectory() as directory:
    root = Path(directory)
    subprocess.run([ffmpeg, "-v", "error", "-f", "lavfi", "-i", "testsrc=size=160x90:rate=10", "-f", "lavfi", "-i", "sine=frequency=440", "-t", "1", "-c:v", "mpeg4", "-c:a", "aac", "-shortest", str(root / "sample.mp4")], check=True)
    class Handler(SimpleHTTPRequestHandler):
        def log_message(self, *args):
            pass
    server = ThreadingHTTPServer(("127.0.0.1", 0), partial(Handler, directory=str(root)))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        url = f"http://127.0.0.1:{server.server_port}/sample.mp4"
        info = request({"action": "analyze", "url": url})
        assert info["formats"]
        for mode in ("video", "audio"):
            result = request({"action": "download", "url": url, "options": {"mode": mode, "destination": str(root / mode)}})
            assert result and all(Path(p).is_file() for p in result), result
            if mode == "audio":
                assert any(Path(p).suffix == ".mp3" for p in result)
        print("Frozen analysis, video download and MP3 conversion OK.")
    finally:
        server.shutdown()
        server.server_close()
