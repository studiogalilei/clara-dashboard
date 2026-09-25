#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""LA SALUTE DEL SISTEMA (25/9/2026, da Galileo: «l'assenza e' il controllo»).

Ogni mattina Clara controlla se stessa, e parla solo se c'e' un problema:
1. corse in errore nelle ultime 24 ore (raggruppate per operazione);
2. operazioni accese che non girano da piu' di tre volte la loro cadenza;
3. bozze aperte da piu' di 21 giorni (stanno marcendo in Posta);
4. classificazioni che cambiano avanti e indietro (piu' di 2 cambi in 7 giorni);
5. proposte aperte per chi non e' piu' un lead (non dovrebbero esistere: trigger).
Se tutto e' in ordine, una riga «controllo» e basta. Se no, una Domanda in Posta.

USO
  python3 scripts/salute.py            controlla e scrive
  python3 scripts/salute.py --prova    controlla e stampa
"""
import collections
import datetime
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from stanza import sb, di_clara, contattabile, proponi        # noqa: E402


def main():
    prova = "--prova" in sys.argv
    ora = datetime.datetime.now(datetime.timezone.utc)
    z = lambda d: d.strftime("%Y-%m-%dT%H:%M:%SZ")
    problemi = []
    # 1. errori
    err = sb("GET", f"/rest/v1/corse?select=operazione,dettaglio&esito=eq.errore&at=gte.{z(ora - datetime.timedelta(days=1))}&limit=500") or []
    if err:
        c = collections.Counter(e["operazione"] for e in err)
        problemi.append("errori nelle ultime 24 ore: " + ", ".join(f"{k} ×{v}" for k, v in c.most_common()))
    # 2. operazioni ferme
    ferme = []
    for o in sb("GET", "/rest/v1/operazioni?select=chiave,cadenza_minuti,ultima_corsa,attiva,comando") or []:
        if not o["attiva"] or not o.get("comando"):
            continue
        u = o.get("ultima_corsa")
        if not u:
            ferme.append(f"{o['chiave']} (mai girata)"); continue
        ritardo = (ora - datetime.datetime.fromisoformat(u.replace("Z", "+00:00"))).total_seconds() / 60
        if ritardo > 3 * max(int(o["cadenza_minuti"] or 60), 5) + 30:
            ferme.append(f"{o['chiave']} (da {int(ritardo // 60)} ore)")
    if ferme:
        problemi.append("operazioni ferme: " + ", ".join(ferme))
    # 3. bozze vecchie
    vecchie = sb("GET", f"/rest/v1/proposte?select=id,titolo&stato=eq.aperta&tipo=in.(risposta,umano)&at=lte.{z(ora - datetime.timedelta(days=21))}&limit=200") or []
    if vecchie:
        problemi.append(f"{len(vecchie)} bozze aperte da più di 21 giorni (es. {vecchie[0]['titolo'][:40]})")
    # 4. classificazioni ballerine
    reg = sb("GET", f"/rest/v1/registro?select=riga&tabella=eq.prospects&campo=eq.classificazione&at=gte.{z(ora - datetime.timedelta(days=7))}&limit=5000") or []
    ball = [k for k, v in collections.Counter(r["riga"] for r in reg).items() if v > 2]
    if ball:
        problemi.append(f"{len(ball)} aziende con la classificazione cambiata più di 2 volte in 7 giorni")
    # 5. bozze a chi non e' piu' un lead
    ap = sb("GET", "/rest/v1/proposte?select=id,prospect_id&stato=in.(aperta,approvata)&tipo=in.(risposta,umano)&prospect_id=not.is.null&limit=1000") or []
    ids = list({x["prospect_id"] for x in ap})
    stato = {}
    for i in range(0, len(ids), 100):
        for p in sb("GET", f"/rest/v1/prospects?select=id,fuori,stage,pipeline_stage,no_followup,classificazione&id=in.({','.join(ids[i:i+100])})") or []:
            stato[p["id"]] = p
    fuori = [x for x in ap if x["prospect_id"] in stato and not contattabile(stato[x["prospect_id"]])]
    if fuori:
        problemi.append(f"{len(fuori)} bozze aperte per aziende che non sono più lead (il trigger dovrebbe impedirlo)")
    testo = "Tutto in ordine: nessun errore, operazioni regolari, Posta pulita." if not problemi else "Salute del sistema:\n- " + "\n- ".join(problemi)
    print(testo)
    if prova:
        return
    if problemi:
        proponi("umano", "Salute del sistema: c'è qualcosa che non torna", perche=testo[:280], azione={"salute": problemi, "giorno": ora.date().isoformat()}, ref=f"salute:{ora.date().isoformat()}")
    else:
        di_clara("controllo", testo, letto=True)


if __name__ == "__main__":
    main()
