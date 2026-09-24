#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""IL FOLLOW-UP COME FLUSSO (24/9/2026).

Dre, 24/9: accettata l'idea «ora che Clara manda, i follow-up diventano una
fila in Posta: template FOLLOW UP 1, Approva e manda, uno dopo l'altro».

Chi: ha ricevuto l'analisi da almeno 5 giorni (playbook), non ha piu' scritto,
non e' fuori, non e' perso, non ha il «niente follow-up» (gigante buono), non
ha gia' avuto un follow-up (una mail nostra dopo l'analisi, o una proposta
FOLLOW UP 1 di qualunque stato).
Cosa: il template FOLLOW UP 1 parola per parola, con il nome della persona al
posto di «Stefania» (o «Salve,» secco se il nome non c'e'). In allegato la
presentazione di Studio Galilei (manda.py la attacca). Massimo 10 al giorno:
si approvano in fila, non a lotti.

USO
  python3 scripts/followup.py            propone
  python3 scripts/followup.py --prova    mostra e non propone
"""
import datetime
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from stanza import sb, proponi                              # noqa: E402
import cervello                                             # noqa: E402

GIORNI = 5
QUANTI = 10
CLASSI = "positivo,tiepido,da_classificare"


def template_fu1():
    t = cervello.manuale("template")
    m = re.search(r"## FOLLOW UP 1\s*```\s*(.*?)```", t, re.S)
    if not m:
        raise RuntimeError("template FOLLOW UP 1 non trovato nel Manuale")
    return m.group(1).strip()


def nome_di(p):
    n = (p.get("name") or "").strip()
    n = re.sub(r"\s+", " ", n).split(" ")[0] if n else ""
    return n if re.fullmatch(r"[A-Za-zÀ-ÿ'\-]{2,}", n or "") and n.lower() not in ("info", "amministrazione", "ufficio") else ""


def main():
    prova = "--prova" in sys.argv
    base = template_fu1()
    oggi = datetime.date.today()
    righe = sb("GET", "/rest/v1/prospects?select=id,name,company,email,analysis_sent_at,last_reply_at,classificazione,analysis_pdf"
                      f"&analysis_sent=eq.true&awaiting_us=eq.false&no_followup=eq.false&fuori=eq.false&stage=neq.perso"
                      f"&classificazione=in.({CLASSI})&order=analysis_sent_at.desc&limit=500") or []
    gia = {x["prospect_id"] for x in (sb("GET", "/rest/v1/proposte?select=prospect_id&azione->>template=eq.FOLLOW%20UP%201&limit=5000") or [])}
    fatti = 0
    for p in righe:
        if not p.get("analysis_sent_at") or p["id"] in gia:
            continue
        inviata = datetime.date.fromisoformat(p["analysis_sent_at"][:10])
        if (oggi - inviata).days < GIORNI:
            continue
        if p.get("last_reply_at") and p["last_reply_at"][:10] > p["analysis_sent_at"][:10]:
            continue                                        # ha scritto lui dopo l'analisi: non e' un silenzio
        dopo = sb("GET", f"/rest/v1/interactions?select=id&prospect_id=eq.{p['id']}&kind=in.(email_out,followup)"
                         f"&at=gt.{(inviata + datetime.timedelta(days=1)).isoformat()}&limit=1") or []
        if dopo:
            continue                                        # un follow-up c'e' gia' stato
        nome = nome_di(p)
        bozza = base.replace("Salve Stefania,", f"Salve {nome}," if nome else "Salve,")
        azienda = p.get("company") or p.get("email")
        print(f"  {azienda[:36]:36} analisi del {inviata:%d/%m}  → «{bozza.splitlines()[0]}»")
        if prova:
            fatti += 1
            continue
        proponi("risposta", f"Follow-up 1 per {azienda[:40]}", prospect_id=p["id"],
                perche=f"Ha ricevuto l'analisi il {inviata:%d/%m} e non ha più scritto. Template FOLLOW UP 1 parola per parola; in allegato la presentazione dello Studio.",
                azione={"bozza": bozza, "intento": "INT-22", "template": "FOLLOW UP 1", "allega_presentazione": True})
        fatti += 1
        if fatti >= QUANTI:
            break
    print(f"followup: {fatti} proposti su {len(righe)} con l'analisi mandata")


if __name__ == "__main__":
    main()
