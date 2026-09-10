#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""IL CAMPANELLO DI SMARTLEAD (10/9/2026).

Dre: «voglio che le mail di Smartlead si vedano subito». Smartlead sa
chiamare un indirizzo a ogni risposta (webhook), ma va detto campagna per
campagna. Questo script passa tutte le campagne (anche quelle in pausa o
finite: le risposte ai vecchi invii arrivano lo stesso) e si assicura che
ognuna abbia il campanello puntato alla funzione cloud di Clara
(supabase/functions/smartlead-webhook), che fa partire subito il direttore.

Gira una volta al giorno dal direttore (operazione `webhooks`), cosi' le
campagne nuove lo prendono da sole.

USO
  python3 scripts/webhook_smartlead.py           registra dove manca
  python3 scripts/webhook_smartlead.py --prova   mostra e non scrive
"""

import json
import os
import sys
import urllib.parse
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from stanza import env                                     # noqa: E402

SL = "https://server.smartlead.ai/api/v1"
NOME = "clara-workspace"
EVENTI = ["EMAIL_REPLY", "EMAIL_BOUNCE", "LEAD_UNSUBSCRIBED"]   # le categorie no: Smartlead vuole la lista


def chiave_smartlead():
    k = env("SMARTLEAD_API_KEY")
    if k:
        return k
    try:
        for riga in open(os.path.expanduser("~/.hermes/config.yaml"), encoding="utf-8"):
            if riga.strip().startswith("SMARTLEAD_API_KEY:"):
                return riga.split(":", 1)[1].strip()
    except OSError:
        pass
    sys.exit("ERRORE: SMARTLEAD_API_KEY non trovata")


def sl(metodo, via, k, corpo=None):
    url = f"{SL}{via}{'&' if '?' in via else '?'}api_key={k}"
    req = urllib.request.Request(url, method=metodo, headers={"Content-Type": "application/json", "User-Agent": "clara-dashboard"},
                                 data=json.dumps(corpo).encode() if corpo is not None else None)
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read() or b"null")


def main():
    prova = "--prova" in sys.argv
    k = chiave_smartlead()
    segreto = env("WEBHOOK_SEGRETO")
    base = env("SUPABASE_FUNZIONI_URL") or "https://tqssfcuzezlczfceqsmk.supabase.co/functions/v1"
    if not segreto:
        sys.exit("ERRORE: manca WEBHOOK_SEGRETO")
    indirizzo = f"{base}/smartlead-webhook?chiave={urllib.parse.quote(segreto)}"

    campagne = sl("GET", "/campaigns", k) or []
    messi, gia = 0, 0
    for c in campagne:
        if c.get("status") == "DRAFTED":
            continue
        esistenti = sl("GET", f"/campaigns/{c['id']}/webhooks", k) or []
        nostro = next((w for w in esistenti if (w.get("webhook_url") or "").startswith(base + "/smartlead-webhook")), None)
        if nostro and nostro.get("webhook_url") == indirizzo and set(nostro.get("event_types") or []) >= set(EVENTI):
            gia += 1
            continue
        corpo = {"id": nostro["id"] if nostro else None, "name": NOME, "webhook_url": indirizzo, "event_types": EVENTI}
        print(f"  {'aggiorno' if nostro else 'metto':8} {c['id']} {c.get('status'):9} {c.get('name', '')[:50]}")
        if not prova:
            sl("POST", f"/campaigns/{c['id']}/webhooks", k, corpo)
        messi += 1
    print(f"campanello smartlead: {messi} messi, {gia} gia' a posto, {len(campagne)} campagne")


if __name__ == "__main__":
    main()
