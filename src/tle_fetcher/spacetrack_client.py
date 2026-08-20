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
