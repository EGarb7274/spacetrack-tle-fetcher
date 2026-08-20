# spacetrack-tle-fetcher Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a CLI tool that fetches the latest TLE for a list of named satellites from Space-Track.org and writes them to a JSON file.

**Architecture:** A small modular Python package (`src/tle_fetcher/`) with one module per responsibility (name list reading, name→NORAD ID mapping, Space-Track auth/query, orchestration, JSON output) and a thin `argparse`-based CLI entrypoint. Space-Track authentication and querying goes through the third-party `spacetrack` library rather than hand-rolled HTTP.

**Tech Stack:** Python 3.10+, `spacetrack` (PyPI) for Space-Track.org access, `pytest` for testing.

## Global Constraints

- Space-Track credentials come ONLY from environment variables `SPACETRACK_USER` and `SPACETRACK_PASS` — never read from or written to a file, never committed.
- Output JSON records have exactly these fields: `name` (str), `norad_id` (int), `line1` (str), `line2` (str), `fetched_at` (str, ISO 8601 UTC, format `YYYY-MM-DDTHH:MM:SSZ`).
- Non-fatal (skip + log warning, continue run): a satellite name not found in the mapping file; a resolved NORAD ID with no TLE returned by Space-Track.
- Fatal (print error to stderr, exit code 1, write nothing): `--names` file not found; `--mapping` file not found or invalid; missing/empty Space-Track credentials; every satellite name in the run fails to resolve (empty resolved batch).
- No test in this plan hits the real network or requires real Space-Track credentials — `spacetrack.SpaceTrackClient` is always mocked/stubbed in tests.

---

### Task 1: Project scaffolding + satellite name list reader

**Files:**
- Create: `pyproject.toml`
- Create: `requirements.txt`
- Create: `requirements-dev.txt`
- Create: `.gitignore`
- Create: `src/tle_fetcher/__init__.py`
- Create: `src/tle_fetcher/satellite_list.py`
- Test: `tests/test_satellite_list.py`

**Interfaces:**
- Produces: `read_satellite_names(path: str) -> list[str]` — reads one satellite name per line, strips whitespace, skips blank lines, raises `FileNotFoundError` if `path` doesn't exist.

- [ ] **Step 1: Create project scaffolding files**

`pyproject.toml`:
```toml
[project]
name = "tle-fetcher"
version = "0.1.0"
requires-python = ">=3.10"

[tool.pytest.ini_options]
pythonpath = ["src"]
testpaths = ["tests"]
```

`requirements.txt`:
```
spacetrack
```

`requirements-dev.txt`:
```
-r requirements.txt
pytest
```

`.gitignore`:
```
__pycache__/
*.pyc
.pytest_cache/
.env
venv/
*.egg-info/
```

`src/tle_fetcher/__init__.py`:
```python
```
(empty file)

- [ ] **Step 2: Install dependencies**

Run: `pip install -r requirements-dev.txt`
Expected: `spacetrack` and `pytest` install successfully (needed for every task's test run from here on)

- [ ] **Step 3: Write the failing test**

`tests/test_satellite_list.py`:
```python
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
```

- [ ] **Step 4: Run test to verify it fails**

Run: `pytest tests/test_satellite_list.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'tle_fetcher.satellite_list'` (or similar import error)

- [ ] **Step 5: Write minimal implementation**

`src/tle_fetcher/satellite_list.py`:
```python
from pathlib import Path


def read_satellite_names(path: str) -> list[str]:
    """Read satellite names from a text file, one per line.

    Blank lines and lines that are only whitespace are skipped. Leading
    and trailing whitespace on each name is stripped.

    Raises FileNotFoundError if the file does not exist.
    """
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Satellite name list not found: {path}")

    names = []
    with p.open("r", encoding="utf-8") as f:
        for line in f:
            stripped = line.strip()
            if stripped:
                names.append(stripped)
    return names
```

- [ ] **Step 6: Run test to verify it passes**

Run: `pytest tests/test_satellite_list.py -v`
Expected: PASS (4 passed)

- [ ] **Step 7: Commit**

```bash
git add pyproject.toml requirements.txt requirements-dev.txt .gitignore src/tle_fetcher/__init__.py src/tle_fetcher/satellite_list.py tests/test_satellite_list.py
git commit -m "feat: project scaffolding and satellite name list reader"
```

---

### Task 2: Name-to-NORAD-ID mapping loader

**Files:**
- Create: `src/tle_fetcher/mapping.py`
- Test: `tests/test_mapping.py`

**Interfaces:**
- Produces: `load_mapping(path: str) -> dict[str, int]` — loads a JSON object mapping satellite name to NORAD ID. Raises `FileNotFoundError` if `path` doesn't exist. Raises `ValueError` if the file isn't valid JSON, isn't a JSON object, or contains a value that isn't `str -> int`.

- [ ] **Step 1: Write the failing test**

`tests/test_mapping.py`:
```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_mapping.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'tle_fetcher.mapping'`

- [ ] **Step 3: Write minimal implementation**

`src/tle_fetcher/mapping.py`:
```python
import json
from pathlib import Path


def load_mapping(path: str) -> dict[str, int]:
    """Load the satellite name -> NORAD ID mapping from a JSON file.

    Raises FileNotFoundError if the file does not exist.
    Raises ValueError if the file is not valid JSON, is not a flat JSON
    object, or contains any value that is not an int.
    """
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Mapping file not found: {path}")

    with p.open("r", encoding="utf-8") as f:
        try:
            data = json.load(f)
        except json.JSONDecodeError as e:
            raise ValueError(f"Mapping file is not valid JSON: {path}") from e

    if not isinstance(data, dict):
        raise ValueError(f"Mapping file must contain a JSON object: {path}")

    result: dict[str, int] = {}
    for name, norad_id in data.items():
        if not isinstance(name, str) or not isinstance(norad_id, int):
            raise ValueError(
                f"Mapping file entries must be string -> int, got "
                f"{name!r} -> {norad_id!r}"
            )
        result[name] = norad_id
    return result
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_mapping.py -v`
Expected: PASS (5 passed)

- [ ] **Step 5: Commit**

```bash
git add src/tle_fetcher/mapping.py tests/test_mapping.py
git commit -m "feat: name-to-NORAD-ID mapping loader"
```

---

### Task 3: Name resolution logic

**Files:**
- Create: `src/tle_fetcher/fetcher.py`
- Test: `tests/test_fetcher.py`

**Interfaces:**
- Consumes: nothing from earlier tasks (pure function over plain `list`/`dict`).
- Produces: `resolve_names(names: list[str], mapping: dict[str, int]) -> tuple[dict[str, int], list[str]]` — returns `(resolved, unresolved)` where `resolved` maps each found name to its NORAD ID (insertion order = input order) and `unresolved` lists names not present in `mapping`, in input order.

- [ ] **Step 1: Write the failing test**

`tests/test_fetcher.py`:
```python
from tle_fetcher.fetcher import resolve_names


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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_fetcher.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'tle_fetcher.fetcher'`

- [ ] **Step 3: Write minimal implementation**

`src/tle_fetcher/fetcher.py`:
```python
def resolve_names(
    names: list[str], mapping: dict[str, int]
) -> tuple[dict[str, int], list[str]]:
    """Resolve satellite names to NORAD IDs using the mapping.

    Returns (resolved, unresolved):
    - resolved: dict of name -> norad_id for names found in the mapping,
      in input order.
    - unresolved: list of names not found in the mapping, in input order.
    """
    resolved: dict[str, int] = {}
    unresolved: list[str] = []
    for name in names:
        if name in mapping:
            resolved[name] = mapping[name]
        else:
            unresolved.append(name)
    return resolved, unresolved
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_fetcher.py -v`
Expected: PASS (4 passed)

- [ ] **Step 5: Commit**

```bash
git add src/tle_fetcher/fetcher.py tests/test_fetcher.py
git commit -m "feat: satellite name resolution logic"
```

---

### Task 4: Space-Track client wrapper

**Files:**
- Create: `src/tle_fetcher/spacetrack_client.py`
- Test: `tests/test_spacetrack_client.py`

**Interfaces:**
- Produces:
  - `SpaceTrackAuthError(RuntimeError)` — raised when credentials are missing.
  - `build_client() -> spacetrack.SpaceTrackClient` — reads `SPACETRACK_USER`/`SPACETRACK_PASS` from env; raises `SpaceTrackAuthError` if either is missing or empty.
  - `fetch_latest_tles(client, norad_ids: list[int]) -> dict[int, dict[str, str]]` — calls `client.tle_latest(norad_cat_id=norad_ids, ordinal=1, format="json")` and returns `{norad_id: {"line1": ..., "line2": ...}}` for every NORAD ID Space-Track returned data for. Returns `{}` immediately (no call made) if `norad_ids` is empty.

- [ ] **Step 1: Write the failing test**

`tests/test_spacetrack_client.py`:
```python
import pytest

from tle_fetcher.spacetrack_client import (
    SpaceTrackAuthError,
    build_client,
    fetch_latest_tles,
)


def test_build_client_succeeds_with_env_vars(monkeypatch):
    monkeypatch.setenv("SPACETRACK_USER", "test_user")
    monkeypatch.setenv("SPACETRACK_PASS", "test_pass")

    client = build_client()

    assert client is not None


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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_spacetrack_client.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'tle_fetcher.spacetrack_client'`

- [ ] **Step 3: Write minimal implementation**

`src/tle_fetcher/spacetrack_client.py`:
```python
import os

from spacetrack import SpaceTrackClient


class SpaceTrackAuthError(RuntimeError):
    """Raised when Space-Track credentials are missing or invalid."""


def build_client() -> SpaceTrackClient:
    """Build an authenticated SpaceTrackClient from environment variables.

    Reads SPACETRACK_USER and SPACETRACK_PASS. Raises SpaceTrackAuthError
    if either is missing or empty.
    """
    user = os.environ.get("SPACETRACK_USER")
    password = os.environ.get("SPACETRACK_PASS")
    if not user or not password:
        raise SpaceTrackAuthError(
            "SPACETRACK_USER and SPACETRACK_PASS environment variables "
            "must both be set"
        )
    return SpaceTrackClient(identity=user, password=password)


def fetch_latest_tles(client, norad_ids: list[int]) -> dict[int, dict[str, str]]:
    """Fetch the latest TLE for each given NORAD ID.

    Returns a dict of norad_id -> {"line1": ..., "line2": ...} for every
    NORAD ID that Space-Track returned a TLE for. NORAD IDs with no TLE
    available are simply absent from the result. Returns {} immediately
    if norad_ids is empty (no network call made).
    """
    if not norad_ids:
        return {}

    rows = client.tle_latest(norad_cat_id=norad_ids, ordinal=1, format="json")

    result: dict[int, dict[str, str]] = {}
    for row in rows:
        norad_id = int(row["NORAD_CAT_ID"])
        result[norad_id] = {
            "line1": row["TLE_LINE1"],
            "line2": row["TLE_LINE2"],
        }
    return result
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_spacetrack_client.py -v`
Expected: PASS (6 passed)

- [ ] **Step 5: Commit**

```bash
git add src/tle_fetcher/spacetrack_client.py tests/test_spacetrack_client.py
git commit -m "feat: Space-Track client wrapper for auth and TLE fetching"
```

---

### Task 5: Fetch orchestrator

**Files:**
- Modify: `src/tle_fetcher/fetcher.py` (add to the file created in Task 3)
- Test: `tests/test_fetcher.py` (add to the file created in Task 3)

**Interfaces:**
- Consumes: `resolve_names` (Task 3, same file); `fetch_latest_tles(client, norad_ids: list[int]) -> dict[int, dict[str, str]]` (Task 4, `tle_fetcher.spacetrack_client`).
- Produces: `fetch_tles(names: list[str], mapping: dict[str, int], client) -> list[dict]` — returns a list of `{"name": str, "norad_id": int, "line1": str, "line2": str, "fetched_at": str}` dicts for every satellite successfully resolved and fetched. Logs a warning (via the standard `logging` module, logger name `tle_fetcher.fetcher`) for each unresolved name and each resolved NORAD ID with no TLE returned. Raises `ValueError` if zero names resolve.

- [ ] **Step 1: Write the failing test**

Append to `tests/test_fetcher.py`:
```python
import logging

from tle_fetcher.fetcher import fetch_tles


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
```

Also add `import pytest` at the top of `tests/test_fetcher.py` if not already present (it is not, since Task 3's version didn't need it).

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_fetcher.py -v`
Expected: FAIL — `AttributeError` / `ImportError` because `fetch_tles` does not exist yet

- [ ] **Step 3: Write minimal implementation**

Add to `src/tle_fetcher/fetcher.py` (below `resolve_names`):
```python
import logging
from datetime import datetime, timezone

from tle_fetcher.spacetrack_client import fetch_latest_tles

logger = logging.getLogger(__name__)


def fetch_tles(names: list[str], mapping: dict[str, int], client) -> list[dict]:
    """Resolve satellite names to NORAD IDs, fetch their latest TLEs, and
    assemble output records.

    Names not found in the mapping, and resolved NORAD IDs with no TLE
    returned, are logged as warnings and excluded from the result.

    Raises ValueError if no names resolve to a NORAD ID.
    """
    resolved, unresolved = resolve_names(names, mapping)
    for name in unresolved:
        logger.warning('no NORAD ID mapping for "%s", skipping', name)

    if not resolved:
        raise ValueError("no satellite names could be resolved to NORAD IDs")

    norad_ids = list(resolved.values())
    tle_by_id = fetch_latest_tles(client, norad_ids)

    fetched_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    results: list[dict] = []
    for name, norad_id in resolved.items():
        tle = tle_by_id.get(norad_id)
        if tle is None:
            logger.warning(
                'no TLE returned for NORAD ID %s ("%s"), skipping',
                norad_id,
                name,
            )
            continue
        results.append({
            "name": name,
            "norad_id": norad_id,
            "line1": tle["line1"],
            "line2": tle["line2"],
            "fetched_at": fetched_at,
        })
    return results
```

Move the top-of-file imports (`import pytest` in the test file, and the new `import logging` / `from datetime import ...` / `from tle_fetcher.spacetrack_client import fetch_latest_tles` in `fetcher.py`) to the top of each file rather than inline, per normal Python style.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_fetcher.py -v`
Expected: PASS (8 passed — 4 from Task 3 + 4 new)

- [ ] **Step 5: Commit**

```bash
git add src/tle_fetcher/fetcher.py tests/test_fetcher.py
git commit -m "feat: fetch orchestrator combining resolution and Space-Track fetch"
```

---

### Task 6: JSON output writer

**Files:**
- Create: `src/tle_fetcher/writer.py`
- Test: `tests/test_writer.py`

**Interfaces:**
- Consumes: a `list[dict]` shaped like `fetch_tles`'s return value (Task 5) — not directly imported, just the same shape.
- Produces: `write_output(results: list[dict], path: str) -> None` — writes `results` to `path` as indented JSON (2-space indent) with a trailing newline.

- [ ] **Step 1: Write the failing test**

`tests/test_writer.py`:
```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_writer.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'tle_fetcher.writer'`

- [ ] **Step 3: Write minimal implementation**

`src/tle_fetcher/writer.py`:
```python
import json
from pathlib import Path


def write_output(results: list[dict], path: str) -> None:
    """Write fetched TLE results to a JSON file (2-space indent, trailing newline)."""
    p = Path(path)
    with p.open("w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
        f.write("\n")
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_writer.py -v`
Expected: PASS (3 passed)

- [ ] **Step 5: Commit**

```bash
git add src/tle_fetcher/writer.py tests/test_writer.py
git commit -m "feat: JSON output writer"
```

---

### Task 7: CLI entrypoint, README, and end-to-end wiring

**Files:**
- Create: `src/tle_fetcher/cli.py`
- Create: `README.md`
- Test: `tests/test_cli.py`

**Interfaces:**
- Consumes: `satellite_list.read_satellite_names` (Task 1), `mapping.load_mapping` (Task 2), `fetcher.fetch_tles` (Task 5), `writer.write_output` (Task 6), `spacetrack_client.build_client` / `spacetrack_client.SpaceTrackAuthError` (Task 4).
- Produces: `build_parser() -> argparse.ArgumentParser`; `main(argv: list[str] | None = None) -> int` — returns `0` on success, `1` on any fatal error (see Global Constraints).

- [ ] **Step 1: Write the failing test**

`tests/test_cli.py`:
```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_cli.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'tle_fetcher.cli'`

- [ ] **Step 3: Write minimal implementation**

`src/tle_fetcher/cli.py`:
```python
import argparse
import logging
import sys

from tle_fetcher import fetcher, mapping as mapping_module, satellite_list, writer
from tle_fetcher.spacetrack_client import SpaceTrackAuthError, build_client


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Fetch current TLEs for a list of satellites from Space-Track.org"
    )
    parser.add_argument(
        "--names", required=True, help="Path to satellite name list (one per line)"
    )
    parser.add_argument(
        "--mapping", required=True, help="Path to name->NORAD ID JSON mapping file"
    )
    parser.add_argument("--out", required=True, help="Path to write output JSON")
    return parser


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        names = satellite_list.read_satellite_names(args.names)
    except FileNotFoundError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1

    try:
        name_map = mapping_module.load_mapping(args.mapping)
    except (FileNotFoundError, ValueError) as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1

    try:
        client = build_client()
    except SpaceTrackAuthError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1

    try:
        results = fetcher.fetch_tles(names, name_map, client)
    except ValueError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1

    writer.write_output(results, args.out)
    print(f"Wrote {len(results)} TLE(s) to {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_cli.py -v`
Expected: PASS (4 passed)

- [ ] **Step 5: Run the full test suite**

Run: `pytest -v`
Expected: All tests across all files PASS (30 passed)

- [ ] **Step 6: Write the README**

`README.md`:
```markdown
# spacetrack-tle-fetcher

Fetches the current TLE (Two-Line Element) for a list of named satellites
from Space-Track.org and writes them to a JSON file.

## Setup

1. Install dependencies:
   ```
   pip install -r requirements.txt
   ```
2. Set your Space-Track.org credentials as environment variables:
   ```
   export SPACETRACK_USER="your_username"
   export SPACETRACK_PASS="your_password"
   ```
3. Create a satellite name list — a plain text file, one name per line:
   ```
   ISS (ZARYA)
   NOAA 19
   ```
4. Create a name -> NORAD ID mapping file (JSON):
   ```json
   {
     "ISS (ZARYA)": 25544,
     "NOAA 19": 33591
   }
   ```

## Usage

```
python -m tle_fetcher.cli --names names.txt --mapping mapping.json --out tles.json
```

Satellite names not found in the mapping file, or NORAD IDs Space-Track
has no current TLE for, are skipped with a warning — the run still
succeeds and writes whatever was successfully fetched.

## Development

```
pip install -r requirements-dev.txt
pytest
```
```

- [ ] **Step 7: Commit**

```bash
git add src/tle_fetcher/cli.py tests/test_cli.py README.md
git commit -m "feat: CLI entrypoint and README"
```

- [ ] **Step 8: Push**

```bash
git push
```
