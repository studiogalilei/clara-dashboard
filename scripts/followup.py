#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""IL FOLLOW-UP COME FLUSSO (24/9/2026).

Dre, 24/9: accettata l'idea «ora che Clara manda, i follow-up diventano una
fila in Posta: template FOLLOW UP 1, Approva e manda, uno dopo l'altro».

Chi: ha ricevuto l'analisi da almeno 5 giorni (playbook), non ha piu' scritto,
non e' fuori, non e' perso, non ha il «niente follow-up» (gigante buono), non
ha gia' avuto un follow-up (una mail nostra dopo l'analisi, o una proposta
FOLLOW UP 1 di qualunque stato).
Cosa (25/9, nessuna bozza senza lettura): questo script NON scrive piu' il
testo. Mette la persona IN CODA (prospects.coda = «FOLLOW UP 1» o «MINI FOLLOW
UP») e il motore delle bozze (bozze.py) legge il filo vero, applica il template
di Dre e passa dalla seconda testa. Il template sta nel file di Dre «Risposte
(template verbatim)».

USO
  python3 scripts/followup.py            propone
  python3 scripts/followup.py --prova    mostra e non propone
"""
import datetime
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from stanza import sb                                       # noqa: E402

GIORNI = 5
QUANTI = 50
CLASSI = "positivo,tiepido,da_classificare"


def gia_avute(*template):
    """Chi ha gia' avuto quella proposta: aperta, mandata, o rifiutata da Dre («NO: ...»).
    Le proposte chiuse dagli script il 25/9 (scritte senza lettura) non contano: si rifanno."""
    rs = sb("GET", f"/rest/v1/proposte?select=prospect_id,stato,risposta&azione->>template=in.({','.join(template)})&limit=5000") or []
    return {x["prospect_id"] for x in rs if x["stato"] != "no" or (x.get("risposta") or "").startswith("NO:")}


def in_coda(pid, gruppo):
    """In coda: il motore delle bozze la trova al prossimo giro (5 minuti) e scrive dopo aver letto."""
    sb("PATCH", f"/rest/v1/prospects?id=eq.{pid}", {"coda": gruppo, "coda_il": datetime.datetime.now(datetime.timezone.utc).isoformat()})


def mini_followup(prova, oggi):
    """IL MINI FOLLOW-UP (Dre, 25/9): a chi ha ricevuto la ripresa (analisi + call) e
    dopo sei giorni non ha risposto, due righe, una volta sola."""
    da = (oggi - datetime.timedelta(days=6)).isoformat()
    mandate = sb("GET", f"/rest/v1/proposte?select=prospect_id,risposta_il&stato=eq.fatta&azione->>intento=eq.RIPRESA&risposta_il=lte.{da}T23:59:59&limit=2000") or []
    gia = gia_avute("MINI%20FOLLOW%20UP")
    n = 0
    for m in mandate:
        pid = m["prospect_id"]
        if not pid or pid in gia:
            continue
        p = (sb("GET", f"/rest/v1/prospects?select=id,name,company,email,last_reply_at,awaiting_us,no_followup,fuori,stage,classificazione,coda&id=eq.{pid}") or [None])[0]
        if not p or p.get("awaiting_us") or p.get("no_followup") or p.get("fuori") or p.get("stage") in ("perso", "cliente"):
            continue
        if p.get("last_reply_at") and p["last_reply_at"] > m["risposta_il"]:
            continue                                        # ha risposto dopo la ripresa: non e' un silenzio
        if p.get("classificazione") in ("negativo", "soppresso", "nervoso", "fuori_target", "persona_sbagliata"):
            continue
        if p.get("coda"):
            continue
        azienda = p.get("company") or p.get("email")
        print(f"  mini → in coda {azienda[:36]}")
        if not prova:
            in_coda(pid, "MINI FOLLOW UP")
        n += 1
    print(f"mini follow-up: {n}")


def main():
    prova = "--prova" in sys.argv
    mini_followup(prova, datetime.date.today())
    oggi = datetime.date.today()
    righe = sb("GET", "/rest/v1/prospects?select=id,name,company,email,analysis_sent_at,last_reply_at,classificazione,analysis_pdf,coda"
                      f"&analysis_sent=eq.true&awaiting_us=eq.false&no_followup=eq.false&fuori=eq.false&stage=neq.perso"
                      f"&classificazione=in.({CLASSI})&order=analysis_sent_at.desc&limit=500") or []
    gia = gia_avute("FOLLOW%20UP%201")
    fatti = 0
    for p in righe:
        if not p.get("analysis_sent_at") or p["id"] in gia or p.get("coda"):
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
        azienda = p.get("company") or p.get("email")
        print(f"  {azienda[:36]:36} analisi del {inviata:%d/%m}  → in coda FOLLOW UP 1")
        if prova:
            fatti += 1
            continue
        in_coda(p["id"], "FOLLOW UP 1")
        fatti += 1
        if fatti >= QUANTI:
            break
    print(f"followup: {fatti} messi in coda su {len(righe)} con l'analisi mandata")


if __name__ == "__main__":
    main()
