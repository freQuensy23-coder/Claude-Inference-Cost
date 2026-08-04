#!/usr/bin/env python3
"""Authoritative pass: re-read every Tel-Aviv-area store file and match Dr Pepper Zero
by BARCODE (not just by item name), so a store that names the SKU oddly is still caught."""
import os, re, json, sys, threading
from concurrent.futures import ThreadPoolExecutor
from scan_pp import iter_items
import match

HERE = os.path.dirname(os.path.abspath(__file__))
DATA, TMP = os.path.join(HERE, "data"), os.path.join(HERE, "tmp_fv")
os.makedirs(TMP, exist_ok=True)

ZERO_PLAIN = {"8435185953711", "5449000121028", "78000035476", "078000035476"}
ZERO_FLAV = {"78000035483", "078000035483", "78000035490", "078000035490",
             "78000037708", "078000037708", "5449000334237"}
ALL_ZERO = {c.lstrip("0") for c in ZERO_PLAIN | ZERO_FLAV}

TA_TEXT = ("תל אביב", "תל-אביב", 'ת"א', "יפו", "רמת אביב")
LOCK = threading.Lock()
ROWS = []


def is_ta(st):
    blob = " ".join([st.get("city", ""), st.get("store_name", ""), st.get("address", "")])
    if "ירושלים" in st.get("city", ""):
        return False
    return st.get("city", "").strip() == "5000" or any(t in blob for t in TA_TEXT)


def store_key(fn):
    body = re.sub(r"(?i)^pricefull", "", fn)
    parts = re.split(r"[-.]", body)
    for i, p in enumerate(parts):
        if p.isdigit() and p.startswith("20") and len(p) in (8, 12, 14) and i >= 1:
            return parts[i - 1].lstrip("0") or "0"
    return None


def check(path, meta):
    found = []
    for it in iter_items(path):
        code = (it.get("itemcode") or "").strip().lstrip("0")
        nm = it.get("itemname") or it.get("itemnm") or ""
        hit_code = code in ALL_ZERO
        hit_name = match.is_dr_pepper(nm) and match.is_zero(nm)
        if hit_code or hit_name:
            d = dict(meta)
            d.update({"code": it.get("itemcode", ""), "name": nm,
                      "price": it.get("itemprice", ""),
                      "plain": code in {c.lstrip("0") for c in ZERO_PLAIN},
                      "matched_by": "barcode" if hit_code else "name-only"})
            found.append(d)
    with LOCK:
        ROWS.extend(found)
        for f in found:
            print("ZERO %-22s %-6s %-38s %-14s %-34s %s (%s)" % (
                f["chain"], f["store_id"], f.get("address", "")[:38], f["code"],
                f["name"][:34], f["price"], f["matched_by"]))
            sys.stdout.flush()
    return found


def do_pp():
    import pp_client as P
    from scan_pp import CHAINS
    stores = json.load(open(os.path.join(DATA, "pp_stores.json")))

    def one(user):
        label, cd = CHAINS[user]
        targets = [s for s in stores if s["portal_user"] == user and is_ta(s)]
        if not targets:
            return
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
        for st in targets:
            k = st["store_id"].lstrip("0") or "0"
            if k not in idx:
                print("   (no price file) %s %s %s" % (label, st["store_id"], st["store_name"]))
                continue
            fn = sorted(idx[k])[-1]
            d = os.path.join(TMP, "%s__%s" % (user, fn))
            try:
                rel = fn if cd == "/" else cd.strip("/") + "/" + fn
                P.download(s, rel, d)
                check(d, {"chain": label, "store_id": st["store_id"],
                          "store_name": st["store_name"], "address": st["address"],
                          "file": fn})
            except Exception as e:
                print("!! pp", user, fn, repr(e))
            finally:
                if os.path.exists(d):
                    os.remove(d)
        print("== pp TA done", label, len(targets))

    with ThreadPoolExecutor(max_workers=4) as ex:
        list(ex.map(one, list(CHAINS)))


def do_shufersal():
    import shufersal as SH
    sts = [s for s in json.load(open(os.path.join(DATA, "shufersal_stores.json"))) if is_ta(s)]
    idx = {}
    for fn, url in SH.list_files("pricefull"):
        k = store_key(fn)
        if k:
            idx.setdefault(k, []).append((fn, url))

    def one(st):
        k = st["store_id"].lstrip("0") or "0"
        if k not in idx:
            return
        fn, url = sorted(idx[k])[-1]
        d = os.path.join(TMP, fn)
        try:
            SH.download(url, d)
            check(d, {"chain": "Shufersal " + st["sub_chain"], "store_id": st["store_id"],
                      "store_name": st["store_name"], "address": st["address"], "file": fn})
        except Exception as e:
            print("!! shufersal", fn, repr(e))
        finally:
            if os.path.exists(d):
                os.remove(d)

    with ThreadPoolExecutor(max_workers=6) as ex:
        list(ex.map(one, sts))
    print("== shufersal TA done", len(sts))


def do_carrefour():
    import carrefour as CF
    sts = [s for s in json.load(open(os.path.join(DATA, "carrefour_stores.json"))) if is_ta(s)]
    path, files, _ = CF.index()
    idx = {}
    for fn in files:
        if fn.lower().startswith("pricefull"):
            k = store_key(fn)
            if k:
                idx.setdefault(k, []).append(fn)

    def one(st):
        k = st["store_id"].lstrip("0") or "0"
        if k not in idx:
            return
        fn = sorted(idx[k])[-1]
        d = os.path.join(TMP, fn)
        try:
            CF.download(path, fn, d)
            check(d, {"chain": "Carrefour", "store_id": st["store_id"],
                      "store_name": st["store_name"], "address": st["address"], "file": fn})
        except Exception as e:
            print("!! carrefour", fn, repr(e))
        finally:
            if os.path.exists(d):
                os.remove(d)

    with ThreadPoolExecutor(max_workers=6) as ex:
        list(ex.map(one, sts))
    print("== carrefour TA done", len(sts))


def do_bina():
    import bina
    s = bina.session()
    meta = json.load(open(os.path.join(DATA, "bina_stores.json")))
    for name, info in meta.items():
        sts = [x for x in info["stores"] if is_ta(x)]
        if not sts:
            continue
        try:
            rows = bina.list_files(info["host"], s)
        except Exception as e:
            print("!! bina", name, repr(e))
            continue
        idx = {}
        for r in rows:
            fn = r["FileNm"]
            if fn.lower().startswith("pricefull"):
                k = store_key(fn)
                if k:
                    idx.setdefault(k, []).append(fn)
        for st in sts:
            k = st["store_id"].lstrip("0") or "0"
            if k not in idx:
                continue
            fn = sorted(idx[k])[-1]
            d = os.path.join(TMP, "%s__%s" % (info["host"], fn))
            try:
                bina.download(info["host"], fn, d, s)
                check(d, {"chain": name, "store_id": st["store_id"],
                          "store_name": st["store_name"], "address": st["address"], "file": fn})
            except Exception as e:
                print("!! bina", name, fn, repr(e))
            finally:
                if os.path.exists(d):
                    os.remove(d)
        print("== bina TA done", name, len(sts))


def do_citymarket():
    import citymarket as CM
    sts = [s for s in CM.stores() if any(t in s["label"] for t in TA_TEXT)]

    def one(st):
        try:
            rows = [r for r in CM.all_files({"s": st["store_id"], "t": "1", "f": "1"})
                    if r["name"].lower().startswith("pricefull")]
            if not rows:
                rows = [r for r in CM.all_files({"s": st["store_id"], "t": "1"})
                        if r["name"].lower().startswith("pricefull")]
        except Exception as e:
            print("!! cm", st["store_id"], repr(e))
            return
        if not rows:
            print("   (no PriceFull) City Market %s %s" % (st["store_id"], st["label"]))
            return
        r = sorted(rows, key=lambda x: x["name"])[-1]
        d = os.path.join(TMP, "cm_%s" % r["name"])
        try:
            CM.download(r["url"], d)
            check(d, {"chain": "City Market", "store_id": st["store_id"],
                      "store_name": st["label"], "address": st["label"], "file": r["name"]})
        except Exception as e:
            print("!! cm", st["store_id"], repr(e))
        finally:
            if os.path.exists(d):
                os.remove(d)

    with ThreadPoolExecutor(max_workers=4) as ex:
        list(ex.map(one, sts))
    print("== citymarket TA done", len(sts))


if __name__ == "__main__":
    for f in (do_pp, do_shufersal, do_carrefour, do_bina, do_citymarket):
        try:
            f()
        except Exception as e:
            print("!! stage failed", f.__name__, repr(e))
    json.dump(ROWS, open(os.path.join(DATA, "final_zero_ta.json"), "w"),
              ensure_ascii=False, indent=1)
    print("TOTAL ZERO ROWS IN TA:", len(ROWS))
