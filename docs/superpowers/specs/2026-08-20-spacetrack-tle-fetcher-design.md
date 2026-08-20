# spacetrack-tle-fetcher — Design Spec

Date: 2026-08-20

## Purpose

A standalone tool that fetches the current TLE (Two-Line Element) for a
user-specified list of satellites from Space-Track.org and writes them to a
local JSON file. This is the first piece of a larger project: a future
"TLE checker" that will compare these freshly fetched TLEs against TLEs
stored in a separate system to detect drift/staleness. That comparison
project is out of scope here — this project only fetches and saves.

## Inputs

- **Satellite name list**: a plain text file, one satellite name per line
  (e.g. `ISS (ZARYA)`).
- **Name → NORAD ID mapping**: a manually maintained JSON file mapping
  satellite name (string, exact match) to NORAD catalog ID (int), e.g.:
  ```json
  { "ISS (ZARYA)": 25544 }
  ```
  This file is hand-edited by the user as their satellite list changes; the
  tool does not auto-populate or auto-update it.
- **Space-Track credentials**: read from environment variables
  `SPACETRACK_USER` and `SPACETRACK_PASS` (never stored in a file or
  committed to source control).

## Architecture

A small modular Python package with a CLI entrypoint. Space-Track
authentication and querying is handled via the third-party `spacetrack`
PyPI library rather than hand-rolled HTTP/session code, since it already
implements Space-Track's cookie-based login flow, session reuse, and rate
limiting.

Modular structure is chosen (over a single script) because the future
comparison project is expected to reuse the fetch logic directly (as an
import), rather than needing to shell out to this tool.

### Components

- **`mapping.py`** — loads and parses the name→NORAD ID JSON mapping file
  into a dict.
- **`satellite_list.py`** — reads the input text file of satellite names
  into a list of strings (one per non-empty line).
- **`spacetrack_client.py`** — thin wrapper around
  `spacetrack.SpaceTrackClient`. Reads `SPACETRACK_USER`/`SPACETRACK_PASS`
  from the environment, authenticates, and exposes a function to fetch the
  latest TLE for a batch of NORAD IDs.
- **`fetcher.py`** — orchestrator. Resolves each satellite name to a NORAD
  ID via the mapping, calls `spacetrack_client` for the resolved IDs, and
  applies skip-and-warn handling for unresolved names or missing TLEs.
- **`writer.py`** — serializes fetched results to the output JSON file.
- **`cli.py`** — argument parsing and entrypoint. Flags:
  `--names <path>` (satellite name list, required)
  `--mapping <path>` (name→NORAD ID mapping file, required)
  `--out <path>` (output JSON path, required)

## Data Flow

1. Read satellite names from `--names`.
2. For each name, look it up in the mapping loaded from `--mapping`.
   - If not found: log a warning (`WARNING: no NORAD ID mapping for
     "<name>", skipping`) and exclude it from the fetch batch.
3. Authenticate to Space-Track using env var credentials via
   `spacetrack_client`.
4. Batch-query the latest TLE for all resolved NORAD IDs in a single
   request.
5. For any NORAD ID with no TLE returned: log a warning (`WARNING: no TLE
   returned for NORAD ID <id> ("<name>"), skipping`) and exclude it from
   the output.
6. Write all successfully fetched results to the `--out` JSON file as a
   list of objects:
   ```json
   [
     {
       "name": "ISS (ZARYA)",
       "norad_id": 25544,
       "line1": "1 25544U 98067A   ...",
       "line2": "2 25544  51.6416 ...",
       "fetched_at": "2026-08-20T14:32:00Z"
     }
   ]
   ```
   `fetched_at` is the UTC timestamp at which the fetch ran, in ISO 8601
   format.

## Error Handling

- **Unresolved satellite name** (not in mapping file) or **no TLE returned**
  for a resolved NORAD ID: non-fatal. Log a warning and continue; that
  satellite is simply absent from the output file. The run still succeeds
  (exit code 0) as long as at least the fetch step itself completed.
- **Input file (`--names`) or mapping file (`--mapping`) not found**: fatal.
  Print a clear error and exit non-zero before attempting any network call.
- **Space-Track authentication failure** (bad/missing credentials): fatal.
  Print a clear error and exit non-zero; nothing is written to the output
  file.
- **Empty resolved-ID batch** (every name in the input file failed to
  resolve): fatal. Print a clear error and exit non-zero rather than
  writing an empty output file silently.

## Testing

- Unit tests for `mapping.py` (parses valid/invalid JSON, missing file)
  and `fetcher.py`'s name-resolution and skip logic — pure functions, no
  network access needed.
- Unit tests for `writer.py`'s JSON serialization (correct shape, ISO 8601
  timestamp format).
- `spacetrack_client.py` is tested with `spacetrack.SpaceTrackClient`
  mocked out, so the test suite never hits the real network or needs real
  credentials.
- No live-network integration test is included in this scope; manual
  verification against the real Space-Track API is done by running the CLI
  directly with real credentials.

## Out of Scope

- Comparing fetched TLEs against any other system (the future "checker"
  project).
- Auto-building or auto-updating the name→NORAD ID mapping file.
- Historical storage of TLEs over time (each run overwrites `--out`; no
  database, no versioning).
- Scheduling/automation of runs (e.g. cron) — this project is invoked
  manually for now.
