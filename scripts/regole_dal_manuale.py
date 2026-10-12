#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""LE REGOLE DAL MANUALE (12/10/2026).

Il documento 01 del Manuale di Clara («Le regole», nel vault) diventa la tabella `regole`
(schema_v80): una riga per regola, un valore, un posto. Dre corregge il documento; questo
script lo ricarica. Lo stato di ogni riga lo dice il testo: «DA CONFERMARE» = scelta di
Achille fra due versioni, «?» = manca una decisione di Dre, altrimenti bozza; quando Dre
cambia la prima riga del documento in «stato: APPROVATO», le righe senza segni diventano
approvate.

    python3 scripts/regole_dal_manuale.py --prova    mostra cosa caricherebbe
    python3 scripts/regole_dal_manuale.py            carica
"""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from stanza import sb                                       # noqa: E402

DOC = os.path.expanduser("~/Documents/Obsidian/studiogalilei/00 - Cervello Condiviso/"
                         "Il manuale di Clara (12-10-2026)/01 - Le regole.md")
PROVA = "--prova" in sys.argv


def pulisci(t):
    return re.sub(r"\*\*|`", "", t or "").strip()


def righe(testo):
    approvato = bool(re.search(r"stato:\s*APPROVATO", testo.split("\n", 3)[2] if testo.count("\n") > 2 else ""))
    sezione, out = None, []
    for r in testo.splitlines():
        m = re.match(r"^## ([A-Z])\. (.+)", r)
        if m:
            sezione = f"{m.group(1)}. {m.group(2).strip()}"
            continue
        if not sezione or not r.startswith("|") or re.match(r"^\|\s*-", r):
            continue
        celle = [c.strip() for c in r.strip().strip("|").split("|")]
        if len(celle) < 2 or celle[0] in ("chiave", "domanda"):
            continue
        chiave, valore = pulisci(celle[0]), pulisci(celle[1])
        perche = pulisci(" | ".join(celle[2:]))
        if not re.fullmatch(r"[a-z0-9_]+", chiave):
            # la tabella del lettore (sezione F) ha la domanda come chiave: si fa una chiave
            chiave = "lettore_" + re.sub(r"[^a-z]+", "_", chiave.lower()).strip("_")
        tutto = valore + " " + perche
        if re.search(r"(^|\s)\?(\s|$)", valore) or valore.startswith("?"):
            stato = "da_decidere"
        elif "DA CONFERMARE" in tutto:
            stato = "da_confermare"
        else:
            stato = "approvata" if approvato else "bozza"
        out.append({"chiave": chiave, "sezione": sezione, "valore": valore, "perche": perche or None, "stato": stato,
                    "aggiornata_da": "regole_dal_manuale.py"})
    return out


def main():
    rr = righe(open(DOC, encoding="utf-8").read())
    doppie = {r["chiave"] for r in rr if sum(1 for x in rr if x["chiave"] == r["chiave"]) > 1}
    if doppie:
        sys.exit(f"chiavi doppie nel documento: {sorted(doppie)}")
    conta = {}
    for r in rr:
        conta[r["stato"]] = conta.get(r["stato"], 0) + 1
    print(f"{len(rr)} regole dal documento 01: {conta}")
    if PROVA:
        for r in rr[:8]:
            print(f"  {r['sezione'][:2]} {r['chiave']:28} [{r['stato']}] {r['valore'][:70]}")
        return
    sb("POST", "/rest/v1/regole?on_conflict=chiave", rr, {"Prefer": "resolution=merge-duplicates,return=minimal"})
    via = {x["chiave"] for x in (sb("GET", "/rest/v1/regole?select=chiave") or [])} - {r["chiave"] for r in rr}
    for k in via:
        sb("DELETE", f"/rest/v1/regole?chiave=eq.{k}")
    print(f"caricate; tolte {len(via)} che nel documento non ci sono piu'")


if __name__ == "__main__":
    main()
