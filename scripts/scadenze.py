#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""LE SCADENZE — la prova che finisce, Clara la mette in stanza (9/9/2026).

Dre: «il periodo di prova dura due mesi; quando finisce mi riaccordo con
loro per alzare il prezzo e si passa al retainer». Quattordici giorni prima
della fine Clara mette una domanda in stanza, una volta sola per prova:
«La prova di X finisce il D: ti riaccordi per il retainer?». Il si' crea la
task «Riaccordarsi con X» con la data; il no la chiude. Se la prova e'
finita e nessuno l'ha portata a Cliente, lo ricorda ogni giorno finche' non
si decide (in un senso o nell'altro).

USO
  python3 scripts/scadenze.py           propone
  python3 scripts/scadenze.py --prova   mostra e basta
"""

import datetime
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from stanza import sb, proponi                             # noqa: E402

PREAVVISO = 14


def main():
    prova = "--prova" in sys.argv
    oggi = datetime.date.today()
    entro = (oggi + datetime.timedelta(days=PREAVVISO)).isoformat()
    righe = sb("GET", f"/rest/v1/prospects?select=id,name,company,prova_inizio,prova_fine,canone"
                      f"&fuori=eq.true&pipeline_stage=eq.prova&prova_fine=lte.{entro}&order=prova_fine.asc&limit=200") or []
    gia = {((p.get("azione") or {}).get("prova_fine"), p.get("prospect_id"))
           for p in (sb("GET", "/rest/v1/proposte?select=prospect_id,azione&tipo=eq.richiesta&limit=5000") or [])}
    fatte = 0
    for p in righe:
        if (p["prova_fine"], p["id"]) in gia:
            continue
        nome = p.get("company") or p.get("name") or "?"
        fine = datetime.date.fromisoformat(p["prova_fine"])
        giorni = (fine - oggi).days
        quando = f"finisce il {fine:%d/%m}" if giorni >= 0 else f"e' finita il {fine:%d/%m}"
        titolo = f"{nome}: la prova {quando}. Ti riaccordi per il retainer?"
        perche = f"Prova dal {p['prova_inizio'] or '?'} al {p['prova_fine']}" + (f" · canone {p['canone']} €" if p.get("canone") else "")
        azione = {"prova_fine": p["prova_fine"],
                  "task": {"titolo": f"Riaccordarsi con {nome} per il retainer", "scadenza": max(oggi, fine - datetime.timedelta(days=7)).isoformat()}}
        if prova:
            print(f"  {titolo}")
            continue
        if proponi("richiesta", titolo, prospect_id=p["id"], perche=perche, azione=azione):
            fatte += 1
    print(f"scadenze: {fatte} proposte, {len(righe)} prove in scadenza")


if __name__ == "__main__":
    main()
