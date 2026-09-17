#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""IL VOCABOLARIO DEI SETTORI, UNO SOLO (17/9/2026).

Il Foglio Settori (data/foglio_settori.csv) e' la lista che usa Clara per
classificare (googlefit.py). L'app la deve usare uguale: chi scrive un
settore a mano sceglie da questa lista, cosi' «consulenza aziendale» e
«consulenza_aziendale» non contano separati e il settore combacia con le
zone misurate. Questo script rigenera src/lib/settori.json dal CSV.

USO: python3 scripts/settori_json.py   (poi si committa il json)
"""
import csv, json, os
RADICE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
righe = list(csv.DictReader(open(os.path.join(RADICE, "data", "foglio_settori.csv"), encoding="utf-8")))
fuori = sorted(({"chiave": r["settore"], "tipo": r.get("tipo") or ""} for r in righe), key=lambda x: x["chiave"])
json.dump(fuori, open(os.path.join(RADICE, "src", "lib", "settori.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=0)
print(f"{len(fuori)} settori scritti in src/lib/settori.json")
