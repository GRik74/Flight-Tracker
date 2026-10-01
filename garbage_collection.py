def get_current_hex_codes(planes):
    codes = {
        plane.get("hex")
        for plane in planes
        if plane.get("hex")
    }

    return codes

def check_existing_hex_codes(list_dicts, current_codes):
    """Checks existing codes against codes in current aircraft list"""
    existing_codes = []
    stale_codes = []
    duplicate_codes = []

    for d in list_dicts:
        if not isinstance(d, dict): return None
        for hex in d.keys():
            existing_codes.append(hex)
            if existing_codes.count(hex) > 1:
                duplicate_codes.append(hex)

            if hex not in current_codes:
                stale_codes.append(hex)

    return stale_codes, duplicate_codes
    