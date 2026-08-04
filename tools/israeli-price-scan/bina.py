#!/usr/bin/env python3
"""binaprojects.com-hosted price portals (King Store, Good Pharm, Zol VeBegadol, ...)"""
import json, requests

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")

SITES = {
    "Bareket": "superbareket.binaprojects.com",
    "City Market Kiryat Gat": "citymarketkiryatgat.binaprojects.com",
    "Good Pharm": "goodpharm.binaprojects.com",
    "King Store": "kingstore.binaprojects.com",
    "Maayan 2000": "maayan2000.binaprojects.com",
    "Shefa Birkat Hashem": "shefabirkathashem.binaprojects.com",
    "Shuk HaIr": "shuk-hayir.binaprojects.com",
    "Super Sapir": "supersapir.binaprojects.com",
    "Zol VeBegadol": "zolvebegadol.binaprojects.com",
}


def session():
    s = requests.Session()
    s.headers.update({"User-Agent": UA, "Accept-Language": "he-IL,he;q=0.9,en;q=0.8"})
    return s


def list_files(host, s=None):
    s = s or session()
    r = s.get("https://%s/MainIO_Hok.aspx" % host, timeout=180)
    r.raise_for_status()
    return r.json()


def download_url(host, fname, s=None):
    """The portal exposes a redirect endpoint that returns the real blob url."""
    s = s or session()
    r = s.get("https://%s/Download.aspx" % host, params={"FileNm": fname},
              timeout=180, allow_redirects=True)
    return r


def download(host, fname, dest, s=None):
    """Download.aspx returns JSON [{"SPath": "<real blob url>"}]."""
    s = s or session()
    r = s.get("https://%s/Download.aspx" % host, params={"FileNm": fname}, timeout=180)
    r.raise_for_status()
    spath = r.json()[0]["SPath"]
    r2 = s.get(spath, timeout=300, stream=True)
    r2.raise_for_status()
    with open(dest, "wb") as f:
        for c in r2.iter_content(1 << 16):
            f.write(c)
    return dest


if __name__ == "__main__":
    s = session()
    for name, host in SITES.items():
        try:
            rows = list_files(host, s)
            pf = [r for r in rows if r["FileNm"].lower().startswith("pricefull")]
            print("%-24s %-40s files=%5d pricefull=%4d" % (name, host, len(rows), len(pf)))
        except Exception as e:
            print("%-24s %-40s FAIL %r" % (name, host, e))
