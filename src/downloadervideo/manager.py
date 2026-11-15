"""Persistent bounded queue; success requires the entire worker to finish."""
from datetime import datetime, timezone
from uuid import uuid4
from PySide6.QtCore import QObject, QTimer, Signal
import logging
from .config import Options, validate_url
from .process import Worker

STATES = {"queued": "Na fila", "downloading": "Baixando", "processing": "Processando", "completed": "Concluído", "cancelled": "Cancelado", "error": "Erro", "interrupted": "Interrompido"}
ACTIVE = {"queued", "downloading", "processing"}


class Manager(QObject):
    changed = Signal()

    def __init__(self, store, parent=None):
        super().__init__(parent)
        self.store = store
        self.jobs = store.jobs()
        self.workers = {}
        self.limit = store.settings().concurrent
        self.closing = False

    def add(self, urls, options, title=""):
        options.validate()
        urls = [validate_url(u) for u in urls]
        for url in urls:
            job = {"id": uuid4().hex, "url": url, "title": title if len(urls) == 1 else url, "options": options.public_dict(), "state": "queued", "created": datetime.now(timezone.utc).isoformat(), "downloaded": 0, "total": None, "speed": None, "eta": None, "message": "", "files": []}
            self.jobs.append(job)
            self.store.save_job(job)
        self.changed.emit()
        QTimer.singleShot(0, self.pump)

    def pump(self):
        if self.closing:
            return
        for job in self.jobs:
            if len(self.workers) >= self.limit:
                break
            if job["state"] == "queued":
                worker = Worker({"action": "download", "url": job["url"], "options": job["options"]}, self)
                self.workers[job["id"]] = worker
                job["state"] = "downloading"
                self.store.save_job(job)
                worker.event.connect(lambda event, j=job: self.update(j, event))
                worker.ended.connect(lambda ok, message, j=job: self.done(j, ok, message))
                worker.start()
        self.changed.emit()

    def update(self, job, event):
        # Buffered process events can arrive after taskkill has been requested.
        # Cancellation is terminal until the user explicitly retries the task.
        if job["state"] == "cancelled":
            return
        kind = event.get("type")
        if kind == "progress":
            job.update({k: event.get(k) for k in ("downloaded", "total", "speed", "eta")})
            job["state"] = "processing" if event.get("status") == "finished" else "downloading"
            job["message"] = f"Item {event['playlist_index']}" if event.get("playlist_index") else ""
        elif kind == "processing":
            job["state"] = "processing"
            job["message"] = event.get("message", "")
        elif kind == "notice":
            job["message"] = event["message"]
        elif kind == "file":
            if event["path"] not in job["files"]:
                job["files"].append(event["path"])
                self.store.save_job(job)
        elif kind == "result":
            job["files"] = list(dict.fromkeys(job["files"] + event["result"]))
        elif kind == "error":
            job["message"] = event["message"]
        self.changed.emit()

    def done(self, job, ok, message):
        worker = self.workers.pop(job["id"], None)
        if self.closing:
            job["state"] = "interrupted"
            job["message"] = "Sessão encerrada. Use Retomar para continuar."
        elif job["state"] != "cancelled":
            job["state"] = "completed" if ok else "error"
            job["message"] = "Todas as etapas finalizadas." if ok else message
        logging.getLogger("downloadervideo").info("job=%s state=%s", job["id"], job["state"])
        job["speed"] = None
        job["eta"] = None
        self.store.save_job(job)
        if worker:
            worker.deleteLater()
        self.changed.emit()
        QTimer.singleShot(0, self.pump)

    def cancel(self, job_id):
        job = self.get(job_id)
        if not job or job["state"] not in ACTIVE:
            return
        job["state"] = "cancelled"
        job["message"] = "Cancelado. Arquivos parciais preservados para retomada."
        self.store.save_job(job)
        worker = self.workers.get(job_id)
        if worker:
            worker.cancel()
        self.changed.emit()

    def retry(self, job_id):
        job = self.get(job_id)
        if job and job["state"] in {"error", "cancelled", "interrupted"} and job_id not in self.workers:
            job["state"] = "queued"
            job["message"] = ""
            self.store.save_job(job)
            self.pump()

    def get(self, job_id):
        return next((j for j in self.jobs if j["id"] == job_id), None)

    def clear_history(self):
        for job in self.jobs[:]:
            if job["state"] not in ACTIVE and job["id"] not in self.workers:
                self.store.remove(job["id"])
                self.jobs.remove(job)
        self.changed.emit()

    def shutdown(self):
        self.closing = True
        for worker in list(self.workers.values()):
            worker.cancel()
        for worker in list(self.workers.values()):
            worker.process.waitForFinished(3000)
            worker.force_stop()
            worker.process.waitForFinished(1000)
