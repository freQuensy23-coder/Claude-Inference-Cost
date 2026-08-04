#!/usr/bin/env python3
"""Join the nationwide Dr Pepper sweep with store metadata; classify Zero by barcode."""
import os, json, re
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")

ZERO_WORDS = re.compile(r'(זירו|zero|ללא\s*סוכר|אפס\s*סוכר|דיאט|diet|sugar\s*free|no\s*sugar)', re.I)
# flavoured variants - the user asked for plain Dr Pepper Zero
FLAVOUR = re.compile(r"(שרי|צ'רי|צרי|דובדבן|cherry|קרם|cream|תות|strawberr|וניל|vanilla|"
                     r"אוכמניות|ענבים|blueberr|קוקוס|coconut|פירות)", re.I)


def load(name):
    p = os.path.join(DATA, "nationwide_%s.json" % name)
    return json.load(open(p)) if os.path.exists(p) else []


def norm(code):
    c = (code or "").strip().lstrip("0")
    return c or "0"


def main():
    rows = []
    for n in ("pp", "shufersal", "carrefour", "bina", "citymarket"):
        rows += load(n)
    print("nationwide dr-pepper rows:", len(rows))

    # ---- classify each barcode using every name any retailer gave it ----
    names = defaultdict(set)
    for r in rows:
        names[norm(r["code"])].add(r["name"].strip())

    zero_codes, flav_zero = set(), set()
    for c, ns in names.items():
        if any(ZERO_WORDS.search(n) for n in ns):
            (flav_zero if all(FLAVOUR.search(n) for n in ns if ZERO_WORDS.search(n))
             else zero_codes).add(c)
    # names that are *always* flavoured (with or without zero wording)
    print("\n=== barcodes whose item name is marked zero/sugar-free somewhere ===")
    for c in sorted(zero_codes | flav_zero):
        tag = "FLAVOURED-ZERO" if c in flav_zero else "ZERO"
        print(" %-14s %-15s %s" % (c, tag, sorted(names[c])[:5]))

    # ---- store metadata ----
    meta = {}
    for st in json.load(open(os.path.join(DATA, "pp_stores.json"))):
        meta[("pp", st["portal_user"], norm(st["store_id"]))] = st
    if os.path.exists(os.path.join(DATA, "shufersal_stores.json")):
        for st in json.load(open(os.path.join(DATA, "shufersal_stores.json"))):
            meta[("shufersal", None, norm(st["store_id"]))] = st
    if os.path.exists(os.path.join(DATA, "bina_stores.json")):
        for name, info in json.load(open(os.path.join(DATA, "bina_stores.json"))).items():
            for st in info["stores"]:
                meta[("bina", name, norm(st["store_id"]))] = st

    def lookup(r):
        if "portal" in r:
            return meta.get(("pp", r["portal"], norm(r["store_id"])))
        if r["chain"] == "Shufersal":
            return meta.get(("shufersal", None, norm(r["store_id"])))
        return meta.get(("bina", r["chain"], norm(r["store_id"])))

    TA_TEXT = ("תל אביב", "תל-אביב", 'ת"א', "יפו", "רמת אביב")

    def is_ta(r, st):
        if r["chain"] == "City Market":
            lab = r.get("store_label", "")
            return any(t in lab for t in TA_TEXT)
        if not st:
            return False
        blob = " ".join([st.get("city", ""), st.get("store_name", ""), st.get("address", "")])
        if "ירושלים" in st.get("city", ""):
            return False
        return st.get("city", "").strip() == "5000" or any(t in blob for t in TA_TEXT)

    out = []
    for r in rows:
        c = norm(r["code"])
        if c not in zero_codes and c not in flav_zero:
            continue
        st = lookup(r)
        rec = dict(r)
        rec["is_zero_plain"] = c in zero_codes
        rec["is_zero_flavoured"] = c in flav_zero
        rec["store_meta"] = st
        rec["ta"] = is_ta(r, st)
        out.append(rec)

    json.dump(out, open(os.path.join(DATA, "zero_rows.json"), "w"), ensure_ascii=False, indent=1)

    print("\n=== ZERO (plain) rows in Tel Aviv ===")
    for r in sorted([x for x in out if x["ta"] and x["is_zero_plain"]],
                    key=lambda x: (x["chain"], x["store_id"])):
        st = r["store_meta"] or {}
        lab = r.get("store_label") or "%s | %s" % (st.get("store_name", ""), st.get("address", ""))
        print(" %-24s %-5s %-55s %-14s %-32s %s" % (
            r["chain"], r["store_id"], lab[:55], r["code"], r["name"][:32], r["price"]))

    print("\n=== ZERO (flavoured variants) rows in Tel Aviv ===")
    for r in sorted([x for x in out if x["ta"] and x["is_zero_flavoured"]],
                    key=lambda x: (x["chain"], x["store_id"])):
        st = r["store_meta"] or {}
        lab = r.get("store_label") or "%s | %s" % (st.get("store_name", ""), st.get("address", ""))
        print(" %-24s %-5s %-55s %-14s %-32s %s" % (
            r["chain"], r["store_id"], lab[:55], r["code"], r["name"][:32], r["price"]))

    print("\n=== ZERO (plain) outside Tel Aviv, by chain ===")
    cnt = defaultdict(int)
    for r in out:
        if r["is_zero_plain"] and not r["ta"]:
            cnt[r["chain"]] += 1
    for k, v in sorted(cnt.items(), key=lambda kv: -kv[1]):
        print(" %-24s %d stores" % (k, v))


if __name__ == "__main__":
    main()
