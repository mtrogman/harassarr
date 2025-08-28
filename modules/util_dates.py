# modules/util_dates.py
from datetime import datetime
import logging

# Parse many common formats; empty/None returns None without warning noise.
def parse_date_or_none(s: str | None):
    s = (s or "").strip()
    if not s:
        return None
    for fmt in ("%Y-%m-%d", "%Y-%m-%d %H:%M:%S", "%m/%d/%Y", "%m/%d/%y"):
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            continue
    logging.debug("Unrecognized date string: %r", s)
    return None
