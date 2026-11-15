"""Official yt-dlp Python API adapter. Runs exclusively in a worker process."""
from pathlib import Path
import shutil
import os
import subprocess
import sys
import yt_dlp
from yt_dlp.utils import download_range_func
from .diagnostics import safe_message
from .config import Options, advanced_options, parse_time, validate_url


def ffmpeg_location(options):
    if options.ffmpeg:
        return options.ffmpeg
    bundled = Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent)) / "ffmpeg"
    if (bundled / "ffmpeg.exe").is_file():
        return str(bundled)
    return shutil.which("ffmpeg")


def dependencies(options=None):
    options = options or Options()
    path = ffmpeg_location(options)
    versions = {}
    for name in ("ffmpeg", "ffprobe"):
        executable = None
        if path:
            parent = Path(path) if Path(path).is_dir() else Path(path).parent
            executable = parent / (name + ".exe" if sys.platform == "win32" else name)
        if not executable or not executable.is_file():
            executable = shutil.which(name)
        version = "Ausente"
        available = False
        if executable:
            try:
                version = subprocess.run([str(executable), "-version"], capture_output=True, text=True, timeout=10, check=True, creationflags=0x08000000 if sys.platform == "win32" else 0).stdout.splitlines()[0]
                available = True
            except (OSError, subprocess.SubprocessError, IndexError):
                version = "Não foi possível executar"
        versions[name] = version
        versions[name + "_available"] = available if name == "ffprobe" else available and bool(path)
    return {"yt_dlp": yt_dlp.version.__version__, **versions, "python": sys.version.split()[0]}



class Logger:
    def __init__(self, emit):
        self.emit = emit

    def debug(self, message):
        if os.environ.get("DOWNLOADERVIDEO_DEBUG") == "1":
            print(safe_message(message), file=sys.stderr, flush=True)

    def warning(self, message):
        # No arbitrary remote text is persisted in logs; errors are displayed only.
        self.emit({"type": "notice", "message": safe_message(message)})

    def error(self, message):
        pass


def build_options(options, emit, analysis=False):
    options.validate()
    opts = {
        "verbose": os.environ.get("DOWNLOADERVIDEO_DEBUG") == "1",
        "quiet": True, "no_warnings": False, "logger": Logger(emit),
        "noplaylist": not options.playlist, "retries": options.retries,
        "fragment_retries": options.retries, "socket_timeout": 30,
        "windowsfilenames": True, "continuedl": True,
        "overwrites": options.existing == "overwrite",
        "outtmpl": str(Path(options.destination).expanduser() / options.filename),
        "format": options.format_id or ("bestaudio/best" if options.mode == "audio" else "bestvideo+bestaudio/best"),
        "merge_output_format": options.container,
        "writesubtitles": options.subtitles, "writeautomaticsub": options.automatic_subtitles,
        "subtitleslangs": [x.strip() for x in options.subtitle_languages.split(",") if x.strip()],
        "writethumbnail": options.thumbnail or options.embed_thumbnail,
        "writedescription": False, "writeinfojson": False,
        "postprocessors": [],
        "extract_flat": "in_playlist" if analysis else False,
        "ignoreerrors": False, "cachedir": False,
    }
    if options.rate_kib:
        opts["ratelimit"] = options.rate_kib * 1024
    if options.playlist_items:
        opts["playlist_items"] = options.playlist_items
    if options.cookies_file:
        opts["cookiefile"] = options.cookies_file
    location = ffmpeg_location(options)
    if location:
        opts["ffmpeg_location"] = location
    if not analysis:
        needs_ffmpeg = options.mode == "audio" or options.embed_subtitles or options.embed_thumbnail or options.video_recode or options.subtitle_format or options.metadata or options.chapters or options.split_chapters or options.section_start or options.section_end
        needs_ffmpeg = needs_ffmpeg or (options.mode == "video" and (not options.format_id or "+" in options.format_id or "+" in advanced_options(options.advanced).get("format", "")))
        if needs_ffmpeg and not location:
            raise ValueError("FFmpeg ausente. Instale-o e configure seu caminho em Configurações.")
        if options.mode == "audio":
            opts["postprocessors"].append({"key": "FFmpegExtractAudio", "preferredcodec": options.audio_format, "preferredquality": options.audio_quality})
        if options.video_recode:
            opts["postprocessors"].append({"key": "FFmpegVideoConvertor", "preferedformat": options.video_recode})
        if options.subtitle_format:
            opts["postprocessors"].append({"key": "FFmpegSubtitlesConvertor", "format": options.subtitle_format})
        if options.metadata:
            opts["postprocessors"].append({"key": "FFmpegMetadata", "add_metadata": True, "add_chapters": options.chapters})
        elif options.chapters:
            opts["postprocessors"].append({"key": "FFmpegMetadata", "add_metadata": False, "add_chapters": True})
        if options.embed_subtitles:
            opts["postprocessors"].append({"key": "FFmpegEmbedSubtitle"})
        if options.embed_thumbnail:
            opts["postprocessors"].append({"key": "EmbedThumbnail", "already_have_thumbnail": options.thumbnail})
        if options.split_chapters:
            opts["postprocessors"].append({"key": "FFmpegSplitChapters", "force_keyframes": False})
        if options.section_start or options.section_end:
            start = parse_time(options.section_start) if options.section_start else 0
            end = parse_time(options.section_end) if options.section_end else float("inf")
            opts["download_ranges"] = download_range_func(None, [(start, end)])
        opts["progress_hooks"] = [lambda d: emit({"type": "progress", "status": d["status"], "downloaded": d.get("downloaded_bytes", 0), "total": d.get("total_bytes") or d.get("total_bytes_estimate"), "speed": d.get("speed"), "eta": d.get("eta"), "filename": d.get("filename", ""), "playlist_index": d.get("info_dict", {}).get("playlist_index")})]
        opts["postprocessor_hooks"] = [lambda d: emit({"type": "processing", "message": d.get("postprocessor", "FFmpeg")})]
    opts.update(advanced_options(options.advanced))
    return opts


def summarize(info):
    entries = info.get("entries")
    if entries is not None:
        items = []
        for entry in entries:
            if entry:
                items.append({k: entry.get(k) for k in ("id", "title", "url", "webpage_url", "duration", "ie_key")})
        return {"title": info.get("title"), "playlist": True, "entries": items, "count": len(items), "extractor": info.get("extractor")}
    keys = ("id", "title", "thumbnail", "duration", "extractor", "uploader", "channel", "webpage_url", "filesize", "filesize_approx", "chapters", "subtitles", "automatic_captions")
    result = {k: info.get(k) for k in keys}
    formats = info.get("formats") or [info]
    result["formats"] = [{k: f.get(k) for k in ("format_id", "ext", "width", "height", "fps", "vcodec", "acodec", "language", "format_note", "filesize", "filesize_approx", "abr", "tbr")} for f in formats]
    result["playlist"] = False
    return result


def analyze(url, options, emit):
    with yt_dlp.YoutubeDL(build_options(options, emit, analysis=True)) as ydl:
        return summarize(ydl.extract_info(validate_url(url), download=False))


def download(url, options, emit):
    Path(options.destination).expanduser().mkdir(parents=True, exist_ok=True)
    outputs = []
    opts = build_options(options, emit)
    # The move hook runs after conversion, embedding and final file movement.
    def final_file(d):
        if d.get("status") == "finished":
            info = d.get("info_dict", {})
            path = info.get("filepath") or info.get("_filename")
            if path and Path(path).is_file():
                outputs.append(str(Path(path).resolve()))
                emit({"type": "file", "path": outputs[-1]})
    opts["postprocessor_hooks"].append(final_file)
    class DownloadSession(yt_dlp.YoutubeDL):
        def process_ie_result(self, ie_result, download=True, extra_info=None):
            if download and not options.playlist and ie_result.get("_type") in {"playlist", "multi_video", "compat_list"}:
                raise ValueError("Este link aponta para uma coleção. Habilite playlists nas opções antes de baixar.")
            return super().process_ie_result(ie_result, download=download, extra_info=extra_info)

    with DownloadSession(opts) as ydl:
        info = ydl.extract_info(validate_url(url), download=True)
        if not info:
            raise RuntimeError("O extrator não retornou um resultado de download.")
        def collect(item):
            if item.get("entries") is not None:
                for entry in item["entries"]:
                    if entry:
                        collect(entry)
            else:
                path = item.get("filepath") or ydl.prepare_filename(item)
                if path and Path(path).is_file():
                    outputs.append(str(Path(path).resolve()))
        collect(info)
    outputs = [p for p in dict.fromkeys(outputs) if Path(p).is_file()]
    if not outputs:
        raise RuntimeError("Nenhum arquivo final foi produzido. Verifique os filtros, formatos e itens selecionados.")
    return outputs
