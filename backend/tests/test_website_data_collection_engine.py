import io
from unittest.mock import MagicMock

import pytest
from PIL import Image

import website_data_collection_engine as collector
from website_data_collection_engine import (
    RequestRecord,
    SingleRunResult,
    WebsiteMeasurementEngine,
    get_registered_domain,
    is_third_party,
    normalize_url,
)


def make_image_bytes(image_format="PNG", mode="RGB"):
    output = io.BytesIO()
    Image.new(mode, (50, 50), color="red").save(output, format=image_format)
    return output.getvalue()


def make_request(body):
    request = MagicMock()
    request.response.return_value.body.return_value = body
    return request


@pytest.mark.parametrize("url, expected", [
    ("example.com", "https://example.com"),
    ("  https://example.com/page  ", "https://example.com/page"),
    ("http://example.com", "http://example.com"),
])
def test_normalize_url(url, expected):
    assert normalize_url(url) == expected


@pytest.mark.parametrize("url", ["", "   ", "https://"])
def test_normalize_url_rejects_invalid_input(url):
    with pytest.raises(ValueError):
        normalize_url(url)


@pytest.mark.parametrize("url, expected", [
    ("https://www.example.com/page", "example.com"),
    ("https://news.bbc.co.uk", "bbc.co.uk"),
    ("http://localhost:8080", "localhost"),
    ("not a url", ""),
])
def test_get_registered_domain(url, expected):
    assert get_registered_domain(url) == expected


@pytest.mark.parametrize("request_url, expected", [
    ("https://example.com/app.js", False),
    ("https://cdn.example.com/app.js", False),
    ("https://www.google-analytics.com/ga.js", True),
    ("data:image/png;base64,abc", False),
])
def test_is_third_party(request_url, expected):
    assert is_third_party(request_url, "https://www.example.com") is expected


@pytest.mark.parametrize("kwargs", [
    {"timeout_ms": 0},
    {"quiet_window_ms": -1},
    {"max_observation_ms": 0},
    {"quiet_window_ms": 5000, "max_observation_ms": 5000},
])
def test_engine_rejects_invalid_settings(kwargs):
    with pytest.raises(ValueError):
        WebsiteMeasurementEngine(**kwargs)


def test_build_summary_adds_up_resources():
    records = {
        "html": RequestRecord("other", transfer_bytes=1000, completed=True),
        "image": RequestRecord("image", transfer_bytes=4000, webp_bytes=1500, completed=True),
        "svg": RequestRecord("image", transfer_bytes=500, webp_bytes=None, completed=True),
        "script": RequestRecord("script", third_party=True, transfer_bytes=3000, completed=True),
        "css": RequestRecord("stylesheet", transfer_bytes=200, completed=True),
        "font": RequestRecord("font", transfer_bytes=300, completed=True),
        "video": RequestRecord("media", transfer_bytes=9000, completed=True),
        "pending": RequestRecord("image", transfer_bytes=7777, completed=False),
    }

    summary = WebsiteMeasurementEngine.build_summary(
        input_url="https://example.com",
        request_records=records,
        page_metrics={"loadMs": 1234}
    )

    assert summary["url"] == "https://example.com"
    assert summary["total_bytes"] == 18000
    assert summary["requests"] == 7
    assert summary["unfinished_requests"] == 1
    assert summary["images_bytes"] == 4500
    assert summary["images_optimizable_bytes"] == 4000
    assert summary["images_webp_bytes"] == 1500
    assert summary["js_bytes"] == 3000
    assert summary["css_bytes"] == 200
    assert summary["fonts_bytes"] == 300
    assert summary["media_bytes"] == 9000
    assert summary["third_party_bytes"] == 3000
    assert summary["third_party_requests"] == 1
    assert summary["load_time"] == 1.234


@pytest.mark.parametrize("page_metrics", [{}, {"loadMs": None}, {"loadMs": 0}, {"loadMs": "fast"}])
def test_build_summary_without_valid_load_time(page_metrics):
    summary = WebsiteMeasurementEngine.build_summary(
        input_url="https://example.com",
        request_records={},
        page_metrics=page_metrics
    )

    assert summary["load_time"] is None
    assert summary["total_bytes"] == 0


def test_build_image_transcoding():
    result = WebsiteMeasurementEngine.build_image_transcoding(
        {"images_optimizable_bytes": 4000, "images_webp_bytes": 1500}
    )

    assert result == {
        "quality": collector.WEBP_QUALITY,
        "original_bytes": 4000,
        "webp_bytes": 1500,
        "saved_bytes": 2500
    }


def test_build_image_transcoding_never_reports_negative_savings():
    result = WebsiteMeasurementEngine.build_image_transcoding(
        {"images_optimizable_bytes": 1000, "images_webp_bytes": 3000}
    )

    assert result["saved_bytes"] == 0


def test_build_image_transcoding_with_missing_values():
    result = WebsiteMeasurementEngine.build_image_transcoding({})

    assert result["original_bytes"] == 0
    assert result["saved_bytes"] == 0


def test_handle_route_blocks_third_party_requests():
    route = MagicMock()
    route.request.url = "https://tracker.net/pixel.gif"

    WebsiteMeasurementEngine.handle_route(route, "https://example.com")

    route.abort.assert_called_once()
    route.continue_.assert_not_called()


def test_handle_route_allows_first_party_requests():
    route = MagicMock()
    route.request.url = "https://static.example.com/logo.png"

    WebsiteMeasurementEngine.handle_route(route, "https://example.com")

    route.continue_.assert_called_once()
    route.abort.assert_not_called()


@pytest.mark.parametrize("image_format, mode", [("PNG", "RGB"), ("PNG", "RGBA"), ("JPEG", "RGB"), ("GIF", "P")])
def test_measure_webp_size_converts_images(image_format, mode):
    request = make_request(make_image_bytes(image_format, mode))

    webp_size = WebsiteMeasurementEngine.measure_webp_size(request)

    assert isinstance(webp_size, int)
    assert webp_size > 0


def test_measure_webp_size_without_response():
    request = MagicMock()
    request.response.return_value = None

    assert WebsiteMeasurementEngine.measure_webp_size(request) is None


@pytest.mark.parametrize("body", [b"", b"this is not an image"])
def test_measure_webp_size_with_empty_or_invalid_body(body):
    assert WebsiteMeasurementEngine.measure_webp_size(make_request(body)) is None


def test_measure_webp_size_skips_animated_images():
    frames = [Image.new("RGB", (10, 10), color) for color in ("red", "blue")]
    output = io.BytesIO()
    frames[0].save(output, format="GIF", save_all=True, append_images=frames[1:])

    assert WebsiteMeasurementEngine.measure_webp_size(make_request(output.getvalue())) is None


def fake_summary(url, total_bytes):
    return {
        "url": url,
        "total_bytes": total_bytes,
        "images_optimizable_bytes": 1000,
        "images_webp_bytes": 400
    }


def test_measure_url_runs_all_three_scenarios(monkeypatch):
    monkeypatch.setattr(collector, "sync_playwright", MagicMock())
    engine = WebsiteMeasurementEngine()
    calls = []

    def fake_measure_run(browser, url, *, scroll_page=False, block_third_party=False):
        calls.append((scroll_page, block_third_party))
        return SingleRunResult(success=True, summary=fake_summary(url, 100 * (len(calls))))

    monkeypatch.setattr(engine, "measure_run", fake_measure_run)

    result = engine.measure_url("example.com")

    assert calls == [(False, False), (True, False), (True, True)]
    assert result["url"] == "https://example.com"
    assert result["baseline"]["total_bytes"] == 100
    assert result["full_scroll"]["total_bytes"] == 200
    assert result["without_third_party"]["total_bytes"] == 300
    assert result["baseline"]["image_transcoding"]["saved_bytes"] == 600


@pytest.mark.parametrize("failing_run", [0, 1, 2])
def test_measure_url_raises_when_a_run_fails(monkeypatch, failing_run):
    monkeypatch.setattr(collector, "sync_playwright", MagicMock())
    engine = WebsiteMeasurementEngine()
    runs = iter(range(3))

    def fake_measure_run(browser, url, **kwargs):
        success = next(runs) != failing_run
        return SingleRunResult(success=success, summary=fake_summary(url, 100), error=None if success else "boom")

    monkeypatch.setattr(engine, "measure_run", fake_measure_run)

    with pytest.raises(RuntimeError, match="boom"):
        engine.measure_url("example.com")
