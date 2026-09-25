#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""IL CONTATTO NUOVO (25/9/2026): chi ci ha risposto «non sono io, scrivete a X».

Dopo la rilettura, «persona sbagliata» sono 18. Alcuni ci hanno dato l'indirizzo
giusto: sta nella loro mail o nella nota della rilettura. Qui si prende
quell'indirizzo, si mette in email_alt (la bozza e l'invio vanno li', nello
stesso thread), e la persona torna «aspetta noi»: bozze.py scrive la risposta
col template del rimbalzo interno e l'analisi va al referente giusto.
Le autorisposte di helpdesk e ticket restano fuori: non c'e' nessuno da scrivere.

USO
  python3 scripts/nuovo_contatto.py --prova
  python3 scripts/nuovo_contatto.py
"""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))   # i moduli comuni stanno in scripts/
from stanza import sb                                       # noqa: E402

NOSTRI = ("studiogalilei", "galilei")
AUTO = re.compile(r"autorisposta|auto-?repl|ticket|helpdesk|help desk|assistenza", re.I)
MAIL = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")


def nuovo_indirizzo(p):
    mio = (p.get("email") or "").lower()
    testi = [((p.get("enriched") or {}).get("lettura") or {}).get("perche") or ""]
    ult = sb("GET", f"/rest/v1/interactions?select=body&prospect_id=eq.{p['id']}&kind=eq.email_in&order=at.desc&limit=1") or []
    if ult:
        testi.append(ult[0].get("body") or "")
    for t in testi:
        for e in MAIL.findall(t):
            e = e.lower().strip(".")
            if e != mio and not any(n in e for n in NOSTRI) and not e.startswith(("noreply", "no-reply", "mailer-daemon", "postmaster")):
                return e
    return None


def main():
    prova = "--prova" in sys.argv
    rs = sb("GET", "/rest/v1/prospects?select=id,company,email,email_alt,enriched,awaiting_us&classificazione=eq.persona_sbagliata&fuori=eq.false&stage=not.in.(perso,cliente)&limit=200") or []
    fatti = 0
    viste = set()          # una mail per azienda, non una per ogni casella vecchia
    for p in rs:
        if (p.get('company') or '').strip().lower() in viste:
            print(f"  {(p.get('company') or '')[:32]:32} stessa azienda, salto"); continue
        viste.add((p.get('company') or '').strip().lower())
        perche = ((p.get("enriched") or {}).get("lettura") or {}).get("perche") or ""
        if AUTO.search(perche) or AUTO.search(p.get("email") or ""):
            continue
        if ((p.get("enriched") or {}).get("contatto_nuovo")):
            continue                                        # gia' fatto: non si rimette in coda a ogni giro
        nuovo = (p.get("email_alt") or [None])[0] or nuovo_indirizzo(p)
        nome = (p.get("company") or p.get("email"))[:32]
        if not nuovo:
            print(f"  {nome:32} contatto nuovo non trovato: resta com'e'"); continue
        print(f"  {nome:32} → {nuovo}")
        if prova:
            fatti += 1; continue
        arr = dict(p.get("enriched") or {}); arr["contatto_nuovo"] = {"email": nuovo, "da": "rilettura 25/9"}
        sb("PATCH", f"/rest/v1/prospects?id=eq.{p['id']}", {"email_alt": [nuovo], "awaiting_us": True, "enriched": arr})
        fatti += 1
    print(f"contatto nuovo: {fatti} pronti per la bozza al referente giusto")


if __name__ == "__main__":
    main()
