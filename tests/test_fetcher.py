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
