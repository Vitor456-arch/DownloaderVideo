import json
from pathlib import Path
import subprocess
import sys
import pytest
from downloadervideo.config import Options
from downloadervideo.engine import analyze, build_options, dependencies, download


def test_analysis_and_selected_video_download(media_server, tmp_path):
    base, _ = media_server
    options = Options(destination=str(tmp_path))
    info = analyze(base + "/sample.mp4", options, lambda e: None)
    assert info["title"] and info["formats"]
    options.format_id = info["formats"][0]["format_id"]
    events = []
    files = download(base + "/sample.mp4", options, events.append)
    assert files and Path(files[-1]).stat().st_size > 1000
    assert any(e["type"] == "progress" and e["downloaded"] > 0 for e in events)
    assert any(e["type"] == "processing" for e in events)
    probe = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "stream=codec_type", "-of", "json", files[-1]], capture_output=True, text=True, check=True)
    assert {s["codec_type"] for s in json.loads(probe.stdout)["streams"]} == {"audio", "video"}
    # Repeat the same job to verify existing-file behavior.
    assert download(base + "/sample.mp4", options, lambda e: None)


def test_audio_conversion(media_server, tmp_path):
    base, _ = media_server
    options = Options(destination=str(tmp_path), mode="audio", audio_format="mp3")
    files = download(base + "/sample.mp4", options, lambda e: None)
    assert any(Path(p).suffix == ".mp3" for p in files)
    result = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "stream=codec_name", "-of", "json", files[-1]], capture_output=True, text=True, check=True)
    assert json.loads(result.stdout)["streams"][0]["codec_name"] == "mp3"


def test_playlist(media_server, tmp_path):
    base, _ = media_server
    options = Options(destination=str(tmp_path), playlist=True)
    info = analyze(base + "/playlist.html", options, lambda e: None)
    assert info["playlist"] and len(info["entries"]) == 2
    files = download(base + "/playlist.html", options, lambda e: None)
    assert len(files) == 2
    assert all(Path(p).is_file() for p in files)


def test_network_failure(media_server, tmp_path):
    base, _ = media_server
    with pytest.raises(Exception, match="404"):
        analyze(base + "/missing.mp4", Options(destination=str(tmp_path), retries=0), lambda e: None)


def test_processing_failure(media_server, tmp_path):
    base, root = media_server
    (root / "broken.mp4").write_bytes(b"not a real mp4" * 100)
    with pytest.raises(Exception):
        download(base + "/broken.mp4", Options(destination=str(tmp_path), mode="audio"), lambda e: None)


def test_dependencies_and_missing_ffmpeg(monkeypatch):
    import downloadervideo.engine as engine
    assert dependencies()["ffmpeg_available"]
    monkeypatch.setattr(engine, "ffmpeg_location", lambda options: None)
    assert not dependencies()["ffmpeg_available"]
    with pytest.raises(ValueError, match="FFmpeg"):
        build_options(Options(mode="audio"), lambda e: None)


def test_worker_protocol_and_dynamic_extractors():
    result = subprocess.run([sys.executable, "-m", "downloadervideo", "--worker"], input='{"action": "about"}\n', capture_output=True, text=True, timeout=30)
    assert result.returncode == 0, result.stderr
    event = json.loads(result.stdout.splitlines()[-1])
    assert event["type"] == "result"
    assert len(event["result"]["extractors"]) > 1000


def test_update_check_uses_official_response(monkeypatch):
    from downloadervideo import worker
    import io
    class Response(io.BytesIO):
        pass
    seen = []
    def open_request(request, timeout):
        seen.append(request.full_url)
        if "pypi.org" in request.full_url:
            return Response(b'{"info": {"version": "2099.01.01"}}')
        if "FFmpeg" in request.full_url:
            return Response(b'[{"name":"n8.0"},{"name":"n8.0.1"},{"name":"n7.9"},{"name":"n9.0-dev"}]')
        return Response(b'{"tag_name":"v1.1.0"}')
    monkeypatch.setattr(worker.urllib.request, "urlopen", open_request)
    monkeypatch.setattr(worker.os, "setsid", lambda: None, raising=False)
    output = io.StringIO()
    monkeypatch.setattr(sys, "stdin", io.StringIO('{"action":"updates"}\n'))
    monkeypatch.setattr(sys, "stdout", output)
    assert worker.run() == 0
    assert seen[0] == "https://pypi.org/pypi/yt-dlp/json"
    assert all(url.startswith("https://") for url in seen)
    result = json.loads(output.getvalue().splitlines()[-1])["result"]
    assert result["latest"] == "2099.01.01"
    assert "8.0.1" in result["ffmpeg_status"]
    assert "v1.1.0" in result["application_status"]


def test_video_recode_and_time_range(media_server, tmp_path):
    base, _ = media_server
    options = Options(destination=str(tmp_path), video_recode="webm", section_start="0", section_end="1")
    files = download(base + "/sample.mp4", options, lambda e: None)
    final = next(Path(p) for p in files if Path(p).suffix == ".webm" and Path(p).is_file())
    result = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "json", str(final)], capture_output=True, text=True, check=True)
    assert float(json.loads(result.stdout)["format"]["duration"]) < 1.8


def test_download_dash_video_and_audio_formats(media_server, tmp_path):
    base, root = media_server
    dash = root / "dash"
    dash.mkdir(exist_ok=True)
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(root / "sample.mp4"), "-c:v", "libx264", "-c:a", "aac", "-f", "dash", str(dash / "manifest.mpd")], check=True)
    options = Options(destination=str(tmp_path))
    info = analyze(base + "/dash/manifest.mpd", options, lambda e: None)
    video = next(f for f in info["formats"] if f.get("vcodec") not in {"none", None})
    audio = next(f for f in info["formats"] if f.get("vcodec") == "none" and f.get("acodec") not in {"none", None})
    assert video["height"] == 90
    options.format_id = video["format_id"] + "+" + audio["format_id"]
    result = download(base + "/dash/manifest.mpd", options, lambda e: None)
    assert any(Path(p).suffix == ".mkv" for p in result)
    final = next(p for p in result if Path(p).suffix == ".mkv")
    probe = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "stream=codec_type", "-of", "json", final], capture_output=True, text=True, check=True)
    assert {s["codec_type"] for s in json.loads(probe.stdout)["streams"]} == {"audio", "video"}


def test_collection_requires_explicit_option(media_server, tmp_path):
    base, _ = media_server
    with pytest.raises(Exception, match="coleção"):
        download(base + "/playlist.html", Options(destination=str(tmp_path)), lambda e: None)
    assert not list(tmp_path.glob("*.mp4"))
