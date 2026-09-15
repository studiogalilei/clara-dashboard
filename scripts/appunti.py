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
import zoneinfo

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from stanza import sb, proponi                             # noqa: E402
import cervello                                            # noqa: E402
from google_api import drive_cerca, drive_testo, drive_copia, cartella   # noqa: E402

ROMA = zoneinfo.ZoneInfo("Europe/Rome")
CLIENTI = "1r1jtdy1ulJHrSARauKHH20HvgP5yNMqT"    # «1 Clienti» nel Drive condiviso (riordinato l'11/9)
GENERICHE = {"studio", "galilei", "studiogalilei", "call", "meet", "riunione", "meeting", "conoscitiva", "tecnica",
             "chiamata", "senza", "titolo", "appunti", "gemini", "sito", "marketing", "b2b", "google", "ads", "srl", "spa",
             "snc", "sas", "srls", "group", "italia", "italy", "servizi", "service", "services", "del", "della", "con",
             "per", "the", "and", "web", "digital", "agency", "consulting", "società", "societa", "impresa", "azienda",
             "ditta", "office", "team", "project", "progetto", "manufacturing", "solutions", "company", "international"}


def quando_dal_titolo(nome):
    m = re.search(r"(\d{4})/(\d{2})/(\d{2}) (\d{2}):(\d{2})", nome)
    if not m:
        return None
    y, mo, d, h, mi = map(int, m.groups())
    return datetime.datetime(y, mo, d, h, mi, tzinfo=ROMA)   # ora di Roma (il titolo la porta cosi')


def parole(s):
    return {w for w in re.findall(r"[a-zà-ú0-9&.']{3,}", (s or "").lower()) if w.strip(".&'") not in GENERICHE and len(w.strip(".&'")) >= 3}


def forti(p):
    """Le parole che identificano un'azienda: nome della societa' e cognome della persona, senza le generiche."""
    return {w for w in parole(p.get("company")) | parole(p.get("name")) if len(w) >= 4}


def punteggio(p, testo_parole):
    f = forti(p)
    if not f:
        return 0
    comuni = f & testo_parole
    if not comuni:
        return 0
    # basta: tutte le parole forti dell'azienda (es. «sarci»), o due parole, o una parola lunga (un cognome vero)
    return 2 if comuni == f or len(comuni) >= 2 or any(len(w) >= 6 for w in comuni) else 0


def di_chi(doc, testo, aziende):
    """Prima l'agenda (stessa ora, ±40 minuti), poi il titolo, poi le prime righe del testo. Solo se e' uno solo."""
    q = quando_dal_titolo(doc["name"])
    if q:
        da = (q - datetime.timedelta(minutes=40)).isoformat()
        a = (q + datetime.timedelta(minutes=40)).isoformat()
        ev = sb("GET", f"/rest/v1/agenda?select=prospect_id,titolo&prospect_id=not.is.null&at=gte.{urllib.parse.quote(da)}&at=lte.{urllib.parse.quote(a)}&limit=3") or []
        if len(ev) == 1:
            return ev[0]["prospect_id"], "agenda"
    titolo = parole(doc["name"].split(" - ")[0])
    uno = unico([p for p in aziende if punteggio(p, titolo)])
    if uno:
        return uno["id"], "titolo"
    testa = parole(testo[:2000])
    uno = unico([p for p in aziende if punteggio(p, testa)])
    if uno:
        return uno["id"], "testo"
    return None, None


def unico(cand):
    """Uno solo; o piu' contatti della stessa azienda: quello con l'SG-ID (il capofila), se no il primo."""
    if not cand:
        return None
    if len(cand) == 1:
        return cand[0]
    if len({(c.get("company") or "").strip().lower() for c in cand}) == 1:
        return next((c for c in cand if c.get("sg_id")), cand[0])
    return None


def main():
    prova = "--prova" in sys.argv
    giorni = int(sys.argv[sys.argv.index("--giorni") + 1]) if "--giorni" in sys.argv else 3
    da = (datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=giorni)).strftime("%Y-%m-%dT%H:%M:%SZ")

    # DA TUTTE LE CALL, NON SOLO DALLE MIE (Dre, 15/9): «se Carlo fa una call
    # e gli appunti arrivano nel suo Drive, devono aggiornare anche il mio».
    # Il progetto Cloud e' uno solo, ma il permesso lo da' ognuno per se':
    # si gira su tutte le caselle collegate e si legge il Drive di ognuno.
    # Quello che si trova finisce nella stessa Scheda, che e' di tutti.
    persone = sb("GET", "/rest/v1/google_token?select=email,user_id") or []
    if not persone:
        print("appunti: nessuno ha collegato Google")
        return
    q = (f"name contains 'Appunti di Gemini' and mimeType = 'application/vnd.google-apps.document' "
         f"and modifiedTime > '{da}' and trashed = false")
    docs, visti, di_chi_e = [], set(), {}
    for u in persone:
        try:
            suoi = drive_cerca(q, email=u["email"])
        except Exception as e:      # un token revocato di uno non ferma gli altri
            print(f"  Drive di {u['email']}: {str(e)[:140]}")
            continue
        for d in suoi:
            if d["id"] in visti:
                continue
            visti.add(d["id"])
            di_chi_e[d["id"]] = u["email"]
            docs.append(d)
    if not docs:
        print("appunti: niente di nuovo nel Drive")
        return
    gia = {r["ref"] for r in (sb("GET", "/rest/v1/interactions?select=ref&ref=like.gemini:*&limit=5000") or [])}
    chiesti = {(pr.get("azione") or {}).get("appunti_id") for pr in (sb("GET", "/rest/v1/proposte?select=azione&tipo=eq.richiesta&limit=5000") or [])}
    aziende = sb("GET", "/rest/v1/prospects?select=id,company,name,sg_id&stage=neq.nuovo&limit=2000") or []
    messi, domande, saltati = 0, 0, 0
    for doc in docs:
        ref = "gemini:" + doc["id"]
        if ref in gia or doc["id"] in chiesti:
            continue
        # la copia che mettiamo noi nella cartella del cliente ha «(SG)» nel nome:
        # se no al giro dopo la rileggiamo, stessa ora e stessa azienda, e l'indice
        # unico di interactions fa 409 (28 corse in errore, QA del 14/9)
        if "(SG)" in doc["name"]:
            continue
        mio = di_chi_e.get(doc["id"])
        testo = drive_testo(doc["id"], email=mio)
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
        try:
            q = quando_dal_titolo(doc["name"])
            at = q.astimezone(datetime.timezone.utc).isoformat() if q else doc["createdTime"]
            # il recap corto in testa (Dre, 15/9: «come Granola, si capisce
            # subito»), gli appunti interi restano nel Drive, col link. Se il
            # cervello non risponde si tiene il testo com'e': meglio lungo
            # che niente.
            corto = cervello.recap(testo, azienda=nome, quando=(at or "")[:10])
            corpo = (f"{corto}\n\nAppunti interi: {doc.get('webViewLink', '')}" if corto
                     else f"Appunti di Gemini: {doc.get('webViewLink', '')}\n\n" + " ".join(testo.split())[:12000])
            sb("POST", "/rest/v1/interactions", {"prospect_id": p["id"], "at": at, "kind": "transcript", "body": corpo, "ref": ref})
            messi += 1
        except Exception as e:                                       # una riga rotta non ferma le altre
            print(f"     (non messo: {str(e)[:140]})")
            saltati += 1
            continue
        try:
            etichetta = f"SG-{p['sg_id']} {nome}" if p.get("sg_id") else nome
            cart = cartella(etichetta if p.get("sg_id") else nome, CLIENTI, email=mio)
            drive_copia(doc["id"], f"{doc['name']} (SG)", cart, email=mio)
        except Exception as e:                                       # la copia e' un di piu': la Scheda e' gia' a posto
            print(f"     (copia nel Drive non riuscita: {str(e)[:120]})")
    print(f"appunti: {messi} messi nelle Schede, {domande} domande, {saltati} saltati, "
          f"{len(docs)} documenti visti nei Drive di {len(persone)} persone")


if __name__ == "__main__":
    main()
