#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""L'ESAME DELLE PRIME RISPOSTE SCRITTE DA DRE (2/10/2026).

Parole sue: «dammi dei metri con esempi di tipo 50 prime risposte: io prendo e
scrivo TESTUALMENTE cosa risponderei, per diversi casi che abbiamo gia'
incontrato. Poi per ognuno cerchi di capire perche' ho risposto in quel modo,
che leve sto usando: cosi' per ogni caso e' come se avessimo un template, e
l'AI ci ragiona e lavora di coerenza, senza troppa immaginazione, che e'
quella che rovina. Sistemi semplici».

Quindi: 50 prime risposte VERE di lead, scelte per coprire casi diversi (si',
chi siete, no gentile, rinvio, ferie, equity, persona sbagliata, stufo...).
Nella pagina «Metro» Dre vede la loro mail e SCRIVE la risposta nel campo del
commento, parola per parola, poi preme «Ho scritto la risposta». Niente
etichette: il testo suo E' la risposta. Le leve e i perche' li estraggo io
dopo, caso per caso, e diventano la biblioteca su cui il sistema lavora di
coerenza.

USO
  python3 scripts/esame_prime.py --prepara 50 [--prova]
"""
import os
import random
import sys
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from stanza import sb, sb_tutte                            # noqa: E402

PROVA = "--prova" in sys.argv
TEMA = "prime_risposte"
DOMANDA = "Scrivi nel riquadro, parola per parola, la risposta che manderesti"
SCELTE = [["scritta", "Ho scritto la risposta"]]
# i casi da coprire, pescati con l'etichetta che Dre ha gia' dato nel metro delle
# risposte: cosi' l'esame copre i modi diversi, non 50 varianti dello stesso si'
QUOTE = {"si": 14, "no": 12, "altro": 12, "rinvio": 6, "fuori_ufficio": 4, "non_scrivere": 2}


def prepara(n):
    gia = {r["riferimento"] for r in sb_tutte(f"/rest/v1/metro_casi?select=riferimento&tema=eq.{TEMA}", chiave="id")}
    etichettate = [r for r in sb_tutte("/rest/v1/metro_risposte?select=interaction_id,prospect_id,testo,etichetta",
                                       chiave="interaction_id") if r.get("etichetta")]
    random.seed(2)
    random.shuffle(etichettate)
    per_classe = Counter()
    fatti = 0
    for r in etichettate:
        e = r["etichetta"]
        if fatti >= n or per_classe[e] >= QUOTE.get(e, 0) or r["interaction_id"] in gia:
            continue
        p = (sb("GET", f"/rest/v1/prospects?select=company,name,sector,city&id=eq.{r['prospect_id']}") or [{}])[0]
        nome = p.get("company") or p.get("name") or "?"
        dove = ", ".join(x for x in (p.get("sector"), p.get("city")) if x)
        if PROVA:
            print(f"  [{e:13}] {str(nome)[:34]:34} {r['testo'][:60]}")
        else:
            sb("POST", "/rest/v1/metro_casi?on_conflict=tema,riferimento",
               {"tema": TEMA, "prospect_id": r["prospect_id"], "riferimento": r["interaction_id"],
                "domanda": DOMANDA,
                "mostra": [{"eti": "Azienda", "testo": f"{nome}" + (f" ({dove})" if dove else "")},
                           {"eti": "La loro mail", "testo": r["testo"][:900]}],
                "scelte": SCELTE,
                "proposta": {"etichetta_metro": e}},
               {"Prefer": "resolution=ignore-duplicates,return=minimal"})
        per_classe[e] += 1
        fatti += 1
    print(f"esame delle prime risposte: {fatti} casi pronti {dict(per_classe)}" + (" (prova)" if PROVA else ""))


if __name__ == "__main__":
    if "--prepara" in sys.argv:
        prepara(int(sys.argv[sys.argv.index("--prepara") + 1]))
    else:
        print(__doc__)
