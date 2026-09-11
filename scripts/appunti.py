#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""GLI APPUNTI DI GEMINI (11/9/2026).

Dre: le call sono quasi tutte su Meet, e Gemini a fine call scrive gli
appunti nel Drive (riassunto, dettagli, passi successivi). Al posto di
Granola. Questo script, ogni mezz'ora:
1. cerca nel Drive i «Appunti di Gemini» degli ultimi giorni (a nome di Dre,
   col suo token: scripts/google_api.py);
2. capisce di che azienda sono: l'evento in agenda alla stessa ora, o il
   nome dell'azienda nel titolo o nel testo;
3. li mette nella Scheda come interazione «transcript» (da li' l'operazione
   `transcript` propone fase e prossimo passo, come col testo incollato);
4. ne fa una copia nella cartella del cliente nel Drive condiviso (1 Clienti /
   SG-xxxx Nome).
Se non capisce di chi sono, lo chiede nella stanza, una volta sola.

USO
  python3 scripts/appunti.py            gli ultimi 3 giorni
  python3 scripts/appunti.py --prova    mostra e non scrive
  python3 scripts/appunti.py --giorni 30
"""

import datetime
import os
import re
import sys
import urllib.parse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from stanza import sb, proponi                             # noqa: E402
from google_api import drive_cerca, drive_testo, drive_copia, cartella   # noqa: E402

CLIENTI = "1r1jtdy1ulJHrSARauKHH20HvgP5yNMqT"    # «1 Clienti» nel Drive condiviso (riordinato l'11/9)
GENERICHE = {"studio", "galilei", "studiogalilei", "call", "meet", "riunione", "meeting", "conoscitiva", "tecnica",
             "chiamata", "senza", "titolo", "appunti", "gemini", "sito", "marketing", "b2b", "google", "ads", "x"}


def quando_dal_titolo(nome):
    m = re.search(r"(\d{4})/(\d{2})/(\d{2}) (\d{2}):(\d{2})", nome)
    if not m:
        return None
    y, mo, d, h, mi = map(int, m.groups())
    return datetime.datetime(y, mo, d, h, mi)          # ora locale di Dre (il titolo la porta cosi')


def parole(s):
    return {w for w in re.findall(r"[a-zà-ú0-9]{3,}", (s or "").lower()) if w not in GENERICHE}


def di_chi(doc, testo, aziende):
    """Prima l'agenda (stessa ora, ±40 minuti), poi i nomi nel titolo, poi nel testo."""
    q = quando_dal_titolo(doc["name"])
    if q:
        da = (q - datetime.timedelta(minutes=40)).isoformat()
        a = (q + datetime.timedelta(minutes=40)).isoformat()
        ev = sb("GET", f"/rest/v1/agenda?select=prospect_id,titolo&prospect_id=not.is.null&at=gte.{urllib.parse.quote(da)}&at=lte.{urllib.parse.quote(a)}&limit=3") or []
        if len(ev) == 1:
            return ev[0]["prospect_id"], "agenda"
    titolo = parole(doc["name"].split(" - ")[0])
    for p in aziende:
        nome = parole(p.get("company")) | parole(p.get("name"))
        if nome and nome <= titolo:
            return p["id"], "titolo"
    testa = parole(testo[:1500])
    trovati = [p for p in aziende if parole(p.get("company")) and parole(p.get("company")) <= testa]
    if len(trovati) == 1:
        return trovati[0]["id"], "testo"
    return None, None


def main():
    prova = "--prova" in sys.argv
    giorni = int(sys.argv[sys.argv.index("--giorni") + 1]) if "--giorni" in sys.argv else 3
    da = (datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=giorni)).strftime("%Y-%m-%dT%H:%M:%SZ")
    docs = drive_cerca(f"name contains 'Appunti di Gemini' and mimeType = 'application/vnd.google-apps.document' "
                       f"and modifiedTime > '{da}' and trashed = false")
    if not docs:
        print("appunti: niente di nuovo nel Drive")
        return
    gia = {r["ref"] for r in (sb("GET", "/rest/v1/interactions?select=ref&ref=like.gemini:*&limit=5000") or [])}
    chiesti = {(pr.get("azione") or {}).get("appunti_id") for pr in (sb("GET", "/rest/v1/proposte?select=azione&tipo=eq.richiesta&limit=5000") or [])}
    aziende = sb("GET", "/rest/v1/prospects?select=id,company,name,sg_id&stage=neq.nuovo&limit=2000") or []
    messi, domande = 0, 0
    for doc in docs:
        ref = "gemini:" + doc["id"]
        if ref in gia or doc["id"] in chiesti:
            continue
        testo = drive_testo(doc["id"])
        if len(testo.strip()) < 200:
            continue
        pid, come = di_chi(doc, testo, aziende)
        p = next((x for x in aziende if x["id"] == pid), None)
        titolo = doc["name"].replace(" - Appunti di Gemini", "")
        if not p:
            print(f"  ?  {titolo[:70]}")
            if not prova and proponi("richiesta", f"Appunti di Gemini: «{titolo[:80]}». Di che azienda sono?",
                                     perche="Non ho trovato l'evento in agenda ne' un nome che conosco. Dimmi l'azienda e li metto nella sua Scheda.",
                                     azione={"appunti_id": doc["id"], "link": doc.get("webViewLink")}):
                domande += 1
            continue
        nome = p.get("company") or p.get("name")
        print(f"  ok {titolo[:60]:60} → {nome} ({come})")
        if prova:
            continue
        q = quando_dal_titolo(doc["name"])
        at = (q.isoformat() + "+02:00") if q else doc["createdTime"]
        corpo = f"Appunti di Gemini: {doc.get('webViewLink', '')}\n\n" + " ".join(testo.split())[:12000]
        sb("POST", "/rest/v1/interactions", {"prospect_id": p["id"], "at": at, "kind": "transcript", "body": corpo, "ref": ref})
        try:
            etichetta = f"SG-{p['sg_id']} {nome}" if p.get("sg_id") else nome
            cart = cartella(etichetta if p.get("sg_id") else nome, CLIENTI)
            drive_copia(doc["id"], doc["name"], cart)
        except Exception as e:                                       # la copia e' un di piu': la Scheda e' gia' a posto
            print(f"     (copia nel Drive non riuscita: {str(e)[:120]})")
        messi += 1
    print(f"appunti: {messi} messi nelle Schede, {domande} domande, {len(docs)} documenti visti")


if __name__ == "__main__":
    main()
