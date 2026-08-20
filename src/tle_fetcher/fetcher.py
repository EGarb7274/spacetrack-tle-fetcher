import logging
from datetime import datetime, timezone

from tle_fetcher.spacetrack_client import fetch_latest_tles

logger = logging.getLogger(__name__)


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
