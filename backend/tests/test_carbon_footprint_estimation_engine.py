import json

import pytest

import carbon_footprint_estimation_engine as engine


CSV_HEADER = "Area,ISO 3 code,Year,Electricity source,Emissions intensity (gCO2e/kWh)\n"


@pytest.mark.parametrize("co2_per_visit, expected_rating", [
    (0.0, "A+"),
    (0.040, "A+"),
    (0.041, "A"),
    (0.079, "A"),
    (0.080, "B"),
    (0.145, "B"),
    (0.146, "C"),
    (0.209, "C"),
    (0.210, "D"),
    (0.278, "D"),
    (0.279, "E"),
    (0.359, "E"),
    (0.360, "F"),
    (10.0, "F"),
])
def test_get_rating_boundaries(co2_per_visit, expected_rating):
    assert engine.get_rating(co2_per_visit) == expected_rating


def test_breakdown_for_zero_bytes_is_zero():
    breakdown = engine.calculate_co2_breakdown_from_bytes(0)

    for value in breakdown.values():
        assert value == 0


def test_breakdown_for_one_gb_with_default_intensity():
    breakdown = engine.calculate_co2_breakdown_from_bytes(engine.bytes_per_gb)

    assert breakdown["dc_operational_co2"] == pytest.approx(0.055 * 494)
    assert breakdown["network_operational_co2"] == pytest.approx(0.059 * 494)
    assert breakdown["user_device_operational_co2"] == pytest.approx(0.080 * 494)
    assert breakdown["embodied_co2"] == pytest.approx((0.012 + 0.013 + 0.081) * 494)


def test_breakdown_parts_add_up_to_total():
    breakdown = engine.calculate_co2_breakdown_from_bytes(2_500_000)

    operational = (
        breakdown["dc_operational_co2"] +
        breakdown["network_operational_co2"] +
        breakdown["user_device_operational_co2"]
    )

    assert breakdown["operational_co2"] == pytest.approx(operational)
    assert breakdown["total_co2"] == pytest.approx(operational + breakdown["embodied_co2"])


def test_breakdown_uses_separate_location_intensities():
    breakdown = engine.calculate_co2_breakdown_from_bytes(
        engine.bytes_per_gb,
        visitor_carbon_intensity=100,
        hosting_carbon_intensity=0,
        network_carbon_intensity=200
    )

    assert breakdown["dc_operational_co2"] == 0
    assert breakdown["user_device_operational_co2"] == pytest.approx(0.080 * 100)
    assert breakdown["network_operational_co2"] == pytest.approx(0.059 * 200)


def test_breakdown_rejects_negative_bytes():
    with pytest.raises(ValueError):
        engine.calculate_co2_breakdown_from_bytes(-1)


def test_calculate_co2_from_bytes_returns_breakdown_total():
    breakdown = engine.calculate_co2_breakdown_from_bytes(1_000_000)

    assert engine.calculate_co2_from_bytes(1_000_000) == breakdown["total_co2"]


def test_more_bytes_means_more_co2():
    assert engine.calculate_co2_from_bytes(2_000_000) > engine.calculate_co2_from_bytes(1_000_000)


def test_get_carbon_factor_ignores_case_and_whitespace():
    assert engine.get_carbon_factor("  world ") == engine.get_carbon_factor("WORLD")


def test_get_carbon_factor_unknown_location_raises():
    with pytest.raises(ValueError, match="Unknown carbon-factor location"):
        engine.get_carbon_factor("NOT_A_COUNTRY")


def test_get_carbon_factor_returns_a_copy():
    factor = engine.get_carbon_factor("WORLD")
    factor["carbon_intensity"] = -1

    assert engine.get_carbon_factor("WORLD")["carbon_intensity"] != -1


def test_load_carbon_factors_keeps_only_valid_latest_rows(tmp_path, monkeypatch):
    csv_file = tmp_path / "ember.csv"
    csv_file.write_text(
        CSV_HEADER +
        "Austria,AUT,2022,Total generation,100\n"
        "Austria,AUT,2024,Total generation,90\n"
        "Austria,AUT,2023,Total generation,95\n"
        "Austria,AUT,2025,Coal,900\n"
        "Germany,DEU,2024,Total generation,\n"
        "France,FRA,2024,Total generation,-5\n"
        "World,,2024,Total generation,480\n",
        encoding="utf-8"
    )
    monkeypatch.setattr(engine, "data_file", csv_file)

    factors = engine.load_carbon_factors()

    assert factors["AUT"] == {"name": "Austria", "carbon_intensity": 90.0, "year": 2024}
    assert factors["WORLD"]["carbon_intensity"] == 480.0
    assert "DEU" not in factors
    assert "FRA" not in factors


def test_load_carbon_factors_without_usable_rows_raises(tmp_path, monkeypatch):
    csv_file = tmp_path / "ember.csv"
    csv_file.write_text(CSV_HEADER + "Austria,AUT,2024,Coal,900\n", encoding="utf-8")
    monkeypatch.setattr(engine, "data_file", csv_file)

    with pytest.raises(ValueError):
        engine.load_carbon_factors()


def test_calculate_co2_result_structure():
    result = engine.calculate_co2(
        {"url": "https://example.com", "total_bytes": 1_000_000},
        visitor_location="world",
        hosting_location="WORLD"
    )

    assert result["url"] == "https://example.com"
    assert result["rating"] == engine.get_rating(result["co2_per_visit"])
    assert result["co2_per_1000_visits"] == pytest.approx(result["co2_per_visit"] * 1000, abs=0.1)
    assert result["carbon_breakdown_unit"] == "gCO2e/visit"
    assert result["carbon_factors"]["visitor"]["location_code"] == "WORLD"
    assert result["carbon_factors"]["network"]["location_code"] == "WORLD"


def test_add_carbon_data_keeps_original_fields():
    entry = {"url": "https://example.com", "total_bytes": 1_000_000, "requests": 12}

    result = engine.add_carbon_data(entry)

    assert result["requests"] == 12
    assert "co2_per_visit" in result
    assert "image_transcoding" not in result


def test_add_carbon_data_adds_image_savings():
    entry = {
        "url": "https://example.com",
        "total_bytes": 1_000_000,
        "image_transcoding": {"quality": 80, "saved_bytes": 500_000}
    }

    result = engine.add_carbon_data(entry)
    expected = engine.calculate_co2_for_locations(500_000)

    assert result["image_transcoding"]["quality"] == 80
    assert result["image_transcoding"]["saved_co2_per_visit"] == round(expected, 4)
    assert result["image_transcoding"]["saved_co2_per_1000_visits"] == round(expected * 1000, 1)


def test_read_json_file_with_single_object(tmp_path):
    file_path = tmp_path / "data.json"
    file_path.write_text(json.dumps({"url": "a", "total_bytes": 1}), encoding="utf-8")

    assert engine.read_json_file(file_path) == [{"url": "a", "total_bytes": 1}]


def test_read_json_file_with_list(tmp_path):
    file_path = tmp_path / "data.json"
    file_path.write_text(json.dumps([{"url": "a"}, {"url": "b"}]), encoding="utf-8")

    assert len(engine.read_json_file(file_path)) == 2


@pytest.mark.parametrize("content", ["[]", "{}", "42"])
def test_read_json_file_rejects_empty_or_invalid_content(tmp_path, content):
    file_path = tmp_path / "data.json"
    file_path.write_text(content, encoding="utf-8")

    with pytest.raises(ValueError):
        engine.read_json_file(file_path)
