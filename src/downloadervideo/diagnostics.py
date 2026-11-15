"""Small rotating diagnostic log. Never records media URLs, cookies or titles."""
import logging
from logging.handlers import RotatingFileHandler
import re
from urllib.parse import urlsplit, urlunsplit
from .config import data_dir


def safe_message(message):
    def clean(match):
        try:
            parsed = urlsplit(match.group(0))
            host = parsed.hostname or ""
            return urlunsplit((parsed.scheme, host, parsed.path, "", ""))
        except ValueError:
            return "[URL removida]"
    text = re.sub(r"https?://[^\s<>\"']+", clean, str(message))
    text = re.sub(r"(?i)(authorization|cookie|password|token|api[_-]?key)\s*[:=]\s*[^\s,;]+", r"\1=[removido]", text)
    return text[:8000]


def configure():
    logger = logging.getLogger("downloadervideo")
    if not logger.handlers:
        handler = RotatingFileHandler(data_dir() / "diagnostics.log", maxBytes=512000, backupCount=2, encoding="utf-8")
        handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
    return logger
