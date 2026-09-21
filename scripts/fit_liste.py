#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""IL FIT SULLE LISTE, prima della campagna (Dre, 21/9/2026).

«Evitare proprio di contattare quelli che non sono in target.» Per ogni
dominio gia' raccolto (tabella raccolta) e non ancora giudicato, chiede al
cervello le stesse cose del google fit (googlefit.capisci: settore, raggio,
tipo, ticket, esclusioni, due cose scomode) leggendo il sito GIA' RACCOLTO,
e da' il verdetto con googlefit.verdetto usando le recensioni gia' raccolte.
Niente crediti, niente letture nuove: si ragiona su quello che c'e'.

Scrive su lead_lista: fit, fit_motivo, fa_ads (copiato da raccolta). Da li'
lo split in quattro campagne e' una query: lista x fa_ads, con fit <> NO.

USO
  fit_liste.py --prova 30      trenta domini, stampa e non scrive
  fit_liste.py                 tutti quelli raccolti e senza fit
"""
import concurrent.futures as cf
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from stanza import sb                                      # noqa: E402
import googlefit as gf                                     # noqa: E402


def giudica(r, settori):
    # al fit bastano le prime 5.000 battute del sito: il resto e' footer e ripetizioni, e costa tempo
    c = gf.capisci(r.get("azienda") or r["dominio"], (r.get("sito_testo") or "")[:5000], settori)
    rec = {"recensioni": int(r["recensioni"]), "voto": r.get("voto")} if r.get("recensioni") is not None else None
    v, motivo = gf.verdetto(c, None, rec)
    return {"dominio": r["dominio"], "fit": v, "fit_motivo": motivo[:300], "fa_ads": bool(r.get("fa_ads")),
            "settore": c.get("settore"), "raggio": c.get("raggio"), "esclusione": c.get("esclusione") or None}


def main():
    args = sys.argv[1:]
    prova = int(args[args.index("--prova") + 1]) if "--prova" in args else 0
    ore = float(args[args.index("--ore") + 1]) if "--ore" in args else 0
    inizio = time.time()
    while True:
        n = lotto(prova)
        if prova or n == 0 or not ore or time.time() - inizio > ore * 3600:
            break


def lotto(prova):
    _, settori = gf.carica_fogli()
    # i domini raccolti che nessun lead ha ancora col fit (PostgREST da' al massimo 1000: un lotto)
    da_fare = sb("GET", "/rest/v1/lead_lista?select=dominio&fit=is.null&order=dominio&limit=1000")
    domini = sorted({d["dominio"] for d in da_fare})
    righe = []
    for i in range(0, len(domini), 200):
        righe += sb("GET", "/rest/v1/raccolta?select=dominio,azienda,sito_testo,recensioni,voto,fa_ads&raccolto_il=not.is.null&dominio=in.("
                    + ",".join(f'"{d}"' for d in domini[i:i + 200]) + ")")
    if prova:
        righe = righe[:prova]
    if not righe:
        print("fit: niente da giudicare (o il pull non e' ancora arrivato qui)"); return 0
    t0 = time.time()
    fatti, esiti = 0, {"SI": 0, "PARZIALE": 0, "NO": 0}
    with cf.ThreadPoolExecutor(24) as ex:
        for g in ex.map(lambda r: giudica(r, settori), righe):
            esiti[g["fit"]] += 1; fatti += 1
            if prova:
                print(f"  {g['fit']:8} ads={'SI' if g['fa_ads'] else 'no':2} {g['dominio'][:30]:30} {(g['settore'] or '?')[:18]:18} {(g['raggio'] or '?')[:10]:10} {g['fit_motivo'][:60]}")
            else:
                sb("PATCH", f"/rest/v1/lead_lista?dominio=eq.{g['dominio']}", {"fit": g["fit"], "fit_motivo": g["fit_motivo"], "fa_ads": g["fa_ads"]})
                if fatti % 200 == 0:
                    print(f"  {fatti}/{len(righe)} in {int(time.time() - t0)}s  {esiti}", flush=True)
    print(f"fit: {fatti} domini in {int(time.time() - t0)}s  SI {esiti['SI']}  PARZIALE {esiti['PARZIALE']}  NO {esiti['NO']}", flush=True)
    return fatti


if __name__ == "__main__":
    main()
