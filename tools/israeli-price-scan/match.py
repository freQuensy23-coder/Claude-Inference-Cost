#!/usr/bin/env python3
"""Dr Pepper (Zero) name matching for Israeli price XML item names."""
import re

# Hebrew renderings of "Dr Pepper" seen in retail catalogues:
#   דר פפר / ד"ר פפר / ד'ר פפר / דר. פפר / דוקטור פפר  (+ optional maqaf/space variants)
HE_DR = r'(?:ד["\'׳״.\s]*ר|דוקטור)'
HE_PEPPER = r'פפר'
RE_HE = re.compile(HE_DR + r'[\s\.\-־]{0,3}' + HE_PEPPER)
RE_EN = re.compile(r'\bDR\.?\s*[\-]?\s*PEPPER\b', re.I)
# broad net for the discovery pass: any "pepper" token that is not peppermint/pepperoni/black pepper
RE_LOOSE_HE = re.compile(r'פפר(?!מינט|ונ|וני)')
RE_LOOSE_EN = re.compile(r'PEPPER(?!MINT|ONI)', re.I)

ZERO = re.compile(r'(זירו|zero|\bZR\b|דיאט|diet|ללא\s*סוכר|no\s*sugar|sugar\s*free)', re.I)
# things that merely contain "pepper" but are not the drink
NOISE = re.compile(r'(פפרמינט|פפרוני|pepperoni|peppermint|פלפל|מסטיק|dr\.?\s*oetker)', re.I)


def is_dr_pepper(name, mfr=""):
    blob = "%s %s" % (name or "", mfr or "")
    if NOISE.search(blob) and not (RE_HE.search(blob) or RE_EN.search(blob)):
        return False
    return bool(RE_HE.search(blob) or RE_EN.search(blob))


def is_zero(name, mfr=""):
    return bool(ZERO.search("%s %s" % (name or "", mfr or "")))


def loose_pepper(name, mfr=""):
    blob = "%s %s" % (name or "", mfr or "")
    if NOISE.search(blob):
        return False
    return bool(RE_LOOSE_HE.search(blob) or RE_LOOSE_EN.search(blob))
