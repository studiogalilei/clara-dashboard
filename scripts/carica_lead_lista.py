#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Una tantum, dal Mac: i due CSV di Lorenzo dentro lead_lista, ognuno con la
sua lista, e i domini unici dentro raccolta (da fare). Si puo' rilanciare:
non duplica (unique su lista+email, dominio chiave in raccolta).

USO  carica_lead_lista.py cecchino /path/CON_NOME.csv
     carica_lead_lista.py strascico /path/SENZA_NOME.csv
"""
import csv
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from stanza import sb                                      # noqa: E402

csv.field_size_limit(sys.maxsize)


def dominio(website, email):
    w = (website or "").strip().lower()
    w = re.sub(r"^https?://", "", w); w = re.sub(r"^www\.", "", w); w = w.split("/")[0].split("?")[0]
    if w and "." in w:
        return w
    return (email or "").split("@")[-1].lower()


def main():
    lista, path = sys.argv[1], sys.argv[2]
    K = lambda r, k: (r.get(k) or r.get("﻿" + k) or "").strip()
    with open(path, encoding="utf-8", errors="replace") as f:
        rows = list(csv.DictReader(f))
    righe, domini = [], {}
    for r in rows:
        em = K(r, "email").lower()
        if "@" not in em:
            continue
        d = dominio(K(r, "website"), em)
        az = K(r, "company_clean_final") or K(r, "company_clean") or K(r, "company_name")
        righe.append({"lista": lista, "email": em, "first_name": K(r, "first_name") or None, "website": K(r, "website") or None,
                      "dominio": d, "azienda": az or None, "icebreaker": K(r, "icebreaker") or None})
        domini.setdefault(d, az)
    for i in range(0, len(righe), 500):
        sb("POST", "/rest/v1/lead_lista", righe[i:i + 500], {"Prefer": "resolution=ignore-duplicates"})
    dl = [{"dominio": d, "azienda": a} for d, a in domini.items()]
    for i in range(0, len(dl), 500):
        sb("POST", "/rest/v1/raccolta", dl[i:i + 500], {"Prefer": "resolution=ignore-duplicates"})
    n = sb("GET", f"/rest/v1/lead_lista?select=id&lista=eq.{lista}&limit=100000")
    print(f"{lista}: nel CSV {len(rows)} | validi {len(righe)} | in tabella {len(n)} | domini unici {len(domini)}")


if __name__ == "__main__":
    main()
