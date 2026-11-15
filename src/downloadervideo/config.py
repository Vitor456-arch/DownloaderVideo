"""Validated preferences shared by UI and worker. Never accepts shell commands."""
from dataclasses import asdict, dataclass, fields
from pathlib import Path
import json
import os
import re
from urllib.parse import urlsplit


def data_dir():
    override = os.environ.get("DOWNLOADERVIDEO_DATA_DIR")
    root = Path(override) if override else Path(os.environ.get("LOCALAPPDATA", Path.home() / ".local/share")) / "DownloaderVideo"
    root.mkdir(mode=0o700, parents=True, exist_ok=True)
    return root


def validate_url(url):
    parsed = urlsplit(url.strip())
    if parsed.scheme not in {"https", "http"} or not parsed.hostname or parsed.username or parsed.password:
        raise ValueError("Informe um endereço HTTP/HTTPS válido, sem credenciais na URL.")
    return url.strip()


@dataclass
class Options:
    destination: str = str(Path.home() / "Downloads" / "DownloaderVideo")
    mode: str = "video"
    format_id: str = ""
    audio_format: str = "mp3"
    audio_quality: str = "192"
    container: str = "mkv"
    video_recode: str = ""
    subtitle_format: str = ""
    playlist: bool = False
    playlist_items: str = ""
    subtitles: bool = False
    automatic_subtitles: bool = False
    subtitle_languages: str = "pt.*,en.*"
    embed_subtitles: bool = False
    thumbnail: bool = False
    embed_thumbnail: bool = False
    metadata: bool = True
    chapters: bool = True
    split_chapters: bool = False
    section_start: str = ""
    section_end: str = ""
    rate_kib: int = 0
    retries: int = 10
    concurrent: int = 2
    filename: str = "%(title).180B [%(id)s].%(ext)s"
    existing: str = "skip"
    cookies_file: str = ""
    ffmpeg: str = ""
    advanced: str = "{}"

    def validate(self):
        if self.mode not in {"video", "audio"}:
            raise ValueError("Modo inválido.")
        if self.container not in {"mkv", "mp4", "webm"} or self.audio_format not in {"mp3", "m4a", "opus", "flac", "wav", "best"}:
            raise ValueError("Formato de saída inválido.")
        if self.video_recode not in {"", "mp4", "mkv", "webm", "avi", "mov"} or self.subtitle_format not in {"", "srt", "vtt", "ass"}:
            raise ValueError("Formato de conversão inválido.")
        if self.mode == "audio" and self.video_recode:
            raise ValueError("A conversão de vídeo exige o modo vídeo.")
        if self.audio_quality not in {"128", "192", "256", "320"}:
            raise ValueError("Qualidade de áudio inválida.")
        if not 1 <= self.concurrent <= 8 or not 0 <= self.rate_kib <= 1000000 or not 0 <= self.retries <= 100:
            raise ValueError("Limites inválidos: simultâneos 1–8, tentativas 0–100.")
        if self.existing not in {"skip", "overwrite"}:
            raise ValueError("Política de arquivos inválida.")
        if not self.destination.strip() or not Path(self.destination).expanduser().is_absolute():
            raise ValueError("Escolha uma pasta de destino absoluta.")
        if not self.filename or any(c in self.filename for c in '/\\\x00\r\n') or self.filename in {".", ".."}:
            raise ValueError("O modelo de nome não pode conter caminhos ou quebras de linha.")
        from yt_dlp import YoutubeDL
        template_error = YoutubeDL.validate_outtmpl(self.filename)
        if template_error:
            raise ValueError("Modelo de nome inválido: " + str(template_error))
        if self.cookies_file and not Path(self.cookies_file).is_file():
            raise ValueError("Arquivo de cookies não encontrado.")
        if self.ffmpeg and not Path(self.ffmpeg).exists():
            raise ValueError("Caminho do FFmpeg não encontrado.")
        if self.embed_subtitles and not (self.subtitles or self.automatic_subtitles):
            raise ValueError("Ative o download de legendas antes de incorporá-las.")
        if self.mode == "audio" and (self.embed_subtitles or self.split_chapters):
            raise ValueError("Legendas incorporadas e divisão de capítulos exigem modo vídeo.")
        if self.playlist_items and not re.fullmatch(r"[0-9,:\- ]+", self.playlist_items):
            raise ValueError("Itens da playlist: use índices e intervalos, como 1:5,8.")
        start = parse_time(self.section_start) if self.section_start else 0
        end = parse_time(self.section_end) if self.section_end else float("inf")
        if end <= start:
            raise ValueError("O fim do intervalo deve ser maior que o início.")
        advanced_options(self.advanced)
        return self

    def public_dict(self):
        return asdict(self)

    @classmethod
    def from_dict(cls, value):
        known = {f.name for f in fields(cls)}
        return cls(**{k: v for k, v in value.items() if k in known})


def parse_time(value):
    if not re.fullmatch(r"\d+(?::[0-5]?\d){0,2}(?:\.\d+)?", value):
        raise ValueError("Intervalo inválido. Use segundos ou HH:MM:SS.")
    result = 0.0
    for part in value.split(":"):
        result = result * 60 + float(part)
    return result


# Deliberately constrained API options: no exec, plugins, external downloaders,
# arbitrary postprocessors, config files, shell arguments or credential storage.
ADVANCED = {
    "format": str, "format_sort": list, "allow_multiple_audio_streams": bool,
    "allow_multiple_video_streams": bool, "prefer_free_formats": bool,
    "socket_timeout": (int, float), "fragment_retries": int,
    "concurrent_fragment_downloads": int, "geo_bypass": bool,
    "subtitlesformat": str, "writesubtitles": bool, "writeautomaticsub": bool,
    "playliststart": int, "playlistend": int, "matchtitle": str,
    "rejecttitle": str, "min_filesize": int, "max_filesize": int,
    "age_limit": int, "skip_unavailable_fragments": bool,
}


def advanced_options(raw):
    try:
        value = json.loads(raw)
    except (ValueError, TypeError) as exc:
        raise ValueError("As opções avançadas devem ser um objeto JSON válido.") from exc
    if not isinstance(value, dict):
        raise ValueError("Use um objeto JSON nas opções avançadas.")
    for key, item in value.items():
        expected = ADVANCED.get(key)
        if expected is None or not isinstance(item, expected) or (isinstance(item, bool) and expected is not bool):
            raise ValueError(f"Opção avançada não permitida ou tipo inválido: {key}")
        if isinstance(item, (int, float)) and not isinstance(item, bool) and not 0 <= item <= 10**12:
            raise ValueError(f"Valor fora dos limites: {key}")
        if key == "format_sort" and not all(isinstance(x, str) for x in item):
            raise ValueError("format_sort deve ser uma lista de textos.")
        if key == "concurrent_fragment_downloads" and not 1 <= item <= 16:
            raise ValueError("Use entre 1 e 16 fragmentos simultâneos.")
    return value
