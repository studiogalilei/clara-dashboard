#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""I SILENZI: dopo il follow-up, 10 giorni senza risposta e si esce dai prospect (9/9/2026, corretto 5/10).

Dre: «se dopo il follow-up non li sentiamo entro 10 giorni, li togliamo dalla
lista prospect». Regola secca, senza domanda: chi ha ricevuto l'analisi, non
ha risposto da allora, e sono passati 10 giorni, va nei Persi con scritto il
motivo. Il recap lo dice. Se poi risponde, il sync lo riporta vivo da solo
(awaiting_us torna vero e Clara prepara la risposta).

Non tocca chi ha una data futura (rinvio, ferie) o chi e' gia' fermo a mano.

USO
  python3 scripts/silenzi.py            applica
  python3 scripts/silenzi.py --prova    mostra e basta
"""

import datetime
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from stanza import sb, di_clara                            # noqa: E402

GIORNI = 10


def ultimo_seguito(p):
    """La data dell'ultimo follow-up PARTITO dopo l'analisi, o None.

    5/10, Dre: «la giornata non e' finita se chi deve avere un follow-up non l'ha
    avuto». I 10 giorni contavano dall'analisi, non dal follow-up: se la bozza
    restava in Posta, al decimo giorno il lead finiva nei Persi senza aver mai
    ricevuto il seguito. Cosi' ne sono spariti 103, quasi tutti sì con l'analisi
    in mano. Conta solo cio' che e' partito davvero: una mail nostra nel filo
    dopo il giorno dell'analisi, o una bozza di risposta segnata «fatta»."""
    dopo = (datetime.date.fromisoformat(p["analysis_sent_at"][:10]) + datetime.timedelta(days=1)).isoformat()
    date = []
    for r in sb("GET", f"/rest/v1/interactions?select=at&prospect_id=eq.{p['id']}&kind=in.(email_out,followup)"
                       f"&at=gte.{dopo}&order=at.desc&limit=1") or []:
        date.append(r["at"][:10])
    for r in sb("GET", f"/rest/v1/proposte?select=risposta_il&prospect_id=eq.{p['id']}&tipo=eq.risposta&stato=eq.fatta"
                       f"&risposta_il=gte.{dopo}&order=risposta_il.desc&limit=1") or []:
        date.append(r["risposta_il"][:10])
    return max(date) if date else None


def ripreso_dopo(p, seguito):
    """Dre l'ha ripreso dall'archivio dopo l'ultimo follow-up partito (la nota la scrive
    percorso.riprendiDallArchivio)."""
    r = sb("GET", f"/rest/v1/interactions?select=at&prospect_id=eq.{p['id']}&kind=eq.nota"
                  "&body=ilike.Ripreso%20dall*&order=at.desc&limit=1") or []
    return bool(r) and (not seguito or r[0]["at"][:10] > seguito)


def proponi_scaduto(p):
    from stanza import proponi
    nome = p.get("company") or p.get("name") or "?"
    proponi("umano", f"{nome}: l'avevi ripreso dall'archivio, e il giorno e' arrivato senza un messaggio",
            prospect_id=p["id"], ref=f"ripreso-scaduto:{p['id']}:{p.get('next_action_date') or ''}",
            perche="Dieci giorni fa l'hai rimesso fra i lead. Non e' partito niente. Fai cosi' = lo rimetto in archivio; "
                   "Lascia stare = resta fra i lead e ci pensi tu.")


def main():
    prova = "--prova" in sys.argv
    oggi = datetime.date.today()
    soglia = (oggi - datetime.timedelta(days=GIORNI)).isoformat()
    righe = sb("GET", "/rest/v1/prospects?select=id,company,name,analysis_sent_at,last_reply_at,next_action_date,ooo_until,followup_due"
                      f"&fuori=eq.false&analysis_sent=eq.true&awaiting_us=eq.false&no_followup=eq.false"
                      f"&stage=not.in.(nuovo,perso,cliente)&passato_a=is.null&analysis_sent_at=lte.{soglia}"
                      "&or=(classificazione.is.null,classificazione.not.in.(negativo,fuori_target,soppresso))&limit=1000") or []
    usciti = 0
    for p in righe:
        # ha risposto dopo l'analisi? allora non e' silenzio
        if p.get("last_reply_at") and p["last_reply_at"] > p["analysis_sent_at"]:
            continue
        # una data futura (rinvio, ferie, la ripresa dall'archivio): si aspetta quella, e quel
        # giorno compreso (revisione 7/10: il giorno della scadenza un ripreso tornava in
        # archivio senza che nessuno vedesse il promemoria)
        futura = max([d for d in (p.get("next_action_date"), p.get("ooo_until")) if d] or [""])
        if futura and futura[:10] >= oggi.isoformat():
            continue
        # ripreso dall'archivio da Dre: non si riarchivia in silenzio. Si dice in Posta una volta,
        # e decide lui (regola 4 del 28/9: niente attese che finiscono senza avviso)
        if ripreso_dopo(p, ultimo_seguito(p)):
            if not prova:
                proponi_scaduto(p)
            continue
        # il silenzio si conta dal follow-up partito: senza follow-up non e' un silenzio, e' un debito nostro
        seguito = ultimo_seguito(p)
        if not seguito or seguito > soglia:
            continue
        nome = p.get("company") or p.get("name") or "?"
        if prova:
            print(f"  esce: {nome} (analisi {p['analysis_sent_at'][:10]})"); usciti += 1; continue
        sb("PATCH", f"/rest/v1/prospects?id=eq.{p['id']}", {
            "stage": "perso", "no_followup": True,
            "lost_reason": f"Nessuna risposta dopo l'analisi ({GIORNI} giorni), uscito dai prospect il {oggi:%d/%m/%Y}",
        })
        usciti += 1
    print(f"silenzi: {usciti} usciti dai prospect, {len(righe)} controllati")


if __name__ == "__main__":
    main()
