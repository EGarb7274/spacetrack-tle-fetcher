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
