#!/usr/bin/env python3
"""Nationwide sweep: every store of every reachable portal, collecting every Dr Pepper SKU.

Purpose: build the definitive barcode -> product-name map so 'Zero' can be identified by
barcode even where a store's own item name omits the word.
"""
import os, re, json, sys, threading
from concurrent.futures import ThreadPoolExecutor
import match
from scan_pp import iter_items

HERE = os.path.dirname(os.path.abspath(__file__))
DATA, TMP = os.path.join(HERE, "data"), os.path.join(HERE, "tmp_nw")
os.makedirs(TMP, exist_ok=True)
LOCK = threading.Lock()
ROWS = []


def emit(rows):
    with LOCK:
        ROWS.extend(rows)
        for r in rows:
            print("HIT %-22s %-8s %-14s %-42s %s" % (
                r["chain"], r["store_id"], r["code"], r["name"][:42], r["price"]))
        sys.stdout.flush()


def scan_path(path, meta):
    out = []
    for it in iter_items(path):
        nm = it.get("itemname") or it.get("itemnm") or ""
        if match.is_dr_pepper(nm, it.get("manufacturename", "")):
            d = dict(meta)
            d.update({"code": it.get("itemcode", ""), "name": nm,
                      "price": it.get("itemprice", ""),
                      "qty": it.get("quantity", ""), "unit": it.get("unitqty", ""),
                      "mfr": it.get("manufacturename", ""),
                      "zero_by_name": match.is_zero(nm)})
            out.append(d)
    return out


def store_key(fn):
    body = re.sub(r"(?i)^pricefull", "", fn)
    parts = re.split(r"[-.]", body)
    for i, p in enumerate(parts):
        if p.isdigit() and p.startswith("20") and len(p) in (8, 12, 14) and i >= 1:
            return parts[i - 1].lstrip("0") or "0"
    return None


# ---------------- publishedprices ----------------
def do_pp():
    import pp_client as P
    from scan_pp import CHAINS

    def one(user):
        label, cd = CHAINS[user]
        try:
            s = P.login(user)
            files = [f["fname"] for f in P.list_files(s, cd=cd)
                     if f["fname"].lower().startswith("pricefull")]
        except Exception as e:
            print("!! pp", user, repr(e))
            return
        idx = {}
        for fn in files:
            k = store_key(fn)
            if k:
                idx.setdefault(k, []).append(fn)
        for k, fns in idx.items():
            fn = sorted(fns)[-1]
            d = os.path.join(TMP, "%s__%s" % (user, fn))
            try:
                rel = fn if cd == "/" else cd.strip("/") + "/" + fn
                P.download(s, rel, d)
                emit(scan_path(d, {"chain": label, "portal": user, "store_id": k, "file": fn}))
            except Exception as e:
                print("!! pp", user, fn, repr(e))
            finally:
                if os.path.exists(d):
                    os.remove(d)
        print("== pp done", label, len(idx), "stores")

    with ThreadPoolExecutor(max_workers=4) as ex:
        list(ex.map(one, list(CHAINS)))


# ---------------- shufersal ----------------
def do_shufersal():
    import shufersal as SH
    pf = SH.list_files("pricefull")
    idx = {}
    for fn, url in pf:
        k = store_key(fn)
        if k:
            idx.setdefault(k, []).append((fn, url))

    def one(kv):
        k, lst = kv
        fn, url = sorted(lst)[-1]
        d = os.path.join(TMP, fn)
        try:
            SH.download(url, d)
            emit(scan_path(d, {"chain": "Shufersal", "store_id": k, "file": fn}))
        except Exception as e:
            print("!! shufersal", fn, repr(e))
        finally:
            if os.path.exists(d):
                os.remove(d)

    with ThreadPoolExecutor(max_workers=6) as ex:
        list(ex.map(one, idx.items()))
    print("== shufersal done", len(idx), "stores")


# ---------------- carrefour ----------------
def do_carrefour():
    import carrefour as CF
    path, files, _ = CF.index()
    idx = {}
    for fn in files:
        if not fn.lower().startswith("pricefull"):
            continue
        k = store_key(fn)
        if k:
            idx.setdefault(k, []).append(fn)

    def one(kv):
        k, fns = kv
        fn = sorted(fns)[-1]
        d = os.path.join(TMP, fn)
        try:
            CF.download(path, fn, d)
            emit(scan_path(d, {"chain": "Carrefour/Yenot Bitan", "store_id": k, "file": fn}))
        except Exception as e:
            print("!! carrefour", fn, repr(e))
        finally:
            if os.path.exists(d):
                os.remove(d)

    with ThreadPoolExecutor(max_workers=6) as ex:
        list(ex.map(one, idx.items()))
    print("== carrefour done", len(idx), "stores")


# ---------------- binaprojects ----------------
def do_bina():
    import bina
    s = bina.session()
    for name, host in bina.SITES.items():
        try:
            rows = bina.list_files(host, s)
        except Exception as e:
            print("!! bina", name, repr(e))
            continue
        idx = {}
        for r in rows:
            fn = r["FileNm"]
            if not fn.lower().startswith("pricefull"):
                continue
            k = store_key(fn)
            if k:
                idx.setdefault(k, []).append(fn)

        def one(kv):
            k, fns = kv
            fn = sorted(fns)[-1]
            d = os.path.join(TMP, "%s__%s" % (host, fn))
            try:
                bina.download(host, fn, d, s)
                emit(scan_path(d, {"chain": name, "store_id": k, "file": fn}))
            except Exception as e:
                print("!! bina", name, fn, repr(e))
            finally:
                if os.path.exists(d):
                    os.remove(d)

        with ThreadPoolExecutor(max_workers=4) as ex:
            list(ex.map(one, idx.items()))
        print("== bina done", name, len(idx), "stores")


# ---------------- city market ----------------
def do_citymarket():
    import citymarket as CM
    sts = CM.stores()

    def one(st):
        try:
            rows = [r for r in CM.all_files({"s": st["store_id"], "t": "1", "f": "1"})
                    if r["name"].lower().startswith("pricefull")]
        except Exception as e:
            print("!! cm list", st["store_id"], repr(e))
            return
        if not rows:
            return
        r = sorted(rows, key=lambda x: x["name"])[-1]
        d = os.path.join(TMP, "cm_%s" % r["name"])
        try:
            CM.download(r["url"], d)
            emit(scan_path(d, {"chain": "City Market", "store_id": st["store_id"],
                               "store_label": st["label"], "file": r["name"]}))
        except Exception as e:
            print("!! cm", st["store_id"], repr(e))
        finally:
            if os.path.exists(d):
                os.remove(d)

    with ThreadPoolExecutor(max_workers=4) as ex:
        list(ex.map(one, sts))
    print("== citymarket done", len(sts), "stores")


if __name__ == "__main__":
    which = sys.argv[1] if len(sys.argv) > 1 else "all"
    fns = {"pp": do_pp, "shufersal": do_shufersal, "carrefour": do_carrefour,
           "bina": do_bina, "citymarket": do_citymarket}
    try:
        if which == "all":
            for f in fns.values():
                f()
        else:
            fns[which]()
    finally:
        json.dump(ROWS, open(os.path.join(DATA, "nationwide_%s.json" % which), "w"),
                  ensure_ascii=False, indent=1)
        print("TOTAL ROWS", len(ROWS))
