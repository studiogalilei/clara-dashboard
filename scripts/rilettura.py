#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""LA RILETTURA — Clara ripassa le risposte e corregge le classificazioni.

PERCHE' UNA SECONDA PASSATA E NON DENTRO IL SYNC
Il sync funziona e riconcilia: e' il pezzo che non deve rompersi mai, perche'
e' quello che garantisce che nessuna risposta si perda. Le sue regex restano
li' come primo colpo d'occhio, veloce e senza rete. La rilettura viene dopo e
corregge: se il cervello non risponde, il CRM resta come prima invece di
restare a meta'. Due passate, due rischi separati (7/9/2026).

COSA TOCCA E COSA NO
Scrive solo `classificazione` e la data di ricontatto, e SOLO su chi non e'
stato corretto a mano da Dre (enriched.classificazione == 'manual') e non e'
gia' uscito dalla pipeline. Il giudizio del cervello e il perche' finiscono
in `enriched.lettura`, cosi' si puo' sempre vedere chi ha deciso cosa.

USO
  python3 scripts/rilettura.py --prova     legge e mostra cosa cambierebbe
  python3 scripts/rilettura.py             legge e scrive
  python3 scripts/rilettura.py --quanti 40 solo i primi 40, per provare
"""

import json
import os
import sys
import urllib.error
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cervello                                            # noqa: E402

RADICE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROVA = "--prova" in sys.argv
QUANTI = None
if "--quanti" in sys.argv:
    QUANTI = int(sys.argv[sys.argv.index("--quanti") + 1])

# non si tocca chi e' gia' uscito dalla pipeline o e' stato deciso a mano
INTOCCABILI = ("cliente", "perso", "call_fissata", "rinviato")


def env(nome):
    for f in (".env.local", ".env"):
        p = os.path.join(RADICE, f)
        if not os.path.exists(p):
            continue
        for riga in open(p, encoding="utf-8"):
            if riga.strip().startswith(nome + "="):
                return riga.split("=", 1)[1].strip().strip("\"'")
    return None


URL = env("VITE_SUPABASE_URL")
CHIAVE = env("SUPABASE_SERVICE_KEY") or env("SUPABASE_SERVICE_ROLE_KEY")
if not URL or not CHIAVE:
    sys.exit("manca VITE_SUPABASE_URL o la service key in .env.local")


def sb(metodo, percorso, corpo=None, intestazioni=None):
    req = urllib.request.Request(
        URL.rstrip("/") + percorso, method=metodo,
        data=json.dumps(corpo).encode() if corpo is not None else None,
        headers={"apikey": CHIAVE, "Authorization": "Bearer " + CHIAVE,
                 "Content-Type": "application/json", **(intestazioni or {})})
    try:
        with urllib.request.urlopen(req, timeout=40) as r:
            grezzo = r.read()
            return json.loads(grezzo) if grezzo else None
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"{e.code} {e.read()[:200].decode(errors='replace')}")


def ultima_risposta_per_persona():
    """L'ultimo messaggio in entrata di ognuno."""
    righe = sb("GET", "/rest/v1/interactions?kind=eq.email_in"
                      "&select=prospect_id,body,at&order=at.desc&limit=3000") or []
    ultima = {}
    for r in righe:
        pid = r.get("prospect_id")
        if pid and pid not in ultima:
            ultima[pid] = r
    return ultima


def main():
    print("LA RILETTURA" + (" (prova: non scrive niente)" if PROVA else ""))
    if not cervello.disponibile():
        sys.exit("il cervello non risponde: serve Claude Code sul Mac (prova: claude -p)")

    persone = sb("GET", "/rest/v1/prospects?last_reply_at=not.is.null"
                        "&select=id,email,company,name,classificazione,stage,fuori,"
                        "pipeline_stage,enriched,followup_due,next_action_date,ooo_until"
                        "&order=last_reply_at.desc&limit=2000") or []
    ultima = ultima_risposta_per_persona()
    print(f"  {len(persone)} persone hanno risposto almeno una volta")
    print(f"  {len(ultima)} hanno un messaggio leggibile in archivio")

    da_leggere, indice = [], {}
    for p in persone:
        msg = ultima.get(p["id"])
        if not msg:
            continue
        a_mano = (p.get("enriched") or {}).get("classificazione") == "manual"
        if a_mano or p.get("stage") in INTOCCABILI or p.get("fuori"):
            continue
        indice[p["id"]] = p
        da_leggere.append({"id": p["id"], "testo": msg.get("body") or ""})
        if QUANTI and len(da_leggere) >= QUANTI:
            break

    print(f"  {len(da_leggere)} da rileggere (esclusi i corretti a mano e chi e' gia' in pipeline)\n")
    if not da_leggere:
        return

    letti = cervello.leggi(
        da_leggere,
        quando_pronto=lambda fatti, tot: print(f"  letti {fatti}/{tot}…"))
    print(f"\n  il cervello ne ha capiti {len(letti)} su {len(da_leggere)}\n")

    cambiati, uguali, scritti = [], 0, 0
    for pid, v in letti.items():
        p = indice[pid]
        prima = p.get("classificazione")
        if v["classe"] == prima:
            uguali += 1
            continue
        cambiati.append((p, prima, v))

    print(f"  confermate: {uguali} · da correggere: {len(cambiati)}\n")
    for p, prima, v in cambiati[:60]:
        chi = (p.get("company") or p.get("name") or p.get("email") or "")[:34]
        print(f"  {chi:36} {str(prima):16} -> {v['classe']:14} {v['perche']}")
    if len(cambiati) > 60:
        print(f"  … e altri {len(cambiati) - 60}")

    if PROVA:
        print("\n(prova: non ho scritto niente)")
        return

    for p, _prima, v in cambiati:
        arricchito = dict(p.get("enriched") or {})
        arricchito["lettura"] = {"classe": v["classe"], "perche": v["perche"],
                                 "quando": v["quando"], "da": "cervello"}
        patch = {"classificazione": v["classe"], "enriched": arricchito}
        # la data: dove ha senso per la classe, e senza calpestare una gia' messa
        if v["quando"]:
            if v["classe"] == "ooo" and not p.get("ooo_until"):
                patch["ooo_until"] = v["quando"]
            elif v["classe"] == "rinvio" and not p.get("next_action_date"):
                patch["next_action_date"] = v["quando"]
                patch["next_action"] = "Ricontatto: l'aveva chiesto lui"
        sb("PATCH", f"/rest/v1/prospects?id=eq.{p['id']}", patch)
        scritti += 1

    print(f"\n  scritte {scritti} correzioni.")


if __name__ == "__main__":
    main()
