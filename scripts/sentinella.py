#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""LA SENTINELLA (Dre, 1/10/2026: «un agente che sta la' e monitora che tutto
operi bene, e se le cose non operano bene si comprende l'errore e si migliora»).

Il guasto che l'ha fatta nascere: il 1/10 un giro delle bozze oltre i 40 minuti
ha tenuto fermo il direttore per DUE ORE, e nessuno urlava (regola 4 del 28/9:
se una cosa e' ferma, deve avvisare). La sentinella gira in un workflow SUO,
separato dal direttore: cosi' lo sorveglia da fuori, e quando lui muore lei
e' ancora viva per dirlo.

Controlla, e per ogni guaio scrive un avviso nella chat di Clara (tipo
«controllo», cosi' si vede in Posta) e lo stampa nel log:
  1. il direttore fermo: nessuna operazione corsa da piu' di 20 minuti;
  2. una risposta fresca senza esito: ha scritto da piu' di 45 minuti e non
     c'e' ne' una mail nostra dopo, ne' una proposta, ne' un freno scritto;
  3. proposte approvate o in_invio ferme da piu' di 30 minuti;
  4. operazioni in errore.
Il risanamento del direttore bloccato (cancellare la corsa ferma) lo fa il
workflow con gh, non questo script: la sentinella vede e dice, non opera.

20/10 («io più il sistema»): il collaudo del 19/10 ha visto che la sentinella falliva senza
arrivare a Dre (scriveva in Posta, che Dre non apre piu'). Ora, se il direttore e' fermo, chiama
gli avvisi di guasto (scripts/guasti.py): la notifica sul telefono parte da qui, perche' quando
il direttore e' morto l'operazione «guasti» non gira. Gli altri guasti li suona «guasti».
"""
import datetime
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from stanza import sb                                      # noqa: E402

ADESSO = datetime.datetime.now(datetime.timezone.utc)


def _min_fa(iso):
    try:
        t = datetime.datetime.fromisoformat(str(iso).replace("Z", "+00:00"))
        if not t.tzinfo:
            t = t.replace(tzinfo=datetime.timezone.utc)
        return (ADESSO - t).total_seconds() / 60
    except Exception:                                      # noqa: BLE001
        return None


def avvisa_se_fermo():
    """Il direttore fermo: la notifica la manda la sentinella (stesse regole e stesso stato degli
    avvisi: una volta, poi ogni 2 ore, poi «Risolto», che arriva dal primo giro del direttore)."""
    import guasti
    import clara_foglio
    if any(g["chiave"] == "direttore" for g in clara_foglio.semaforo(ADESSO)):
        guasti.giro(ora=ADESSO)


def main():
    """Notte del 22/10: la sentinella fa UNA cosa, quella che solo lei puo' fare (guardare il direttore
    da fuori). Prima giudicava anche i lead con regole sue («ha scritto da 45 minuti e non c'e' una
    bozza»): dal 20/10 le conversazioni non hanno bozze per scelta, e dal 19/10 la sentinella era rossa
    quasi a ogni giro su lead gia' in mano a Dre, in una chat che nessuno legge. Il resto lo giudica
    il semaforo della scheda Clara, una volta sola."""
    ops = sb("GET", "/rest/v1/operazioni?select=chiave,ultima_corsa&attiva=eq.true") or []
    fresche = [m for m in (_min_fa(o.get("ultima_corsa")) for o in ops) if m is not None]
    fermo = bool(fresche) and min(fresche) > 20
    try:
        avvisa_se_fermo()
    except Exception as e:                                 # noqa: BLE001
        print("  (avviso di guasto non partito:", str(e)[:100] + ")")
    if not fermo:
        print(f"sentinella: il direttore gira ({len(ops)} operazioni accese)")
        return
    print(f"sentinella: il direttore e' fermo, nessuna operazione da {int(min(fresche))} minuti")
    sys.exit(1)        # il workflow della sentinella diventa rosso: si vede anche da GitHub


if __name__ == "__main__":
    main()
