import json
from pathlib import Path


def write_output(results: list[dict], path: str) -> None:
    """Write fetched TLE results to a JSON file (2-space indent, trailing newline)."""
    p = Path(path)
    with p.open("w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
        f.write("\n")
