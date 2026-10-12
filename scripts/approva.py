#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""APPROVA: Dre approva in chat, Achille segna (12/10/2026).

Dre, 12/10 sera: «vorrei che tu semplicemente rispondessi a tutti questi». Le mail le
manda il postino in cloud (manda.py) quando una bozza e' «approvata»; questo comando fa
SOLO quel passo, per le bozze che Dre ha approvato in chat, una per una, con il loro id.
Non scrive testi e non manda niente da solo: segna, e sveglia il postino.

Per ogni id:
  - la bozza dev'essere ancora «aperta» (se e' cambiata o chiusa, non si tocca);
  - ripassa dal cancello (bozze.cancello) e dal controllo del postino (manda.controlla):
    se non passa, resta aperta e si dice perche';
  - la persona dev'essere contattabile (stanza.contattabile);
  - si scrive chi ha approvato e quando (azione.approvata_da / approvata_il).

    python3 scripts/approva.py --prova ID [ID ...]   mostra cosa farebbe
    python3 scripts/approva.py ID [ID ...]            approva e sveglia il postino
    python3 scripts/approva.py --lista FILE           gli id da un file
"""
import datetime
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from stanza import sb, contattabile                          # noqa: E402

PROVA = "--prova" in sys.argv
CHI = "Dre (approvata in chat con Achille, una per una)"


def main():
    args = sys.argv[1:]
    if "--lista" in args:
        # un file con gli id, uno dopo l'altro (separati da spazi o a capo)
        f = args[args.index("--lista") + 1]
        args = [a for a in args if a not in ("--lista", f)] + open(f).read().split()
    ids = [a for a in args if not a.startswith("--")]
    if not ids:
        sys.exit(__doc__)
    import bozze
    import manda
    fatte, ferme = [], []
    for pid in ids:
        pr = (sb("GET", f"/rest/v1/proposte?select=id,stato,tipo,titolo,prospect_id,azione&id=eq.{pid}") or [None])[0]
        if not pr:
            ferme.append((pid, "non esiste")); continue
        if pr["stato"] != "aperta":
            ferme.append((pr["titolo"][:40], f"non e' aperta ({pr['stato']})")); continue
        az = dict(pr.get("azione") or {})
        testo = (az.get("bozza") or "").strip()
        p = (sb("GET", f"/rest/v1/prospects?select=*&id=eq.{pr['prospect_id']}") or [None])[0] if pr.get("prospect_id") else None
        if not p or not testo:
            ferme.append((pr["titolo"][:40], "manca la scheda o il testo")); continue
        if not contattabile(p):
            ferme.append((p.get("company") or pr["titolo"][:40], "non contattabile (pipeline, cliente, perso, soppresso o niente follow-up)")); continue
        errori = manda.controlla(testo, p, gruppo=az.get("gruppo") or az.get("template")) or []
        if errori:
            ferme.append((p.get("company") or pr["titolo"][:40], "; ".join(errori)[:160])); continue
        if PROVA:
            fatte.append(p.get("company") or pr["titolo"][:40]); continue
        az["approvata_da"] = CHI
        az["approvata_il"] = datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")
        r = sb("PATCH", f"/rest/v1/proposte?id=eq.{pr['id']}&stato=eq.aperta",
               {"stato": "approvata", "azione": az}, {"Prefer": "return=representation"})
        if r:
            fatte.append(p.get("company") or pr["titolo"][:40])
        else:
            ferme.append((p.get("company") or pr["titolo"][:40], "cambiata mentre la approvavo: non toccata"))
    print(f"{'(prova) ' if PROVA else ''}approvate {len(fatte)}: {', '.join(fatte)}")
    for n, m in ferme:
        print(f"  ferma {n}: {m}")
    if fatte and not PROVA:
        try:
            sb("POST", "/rest/v1/rpc/chiama_direttore", {"forza": "manda"})
            print("postino svegliato: le mail partono entro pochi minuti")
        except Exception as e:                                # noqa: BLE001
            print(f"postino non svegliato ({str(e)[:60]}): parte al prossimo giro del direttore")


if __name__ == "__main__":
    main()
