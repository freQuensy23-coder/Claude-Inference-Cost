#!/usr/bin/env python3
import os, json, re
from concurrent.futures import ThreadPoolExecutor
import citymarket as CM, match
from scan_pp import iter_items

HERE = os.path.dirname(os.path.abspath(__file__))
DATA, TMP = os.path.join(HERE, "data"), os.path.join(HERE, "tmp")
os.makedirs(TMP, exist_ok=True)
TA = ("תל אביב", 'ת"א', "תל-אביב", "יפו")


def work(st):
    rows = CM.all_files({"s": st["store_id"], "t": "1", "f": "1"})
    rows = [r for r in rows if r["name"].lower().startswith("pricefull")]
    if not rows:
        return {"store": st, "missing": True, "rows": []}
    r = sorted(rows, key=lambda x: x["name"])[-1]
    dest = os.path.join(TMP, "cm_%s" % r["name"])
    out = []
    try:
        CM.download(r["url"], dest)
        for it in iter_items(dest):
            nm = it.get("itemname") or it.get("itemnm") or ""
            if match.is_dr_pepper(nm, it.get("manufacturename", "")):
                out.append({"chain": "City Market", "store_id": st["store_id"],
                            "store_name": st["label"], "code": it.get("itemcode", ""),
                            "name": nm, "price": it.get("itemprice", ""),
                            "zero": match.is_zero(nm), "file": r["name"]})
    except Exception as e:
        return {"store": st, "error": repr(e), "rows": []}
    finally:
        if os.path.exists(dest):
            os.remove(dest)
    return {"store": st, "rows": out, "file": r["name"]}


def main():
    sts = [s for s in CM.stores() if any(t in s["label"] for t in TA)]
    print("City Market TA stores:", len(sts))
    res = []
    with ThreadPoolExecutor(max_workers=4) as ex:
        for r in ex.map(work, sts):
            res.append(r)
            tag = "MISSING" if r.get("missing") else r.get("error", "")
            print("  %-4s %-60s hits=%d %s" % (r["store"]["store_id"], r["store"]["label"][:60],
                                               len(r["rows"]), tag))
            for x in r["rows"]:
                print("    HIT", x["code"], x["name"], x["price"], "ZERO" if x["zero"] else "")
    json.dump(res, open(os.path.join(DATA, "citymarket_scan.json"), "w"),
              ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()
