import logging

import pytest

from tle_fetcher.fetcher import fetch_tles, resolve_names


def test_resolves_known_names():
    names = ["ISS (ZARYA)", "NOAA 19"]
    mapping = {"ISS (ZARYA)": 25544, "NOAA 19": 33591}

    resolved, unresolved = resolve_names(names, mapping)

    assert resolved == {"ISS (ZARYA)": 25544, "NOAA 19": 33591}
    assert unresolved == []


def test_unresolved_names_are_reported_and_excluded():
    names = ["ISS (ZARYA)", "UNKNOWN SAT"]
    mapping = {"ISS (ZARYA)": 25544}

    resolved, unresolved = resolve_names(names, mapping)

    assert resolved == {"ISS (ZARYA)": 25544}
    assert unresolved == ["UNKNOWN SAT"]


def test_all_unresolved():
    names = ["UNKNOWN SAT"]
    mapping = {"ISS (ZARYA)": 25544}

    resolved, unresolved = resolve_names(names, mapping)

    assert resolved == {}
    assert unresolved == ["UNKNOWN SAT"]


def test_empty_names_list():
    resolved, unresolved = resolve_names([], {"ISS (ZARYA)": 25544})

    assert resolved == {}
    assert unresolved == []


class _StubClient:
    def __init__(self, tle_by_id):
        self._tle_by_id = tle_by_id

    def tle_latest(self, norad_cat_id, ordinal, format):
        rows = []
        for norad_id in norad_cat_id:
            if norad_id in self._tle_by_id:
                rows.append({
                    "NORAD_CAT_ID": str(norad_id),
                    "TLE_LINE1": self._tle_by_id[norad_id]["line1"],
                    "TLE_LINE2": self._tle_by_id[norad_id]["line2"],
                })
        return rows


def test_fetch_tles_returns_full_records():
    names = ["ISS (ZARYA)"]
    mapping = {"ISS (ZARYA)": 25544}
    client = _StubClient({25544: {"line1": "1 25544U ...", "line2": "2 25544 ..."}})

    results = fetch_tles(names, mapping, client)

    assert len(results) == 1
    record = results[0]
    assert record["name"] == "ISS (ZARYA)"
    assert record["norad_id"] == 25544
    assert record["line1"] == "1 25544U ..."
    assert record["line2"] == "2 25544 ..."
    assert record["fetched_at"].endswith("Z")


def test_fetch_tles_skips_unresolved_name_with_warning(caplog):
    names = ["ISS (ZARYA)", "UNKNOWN SAT"]
    mapping = {"ISS (ZARYA)": 25544}
    client = _StubClient({25544: {"line1": "1 25544U ...", "line2": "2 25544 ..."}})

    with caplog.at_level(logging.WARNING):
        results = fetch_tles(names, mapping, client)

    assert len(results) == 1
    assert any("UNKNOWN SAT" in message for message in caplog.messages)


def test_fetch_tles_skips_missing_tle_with_warning(caplog):
    names = ["ISS (ZARYA)"]
    mapping = {"ISS (ZARYA)": 25544}
    client = _StubClient({})  # Space-Track returns nothing for 25544

    with caplog.at_level(logging.WARNING):
        results = fetch_tles(names, mapping, client)

    assert results == []
    assert any("25544" in message for message in caplog.messages)


def test_fetch_tles_raises_when_nothing_resolves():
    names = ["UNKNOWN SAT"]
    mapping = {"ISS (ZARYA)": 25544}
    client = _StubClient({})

    with pytest.raises(ValueError):
        fetch_tles(names, mapping, client)
