#!/usr/bin/env python3
"""www.citymarket-shops.co.il — City Market price portal."""
import re, html, requests

BASE = "https://www.citymarket-shops.co.il"
S = requests.Session()
S.headers.update({"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/126.0",
                  "Accept-Language": "he-IL,he;q=0.9"})


def _clean(x):
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", "", x))).strip()


def page(params=None, p=None):
    q = dict(params or {})
    if p:
        q["p"] = p
    return S.get(BASE + "/", params=q, timeout=120).text


def stores(h=None):
    h = h or page()
    m = re.search(r'id="ddlStores".*?</select>', h, re.S)
    out = []
    for v, t in re.findall(r'<option value="([^"]*)"[^>]*>(.*?)</option>', m.group(0), re.S):
        if not v:
            continue
        out.append({"store_id": v, "label": _clean(t)})
    return out


def files(h):
    """Rows -> (filename, download_path)."""
    out = []
    for r in re.findall(r"<tr[^>]*>(.*?)</tr>", h, re.S):
        cells = [_clean(c) for c in re.findall(r"<td[^>]*>(.*?)</td>", r, re.S)]
        link = re.search(r'href="(/downloadFile/[^"]+)"', r)
        if len(cells) >= 4 and link:
            out.append({"time": cells[0], "store": cells[1], "name": cells[2],
                        "kind": cells[3], "url": BASE + link.group(1)})
    return out


def all_files(params):
    """Walk pagination until no new filenames appear."""
    out, seen = [], set()
    for p in range(1, 60):
        rows = files(page(params, p))
        new = [r for r in rows if r["name"] not in seen]
        if not new:
            break
        for r in new:
            seen.add(r["name"])
        out += new
    return out


def download(url, dest):
    r = S.get(url, timeout=300, stream=True)
    r.raise_for_status()
    with open(dest, "wb") as f:
        for c in r.iter_content(1 << 16):
            f.write(c)
    return dest


if __name__ == "__main__":
    h = page()
    st = stores(h)
    print("stores:", len(st))
    for s in st:
        if any(t in s["label"] for t in ("תל אביב", 'ת"א', "תל-אביב", "יפו")):
            print("  TA:", s["store_id"], s["label"])
    m = re.search(r'id="ddlFileType".*?</select>', h, re.S)
    print("types:", re.findall(r'<option value="([^"]*)"[^>]*>(.*?)</option>', m.group(0), re.S))
    m2 = re.search(r'id="ddlFileIsFull".*?</select>', h, re.S)
    print("full:", re.findall(r'<option value="([^"]*)"[^>]*>(.*?)</option>', m2.group(0), re.S))
