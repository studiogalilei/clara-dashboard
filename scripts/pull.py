#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""IL PULL: si raccoglie prima, si ragiona dopo (Dre, 21/9/2026).

Per ogni dominio delle liste in attesa (tabella raccolta, raccolto_il vuoto):
  1. Transparency Center: fa ads? quanti annunci, da quanti giorni   (1 credito)
  2. scheda Google Maps: trovata? recensioni, voto                    (1 credito)
  3. i testi delle recensioni, fino a 20                              (1 credito, solo se c'e' la scheda)
  4. il sito: home, servizi, prezzi, testo pulito                     (0 crediti, in parallelo)
Solo dati grezzi. Nessun verdetto: quello lo fa il fit, dopo, su tutto insieme.

Il limite vero e' la quota SearchAPI (7.000 chiamate/ora sul piano), non il
parallelismo: le chiamate a crediti vanno in fila con la pausa di giugno, il
sito si legge con 16 thread perche' non costa niente.

USO
  pull.py --max 1100          un lotto (il direttore, ogni 20 min, sta nei 40)
  pull.py --campione 25       25 domini per lista, li scrive e li stampa
  pull.py --stato             quanti fatti, quanti mancano, crediti spesi
"""
import concurrent.futures as cf
import datetime
import html
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from stanza import sb, env                                 # noqa: E402

KEY = env("SEARCHAPI_KEY")
# il ritmo lo detta il piano SearchAPI (21/9: da 7.000 a 2.000 chiamate l'ora
# col piano da 40$). Si legge dal conto all'avvio, all'85% del limite.
def _limite_orario():
    try:
        return json.loads(urllib.request.urlopen(f"https://www.searchapi.io/api/v1/me?api_key={KEY}", timeout=30).read())["api_usage"]["hourly_rate_limit"]
    except Exception:
        return 2000
PAUSA = 3600.0 / (_limite_orario() * 0.85)
UA = {"User-Agent": "Mozilla/5.0 (Macintosh) StudioGalilei/1.0"}
import threading
_ultima = [0.0]
_usati = [0]
_lock = threading.Lock()


def cerca(engine, **p):
    """Una chiamata SearchAPI, con la pausa della quota. Il 429 dopo 3 tentativi
    chiede al conto se sono finiti i crediti (imparato il 18/8)."""
    p.update({"engine": engine, "api_key": KEY})
    for t in range(3):
        with _lock:
            a = PAUSA - (time.time() - _ultima[0])
            if a > 0:
                time.sleep(a)
            _ultima[0] = time.time()
        try:
            d = json.loads(urllib.request.urlopen(
                "https://www.searchapi.io/api/v1/search?" + urllib.parse.urlencode(p), timeout=60).read())
            _usati[0] += 1
            return d
        except Exception as e:
            if "429" in str(e) and t == 2 and crediti_residui() <= 0:
                print("STOP: crediti SearchAPI finiti. Ricaricare su searchapi.io: il pull riparte da solo al giro dopo.", flush=True)
                raise SystemExit(0)
            if t == 2:
                return {"_errore": str(e)[:120]}
            time.sleep(3 * (t + 1))
    return {}


def conta(filtro):
    """Quante righe risponde una tabella, leggendo Content-Range (PostgREST taglia il corpo a 1000)."""
    from stanza import URL, CHIAVE
    req = urllib.request.Request(URL.rstrip("/") + filtro + "&limit=1", headers={
        "apikey": CHIAVE, "Authorization": "Bearer " + CHIAVE, "Prefer": "count=exact"})
    with urllib.request.urlopen(req, timeout=40) as r:
        return int((r.headers.get("Content-Range") or "*/0").split("/")[-1])


def crediti_residui():
    try:
        a = json.loads(urllib.request.urlopen(f"https://www.searchapi.io/api/v1/me?api_key={KEY}", timeout=30).read())["account"]
        return a["monthly_allowance"] - a["current_month_usage"]
    except Exception:
        return 1


# ── i tre pull a crediti ──────────────────────────────────────────
def fa_ads(dom):
    d = cerca("google_ads_transparency_center", domain=dom, region="IT")
    if "_errore" in d:
        return {"errore": "ads: " + d["_errore"]}
    ann = d.get("ad_creatives") or []
    if not ann:
        return {"fa_ads": False, "annunci": 0, "giorni_ads": 0}
    return {"fa_ads": True, "annunci": len(ann),
            "giorni_ads": max((a.get("total_days_shown") or 0) for a in ann),
            "inserzionista": _nome(ann[0].get("advertiser"))}


def _nome(x):
    """Il Transparency Center restituisce l'inserzionista come oggetto."""
    if isinstance(x, dict):
        x = x.get("name") or x.get("advertiser_name") or x.get("id")
    return str(x or "")[:120] or None


def scheda_maps(nome, dom):
    """La scheda giusta e' quella col sito che combacia; se no, il nome."""
    d = cerca("google_maps", q=nome or dom, gl="it", hl="it")
    if "_errore" in d:
        return {"errore": "maps: " + d["_errore"]}, None
    ris = d.get("local_results") or []
    radice = dom.split(".")[0][:8]
    scelta = next((r for r in ris[:5] if radice in (r.get("website") or "").lower()), None)
    if not scelta and ris and nome and (ris[0].get("title") or "").lower()[:10] == nome.lower()[:10]:
        scelta = ris[0]
    if not scelta:
        return {"maps_trovato": False}, None
    return {"maps_trovato": True, "recensioni": scelta.get("reviews"), "voto": scelta.get("rating"),
            "tipo_maps": (scelta.get("type") or "")[:80]}, scelta.get("data_id") or scelta.get("place_id")


def testi_recensioni(data_id):
    d = cerca("google_maps_reviews", data_id=data_id, hl="it", sort_by="newest")
    if "_errore" in d:
        return None
    out = []
    for r in (d.get("reviews") or [])[:20]:
        t = (r.get("snippet") or r.get("text") or "").strip()
        if t:
            out.append({"voto": r.get("rating"), "testo": _pulito(t)[:600], "quando": r.get("date") or r.get("iso_date")})
    return out


# ── il sito, senza crediti ────────────────────────────────────────
def _pulito(t):
    """Postgres rifiuta il carattere nullo e gli altri di controllo: via."""
    return re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", t) if t else t


def leggi_sito(dom):
    testi = []
    for p in ("", "/chi-siamo", "/servizi", "/prodotti", "/prezzi"):
        try:
            raw = urllib.request.urlopen(urllib.request.Request("https://" + dom + p, headers=UA), timeout=8).read(200_000).decode("utf-8", "replace")
        except Exception:
            continue
        raw = re.sub(r"(?is)<(script|style|nav|footer|svg|noscript).*?</\1>", " ", raw)
        t = html.unescape(re.sub(r"<[^>]+>", " ", raw))
        t = re.sub(r"\s+", " ", t).strip()
        if len(t) > 200:
            testi.append(t)
    return _pulito(" || ".join(testi))[:12000]


# ── un dominio, per intero ────────────────────────────────────────
def raccogli(riga):
    dom, nome = riga["dominio"], riga.get("azienda") or ""
    out = {"crediti_usati": 0}
    a = fa_ads(dom); out.update(a); out["crediti_usati"] += 1
    m, data_id = scheda_maps(nome, dom); out.update(m); out["crediti_usati"] += 1
    if data_id:
        out["recensioni_testi"] = testi_recensioni(data_id); out["crediti_usati"] += 1
    # un 429 (quota oraria) non e' un dato: il dominio resta da fare e si riprende
    # al giro dopo, invece di finire in tabella con un buco (21/9)
    if "429" not in (out.get("errore") or ""):
        out["raccolto_il"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
    return out


def main():
    args = sys.argv[1:]
    if "--stato" in args:
        tot = conta("/rest/v1/raccolta?select=dominio")
        fatti = conta("/rest/v1/raccolta?select=dominio&raccolto_il=not.is.null")
        ads = conta("/rest/v1/raccolta?select=dominio&fa_ads=eq.true")
        maps = conta("/rest/v1/raccolta?select=dominio&maps_trovato=eq.true")
        print(f"raccolta: {fatti}/{tot} domini fatti | fa ads {ads} | scheda Maps {maps} | mancano {tot - fatti} | crediti SearchAPI residui {crediti_residui()}")
        return
    campione = int(args[args.index("--campione") + 1]) if "--campione" in args else 0
    massimo = int(args[args.index("--max") + 1]) if "--max" in args else 1100
    ore = float(args[args.index("--ore") + 1]) if "--ore" in args else 0
    inizio = time.time()
    while True:
        n = lotto(campione, massimo)
        if campione or n == 0 or not ore or (time.time() - inizio) > ore * 3600:
            break
        if crediti_residui() < 200:
            print("pull: crediti SearchAPI quasi finiti, mi fermo: ricaricare e riparte da solo"); break
    if not campione:
        print(f"pull: finito il giro in {int((time.time() - inizio) / 60)} min, {_usati[0]} crediti in tutto")
    # Dre (21/9): «sull'andamento mi aggiorna Clara?». Una riga in chat a fine giro,
    # solo se il giro ha lavorato: quando e' tutto finito, i giri a vuoto stanno zitti.
    if ore and _usati[0]:
        from stanza import di_clara
        tot = conta("/rest/v1/raccolta?select=dominio")
        fatti = conta("/rest/v1/raccolta?select=dominio&raccolto_il=not.is.null")
        ads = conta("/rest/v1/raccolta?select=dominio&fa_ads=eq.true")
        resto = crediti_residui()
        if fatti >= tot:
            testo = f"Pull finito: {tot} domini raccolti, {ads} fanno gia' ads. Crediti SearchAPI rimasti: {resto}. Ora si puo' fare il fit e dividere le campagne."
        else:
            testo = f"Pull: {fatti} domini su {tot} ({100 * fatti // tot}%), {ads} fanno gia' ads. Mancano {tot - fatti}, crediti SearchAPI rimasti {resto}. Riprende da solo al prossimo giro."
        di_clara("controllo", testo)


def lotto(campione, massimo):

    # chi manca: i domini di raccolta senza raccolto_il (li mette carica_lead_lista)
    if campione:
        righe = []
        for lista in ("cecchino", "strascico"):
            dom = sb("GET", f"/rest/v1/lead_lista?select=dominio,azienda&lista=eq.{lista}&order=id&limit={campione * 3}")
            visti, presi = set(), []
            for r in dom:
                if r["dominio"] in visti:
                    continue
                visti.add(r["dominio"]); presi.append(r)
                if len(presi) == campione:
                    break
            gia = {r["dominio"] for r in sb("GET", "/rest/v1/raccolta?select=dominio&raccolto_il=not.is.null&dominio=in.(" + ",".join(p["dominio"] for p in presi) + ")")} if presi else set()
            righe += [p for p in presi if p["dominio"] not in gia]
    else:
        righe = sb("GET", f"/rest/v1/raccolta?select=dominio,azienda&raccolto_il=is.null&order=dominio&limit={massimo}")
    if not righe:
        print("pull: niente da fare"); return 0

    t0 = time.time()
    # ogni dominio per intero (sito + crediti) e subito scritto: si vede il
    # progresso e se il run muore resta quello fatto. Il sito non costa
    # crediti e si legge nel tempo morto fra una chiamata a quota e l'altra.
    fatti = 0
    def uno(r):
        out = raccogli(r)
        out["sito_testo"] = leggi_sito(r["dominio"]) or None
        out["sito_letto"] = bool(out["sito_testo"])
        out["dominio"] = r["dominio"]; out["azienda"] = r.get("azienda")
        sb("POST", "/rest/v1/raccolta", out, {"Prefer": "resolution=merge-duplicates"})
        return r, out
    with cf.ThreadPoolExecutor(8) as ex:
      for r, out in ex.map(uno, righe):
        fatti += 1
        if campione:
            print(f"  {r['dominio'][:34]:34} ads={'SI' if out.get('fa_ads') else 'no':3} ann={out.get('annunci') or 0:3} "
                  f"maps={'SI' if out.get('maps_trovato') else 'no':3} rec={str(out.get('recensioni') or '-'):5} voto={str(out.get('voto') or '-'):4} "
                  f"testi={len(out.get('recensioni_testi') or []):2} sito={len(out.get('sito_testo') or ''):5}", flush=True)
        elif fatti % 100 == 0:
            print(f"  {fatti}/{len(righe)} in {int(time.time() - t0)}s, {_usati[0]} crediti", flush=True)
    print(f"pull: lotto di {fatti} domini in {int(time.time() - t0)}s, {(time.time() - t0) / max(fatti, 1):.1f} s/dominio", flush=True)
    return fatti


if __name__ == "__main__":
    main()
