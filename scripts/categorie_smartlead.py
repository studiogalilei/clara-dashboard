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


def categoria_di(p, intento=None, girato=False):
    """La categoria di Dre per un lead, o None se non se ne mette una."""
    if p.get("fuori") or p.get("bloccato"):
        return None
    c = p.get("classificazione")
    if c in ("soppresso", "fuori_target", "da_classificare", None):
        return None
    if c in ("negativo", "nervoso"):
        return NO
    if c in ("rinvio", "ooo"):
        return AVANTI
    if c == "persona_sbagliata" or girato or intento in INTENTI_GIRATO:
        return GIRATO
    if c == "tiepido" or intento in INTENTI_DOMANDA:
        return DOMANDA
    if c == "positivo":
        return SI
    return None


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
    righe = []
    for p in ps:
        voluta = categoria_di(p, intenti.get(p["id"]), p["id"] in girati)
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
