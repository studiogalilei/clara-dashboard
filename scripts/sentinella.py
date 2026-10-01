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
"""
import datetime
import os
import sys
import urllib.parse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from stanza import sb, di_clara                            # noqa: E402

ADESSO = datetime.datetime.now(datetime.timezone.utc)


def _min_fa(iso):
    try:
        t = datetime.datetime.fromisoformat(str(iso).replace("Z", "+00:00"))
        if not t.tzinfo:
            t = t.replace(tzinfo=datetime.timezone.utc)
        return (ADESSO - t).total_seconds() / 60
    except Exception:                                      # noqa: BLE001
        return None


def main():
    guai = []

    ops = sb("GET", "/rest/v1/operazioni?select=chiave,ultima_corsa,ultimo_esito&attiva=eq.true") or []
    fresche = [m for m in (_min_fa(o.get("ultima_corsa")) for o in ops) if m is not None]
    if fresche and min(fresche) > 20:
        guai.append(f"il direttore e' fermo: nessuna operazione da {int(min(fresche))} minuti")
    for o in ops:
        if o.get("ultimo_esito") == "errore":
            guai.append(f"operazione «{o['chiave']}» in errore")

    da = urllib.parse.quote((ADESSO - datetime.timedelta(hours=24)).isoformat())
    attese = sb("GET", "/rest/v1/prospects?select=id,company,name,email,last_reply_at"
                       f"&awaiting_us=eq.true&fuori=eq.false&last_reply_at=gte.{da}"
                       "&or=(classificazione.is.null,classificazione.not.in.(negativo,fuori_target,soppresso,nervoso))"
                       "&order=last_reply_at.asc&limit=50") or []
    con_proposta = {x["prospect_id"] for x in sb("GET", "/rest/v1/proposte?select=prospect_id&stato=in.(aperta,approvata,in_invio)&limit=1000") or []}
    for p in attese:
        m = _min_fa(p["last_reply_at"])
        if m and m > 45 and p["id"] not in con_proposta:
            nome = p.get("company") or p.get("name") or p["email"]
            guai.append(f"{nome}: ha scritto {int(m)} minuti fa e non c'e' ancora niente (ne' bozza, ne' freno)")

    ferme = sb("GET", "/rest/v1/proposte?select=id,titolo,stato,risposta_il,at&stato=in.(approvata,in_invio)&limit=50") or []
    for x in ferme:
        m = _min_fa(x.get("risposta_il") or x.get("at"))
        if m and m > 30:
            guai.append(f"proposta «{x['titolo'][:50]}» {x['stato']} da {int(m)} minuti e il postino non la prende")

    if not guai:
        print(f"sentinella: tutto opera ({len(ops)} operazioni, {len(attese)} attese fresche seguite)")
        return
    print(f"sentinella: {len(guai)} guai")
    for g in guai[:10]:
        print("  !", g)
    try:
        di_clara("controllo", "SENTINELLA, qualcosa non opera:\n- " + "\n- ".join(guai[:8]), letto=False)
    except Exception as e:                                 # noqa: BLE001
        print("  (avviso non scritto:", str(e)[:60] + ")")
    sys.exit(1)        # il workflow della sentinella diventa rosso: si vede anche da GitHub


if __name__ == "__main__":
    main()
