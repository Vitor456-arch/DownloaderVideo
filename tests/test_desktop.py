from pathlib import Path
import time
from PySide6.QtCore import QTimer
from downloadervideo.config import Options
from downloadervideo.manager import Manager
from downloadervideo.process import Worker
from downloadervideo.store import Store
from conftest import spin


def test_queue_completion_and_history(qt_app, media_server, tmp_path):
    base, _ = media_server
    store = Store(tmp_path / "data")
    manager = Manager(store)
    manager.limit = 1
    manager.add([base + "/sample.mp4", base + "/second.mp4"], Options(destination=str(tmp_path / "out")))
    maximum = []
    manager.changed.connect(lambda: maximum.append(len(manager.workers)))
    spin(qt_app, lambda: all(j["state"] in {"completed", "error"} for j in manager.jobs), timeout=40)
    assert all(j["state"] == "completed" for j in manager.jobs), manager.jobs
    assert max(maximum) == 1
    assert all(j["files"] for j in manager.jobs)
    assert all(Path(j["files"][-1]).is_file() for j in manager.jobs)
    assert len(store.jobs()) == 2
    manager.clear_history()
    assert not store.jobs()
    manager.shutdown()
    store.close()


def test_cancel_retry_and_responsive_event_loop(qt_app, media_server, tmp_path):
    base, _ = media_server
    store = Store(tmp_path / "db")
    manager = Manager(store)
    manager.add([base + "/large.mp4"], Options(destination=str(tmp_path / "out"), rate_kib=32, metadata=False, chapters=False))
    ticks = []
    timer = QTimer()
    timer.setInterval(10)
    timer.timeout.connect(lambda: ticks.append(time.monotonic()))
    timer.start()
    spin(qt_app, lambda: manager.jobs[0].get("downloaded", 0) > 0)
    job = manager.jobs[0]
    manager.cancel(job["id"])
    spin(qt_app, lambda: not manager.workers)
    assert job["state"] == "cancelled"
    assert len(ticks) >= 5
    assert list((tmp_path / "out").glob("*.part"))
    job["options"]["rate_kib"] = 0
    manager.retry(job["id"])
    spin(qt_app, lambda: job["state"] in {"completed", "error"}, timeout=30)
    assert job["state"] == "completed", job["message"]
    timer.stop()
    manager.shutdown()
    store.close()


def test_analysis_cancel(qt_app, media_server):
    base, _ = media_server
    worker = Worker({"action": "analyze", "url": base + "/slow.mp4"})
    ended = []
    worker.ended.connect(lambda ok, message: ended.append(ok))
    worker.start()
    spin(qt_app, lambda: worker.process.processId() > 0)
    QTimer.singleShot(300, worker.cancel)
    spin(qt_app, lambda: bool(ended))
    assert ended == [False]


def test_main_window_analysis_settings(qt_app, media_server, tmp_path):
    from downloadervideo.theme import STYLE
    qt_app.setStyle("Fusion")
    qt_app.setStyleSheet(STYLE)
    from downloadervideo.app import MainWindow
    base, _ = media_server
    window = MainWindow(Store(tmp_path / "db"))
    window.show()
    window.urls.setPlainText(base + "/sample.mp4")
    window.start_analysis()
    spin(qt_app, lambda: window.info is not None and window.analysis_worker is None, timeout=30)
    assert window.formats.rowCount() > 0
    spin(qt_app, lambda: len(window.extractors) > 1000)
    assert window.pages.count() == 4
    window.settings_form.controls["rate_kib"].setValue(42)
    window.save_settings()
    assert window.store.settings().rate_kib == 42
    window.search_extractors("youtube")
    assert window.extractor_list.count() > 0
    window.grab().save(str(tmp_path / "interface.png"))
    window.close()


def test_shutdown_recovers_active_tasks(qt_app, media_server, tmp_path):
    base, _ = media_server
    store = Store(tmp_path / "db")
    manager = Manager(store)
    manager.limit = 1
    manager.add([base + "/large.mp4", base + "/second.mp4"], Options(destination=str(tmp_path / "out"), rate_kib=32))
    spin(qt_app, lambda: manager.jobs[0].get("downloaded", 0) > 0)
    manager.shutdown()
    recovered = store.jobs()
    assert all(j["state"] == "interrupted" for j in recovered)
    assert not manager.workers
    store.close()
