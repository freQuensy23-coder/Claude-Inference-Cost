#!/usr/bin/env python3
"""prices.shufersal.co.il  (Shufersal Sheli / Deal / Yesh / BE / AM:PM-like 'Shufersal Express')"""
import re, os, requests
from html import unescape

BASE = "https://prices.shufersal.co.il"
CAT = {"price": 1, "pricefull": 2, "promo": 3, "promofull": 4, "stores": 5}
S = requests.Session()
S.headers["User-Agent"] = "Mozilla/5.0 price-research/1.0"


def list_files(cat="pricefull", store_id=0, max_pages=60):
    """Return [(filename, url)] across all pages."""
    out, seen = [], set()
    page = 1
    while page <= max_pages:
        u = "%s/FileObject/UpdateCategory?catID=%d&storeId=%d&page=%d" % (
            BASE, CAT[cat], store_id, page)
        h = S.get(u, timeout=120).text
        links = re.findall(r'href="(https://pricesprodpublic\.blob\.core\.windows\.net/[^"]+)"', h)
        links = [unescape(l) for l in links]
        if not links:
            break
        new = 0
        for l in links:
            fn = l.split("/")[-1].split("?")[0]
            if fn in seen:
                continue
            seen.add(fn)
            out.append((fn, l))
            new += 1
        if new == 0:
            break
        page += 1
    return out


def download(url, dest):
    r = S.get(url, timeout=300, stream=True)
    r.raise_for_status()
    with open(dest, "wb") as f:
        for c in r.iter_content(1 << 16):
            f.write(c)
    return dest


if __name__ == "__main__":
    st = list_files("stores")
    print("stores files:", st[:2], len(st))
    pf = list_files("pricefull")
    print("pricefull files:", len(pf))
    print(pf[0][0], pf[-1][0])
