#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""LA CARD «MERCATO» DELLA SCHEDA, DALLO STESSO NUMERO (12/10/2026).

src/lib/mercato.json era la base del 24/8 in versione grezza: per le agenzie immobiliari
di Milano diceva 1.345.300 ricerche al mese (il portale Immobiliare.it dentro), mentre la
mail e l'analisi dal 12/10 dicono 44.000. Lo stesso numero deve stare ovunque: questo
script rigenera il file dalla base pulita (mercato.domanda) per tutte le province.

    python3 scripts/mercato_json.py        # riscrive src/lib/mercato.json
"""
import json
import os
import statistics
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import mercato as M                                         # noqa: E402

OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src", "lib", "mercato.json")


def main():
    out = {}
    for (settore, prov), v in sorted(M.base().items()):
        d = M.domanda(settore, prov)
        if not d:
            continue
        n, _, _ = d
        serie = v.get("serie") or []
        top = max(serie) if serie else 0
        bars = [[round(x * 100 / top) if top else 0, 0] for x in serie]
        if bars:
            i = max(range(len(bars)), key=lambda i: bars[i][0])
            bars[i][1] = 1
        vivi = v.get("mesi_vivi") or (sum(1 for x in serie if x >= statistics.mean(serie) * 0.5) if serie else 0)
        out[f"{settore}|{M.norm(prov)}"] = {"ricerche": n, "cpc": v.get("cpc_medio") or 0, "mesi_vivi": vivi, "bars": bars,
                                           "zona": M.luogo(prov).replace("nella ", "").replace("in ", ""), "fit": "si" if vivi >= 9 else "no"}
    # come la scheda puo' scrivere la provincia (nome, sigla, nomi vecchi) → la chiave della base
    nomi, per_sigla, _ = M._province()
    alias = {M.norm(k): M.norm(v) for k, v in {**{s: p for s, p in per_sigla.items()}, **M.VECCHI}.items()}
    out["_alias"] = {k: v for k, v in alias.items() if k != v}
    out["_misurato_il"] = "2026-10-12"
    json.dump(out, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
    print(f"{len(out) - 1} combinazioni → {OUT}")


if __name__ == "__main__":
    main()
