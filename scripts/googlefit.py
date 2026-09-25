#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""IL GOOGLE FIT — Clara lo fa da sola su chi risponde (9/9/2026).

Dre: «si passa solo dopo che hanno superato il Google Fit, che dovra' fare
Clara in automatico». E' il filtro del 18/8 (docs nel vault: GOOGLE FIT,
criteri ricavati da chi paga davvero), portato in cloud e applicato a ogni
risposta nuova, prima che parta il pacchetto (analisi + bozza).

COSA FA, PER OGNI AZIENDA «IN ARRIVO» (ha risposto, l'analisi non e' partita)
1. legge la home del sito (poche righe, senza fronzoli);
2. chiede al cervello: sottosettore (fra i 141 del Foglio Settori), provincia,
   B2B o B2C, ticket, e se e' agenzia, portale, catena o franchising;
3. guarda il Foglio Zone (settore x provincia): verde, giallo o rosso, con
   domanda, CPC e budget suggerito;
4. se c'e' SEARCHAPI_KEY, conta le recensioni su Google Maps;
5. verdetto: SI', PARZIALE o NO, con il motivo scritto, e lo salva in
   enriched.google_fit. Da li' lo leggono la scheda, il foglio e le bozze
   (che mettono nel messaggio il numero della zona: «a Bergamo ci sono 260
   ricerche al mese per quello che fate»).

Non manda niente e non chiude nessuno: un NO resta «in arrivo» col motivo,
e Dre decide. Il pedaggio e' l'invio dell'analisi.

USO
  python3 scripts/googlefit.py              tutti quelli in arrivo senza fit
  python3 scripts/googlefit.py --prova      mostra e non scrive
  python3 scripts/googlefit.py --uno EMAIL  uno solo (anche se ce l'ha gia')
"""

import csv
import datetime
import html
import json
import os
import re
import sys
import urllib.parse
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from stanza import sb, env                                 # noqa: E402
import cervello                                            # noqa: E402

RADICE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
QUANTI = 20          # per giro: il resto al giro dopo (ogni 15 minuti)

# ── i fogli ──────────────────────────────────────────────────────
def carica_fogli():
    zone = {}
    for r in csv.DictReader(open(os.path.join(RADICE, "data", "foglio_zone.csv"), encoding="utf-8")):
        zone[(r["settore"], _norm(r["provincia"]))] = r
    settori = {r["settore"]: r for r in csv.DictReader(open(os.path.join(RADICE, "data", "foglio_settori.csv"), encoding="utf-8"))}
    return zone, settori


def _norm(s):
    s = (s or "").lower()
    s = re.sub(r"citt[aà] metropolitana di |provincia di |libero consorzio comunale di |provincia autonoma di ", "", s)
    s = s.replace("roma capitale", "roma").replace("reggio nell'emilia", "reggio emilia").replace("forlì-cesena", "forli-cesena")
    return re.sub(r"[^a-z]", "", s)


# ── il sito ──────────────────────────────────────────────────────
def leggi_sito(url):
    if not url:
        return ""
    if not url.startswith("http"):
        url = "https://" + url
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (clara-dashboard)"})
        with urllib.request.urlopen(req, timeout=10) as r:
            raw = r.read(300_000).decode("utf-8", errors="replace")
    except Exception:
        return ""
    raw = re.sub(r"<(script|style|noscript)[^>]*>.*?</\1>", " ", raw, flags=re.S | re.I)
    titolo = re.search(r"<title[^>]*>(.*?)</title>", raw, flags=re.S | re.I)
    descr = re.search(r'<meta[^>]+name=["\']description["\'][^>]+content=["\']([^"\']*)', raw, flags=re.I)
    testo = html.unescape(re.sub(r"<[^>]+>", " ", raw))
    testo = " ".join(testo.split())
    pezzi = []
    if titolo:
        pezzi.append("TITOLO: " + " ".join(titolo.group(1).split()))
    if descr:
        pezzi.append("DESCRIZIONE: " + descr.group(1))
    pezzi.append(testo[:3500])
    return "\n".join(pezzi)


# ── il cervello: settore, provincia, natura ───────────────────────
def lezioni_dai_persi():
    """I PERSI INSEGNANO AL FIT (Dre, 24/9): il motivo di ogni perso, con le parole
    del cliente quando ci sono, torna qui come bandierina per i prossimi simili."""
    try:
        righe = sb("GET", "/rest/v1/prospects?select=sector,lost_reason,notes&lost_reason=not.is.null&order=updated_at.desc&limit=25") or []
    except Exception:                                             # noqa: BLE001
        return ""
    if not righe:
        return ""
    voci = [f"- {(r.get('sector') or 'settore ?')[:30]}: {r['lost_reason'][:120]}" for r in righe if r.get("lost_reason")]
    return ("\nCOSA ABBIAMO IMPARATO DAI PERSI (motivi veri, recenti): usali per le due cose scomode e per l'esclusione, "
            "se il caso somiglia:\n" + "\n".join(voci[:25]) + "\n") if voci else ""


def capisci(azienda, sito_testo, settori):
    lista = ", ".join(sorted(settori))
    persi = lezioni_dai_persi()
    prompt = f"""Sei l'analista di Studio Galilei, agenzia Google Ads di Silea (TV).
Devi capire un'azienda che ha risposto a una nostra mail, leggendo il suo sito.

REGOLE (non negoziabili)
- Il dato prima dell'interpretazione. Se una cosa non sta scritta nel sito, non la sai.
- Niente falsa precisione: i valori stimati vanno a intervallo, non a numero secco.
- Non attribuire mai all'azienda un numero che non ha scritto da nessuna parte.
- Se il sito non si legge o dice troppo poco, dillo invece di inventare.

Rispondi SOLO con un JSON su una riga, con queste chiavi:
{{"settore": una voce ESATTA fra quelle qui sotto, o "altro",
 "provincia": la provincia italiana della SEDE (nome del capoluogo, es. "Bergamo", "Milano"), o "" se non si capisce,
 "raggio": dove vendono DAVVERO, che spesso non e' dove hanno la sede. Una fra
   "citta'" (solo il comune e i paesi attorno), "provincia", "regione",
   "piu' regioni", "italia", "estero". Leggilo da quello che dice il sito
   (zone servite, sedi, spedizioni, "in tutta Italia"), non dedurlo dalla sede.
 "zone_servite": array delle province o regioni che il sito nomina esplicitamente
   come coperte, in ordine di importanza; array vuoto se il sito non lo dice.
 "tipo": "B2B" o "B2C",
 "ticket_min": stima bassa in euro di quanto vale un cliente per loro (intero),
 "ticket_max": stima alta in euro (intero),
 "ticket_fonte": "sito" se i prezzi stanno scritti sul sito, "stima" se lo stai ipotizzando tu dal settore,
 "cosa_fa": una frase secca su cosa vende e a chi,
 "da_sistemare": quello che conviene mettere a posto sul sito PRIMA di spendere, scelta fra
   "niente", "manca un modo per contattarli", "sito vecchio o lento",
   "nessun prezzo ne' offerta chiara", "vendono solo di persona", "non si capisce cosa vendono".
   Non e' un motivo per bocciare: quasi tutti i clienti, capito il ritorno, il sito lo rifanno
   o lo migliorano. Serve solo a sapere da dove si parte.
 "vendita_possibile_online": true se quello che vendono si puo' comprare o richiedere dal sito,
   false se la vendita avviene solo di persona o per telefono,
 "due_cose_scomode": array di due stringhe brevi: le due ragioni per cui questo cliente
   potrebbe NON funzionare con Google Ads. Sempre due, anche quando l'azienda ti convince.
 "come_lo_cercano": come si arriva a comprare quello che vendono. Una fra
   "ricerca" (la gente lo cerca su Google con parole chiare: un idraulico, una casa, un infisso),
   "impulso" (si compra perche' lo si vede, non perche' lo si cerca: meglio social o display),
   "da_spiegare" (prodotto nuovo o che va capito prima di poterlo cercare: nessuno digita il suo nome),
   "per_pubblico" (il cliente si riconosce bene per eta', interessi o zona, ma quasi mai da una parola chiave).
 "esclusione": "" oppure uno fra "agenzia" (marketing/comunicazione/web agency/lead generation), "portale", "catena", "franchising" (SOLO i network Tecnocasa, Tecnorete, Tempocasa: un affiliato Century 21, RE/MAX, Coldwell Banker o simili NON e' un'esclusione, decide il suo marketing e va bene, Dre 25/9), "multinazionale", "onlus", "privacy"}}

I settori possibili: {lista}
{persi}
AZIENDA: {azienda}
SITO:
{sito_testo or '(sito non leggibile)'}
"""
    testo = cervello._chiedi(prompt) or ""
    m = re.search(r"\{.*\}", testo, flags=re.S)
    if not m:
        return {}
    try:
        return json.loads(m.group(0))
    except json.JSONDecodeError:
        return {}


# ── le recensioni (se c'e' SearchAPI) ─────────────────────────────
def recensioni(nome, provincia):
    chiave = env("SEARCHAPI_KEY")
    if not chiave or not nome:
        return None
    q = f"{nome} {provincia}".strip()
    url = "https://www.searchapi.io/api/v1/search?" + urllib.parse.urlencode({"engine": "google_maps", "q": q, "api_key": chiave, "hl": "it", "gl": "it"})
    try:
        with urllib.request.urlopen(url, timeout=20) as r:
            d = json.loads(r.read())
        for posto in (d.get("local_results") or d.get("places") or [])[:3]:
            if posto.get("reviews") is not None:
                return {"recensioni": int(posto.get("reviews") or 0), "voto": posto.get("rating")}
    except Exception:
        return None
    return None


# ── il verdetto: i criteri del 18/8 con le regole di Carlo (21/9) ──
# Dre, 21/9: il fit deve ragionare come lo studio di fattibilita' di Carlo.
# Tre cose in piu' rispetto a prima:
#   1. ogni numero porta scritto DA DOVE VIENE (misurato / dal sito / stima)
#   2. si rema contro almeno due volte, anche quando il verdetto e' SI
#   3. niente falsa precisione: il ticket e' un intervallo, mai un numero secco
# Il verdetto resta SI / PARZIALE / NO, perche' e' quello che leggono la
# scheda, il foglio e le bozze.

def _provenienza(c, zona, rec):
    """Da dove viene ogni numero. Le tre categorie di Carlo, niente di piu'."""
    righe = []
    if zona:
        dove = "Google Keyword Planner"
        if zona.get("su"):
            dove += f" ({zona['su']})"
        righe.append({"voce": "domanda e CPC dove vendono", "valore": f"{int(float(zona['domanda_mese']))} ricerche/mese, CPC {zona['cpc']} €",
                      "fonte": "misurato", "dove": dove})
    if rec is not None:
        righe.append({"voce": "recensioni", "valore": f"{rec['recensioni']}" + (f", voto {rec['voto']}" if rec.get("voto") else ""),
                      "fonte": "misurato", "dove": "Google Maps"})
    tmin, tmax = c.get("ticket_min"), c.get("ticket_max")
    if tmin or tmax:
        righe.append({"voce": "valore di un cliente", "valore": _ticket_scritto(c),
                      "fonte": "dal sito" if c.get("ticket_fonte") == "sito" else "stima",
                      "dove": "prezzi sul sito" if c.get("ticket_fonte") == "sito" else "riferimento di settore"})
    if c.get("settore"):
        righe.append({"voce": "settore", "valore": c["settore"], "fonte": "dal sito", "dove": "lettura della home"})
    return righe


def _ticket_scritto(c):
    """Intervallo, mai un numero secco (regola di Carlo)."""
    tmin, tmax = c.get("ticket_min"), c.get("ticket_max")
    if tmin and tmax and tmin != tmax:
        return f"fra {int(tmin):,} e {int(tmax):,} €".replace(",", ".")
    solo = tmin or tmax
    return f"intorno a {int(solo):,} €".replace(",", ".") if solo else "non stimabile"


def verdetto(c, zona, rec):
    motivi = []
    if c.get("esclusione"):
        return "NO", f"{c['esclusione']}: non e' un cliente possibile"
    if not c.get("settore") or c.get("settore") == "altro":
        motivi.append("settore non fra quelli misurati")
    # la zona mancante NON e' un difetto del cliente: e' un dato che non abbiamo (Dre, 21/9).
    # Prima finivano PARZIALE aziende sane solo perche' la loro combinazione non era nel foglio.
    if zona is None:
        pass
    elif zona["verdetto"] == "ROSSO":
        return "NO", f"provincia rossa: {zona['domanda_mese']} ricerche/mese, meno di 2 clic al giorno"
    elif zona["verdetto"] == "GIALLO":
        motivi.append(f"provincia gialla ({zona['domanda_mese']} ricerche/mese): si va se il ticket e' alto")
    # ── le red flag di Carlo (23/9/2026) ──────────────────────────
    # 4 e 8: ticket troppo basso, la nostra fee (1.200 €/mese) pesa piu' della campagna
    tmax = c.get("ticket_max") or c.get("ticket_min") or 0
    if tmax and tmax < 100:
        return "NO", f"ticket sotto i 100 € ({_ticket_scritto(c)}): la fee pesa piu' della campagna"
    if tmax and tmax < 300:
        motivi.append(f"ticket basso ({_ticket_scritto(c)}): la fee pesa, si va solo con volumi alti")
    # 6: competizione alta rispetto al valore di un cliente (33 clic per cliente, al 3% di conversione)
    if zona and tmax and float(zona.get("cpc") or 0) * 33 > tmax:
        motivi.append(f"CPC {zona['cpc']} € alto rispetto al ticket ({_ticket_scritto(c)}): un cliente costa piu' di quanto vale")
    # 9, 10, 11: se nessuno lo cerca su Google, Google Ads non e' il servizio giusto
    come = (c.get("come_lo_cercano") or "ricerca").lower()
    if come in ("impulso", "da_spiegare", "per_pubblico"):
        spiega = {"impulso": "si compra d'impulso, non si cerca: meglio social o display",
                  "da_spiegare": "prodotto da spiegare prima che qualcuno lo cerchi",
                  "per_pubblico": "il cliente si riconosce per pubblico, non per parola chiave"}[come]
        if (zona and zona["verdetto"] == "GIALLO") or (tmax and tmax < 300):
            return "NO", f"{spiega}; e in piu' " + (f"provincia gialla" if zona and zona["verdetto"] == "GIALLO" else "ticket basso")
        motivi.append(spiega)
    if rec is not None:
        if rec["recensioni"] < 5:
            return "NO", f"meno di 5 recensioni ({rec['recensioni']}): troppo piccolo"
        if rec["recensioni"] < 20:
            motivi.append(f"{rec['recensioni']} recensioni: piccolo, forse regge un pilot")
    else:
        motivi.append("recensioni non misurate")
    # il sito NON declassa (Dre, 21/9): i clienti, capito il ritorno, lo rifanno.
    # Resta scritto nel fit come punto di partenza per l'avvio, non come bocciatura.
    if motivi:
        return "PARZIALE", "; ".join(motivi)
    # il SI si puo' dare anche senza zona misurata: la zona non e' un requisito (Dre, 21/9)
    pezzi = []
    if zona:
        pezzi.append(f"dove vendono ci sono {int(float(zona['domanda_mese']))} ricerche/mese, CPC {zona['cpc']} €")
    if rec:
        pezzi.append(f"{rec['recensioni']} recensioni")
    if c.get("cosa_fa"):
        pezzi.append("settore e mercato in linea")
    return "SI", "; ".join(pezzi) if pezzi else "nessun motivo di scarto"


def _zona_sul_raggio(c, zone):
    """La domanda si misura dove l'azienda vende davvero, non dove ha la sede (Dre, 21/9).

    Un'azienda con sede a Brescia che lavora in tutta la Lombardia non ha la
    domanda di Brescia. Si sommano le zone che il sito dichiara di servire; se
    non ne dichiara nessuna, si usa la provincia della sede. Un raggio nazionale
    o estero non si misura con un foglio provinciale: si dice e basta.
    """
    settore = c.get("settore")
    if not settore or settore == "altro":
        return None
    raggio = (c.get("raggio") or "").strip()
    if raggio in ("italia", "estero"):
        return None                      # fuori dalla scala del foglio: non si finge di saperlo
    luoghi = [x for x in (c.get("zone_servite") or []) if x] or [c.get("provincia")]
    trovate = [zone[(settore, _norm(l))] for l in luoghi if l and (settore, _norm(l)) in zone]
    if not trovate:
        return None
    if len(trovate) == 1:
        return trovate[0]
    # piu' zone servite: la domanda si somma, il CPC e' la media, il verdetto lo da' il totale
    domanda = sum(float(z["domanda_mese"]) for z in trovate)
    cpc = sum(float(z["cpc"]) for z in trovate) / len(trovate)
    peggiore = "ROSSO" if all(z["verdetto"] == "ROSSO" for z in trovate) else (
               "VERDE" if any(z["verdetto"] == "VERDE" for z in trovate) else "GIALLO")
    return {"domanda_mese": domanda, "cpc": round(cpc, 2), "verdetto": peggiore,
            "budget_giorno": sum(float(z["budget_giorno"]) for z in trovate),
            "aziende_sostenibili": sum(float(z["aziende_sostenibili"]) for z in trovate),
            "su": f"{len(trovate)} zone servite"}


def valuta(p, zone, settori):
    azienda = p.get("company") or p.get("name") or p.get("email")
    sito = p.get("website") or ("https://" + p["email"].split("@")[-1] if "@" in (p.get("email") or "") else "")
    testo = leggi_sito(sito)
    c = capisci(azienda, testo, settori)
    zona = _zona_sul_raggio(c, zone)
    # le recensioni costano (SearchAPI): non si chiedono per chi e' gia' fuori
    rec = None if c.get("esclusione") else recensioni(azienda, c.get("provincia", ""))
    v, motivo = verdetto(c, zona, rec)
    fit = {
        "verdetto": v, "motivo": motivo, "settore": c.get("settore"), "provincia": c.get("provincia"),
        "tipo": c.get("tipo"), "cosa_fa": c.get("cosa_fa"), "esclusione": c.get("esclusione") or None,
        # il valore di un cliente e' un intervallo, e si sa da dove viene (Carlo, 21/9)
        "ticket": _ticket_scritto(c), "ticket_min": c.get("ticket_min"), "ticket_max": c.get("ticket_max"),
        "ticket_fonte": c.get("ticket_fonte") or "stima",
        # cosa conviene sistemare sul sito in fase di avvio: non boccia nessuno (Dre, 21/9)
        "da_sistemare": (c.get("da_sistemare") or None) if (c.get("da_sistemare") or "") != "niente" else None,
        "vendita_possibile_online": c.get("vendita_possibile_online"),
        # dove vendono davvero: e' quello che decide su che zona si misura la domanda
        "raggio": c.get("raggio") or None,
        "zone_servite": c.get("zone_servite") or [],
        "due_cose_scomode": (c.get("due_cose_scomode") or [])[:2],
        # da dove viene ogni numero: misurato, dal sito, stima
        "provenienza": _provenienza(c, zona, rec),
        "zona": {"verdetto": zona["verdetto"], "domanda_mese": int(float(zona["domanda_mese"])), "cpc": float(zona["cpc"]),
                 "budget_giorno": float(zona["budget_giorno"]), "aziende_sostenibili": float(zona["aziende_sostenibili"])} if zona else None,
        "recensioni": rec, "sito_letto": bool(testo), "letto_il": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    }
    return fit


def main():
    prova = "--prova" in sys.argv
    zone, settori = carica_fogli()
    if "--uno" in sys.argv:
        email = sys.argv[sys.argv.index("--uno") + 1]
        righe = sb("GET", f"/rest/v1/prospects?select=id,email,name,company,website,sector,city,enriched&email=eq.{urllib.parse.quote(email)}")
    else:
        righe = sb("GET", "/rest/v1/prospects?select=id,email,name,company,website,sector,city,enriched"
                          "&fuori=eq.false&analysis_sent=eq.false&awaiting_us=eq.true&stage=neq.nuovo&passato_a=is.null"
                          "&or=(classificazione.is.null,classificazione.not.in.(negativo,fuori_target,soppresso))"
                          "&order=last_reply_at.desc&limit=200") or []
        righe = [p for p in righe if not (p.get("enriched") or {}).get("google_fit")]
        # anche i negativi cortesi degli ultimi 45 giorni: il gigante buono (bozze.py)
        # lascia loro l'analisi, quindi l'analisi deve esistere
        da = (datetime.date.today() - datetime.timedelta(days=45)).isoformat()
        negativi = sb("GET", "/rest/v1/prospects?select=id,email,name,company,website,sector,city,enriched"
                             f"&fuori=eq.false&analysis_sent=eq.false&classificazione=eq.negativo&last_reply_at=gte.{da}"
                             "&order=last_reply_at.desc&limit=100") or []
        righe += [p for p in negativi if not (p.get("enriched") or {}).get("google_fit")]
        righe = righe[:QUANTI]
    fatti = 0
    for p in righe:
        nome = p.get("company") or p.get("name") or p.get("email")
        try:
            fit = valuta(p, zone, settori)
        except Exception as e:                      # noqa: BLE001
            print(f"  {'?':8} {str(nome)[:34]:34} non valutata: {str(e)[:70]}")
            continue
        print(f"  {fit['verdetto']:8} {nome[:34]:34} {fit.get('settore') or '?':24} {fit.get('provincia') or '?':14} {fit['motivo'][:70]}")
        if prova:
            continue
        patch = {"enriched": {**(p.get("enriched") or {}), "google_fit": fit}}
        if not p.get("sector") and fit.get("settore") and fit["settore"] != "altro":
            patch["sector"] = fit["settore"]
        if not p.get("provincia_fit") and fit.get("provincia"):
            pass    # la provincia sta dentro enriched.google_fit: «city» e' la citta', non la provincia
        sb("PATCH", f"/rest/v1/prospects?id=eq.{p['id']}", patch)
        fatti += 1
    print(f"google fit: {fatti} valutati, {len(righe)} nel giro")


if __name__ == "__main__":
    main()
