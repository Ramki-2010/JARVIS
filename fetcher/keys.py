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
KEYWORD_MAX = 30
LOOKUPS = ("weather", "hn", "news")
