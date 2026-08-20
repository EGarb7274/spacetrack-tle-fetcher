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
