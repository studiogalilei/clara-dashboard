#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""IL TRACCIATO — il calendario dice dov'e' arrivato un lead; Clara lo propone (7/9/2026).

PERCHE'
Dre: «Zafferano l'ho gia' sentito ed e' quasi cliente ormai». Nel CRM era
ancora un prospect «risposto», fuori dalla pipeline: il calendario invece
aveva la chiamata dell'11/8, la call tecnica del 13/8 e la call di avvio del
25/8. La verita' era in agenda, la bacheca era indietro.

COSA FA
Per ogni prospect con call passate in `agenda`, guarda la fase piu' avanti
raggiunta (conoscitiva < tecnica < avvio) e la confronta con la bacheca. Se
la bacheca e' indietro, mette una proposta nella stanza: «Dal calendario
risulta la call di avvio del 25/8: lo metto in pipeline in Avvio?». Dre dice
si' e il prospect entra o avanza; dice no e non se ne parla piu' (la proposta
chiusa non si ripropone). Non scrive niente da sola: Clara propone, Dre dispone.

USO
  python3 scripts/tracciato.py            propone
  python3 scripts/tracciato.py --prova    mostra e basta
"""

import datetime
import os
import sys
import zoneinfo

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from stanza import sb, proponi                             # noqa: E402

ROMA = zoneinfo.ZoneInfo("Europe/Rome")
ORDINE = {"conoscitiva": 1, "tecnica": 2, "avvio": 3}
NOME = {"conoscitiva": "Conoscitiva", "tecnica": "Call tecnica", "avvio": "Avvio"}


def main():
    prova = "--prova" in sys.argv
    adesso = datetime.datetime.now(datetime.timezone.utc)
    agenda = sb("GET", f"/rest/v1/agenda?select=at,titolo,tipo,prospect_id&prospect_id=not.is.null"
                       f"&at=lte.{adesso.strftime('%Y-%m-%dT%H:%M:%SZ')}&tipo=in.(conoscitiva,tecnica,avvio)&order=at.asc&limit=5000") or []
    per_prospect = {}
    for a in agenda:
        per_prospect.setdefault(a["prospect_id"], []).append(a)
    if not per_prospect:
        print("tracciato: nessuna call passata con prospect")
        return
    ids = ",".join(per_prospect)
    prospects = {p["id"]: p for p in (sb("GET", f"/rest/v1/prospects?select=id,name,company,fuori,pipeline_stage,stage&id=in.({ids})") or [])}
    # le proposte gia' fatte (aperte o chiuse): un no di Dre vale
    fatte = {(p["prospect_id"], (p.get("azione") or {}).get("prospects", {}).get("pipeline_stage"))
             for p in (sb("GET", "/rest/v1/proposte?select=prospect_id,azione&tipo=eq.avanza&limit=5000") or [])}

    proposte = 0
    for pid, calls in per_prospect.items():
        p = prospects.get(pid)
        if not p or p.get("pipeline_stage") in ("cliente", "perso") or p.get("stage") == "perso":
            continue
        ultima = max(calls, key=lambda a: ORDINE[a["tipo"]])
        fase = ultima["tipo"]
        attuale = p.get("pipeline_stage") if p.get("fuori") else None
        if attuale and ORDINE.get(attuale, 0) >= ORDINE[fase]:
            continue
        if (pid, fase) in fatte:
            continue
        nome = p.get("company") or p.get("name") or "?"
        quando = datetime.datetime.fromisoformat(ultima["at"].replace("Z", "+00:00")).astimezone(ROMA)
        tappe = "; ".join(f"{datetime.datetime.fromisoformat(a['at'].replace('Z', '+00:00')).astimezone(ROMA):%d/%m} {a['titolo'][:50]}" for a in calls)
        if attuale:
            titolo = f"{nome}: dal calendario risulta «{ultima['titolo'][:60]}» del {quando:%d/%m}. Lo porto in {NOME[fase]}?"
            azione = {"prospects": {"pipeline_stage": fase}}
        else:
            titolo = f"{nome}: dal calendario risulta «{ultima['titolo'][:60]}» del {quando:%d/%m}. Lo metto in pipeline, in {NOME[fase]}?"
            azione = {"prospects": {"fuori": True, "fuori_at": adesso.isoformat(), "pipeline_stage": fase, "awaiting_us": False}}
        perche = f"Call in calendario: {tappe}"[:280]
        if prova:
            print(f"  {titolo}\n      {perche}")
        else:
            if proponi("avanza", titolo, prospect_id=pid, perche=perche, azione=azione):
                proposte += 1
    print(f"tracciato: {proposte} proposte, {len(per_prospect)} prospect con call")


if __name__ == "__main__":
    main()
