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
        perche = f"Prova dal {p['prova_inizio'] or '?'} al {p['prova_fine']}" + (f", canone {p['canone']} €" if p.get("canone") else "")
        azione = {"prova_fine": p["prova_fine"],
                  "task": {"titolo": f"Riaccordarsi con {nome} per il retainer", "scadenza": max(oggi, fine - datetime.timedelta(days=7)).isoformat()}}
        if prova:
            print(f"  {titolo}")
            continue
        if proponi("richiesta", titolo, prospect_id=p["id"], perche=perche, azione=azione):
            fatte += 1
    print(f"scadenze: {fatte} proposte, {len(righe)} prove in scadenza")
    preventivi_scaduti(prova, oggi)


def preventivi_scaduti(prova, oggi):
    """I preventivi mandati e mai risposti (Giacomo, 15/9).

    Oggi il preventivo scaduto diventa un'etichetta ambra nella lista e li'
    resta: nessuno lo richiama, perche' niente lo mette nella giornata di
    qualcuno. Il giorno dopo la scadenza Clara lo chiede, una volta sola:
    si' e nasce la task per richiamarlo, no e si segna rifiutato a mano.
    """
    righe = sb("GET", f"/rest/v1/preventivi?select=id,numero,titolo,importo,mensile,valido_fino,prospect_id,inviato_il"
                      f"&stato=eq.inviato&valido_fino=lt.{oggi.isoformat()}&order=valido_fino.asc&limit=200") or []
    if not righe:
        print("preventivi scaduti: nessuno")
        return
    gia = {(p.get("azione") or {}).get("preventivo_id")
           for p in (sb("GET", "/rest/v1/proposte?select=azione&tipo=eq.richiesta&limit=5000") or [])}
    nomi = {}
    for q in righe:
        if q["prospect_id"] not in nomi:
            r = sb("GET", f"/rest/v1/prospects?select=company,name&id=eq.{q['prospect_id']}&limit=1") or [{}]
            nomi[q["prospect_id"]] = r[0].get("company") or r[0].get("name") or "?"
    fatte = 0
    for q in righe:
        if q["id"] in gia:
            continue
        nome = nomi[q["prospect_id"]]
        scaduto = datetime.date.fromisoformat(q["valido_fino"])
        quanto = f"{int(q['importo'] or 0)} €" + (f" piu' {int(q['mensile'])} €/mese" if q.get("mensile") else "")
        titolo = f"{nome}: il preventivo {q['numero']} e' scaduto il {scaduto:%d/%m} senza risposta. Lo richiamo?"
        perche = f"{quanto}, mandato il {q.get('inviato_il') or '?'}. Se non se ne fa niente, segnalo rifiutato dai Preventivi."
        azione = {"preventivo_id": q["id"],
                  "task": {"titolo": f"Richiamare {nome} sul preventivo {q['numero']}", "scadenza": oggi.isoformat()}}
        if prova:
            print(f"  {titolo}")
            continue
        if proponi("richiesta", titolo, prospect_id=q["prospect_id"], perche=perche, azione=azione):
            fatte += 1
    print(f"preventivi scaduti: {fatte} proposte, {len(righe)} scaduti")


if __name__ == "__main__":
    main()
