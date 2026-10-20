#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""GLI AVVISI — la notifica arriva a chi deve fare la cosa (24/9/2026).

Prima il telefono squillava solo ai ceo. Una task che Carlo manda ad Alex la
deve sapere Alex, subito, con la scadenza. Ogni 5 minuti: le task nuove con
un destinatario diverso da chi le ha scritte, non ancora avvisate, vanno sul
telefono del destinatario e si segnano (task.avvisata_il).

USO
  python3 scripts/avvisi.py           avvisa
  python3 scripts/avvisi.py --prova   mostra e non manda
"""
import datetime
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from stanza import sb, env                                  # noqa: E402

DASHBOARD = env("DASHBOARD_URL") or "./"


def main():
    prova = "--prova" in sys.argv
    da = (datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=2)).strftime("%Y-%m-%dT%H:%M:%SZ")
    task = sb("GET", f"/rest/v1/task?select=id,titolo,scadenza,owner,da,prospect_id&avvisata_il=is.null&fatta=eq.false&at=gte.{da}&order=at") or []
    nomi = {r["id"]: r["nome"] for r in (sb("GET", "/rest/v1/profili?select=id,nome") or [])}
    mandate = 0
    for t in task:
        if not t.get("owner") or t.get("owner") == t.get("da"):
            continue
        chi = (nomi.get(t.get("da")) or "qualcuno").split(" ")[0]
        entro = f", entro il {t['scadenza'][8:10]}/{t['scadenza'][5:7]}" if t.get("scadenza") else ""
        testo = f"Task da {chi}: {t['titolo'][:80]}{entro}"
        url = f"{DASHBOARD}?scheda={t['prospect_id']}" if t.get("prospect_id") else DASHBOARD
        print(f"  → {nomi.get(t['owner'], t['owner'])[:20]}: {testo}")
        if prova:
            continue
        try:
            from avvisa import avvisa
            avvisa(testo, titolo="Clara", url=url, a=[t["owner"]])
        except Exception as e:                                   # noqa: BLE001
            print(f"    (notifica non partita: {str(e)[:80]})")
        sb("PATCH", f"/rest/v1/task?id=eq.{t['id']}", {"avvisata_il": datetime.datetime.now(datetime.timezone.utc).isoformat()})
        mandate += 1
    print(f"avvisi: {mandate} notifiche, {len(task)} task guardate")


if __name__ == "__main__":
    main()
