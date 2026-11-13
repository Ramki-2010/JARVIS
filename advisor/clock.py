"""Time and date answers, worked out offline from the machine clock and the tzdata package (ADR-0014 section 4).

No network, no model. A zone name comes only from the fixed table in fetcher.keys. If the zone data is missing the answer says so.
"""

from datetime import datetime, timezone
from typing import Callable, Optional, Tuple

from fetcher import keys

try:
    from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
except ImportError:  # pragma: no cover
    ZoneInfo = None


class NoZoneData(Exception):
    pass


def _zone(iana: str):
    try:
        return ZoneInfo(iana)
    except Exception:
        raise NoZoneData(iana) from None


def _clock(moment: datetime) -> str:
    hour = moment.hour % 12 or 12
    return "%d:%02d %s" % (hour, moment.minute, "in the morning" if moment.hour < 12 else "in the afternoon" if moment.hour < 17
                           else "in the evening" if moment.hour < 21 else "at night")


def time_text(key: str, now: Optional[Callable[[], datetime]] = None) -> Tuple[str, str]:
    """(shown, spoken) for the time at the home zone (key "") or at a key of keys.ZONES. Raises NoZoneData."""
    utc = (now or (lambda: datetime.now(timezone.utc)))()
    home_name, home_iana = keys.HOME_ZONE
    home = utc.astimezone(_zone(home_iana))
    if not key:
        shown = home.strftime("%A %d %B %Y, %H:%M IST")
        return shown, "It is %s, sir." % _clock(home)
    name, iana, _aliases = keys.ZONES[key]
    there = utc.astimezone(_zone(iana))
    gap = (there.date() - home.date()).days
    day = {0: "", 1: " tomorrow", -1: " yesterday"}.get(gap, "")
    abbr = there.tzname() or iana
    shown = "%s: %s (%s). India: %s" % (name, there.strftime("%A %d %B, %H:%M"), abbr, home.strftime("%H:%M IST"))
    return shown, "In %s it is %s%s, sir." % (name, _clock(there), day)


def date_text(now: Optional[Callable[[], datetime]] = None) -> Tuple[str, str]:
    utc = (now or (lambda: datetime.now(timezone.utc)))()
    home = utc.astimezone(_zone(keys.HOME_ZONE[1]))
    day = home.day
    suffix = "th" if 10 <= day % 100 <= 20 else {1: "st", 2: "nd", 3: "rd"}.get(day % 10, "th")
    return home.strftime("%A %d %B %Y"), "It is %s the %d%s of %s, %d, sir." % (home.strftime("%A"), day, suffix, home.strftime("%B"), home.year)
