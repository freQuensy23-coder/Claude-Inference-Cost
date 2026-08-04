#!/usr/bin/env python3
"""Download + parse Stores files for every publishedprices chain."""
import os, sys, gzip, io, json, re, traceback
import xml.etree.ElementTree as ET
import pp_client as P

USERS = [
    ("SuperCofixApp", "/", "Cofix"),
    ("doralon", "/", "Dor Alon"),
    ("freshmarket", "/", "Freshmarket/Super Dosh"),
    ("Keshet", "/", "Keshet Teamim"),
    ("osherad", "/", "Osher Ad"),
    ("politzer", "/", "Politzer"),
    ("RamiLevi", "/", "Rami Levy"),
    ("SalachD", "/", "Salah Dabah"),
    ("Stop_Market", "/", "Stop Market"),
    ("yuda_ho", "/Yuda", "Super Yuda"),
    ("TivTaam", "/", "Tiv Taam"),
    ("Paz_bo", "/", "Yellow (Paz)"),
    ("yohananof", "/", "Yohananof"),
]

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")


def read_xml_bytes(path):
    with open(path, "rb") as f:
        raw = f.read()
    if raw[:2] == b"\x1f\x8b":
        raw = gzip.decompress(raw)
    # strip BOM / leading junk
    i = raw.find(b"<")
    return raw[i:]


def txt(node, *names):
    for n in names:
        el = node.find(n)
        if el is None:
            # case-insensitive fallback
            for c in node:
                if c.tag.lower() == n.lower():
                    el = c
                    break
        if el is not None and el.text:
            return el.text.strip()
    return ""


def parse_stores(path):
    raw = read_xml_bytes(path)
    root = ET.fromstring(raw)
    chain_id = txt(root, "ChainId", "ChainID", "CHAINID")
    chain_name = txt(root, "ChainName", "CHAINNAME")
    stores = []
    # Store elements can be nested at various depths
    for st in root.iter():
        if st.tag.lower() not in ("store", "branch"):
            continue
        sid = txt(st, "StoreId", "StoreID", "STOREID")
        if not sid:
            continue
        stores.append({
            "chain_id": chain_id,
            "chain_name": chain_name,
            "store_id": sid,
            "sub_chain": txt(st, "SubChainName", "SUBCHAINNAME"),
            "store_name": txt(st, "StoreName", "STORENAME"),
            "address": txt(st, "Address", "ADDRESS"),
            "city": txt(st, "City", "CITY"),
            "zip": txt(st, "ZipCode", "ZIPCODE"),
        })
    return chain_id, chain_name, stores


def main():
    os.makedirs(OUT, exist_ok=True)
    allstores = []
    for user, cd, label in USERS:
        try:
            s = P.login(user)
            files = P.list_files(s, cd=cd)
            names = [f["fname"] for f in files]
            cands = [n for n in names if re.match(r"(?i)^stores?(full)?[0-9\-]*\.(gz|xml)$", n)] \
                or [n for n in names if re.match(r"(?i)^storesfull", n)] \
                or [n for n in names if re.match(r"(?i)^stores", n)]
            if not cands:
                print("!! no stores file for", label, "sample:", names[:3])
                continue
            cands.sort()
            fn = cands[-1]
            dest = os.path.join(OUT, "%s__%s" % (user, fn))
            P.download(s, (cd.rstrip('/') + '/' + fn).lstrip('/') if cd != '/' else fn, dest)
            cid, cname, stores = parse_stores(dest)
            for st in stores:
                st["portal_user"] = user
                st["label"] = label
                st["cd"] = cd
            allstores += stores
            print("OK %-16s %-22s stores=%4d file=%s" % (user, label, len(stores), fn))
        except Exception as e:
            print("!! FAIL", user, label, repr(e))
            traceback.print_exc()
    with open(os.path.join(OUT, "pp_stores.json"), "w") as f:
        json.dump(allstores, f, ensure_ascii=False, indent=1)
    print("total stores:", len(allstores))


if __name__ == "__main__":
    main()
