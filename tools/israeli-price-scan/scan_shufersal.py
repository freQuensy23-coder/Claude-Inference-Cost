#!/usr/bin/env python3
import os, re, json, gzip
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor
import shufersal as SH
import match
from scan_pp import iter_items

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")
TMP = os.path.join(HERE, "tmp")
os.makedirs(TMP, exist_ok=True)
TA_TEXT = ("תל אביב", "תל-אביב", 'ת"א', "יפו", "רמת אביב")


def stores():
    xml = open(os.path.join(DATA, "shufersal_stores.xml"), "rb").read()
    i = xml.find(b"<Chain")
    root = ET.fromstring(xml[i:])
    out = []
    for sc in root.iter("SubChain"):
        scn = (sc.findtext("SubChainName") or "").strip()
        scid = (sc.findtext("SubChainID") or "").strip()
        for st in sc.iter("Store"):
            out.append({
                "sub_chain_id": scid, "sub_chain": scn,
                "store_id": (st.findtext("StoreID") or "").strip(),
                "store_name": (st.findtext("StoreName") or "").strip(),
                "address": (st.findtext("Address") or "").strip(),
                "city": (st.findtext("City") or "").strip(),
            })
    return out


def is_ta(st):
    blob = " ".join([st["city"], st["store_name"], st["address"]])
    return st["city"].strip() == "5000" or any(t in blob for t in TA_TEXT)


def main():
    sts = stores()
    ta = [s for s in sts if is_ta(s)]
    json.dump(sts, open(os.path.join(DATA, "shufersal_stores.json"), "w"),
              ensure_ascii=False, indent=1)
    print("shufersal stores:", len(sts), "TA:", len(ta))
    pf = SH.list_files("pricefull")
    idx = {}
    for fn, url in pf:
        body = re.sub(r"(?i)^pricefull", "", fn)
        parts = re.split(r"[-.]", body)
        for i, p in enumerate(parts):
            if len(p) == 8 and p.isdigit() and p.startswith("20") and i >= 1:
                idx.setdefault(parts[i - 1].lstrip("0") or "0", []).append((fn, url))
                break
    print("pricefull stores indexed:", len(idx))

    def work(st):
        k = st["store_id"].lstrip("0") or "0"
        if k not in idx:
            return {"store": st, "missing": True, "rows": []}
        fn, url = sorted(idx[k])[-1]
        dest = os.path.join(TMP, fn)
        rows = []
        try:
            if not os.path.exists(dest):
                SH.download(url, dest)
            for d in iter_items(dest):
                nm = d.get("itemname") or d.get("itemnm") or ""
                if match.is_dr_pepper(nm, d.get("manufacturername", "") or d.get("manufacturename", "")):
                    rows.append({
                        "chain": "Shufersal", "sub_chain": st["sub_chain"],
                        "store_id": st["store_id"], "store_name": st["store_name"],
                        "address": st["address"], "city": st["city"],
                        "code": d.get("itemcode", ""), "name": nm,
                        "price": d.get("itemprice", ""),
                        "qty": d.get("quantity", ""), "unit": d.get("unitqty", ""),
                        "zero": match.is_zero(nm), "file": fn,
                    })
        except Exception as e:
            return {"store": st, "error": repr(e), "rows": []}
        finally:
            if os.path.exists(dest):
                os.remove(dest)
        return {"store": st, "rows": rows}

    res = []
    with ThreadPoolExecutor(max_workers=6) as ex:
        for r in ex.map(work, ta):
            res.append(r)
            if r["rows"]:
                z = [x for x in r["rows"] if x["zero"]]
                print("HIT %-4s %-28s %-24s items=%d zero=%d" % (
                    r["store"]["store_id"], r["store"]["store_name"],
                    r["store"]["address"], len(r["rows"]), len(z)))
    json.dump(res, open(os.path.join(DATA, "shufersal_scan.json"), "w"),
              ensure_ascii=False, indent=1)
    tot = sum(len(r["rows"]) for r in res)
    print("done. TA stores scanned:", len(res), "dr-pepper rows:", tot,
          "missing:", len([r for r in res if r.get("missing")]))


if __name__ == "__main__":
    main()
