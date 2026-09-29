#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""IL METRO DELLE RISPOSTE (Dre, 29/9/2026: strada A del lettore unico).

PERCHE'
Per decidere se il lettore unico (cervello.classifica_risposta) puo' prendere il
posto delle quattro regex serve un metro: mail vere, ognuna etichettata da Dre
per quello che dice LEI, non per com'e' l'azienda oggi. Il 29/9 le 435
classificazioni a mano si sono rivelate un metro sbagliato per questo: descrivono
l'azienda dopo tutta la storia.

COSA FA
  --prepara N   sceglie N risposte vere (una per azienda, di ogni tipo, anche le rare)
                e le mette in metro_risposte con la lettura del modello accanto;
                Dre le etichetta nella pagina «Metro» del Workspace, senza vederla.
  --misura      confronta con le etichette di Dre: il lettore nuovo e le regole di oggi.
                I numeri che contano (criterio del 28/9): quanti sì presi per no, quanti
                no presi per sì, quanti «non scrivetemi» mancati; poi quanto decide da solo.

USO
  python3 scripts/metro.py --prepara 150
  python3 scripts/metro.py --misura
"""
import os
import random
import sys
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from stanza import sb, sb_tutte                            # noqa: E402

PROVA = "--prova" in sys.argv
# quante per tipo (la classificazione di oggi serve solo a pescarne di ogni genere)
QUOTE = {"negativo": 35, "positivo": 25, "tiepido": 5, "ooo": 20, "rinvio": 20, "soppresso": 20,
         "persona_sbagliata": 5, "da_classificare": 10, "nervoso": 2, "fuori_target": 8}


def prepara(n):
    import cervello
    import lettura
    gia = {r["interaction_id"] for r in sb_tutte("/rest/v1/metro_risposte?select=interaction_id", chiave="interaction_id")}
    classe = {p["id"]: p.get("classificazione") for p in sb_tutte("/rest/v1/prospects?select=id,classificazione&last_reply_at=not.is.null")}
    per_tipo = {}
    for r in sb_tutte("/rest/v1/interactions?select=id,prospect_id,at,body&kind=eq.email_in&order=at.desc"):
        if r["id"] in gia or r["prospect_id"] not in classe:
            continue
        t = " ".join(lettura.solo_suo(r.get("body") or "").split())
        if len(t) < 8:
            continue
        per_tipo.setdefault(classe[r["prospect_id"]] or "da_classificare", []).append({**r, "testo": t[:1500]})
    random.seed(29)
    scelte, visti = [], set()
    for tipo, quota in QUOTE.items():
        candidati = [r for r in per_tipo.get(tipo, []) if r["prospect_id"] not in visti]
        random.shuffle(candidati)
        for r in candidati[:quota]:
            scelte.append(r); visti.add(r["prospect_id"])
    scelte = scelte[:n]
    print(f"il metro: {len(scelte)} risposte scelte ({dict(Counter(classe[r['prospect_id']] for r in scelte))})")
    # sei letture alla volta: una sola ci mette una ventina di secondi
    from concurrent.futures import ThreadPoolExecutor
    with ThreadPoolExecutor(max_workers=6) as pool:
        letture = list(pool.map(lambda r: cervello.classifica_risposta(r["testo"]), scelte))
    print(f"lette: {sum(x is not None for x in letture)} di {len(scelte)}")
    fatte = 0
    for r, lett in zip(scelte, letture):
        if PROVA:
            continue
        sb("POST", "/rest/v1/metro_risposte?on_conflict=interaction_id",
           {"interaction_id": r["id"], "prospect_id": r["prospect_id"], "testo": r["testo"], "proposta": lett},
           {"Prefer": "resolution=ignore-duplicates,return=minimal"})
        fatte += 1
    print(f"messe nel metro: {fatte}")


def regex_di_oggi(t):
    """Come le quattro regole di oggi etichetterebbero la mail."""
    import lettura
    import analisi_auto as A
    if A.NON_TOCCARE.search(t):
        return "non_scrivere"
    if lettura.AUTORISPOSTA.search(t[:1200]):
        return "fuori_ufficio"
    if lettura.DETTO_NO.search(t):
        return "no"
    if A.CHIEDE_ANALISI.search(t):
        return "si"
    return "altro"


def misura():
    import cervello
    righe = [r for r in sb_tutte("/rest/v1/metro_risposte?select=testo,proposta,etichetta", chiave="interaction_id") if r.get("etichetta")]
    if not righe:
        print("nessuna etichetta ancora: il metro si riempie dalla pagina «Metro» del Workspace"); return
    print(f"IL METRO: {len(righe)} risposte etichettate da Dre {dict(Counter(r['etichetta'] for r in righe))}\n")
    for r in righe:      # se il giorno della preparazione la rete era giu', la lettura si fa adesso
        r["proposta"] = r.get("proposta") or cervello.classifica_risposta(r["testo"])
    for nome, chi in (("lettore unico (GPT, soglie asimmetriche)", lambda r: cervello.decisioni(r.get("proposta"))),
                      ("regole di oggi (regex)", lambda r: {"etichetta": regex_di_oggi(r["testo"]), "dubbio": False})):
        giusti = si_per_no = no_per_si = ns_mancati = decide = decide_giusti = 0
        for r in righe:
            d = chi(r); vero, dato = r["etichetta"], d["etichetta"]
            giusti += vero == dato
            si_per_no += vero == "si" and dato in ("no", "non_scrivere")
            no_per_si += vero in ("no", "non_scrivere") and dato == "si"
            ns_mancati += vero == "non_scrivere" and dato != "non_scrivere"
            if not d.get("dubbio"):
                decide += 1; decide_giusti += vero == dato
        n = len(righe)
        tot = Counter(r["etichetta"] for r in righe)
        print(f"  {nome}\n    giuste {giusti}/{n} ({giusti/n:.0%})"
              f"  | sì presi per no {si_per_no}/{tot['si']}  | no presi per sì {no_per_si}/{tot['no'] + tot['non_scrivere']}"
              f"  | «non scrivetemi» mancati {ns_mancati}/{tot['non_scrivere']}"
              f"\n    decide da solo {decide}/{n}, e quando decide ha ragione {decide_giusti}/{decide or 1} ({decide_giusti/(decide or 1):.0%})\n")


if __name__ == "__main__":
    if "--prepara" in sys.argv:
        prepara(int(sys.argv[sys.argv.index("--prepara") + 1]))
    elif "--misura" in sys.argv:
        misura()
    else:
        print(__doc__)
