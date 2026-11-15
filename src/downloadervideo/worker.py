"""One-shot worker with a JSON-lines protocol, never a shell command."""
import json
import os
import sys
import urllib.request
import urllib.error
import re
from .config import Options
from .engine import analyze, dependencies, download


def run():
    if os.name != "nt":
        os.setsid()  # Own group: cancellation also stops FFmpeg children.
    # Windowed PyInstaller executables have no Python stdio wrappers. QProcess
    # still passes real Windows pipe handles; wrap those explicitly.
    if os.name == "nt" and (sys.stdin is None or sys.stdout is None):
        import ctypes
        import msvcrt
        kernel = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel.GetStdHandle.restype = ctypes.c_void_p
        for name, number, mode, flags in (("stdin", -10, "r", os.O_RDONLY), ("stdout", -11, "w", os.O_WRONLY), ("stderr", -12, "w", os.O_WRONLY)):
            handle = kernel.GetStdHandle(number)
            if handle and handle != ctypes.c_void_p(-1).value:
                fd = msvcrt.open_osfhandle(handle, flags)
                setattr(sys, name, os.fdopen(fd, mode, encoding="utf-8", buffering=1))
    output = sys.stdout
    sys.stdout = sys.stderr

    def emit(event):
        output.write(json.dumps(event, ensure_ascii=True) + "\n")
        output.flush()

    emit({"type": "ready", "pid": os.getpid()})
    try:
        request = json.loads(sys.stdin.readline())
        options = Options.from_dict(request.get("options", {}))
        action = request["action"]
        if action == "analyze":
            result = analyze(request["url"], options, emit)
        elif action == "download":
            result = download(request["url"], options, emit)
        elif action == "about":
            from yt_dlp.extractor import list_extractor_classes
            result = {"dependencies": dependencies(options), "extractors": sorted(c.IE_NAME for c in list_extractor_classes())}
        elif action == "updates":
            req = urllib.request.Request("https://pypi.org/pypi/yt-dlp/json", headers={"User-Agent": "DownloaderVideo/1.0"})
            with urllib.request.urlopen(req, timeout=20) as response:
                release = json.load(response)
            result = {"installed": dependencies(options)["yt_dlp"], "latest": release["info"]["version"], "url": "https://github.com/yt-dlp/yt-dlp/releases", "app": "https://github.com/Vitor456-arch/DownloaderVideo/releases", "ffmpeg": "https://ffmpeg.org/download.html"}
            endpoints = {
                "application": "https://api.github.com/repos/Vitor456-arch/DownloaderVideo/releases/latest",
                "ffmpeg": "https://api.github.com/repos/FFmpeg/FFmpeg/tags?per_page=100",
            }
            for component, endpoint in endpoints.items():
                try:
                    req = urllib.request.Request(endpoint, headers={"User-Agent": "DownloaderVideo/1.0", "Accept": "application/vnd.github+json"})
                    with urllib.request.urlopen(req, timeout=15) as response:
                        payload = json.load(response)
                    if component == "application":
                        version = payload.get("tag_name")
                        if not isinstance(version, str):
                            raise ValueError("Resposta oficial sem versão publicada.")
                        result[component + "_status"] = "Última release: " + version
                    else:
                        tags = [tag["name"][1:] for tag in payload if isinstance(tag, dict) and re.fullmatch(r"n\d+\.\d+(?:\.\d+)?", tag.get("name", ""))]
                        if not tags:
                            raise ValueError("Resposta oficial sem versões estáveis.")
                        version = max(tags, key=lambda tag: tuple(int(part) for part in tag.split(".")))
                        result[component + "_status"] = "Versão estável publicada: " + version
                except urllib.error.HTTPError as exc:
                    result[component + "_status"] = "Nenhuma release pública encontrada." if exc.code == 404 else "Consulta indisponível (HTTP " + str(exc.code) + ")."
                except Exception as exc:
                    from .diagnostics import safe_message
                    result[component + "_status"] = "Não foi possível consultar: " + safe_message(exc)
        elif action == "thumbnail":
            from .config import validate_url
            req = urllib.request.Request(validate_url(request["url"]), headers={"User-Agent": "DownloaderVideo/1.0"})
            with urllib.request.urlopen(req, timeout=15) as response:
                content = response.read(5 * 1024 * 1024 + 1)
            if len(content) > 5 * 1024 * 1024:
                raise ValueError("Miniatura excede 5 MiB.")
            import base64
            result = base64.b64encode(content).decode("ascii")
        else:
            raise ValueError("Operação desconhecida.")
        emit({"type": "result", "result": result})
        return 0
    except Exception as exc:
        from .diagnostics import safe_message
        if os.environ.get("DOWNLOADERVIDEO_DEBUG") == "1":
            for cause in getattr(exc, "unexpected_errors", []):
                print(safe_message(f"{cause!r} filename={getattr(cause, 'filename', None)}"), file=sys.stderr, flush=True)
        emit({"type": "error", "message": safe_message(exc)})
        return 1
