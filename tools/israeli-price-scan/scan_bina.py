#!/usr/bin/env python3
import os, re, json
from concurrent.futures import ThreadPoolExecutor
import bina, match
from scan_pp import iter_items

HERE = os.path.dirname(os.path.abspath(__file__))
DATA, TMP = os.path.join(HERE, "data"), os.path.join(HERE, "tmp")
os.makedirs(TMP, exist_ok=True)


def is_ta(st):
    blob = " ".join([st["city"], st["store_name"], st["address"]])
    if "ירושלים" in st["city"]:
        return False
    return st["city"].strip() == "5000" or any(
        t in blob for t in ("תל אביב", "תל-אביב", 'ת"א', "יפו"))


def main():
    meta = json.load(open(os.path.join(DATA, "bina_stores.json")))
    s = bina.session()
    out = []
    for name, info in meta.items():
        host = info["host"]
        ta = [x for x in info["stores"] if is_ta(x)]
        if not ta:
            print("%-24s TA stores: 0 (skipped)" % name)
            continue
        try:
            rows = bina.list_files(host, s)
        except Exception as e:
            print("%-24s FAIL listing %r" % (name, e))
            continue
        idx = {}
        for r in rows:
            fn = r["FileNm"]
            if not fn.lower().startswith("pricefull"):
                continue
            body = re.sub(r"(?i)^pricefull", "", fn)
            parts = re.split(r"[-.]", body)
            for i, p in enumerate(parts):
                if p.isdigit() and len(p) >= 12 and p.startswith("20") and i >= 1:
                    idx.setdefault(parts[i - 1].lstrip("0") or "0", []).append(fn)
                    break
                if len(p) == 8 and p.isdigit() and p.startswith("20") and i >= 1:
                    idx.setdefault(parts[i - 1].lstrip("0") or "0", []).append(fn)
                    break

        def work(st):
            k = st["store_id"].lstrip("0") or "0"
            if k not in idx:
                return {"chain": name, "store": st, "missing": True, "rows": []}
            fn = sorted(idx[k])[-1]
            d = os.path.join(TMP, "%s__%s" % (host, fn))
            res = []
            try:
                if not os.path.exists(d):
                    bina.download(host, fn, d, s)
                for it in iter_items(d):
                    nm = it.get("itemname") or it.get("itemnm") or ""
                    if match.is_dr_pepper(nm, it.get("manufacturename", "")):
                        res.append({"chain": name, "store_id": st["store_id"],
                                    "store_name": st["store_name"], "address": st["address"],
                                    "city": st["city"], "code": it.get("itemcode", ""),
                                    "name": nm, "price": it.get("itemprice", ""),
                                    "zero": match.is_zero(nm), "file": fn})
            except Exception as e:
                return {"chain": name, "store": st, "error": repr(e), "rows": []}
            finally:
                if os.path.exists(d):
                    os.remove(d)
            return {"chain": name, "store": st, "rows": res}

        got = []
        with ThreadPoolExecutor(max_workers=4) as ex:
            for r in ex.map(work, ta):
                got.append(r)
                for x in r["rows"]:
                    print("HIT", name, x["store_id"], x["store_name"], "|", x["code"],
                          x["name"], x["price"], "ZERO" if x["zero"] else "")
        miss = [r["store"]["store_id"] for r in got if r.get("missing")]
        err = [r for r in got if r.get("error")]
        print("%-24s TA=%d hits=%d missing_files=%s errors=%d" % (
            name, len(ta), sum(len(r["rows"]) for r in got), miss, len(err)))
        out += got
    json.dump(out, open(os.path.join(DATA, "bina_scan.json"), "w"),
              ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()
