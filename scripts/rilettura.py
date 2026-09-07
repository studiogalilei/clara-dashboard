#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""LA RILETTURA — Clara ripassa le risposte: corregge il sicuro, propone il resto.

PERCHE' UNA SECONDA PASSATA E NON DENTRO IL SYNC
Il sync funziona e riconcilia: e' il pezzo che non deve rompersi mai. Le sue
regex restano come primo colpo d'occhio. La rilettura viene dopo: se il
cervello tace, il CRM resta com'era invece che a meta'.

LA LINEA FRA FARE E CHIEDERE (docs/LA-STANZA-DI-CLARA.md)
Fa da sola, annotandolo in enriched.lettura:
  - spostare fra ooo, negativo, rinvio, tiepido
  - mettere la data di ricontatto che la persona ha detto
Chiede nella stanza, con una proposta:
  - chiunque entri o esca dai positivi (cambia il lavoro di Dre)
  - chiunque vada scartato (fuori_target): lo decide Dre
  - i messaggi che non ha capito: non li nasconde in «da classificare»
Non tocca: i corretti a mano, chi e' gia' in pipeline, i clienti, i persi.

L'ARCHIVIO VUOTO
274 risposte su 738 hanno in archivio solo la notifica di Smartlead, non il
testo. Quando il cervello dice «non leggibile» la classe vecchia resta:
veniva dal tag di Smartlead letto sul thread vivo, e vale piu' del niente.

USO
  python3 scripts/rilettura.py --prova     mostra cosa farebbe
  python3 scripts/rilettura.py             corregge il sicuro, propone il resto
  python3 scripts/rilettura.py --quanti 40 solo i primi 40
"""

import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cervello                                            # noqa: E402
from stanza import sb, proponi                             # noqa: E402

PROVA = "--prova" in sys.argv
QUANTI = int(sys.argv[sys.argv.index("--quanti") + 1]) if "--quanti" in sys.argv else None

INTOCCABILI = ("cliente", "perso", "call_fissata", "rinviato")
SICURE = {"ooo", "negativo", "rinvio", "tiepido"}
AUTOMATICA = re.compile(r"automatic|autorispo|auto-?repl|out of office|fuori ufficio|assen|ferie|vacan|rientr|chius", re.I)
ETICHETTA = {"positivo": "positivo", "tiepido": "tiepido", "negativo": "negativo",
             "ooo": "fuori ufficio", "rinvio": "rinvio", "fuori_target": "fuori target",
             "da_classificare": "da capire"}


def ultima_risposta_per_persona():
    righe = sb("GET", "/rest/v1/interactions?kind=eq.email_in"
                      "&select=prospect_id,body,at&order=at.desc&limit=3000") or []
    ultima = {}
    for r in righe:
        pid = r.get("prospect_id")
        if pid and pid not in ultima:
            ultima[pid] = r
    return ultima


def illeggibile(v):
    p = (v.get("perche") or "").lower()
    return v["classe"] == "da_classificare" and any(
        k in p for k in ("non leggibile", "vuoto", "notifica", "solo firma", "illeggibile"))


def main():
    print("LA RILETTURA" + (" (prova: non scrive niente)" if PROVA else ""))
    if not cervello.disponibile():
        sys.exit("il cervello non risponde: serve Claude Code sul Mac (prova: claude -p)")

    persone = sb("GET", "/rest/v1/prospects?last_reply_at=not.is.null"
                        "&select=id,email,company,name,classificazione,stage,fuori,"
                        "pipeline_stage,enriched,next_action_date,ooo_until"
                        "&order=last_reply_at.desc&limit=2000") or []
    ultima = ultima_risposta_per_persona()

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
    print(f"  {len(persone)} hanno risposto · {len(da_leggere)} da rileggere\n")
    if not da_leggere:
        return

    letti = cervello.leggi(da_leggere, quando_pronto=lambda f, t: print(f"  letti {f}/{t}…"))

    uguali, vuoti, sicure, proposte = 0, 0, [], []
    for pid, v in letti.items():
        p = indice[pid]
        prima = p.get("classificazione")
        nome = (p.get("company") or p.get("name") or p.get("email") or "")[:40]
        if illeggibile(v):
            vuoti += 1
            continue
        if v["classe"] == prima:
            uguali += 1
            # anche se non cambia classe, una data detta dalla persona vale
            if v["quando"] and v["classe"] in ("rinvio", "ooo") and not p.get("next_action_date"):
                sicure.append((p, prima, v, "data"))
            continue
        calda = prima == "positivo" or v["classe"] == "positivo"
        # un risponditore automatico fra i positivi non e' una domanda: lo
        # dice il capitolo «fa da sola» di LA-STANZA-DI-CLARA.md (7/9)
        if v["classe"] == "ooo" and AUTOMATICA.search(v.get("perche") or ""):
            calda = False
        if v["classe"] == "fuori_target":
            proposte.append((p, prima, v, "scarta", f"Scarto {nome}?"))
        elif v["classe"] == "da_classificare":
            proposte.append((p, prima, v, "classifica", f"{nome}: non ho capito la risposta, tu?"))
        elif calda:
            proposte.append((p, prima, v, "classifica",
                             f"{nome}: da {ETICHETTA.get(prima, prima)} a {ETICHETTA[v['classe']]}?"))
        elif v["classe"] in SICURE:
            sicure.append((p, prima, v, "classe"))

    print(f"\n  confermate {uguali} · archivio vuoto {vuoti} · "
          f"correggo da sola {len(sicure)} · chiedo a Dre {len(proposte)}\n")
    for p, prima, v, cosa in sicure[:25]:
        nome = (p.get("company") or p.get("name") or p.get("email") or "")[:34]
        print(f"  faccio   {nome:36} {str(prima):14} -> {v['classe']:12} {v['perche']}")
    for p, prima, v, tipo, titolo in proposte[:40]:
        print(f"  chiedo   [{tipo:10}] {titolo:52} {v['perche']}")
    if PROVA:
        print("\n(prova: non ho scritto niente)")
        return

    for p, prima, v, cosa in sicure:
        arr = dict(p.get("enriched") or {})
        arr["lettura"] = {"classe": v["classe"], "perche": v["perche"], "quando": v["quando"], "da": "cervello"}
        patch = {"enriched": arr}
        if cosa == "classe":
            patch["classificazione"] = v["classe"]
        if v["quando"] and v["classe"] in ("rinvio", "ooo") and not p.get("next_action_date"):
            patch["next_action_date"] = v["quando"]
            patch["next_action"] = "Rientra" if v["classe"] == "ooo" else "Ricontatto: l'aveva chiesto lui"
        sb("PATCH", f"/rest/v1/prospects?id=eq.{p['id']}", patch)

    for p, prima, v, tipo, titolo in proposte:
        azione = {"prospects": {"classificazione": v["classe"]}}
        if tipo == "scarta":
            azione = {"prospects": {"classificazione": "fuori_target", "no_followup": True}}
        if v["quando"]:
            azione["prospects"]["next_action_date"] = v["quando"]
        proponi(tipo, titolo, prospect_id=p["id"], perche=v["perche"], azione=azione)

    print(f"\n  scritte {len(sicure)} correzioni, messe {len(proposte)} proposte nella stanza.")


if __name__ == "__main__":
    main()
