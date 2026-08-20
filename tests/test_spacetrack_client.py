import pytest

from tle_fetcher.spacetrack_client import (
    SpaceTrackAuthError,
    build_client,
    fetch_latest_tles,
)


def test_build_client_raises_when_user_missing(monkeypatch):
    monkeypatch.delenv("SPACETRACK_USER", raising=False)
    monkeypatch.setenv("SPACETRACK_PASS", "test_pass")

    with pytest.raises(SpaceTrackAuthError):
        build_client()


def test_build_client_raises_when_pass_missing(monkeypatch):
    monkeypatch.setenv("SPACETRACK_USER", "test_user")
    monkeypatch.delenv("SPACETRACK_PASS", raising=False)

    with pytest.raises(SpaceTrackAuthError):
        build_client()


class _FakeClient:
    def __init__(self, rows):
        self._rows = rows
        self.calls = []

    def tle_latest(self, norad_cat_id, ordinal, format):
        self.calls.append(list(norad_cat_id))
        return self._rows


def test_fetch_latest_tles_returns_data_by_norad_id():
    rows = [
        {"NORAD_CAT_ID": "25544", "TLE_LINE1": "1 25544U ...", "TLE_LINE2": "2 25544 ..."},
        {"NORAD_CAT_ID": "33591", "TLE_LINE1": "1 33591U ...", "TLE_LINE2": "2 33591 ..."},
    ]
    client = _FakeClient(rows)

    result = fetch_latest_tles(client, [25544, 33591])

    assert result == {
        25544: {"line1": "1 25544U ...", "line2": "2 25544 ..."},
        33591: {"line1": "1 33591U ...", "line2": "2 33591 ..."},
    }
    assert client.calls == [[25544, 33591]]


def test_fetch_latest_tles_missing_norad_id_absent_from_result():
    rows = [
        {"NORAD_CAT_ID": "25544", "TLE_LINE1": "1 25544U ...", "TLE_LINE2": "2 25544 ..."},
    ]
    client = _FakeClient(rows)

    result = fetch_latest_tles(client, [25544, 99999])

    assert result == {25544: {"line1": "1 25544U ...", "line2": "2 25544 ..."}}


def test_fetch_latest_tles_empty_input_makes_no_call():
    client = _FakeClient([])

    result = fetch_latest_tles(client, [])

    assert result == {}
    assert client.calls == []
