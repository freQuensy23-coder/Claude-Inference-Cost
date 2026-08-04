#!/usr/bin/env python3
"""Scan publishedprices chains' PriceFull files for Dr Pepper items.

Usage: scan_pp.py discover   -> one file per chain (a TA store when available)
       scan_pp.py full       -> every store of the chains listed in HITS
"""
import os, sys, re, gzip, json, time, io
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor, as_completed
import pp_client as P
import match

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")
CACHE = os.path.join(HERE, "cache")
os.makedirs(CACHE, exist_ok=True)

CHAINS = {
    "SuperCofixApp": ("Cofix", "/"),
    "doralon": ("Dor Alon / AM:PM", "/"),
    "freshmarket": ("Freshmarket / Super Dosh", "/"),
    "Keshet": ("Keshet Teamim", "/"),
    "osherad": ("Osher Ad", "/"),
    "politzer": ("Politzer", "/"),
    "RamiLevi": ("Rami Levy", "/"),
    "SalachD": ("Salah Dabah", "/"),
    "Stop_Market": ("Stop Market", "/"),
    "yuda_ho": ("Super Yuda", "/Yuda"),
    "TivTaam": ("Tiv Taam", "/"),
    "yohananof": ("Yohananof", "/"),
}


def read_xml(path):
    """Files are named .gz but some portals actually ship zip archives or plain xml."""
    with open(path, "rb") as f:
        raw = f.read()
    if raw[:2] == b"\x1f\x8b":
        try:
            raw = gzip.decompress(raw)
        except Exception:
            raw = gzip.GzipFile(fileobj=io.BytesIO(raw)).read()
    elif raw[:2] == b"PK":
        import zipfile
        z = zipfile.ZipFile(io.BytesIO(raw))
        raw = z.read(z.namelist()[0])
    i = raw.find(b"<")
    return raw[i:] if i >= 0 else raw


def iter_items(path):
    raw = read_xml(path)
    try:
        root = ET.fromstring(raw)
    except ET.ParseError:
        raw = re.sub(rb"&(?!(amp|lt|gt|quot|apos|#\d+);)", b"&amp;", raw)
        root = ET.fromstring(raw)
    store_id = ""
    for tag in ("StoreID", "StoreId", "STOREID"):
        el = root.find(tag)
        if el is not None and el.text:
            store_id = el.text.strip()
            break
    for it in root.iter():
        if it.tag.lower() not in ("item", "product"):
            continue
        d = {}
        for c in it:
            d[c.tag.lower()] = (c.text or "").strip()
        if "itemname" in d or "itemnm" in d:
            d["_store"] = store_id
            yield d


def name_of(d):
    return d.get("itemname") or d.get("itemnm") or ""


def store_files_index(user, cd):
    s = P.login(user)
    files = P.list_files(s, cd=cd)
    idx = {}
    for f in files:
        n = f["fname"]
        if not n.lower().startswith("pricefull"):
            continue
        m = re.match(r"(?i)pricefull(\d+)-(\d+)-(\d+)-(\d{8})-?(\d*)\.(gz|xml)", n)
        if m:
            sid = m.group(3)
        else:
            m2 = re.match(r"(?i)pricefull(\d+)-(\d+)-(\d{8})", n)
            if not m2:
                continue
            sid = m2.group(2)
        idx.setdefault(sid.lstrip("0") or "0", []).append(n)
    for k in idx:
        idx[k].sort()
    return s, idx


def scan_file(s, user, cd, fname):
    dest = os.path.join(CACHE, "%s__%s" % (user, fname))
    if not os.path.exists(dest) or os.path.getsize(dest) == 0:
        rel = fname if cd == "/" else cd.strip("/") + "/" + fname
        P.download(s, rel, dest)
    hits = []
    for d in iter_items(dest):
        nm = name_of(d)
        if match.is_dr_pepper(nm, d.get("manufacturename", "")) or match.loose_pepper(nm, d.get("manufacturename", "")):
            hits.append({
                "store": d.get("_store", ""),
                "code": d.get("itemcode", ""),
                "name": nm,
                "mfr": d.get("manufacturename", ""),
                "qty": d.get("quantity", ""),
                "unit": d.get("unitqty", ""),
                "price": d.get("itemprice", ""),
                "strict": match.is_dr_pepper(nm, d.get("manufacturename", "")),
                "zero": match.is_zero(nm, d.get("manufacturename", "")),
            })
    return hits


def discover():
    stores = json.load(open(os.path.join(DATA, "pp_stores.json")))
    out = {}
    for user, (label, cd) in CHAINS.items():
        try:
            s, idx = store_files_index(user, cd)
            mine = [st["store_id"] for st in stores if st["portal_user"] == user]
            ta = [st["store_id"] for st in stores if st["portal_user"] == user and
                  (st["city"].strip() == "5000" or "תל אביב" in st["address"] + st["store_name"] + st["city"])]
            pick = []
            for sid in (ta + mine):
                k = sid.lstrip("0") or "0"
                if k in idx and k not in pick:
                    pick.append(k)
                if len(pick) >= 3:
                    break
            allhits = []
            for k in pick:
                allhits += scan_file(s, user, cd, idx[k][-1])
            out[user] = {"label": label, "stores_probed": pick, "hits": allhits,
                         "n_price_stores": len(idx)}
            strict = [h for h in allhits if h["strict"]]
            print("%-16s %-24s probed=%s  drpepper=%d loose=%d" %
                  (user, label, pick, len(strict), len(allhits)))
            for h in strict:
                print("      ", h["code"], h["name"], h["price"], "ZERO" if h["zero"] else "")
        except Exception as e:
            print("!! FAIL", user, repr(e))
            out[user] = {"label": label, "error": repr(e)}
    json.dump(out, open(os.path.join(DATA, "pp_discover.json"), "w"), ensure_ascii=False, indent=1)


if __name__ == "__main__":
    discover()
