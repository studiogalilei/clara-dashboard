#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""IL PREZZO SUGGERITO (Dre, 26/9/2026).

Dre: «la fee segue la capacita' di spesa del cliente e resta sotto il valore che
gli portiamo. Il sistema propone, Dre decide il prezzo finale».

Le modifiche concordate al dossier (26/9):
  1. si parte dalla DOMANDA GOOGLE della sua zona (volumi x CPC per settore e
     provincia, gia' precalcolati per le analisi): spesa Ads sostenibile =
     domanda x CPC x quota di cattura. Il fatturato dice quanto e' grande
     l'azienda, non quanto puo' spendere su Google;
  2. il BILANCIO corregge, se c'e' (enriched.bilancio: fatturato, utile, anno,
     forma; li scrive Dre nella scheda o un arricchimento futuro): budget
     marketing a scaglioni, moltiplicatore per margine, flag «rischio pagamento»;
  3. la fee e' quella del calcolo «Quanto chiedere» (16/9): base + quota della
     spesa gestita sopra la soglia, mai sotto il floor;
  4. si calcola SOLO in pipeline (call fissata in poi), non per 13.000 prospect;
  5. e' una FASCIA con affidabilita', non un numero secco;
  6. il tetto di valore (un terzo del margine extra) si stima dal ticket del fit e
     resta «da verificare in chiamata» finche' non ci sono i numeri veri.
I parametri stanno nella tabella `parametri` (chiave prezzo.*): Dre cambia un
numero e al giro dopo tutte le schede si ricalcolano.

CORRETTO IL 12/10/2026 (Dre: «dice di spendere 15k in Ads, non e' realistico, di solito
facciamo 20/30 al giorno»). Il punto 1 era sbagliato nel principio: domanda di TUTTA la
provincia × CPC × 3% dava 15.100 €/mese a un'agenzia di Bologna (25 volte il massimo mai
visto sui clienti veri: 10-21 €/giorno), e il canone e il tetto di valore salivano con lei,
quindi il controllo confermava l'errore invece di vederlo. Da oggi:
  1. la spesa Ads e' il BUDGET SUGGERITO di mercato.regola_budget (la regola di Carlo del
     31/7: 6 clic al giorno × CPC, fra 10 e 25 €/giorno in prova), × 30; il bilancio puo'
     solo abbassarla;
  3. il canone e' il LISTINO (tabella listino, Impostazioni › Lo Studio): non dipende dalla
     spesa. Sale sopra il listino solo con i numeri veri della chiamata (enriched.valore),
     fino a un terzo del margine extra: e' «la parte del valore che generiamo» (Dre, 16/9);
  6. il tetto stimato dal ticket del fit si calcola sul budget vero, con l'imbuto prudente
     (0,6% dei clic: contatto 3% × chiusura 20%), e resta «da verificare in chiamata».
DIFESA: il numero e' interno. Non entra mai in una mail (manda.py lo controlla).

USO
  python3 scripts/prezzo.py            calcola per chi e' in pipeline
  python3 scripts/prezzo.py --prova    mostra e non scrive
  python3 scripts/prezzo.py --email a@b.it
"""
import datetime
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from stanza import sb, soldi_clienti, con_soldi           # noqa: E402

PROVA = "--prova" in sys.argv
SOLO = sys.argv[sys.argv.index("--email") + 1] if "--email" in sys.argv else None


def parametri():
    rs = sb("GET", "/rest/v1/parametri?select=chiave,valore&chiave=like.prezzo.*") or []
    return {r["chiave"].split(".", 1)[1]: r["valore"] for r in rs}


def scaglioni(fatturato, tabella):
    """Budget marketing annuo a scaglioni, come l'IRPEF: ogni fetta ha la sua percentuale."""
    tot, prec = 0.0, 0.0
    for limite, perc in tabella:
        alto = fatturato if limite is None else min(fatturato, limite)
        if alto > prec:
            tot += (alto - prec) * perc
        prec = alto if limite is not None else prec
        if limite is not None and fatturato <= limite:
            break
    return tot


def moltiplicatore(valore, tabella):
    for limite, k in tabella:
        if limite is None or valore < limite:
            return k
    return tabella[-1][1]


def tondo(x, a=100):
    return int(round(x / a) * a)


def listino_canone(P):
    """Il canone dal listino (la voce ricorrente della linea marketing) e il prezzo della
    prova. Se il listino non si legge, la base dei parametri."""
    try:
        rs = sb("GET", "/rest/v1/listino?select=nome,prezzo,ricorrenza&linea=eq.marketing&attivo=eq.true&order=ordine") or []
        mese = next((float(r["prezzo"]) for r in rs if r.get("ricorrenza") == "mese"), None)
        prova = next((float(r["prezzo"]) for r in rs if r.get("ricorrenza") == "una_tantum"), None)
        return (mese or float(P["base"]), prova)
    except Exception:                                         # noqa: BLE001
        return (float(P["base"]), None)


def calcola(p, P, vol, fit, racc, listino=None):
    """Torna il blocco enriched.prezzo, o None se manca tutto. `listino` = (canone al mese, prova)."""
    import mercato
    canone, prova = listino or (float(P["base"]), None)
    flag, perche = [], []
    fase = "retainer" if (p.get("pipeline_stage") == "cliente") else "prova"
    # 1. il budget suggerito, dalla regola di Carlo (non dalla domanda di tutta la provincia)
    spesa_domanda, budget_giorno = None, None
    if vol and vol.get("tam") and vol.get("cpc_medio"):
        budget_giorno, come = mercato.regola_budget(vol["tam"], vol["cpc_medio"], fase)
        if budget_giorno:
            spesa_domanda = budget_giorno * 30
            perche.append(f"budget Ads suggerito {budget_giorno:g} €/giorno (~{tondo(spesa_domanda):,} €/mese): {come}".replace(",", "."))
    # 2. il bilancio, se c'e': puo' solo abbassare
    bil = (p.get("enriched") or {}).get("bilancio") or {}
    spesa_bilancio, k_m, affid_bil = None, 1.0, None
    try:
        F = float(bil.get("fatturato") or 0)
    except (TypeError, ValueError):
        F = 0
    if F > 0:
        budget = scaglioni(F, P["scaglioni"])
        spesa_bilancio = budget * (1 - P["quota_agenzia"]) / 12
        perche.append(f"bilancio {bil.get('anno') or '?'}: fatturato {tondo(F, 1000):,} € → budget marketing ~{tondo(budget, 1000):,} €/anno".replace(",", "."))
        try:
            U = float(bil.get("utile")) if bil.get("utile") not in (None, "") else None
        except (TypeError, ValueError):
            U = None
        if U is not None:
            m = U / F
            k_m = moltiplicatore(m, P["margine"]) if U >= 0 else P["margine"][0][1]
            perche.append(f"margine netto {m:.1%} → x{k_m}")
            if U < 0:
                flag.append("rischio pagamento: bilancio in perdita")
            affid_bil = "alta"
        else:
            affid_bil = "media"
        anno = bil.get("anno")
        if anno and int(anno) < datetime.date.today().year - 1:
            flag.append(f"bilancio vecchio ({anno})")
            affid_bil = "media"
    if spesa_domanda is None and spesa_bilancio is None:
        return None
    spesa = min(x for x in (spesa_domanda, (spesa_bilancio * k_m) if spesa_bilancio else None) if x is not None)
    formula = "domanda" if spesa_domanda is not None and (spesa_bilancio is None or spesa_domanda <= spesa_bilancio * k_m) else "bilancio"
    if formula == "bilancio":
        perche.append(f"il bilancio tiene la spesa a ~{tondo(spesa):,} €/mese".replace(",", "."))
    # 3. il canone: il listino. Non dipende dalla spesa.
    fee = canone
    perche.append(f"canone dal listino: {tondo(fee):,} €/mese".replace(",", ".") + (f" (prova di 2 mesi a {tondo(prova):,} €)".replace(",", ".") if prova else ""))
    # 4. il tetto di valore: dai numeri della chiamata, o stimato dal ticket del fit sul budget vero
    valore = (p.get("enriched") or {}).get("valore") or {}
    tetto, tetto_fonte, dalla_call = None, "da verificare in chiamata", False
    try:
        if valore.get("clienti_extra_anno") and valore.get("valore_cliente") and valore.get("margine_lordo") is not None:
            tetto = float(valore["clienti_extra_anno"]) * float(valore["valore_cliente"]) * float(valore["margine_lordo"]) * P["tetto_quota"] / 12
            tetto_fonte, dalla_call = "dai numeri della chiamata", True
        elif fit.get("ticket_min") and vol and vol.get("cpc_medio"):
            clic = spesa / vol["cpc_medio"]
            clienti_mese = clic * P["conversione"]
            tetto = clienti_mese * float(fit["ticket_min"]) * 0.5 * P["tetto_quota"]     # margine lordo 50%: ipotesi
            tetto_fonte = f"stima dal ticket del fit ({fit['ticket_fonte'] or 'stima'}): ~{clienti_mese:.1f} clienti/mese a {int(fit['ticket_min']):,} €".replace(",", ".")
    except (TypeError, ValueError):
        tetto = None
    # la fascia: il listino; con i numeri della chiamata sale fino al tetto, mai oltre il doppio
    alto = fee
    if dalla_call and tetto and tetto > fee:
        alto = min(tetto, fee * 2)
        perche.append(f"con i numeri della chiamata si puo' chiedere fino a ~{tondo(alto):,} €/mese (un terzo del margine extra)".replace(",", "."))
    if tetto is not None and fee > tetto:
        flag.append("la fee supera un terzo del valore stimato")
    # 5. affidabilita'
    if dalla_call:
        affid = "alta"
    elif spesa_domanda is not None:
        affid = "media"
    else:
        affid = "bassa"
    return {
        "fascia": [tondo(fee), tondo(alto)], "punto": tondo(fee), "prova": tondo(prova) if prova else None,
        "spesa_ads_mese": tondo(spesa, 10), "budget_giorno": budget_giorno, "fase": fase, "formula": formula,
        "tetto_mese": tondo(tetto, 10) if tetto is not None else None, "tetto_fonte": tetto_fonte,
        "affidabilita": affid, "flag": flag, "perche": perche,
        "il": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
    }


# IL BILANCIO DA OPENAPI (Dre, 26/9): «si fa quando ha prenotato la call conoscitiva: e' bene
# averlo nella preparazione pre call, cosi' so gia' come impostarmi, che domande fare e che
# lingo usare». Company Advanced, 0,10 € a chiamata: fatturato, utile, dipendenti, forma,
# anno. Una volta per lead, da quando entra in pipeline, solo se la chiave c'e' (OPENAPI_KEY).
DA_TECNICA = ("conoscitiva", "tecnica", "avvio", "prova", "cliente")


def bilancio_openapi(p):
    """Torna il blocco bilancio, o None. Cerca per nome (IT-search, 0,01 €) e poi legge
    l'Advanced (0,10 €). I nomi dei campi si tengono larghi: la risposta grezza resta nel blocco."""
    import urllib.parse
    import urllib.request
    from stanza import env
    k = os.environ.get("OPENAPI_KEY") or env("OPENAPI_KEY")
    if not k or not p.get("company"):
        return None

    def g(url):
        req = urllib.request.Request(url, headers={"Authorization": f"Bearer {k}", "User-Agent": "clara/1.0"})
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.loads(r.read() or b"{}")
    try:
        cerca = g(f"https://company.openapi.com/IT-search?denominazione={urllib.parse.quote(p['company'])}&limit=5")
        trovati = cerca.get("data") or []
        citta = (p.get("city") or "").lower()
        scelto = next((t for t in trovati if citta and citta in json.dumps(t, ensure_ascii=False).lower()), trovati[0] if trovati else None)
        if not scelto:
            return {"esito": "non trovata su OpenAPI", "il": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")}
        piva = scelto.get("vatCode") or scelto.get("taxCode") or scelto.get("piva")
        adv = (g(f"https://company.openapi.com/IT-advanced/{piva}").get("data") or {})
        adv = adv[0] if isinstance(adv, list) and adv else adv
        bil = adv.get("balanceSheets") or adv.get("balanceSheet") or adv.get("bilanci") or {}
        ultimo = (bil.get("last") if isinstance(bil, dict) else (bil[0] if bil else {})) or {}
        return {
            "fatturato": ultimo.get("turnover") or ultimo.get("revenue") or ultimo.get("fatturato") or adv.get("turnover") or adv.get("revenue"),
            "utile": ultimo.get("profit") or ultimo.get("netProfit") or ultimo.get("utile"),
            "anno": ultimo.get("year") or ultimo.get("balanceSheetDate", "")[:4] or ultimo.get("anno"),
            "dipendenti": adv.get("employees") or ultimo.get("employees"),
            "forma": (adv.get("legalForm") or {}).get("description") if isinstance(adv.get("legalForm"), dict) else adv.get("legalForm"),
            "piva": piva, "fonte": "openapi IT-advanced", "grezzo": json.dumps(adv, ensure_ascii=False)[:1500],
            "il": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
        }
    except Exception as e:                                    # noqa: BLE001
        print(f"    openapi non risponde per {p.get('company')[:30]}: {str(e)[:80]}")
        return None


def main():
    import analisi_auto
    P = parametri()
    if not P:
        sys.exit("mancano i parametri prezzo.* (schema_v59)")
    campi = "id,email,company,website,sector,city,pipeline_stage,fuori,enriched"
    if SOLO:
        righe = sb("GET", f"/rest/v1/prospects?select={campi}&email=eq.{SOLO}") or []
    else:
        righe = sb("GET", f"/rest/v1/prospects?select={campi}&fuori=eq.true&pipeline_stage=not.in.(perso)&limit=300") or []
    # prezzo, bilancio e valore stanno in cassaforte (29/9): si rimettono in memoria per il calcolo
    soldi = soldi_clienti([r["id"] for r in righe])
    righe = [con_soldi(r, soldi) for r in righe]
    listino = listino_canone(P)
    fatti, saltati = 0, 0
    for p in righe:
        arr = p.get("enriched") or {}
        vecchio = arr.get("prezzo") or {}
        # si ricalcola se non c'e', se i parametri o il bilancio sono cambiati dopo, o ogni 7 giorni
        bil_il = (arr.get("bilancio") or {}).get("il") or ""
        val_il = (arr.get("valore") or {}).get("il") or ""
        par_il = max((r.get("aggiornato_il") or "" for r in (sb("GET", "/rest/v1/parametri?select=aggiornato_il&chiave=like.prezzo.*") or [])), default="")
        if vecchio.get("il") and vecchio["il"] > max(bil_il, val_il, par_il) and (datetime.datetime.now(datetime.timezone.utc) - datetime.datetime.fromisoformat(vecchio["il"])).days < 7 and not SOLO:
            saltati += 1; continue
        # dalla call tecnica in poi, il bilancio si prende da OpenAPI una volta sola
        bil = arr.get("bilancio") or {}
        if p.get("pipeline_stage") in DA_TECNICA and not bil.get("fatturato") and not bil.get("fonte") and not PROVA:
            nuovo = bilancio_openapi(p)
            if nuovo:
                fresco = (sb("GET", f"/rest/v1/prospects?select=enriched&id=eq.{p['id']}") or [{}])[0]
                arr = dict(fresco.get("enriched") or {}); arr["bilancio"] = {**bil, **{k: v for k, v in nuovo.items() if v not in (None, "")}}
                sb("PATCH", f"/rest/v1/prospects?id=eq.{p['id']}", {"enriched": arr}); p["enriched"] = arr
                print(f"  {(p.get('company') or p['email'])[:36]}: bilancio da OpenAPI: {nuovo.get('fatturato')} € ({nuovo.get('anno')}), {nuovo.get('esito', '')}")
        try:
            s = analisi_auto.scheda(p)
        except Exception as e:                                # noqa: BLE001
            print(f"  {(p.get('company') or p['email'])[:36]}: scheda non letta ({str(e)[:60]})"); continue
        blocco = calcola(p, P, s.get("volumi"), s.get("fit") or {}, s.get("raccolta") or {}, listino)
        nome = (p.get("company") or p["email"])[:36]
        if not blocco:
            print(f"  {nome:36} niente: senza volumi della zona e senza bilancio"); continue
        print(f"  {nome:36} {blocco['fascia'][0]:>6}-{blocco['fascia'][1]:<6} €/mese  {blocco['affidabilita']:5} {blocco['formula']:8} {'; '.join(blocco['flag'])}")
        for r in blocco["perche"]:
            print(f"      {r}")
        if not PROVA:
            fresco = (sb("GET", f"/rest/v1/prospects?select=enriched&id=eq.{p['id']}") or [{}])[0]
            arr = dict(fresco.get("enriched") or {}); arr["prezzo"] = blocco
            sb("PATCH", f"/rest/v1/prospects?id=eq.{p['id']}", {"enriched": arr})
        fatti += 1
    print(f"prezzo: {fatti} calcolati, {saltati} già aggiornati, su {len(righe)} in pipeline")
    taratura(P)


def taratura(P):
    """I contatori della taratura dai preventivi veri (12/10: la card prometteva «si tarano
    sui primi dieci preventivi» e nessun codice li contava)."""
    rs = sb("GET", "/rest/v1/preventivi?select=accettato_il,rifiutato_il&linea=eq.marketing") or []
    nuovo = {**(P.get("taratura") or {"preventivi_minimi": 10}),
             "accettati": sum(1 for r in rs if r.get("accettato_il")), "rifiutati": sum(1 for r in rs if r.get("rifiutato_il"))}
    if nuovo != P.get("taratura") and not PROVA:
        sb("PATCH", "/rest/v1/parametri?chiave=eq.prezzo.taratura", {"valore": nuovo})
        print(f"  taratura: {nuovo['accettati']} accettati, {nuovo['rifiutati']} rifiutati")


if __name__ == "__main__":
    main()
