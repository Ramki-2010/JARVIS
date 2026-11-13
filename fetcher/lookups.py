"""The three lookups. Each returns (data, hosts, byte count) or raises FetchFailed; only named fields leave (D3 item 6)."""

import json
import re
import threading
from urllib.parse import urlsplit

from fetcher import keys, net, rss
from fetcher.text import clean

WMO = {
    0: "clear", 1: "mostly clear", 2: "partly cloudy", 3: "overcast", 45: "foggy", 48: "foggy",
    51: "light drizzle", 53: "drizzle", 55: "heavy drizzle", 56: "freezing drizzle", 57: "freezing drizzle",
    61: "light rain", 63: "rain", 65: "heavy rain", 66: "freezing rain", 67: "freezing rain",
    71: "light snow", 73: "snow", 75: "heavy snow", 77: "snow grains", 80: "light showers", 81: "showers",
    82: "violent showers", 85: "snow showers", 86: "snow showers", 95: "a thunderstorm", 96: "a thunderstorm with hail",
    99: "a thunderstorm with hail",
}
STORIES = 5


class BadData(Exception):
    pass


def _number(value, low, high):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not (low <= value <= high):
        raise BadData("NUMBER")
    return round(float(value), 1)


def _json(data: bytes):
    try:
        return json.loads(data.decode("utf-8"))
    except (UnicodeDecodeError, ValueError):
        raise BadData("JSON") from None


def weather(place: str, get=net.get):
    if place not in keys.PLACES:
        raise net.FetchFailed("REFUSED")
    _name, lat, lon, _aliases = keys.PLACES[place]
    path = ("/v1/forecast?latitude=%.4f&longitude=%.4f&current=temperature_2m,apparent_temperature,weather_code,wind_speed_10m"
            "&daily=temperature_2m_max,temperature_2m_min,precipitation_probability_max&timezone=Asia%%2FKolkata&forecast_days=1") % (lat, lon)
    raw = get("api.open-meteo.com", path)
    doc = _json(raw)
    try:
        cur, day = doc["current"], doc["daily"]
        code = cur["weather_code"]
        data = {"place": place, "temp_c": _number(cur["temperature_2m"], -90, 70),
                "feels_c": _number(cur["apparent_temperature"], -90, 70),
                "conditions": WMO.get(code if isinstance(code, int) else -1, "unsettled"),
                "wind_kmh": _number(cur["wind_speed_10m"], 0, 500),
                "high_c": _number(day["temperature_2m_max"][0], -90, 70),
                "low_c": _number(day["temperature_2m_min"][0], -90, 70),
                "rain_pct": int(_number(day["precipitation_probability_max"][0], 0, 100))}
    except (KeyError, IndexError, TypeError):
        raise BadData("SHAPE") from None
    return data, ["api.open-meteo.com"], len(raw)


def hacker_news(get=net.get):
    host = "hacker-news.firebaseio.com"
    raw = get(host, "/v0/topstories.json")
    ids = _json(raw)
    if not isinstance(ids, list):
        raise BadData("SHAPE")
    ids = [i for i in ids[:STORIES] if isinstance(i, int) and not isinstance(i, bool) and 0 < i < 10 ** 10]
    if not ids:
        raise BadData("EMPTY")
    found = {}

    def one(story_id):
        try:
            blob = get(host, "/v0/item/%d.json" % story_id)
            found[story_id] = (blob, _json(blob))
        except (net.FetchFailed, BadData):
            pass

    workers = [threading.Thread(target=one, args=(i,)) for i in ids]
    for w in workers:
        w.start()
    for w in workers:
        w.join()
    total, stories = len(raw), []
    for story_id in ids:
        if story_id not in found:
            continue
        blob, item = found[story_id]
        total += len(blob)
        if not isinstance(item, dict) or not isinstance(item.get("title"), str):
            continue
        score = item.get("score")
        site = ""
        try:
            site = (urlsplit(item.get("url", "")).hostname or "") if isinstance(item.get("url"), str) else ""
        except ValueError:
            site = ""
        site = re.sub(r"^www\.", "", site)
        stories.append({"title": clean(item["title"], 140),
                        "score": score if isinstance(score, int) and not isinstance(score, bool) else 0,
                        "site": clean(site, 60)})
    if not stories:
        raise BadData("EMPTY")
    return {"stories": stories}, [host], total


def news(source: str, keyword: str = "", get=net.get):
    wanted = keys.NEWS_ALL if source == "all" else (source,)
    if any(s not in keys.NEWS for s in wanted):
        raise net.FetchFailed("REFUSED")
    results, failed, total = {}, [], [0]
    lock = threading.Lock()

    def one(key):
        _name, host, path = keys.NEWS[key]
        try:
            raw = get(host, path)
            items = rss.parse(raw)
            with lock:
                results[key] = items
                total[0] += len(raw)
        except (net.FetchFailed, rss.BadFeed):
            with lock:
                failed.append(key)

    workers = [threading.Thread(target=one, args=(k,)) for k in wanted]
    for w in workers:
        w.start()
    for w in workers:
        w.join()
    if not results:
        raise net.FetchFailed("NETWORK")
    kw = keyword.casefold()
    out = []
    for key in wanted:  # a fixed order
        if key not in results:
            continue
        items = [(t, when) for t, when in results[key] if not kw or kw in t.casefold()]
        limit = 1 if (source == "all" and not kw) else 4
        out += [{"source": keys.NEWS[key][0], "title": t, "time": when} for t, when in items[:limit]]
    hosts = sorted({keys.NEWS[k][1] for k in results})
    return {"items": out, "failed": [keys.NEWS[k][0] for k in failed if k in wanted], "keyword": kw}, hosts, total[0]
