#!/usr/bin/env python3
"""Client for the shared Israeli price-transparency portal url.publishedprices.co.il"""
import re, sys, json, time
import requests

BASE = "https://url.publishedprices.co.il"


def login(user, password=""):
    s = requests.Session()
    s.headers["User-Agent"] = "Mozilla/5.0 (X11; Linux x86_64) price-research/1.0"
    r = s.get(BASE + "/login", timeout=60)
    r.raise_for_status()
    m = re.search(r'name="csrftoken"\s+content="([^"]+)"', r.text)
    if not m:
        m = re.search(r'name="csrftoken"[^>]*value="([^"]+)"', r.text)
    token = m.group(1)
    r = s.post(BASE + "/login/user",
               data={"username": user, "password": password, "csrftoken": token},
               timeout=60, allow_redirects=True)
    r.raise_for_status()
    if "/login" in r.url and "file" not in r.url:
        raise RuntimeError("login failed for %s (landed on %s)" % (user, r.url))
    # the csrf token rotates after login - take the fresh one from the file page
    r2 = s.get(BASE + "/file", timeout=60)
    m2 = re.search(r'name="csrftoken"\s+content="([^"]+)"', r2.text)
    s.csrftoken = m2.group(1) if m2 else token
    return s


def list_files(s, pattern="", cd="/"):
    """Returns list of dicts with keys incl. 'fname', 'size', 'time'."""
    out = []
    r = s.post(BASE + "/file/json/dir", timeout=120, data={
        "sEcho": "1", "iColumns": "5", "sColumns": ",,,,",
        "iDisplayStart": "0", "iDisplayLength": "100000",
        "mDataProp_0": "fname", "sSearch_0": "", "bRegex_0": "false",
        "mDataProp_1": "typeLabel", "mDataProp_2": "size",
        "mDataProp_3": "ftime", "mDataProp_4": "",
        "sSearch": pattern, "bRegex": "false",
        "iSortingCols": "0", "cd": cd,
        "csrftoken": getattr(s, "csrftoken", ""),
    })
    r.raise_for_status()
    data = r.json()
    for row in data.get("aaData", []):
        out.append(row)
    return out


def download(s, fname, dest, cd="/"):
    url = BASE + "/file/d/" + fname.lstrip("/")
    r = s.get(url, timeout=300, stream=True)
    r.raise_for_status()
    with open(dest, "wb") as f:
        for chunk in r.iter_content(1 << 16):
            f.write(chunk)
    return dest


if __name__ == "__main__":
    user = sys.argv[1]
    cd = sys.argv[2] if len(sys.argv) > 2 else "/"
    s = login(user)
    files = list_files(s, cd=cd)
    print(len(files), "files")
    for f in files[:20]:
        print(json.dumps(f, ensure_ascii=False))
