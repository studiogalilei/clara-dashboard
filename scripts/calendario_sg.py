#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""IL CALENDARIO «SG Scadenze» (15/9/2026): le nostre scadenze dentro Google.

PERCHE'
Dre (15/9): «esiste gia' Google Calendar e non voglio che i ragazzi si
ammazzino su piu' calendari». Giusto. Le call stanno gia' su Google e il
Workspace le legge. Il problema e' il contrario: le scadenze dei progetti,
le task con una data e le prove che finiscono vivono solo dentro il
Workspace, quindi chi guarda solo Google non le vede.

COSA FA
Le scrive dentro Google, in un calendario a parte chiamato «SG Scadenze»,
condiviso con tutta la squadra: ognuno se lo vede insieme al suo, e chi non
lo vuole lo spegne con un clic senza rompere niente a nessuno. Il calendario
nasce una volta sola, nell'account di chi lancia (Dre), e il suo id resta in
`istruzioni` (chiave `calendario_scadenze`).

L'id di ogni evento e' calcolato dal tipo e dalla riga: la stessa scadenza
riscritta due volte non fa due eventi, e se la data cambia l'evento si
sposta invece di duplicarsi.

USO
  python3 scripts/calendario_sg.py            scrive
  python3 scripts/calendario_sg.py --prova    dice cosa farebbe
"""

import datetime
import hashlib
import json
import os
import sys
import urllib.parse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from stanza import sb, env                                 # noqa: E402
from google_api import g                                   # noqa: E402

CAL = "https://www.googleapis.com/calendar/v3"
NOME = "SG Scadenze"
PADRONE = env("GOOGLE_UTENTE") or "dramane@studiogalilei.com"
GIORNI_AVANTI = 120


def id_evento(chiave):
    """Un id stabile: stessa riga, stesso evento. Google accetta 0-9 e a-v."""
    return "sg" + hashlib.sha1(chiave.encode()).hexdigest()


def istruzione(chiave, valore=None):
    if valore is None:
        r = sb("GET", f"/rest/v1/istruzioni?select=testo&chiave=eq.{chiave}&limit=1") or []
        return r[0]["testo"] if r else None
    sb("POST", "/rest/v1/istruzioni", {"chiave": chiave, "titolo": "Il calendario delle scadenze", "testo": valore},
       {"Prefer": "resolution=merge-duplicates"})
    return valore


def calendario(prova):
    """Il calendario condiviso: si crea una volta e si condivide con la squadra."""
    gia = istruzione("calendario_scadenze")
    if gia:
        return gia
    if prova:
        return None
    fatto = g("POST", f"{CAL}/calendars", {"summary": NOME, "timeZone": "Europe/Rome",
                                           "description": "Le scadenze di SG Workspace: progetti, prove, task con una data."},
              email=PADRONE)
    cid = fatto["id"]
    # tutta la squadra lo vede, nessuno lo deve cercare
    for u in (sb("GET", "/rest/v1/google_token?select=email") or []):
        if u["email"] == PADRONE:
            continue
        try:
            g("POST", f"{CAL}/calendars/{urllib.parse.quote(cid)}/acl",
              {"role": "reader", "scope": {"type": "user", "value": u["email"]}}, email=PADRONE)
        except Exception as e:
            print(f"  non condiviso con {u['email']}: {str(e)[:120]}")
    istruzione("calendario_scadenze", cid)
    print(f"calendario «{NOME}» creato e condiviso")
    return cid


def scrivi(cid, chiave, titolo, giorno, descrizione, prova):
    eid = id_evento(chiave)
    corpo = {"id": eid, "summary": titolo[:200], "description": descrizione[:600],
             "start": {"date": giorno}, "end": {"date": giorno},
             "transparency": "transparent", "reminders": {"useDefault": False}}
    if prova:
        print(f"  [prova] {giorno}  {titolo}")
        return "prova"
    try:
        g("POST", f"{CAL}/calendars/{urllib.parse.quote(cid)}/events", corpo, email=PADRONE)
        return "nuovo"
    except RuntimeError as e:
        if "409" in str(e) or "duplicate" in str(e).lower():
            try:
                g("PUT", f"{CAL}/calendars/{urllib.parse.quote(cid)}/events/{eid}", corpo, email=PADRONE)
                return "aggiornato"
            except RuntimeError as e2:
                print(f"  non aggiornato: {str(e2)[:140]}")
                return None
        print(f"  non scritto: {str(e)[:140]}")
        return None


def nomi_aziende(ids):
    if not ids:
        return {}
    lista = ",".join(f'"{i}"' for i in ids)
    righe = sb("GET", f"/rest/v1/prospects?select=id,company,name&id=in.({lista})&limit=500") or []
    return {r["id"]: (r.get("company") or r.get("name") or "") for r in righe}


def main():
    prova = "--prova" in sys.argv
    oggi = datetime.date.today()
    fino = (oggi + datetime.timedelta(days=GIORNI_AVANTI)).isoformat()
    cid = calendario(prova)
    if not cid and not prova:
        print("calendario: non creato")
        return

    conta = {"nuovo": 0, "aggiornato": 0, "prova": 0}

    # 1. le scadenze dei progetti
    progetti = sb("GET", "/rest/v1/progetti?select=id,nome,scadenza,stato,chi_segue,prospect_id"
                         f"&scadenza=gte.{oggi.isoformat()}&scadenza=lte.{fino}&stato=neq.consegnato&limit=500") or []
    aziende = nomi_aziende([p["prospect_id"] for p in progetti if p.get("prospect_id")])
    for p in progetti:
        az = aziende.get(p.get("prospect_id"), "")
        titolo = f"Scadenza: {p['nome']}" + (f", {az}" if az else "")
        chi = f"Segue {p['chi_segue']}." if p.get("chi_segue") else ""
        e = scrivi(cid, f"progetto:{p['id']}", titolo, p["scadenza"], f"{chi} Dal Workspace.", prova)
        if e:
            conta[e] = conta.get(e, 0) + 1

    # 2. le prove che finiscono: e' il giorno in cui si decide il rinnovo
    prove = sb("GET", "/rest/v1/prospects?select=id,company,name,prova_fine"
                      f"&prova_fine=gte.{oggi.isoformat()}&prova_fine=lte.{fino}&limit=200") or []
    for p in prove:
        nome = p.get("company") or p.get("name") or ""
        e = scrivi(cid, f"prova:{p['id']}", f"Finisce la prova: {nome}", p["prova_fine"],
                   "Da qui si decide il rinnovo. Dal Workspace.", prova)
        if e:
            conta[e] = conta.get(e, 0) + 1

    # 3. le task con una data, di chiunque
    task = sb("GET", "/rest/v1/task?select=id,titolo,scadenza,owner,fatta"
                     f"&scadenza=gte.{oggi.isoformat()}&scadenza=lte.{fino}&fatta=is.false&limit=500") or []
    profili = {r["id"]: r.get("nome") for r in (sb("GET", "/rest/v1/profili?select=id,nome") or [])}
    for t in task:
        chi = profili.get(t.get("owner")) or ""
        e = scrivi(cid, f"task:{t['id']}", f"{t['titolo']}" + (f", {chi}" if chi else ""), t["scadenza"],
                   "Task del Workspace.", prova)
        if e:
            conta[e] = conta.get(e, 0) + 1

    print(f"{'(prova) ' if prova else ''}calendario: {conta.get('nuovo', 0)} nuovi, "
          f"{conta.get('aggiornato', 0)} aggiornati, {conta.get('prova', 0)} da scrivere")


if __name__ == "__main__":
    main()
