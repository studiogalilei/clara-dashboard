#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""L'IMPRONTA DIGITALE DI UN'AZIENDA (Dre, 22/9/2026).

Dre: «se fanno pubblicità non è positivo di per sé: la domanda diventa se la
fanno bene o male, e lì si va a penetrare». Questo script misura quello che si
può misurare davvero, su tutti i domini, in automatico e senza crediti.

COSA MISURA, per ogni dominio gia' raccolto

1. CHI PAGA GLI ANNUNCI — l'inserzionista del Transparency Center (lo prende
   gia' il pull). Se lo STESSO inserzionista compare su piu' domini diversi,
   non e' l'azienda: e' un rivenditore o un'agenzia. Italiaonline compare su
   47 aziende della nostra lista, Pagine Si' su 8. Nessuna azienda gestisce
   47 siti. Questo si calcola contando, non indovinando.

2. COSA HANNO SUL SITO — i tag che dicono se misurano quello che spendono:
   Google Ads (conversioni), Analytics, Tag Manager, Microsoft Clarity, Meta
   Pixel. Sono gli stessi strumenti che Carlo installa ai clienti nuovi.

IL LIMITE, detto chiaro (misurato il 22/9 su 46 siti che fanno ads):
   solo il 13% mostra il tag Ads nel codice, ma il 54% ha Tag Manager, dove il
   tag puo' essere caricato senza comparire nell'HTML. Quindi «non ha il tag
   conversioni» e' un SOSPETTO FORTE quando non c'e' nemmeno Tag Manager, e
   NON e' una prova quando Tag Manager c'e'. Lo script lo scrive, non lo
   nasconde: chi legge deve sapere quanto vale il dato che ha in mano.

L'ANGOLO, che e' quello che serve alle mail (le quattro situazioni di Dre):
   non_fa_ads     i concorrenti pagano e tu no: che paghino dimostra che rende
   fermo          pochi annunci da mesi: lo fai ma e' li' fermo. Il migliore
   investe        molti annunci da tempo, per conto suo: lo fai ma non misuri
   rivenditore    l'inserzionista e' un'agenzia o un rivenditore: gia' seguito

USO
  impronta.py --prova 20     venti domini, stampa e non scrive
  impronta.py                tutti quelli raccolti e senza impronta
  impronta.py --ore 5        a lotti, per il cloud
"""
import concurrent.futures as cf
import os
import re
import sys
import time
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))   # i moduli comuni stanno in scripts/
from stanza import sb                                      # noqa: E402

UA = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36"}

# i tag che contano, con l'espressione che li riconosce nel codice della home
TAG = {
    "google_ads":  r"AW-\d{9,}|googleadservices\.com|gtag/js\?id=AW-",
    "analytics":   r"G-[A-Z0-9]{8,}|google-analytics\.com|gtag/js\?id=G-|UA-\d{4,}-\d",
    "tag_manager": r"googletagmanager\.com/gtm\.js|GTM-[A-Z0-9]{5,}",
    "clarity":     r"clarity\.ms|clarity\(\s*[\"']",
    "meta_pixel":  r"connect\.facebook\.net|fbq\(\s*[\"']",
}

# quante aziende diverse deve servire un inserzionista per chiamarlo rivenditore.
# 2 basta: due domini con lo stesso pagante non e' un caso (Dre, 22/9).
SOGLIA_RIVENDITORE = 2


def leggi_home(dominio):
    """Il codice della home, non il testo: i tag stanno nel sorgente."""
    for url in (f"https://{dominio}", f"https://www.{dominio}"):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=12) as r:
                return r.read(400_000).decode("utf-8", "replace")
        except Exception:
            continue
    return None


def tag_del_sito(dominio):
    raw = leggi_home(dominio)
    if raw is None:
        return None
    return {k: bool(re.search(p, raw, re.I)) for k, p in TAG.items()}


def rivenditori(soglia=SOGLIA_RIVENDITORE):
    """Gli inserzionisti che pagano per piu' di un'azienda: lo dicono i dati."""
    conta = {}
    passo = 1000
    da = 0
    while True:
        r = sb("GET", f"/rest/v1/raccolta?select=inserzionista&fa_ads=is.true"
                      f"&inserzionista=not.is.null&order=dominio&limit={passo}&offset={da}")
        if not r:
            break
        for x in r:
            n = (x["inserzionista"] or "").strip()
            if n:
                conta[n] = conta.get(n, 0) + 1
        if len(r) < passo:
            break
        da += passo
    return {n: c for n, c in conta.items() if c >= soglia}


def angolo(r, e_rivenditore):
    """La situazione in una parola, piu' il perche' scritto."""
    if not r.get("fa_ads"):
        return "non_fa_ads", "non compare nel Transparency Center"
    if e_rivenditore:
        return "rivenditore", f"gli annunci li paga {r['inserzionista']}, che compare su piu' aziende"
    n = r.get("annunci") or 0
    g = r.get("giorni_ads") or 0
    if n <= 2 and g >= 60:
        return "fermo", f"{n} annunci da {g} giorni: acceso e mai piu' toccato"
    if n >= 6:
        return "investe", f"{n} annunci attivi da {g} giorni"
    return "investe", f"{n} annunci da {g} giorni"


def misura(dominio):
    """Quanto vale il giudizio sul tag conversioni (il limite del 13%)."""
    return dominio


def una(r, riv):
    d = r["dominio"]
    tag = tag_del_sito(d)
    e_riv = (r.get("inserzionista") or "").strip() in riv
    ang, perche = angolo(r, e_riv)

    out = {"dominio": d, "angolo": ang, "angolo_perche": perche[:200],
           "sito_letto_tag": tag is not None}
    if tag:
        out.update({"tag_" + k: v for k, v in tag.items()})
        # il verdetto sul misurare, con la sua incertezza dichiarata
        if tag["google_ads"]:
            out["misura"] = "si"
        elif tag["tag_manager"]:
            out["misura"] = "forse"        # il tag puo' stare dentro Tag Manager
        else:
            out["misura"] = "no"
    else:
        out["misura"] = "non_letto"
    return out


def lotto(prova, riv):
    quanti = prova or 500
    r = sb("GET", "/rest/v1/raccolta?select=dominio,azienda,fa_ads,annunci,giorni_ads,inserzionista"
                  f"&raccolto_il=not.is.null&angolo=is.null&order=dominio&limit={quanti}")
    if not r:
        print("impronta: niente da fare"); return 0
    t0 = time.time()
    fatti = 0
    conta = {}
    with cf.ThreadPoolExecutor(12) as ex:
        for out in ex.map(lambda x: una(x, riv), r):
            conta[out["angolo"]] = conta.get(out["angolo"], 0) + 1
            fatti += 1
            if prova:
                tag = " ".join(k[4:] for k, v in out.items() if k.startswith("tag_") and v) or "nessun tag"
                print(f"  {out['angolo']:12} misura={out['misura']:9} {out['dominio'][:30]:30} {tag[:44]}")
            else:
                sb("PATCH", f"/rest/v1/raccolta?dominio=eq.{out['dominio']}",
                   {k: v for k, v in out.items() if k != "dominio"})
    print(f"impronta: {fatti} domini in {int(time.time() - t0)}s  " +
          "  ".join(f"{k} {v}" for k, v in sorted(conta.items())))
    return fatti


def main():
    args = sys.argv[1:]
    prova = int(args[args.index("--prova") + 1]) if "--prova" in args else 0
    ore = float(args[args.index("--ore") + 1]) if "--ore" in args else 0
    print("impronta: conto gli inserzionisti che servono piu' aziende...")
    riv = rivenditori()
    print(f"impronta: {len(riv)} rivenditori o agenzie riconosciuti dai dati")
    if riv:
        for n, c in sorted(riv.items(), key=lambda x: -x[1])[:5]:
            print(f"    {c:3} aziende <- {n[:46]}")
    inizio = time.time()
    while True:
        n = lotto(prova, riv)
        if prova or n == 0 or not ore or time.time() - inizio > ore * 3600:
            break


if __name__ == "__main__":
    main()
