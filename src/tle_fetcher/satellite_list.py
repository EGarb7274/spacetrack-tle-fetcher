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
