#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""IL GOOGLE FIT NUOVO: i conti dell'azienda, non il foglio dei settori (5/10/2026).

Dre, 5/10: «se un lead non supera il Google Fit lasciamo stare. Ho paura che il
Fit faccia errori: crea il nuovo Google Fit, che abbia senso.» Il progetto, con
le tre architetture e il perche' della scelta, sta nel vault: «Il Google Fit
nuovo (5-10-2026)».

UNA DOMANDA: con la nostra fee piu' un budget pubblicitario, questa azienda puo'
guadagnare da Google Ads?
1. il modello legge il sito (googlefit.capisci: cosa vendono, a chi, dove, ticket);
2. il modello scrive le parole che userebbe un loro cliente;
3. Keyword Planner, dal vivo, misura quelle parole dove vendono davvero;
4. il modello scarta le idee di Google che non sono loro clienti;
5. il conto, in due scenari: regge la fee e la pubblicita'?
Il modello legge e filtra; il verdetto lo danno i numeri.

Il risultato va in enriched.google_fit_v2, accanto al Fit vecchio.

Gira sul Mac: Keyword Planner usa ~/.hermes/google-ads.yaml e la libreria
google-ads. In cloud serve la stessa chiave nei segreti (da decidere con Dre).

USO
  python3 scripts/fit_nuovo.py --uno EMAIL        uno solo, stampa il conto
  python3 scripts/fit_nuovo.py --ids FILE.json    una lista di id prospect
  aggiungere --prova per non scrivere
"""
import datetime
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from stanza import sb                                               # noqa: E402
import cervello                                                     # noqa: E402
import googlefit                                                    # noqa: E402

# ── il conto: ogni numero col suo perche' ─────────────────────────
BUDGET_ADS = 1000         # euro/mese di pubblicita' in una prova
FEE = 1200                # euro/mese, la nostra
QUOTA_MAX = 0.30          # dei clic possibili non si prende mai piu' del 30%: il mercato non e' tutto nostro
CONTATTO = (0.03, 0.06)   # clic che diventano un contatto: prudente, pieno
CHIUSURA = (0.20, 0.35)   # contatti che diventano clienti: prudente, pieno
ACQUISTO = (0.015, 0.03)  # chi compra al clic (e-commerce): clic che diventano un ordine
DOMANDA_MIN = 100         # ricerche/mese sotto cui non c'e' una campagna da fare
IDEE_MIN = 10             # sotto, Google i dati non li da' (salute e altri settori protetti): non e' «nessuno cerca»
NO_SOTTO = 0.5            # il NO per i numeri solo se anche il caso pieno copre meno di meta' del costo
ESCLUSIONI = {"agenzia": "agenzia di marketing: e' un concorrente, non un cliente",
              "portale": "portale: vive di traffico suo, non compra clic",
              "multinazionale": "multinazionale: il marketing si decide altrove",
              "onlus": "onlus o ente: niente budget pubblicitario",
              "franchising": "network in franchising: il marketing lo fa la casa madre"}

KP = os.path.expanduser("~/Documents/Obsidian/studiogalilei/Sistema Operativo Studio Galilei/ODYN Cockpit/scripts")
GEO_PROV = json.load(open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "geo_province.json")))
GEO_REGIONI = {"veneto": 20580, "lombardia": 20565, "emilia": 20559, "emilia-romagna": 20559, "piemonte": 20573,
               "toscana": 20578, "lazio": 20563, "friuli": 20561, "friuli venezia giulia": 20561,
               "trentino": 20579, "trentino-alto adige": 20579}
ITALIA = "geoTargetConstants/2380"


def _kp():
    sys.path.insert(0, KP)
    import keyword_planner as k
    import yaml
    cfg = yaml.safe_load(open(k.CONFIG))
    cid = str(cfg.get("customer_id") or cfg.get("login_customer_id") or "").replace("-", "")
    return k, k.client_da_config(), cid


def _geo(c, da_dove="zona"):
    """Dove si misura: dove sta chi COMPRA. Le province del raggio, la regione, o l'Italia."""
    raggio = (c.get("raggio") or "").lower()
    if da_dove in ("italia", "estero") or raggio in ("italia", "estero", "piu' regioni"):
        return [ITALIA], "Italia"
    luoghi = [x for x in (c.get("zone_servite") or []) if x] or [c.get("provincia") or ""]
    if raggio == "regione":
        for l in luoghi:
            r = GEO_REGIONI.get(googlefit._norm(l)) or GEO_REGIONI.get(l.lower())
            if r:
                return [f"geoTargetConstants/{r}"], l
    geo, nomi = [], []
    for l in luoghi:
        for nome, codice in GEO_PROV.items():
            if googlefit._norm(l) and googlefit._norm(l) in googlefit._norm(nome):
                geo.append(codice); nomi.append(nome); break
    if geo:
        return geo[:5], ", ".join(nomi[:5])
    return [ITALIA], "Italia (zona non letta: misura larga, da prendere con cautela)"


def _json(testo):
    m = re.search(r"[\[{].*[\]}]", testo or "", flags=re.S)
    try:
        return json.loads(m.group(0)) if m else None
    except json.JSONDecodeError:
        return None


def parole(c, azienda):
    """Le parole del loro cliente, da dove le cerca, e come compra.

    5/10, collaudo sui clienti veri: Bea Vita Tours misurata in Veneto (dove si fa il tour)
    dava 10 ricerche, ma chi compra e' un turista che cerca da fuori; Zafferano misurato
    con l'imbuto «contatto, poi chiusura» quando vende direttamente online. Quindi il
    modello dice anche DA DOVE cerca il cliente e se compra al clic o chiede un contatto."""
    r = cervello._chiedi(f"""Azienda: {azienda}. Cosa fa: {c.get('cosa_fa')}. Tipo: {c.get('tipo')}. Sede: {c.get('provincia')}.
1. Scrivi da 4 a 6 ricerche Google, in italiano, fra le PIU' COMUNI che fa un loro cliente quando
cerca quello che vendono. Brevi: 1-3 parole, quelle che digita la gente, non frasi da brochure.
Niente nome dell'azienda, niente citta'.
Esempio per un idraulico: ["idraulico", "riparazione caldaia", "pronto intervento idraulico"].
Esempio per un intermediario del credito: ["mutuo prima casa", "cessione del quinto", "prestito personale"].
2. Da dove fa quella ricerca il loro cliente: "zona" (vive o lavora vicino a loro), "italia" (da tutta
Italia: e-commerce, turisti italiani, servizi a distanza), "estero" (soprattutto stranieri).
3. Come compra: "online" (compra direttamente sul sito), "contatto" (chiama, scrive, chiede un preventivo).
Rispondi SOLO con JSON: {{"parole": [...], "da_dove": "...", "come_compra": "..."}}""")
    d = _json(r)
    if not isinstance(d, dict):
        return [], "zona", "contatto"
    lista = d.get("parole") if isinstance(d.get("parole"), list) else []
    return [str(x)[:80] for x in lista][:6], str(d.get("da_dove") or "zona"), str(d.get("come_compra") or "contatto")


def misura(k, client, cid, semi, sito, geo):
    """Keyword Planner dal vivo: le idee sulle parole del cliente, nel raggio."""
    svc = client.get_service("KeywordPlanIdeaService")
    req = client.get_type("GenerateKeywordIdeasRequest")
    req.customer_id = cid
    req.language = k.LANG["it"]
    req.geo_target_constants.extend(geo)
    req.include_adult_keywords = False
    req.keyword_plan_network = client.enums.KeywordPlanNetworkEnum.GOOGLE_SEARCH
    if semi and sito:
        req.keyword_and_url_seed.url = sito
        req.keyword_and_url_seed.keywords.extend(semi)
    elif semi:
        req.keyword_seed.keywords.extend(semi)
    else:
        req.url_seed.url = sito
    righe = []
    for r in svc.generate_keyword_ideas(request=req):
        m = r.keyword_idea_metrics
        if (m.avg_monthly_searches or 0) > 0:
            righe.append({"kw": r.text, "vol": m.avg_monthly_searches,
                          "cpc": round(((m.low_top_of_page_bid_micros or 0) + (m.high_top_of_page_bid_micros or 0)) / 2_000_000, 2)})
    righe.sort(key=lambda x: x["vol"], reverse=True)
    return righe[:80]


def filtra(righe, c, azienda):
    """Il modello toglie le idee di Google che non sono clienti loro (concorrenti, curiosi, altro)."""
    if not righe:
        return []
    elenco = "\n".join(f"{i}. {r['kw']}" for i, r in enumerate(righe))
    r = cervello._chiedi(f"""Azienda: {azienda}. Cosa fa: {c.get('cosa_fa')}.
Qui sotto ricerche Google proposte da Keyword Planner. Tieni SOLO quelle fatte da qualcuno che
potrebbe diventare loro cliente per quello che vendono davvero. Togli: nomi di altre aziende o marchi,
ricerche di lavoro, fai-da-te, definizioni e curiosita', prodotti che non vendono.
NEL DUBBIO TIENI: buttare una ricerca buona fa sembrare il mercato piu' piccolo di quello che e'.
{elenco}
Rispondi SOLO con l'array JSON dei numeri da tenere.""")
    tieni = _json(r)
    if not isinstance(tieni, list):
        return righe[:20]
    return [righe[i] for i in tieni if isinstance(i, int) and 0 <= i < len(righe)]


def uniche(tenute):
    """Le varianti della stessa ricerca si contano una volta. Keyword Planner da' a «cessione
    quinto», «quinto cessione», «cessione di un quinto» lo stesso volume e lo stesso CPC: sono
    la stessa domanda. Sommate gonfiavano Hi Finance a 1,4 milioni di ricerche (5/10)."""
    viste, out = set(), []
    for r in tenute:
        chiave = (r["vol"], r["cpc"])
        if chiave in viste:
            continue
        viste.add(chiave)
        out.append(r)
    return out


def incasso(c, azienda):
    """Quanto INCASSA l'azienda da un cliente medio: il suo margine o la sua fattura, non il
    valore del bene. Per un intermediario del credito e' la provvigione, non il mutuo (5/10:
    il modello aveva scritto 5.000-100.000 € per Hi Finance, l'importo dei prestiti)."""
    r = cervello._chiedi(f"""Azienda: {azienda}. Cosa fa: {c.get('cosa_fa')}. Tipo: {c.get('tipo')}.
Quanto INCASSA questa azienda da UN cliente medio acquisito? Non il valore del bene o del finanziamento:
quello che resta a loro come fattura o provvigione, contando anche i riacquisti del primo anno se
il cliente torna. Dai un intervallo prudente in euro. Esempi: un intermediario del credito incassa
la provvigione (spesso 500-3.000 €), non l'importo del mutuo; un ristorante incassa un conto medio
per le visite di un anno; un'impresa edile la commessa media.
Rispondi SOLO con JSON: {{"min": intero, "max": intero, "perche": "una riga"}}""")
    d = _json(r)
    if isinstance(d, dict) and d.get("min") and d.get("max"):
        return int(d["min"]), int(d["max"]), str(d.get("perche") or "")[:160]
    return None


def conto(tenute, c, come_compra="contatto"):
    """Due scenari. Regge se il valore dei clienti copre fee e pubblicita'."""
    tenute = uniche(tenute)
    domanda = sum(r["vol"] for r in tenute)
    con_cpc = [r for r in tenute if r["cpc"] > 0]
    cpc = round(sum(r["cpc"] * r["vol"] for r in con_cpc) / sum(r["vol"] for r in con_cpc), 2) if con_cpc else None
    tmin = c.get("ticket_min") or c.get("ticket_max") or 0
    tmax = c.get("ticket_max") or c.get("ticket_min") or 0
    if not domanda or not cpc:
        return {"domanda": domanda, "cpc": cpc, "scenari": None}
    clic = min(BUDGET_ADS / cpc, domanda * QUOTA_MAX)
    scen = []
    for i, ticket in enumerate((tmin, tmax)):
        tasso = ACQUISTO[i] if come_compra == "online" else CONTATTO[i] * CHIUSURA[i]
        clienti = clic * tasso
        scen.append({"clic": round(clic), "clienti": round(clienti, 1), "valore": round(clienti * ticket), "ticket": ticket})
    return {"domanda": domanda, "cpc": cpc, "scenari": scen, "costo": BUDGET_ADS + FEE, "imbuto": come_compra}


def giudica(c, misurato, dove, idee=None):
    """SI / FORSE / NO, col perche' in una riga. Bocciare solo su fatti."""
    esc = (c.get("esclusione") or "").strip()
    if esc in ESCLUSIONI:
        return "NO", ESCLUSIONI[esc]
    if not c.get("cosa_fa"):
        return "FORSE", "il sito non si legge: non sappiamo abbastanza per dire di no"
    if misurato is None:
        return "FORSE", "Keyword Planner non ha risposto: misura da rifare"
    d, cpc, sc = misurato["domanda"], misurato["cpc"], misurato["scenari"]
    if idee is not None and idee < IDEE_MIN:
        # 5/10: «fisioterapista» da' zero idee, «idraulico» 80. Google nasconde i dati della
        # salute e di altri settori protetti: zero qui vuol dire «non ce lo dice», non «nessuno cerca»
        return "FORSE", f"Google non da' i volumi su queste parole ({idee} idee: settore protetto o parole rare): domanda non misurabile, non e' un no"
    if d < DOMANDA_MIN:
        return "NO", f"solo {d} ricerche/mese sulle parole dei loro clienti ({dove}): non c'e' una campagna da fare"
    if not sc:
        return "FORSE", f"{d} ricerche/mese ma senza CPC: conto non fattibile"
    costo = misurato["costo"]
    if not (c.get("ticket_min") or c.get("ticket_max")):
        return "FORSE", f"{d} ricerche/mese, CPC {cpc} €, ma il valore di un cliente non si stima: conto aperto"
    pru, pieno = sc
    base = f"{d} ricerche/mese ({dove}), CPC {cpc} €, cliente da {c.get('ticket_min') or '?'}-{c.get('ticket_max') or '?'} €"
    if pru["valore"] >= costo:
        return "SI", f"{base}: anche nel caso prudente {pru['clienti']} clienti/mese valgono {pru['valore']} € contro {costo} € di costo"
    if pieno["valore"] >= costo:
        return "FORSE", f"{base}: regge solo nel caso pieno ({pieno['valore']} € contro {costo} €), nel prudente {pru['valore']} €"
    if pieno["valore"] >= costo * NO_SOTTO:
        return "FORSE", f"{base}: nemmeno il caso pieno copre il costo ({pieno['valore']} € contro {costo} €), ma ci va vicino: da sentire"
    return "NO", f"{base}: anche nel caso pieno {pieno['clienti']} clienti/mese valgono {pieno['valore']} €, meno di meta' dei {costo} € di costo"


def valuta(p, kp=None):
    azienda = p.get("company") or p.get("name") or p.get("email")
    sito = p.get("website") or ("https://" + p["email"].split("@")[-1] if "@" in (p.get("email") or "") else "")
    vecchio = (p.get("enriched") or {}).get("google_fit") or {}
    testo = vecchio.get("sito_testo") or googlefit.leggi_sito(sito)
    c = googlefit.capisci(azienda, testo, googlefit.carica_fogli()[1]) if testo else {}
    if testo and not c:
        c = {k: vecchio.get(k) for k in ("cosa_fa", "tipo", "ticket_min", "ticket_max", "raggio", "zone_servite", "provincia", "esclusione")}
    semi, idee, tenute, misurato, errore, da_dove, come_compra = [], [], [], None, None, "zona", "contatto"
    geo, dove = _geo(c)
    if c.get("cosa_fa") and not (c.get("esclusione") in ESCLUSIONI):
        try:
            k, client, cid = kp or _kp()
            inc = incasso(c, azienda)
            if inc:
                c = {**c, "ticket_sito_min": c.get("ticket_min"), "ticket_sito_max": c.get("ticket_max"),
                     "ticket_min": inc[0], "ticket_max": inc[1], "ticket_fonte": "incasso stimato", "ticket_perche": inc[2]}
            semi, da_dove, come_compra = parole(c, azienda)
            geo, dove = _geo(c, da_dove)
            try:
                idee = misura(k, client, cid, semi, sito, geo)
            except Exception:                                        # noqa: BLE001
                import time
                time.sleep(8)                                        # un intoppo di Google non e' un verdetto: si riprova una volta
                idee = misura(k, client, cid, semi, sito, geo)
            tenute = filtra(idee, c, azienda)
            misurato = conto(tenute, c, come_compra)
        except Exception as e:                                       # noqa: BLE001
            errore = str(e)[:200]
    v, motivo = giudica(c, misurato, dove, len(idee) if misurato is not None else None)
    return {
        "verdetto": v, "motivo": motivo, "cosa_fa": c.get("cosa_fa"), "tipo": c.get("tipo"),
        "esclusione": c.get("esclusione") or None, "dove": dove, "raggio": c.get("raggio"),
        "ticket_min": c.get("ticket_min"), "ticket_max": c.get("ticket_max"), "ticket_fonte": c.get("ticket_fonte") or "stima",
        "ticket_perche": c.get("ticket_perche"),
        "da_dove": da_dove, "come_compra": come_compra, "parole_cliente": semi, "idee_google": len(idee), "parole_tenute": len(tenute), "parole_misurate": tenute[:15], "conto": misurato,
        "due_cose_scomode": (c.get("due_cose_scomode") or [])[:2], "errore": errore,
        "provenienza": "domanda e CPC: Google Keyword Planner dal vivo, varianti contate una volta; valore di un cliente: " + (c.get("ticket_fonte") or "stima"),
        "fatto_il": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
    }


def salva(p, fit):
    e = dict(p.get("enriched") or {})
    e["google_fit_v2"] = fit
    sb("PATCH", f"/rest/v1/prospects?id=eq.{p['id']}", {"enriched": e})


def main():
    prova = "--prova" in sys.argv
    if "--uno" in sys.argv:
        email = sys.argv[sys.argv.index("--uno") + 1]
        p = (sb("GET", f"/rest/v1/prospects?select=*&email=eq.{email}") or [None])[0]
        if not p:
            sys.exit("non trovato")
        fit = valuta(p)
        print(json.dumps({k: v for k, v in fit.items() if k != "parole_misurate"}, ensure_ascii=False, indent=1))
        print("parole misurate:", [f"{r['kw']} {r['vol']}" for r in fit["parole_misurate"]])
        if not prova:
            salva(p, fit)
        return
    ids = json.load(open(sys.argv[sys.argv.index("--ids") + 1]))
    kp = _kp()
    from concurrent.futures import ThreadPoolExecutor

    def uno(i):
        p = (sb("GET", f"/rest/v1/prospects?select=*&id=eq.{i}") or [None])[0]
        if not p:
            return i, None
        fit = valuta(p, kp)
        if not prova:
            salva(p, fit)
        return i, (p.get("company") or p.get("email"), fit)
    with ThreadPoolExecutor(max_workers=4) as pool:
        esiti = list(pool.map(uno, ids))
    conti = {}
    for i, x in esiti:
        if not x:
            continue
        nome, fit = x
        conti[fit["verdetto"]] = conti.get(fit["verdetto"], 0) + 1
        print(f"  {fit['verdetto']:6} {str(nome)[:32]:32} {fit['motivo'][:150]}")
    print("fit nuovo:", conti, "(prova)" if prova else "")


if __name__ == "__main__":
    main()
