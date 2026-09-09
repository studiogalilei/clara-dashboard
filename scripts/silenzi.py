#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""I SILENZI — dopo l'analisi, 10 giorni senza risposta e si esce dai prospect (9/9/2026).

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
from stanza import sb                                      # noqa: E402

GIORNI = 10


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
        # una data futura (rinvio, ferie): si aspetta quella
        futura = max([d for d in (p.get("next_action_date"), p.get("ooo_until")) if d] or [""])
        if futura and futura > oggi.isoformat():
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
