import json

import pytest

from tle_fetcher import cli


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


def _write(path, content):
    path.write_text(content, encoding="utf-8")
    return str(path)


def test_main_writes_output_on_success(tmp_path, monkeypatch):
    names_path = _write(tmp_path / "names.txt", "ISS (ZARYA)\n")
    mapping_path = _write(tmp_path / "mapping.json", '{"ISS (ZARYA)": 25544}')
    out_path = tmp_path / "out.json"

    monkeypatch.setattr(
        cli,
        "build_client",
        lambda: _StubClient({25544: {"line1": "1 25544U ...", "line2": "2 25544 ..."}}),
    )

    exit_code = cli.main([
        "--names", names_path,
        "--mapping", mapping_path,
        "--out", str(out_path),
    ])

    assert exit_code == 0
    with out_path.open("r", encoding="utf-8") as f:
        written = json.load(f)
    assert len(written) == 1
    assert written[0]["name"] == "ISS (ZARYA)"
    assert written[0]["norad_id"] == 25544


def test_main_returns_1_when_names_file_missing(tmp_path, monkeypatch, capsys):
    mapping_path = _write(tmp_path / "mapping.json", '{"ISS (ZARYA)": 25544}')
    out_path = tmp_path / "out.json"
    monkeypatch.setattr(cli, "build_client", lambda: _StubClient({}))

    exit_code = cli.main([
        "--names", str(tmp_path / "does_not_exist.txt"),
        "--mapping", mapping_path,
        "--out", str(out_path),
    ])

    assert exit_code == 1
    assert not out_path.exists()
    assert "ERROR" in capsys.readouterr().err


def test_main_returns_1_when_credentials_missing(tmp_path, monkeypatch):
    names_path = _write(tmp_path / "names.txt", "ISS (ZARYA)\n")
    mapping_path = _write(tmp_path / "mapping.json", '{"ISS (ZARYA)": 25544}')
    out_path = tmp_path / "out.json"

    from tle_fetcher.spacetrack_client import SpaceTrackAuthError

    def _raise():
        raise SpaceTrackAuthError("missing credentials")

    monkeypatch.setattr(cli, "build_client", _raise)

    exit_code = cli.main([
        "--names", names_path,
        "--mapping", mapping_path,
        "--out", str(out_path),
    ])

    assert exit_code == 1
    assert not out_path.exists()


def test_main_returns_1_when_nothing_resolves(tmp_path, monkeypatch):
    names_path = _write(tmp_path / "names.txt", "UNKNOWN SAT\n")
    mapping_path = _write(tmp_path / "mapping.json", '{"ISS (ZARYA)": 25544}')
    out_path = tmp_path / "out.json"
    monkeypatch.setattr(cli, "build_client", lambda: _StubClient({}))

    exit_code = cli.main([
        "--names", names_path,
        "--mapping", mapping_path,
        "--out", str(out_path),
    ])

    assert exit_code == 1
    assert not out_path.exists()
