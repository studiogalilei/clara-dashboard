#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""LE LEZIONI — le correzioni di Dre diventano le regole di Clara (24/9/2026).

Dre, 24/9: accettata l'idea «le tue correzioni diventano le sue regole».
Da oggi ogni bozza approvata porta due versioni: quella di Clara
(azione.bozza_originale) e quella mandata (azione.bozza). Una volta a
settimana Clara legge le differenze, piu' i «Non cosi'» con il motivo, e
propone al massimo TRE regole, concrete, con l'esempio prima/dopo.
Non le scrive da sola: le propone in Posta. Sul si', il workspace le appende
alle istruzioni (chiave `bozze`), che bozze.py legge prima di ogni bozza.

USO
  python3 scripts/lezioni.py            propone (una volta a settimana)
  python3 scripts/lezioni.py --prova    mostra e non propone
"""
import datetime
import difflib
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from stanza import sb, proponi                              # noqa: E402
import cervello                                             # noqa: E402

PROMPT = """Sei Clara. Qui sotto ci sono le bozze di risposta che hai scritto tu e la versione
che Dre ha davvero mandato (o il motivo per cui l'ha scartata). Dre e' il capo e ha sempre
ragione sul tono: il tuo compito e' capire COSA cambia sempre, non giustificarti.

Scrivi al massimo TRE regole, solo se si ripetono o sono nette. Ogni regola:
- una riga, in imperativo, concreta («Non aprire con "Volentieri": apri con il nome»),
- seguita da un esempio prima → dopo preso dalle correzioni (breve).
Se non c'e' niente di netto, rispondi solo: NESSUNA.

LE CORREZIONI:
{correzioni}
"""


def differenze(a, b):
    """Le righe cambiate, compatte: - tolta / + messa."""
    out = []
    for r in difflib.unified_diff(a.splitlines(), b.splitlines(), lineterm="", n=0):
        if r.startswith(("---", "+++", "@@")):
            continue
        out.append(r[:160])
    return "\n".join(out[:30])


def main():
    prova = "--prova" in sys.argv
    settimana = datetime.date.today().isocalendar()
    marca = f"{settimana[0]}-{settimana[1]:02d}"
    gia = [pr for pr in (sb("GET", "/rest/v1/proposte?select=id,azione&tipo=eq.umano&order=at.desc&limit=50") or [])
           if (pr.get("azione") or {}).get("lezioni_settimana") == marca]
    if gia and not prova:
        print(f"lezioni: gia' proposte questa settimana ({marca})"); return
    da = (datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=7)).strftime("%Y-%m-%dT%H:%M:%SZ")
    righe = sb("GET", f"/rest/v1/proposte?select=id,titolo,stato,risposta,azione,prospect_id&tipo=in.(risposta,umano)&stato=in.(fatta,no)&at=gte.{da}&order=at") or []
    blocchi = []
    for pr in righe:
        az = pr.get("azione") or {}
        orig, fin = (az.get("bozza_originale") or "").strip(), (az.get("bozza") or "").strip()
        if pr["stato"] == "no" and (pr.get("risposta") or "").startswith("NO:"):
            blocchi.append(f"[{pr['titolo'][:50]}] SCARTATA, motivo di Dre: {pr['risposta'][3:].strip()[:200]}\n  la mia bozza: {fin[:300]}")
        elif orig and fin and orig != fin:
            blocchi.append(f"[{pr['titolo'][:50]}] CORRETTA:\n{differenze(orig, fin)}")
    if not blocchi:
        print("lezioni: nessuna correzione questa settimana"); return
    testo = (cervello._chiedi(PROMPT.format(correzioni="\n\n".join(blocchi)[:9000])) or "").strip()
    print(f"  {len(blocchi)} correzioni lette\n" + testo[:800])
    if testo.upper().startswith("NESSUNA") or not testo:
        return
    if prova:
        return
    proponi("umano", "Ho imparato dalle tue correzioni: le scrivo nelle mie regole?",
            perche=testo[:280],
            azione={"lezioni_settimana": marca, "istruzione": {"chiave": "bozze", "titolo": "Lezioni dalle correzioni di Dre",
                                                               "testo": f"({datetime.date.today():%d/%m/%Y})\n{testo}"}})
    print("lezioni: proposta in Posta")


if __name__ == "__main__":
    main()
