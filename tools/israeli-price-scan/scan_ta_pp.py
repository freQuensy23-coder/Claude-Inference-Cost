#!/usr/bin/env python3
"""Full scan: every Tel-Aviv-area store of every publishedprices chain, looking for Dr Pepper."""
import os, re, json, sys, traceback
from concurrent.futures import ThreadPoolExecutor
import pp_client as P
import match
from scan_pp import iter_items, CHAINS, DATA, read_xml

TMP = "/root/work/dp/tmp"
os.makedirs(TMP, exist_ok=True)

# Israeli CBS city codes for Tel Aviv and the immediately adjacent ring
TA = {"5000"}
RING = {"8600": "Ramat Gan", "6300": "Givatayim", "6100": "Bnei Brak",
        "6600": "Holon", "6200": "Bat Yam", "9500": "", "2600": ""}
TA_TEXT = ("תל אביב", "תל-אביב", 'ת"א', "יפו", "רמת אביב")


def is_ta(st):
    blob = " ".join([st["city"], st["store_name"], st["address"], st["sub_chain"]])
    return st["city"].strip() in TA or any(t in blob for t in TA_TEXT)


def build_index(user, cd):
    s = P.login(user)
    files = P.list_files(s, cd=cd)
    idx = {}
    for f in files:
        n = f["fname"]
        if not n.lower().startswith("pricefull"):
            continue
        # PriceFull<chain>[-<subchain>]-<store>-<YYYYMMDD>[-<HHMMSS>].gz
        body = re.sub(r"(?i)^pricefull", "", n)
        parts = re.split(r"[-.]", body)
        sid = None
        for i, p in enumerate(parts):
            if len(p) == 8 and p.isdigit() and p.startswith("20") and i >= 1:
                sid = parts[i - 1]
                break
        if sid is None or not sid.isdigit():
            continue
        idx.setdefault(sid.lstrip("0") or "0", []).append(n)
    for k in idx:
        idx[k].sort()
    return s, idx


def scan_chain(user):
    label, cd = CHAINS[user]
    stores = [st for st in json.load(open(os.path.join(DATA, "pp_stores.json")))
              if st["portal_user"] == user]
    targets = [st for st in stores if is_ta(st)]
    out = []
    try:
        s, idx = build_index(user, cd)
    except Exception as e:
        return {"user": user, "label": label, "error": repr(e), "rows": []}
    missing = []
    for st in targets:
        k = st["store_id"].lstrip("0") or "0"
        if k not in idx:
            missing.append(st["store_id"])
            continue
        fn = idx[k][-1]
        dest = os.path.join(TMP, "%s__%s" % (user, fn))
        try:
            rel = fn if cd == "/" else cd.strip("/") + "/" + fn
            if not os.path.exists(dest):
                P.download(s, rel, dest)
            for d in iter_items(dest):
                nm = d.get("itemname") or d.get("itemnm") or ""
                if match.is_dr_pepper(nm, d.get("manufacturename", "")):
                    out.append({
                        "chain": label, "portal": user,
                        "store_id": st["store_id"], "store_name": st["store_name"],
                        "address": st["address"], "city": st["city"],
                        "code": d.get("itemcode", ""), "name": nm,
                        "price": d.get("itemprice", ""),
                        "qty": d.get("quantity", ""), "unit": d.get("unitqty", ""),
                        "zero": match.is_zero(nm, d.get("manufacturename", "")),
                        "file": fn,
                    })
        except Exception as e:
            out.append({"chain": label, "store_id": st["store_id"], "error": repr(e)})
        finally:
            if os.path.exists(dest):
                os.remove(dest)
    return {"user": user, "label": label, "targets": len(targets),
            "missing_price_files": missing, "rows": out}


def main():
    results = []
    with ThreadPoolExecutor(max_workers=4) as ex:
        for r in ex.map(scan_chain, list(CHAINS)):
            results.append(r)
            n_zero = len([x for x in r["rows"] if x.get("zero")])
            print("%-16s %-24s ta_stores=%3s hits=%3d zero=%d %s" % (
                r["user"], r["label"], r.get("targets", "-"), len(r["rows"]), n_zero,
                r.get("error", "")))
            sys.stdout.flush()
    json.dump(results, open(os.path.join(DATA, "pp_ta_scan.json"), "w"),
              ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()
