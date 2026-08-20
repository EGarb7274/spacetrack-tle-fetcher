import json

from tle_fetcher.writer import write_output


def test_writes_results_as_json(tmp_path):
    out_path = tmp_path / "out.json"
    results = [
        {
            "name": "ISS (ZARYA)",
            "norad_id": 25544,
            "line1": "1 25544U ...",
            "line2": "2 25544 ...",
            "fetched_at": "2026-08-20T14:32:00Z",
        }
    ]

    write_output(results, str(out_path))

    with out_path.open("r", encoding="utf-8") as f:
        loaded = json.load(f)
    assert loaded == results


def test_writes_empty_list(tmp_path):
    out_path = tmp_path / "out.json"

    write_output([], str(out_path))

    with out_path.open("r", encoding="utf-8") as f:
        loaded = json.load(f)
    assert loaded == []


def test_output_file_ends_with_newline(tmp_path):
    out_path = tmp_path / "out.json"

    write_output([], str(out_path))

    content = out_path.read_text(encoding="utf-8")
    assert content.endswith("\n")
