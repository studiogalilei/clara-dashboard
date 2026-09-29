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
  --rinfresca   rilegge i testi con la pulizia di adesso (la nostra mail citata fuori)
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
    ci_sono = sb_tutte("/rest/v1/metro_risposte?select=interaction_id,prospect_id", chiave="interaction_id")
    gia = {r["interaction_id"] for r in ci_sono}
    classe = {p["id"]: p.get("classificazione") for p in sb_tutte("/rest/v1/prospects?select=id,classificazione&last_reply_at=not.is.null")}
    per_tipo = {}
    for r in sb_tutte("/rest/v1/interactions?select=id,prospect_id,at,body&kind=eq.email_in&order=at.desc"):
        if r["id"] in gia or r["prospect_id"] not in classe:
            continue
        # «Risposta ricevuta (Smartlead)» non e' una mail, e' l'import vecchio. Non lettura._segnaposto:
        # quello scarta anche i «Non mi interessa, grazie», che nel metro servono
        if (r.get("body") or "").strip().lower().startswith("risposta ricevuta"):
            continue
        t = " ".join(lettura.solo_suo(r.get("body") or "").split())
        if len(t) < 8:
            continue
        per_tipo.setdefault(classe[r["prospect_id"]] or "da_classificare", []).append({**r, "testo": t[:1500]})
    random.seed(29)
    # si riempie quello che manca: le quote contano anche le righe gia' nel metro
    gia_per_tipo = Counter(classe.get(r["prospect_id"]) or "da_classificare" for r in ci_sono)
    scelte, visti = [], {r["prospect_id"] for r in ci_sono}
    for tipo, quota in QUOTE.items():
        candidati = [r for r in per_tipo.get(tipo, []) if r["prospect_id"] not in visti]
        random.shuffle(candidati)
        for r in candidati[:max(quota - gia_per_tipo[tipo], 0)]:
            scelte.append(r); visti.add(r["prospect_id"])
    scelte = scelte[:max(n - len(ci_sono), 0)]
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


def rinfresca():
    """Rilegge i testi del metro con lettura.solo_suo di adesso (29/9: la nostra mail
    citata restava dentro a una risposta su sette). Dove il testo cambia si rilegge
    anche col modello; dove non resta niente di suo (ci ha solo girato la nostra
    mail) e non e' ancora etichettata, la riga esce: non e' una risposta."""
    import cervello
    import lettura
    righe = sb_tutte("/rest/v1/metro_risposte?select=interaction_id,testo,etichetta", chiave="interaction_id")
    corpi = {}
    for k in range(0, len(righe), 100):
        ids = ",".join(r["interaction_id"] for r in righe[k:k + 100])
        corpi.update({x["id"]: x.get("body") or "" for x in sb("GET", f"/rest/v1/interactions?select=id,body&id=in.({ids})")})
    cambiate, fuori = [], 0
    for r in righe:
        t = " ".join(lettura.solo_suo(corpi.get(r["interaction_id"], "")).split())[:1500]
        if t == r["testo"]:
            continue
        if len(t) < 8 and not r.get("etichetta"):
            if not PROVA:
                sb("DELETE", f"/rest/v1/metro_risposte?interaction_id=eq.{r['interaction_id']}&etichetta=is.null", None, {"Prefer": "return=minimal"})
            fuori += 1
            continue
        cambiate.append({**r, "nuovo": t})
    from concurrent.futures import ThreadPoolExecutor
    with ThreadPoolExecutor(max_workers=6) as pool:
        letture = list(pool.map(lambda r: cervello.classifica_risposta(r["nuovo"]), cambiate))
    for r, lett in zip(cambiate, letture):
        if not PROVA:
            sb("PATCH", f"/rest/v1/metro_risposte?interaction_id=eq.{r['interaction_id']}",
               {"testo": r["nuovo"], "proposta": lett}, {"Prefer": "return=minimal"})
    print(f"testi ripuliti: {len(cambiate)} (di cui gia' etichettati {sum(1 for r in cambiate if r.get('etichetta'))}), "
          f"usciti perche' senza niente di suo: {fuori}")


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
    righe = [r for r in sb_tutte("/rest/v1/metro_risposte?select=testo,proposta,etichetta,nota", chiave="interaction_id") if r.get("etichetta")]
    if not righe:
        print("nessuna etichetta ancora: il metro si riempie dalla pagina «Metro» del Workspace"); return
    print(f"IL METRO: {len(righe)} risposte etichettate da Dre {dict(Counter(r['etichetta'] for r in righe))}\n")
    for r in righe:      # se il giorno della preparazione la rete era giu', la lettura si fa adesso
        r["proposta"] = r.get("proposta") or cervello.classifica_risposta(r["testo"])
    for nome, chi in (("lettore unico (GPT, soglie asimmetriche)", lambda r: cervello.decisioni(r.get("proposta"))),
                      # quando nessuna regola scatta la mail va a una persona: e' un dubbio, non una decisione
                      ("regole di oggi (regex)", lambda r: {"etichetta": regex_di_oggi(r["testo"]), "dubbio": regex_di_oggi(r["testo"]) == "altro"})):
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
    # i commenti di Dre: il perche' che la mail non dice, il primo pezzo delle sue regole non scritte
    note = [r for r in righe if r.get("nota")]
    if note:
        print(f"  I COMMENTI DI DRE ({len(note)})")
        for r in note:
            print(f"    [{r['etichetta']}] «{r['testo'][:70]}»\n        {r['nota']}")


if __name__ == "__main__":
    if "--prepara" in sys.argv:
        prepara(int(sys.argv[sys.argv.index("--prepara") + 1]))
    elif "--misura" in sys.argv:
        misura()
    elif "--rinfresca" in sys.argv:
        rinfresca()
    else:
        print(__doc__)
