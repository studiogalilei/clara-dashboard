#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""IL RECAP — Clara fa il punto tre volte al giorno (9/9/2026).

Dre: «il riquadro "da fare oggi" non so se serve; al massimo Clara fa un
recap la mattina, il pomeriggio e la sera, dove riepiloga le cose che ci
sono ancora». La mattina c'e' gia' il brief (clara.py, ore 8). Questo e' il
punto del pomeriggio (13) e della sera (18): cosa resta aperto, secco, in un
messaggio nella chat di Clara. Se non resta niente, dice quello.

USO
  python3 scripts/recap.py            scrive il recap nella chat
  python3 scripts/recap.py --prova    lo stampa e basta
"""

import datetime
import os
import sys
import zoneinfo

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from stanza import sb                                      # noqa: E402

ROMA = zoneinfo.ZoneInfo("Europe/Rome")


def main():
    prova = "--prova" in sys.argv
    adesso = datetime.datetime.now(ROMA)
    oggi = adesso.date().isoformat()
    fine_giorno = adesso.replace(hour=23, minute=59, second=59).astimezone(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    ora_utc = adesso.astimezone(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    proposte = sb("GET", "/rest/v1/proposte?select=tipo&stato=eq.aperta&limit=500") or []
    bozze = sum(1 for p in proposte if p["tipo"] in ("risposta", "umano"))
    domande = len(proposte) - bozze
    call = sb("GET", f"/rest/v1/agenda?select=at,titolo&at=gte.{ora_utc}&at=lte.{fine_giorno}&order=at.asc&limit=10") or []
    task = sb("GET", f"/rest/v1/task?select=titolo,scadenza&fatta=eq.false&stato=neq.proposta&scadenza=lte.{oggi}&order=scadenza.asc&limit=20") or []
    aspettano = sb("GET", "/rest/v1/prospects?select=id&awaiting_us=eq.true&fuori=eq.false&limit=500") or []
    prove = sb("GET", f"/rest/v1/prospects?select=company,name,prova_fine&fuori=eq.true&pipeline_stage=eq.prova"
                      f"&prova_fine=lte.{(adesso.date() + datetime.timedelta(days=14)).isoformat()}&limit=10") or []

    righe = []
    if call:
        righe.append("• " + " · ".join(f"{datetime.datetime.fromisoformat(c['at'].replace('Z', '+00:00')).astimezone(ROMA):%H:%M} {c['titolo'][:40]}" for c in call[:3]) + (f" (+{len(call) - 3})" if len(call) > 3 else ""))
    if bozze:
        righe.append(f"• {bozze} bozz{'a' if bozze == 1 else 'e'} da approvare nella posta")
    if domande:
        righe.append(f"• {domande} cos{'a' if domande == 1 else 'e'} che ti chiedo")
    if task:
        righe.append(f"• {len(task)} task in scadenza: " + ", ".join(t["titolo"][:30] for t in task[:3]) + ("…" if len(task) > 3 else ""))
    if aspettano:
        righe.append(f"• {len(aspettano)} persone aspettano una risposta")
    if prove:
        righe.append("• prova in scadenza: " + ", ".join(f"{p.get('company') or p.get('name')} il {p['prova_fine'][8:10]}/{p['prova_fine'][5:7]}" for p in prove))

    momento = "pomeriggio" if adesso.hour < 16 else "sera"
    if righe:
        testo = f"Punto del {momento}. Resta aperto:\n" + "\n".join(righe)
    else:
        testo = f"Punto del {momento}: non resta niente di aperto. Bella giornata."
    if prova:
        print(testo); return
    # uno per momento: se e' gia' scritto, non si ripete
    da = adesso.replace(hour=12 if momento == "pomeriggio" else 16, minute=0, second=0).astimezone(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    gia = sb("GET", f"/rest/v1/clara_messaggi?select=id&tipo=eq.promemoria&at=gte.{da}&testo=like.Punto%20del%20{momento}*&limit=1")
    if gia:
        print("recap gia' scritto"); return
    sb("POST", "/rest/v1/clara_messaggi", {"tipo": "promemoria", "testo": testo})
    print("recap scritto:", testo[:60])


if __name__ == "__main__":
    main()
