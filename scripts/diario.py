#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""IL DIARIO AZIENDALE (12/9/2026).

Dre (9/9): «mi piace, approvato, ma non lo chiederei ogni giorno». Clara
chiede a ognuno com'e' andata un paio di volte a settimana (martedi' e
giovedi', o il primo giorno utile), con una domanda vera e diversa, nella
sua chat. La risposta la salva la funzione cloud clara-risponde (vede che
l'ultima cosa che Clara ha detto era una domanda del diario) nella tabella
`diario`, che leggono solo Dre e Giacomo. Il lunedi' (--recap) Clara scrive
ai ceo il punto della settimana: cosa e' andato, cosa ha fatto perdere tempo,
chi non ha risposto.

USO
  python3 scripts/diario.py            manda le domande dovute oggi
  python3 scripts/diario.py --recap    il recap del lunedi' (solo se e' lunedi', o --forza)
  python3 scripts/diario.py --prova    mostra e non scrive
"""

import datetime
import os
import random
import sys
import urllib.parse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from stanza import sb, di_clara                            # noqa: E402
import cervello                                            # noqa: E402

MARCA = "📔"     # la domanda del diario si riconosce da qui (la legge clara-risponde)
GIORNI = {1, 3}  # martedi' e giovedi'
DOMANDE = [
    "Com'è andata questa settimana finora? Una cosa che ha funzionato e una che ti ha fatto perdere tempo.",
    "Su cosa hai lavorato di più in questi giorni? C'è qualcosa che ti blocca?",
    "Se potessi cambiare una cosa di come lavoriamo, quale sarebbe? Anche piccola.",
    "Qual è stata la cosa più utile che hai fatto in questi giorni? E quella più inutile?",
    "C'è un cliente o un progetto che ti preoccupa? Dimmelo in due righe, niente di formale.",
    "Cosa ti aspetti dai prossimi giorni? C'è qualcosa che vorresti che qualcuno sapesse?",
    "Come stai, di energia? Dammi un numero da 1 a 10 e il perché.",
]


def persone():
    return sb("GET", "/rest/v1/profili?select=id,nome,ruolo") or []


def ultima_domanda(uid):
    r = sb("GET", f"/rest/v1/clara_messaggi?select=at&owner=eq.{uid}&tipo=eq.domanda&testo=like.{urllib.parse.quote(MARCA)}*&order=at.desc&limit=1") or []
    return r[0]["at"] if r else None


def chiedi_oggi(prova):
    oggi = datetime.date.today()
    if oggi.weekday() not in GIORNI:
        print("diario: oggi non e' giorno di domande")
        return
    fatte = 0
    for p in persone():
        ult = ultima_domanda(p["id"])
        if ult and (datetime.datetime.now(datetime.timezone.utc) - datetime.datetime.fromisoformat(ult.replace("Z", "+00:00"))).days < 2:
            continue
        nome = (p.get("nome") or "").split(" ")[0] or "ciao"
        d = random.choice(DOMANDE)
        domanda = f"{MARCA} {nome}, {d[0].lower()}{d[1:]}"
        print(f"  → {p.get('nome')}: {domanda[:80]}")
        if not prova:
            di_clara("domanda", domanda, owner=p["id"])
            fatte += 1
    print(f"diario: {fatte} domande mandate")


def recap(prova, forza=False):
    if datetime.date.today().weekday() != 0 and not forza:
        print("diario: il recap e' del lunedi'")
        return
    da = (datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=7)).strftime("%Y-%m-%dT%H:%M:%SZ")
    voci = sb("GET", f"/rest/v1/diario?select=user_id,at,domanda,testo&at=gte.{da}&order=at.asc&limit=200") or []
    nomi = {p["id"]: p.get("nome") or "?" for p in persone()}
    muti = [n for i, n in nomi.items() if i not in {v["user_id"] for v in voci}]
    if not voci:
        testo = "Diario della settimana: nessuno ha scritto niente. " + (f"Non hanno risposto: {', '.join(muti)}." if muti else "")
    else:
        righe = "\n".join(f"- {nomi.get(v['user_id'], '?')} ({v['at'][5:10]}): {' '.join(v['testo'].split())[:600]}" for v in voci)
        prompt = f"""Sei Clara, l'assistente di Studio Galilei. E' lunedi' mattina e scrivi a Dre e Giacomo
il punto del diario aziendale della settimana: quello che le persone del team hanno risposto
alle tue domande. Italiano informale e diretto, massimo 12 righe, niente elenchi con voci
tutte uguali, niente trattino lungo. Prima cosa conta (una o due righe), poi persona per
persona in una riga ciascuno (cosa e' andato, cosa li frena), poi se c'e' un pattern che
torna in piu' persone, dillo. Non inventare: solo quello che c'e' scritto.

LE RISPOSTE:
{righe}

NON HANNO RISPOSTO: {', '.join(muti) or 'nessuno'}
"""
        testo = (cervello._chiedi(prompt) or "").strip() or f"Diario della settimana: {len(voci)} risposte.\n{righe}"
    print(testo[:500])
    if not prova:
        di_clara("brief", testo, owner=None)     # ai ceo (owner null = direzione)
    print("diario: recap mandato" if not prova else "diario: recap (prova)")


if __name__ == "__main__":
    prova = "--prova" in sys.argv
    if "--recap" in sys.argv:
        recap(prova, forza="--forza" in sys.argv)
    else:
        chiedi_oggi(prova)
