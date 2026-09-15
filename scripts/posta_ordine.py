#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""LA POSTA IN ORDINE (15/9/2026): le domande vecchie si chiudono da sole.

PERCHE'
Sui dati veri la Posta di Clara ha 224 domande aperte e 219 sono li' da piu'
di tre giorni: 108 classificazioni, 63 bozze, 28 dalle call. Una posta cosi'
non si legge piu', e allora non si legge piu' niente, comprese le tre cose
che contavano davvero. La regola di Dre e' «poche alla volta».

COSA FA
Chiude le domande a basso rischio rimaste senza risposta troppo a lungo, e
le chiude SENZA applicarle: quello che proponevano non succede, le cose
restano come sono. Se serviranno di nuovo, Clara le rifara' quando rivede
quell'azienda. Non tocca mai le richieste di accesso, le cose da guardare a
mano e le proposte nate da una call: quelle le decide una persona.

Alla fine lo dice in chat, una riga, cosi' nessuno scopre la Posta vuota
senza sapere perche'.

USO
  python3 scripts/posta_ordine.py            chiude
  python3 scripts/posta_ordine.py --prova    dice cosa chiuderebbe
"""

import datetime
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from stanza import sb, di_clara                            # noqa: E402

# quanto puo' restare aperta una domanda, per tipo. Le bozze durano di piu':
# una risposta scritta due settimane fa si puo' ancora mandare, una
# classificazione di due settimane fa l'ha gia' decisa il tempo.
GIORNI = {"classifica": 7, "data": 7, "scarta": 10, "risposta": 21, "tornato": 21}
NOME = {"classifica": "classificazioni", "data": "domande su una data", "scarta": "scarti",
        "risposta": "bozze", "tornato": "rientri"}


def quando_di(iso):
    """Le date del database hanno i microsecondi a cinque cifre e Python 3.9
    non le legge: si taglia la virgola, l'ora basta."""
    import re
    t = re.sub(r"\.\d+", "", (iso or "").replace("Z", "+00:00"))
    return datetime.datetime.fromisoformat(t)


def main():
    prova = "--prova" in sys.argv
    adesso = datetime.datetime.now(datetime.timezone.utc)
    aperte = sb("GET", "/rest/v1/proposte?select=id,tipo,at,titolo&stato=eq.aperta&limit=2000") or []
    da_chiudere = {}
    for p in aperte:
        limite = GIORNI.get(p["tipo"])
        if not limite:
            continue
        quando = quando_di(p["at"])
        if (adesso - quando).days < limite:
            continue
        da_chiudere.setdefault(p["tipo"], []).append(p)

    quante = sum(len(v) for v in da_chiudere.values())
    if not quante:
        print(f"posta: {len(aperte)} aperte, nessuna da chiudere")
        return

    pezzi = [f"{len(v)} {NOME.get(k, k)}" for k, v in sorted(da_chiudere.items(), key=lambda x: -len(x[1]))]
    print(f"posta: {len(aperte)} aperte, chiudo {quante} ({', '.join(pezzi)})")
    if prova:
        for k, v in da_chiudere.items():
            for p in v[:3]:
                print(f"  {k}: {p['titolo'][:70]}")
        return

    for k, v in da_chiudere.items():
        for i in range(0, len(v), 50):
            ids = ",".join(str(p["id"]) for p in v[i:i + 50])
            sb("PATCH", f"/rest/v1/proposte?id=in.({ids})",
               {"stato": "no", "risposta_il": adesso.isoformat()})

    di_clara("controllo",
             f"Ho chiuso {quante} domande rimaste senza risposta: {', '.join(pezzi)}. "
             f"Non ho toccato niente, restano tutte come sono. Se servono ancora, "
             f"te le richiedo quando rivedo quell'azienda.")
    print("fatto")


if __name__ == "__main__":
    main()
