#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""CLARA RIEMPIE QUELLO CHE SA (24/9/2026).

Dre: «i chip "Cosa manca" li puo' chiudere lei per sito, settore e chi sono;
a me restano referente, ruolo, telefono. E ricerca anche su internet, ma in
modo preciso, no slop». Quindi:
- SETTORE e CHI SONO: dal Google Fit (letto dal sito della persona), se vuoti.
- SITO: se manca, UNA ricerca (SearchAPI) con nome e citta'. Si accetta solo
  se il dominio contiene una parola distintiva del nome dell'azienda E la
  home del sito contiene il nome. Se non e' certo, resta vuoto: meglio un
  chip vuoto che un sito sbagliato.
Ogni campo riempito porta enriched.<campo> = 'auto' (si vede in scheda) e
il sync non lo tocca. Referente, ruolo, telefono, LinkedIn non si toccano mai.

USO
  python3 scripts/arricchisci.py            riempie (max 40 per giro)
  python3 scripts/arricchisci.py --prova    mostra e non scrive
"""
import json
import os
import re
import sys
import urllib.parse
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from stanza import sb, env                                  # noqa: E402

GENERICHE = {"srl", "spa", "snc", "sas", "srls", "group", "italia", "italy", "studio", "societa", "azienda", "impresa", "service",
             "servizi", "the", "and", "di", "del", "della", "dei", "con", "per", "srl.", "s.r.l.", "s.p.a.", "sas.", "ditta", "officina"}


def parole(nome):
    return [w for w in re.findall(r"[a-z0-9]{4,}", (nome or "").lower()) if w not in GENERICHE]


def cerca_sito(azienda, citta):
    chiave = env("SEARCHAPI_KEY")
    if not chiave or not azienda:
        return None, "senza chiave o nome"
    q = f'"{azienda}" {citta or ""} sito ufficiale'.strip()
    url = "https://www.searchapi.io/api/v1/search?" + urllib.parse.urlencode({"engine": "google", "q": q, "api_key": chiave, "hl": "it", "gl": "it", "num": 5})
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "clara/1.0"}), timeout=40) as r:
            d = json.load(r)
    except Exception as e:                                        # noqa: BLE001
        return None, f"ricerca fallita ({str(e)[:50]})"
    tok = parole(azienda)
    if not tok:
        return None, "nome troppo generico"
    for ris in (d.get("organic_results") or [])[:5]:
        link = ris.get("link") or ""
        dom = urllib.parse.urlparse(link).netloc.lower().replace("www.", "")
        if any(x in dom for x in ("facebook.", "linkedin.", "instagram.", "paginegialle", "pagine-gialle", "ufficiocamerale", "reportaziende", "cribis", "atoka", "companyreports", "registroimprese", "youtube.", "wikipedia")):
            continue
        if not any(t in dom.replace("-", "") for t in tok):
            continue
        # la conferma: la home nomina l'azienda
        try:
            with urllib.request.urlopen(urllib.request.Request(f"https://{dom}", headers={"User-Agent": "Mozilla/5.0 (clara)"}), timeout=20) as r:
                home = r.read(200000).decode("utf-8", "replace").lower()
        except Exception:                                          # noqa: BLE001
            continue
        if sum(t in home for t in tok) >= max(1, min(2, len(tok))):
            return dom, "ricerca + home confermata"
    return None, "nessun risultato certo"


def main():
    prova = "--prova" in sys.argv
    righe = sb("GET", "/rest/v1/prospects?select=id,company,name,city,website,sector,descrizione,enriched,stage,fuori,awaiting_us"
                      "&stage=neq.nuovo&or=(website.is.null,sector.is.null,descrizione.is.null)&order=last_reply_at.desc.nullslast&limit=40") or []
    fatti, cercati = 0, 0
    for p in righe:
        arr = dict(p.get("enriched") or {})
        fit = arr.get("google_fit") or {}
        patch = {}
        if not (p.get("sector") or "").strip() and fit.get("settore") and fit["settore"] != "altro":
            patch["sector"] = fit["settore"]; arr["sector"] = "auto"
        cosa_fa = (fit.get("cosa_fa") or "").strip()
        # «non specificato nel sito» non e' una descrizione: meglio il chip vuoto
        if re.match(r"^(non |il sito|sito non|nessun|non si capisce|n/a|\?)", cosa_fa, re.I):
            cosa_fa = ""
        if not (p.get("descrizione") or "").strip() and cosa_fa:
            patch["descrizione"] = fit["cosa_fa"].strip()[:400]; arr["descrizione"] = "auto"
        if not (p.get("website") or "").strip() and p.get("company") and arr.get("sito_cercato") != "si" and cercati < 15:
            cercati += 1
            dom, come = cerca_sito(p["company"], p.get("city"))
            arr["sito_cercato"] = "si"
            if dom:
                patch["website"] = dom; arr["website"] = "auto"
            print(f"  sito per {p['company'][:30]}: {dom or '-'} ({come})")
        if not patch and arr.get("sito_cercato") != "si":
            continue
        nome = (p.get("company") or p.get("name") or "")[:30]
        if patch:
            print(f"  {nome}: " + ", ".join(f"{k}={str(v)[:40]}" for k, v in patch.items()))
        if prova:
            continue
        patch["enriched"] = arr
        sb("PATCH", f"/rest/v1/prospects?id=eq.{p['id']}", patch)
        fatti += 1 if len(patch) > 1 else 0
    print(f"arricchisci: {fatti} schede riempite, {cercati} siti cercati, {len(righe)} guardate")


if __name__ == "__main__":
    main()
