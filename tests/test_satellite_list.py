import pytest

from tle_fetcher.satellite_list import read_satellite_names


def test_reads_names_one_per_line(tmp_path):
    names_file = tmp_path / "names.txt"
    names_file.write_text("ISS (ZARYA)\nNOAA 19\n", encoding="utf-8")

    result = read_satellite_names(str(names_file))

    assert result == ["ISS (ZARYA)", "NOAA 19"]


def test_skips_blank_lines(tmp_path):
    names_file = tmp_path / "names.txt"
    names_file.write_text("ISS (ZARYA)\n\n   \nNOAA 19\n", encoding="utf-8")

    result = read_satellite_names(str(names_file))

    assert result == ["ISS (ZARYA)", "NOAA 19"]


def test_strips_surrounding_whitespace(tmp_path):
    names_file = tmp_path / "names.txt"
    names_file.write_text("  ISS (ZARYA)  \n", encoding="utf-8")

    result = read_satellite_names(str(names_file))

    assert result == ["ISS (ZARYA)"]


def test_missing_file_raises_file_not_found_error(tmp_path):
    missing = tmp_path / "does_not_exist.txt"

    with pytest.raises(FileNotFoundError):
        read_satellite_names(str(missing))
