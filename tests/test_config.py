import json
import pytest
from downloadervideo.config import Options, advanced_options, parse_time, validate_url
from downloadervideo.store import Store


@pytest.mark.parametrize("url", ["file:///etc/passwd", "javascript:alert(1)", "https://u:p@site.com/v", "hello", "https://"])
def test_bad_urls(url):
    with pytest.raises(ValueError):
        validate_url(url)


@pytest.mark.parametrize("raw", ['{"exec_cmd":"calc"}', '{"postprocessors": []}', '{"external_downloader":"cmd"}', '{"format_sort": [1]}', '[]', '{"concurrent_fragment_downloads": 100}'])
def test_unsafe_options_rejected(raw):
    with pytest.raises(ValueError):
        advanced_options(raw)


def test_validation_and_settings(tmp_path):
    options = Options(destination=str(tmp_path), rate_kib=150, concurrent=3)
    store = Store(tmp_path / "data")
    store.save_settings(options)
    store.close()
    store = Store(tmp_path / "data")
    assert store.settings() == options
    with pytest.raises(ValueError):
        Options(filename="../outside.mp4").validate()
    with pytest.raises(ValueError):
        Options(embed_subtitles=True).validate()
    with pytest.raises(ValueError):
        Options(section_start="01:30", section_end="30").validate()
    assert parse_time("1:02:03.5") == 3723.5
    assert advanced_options('{"format": "best", "socket_timeout": 10}')["format"] == "best"
    store.close()


def test_recover_history(tmp_path):
    store = Store(tmp_path)
    store.save_job({"id": "1", "state": "processing"})
    store.save_job({"id": "2", "state": "completed", "files": ["video.mp4"]})
    assert store.jobs()[0]["state"] == "interrupted"
    assert store.jobs()[1]["files"] == ["video.mp4"]
    store.remove("2")
    assert len(store.jobs()) == 1
    store.close()
