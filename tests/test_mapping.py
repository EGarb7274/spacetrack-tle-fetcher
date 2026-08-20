import pytest

from tle_fetcher.mapping import load_mapping


def test_loads_valid_mapping(tmp_path):
    mapping_file = tmp_path / "mapping.json"
    mapping_file.write_text(
        '{"ISS (ZARYA)": 25544, "NOAA 19": 33591}', encoding="utf-8"
    )

    result = load_mapping(str(mapping_file))

    assert result == {"ISS (ZARYA)": 25544, "NOAA 19": 33591}


def test_missing_file_raises_file_not_found_error(tmp_path):
    missing = tmp_path / "does_not_exist.json"

    with pytest.raises(FileNotFoundError):
        load_mapping(str(missing))


def test_invalid_json_raises_value_error(tmp_path):
    mapping_file = tmp_path / "mapping.json"
    mapping_file.write_text("{not valid json", encoding="utf-8")

    with pytest.raises(ValueError):
        load_mapping(str(mapping_file))


def test_non_object_json_raises_value_error(tmp_path):
    mapping_file = tmp_path / "mapping.json"
    mapping_file.write_text("[1, 2, 3]", encoding="utf-8")

    with pytest.raises(ValueError):
        load_mapping(str(mapping_file))


def test_non_int_value_raises_value_error(tmp_path):
    mapping_file = tmp_path / "mapping.json"
    mapping_file.write_text('{"ISS (ZARYA)": "25544"}', encoding="utf-8")

    with pytest.raises(ValueError):
        load_mapping(str(mapping_file))
