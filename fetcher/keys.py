"""Fixed names the user may refer to. Plain data: no network import, safe to import anywhere.

An utterance can only ever select one of these keys; it can never supply a coordinate, a host or an address.
"""

# key -> (spoken name, latitude, longitude, aliases). RK's list, 2026-11-13. The first key is the default.
PLACES = {
    "kumbakonam": ("Kumbakonam", 10.9621, 79.3912, ("kumbakonam", "kumbakonam tamil nadu")),
    "hosur": ("Hosur", 12.7365, 77.8326, ("hosur", "hosur tamil nadu")),
    "bangalore": ("Bangalore", 12.9716, 77.5946, ("bangalore", "bengaluru", "bangalore karnataka")),
    "thanjavur": ("Thanjavur", 10.7852, 79.1391, ("thanjavur", "tanjore", "tanjavur")),
    "chennai": ("Chennai", 13.0878, 80.2785, ("chennai", "madras")),
    "tirunelveli": ("Tirunelveli", 8.7274, 77.6838, ("tirunelveli", "nellai", "tinnevelly")),
}
DEFAULT_PLACE = "kumbakonam"

# Indian news sources: key -> (spoken name, host, path). The published addresses were measured on 2026-11-13.
NEWS = {
    "hindu": ("The Hindu", "www.thehindu.com", "/news/national/feeder/default.rss"),
    "hindu-business": ("The Hindu Business", "www.thehindu.com", "/business/feeder/default.rss"),
    "express": ("The Indian Express", "indianexpress.com", "/section/india/feed/"),
    "ndtv": ("NDTV", "feeds.feedburner.com", "/ndtvnews-india-news"),
    "toi": ("The Times of India", "timesofindia.indiatimes.com", "/rssfeedstopstories.cms"),
    "ht": ("Hindustan Times", "www.hindustantimes.com", "/feeds/rss/india-news/rssfeed.xml"),
}
NEWS_ALL = ("hindu", "express", "ndtv", "toi", "ht")  # "the news" with no source named: one headline each
NEWS_ALIASES = {
    "hindu": ("the hindu", "hindu"), "hindu-business": ("business", "the hindu business", "business news"),
    "express": ("indian express", "the indian express", "express"), "ndtv": ("ndtv",),
    "toi": ("times of india", "the times of india", "toi"), "ht": ("hindustan times", "ht"),
}
# Time zones for "what time is it in ...": key -> (spoken name, IANA zone, aliases). Offline: the zone data comes from the
# tzdata package (ADR-0014 section 4); no network is involved. HOME_ZONE is where "what time is it" is answered for.
HOME_ZONE = ("India", "Asia/Kolkata")
ZONES = {
    "india": ("India", "Asia/Kolkata", ("india", "delhi", "new delhi", "mumbai", "kolkata", "calcutta", "chennai", "bangalore", "bengaluru",
                                        "hosur", "kumbakonam", "thanjavur", "tanjore", "tirunelveli", "nellai", "madras", "ist")),
    "london": ("London", "Europe/London", ("london", "uk", "britain", "england")),
    "paris": ("Paris", "Europe/Paris", ("paris", "france")),
    "berlin": ("Berlin", "Europe/Berlin", ("berlin", "germany")),
    "moscow": ("Moscow", "Europe/Moscow", ("moscow", "russia")),
    "dubai": ("Dubai", "Asia/Dubai", ("dubai", "uae", "abu dhabi")),
    "singapore": ("Singapore", "Asia/Singapore", ("singapore",)),
    "hong kong": ("Hong Kong", "Asia/Hong_Kong", ("hong kong",)),
    "tokyo": ("Tokyo", "Asia/Tokyo", ("tokyo", "japan")),
    "sydney": ("Sydney", "Australia/Sydney", ("sydney", "australia")),
    "new york": ("New York", "America/New_York", ("new york", "new york city", "nyc", "washington")),
    "chicago": ("Chicago", "America/Chicago", ("chicago",)),
    "los angeles": ("Los Angeles", "America/Los_Angeles", ("los angeles", "la", "san francisco", "california", "seattle")),
    "toronto": ("Toronto", "America/Toronto", ("toronto", "canada")),
    "utc": ("UTC", "UTC", ("utc", "gmt", "greenwich")),
}
KEYWORD_MAX = 30
LOOKUPS = ("weather", "hn", "news")
