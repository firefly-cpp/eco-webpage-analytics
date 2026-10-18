import pytest
from fastapi.testclient import TestClient

import app as app_module


client = TestClient(app_module.app)


def measurement(total_bytes, saved_bytes=0):
    return {
        "url": "https://example.com",
        "total_bytes": total_bytes,
        "image_transcoding": {"quality": 80, "saved_bytes": saved_bytes}
    }


def fake_measure_url(url):
    return {
        "url": "https://example.com",
        "baseline": measurement(1_000_000, 200_000),
        "full_scroll": measurement(3_000_000, 500_000),
        "without_third_party": measurement(600_000, 100_000)
    }


def recalculate_body(**overrides):
    body = {
        "url": "https://example.com",
        "visitor_location": "WORLD",
        "hosting_location": "WORLD",
        "baseline": measurement(1_000_000, 200_000),
        "full_scroll": measurement(3_000_000),
        "without_third_party": measurement(600_000)
    }
    body.update(overrides)
    return body


def test_get_locations_is_sorted_and_complete():
    response = client.get("/api/locations")

    assert response.status_code == 200

    locations = response.json()
    names = [location["name"] for location in locations]
    codes = [location["location_code"] for location in locations]

    assert names == sorted(names)
    assert "WORLD" in codes
    assert set(locations[0]) == {"location_code", "name", "carbon_intensity", "year"}


def test_analyze_returns_carbon_data_for_all_scenarios(monkeypatch):
    monkeypatch.setattr(app_module.engine, "measure_url", fake_measure_url)

    response = client.post("/api/analyze", json={"url": "example.com"})

    assert response.status_code == 200

    data = response.json()

    for scenario in ("baseline", "full_scroll", "without_third_party"):
        assert "co2_per_visit" in data[scenario]
        assert "rating" in data[scenario]
        assert "saved_co2_per_visit" in data[scenario]["image_transcoding"]

    assert data["full_scroll"]["co2_per_visit"] > data["baseline"]["co2_per_visit"]


def test_analyze_accepts_lowercase_locations(monkeypatch):
    monkeypatch.setattr(app_module.engine, "measure_url", fake_measure_url)

    response = client.post("/api/analyze", json={
        "url": "example.com",
        "visitor_location": " world ",
        "hosting_location": "world"
    })

    assert response.status_code == 200
    assert response.json()["baseline"]["carbon_factors"]["visitor"]["location_code"] == "WORLD"


def test_analyze_rejects_unknown_location_before_measuring(monkeypatch):
    def must_not_be_called(url):
        raise AssertionError("measure_url should not be called")

    monkeypatch.setattr(app_module.engine, "measure_url", must_not_be_called)

    response = client.post("/api/analyze", json={"url": "example.com", "visitor_location": "XYZ"})

    assert response.status_code == 400
    assert "XYZ" in response.json()["detail"]


@pytest.mark.parametrize("error, expected_status", [
    (ValueError("Invalid URL"), 400),
    (RuntimeError("Main document returned HTTP 500."), 502),
])
def test_analyze_maps_engine_errors_to_http_status(monkeypatch, error, expected_status):
    def failing_measure_url(url):
        raise error

    monkeypatch.setattr(app_module.engine, "measure_url", failing_measure_url)

    response = client.post("/api/analyze", json={"url": "example.com"})

    assert response.status_code == expected_status
    assert response.json()["detail"] == str(error)


def test_recalculate_returns_carbon_data():
    response = client.post("/api/recalculate", json=recalculate_body())

    assert response.status_code == 200

    data = response.json()

    assert data["url"] == "https://example.com"
    assert data["baseline"]["total_bytes"] == 1_000_000
    assert "saved_co2_per_visit" in data["baseline"]["image_transcoding"]


def test_recalculate_keeps_extra_measurement_fields():
    baseline = {**measurement(1_000_000), "requests": 42, "js_bytes": 1234}

    response = client.post("/api/recalculate", json=recalculate_body(baseline=baseline))

    assert response.status_code == 200
    assert response.json()["baseline"]["requests"] == 42
    assert response.json()["baseline"]["js_bytes"] == 1234


def test_recalculate_rejects_unknown_location():
    response = client.post("/api/recalculate", json=recalculate_body(hosting_location="XYZ"))

    assert response.status_code == 400


@pytest.mark.parametrize("total_bytes", [-1, "1000", 1.5])
def test_recalculate_rejects_invalid_total_bytes(total_bytes):
    body = recalculate_body(baseline={"url": "https://example.com", "total_bytes": total_bytes})

    response = client.post("/api/recalculate", json=body)

    assert response.status_code == 422


def test_recalculate_rejects_missing_scenario():
    body = recalculate_body()
    del body["full_scroll"]

    response = client.post("/api/recalculate", json=body)

    assert response.status_code == 422
