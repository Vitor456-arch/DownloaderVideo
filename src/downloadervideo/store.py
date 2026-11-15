"""Transactional persistence; interrupted jobs are recovered without auto-starting."""
import json
import sqlite3
from .config import Options, data_dir


class Store:
    def __init__(self, root=None):
        root = root or data_dir()
        root.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(root / "library.sqlite3")
        self.db.execute("PRAGMA journal_mode=WAL")
        self.db.executescript("""
          CREATE TABLE IF NOT EXISTS settings (id INTEGER PRIMARY KEY CHECK(id=1), body TEXT NOT NULL);
          CREATE TABLE IF NOT EXISTS jobs (id TEXT PRIMARY KEY, body TEXT NOT NULL);
        """)

    def settings(self):
        row = self.db.execute("SELECT body FROM settings WHERE id=1").fetchone()
        return Options.from_dict(json.loads(row[0])) if row else Options()

    def save_settings(self, options):
        options.validate()
        # Cookie paths are references to user-managed files, never copied contents.
        with self.db:
            self.db.execute("INSERT OR REPLACE INTO settings VALUES (1, ?)", (json.dumps(options.public_dict()),))

    def save_job(self, job):
        with self.db:
            self.db.execute("INSERT OR REPLACE INTO jobs VALUES (?,?)", (job["id"], json.dumps(job)))

    def jobs(self):
        result = []
        for row in self.db.execute("SELECT body FROM jobs ORDER BY rowid"):
            job = json.loads(row[0])
            if job["state"] in {"queued", "downloading", "processing"}:
                job["state"] = "interrupted"
                job["message"] = "Sessão interrompida. Use Retomar para aproveitar arquivos parciais."
            result.append(job)
        return result

    def remove(self, job_id):
        with self.db:
            self.db.execute("DELETE FROM jobs WHERE id=?", (job_id,))

    def close(self):
        self.db.close()
