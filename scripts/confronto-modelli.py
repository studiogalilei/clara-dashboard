#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""IL CONFRONTO — quale modello legge meglio le risposte vere di Dre (7/9/2026).

Si sceglie coi numeri, non a opinione. Le stesse risposte vere le leggono piu'
modelli; il verdetto di riferimento e' quello gia' visto e approvato da Dre
(la cache delle letture fatte da Claude il 7/9). Si stampano i disaccordi,
cosi' Dre li giudica uno per uno, e i token consumati, cosi' il costo e'
misurato e non temuto.

Uso:  python3 scripts/confronto-modelli.py                 (36 risposte)
      python3 scripts/confronto-modelli.py --quanti 80
      python3 scripts/confronto-modelli.py --modelli gpt-5-mini,gpt-5
Serve OPENAI_API_KEY in .env.local.
"""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cervello                                            # noqa: E402
from stanza import sb                                      # noqa: E402

QUANTI = int(sys.argv[sys.argv.index("--quanti") + 1]) if "--quanti" in sys.argv else 36
MODELLI = (sys.argv[sys.argv.index("--modelli") + 1].split(",") if "--modelli" in sys.argv
           else ["gpt-5-mini", "gpt-5"])
# prezzi indicativi per milione di token (ingresso, uscita): si aggiornano a mano
PREZZO = {"gpt-5-mini": (0.25, 2.0), "gpt-5": (1.25, 10.0), "gpt-5-nano": (0.05, 0.4)}


def riferimento():
    """I verdetti gia' dati da Claude e visti da Dre, per testo."""
    try:
        cache = json.load(open(cervello.CACHE, encoding="utf-8"))
    except Exception:
        return {}
    return cache


def main():
    if cervello.FORNITORE != "openai":
        sys.exit("metti FORNITORE=openai e OPENAI_API_KEY in .env.local")
    persone = sb("GET", "/rest/v1/prospects?last_reply_at=not.is.null&select=id,company,name,email,classificazione"
                        "&order=last_reply_at.desc&limit=400") or []
    righe = sb("GET", "/rest/v1/interactions?kind=eq.email_in&select=prospect_id,body&order=at.desc&limit=3000") or []
    ultima = {}
    for r in righe:
        if r.get("prospect_id") and r["prospect_id"] not in ultima and len((r.get("body") or "").strip()) > 60:
            ultima[r["prospect_id"]] = r["body"]
    campione = [{"id": p["id"], "testo": ultima[p["id"]], "nome": (p.get("company") or p.get("name") or "")[:30]}
                for p in persone if p["id"] in ultima][:QUANTI]
    print(f"{len(campione)} risposte vere, {len(MODELLI)} modelli: {', '.join(MODELLI)}\n")

    rif = riferimento()
    esiti = {}
    for m in MODELLI:
        prima = json.load(open(cervello.USO)) if os.path.exists(cervello.USO) else {}
        esiti[m] = cervello.leggi(campione, modello=m)
        dopo = json.load(open(cervello.USO)) if os.path.exists(cervello.USO) else {}
        u0, u1 = prima.get(m, {"dentro": 0, "fuori": 0}), dopo.get(m, {"dentro": 0, "fuori": 0})
        dentro, fuori = u1["dentro"] - u0["dentro"], u1["fuori"] - u0["fuori"]
        pin, pout = PREZZO.get(m, (0, 0))
        costo = dentro / 1e6 * pin + fuori / 1e6 * pout
        print(f"  {m:12} letti {len(esiti[m])}/{len(campione)} · token {dentro}+{fuori} · costo {costo:.4f} $")

    print("\nDOVE NON SONO D'ACCORDO (riferimento = la lettura approvata il 7/9):\n")
    testa = f"  {'chi':30} {'riferimento':16}" + "".join(f"{m:16}" for m in MODELLI)
    print(testa)
    disaccordi = {m: 0 for m in MODELLI}
    for c in campione:
        # il riferimento e' nella cache di stamattina, salvata prima che la
        # chiave della cache portasse il nome del modello: si provano tutte e due
        import hashlib
        vecchia = hashlib.sha256((cervello.REGOLE + "\x00" + " ".join(c["testo"].split())).encode("utf-8")).hexdigest()[:24]
        r = (rif.get(vecchia) or rif.get(cervello._impronta(c["testo"], "claude-sonnet-5")) or {}).get("classe", "?")
        verdetti = [esiti[m].get(c["id"], {}).get("classe", "-") for m in MODELLI]
        if any(v != r for v in verdetti):
            for m, v in zip(MODELLI, verdetti):
                if v != r:
                    disaccordi[m] += 1
            print(f"  {c['nome']:30} {r:16}" + "".join(f"{v:16}" for v in verdetti))
    print()
    for m in MODELLI:
        print(f"  {m:12} in disaccordo col riferimento su {disaccordi[m]} / {len(campione)}")
    print("\nIl riferimento non e' la verita': e' Claude. Dove un modello dissente, giudica Dre.")


if __name__ == "__main__":
    main()
