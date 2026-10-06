#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""LE CATEGORIE DI DRE SU SMARTLEAD (6/10/2026).

Dre: «posso cambiare i "mark lead as" e mettere termini miei? quando li approvo
li imposti e ogni volta le mail si autoclassificano». Le 5 categorie le ha create
lui in Smartlead (Settings → Lead Categories). Decide UN cervello solo, il nostro
(rilettura, bozze, Dre a mano): Smartlead mostra l'etichetta, non giudica. Due
classificatori in disaccordo li abbiamo gia' visti: il 6/10 alle 5 il sync aveva
fatto diventare positivi quattro no.

Come lavora: per ogni lead che ha risposto calcola la categoria dalla classe del
Workspace (e dall'intento dell'ultima bozza, per distinguere un si' da una
domanda) e, se e' diversa da quella gia' scritta (enriched.sl_categoria), la
scrive su Smartlead nella campagna dove ha risposto per ultimo. Ogni giro del
direttore la riallinea: qualunque cosa cambi la classe, la categoria segue.

Mai toccati: soppressi, fuori (pipeline e clienti), bloccati (regole del
Revisore); fuori target e da classificare restano senza categoria (non sono
una loro risposta). Mai una mail: cambia solo l'etichetta, pause_lead=false.

  python3 scripts/categorie_smartlead.py --prova     mostra cosa farebbe
  python3 scripts/categorie_smartlead.py             allinea (passa dal Revisore)
"""
import datetime
import os
import sys
import urllib.parse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from stanza import sb, sb_tutte, di_clara                     # noqa: E402

PROVA = "--prova" in sys.argv or os.environ.get("PROVA") == "1"

SI, DOMANDA, AVANTI, GIRATO, NO = "Sì, vuole l'analisi.", "Ha una domanda", "Più avanti", "Girato a un altro.", "No"
CATEGORIE = (SI, DOMANDA, AVANTI, GIRATO, NO)
# gli intenti del playbook che sono una domanda, non un si' (INT-03 chi siete, INT-04 come
# ci avete trovato, INT-15 che societa' siete)
INTENTI_DOMANDA = {"INT-03", "INT-04", "INT-15"}
INTENTI_GIRATO = {"INT-08", "INT-09"}


import re as _re
# 6/10, dal campione letto prima di scrivere: «il mio indirizzo e' cambiato», «casella
# dismessa», «non collabora piu'» erano classificati fuori ufficio e finivano in «Piu' avanti»
CAMBIO = _re.compile(r"(indirizzo|address|e-?mail)\W+(\w+\W+){0,4}(cambiat|changed|modificat)|non (e'|è) piu' attiv|non è più attiv|"
                     r"(verra'|verrà|sara'|sarà) dismess|casella\W+(\w+\W+){0,4}(chius|dismess|disattiv|non (e'|è) piu')|"
                     r"non collabora pi|non fa pi[uù] parte|no longer (with|works)|inoltrare la (mail|comunicazione)", _re.I)
# «ho girato la vostra mail all'ufficio competente» (6/10, secondo campione): e' un inoltro
INOLTRATO = _re.compile(r"(ho|abbiamo) (girato|inoltrato|passato) (la (vostra|sua|tua) (mail|email|richiesta)|al (collega|responsabile|ufficio))", _re.I)
# un no scritto chiaro dentro un si' di classe: non si etichetta, si segnala (la classe e' sbagliata)
NO_SCRITTO = _re.compile(r"non (e'|è) di (nostro|mio) interesse|non (ci|mi) interessa|non (siamo|sono) interessat|"
                         r"non fa per noi|non abbiamo (bisogno|necessit|interesse)|abbiamo gi[aà] chi", _re.I)


def categoria_di(p, intento=None, girato=False, testo=""):
    """La categoria di Dre per un lead, o None se non se ne mette una.
    `testo` e' la sua ultima risposta (solo la parte sua): corregge i casi che la classe
    sbaglia per costruzione (un cambio d'indirizzo letto come fuori ufficio)."""
    if p.get("fuori") or p.get("bloccato"):
        return None
    c = p.get("classificazione")
    if c in ("soppresso", "fuori_target", "da_classificare", None):
        return None
    if c in ("negativo", "nervoso"):
        return NO
    if testo and CAMBIO.search(testo):
        return GIRATO
    if c in ("rinvio", "ooo"):
        return AVANTI
    if c == "persona_sbagliata" or intento in INTENTI_GIRATO:
        return GIRATO
    if c in ("positivo", "tiepido") and testo and NO_SCRITTO.search(testo):
        return None                       # la classe dice si', lui dice no: va guardato, non etichettato
    if (girato or (testo and INOLTRATO.search(testo))) and c != "positivo":
        return GIRATO                     # un inoltro conta se non ha detto si' (6/10: «Ok grazie» finiva qui)
    if c == "tiepido" or intento in INTENTI_DOMANDA:
        return DOMANDA
    if c == "positivo":
        return SI
    return None


def da_guardare(p, testo):
    """Si' di classe con un no scritto: la classe va corretta da Dre o dalla rilettura."""
    return p.get("classificazione") in ("positivo", "tiepido") and not p.get("fuori") and bool(testo and NO_SCRITTO.search(testo))


def _sl(metodo, percorso, corpo=None):
    """Smartlead frena se le richieste sono tante: si riprova con attesa crescente."""
    import time
    import manda
    for tentativo in range(4):
        try:
            return manda.sl(metodo, percorso, corpo)
        except Exception:                                          # noqa: BLE001
            if tentativo == 3:
                raise
            time.sleep(2 * (tentativo + 1) ** 2)


def id_categorie():
    nomi = {c["name"]: c["id"] for c in (_sl("GET", "/leads/fetch-categories") or [])}
    mancano = [n for n in CATEGORIE if n not in nomi]
    if mancano:
        sys.exit(f"categorie: su Smartlead mancano {mancano}, non scrivo niente")
    return {n: nomi[n] for n in CATEGORIE}


def dove_ha_risposto(email):
    """(campagna, lead) dove ha risposto per ultimo."""
    d = _sl("GET", f"/leads/?email={urllib.parse.quote(email)}") or {}
    camp = sorted([c for c in d.get("lead_campaign_data") or [] if c.get("last_reply_at")],
                  key=lambda c: c["last_reply_at"], reverse=True)
    return (int(camp[0]["campaign_id"]), int(d["id"])) if camp and d.get("id") else (None, None)


DA_GUARDARE = []


def da_allineare():
    ps = sb_tutte("/rest/v1/prospects?select=id,email,company,classificazione,fuori,enriched"
                  "&last_reply_at=not.is.null&email=not.is.null")
    intenti, girati = {}, set()
    for x in sb_tutte("/rest/v1/proposte?select=prospect_id,at,azione&prospect_id=not.is.null"
                      "&tipo=in.(risposta,umano)&order=at.asc") or []:
        az = x.get("azione") or {}
        if az.get("intento"):
            intenti[x["prospect_id"]] = az["intento"]
        if (az.get("lettura") or {}).get("girato_a"):
            girati.add(x["prospect_id"])
    import lettura
    ultima = {}
    ids = [p["id"] for p in ps]
    for i in range(0, len(ids), 80):
        for x in sb("GET", "/rest/v1/interactions?select=prospect_id,at,body&kind=eq.email_in&order=at.desc&limit=1000"
                           f"&prospect_id=in.({','.join(ids[i:i + 80])})") or []:
            ultima.setdefault(x["prospect_id"], x.get("body") or "")
    righe, DA_GUARDARE[:] = [], []
    for p in ps:
        testo = lettura.solo_suo(ultima.get(p["id"], ""), con_firma=True) or ""
        if da_guardare(p, testo):
            DA_GUARDARE.append((p.get("company") or p["email"], p.get("classificazione"), testo[:90]))
        voluta = categoria_di(p, intenti.get(p["id"]), p["id"] in girati, testo)
        gia = ((p.get("enriched") or {}).get("sl_categoria") or {}).get("nome")
        if voluta and voluta != gia:
            righe.append({"id": p["id"], "email": p["email"], "azienda": p.get("company") or "", "classificazione": p.get("classificazione"),
                          "esito": voluta, "fuori": p.get("fuori"), "enriched": p.get("enriched") or {}})
    return righe


def main():
    righe = da_allineare()
    conta = {}
    for r in righe:
        conta[r["esito"]] = conta.get(r["esito"], 0) + 1
    print(f"categorie: {len(righe)} lead da allineare {conta}")
    if DA_GUARDARE:
        print(f"categorie: {len(DA_GUARDARE)} si' di classe con un no scritto, senza etichetta (da correggere la classe):")
        for n, c, t in DA_GUARDARE[:15]:
            print(f"  {n[:30]:30} {c}: «{t}»")
    if not righe:
        return
    if PROVA:
        for r in righe[:25]:
            print(f"  {r['email'][:34]:34} {str(r['classificazione']):12} → {r['esito']}")
        print("(prova: non scrivo niente)")
        return
    from revisore import controlla
    righe = controlla("scrivo la categoria di Dre su Smartlead (solo l'etichetta, nessuna mail)", righe,
                      chiave=lambda r: r["email"], irreversibile=False,
                      motivo="Dre ha creato le 5 categorie il 6/10 e ha chiesto di categorizzare tutti")
    ids = id_categorie()
    fatti, saltati = 0, []
    for r in righe:
        try:
            cid, lid = dove_ha_risposto(r["email"])
            if not cid:
                saltati.append((r["email"], "non trovato su Smartlead")); continue
            esito = _sl("POST", f"/campaigns/{cid}/leads/{lid}/category", {"category_id": ids[r["esito"]], "pause_lead": False})
            if isinstance(esito, dict) and esito.get("ok") is False:
                saltati.append((r["email"], str(esito)[:80])); continue
            arr = dict(r["enriched"])
            arr["sl_categoria"] = {"nome": r["esito"], "campagna": cid, "il": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")}
            sb("PATCH", f"/rest/v1/prospects?id=eq.{r['id']}", {"enriched": arr})
            fatti += 1
        except Exception as e:                                     # noqa: BLE001
            saltati.append((r["email"], str(e)[:80]))
    print(f"categorie: scritte {fatti}, saltate {len(saltati)}")
    for e, m in saltati[:10]:
        print(f"  saltato {e}: {m}")
    if fatti > 20 or saltati:
        di_clara("controllo", f"Categorie su Smartlead: scritte {fatti}" + (f", {len(saltati)} saltate (es. {saltati[0][0]}: {saltati[0][1]})" if saltati else "") + ".")


if __name__ == "__main__":
    main()
