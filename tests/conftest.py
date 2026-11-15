import functools
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import os
from pathlib import Path
import subprocess
import threading
import time
import pytest
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


@pytest.fixture(scope="session")
def media_server(tmp_path_factory):
    root = tmp_path_factory.mktemp("media")
    subprocess.run(["ffmpeg", "-v", "error", "-f", "lavfi", "-i", "testsrc=size=160x90:rate=10", "-f", "lavfi", "-i", "sine=frequency=440", "-t", "2", "-c:v", "mpeg4", "-c:a", "aac", "-shortest", str(root / "sample.mp4")], check=True)
    (root / "playlist.html").write_text('<html><head><title>Playlist local</title></head><body><video controls src="sample.mp4"></video><video controls src="second.mp4"></video></body></html>')
    (root / "second.mp4").write_bytes((root / "sample.mp4").read_bytes())
    (root / "large.mp4").write_bytes((root / "sample.mp4").read_bytes() * 100)
    class Handler(SimpleHTTPRequestHandler):
        def log_message(self, *args):
            pass
        def do_GET(self):
            if self.path == "/slow.mp4":
                time.sleep(3)
                self.path = "/sample.mp4"
            try:
                super().do_GET()
            except (BrokenPipeError, ConnectionResetError):
                pass
    server = ThreadingHTTPServer(("127.0.0.1", 0), functools.partial(Handler, directory=str(root)))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{server.server_port}", root
    server.shutdown()
    server.server_close()


@pytest.fixture(scope="session")
def qt_app():
    from PySide6.QtWidgets import QApplication
    app = QApplication.instance() or QApplication([])
    yield app


def spin(app, predicate, timeout=20):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        app.processEvents()
        if predicate():
            return
        time.sleep(.01)
    raise AssertionError("Timed out waiting for Qt operation")
