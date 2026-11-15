"""Qt process transport and process-tree cancellation."""
import json
import os
import signal
import sys
from PySide6.QtCore import QObject, QProcess, QTimer, Signal, QCoreApplication


class Worker(QObject):
    event = Signal(dict)
    ended = Signal(bool, str)

    def __init__(self, request, parent=None):
        super().__init__(parent)
        self.request = request
        self.process = QProcess(self)
        self.buffer = bytearray()
        self.result_seen = False
        self.error = ""
        self.cancelled = False
        self.group_pid = None
        self.process.readyReadStandardOutput.connect(self.read)
        self.process.readyReadStandardError.connect(lambda: self.process.readAllStandardError())
        self.process.started.connect(self.send)
        self.process.finished.connect(self.finished)
        self.process.errorOccurred.connect(self.process_error)

    def start(self):
        if getattr(sys, "frozen", False):
            self.process.start(sys.executable, ["--worker"])
        else:
            self.process.start(sys.executable, ["-m", "downloadervideo", "--worker"])

    def send(self):
        self.process.write((json.dumps(self.request) + "\n").encode())
        self.process.closeWriteChannel()

    def read(self):
        self.buffer.extend(bytes(self.process.readAllStandardOutput()))
        while b"\n" in self.buffer:
            line, _, remaining = self.buffer.partition(b"\n")
            self.buffer = bytearray(remaining)
            try:
                event = json.loads(line)
            except ValueError:
                continue
            if event.get("type") == "ready":
                value = event.get("pid")
                if isinstance(value, int) and value > 0:
                    self.group_pid = value
                    if self.cancelled:
                        self.cancel()
            if event.get("type") == "result":
                self.result_seen = True
            elif event.get("type") == "error":
                self.error = event.get("message", "Erro desconhecido")
            self.event.emit(event)

    def process_error(self, error):
        if error == QProcess.ProcessError.FailedToStart:
            self.ended.emit(False, "Não foi possível iniciar o processo do yt-dlp.")

    def finished(self, exit_code, status):
        self.read()
        ok = exit_code == 0 and self.result_seen and not self.cancelled
        self.ended.emit(ok, self.error or ("Cancelado" if self.cancelled else "Processo interrompido sem resultado."))

    def cancel(self):
        self.cancelled = True
        pid = self.process.processId()
        if not pid:
            return
        if os.name == "nt":
            # Fixed executable and numeric PID; no shell interpolation.
            killer = QProcess(QCoreApplication.instance())
            killer.finished.connect(killer.deleteLater)
            killer.errorOccurred.connect(lambda error: self.process.kill())
            killer.start(os.path.join(os.environ.get("SystemRoot", "C:/Windows"), "System32", "taskkill.exe"), ["/PID", str(pid), "/T", "/F"])
        else:
            try:
                os.killpg(self.group_pid or pid, signal.SIGTERM)
            except ProcessLookupError:
                pass
            except PermissionError:
                self.process.terminate()
        QTimer.singleShot(2000, self.force_stop)

    def force_stop(self):
        if self.process.state() != QProcess.ProcessState.NotRunning:
            pid = self.process.processId()
            if os.name != "nt" and pid:
                try:
                    os.killpg(self.group_pid or pid, signal.SIGKILL)
                except (ProcessLookupError, PermissionError):
                    pass
            self.process.kill()
