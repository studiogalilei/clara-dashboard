#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""IL BANCO DI PROVA DEI MODELLI — chi legge meglio, e quanto costa (8/10/2026).

Erede di archivio/confronto-modelli.py (7/9), che provava solo OpenAI. Dre l'8/10:
«avevamo fatto dei test per vedere chi faceva meglio le cose con meno errori, dovremo
fare test con questi comunque; guarda anche grok, cinesi, alternative».

Come funziona: le STESSE risposte vere le leggono piu' modelli. Il riferimento e' la
lettura gia' vista e approvata da Dre (cache ~/.odyn-letture.json). Si stampano gli
errori per modello, il costo misurato e i disaccordi uno per uno, perche' dove un
modello dissente giudica Dre: il riferimento non e' la verita', e' quello che abbiamo.

Un modello di cui manca la chiave viene SALTATO con il motivo, non fa morire il giro.
Claude passa dal CLI sul Mac (dentro l'abbonamento): i suoi token non si contano, e
il costo per lui si legge come «abbonamento», non come zero.

Uso:  python3 scripts/banco_modelli.py                      (36 risposte, i modelli economici)
      python3 scripts/banco_modelli.py --quanti 80
      python3 scripts/banco_modelli.py --modelli gpt-5-nano,deepseek-chat
      python3 scripts/banco_modelli.py --prova              (dice cosa farebbe e quanto costa, senza spendere)
"""

import hashlib
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cervello                                            # noqa: E402
from stanza import sb, sb_tutte                            # noqa: E402

QUANTI = int(sys.argv[sys.argv.index("--quanti") + 1]) if "--quanti" in sys.argv else 36
PROVA = "--prova" in sys.argv
CANDIDATI = ["gpt-5-nano", "gpt-5-mini", "claude-haiku-4-5", "deepseek-chat", "grok-4.3"]
MODELLI = (sys.argv[sys.argv.index("--modelli") + 1].split(",") if "--modelli" in sys.argv
           else CANDIDATI)
# per milione di token (ingresso, uscita). Si aggiornano a mano: 8/10/2026.
PREZZO = {"gpt-5": (1.25, 10.0), "gpt-5-mini": (0.25, 2.0), "gpt-5-nano": (0.05, 0.4),
          "deepseek-chat": (0.14, 0.28), "deepseek-reasoner": (0.435, 0.87),
          "grok-4.3": (1.25, 2.50), "grok-4.7": (2.0, 6.0),
          "claude-haiku-4-5": (1.0, 5.0), "claude-sonnet-5-5": (2.0, 10.0)}
# media misurata sul consumo vero di settembre-ottobre, per la stima a secco
MEDIA_DENTRO, MEDIA_FUORI = 3108, 2355


def disponibile(m):
    """Si puo' provare? Se no, perche'."""
    f = cervello.fornitore_di(m)
    if f == "claude":
        return True, "CLI sul Mac, dentro l'abbonamento"
    if f not in cervello.COMPATIBILI:
        return False, f"fornitore «{f}» non previsto"
    nome = cervello.COMPATIBILI[f][1]
    return (True, f"chiave {nome} presente") if cervello._env(nome) else (False, f"manca {nome} in .env.local")


def campione_vero(quanti):
    """Le risposte che HANNO GIA' un verdetto approvato da Dre.

    8/10: la prima versione pescava le risposte piu' recenti, come faceva il confronto
    del 7/9. Ma il riferimento sta nella cache delle letture approvate, e le risposte
    nuove non ci sono: su 36 ne avevano un verdetto 1. Senza riferimento il banco non
    misura niente. Quindi si parte dal riferimento e si tengono solo quelle: il
    campione e' piu' vecchio, ma e' l'unico su cui «ha sbagliato» vuol dire qualcosa."""
    # 8/10: l'invariante «mai mille righe scambiate per tutte» ha bocciato la prima versione,
    # che leggeva con limit=3000. Chi vuole tutto legge a pagine.
    persone = sb_tutte("/rest/v1/prospects?last_reply_at=not.is.null&select=id,company,name,email,"
                       "classificazione,stage,fuori,enriched&order=last_reply_at.desc") or []
    righe = sb_tutte("/rest/v1/interactions?kind=eq.email_in&select=prospect_id,body&order=at.desc") or []
    ultima = {}
    for r in righe:
        if r.get("prospect_id") and r["prospect_id"] not in ultima:
            ultima[r["prospect_id"]] = r.get("body") or ""
    INTOCCABILI = ("cliente", "perso", "call_fissata", "rinviato")
    fuori = senza_rif = 0
    out = []
    for p in persone:
        if p["id"] not in ultima or len(ultima[p["id"]].strip()) < 15:
            continue
        if (p.get("enriched") or {}).get("classificazione") == "manual" or p.get("stage") in INTOCCABILI or p.get("fuori"):
            fuori += 1
            continue
        if not atteso(ultima[p["id"]]):               # niente verdetto approvato = non misurabile
            senza_rif += 1
            continue
        out.append({"id": p["id"], "testo": ultima[p["id"]], "nome": (p.get("company") or p.get("name") or "")[:28]})
        if len(out) >= quanti:
            break
    return out, fuori, senza_rif


def atteso(testo):
    """Il verdetto approvato da Dre per questo testo, se c'e'."""
    try:
        cache = json.load(open(cervello.CACHE, encoding="utf-8"))
    except Exception:
        return None
    vecchia = hashlib.sha256((cervello.REGOLE + "\x00" + " ".join(testo.split())).encode("utf-8")).hexdigest()[:24]
    for k in (vecchia, cervello._impronta(testo, "claude-sonnet-5"), cervello._impronta(testo, "gpt-5")):
        if k in cache:
            return (cache[k] or {}).get("classe")
    return None


def main():
    campione, scartati, senza_rif = campione_vero(QUANTI)
    con_rif = campione                                   # per costruzione hanno tutte un riferimento
    print(f"BANCO DI PROVA — {len(campione)} risposte vere, tutte con un verdetto approvato da Dre")
    print(f"({scartati} scartate perche' clienti/persi/fuori, {senza_rif} perche' mai lette e approvate)\n")

    print("I CANDIDATI")
    pronti = []
    for m in MODELLI:
        ok, perche = disponibile(m)
        pin, pout = PREZZO.get(m, (0, 0))
        stima = (MEDIA_DENTRO * pin + MEDIA_FUORI * pout) / 1e6 * len(campione)
        soldi = "abbonamento" if cervello.fornitore_di(m) == "claude" else f"~{stima:.2f} $"
        print(f"  {'SI ' if ok else 'NO '} {m:18} {soldi:>14}   {perche}")
        if ok:
            pronti.append(m)
    costo_atteso = sum((MEDIA_DENTRO * PREZZO.get(m, (0, 0))[0] + MEDIA_FUORI * PREZZO.get(m, (0, 0))[1]) / 1e6 * len(campione)
                       for m in pronti if cervello.fornitore_di(m) != "claude")
    print(f"\n  il giro costa in tutto ~{costo_atteso:.2f} $ (i modelli via CLI non si pagano a consumo)")
    if not con_rif:
        print("\nSENZA RIFERIMENTO non si misura niente: la cache delle letture approvate e' vuota per questo campione.")
        return
    if PROVA:
        print("\n(--prova: non ho speso niente. Togli --prova per farlo davvero.)")
        return

    esiti, spesa, tempi = {}, {}, {}
    for m in pronti:
        prima = json.load(open(cervello.USO)) if os.path.exists(cervello.USO) else {}
        t0 = time.time()
        try:
            esiti[m] = cervello.leggi(campione, modello=m)
        except Exception as e:                                    # noqa: BLE001
            print(f"\n  {m}: il giro e' fallito ({str(e)[:90]})")
            esiti[m] = {}
        tempi[m] = time.time() - t0
        dopo = json.load(open(cervello.USO)) if os.path.exists(cervello.USO) else {}
        u0, u1 = prima.get(m, {"dentro": 0, "fuori": 0}), dopo.get(m, {"dentro": 0, "fuori": 0})
        d, f = u1["dentro"] - u0["dentro"], u1["fuori"] - u0["fuori"]
        pin, pout = PREZZO.get(m, (0, 0))
        spesa[m] = (d, f, d / 1e6 * pin + f / 1e6 * pout)

    print("\nCOME SONO ANDATI\n")
    print(f"  {'modello':18} {'letti':>7} {'giusti':>11} {'sbagliati':>10} {'costo':>10} {'secondi':>9}")
    for m in pronti:
        giusti = sum(1 for c in con_rif if esiti[m].get(c["id"], {}).get("classe") == atteso(c["testo"]))
        letti = sum(1 for c in con_rif if c["id"] in esiti[m])
        d, f, costo = spesa.get(m, (0, 0, 0))
        soldi = "abbonam." if cervello.fornitore_di(m) == "claude" else f"{costo:.4f} $"
        print(f"  {m:18} {letti:>3}/{len(con_rif):<3} {giusti:>7}/{len(con_rif):<3} {letti - giusti:>10} {soldi:>10} {tempi.get(m, 0):>8.1f}")

    print("\nDOVE NON SONO D'ACCORDO (giudica Dre)\n")
    print(f"  {'chi':28} {'approvato':14}" + "".join(f"{m[:13]:14}" for m in pronti))
    for c in con_rif:
        r = atteso(c["testo"])
        v = [esiti[m].get(c["id"], {}).get("classe", "-") for m in pronti]
        if any(x != r for x in v):
            print(f"  {c['nome']:28} {str(r):14}" + "".join(f"{str(x)[:13]:14}" for x in v))
    print("\nIl riferimento non e' la verita': e' la lettura che Dre ha approvato.")


if __name__ == "__main__":
    main()
