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
def capisci(azienda, sito_testo, settori):
    lista = ", ".join(sorted(settori))
    prompt = f"""Sei l'analista di Studio Galilei, agenzia Google Ads. Devi classificare
un'azienda che ha risposto a una nostra mail, leggendo il suo sito.

Rispondi SOLO con un JSON su una riga, con queste chiavi:
{{"settore": una voce ESATTA fra quelle qui sotto, o "altro",
 "provincia": la provincia italiana della sede (nome della citta' capoluogo, es. "Bergamo", "Milano", "Roma"), o "" se non si capisce,
 "tipo": "B2B" o "B2C",
 "ticket": stima in euro di quanto vale un cliente per loro (numero intero),
 "cosa_fa": una frase secca su cosa vende e a chi,
 "esclusione": "" oppure uno fra "agenzia" (marketing/comunicazione/web agency/lead generation), "portale", "catena", "franchising", "multinazionale", "onlus", "privacy"}}

I settori possibili: {lista}

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


# ── il verdetto, con i criteri del 18/8 ───────────────────────────
def verdetto(c, zona, rec):
    motivi = []
    if c.get("esclusione"):
        return "NO", f"{c['esclusione']}: non e' un cliente possibile"
    if not c.get("settore") or c.get("settore") == "altro":
        motivi.append("settore non fra quelli misurati")
    if zona is None:
        motivi.append("zona non misurata")
    elif zona["verdetto"] == "ROSSO":
        return "NO", f"provincia rossa: {zona['domanda_mese']} ricerche/mese, meno di 2 clic al giorno"
    elif zona["verdetto"] == "GIALLO":
        motivi.append(f"provincia gialla ({zona['domanda_mese']} ricerche/mese): si va se il ticket e' alto")
    if rec is not None:
        if rec["recensioni"] < 5:
            return "NO", f"meno di 5 recensioni ({rec['recensioni']}): troppo piccolo"
        if rec["recensioni"] < 20:
            motivi.append(f"{rec['recensioni']} recensioni: piccolo, forse regge un pilot")
    else:
        motivi.append("recensioni non misurate")
    if motivi:
        return "PARZIALE", "; ".join(motivi)
    return "SI", f"provincia verde ({zona['domanda_mese']} ricerche/mese, CPC {zona['cpc']} €)" + (f", {rec['recensioni']} recensioni" if rec else "")


def valuta(p, zone, settori):
    azienda = p.get("company") or p.get("name") or p.get("email")
    sito = p.get("website") or ("https://" + p["email"].split("@")[-1] if "@" in (p.get("email") or "") else "")
    testo = leggi_sito(sito)
    c = capisci(azienda, testo, settori)
    zona = zone.get((c.get("settore"), _norm(c.get("provincia")))) if c.get("settore") and c.get("provincia") else None
    # le recensioni costano (SearchAPI): non si chiedono per chi e' gia' fuori
    rec = None if c.get("esclusione") else recensioni(azienda, c.get("provincia", ""))
    v, motivo = verdetto(c, zona, rec)
    fit = {
        "verdetto": v, "motivo": motivo, "settore": c.get("settore"), "provincia": c.get("provincia"),
        "tipo": c.get("tipo"), "ticket": c.get("ticket"), "cosa_fa": c.get("cosa_fa"), "esclusione": c.get("esclusione") or None,
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
