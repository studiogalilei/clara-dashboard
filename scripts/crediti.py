#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""I CREDITI DELLE PIATTAFORME (Dre, 21/9/2026): «mi serve un modo per
tracciare tutte queste piattaforme, e che Clara mi avvisi quando stanno
finendo, cosi' rimetto crediti».

Ogni sei ore legge il saldo dei servizi che lo espongono e lo scrive in
piattaforme. Sotto la soglia, una riga in chat ai ceo, non piu' di una al
giorno per servizio. Oggi: SearchAPI. Gli altri si aggiungono qui sotto.
"""
import datetime
import json
import os
import sys
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from stanza import sb, env, di_clara                       # noqa: E402


def searchapi():
    a = json.loads(urllib.request.urlopen(f"https://www.searchapi.io/api/v1/me?api_key={env('SEARCHAPI_KEY')}", timeout=30).read())["account"]
    return {"saldo": a["monthly_allowance"] - a["current_month_usage"], "totale": a["monthly_allowance"]}


LETTORI = {"searchapi": searchapi}


def main():
    adesso = datetime.datetime.now(datetime.timezone.utc)
    for nome, leggi in LETTORI.items():
        try:
            s = leggi()
        except Exception as e:
            print(f"{nome}: non leggibile ({str(e)[:80]})"); continue
        riga = (sb("GET", f"/rest/v1/piattaforme?nome=eq.{nome}&limit=1") or [{}])[0]
        s.update({"nome": nome, "aggiornato_il": adesso.isoformat()})
        soglia = riga.get("soglia")
        ultimo = riga.get("avvisato_il")
        if soglia is not None and s["saldo"] < float(soglia):
            da_ore = (adesso - datetime.datetime.fromisoformat(ultimo.replace("Z", "+00:00"))).total_seconds() / 3600 if ultimo else 99
            if da_ore >= 24:
                di_clara("controllo", f"{nome}: restano {int(s['saldo'])} crediti su {int(s['totale'])}, sotto la soglia di {int(soglia)}. "
                                      f"Il pull si ferma da solo quando finiscono: conviene ricaricare.")
                s["avvisato_il"] = adesso.isoformat()
                print(f"{nome}: AVVISATO in chat ({int(s['saldo'])} < {int(soglia)})")
        sb("POST", "/rest/v1/piattaforme", s, {"Prefer": "resolution=merge-duplicates"})
        print(f"{nome}: {int(s['saldo'])}/{int(s['totale'])}")


if __name__ == "__main__":
    main()
