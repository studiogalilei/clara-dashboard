# -*- coding: utf-8 -*-
"""IL NUMERO DEL MERCATO, IN UN POSTO SOLO (12/10/2026).

Dre, 12/10: nella mail con cui mandiamo l'analisi a giugno c'era una riga che «diceva
alla persona che la contattavamo perche' trovavamo potenziale in loro»; da luglio sembra
un messaggio automatico. Misurato: risposte entro una settimana dall'invio dell'analisi
21% a giugno, 8-15% da luglio. Il template INTERESSATO «aggiornato 3/7» aveva perso la
frase del potenziale e preso un «pero'» che la rendeva una scusa.

La riga torna, con UN numero vero dentro. Il numero lo sceglie QUESTO codice, mai il
modello (regola del 24/9), ed e' lo stesso che riceve l'analisi in PDF: mail e allegato
dicono la stessa cosa.

Tre cose che il test del 12/10 ha trovato e che qui sono murate:
1. il «tam» grezzo della base e' gonfiato da parole che non sono domanda per il servizio:
   per le agenzie immobiliari «immobiliare» da sola fa il 90-95% (e' chi cerca il PORTALE
   Immobiliare.it). Milano: 1.345.300 grezzi, 44.000 veri. Le parole generiche si tolgono;
2. i nomi del fit e della base non combaciavano (fotovoltaico / fotovoltaico_casa, caldaie
   e pompe_calore / pompe_calore_casa): stesso settore, numero perso. I sinonimi lo tengono;
3. un mestiere piu' stretto del settore (porte blindate dentro serramenti) prende solo la
   sua parola, non il totale del settore: 3.600 a Roma, non 22.000.
Sotto SOGLIA il numero non si mette: «50 ricerche al mese» non convince, smonta.
"""
import json
import os
import re
import tempfile
import time
import unicodedata
import urllib.request

SOGLIA = 300
SINONIMI = {"fotovoltaico": "fotovoltaico_casa", "pompe_calore": "pompe_calore_casa", "caldaie": "pompe_calore_casa",
            "climatizzazione": "pompe_calore_casa", "porte_blindate": "serramenti", "infissi": "serramenti",
            "fabbro": "ferro_battuto"}
SOLO = {"porte_blindate": "porte blindate"}     # mestiere piu' stretto del settore: solo la sua parola
GENERICHE = re.compile(r"^(immobiliare|immobiliare\.it|idealista|casa\.it|subito|case)$", re.I)
COSA = {"agenzie_immobiliari": "cercano casa o un'agenzia immobiliare", "serramenti": "cercano infissi e serramenti",
        "porte_blindate": "cercano porte blindate", "fotovoltaico_casa": "cercano un impianto fotovoltaico",
        "pompe_calore_casa": "cercano pompe di calore, caldaie o climatizzazione",
        "ferro_battuto": "cercano un fabbro o lavorazioni in ferro", "pavimentazioni_esterne": "cercano pavimentazioni esterne",
        "case_legno": "cercano una casa in legno", "carpenteria_metallica": "cercano lavorazioni di carpenteria metallica"}
_BASE = None


def norm(s):
    return unicodedata.normalize("NFKD", str(s or "")).encode("ascii", "ignore").decode().lower().strip()


def base():
    """La base settore x provincia (Keyword Planner, precalcolata il 24/8). Sta nel bucket
    riservato; si tiene un'ora in cache. Se non si legge, nessun numero: mai uno inventato."""
    global _BASE
    if _BASE is not None:
        return _BASE
    loc = os.path.join(tempfile.gettempdir(), "odyn-base_analisi.json")
    try:
        if not os.path.exists(loc) or time.time() - os.path.getmtime(loc) > 3600:
            from stanza import env
            req = urllib.request.Request(f"{env('VITE_SUPABASE_URL')}/storage/v1/object/vault/riservato/base_analisi.json",
                                         headers={"apikey": env("SUPABASE_SERVICE_KEY"), "Authorization": f"Bearer {env('SUPABASE_SERVICE_KEY')}"})
            with urllib.request.urlopen(req, timeout=60) as r:
                dati = r.read()
            if dati.strip():
                open(loc, "wb").write(dati)
        _BASE = {(norm(v["settore"]), norm(v["provincia"])): v for v in json.load(open(loc, encoding="utf-8")).values()}
    except Exception as e:                                       # noqa: BLE001
        print(f"  (base dei volumi non letta: {str(e)[:80]})")
        _BASE = {}
    return _BASE


def voce(settore, provincia):
    """La riga della base per un settore (anche col nome del fit) e una provincia, o None."""
    return base().get((SINONIMI.get(norm(settore), norm(settore)), norm(provincia)))


def domanda(settore, provincia):
    """(ricerche al mese vere, parole che le fanno, riga della base) o None. Senza le parole
    generiche, e col solo mestiere quando e' piu' stretto del settore."""
    v = voce(settore, provincia)
    if not v:
        return None
    parole = [t for t in (v.get("top") or []) if not GENERICHE.match(str(t.get("k", "")).strip())]
    if norm(settore) in SOLO:
        parole = [t for t in parole if SOLO[norm(settore)] in str(t.get("k", "")).lower()]
    return sum(int(t.get("n") or 0) for t in parole), parole, v


def migliaia(n):
    return f"{n:,}".replace(",", ".")


def dato_forte(settore, provincia):
    """(«nella provincia di X ci sono circa N ricerche al mese di persone che cercano Y», N)
    oppure (None, motivo). Il numero e' tondo e mai sotto SOGLIA."""
    d = domanda(settore, provincia)
    if not d:
        return None, "nessun dato per settore e provincia"
    n, _, v = d
    if n < SOGLIA:
        return None, f"troppo poco ({n} al mese)"
    cosa = COSA.get(norm(settore)) or COSA.get(SINONIMI.get(norm(settore), norm(settore)))
    if not cosa:
        return None, "settore senza descrizione"
    tondo = int(round(n, -2)) if n < 10000 else int(round(n, -3))
    return f"nella provincia di {v['provincia']} ci sono circa {migliaia(tondo)} ricerche al mese di persone che {cosa}", tondo


def dato_di(p):
    """Il dato forte di un lead, da quello che sappiamo di lui (fit, poi scheda)."""
    fit = ((p or {}).get("enriched") or {}).get("google_fit") or {}
    return dato_forte(fit.get("settore") or (p or {}).get("sector"), (fit.get("provincia") or (p or {}).get("city") or ""))
