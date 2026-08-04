#!/usr/bin/env python3
"""prices.carrefour.co.il (Carrefour / Yenot Bitan / Quik-branded stores)"""
import re, json, os, requests

BASE = "https://prices.carrefour.co.il"
S = requests.Session()
S.headers["User-Agent"] = "Mozilla/5.0 price-research/1.0"


def index(date=None):
    url = BASE + "/" if not date else BASE + "/?date=%s" % date
    h = S.get(url, timeout=120).text
    path = re.search(r"const path = '(\d+)'", h).group(1)
    files = json.loads(re.search(r'const files = (\[.*?\]);', h, re.S).group(1))
    branches = json.loads(re.search(r'const branches = (\{.*?\});', h, re.S).group(1))
    return path, [f["name"] for f in files], branches


def download(path, name, dest):
    r = S.get("%s/%s/%s" % (BASE, path, name), timeout=300, stream=True)
    r.raise_for_status()
    with open(dest, "wb") as f:
        for c in r.iter_content(1 << 16):
            f.write(c)
    return dest


if __name__ == "__main__":
    p, files, br = index()
    print("date", p, "files", len(files), "branches", len(br))
    print("stores files:", [f for f in files if f.lower().startswith("store")])
