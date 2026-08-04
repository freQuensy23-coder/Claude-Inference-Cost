#!/usr/bin/env python3
import os, re, json
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor
import carrefour as CF
import match
from scan_pp import iter_items, read_xml

HERE = os.path.dirname(os.path.abspath(__file__))
DATA, TMP = os.path.join(HERE, "data"), os.path.join(HERE, "tmp")
os.makedirs(TMP, exist_ok=True)
TA_TEXT = ("תל אביב", "תל-אביב", 'ת"א', "יפו", "רמת אביב")


def main():
    path, files, branches = CF.index()
    print("date", path, "files", len(files))
    stf = [f for f in files if f.lower().startswith("store")]
    dest = os.path.join(DATA, stf[0])
    if not os.path.exists(dest):
        CF.download(path, stf[0], dest)
    root = ET.fromstring(read_xml(dest))
    stores = []
    for st in root.iter():
        if st.tag.lower() not in ("store", "branch"):
            continue
        g = lambda *n: next(((c.text or "").strip() for c in st for x in n
                             if c.tag.lower() == x.lower()), "")
        sid = g("storeid")
        if not sid:
            continue
        stores.append({"store_id": sid, "store_name": g("storename"),
                       "address": g("address"), "city": g("city"),
                       "sub_chain": g("subchainname")})
    json.dump(stores, open(os.path.join(DATA, "carrefour_stores.json"), "w"),
              ensure_ascii=False, indent=1)
    print("carrefour stores:", len(stores))

    def is_ta(s):
        blob = " ".join([s["city"], s["store_name"], s["address"]])
        return s["city"].strip() in ("5000",) or any(t in blob for t in TA_TEXT)

    ta = [s for s in stores if is_ta(s)]
    print("TA stores:", len(ta))
    for s in ta:
        print("  ", s["store_id"], s["store_name"], "|", s["address"], "|", s["city"])

    idx = {}
    for fn in files:
        if not fn.lower().startswith("pricefull"):
            continue
        body = re.sub(r"(?i)^pricefull", "", fn)
        parts = re.split(r"[-.]", body)
        for i, p in enumerate(parts):
            if len(p) == 8 and p.isdigit() and p.startswith("20") and i >= 1:
                idx.setdefault(parts[i - 1].lstrip("0") or "0", []).append(fn)
                break
    print("pricefull store index:", len(idx))

    def work(s):
        k = s["store_id"].lstrip("0") or "0"
        if k not in idx:
            return {"store": s, "missing": True, "rows": []}
        fn = sorted(idx[k])[-1]
        d = os.path.join(TMP, fn)
        rows = []
        try:
            if not os.path.exists(d):
                CF.download(path, fn, d)
            for it in iter_items(d):
                nm = it.get("itemname") or it.get("itemnm") or ""
                if match.is_dr_pepper(nm, it.get("manufacturename", "")):
                    rows.append({"chain": "Carrefour/Yenot Bitan",
                                 "store_id": s["store_id"], "store_name": s["store_name"],
                                 "address": s["address"], "city": s["city"],
                                 "code": it.get("itemcode", ""), "name": nm,
                                 "price": it.get("itemprice", ""),
                                 "zero": match.is_zero(nm), "file": fn})
        except Exception as e:
            return {"store": s, "error": repr(e), "rows": []}
        finally:
            if os.path.exists(d):
                os.remove(d)
        return {"store": s, "rows": rows}

    res = []
    with ThreadPoolExecutor(max_workers=6) as ex:
        for r in ex.map(work, ta):
            res.append(r)
            for x in r["rows"]:
                print("HIT", x["store_id"], x["store_name"], "|", x["code"], x["name"],
                      x["price"], "ZERO" if x["zero"] else "")
    json.dump(res, open(os.path.join(DATA, "carrefour_scan.json"), "w"),
              ensure_ascii=False, indent=1)
    print("done", len(res), "missing:", len([r for r in res if r.get("missing")]))


if __name__ == "__main__":
    main()
