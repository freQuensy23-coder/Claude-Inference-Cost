#!/usr/bin/env python3
"""Geocode candidate store addresses and measure distance from Ben Gurion Blvd, Tel Aviv."""
import json, math, os, sys, time, urllib.parse, requests

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")
UA = {"User-Agent": "dr-pepper-availability-research/1.0"}
ORIGIN = (32.0835044, 34.7761551)  # שדרות דוד בן גוריון, Tel Aviv (OSM way 32904908)
CACHE_PATH = os.path.join(DATA, "geocache.json")
CACHE = json.load(open(CACHE_PATH)) if os.path.exists(CACHE_PATH) else {}


def haversine(a, b):
    R = 6371.0
    p1, p2 = math.radians(a[0]), math.radians(b[0])
    dp = p2 - p1
    dl = math.radians(b[1] - a[1])
    h = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * R * math.asin(math.sqrt(h))


def geocode(q):
    if q in CACHE:
        return CACHE[q]
    url = "https://nominatim.openstreetmap.org/search?" + urllib.parse.urlencode(
        {"format": "json", "limit": 1, "countrycodes": "il", "q": q})
    try:
        r = requests.get(url, headers=UA, timeout=60)
        js = r.json()
    except Exception:
        js = []
    res = (float(js[0]["lat"]), float(js[0]["lon"])) if js else None
    CACHE[q] = res
    json.dump(CACHE, open(CACHE_PATH, "w"))
    time.sleep(1.2)  # be polite to the public geocoder
    return res


if __name__ == "__main__":
    for q in sys.argv[1:]:
        p = geocode(q)
        if p:
            print("%-55s %.5f,%.5f  %.2f km" % (q[:55], p[0], p[1], haversine(ORIGIN, p)))
        else:
            print("%-55s  NOT FOUND" % q[:55])
