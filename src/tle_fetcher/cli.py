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
