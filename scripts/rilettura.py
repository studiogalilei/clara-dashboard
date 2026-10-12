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
import datetime
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cervello                                            # noqa: E402
from stanza import sb, proponi, sb_tutte                             # noqa: E402

PROVA = "--prova" in sys.argv
QUANTI = int(sys.argv[sys.argv.index("--quanti") + 1]) if "--quanti" in sys.argv else None

INTOCCABILI = ("cliente", "perso", "call_fissata", "rinviato")
# il recupero notturno con senso_v2 acceso (12/10 sera): solo le risposte recenti, con un tetto alle
# letture pagate. Lo storico passa dal poliziotto (piano del 12/10, passo 6)
GIORNI_RECUPERO = 14
TETTO_RECUPERO = 40
SICURE = {"ooo", "negativo", "rinvio", "tiepido", "persona_sbagliata", "nervoso", "soppresso"}
AUTOMATICA = re.compile(r"automatic|autorispo|auto-?repl|out of office|fuori ufficio|assen|ferie|vacan|rientr|chius", re.I)
ETICHETTA = {"positivo": "positivo", "tiepido": "parziale", "negativo": "negativo",
             "ooo": "fuori ufficio", "rinvio": "rinviato", "fuori_target": "fuori target",
             "da_classificare": "da capire", "soppresso": "richiesta di rimozione",
             "persona_sbagliata": "persona sbagliata", "nervoso": "nervoso"}


def ultima_risposta_per_persona():
    righe = sb_tutte("/rest/v1/interactions?kind=eq.email_in"
                      "&select=id,prospect_id,body,ref,at&order=at.desc&limit=3000") or []
    ultima = {}
    for r in righe:
        pid = r.get("prospect_id")
        if pid and pid not in ultima:
            ultima[pid] = r
    return ultima


def segnaposto(testo):
    """La notifica di Smartlead al posto della risposta vera. Si decide col codice, non con le
    parole del modello (5/10: «messaggio di sistema», «testo non disponibile», «automatico
    senza contenuto» passavano il controllo e la classe cambiava ogni notte).
    12/10: una regola, un posto: e' quella della lettura (lettura._segnaposto)."""
    import lettura
    return lettura._segnaposto(testo)


def parte_sua(testo):
    """Solo quello che ha scritto la persona, senza la nostra mail citata sotto (6/10: un lead
    aveva risposto a vuoto, col nostro messaggio citato; il modello ha letto la NOSTRA frase «se le
    fa piacere riceverla, gliela mando subito» come sua e l'ha fatto passare da fuori target a
    positivo). Lo stesso taglio che usa la lettura delle risposte nuove (lettura.solo_suo)."""
    import lettura
    return lettura.solo_suo(testo or "", con_firma=True).strip()


def conferma(p, nuova):
    """L'ISTERESI (6/10). La rilettura gira in cloud e la cache del cervello non sopravvive fra
    una corsa e l'altra: ogni notte lo stesso messaggio ambiguo veniva riletto da capo e la
    classe saltava (tiepido, negativo, tiepido, negativo: cinque cambi in una settimana, e ogni
    cambio accende o spegne i blocchi dei follow-up). Una classe nuova si applica solo se la
    rilettura la ripete due volte di fila; la prima volta si annota come candidata.
    La richiesta di rimozione non aspetta: vale subito.
    Torna «applica» o «aspetta»."""
    if nuova == "soppresso":
        return "applica"
    cand = ((p.get("enriched") or {}).get("lettura_candidata") or {}).get("classe")
    return "applica" if cand == nuova else "aspetta"


def illeggibile(v):
    p = (v.get("perche") or "").lower()
    return v["classe"] == "da_classificare" and any(
        k in p for k in ("non leggibile", "vuoto", "notifica", "solo firma", "illeggibile", "non disponibile",
                         "senza contenuto", "messaggio di sistema", "non risposta umana", "nessun testo"))


def blocca(p):
    """RICHIESTA DI RIMOZIONE (25/9): chi la chiede finisce nella lista di blocco, cosi'
    nessuna lista futura lo ricarica. Da qualunque strada passi la classe (6/10: la strada
    «decisa da sola» scriveva soppresso senza bloccare, un caso del 6/10)."""
    try:
        sb("POST", "/rest/v1/suppressions", [{"kind": "email", "email": e.lower(), "reason": "richiesta di rimozione", "source": "rilettura"}
                                             for e in [p.get("email")] if e], {"Prefer": "resolution=merge-duplicates"})
    except Exception as e2:                              # noqa: BLE001
        print(f"    (blocco non scritto: {str(e2)[:60]})")


def recupero():
    """CON senso_v2 ACCESO la rilettura diventa il recupero notturno (12/10): le risposte senza
    lettura, quelle rimaste «senza AI», e quelle lette da un lettore di una versione vecchia.
    Niente piu' cervello.leggi con le classi nel prompt, niente isteresi: la lettura e' salvata,
    e la classe la da' senso.classe. Il blocco (suppressions) solo con l'AI sicura o con Dre."""
    import lettura
    import senso as S
    persone = sb_tutte("/rest/v1/prospects?last_reply_at=not.is.null"
                       "&select=id,email,email_alt,company,name,classificazione,stage,fuori,pipeline_stage,enriched,next_action_date"
                       "&order=last_reply_at.desc&limit=2000") or []
    # 12/10 sera, dagli scettici: il recupero rileggeva a pagamento TUTTI quelli che hanno risposto (circa
    # 900 letture la prima notte, e di nuovo a ogni versione del lettore), senza tetto, riscrivendo classi.
    # Lo storico e' un'azione di massa: passa dal poliziotto, non da qui. Qui solo le risposte recenti
    # senza una lettura buona, al massimo TETTO letture pagate a notte.
    dal = (datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=GIORNI_RECUPERO)).isoformat()
    ultima = {k: v for k, v in ultima_risposta_per_persona().items() if (v.get("at") or "") >= dal[:19]}
    tetto = QUANTI or TETTO_RECUPERO
    guardate, pagate, cambiate = 0, 0, 0
    for p in persone:
        msg = ultima.get(p["id"])
        a_mano = (p.get("enriched") or {}).get("classificazione") == "manual"
        if not msg or a_mano or p.get("stage") in INTOCCABILI or p.get("fuori") or segnaposto(msg.get("body")):
            continue
        gia = lettura.lettura_salvata(p, msg)
        if gia and gia.get("stato") in ("letta", "seconda", "deciso_dre", "dubbio_a_dre"):
            # gia' letta (dal sync, dalle bozze): la classe l'ha gia' data chi l'ha letta. Restano due cose
            # gratis: un dubbio mai arrivato a Dre (nato in ombra, o la domanda non riuscita) e la data
            # di un rinvio o di un rientro che manca ancora sulla scheda
            if gia.get("stato") == "dubbio_a_dre" and not gia.get("proposta_id") and not gia.get("decisione_dre"):
                lettura.senso(p, msg, attuale=p.get("classificazione"))
            riga, nuova_lettura = None, False
            if not p.get("next_action_date") and p.get("classificazione") in ("rinvio", "ooo"):
                riga = lettura.senso(p, msg, attuale=p.get("classificazione"))
            if not riga:
                continue
        else:
            if pagate >= tetto:
                continue
            riga, nuova_lettura = lettura.senso(p, msg, attuale=p.get("classificazione")), True
            pagate += 1
        guardate += 1
        dec = riga.get("decisione") or {}
        nuova = S.classe(dec, p.get("classificazione"))
        patch = {}
        # la data detta dalla persona vale anche se la classe non cambia (com'era nella rilettura di prima)
        effettiva = nuova if nuova_lettura else p.get("classificazione")
        if effettiva in ("rinvio", "ooo") and not p.get("next_action_date") and (dec.get("quando") or effettiva == "rinvio"):
            if effettiva == "ooo":
                patch["next_action_date"], patch["next_action"] = dec["quando"], "Rientra"
            else:
                patch["next_action_date"], patch["next_action"] = S.ripresa(dec.get("quando"))
        if nuova != p.get("classificazione") and nuova_lettura:
            cambiate += 1
            arr = dict(p.get("enriched") or {})
            arr["lettura"] = {"classe": nuova, "perche": dec.get("motivo"), "quando": dec.get("quando"), "da": "senso",
                              "fonte": dec.get("fonte"), "lettura_id": riga.get("id"), "prima": p.get("classificazione"),
                              "il": datetime.datetime.now(datetime.timezone.utc).isoformat()}
            patch.update({"enriched": arr, "classificazione": nuova})
            if nuova == "soppresso" and S.permanente_ok(dec) and not PROVA:
                blocca(p)
        if not patch:
            continue
        nome = (p.get("company") or p.get("name") or p.get("email") or "")[:40]
        print(f"  {nome:40} {str(p.get('classificazione')):14} -> {nuova:14} {dec.get('fonte')}: «{(dec.get('frase') or '')[:60]}»"
              + (f" (data {patch['next_action_date']})" if patch.get("next_action_date") else ""))
        if PROVA:
            continue
        sb("PATCH", f"/rest/v1/prospects?id=eq.{p['id']}", patch)
    print(f"  recupero: {guardate} risposte degli ultimi {GIORNI_RECUPERO} giorni guardate, {pagate} letture pagate "
          f"(tetto {tetto}), {cambiate} classi cambiate")


def main():
    print("LA RILETTURA" + (" (prova: non scrive niente)" if PROVA else ""))
    import lettura
    if lettura.senso_acceso():
        return recupero()
    if not cervello.disponibile():
        sys.exit("il cervello non risponde: serve Claude Code sul Mac (prova: claude -p)")

    persone = sb_tutte("/rest/v1/prospects?last_reply_at=not.is.null"
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
        if segnaposto(msg.get("body")):
            continue                                        # non c'e' niente da leggere: la classe resta
        suo = parte_sua(msg.get("body"))
        if not suo:
            continue                                        # ha risposto solo citando noi: la classe resta

        indice[p["id"]] = p
        da_leggere.append({"id": p["id"], "testo": suo})
        if QUANTI and len(da_leggere) >= QUANTI:
            break
    print(f"  {len(persone)} hanno risposto, {len(da_leggere)} da rileggere\n")
    if not da_leggere:
        return

    letti = cervello.leggi(da_leggere, quando_pronto=lambda f, t: print(f"  letti {f}/{t}…"))

    uguali, vuoti, sicure, proposte = 0, 0, [], []
    candidate, smentite = [], []                            # l'isteresi (6/10): vedi conferma()
    for pid, v in letti.items():
        p = indice[pid]
        prima = p.get("classificazione")
        nome = (p.get("company") or p.get("name") or p.get("email") or "")[:40]
        if illeggibile(v):
            vuoti += 1
            continue
        if prima in ("positivo", "tiepido", "rinvio") and v["classe"] == "da_classificare":
            vuoti += 1                                      # non capire non e' una prova contro un si'
            continue
        if v["classe"] == prima:
            uguali += 1
            if (p.get("enriched") or {}).get("lettura_candidata"):
                smentite.append(p)                          # l'oscillazione e' rientrata: la candidata si toglie
            # anche se non cambia classe, una data detta dalla persona vale
            if v["quando"] and v["classe"] in ("rinvio", "ooo") and not p.get("next_action_date"):
                sicure.append((p, prima, v, "data"))
            continue
        if conferma(p, v["classe"]) == "aspetta":
            candidate.append((p, v))                        # la prima volta si annota soltanto
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

    print(f"\n  confermate {uguali}, archivio vuoto {vuoti}, "
          f"correggo da sola {len(sicure)}, chiedo a Dre {len(proposte)}, "
          f"in attesa di una seconda lettura {len(candidate)}, oscillazioni rientrate {len(smentite)}\n")
    for p, prima, v, cosa in sicure[:25]:
        nome = (p.get("company") or p.get("name") or p.get("email") or "")[:34]
        print(f"  faccio   {nome:36} {str(prima):14} -> {v['classe']:12} {v['perche']}")
    for p, prima, v, tipo, titolo in proposte[:40]:
        print(f"  chiedo   [{tipo:10}] {titolo:52} {v['perche']}")
    if PROVA:
        print("\n(prova: non ho scritto niente)")
        return

    adesso = datetime.datetime.now(datetime.timezone.utc).isoformat()
    for p, v in candidate:
        arr = dict(p.get("enriched") or {})
        arr["lettura_candidata"] = {"classe": v["classe"], "perche": v["perche"], "il": adesso}
        sb("PATCH", f"/rest/v1/prospects?id=eq.{p['id']}", {"enriched": arr})
    for p in smentite:
        arr = dict(p.get("enriched") or {})
        arr.pop("lettura_candidata", None)
        sb("PATCH", f"/rest/v1/prospects?id=eq.{p['id']}", {"enriched": arr})

    for p, prima, v, cosa in sicure:
        arr = dict(p.get("enriched") or {})
        arr.pop("lettura_candidata", None)
        arr["lettura"] = {"classe": v["classe"], "perche": v["perche"], "quando": v["quando"], "da": "cervello", "il": datetime.datetime.now(datetime.timezone.utc).isoformat()}
        patch = {"enriched": arr}
        if cosa == "classe":
            patch["classificazione"] = v["classe"]
            # RICHIESTA DI RIMOZIONE (25/9): chi lo chiede finisce subito nella lista di
            # blocco, cosi' nessuna lista futura lo ricarica
            if v["classe"] == "soppresso":
                blocca(p)
        if v["quando"] and v["classe"] in ("rinvio", "ooo") and not p.get("next_action_date"):
            patch["next_action_date"] = v["quando"]
            patch["next_action"] = "Rientra" if v["classe"] == "ooo" else "Ricontatto: l'aveva chiesto lui"
        sb("PATCH", f"/rest/v1/prospects?id=eq.{p['id']}", patch)

    # 23/9 (pulizia di Dre): niente piu' domande in Posta. Clara decide, scrive
    # il perche' nella scheda (enriched.lettura) e Dre corregge se sbaglia.
    # 67 «da positivo a tiepido?» aperte erano lavoro in piu', non in meno.
    for p, prima, v, tipo, titolo in proposte:
        arr = dict(p.get("enriched") or {})
        arr.pop("lettura_candidata", None)
        arr["lettura"] = {"classe": v["classe"], "perche": v["perche"], "quando": v["quando"], "da": "cervello", "il": datetime.datetime.now(datetime.timezone.utc).isoformat(), "prima": prima}
        patch = {"enriched": arr, "classificazione": "fuori_target" if tipo == "scarta" else v["classe"]}
        if tipo == "scarta":
            patch["no_followup"] = True
        if patch["classificazione"] == "soppresso":
            blocca(p)                                    # 6/10: una lead era soppressa ma non bloccata
        if v["quando"]:
            patch["next_action_date"] = v["quando"]
        sb("PATCH", f"/rest/v1/prospects?id=eq.{p['id']}", patch)

    print(f"\n  scritte {len(sicure)} correzioni sicure e {len(proposte)} decise da sola (annotate nella scheda).")


if __name__ == "__main__":
    main()
