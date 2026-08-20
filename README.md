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
