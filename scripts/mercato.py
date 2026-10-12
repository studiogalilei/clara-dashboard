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

Stesso giorno, la copertura: sui si' da settembre il numero c'era per 41 su 70. La base
aveva 85 province su 107 e la provincia si cercava per nome esatto: «Pesaro» non trovava
«Pesaro e Urbino», «Carbonia» e «Rovereto» (comuni) nessuna. Ora la base ha tutte le
province per ogni settore, e provincia() riconosce nome, sigla e comune (ISTAT).
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
_PROV = None
# i nomi con cui la base del 24/8 ha salvato alcune province, verso il nome ISTAT
VECCHI = {"aquila": "L'Aquila", "bolzano - alto adige": "Bolzano/Bozen", "bolzano": "Bolzano/Bozen", "massa e carrara": "Massa-Carrara",
          "spezia": "La Spezia", "reggio emilia": "Reggio nell'Emilia", "monza e brianza": "Monza e della Brianza",
          "aosta": "Valle d'Aosta/Vallée d'Aoste", "valle d'aosta": "Valle d'Aosta/Vallée d'Aoste", "forli": "Forlì-Cesena",
          "pesaro": "Pesaro e Urbino", "urbino": "Pesaro e Urbino", "barletta": "Barletta-Andria-Trani", "andria": "Barletta-Andria-Trani"}
# come si dice nella mail: «nella provincia di Reggio Emilia», non «di Reggio nell'Emilia»
LUOGO = {"Bolzano/Bozen": "nella provincia di Bolzano", "Valle d'Aosta/Vallée d'Aoste": "in Valle d'Aosta",
         "Reggio nell'Emilia": "nella provincia di Reggio Emilia", "Monza e della Brianza": "nella provincia di Monza e Brianza",
         "Sud Sardegna": "nella provincia del Sud Sardegna", "L'Aquila": "nella provincia dell'Aquila", "La Spezia": "nella provincia della Spezia"}


def norm(s):
    return unicodedata.normalize("NFKD", str(s or "")).encode("ascii", "ignore").decode().lower().strip()


def _province():
    """Le 107 province e i 7.900 comuni ISTAT (province_it.json, dato pubblico)."""
    global _PROV
    if _PROV is None:
        d = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "province_it.json"), encoding="utf-8"))
        per_sigla = {v: k for k, v in d["province"].items()}
        _PROV = ({norm(k): k for k in d["province"]}, per_sigla, {norm(k): per_sigla.get(v) for k, v in d["comuni"].items()})
    return _PROV


def provincia(testo):
    """Il nome ISTAT della provincia da come l'abbiamo scritta noi: «Milano», «MI»,
    «Roma (RM)», «Provincia di Pesaro», «Carbonia» (un comune). None se non e' italiana."""
    nomi, per_sigla, comuni = _province()
    t = str(testo or "").strip()
    m = re.search(r"\(([A-Za-z]{2})\)\s*$", t)
    if m and m.group(1).upper() in per_sigla:
        return per_sigla[m.group(1).upper()]
    if re.fullmatch(r"[A-Z]{2}", t) and t in per_sigla:
        return per_sigla[t]
    n = re.sub(r"^(citta metropolitana d[i']|ente di decentramento regionale di|libero consorzio comunale di|"
               r"provincia autonoma di|provincia (?:di|del|della|dell'))\s*", "", norm(t)).strip(" ,.-")
    n = re.sub(r"\s+", " ", n)
    if not n or n in ("none", "null", "nan", "n/a", "na", "italia", "italy"):   # «None» e' un comune del Torinese
        return None
    return nomi.get(n) or VECCHI.get(n) or comuni.get(n) or next((v for k, v in nomi.items() if k.startswith(n + " ")), None)


def luogo(prov):
    return LUOGO.get(prov, f"nella provincia di {prov}")


def base():
    """La base settore x provincia (Keyword Planner, precalcolata il 24/8). Sta nel bucket
    riservato; si tiene un'ora in cache. Se non si legge, nessun numero: mai uno inventato."""
    global _BASE
    if _BASE is not None:
        return _BASE
    loc = os.path.join(tempfile.gettempdir(), "odyn-base_analisi.json")
    # 12/10: tre tentativi, e un fallimento NON si ricorda. Prima un colpo di rete perso
    # lasciava la base vuota per tutto il giro: ogni mail di quel giro partiva senza numero.
    for tentativo in range(3):
        try:
            if not os.path.exists(loc) or time.time() - os.path.getmtime(loc) > 3600:
                from stanza import env
                req = urllib.request.Request(f"{env('VITE_SUPABASE_URL')}/storage/v1/object/vault/riservato/base_analisi.json",
                                             headers={"apikey": env("SUPABASE_SERVICE_KEY"), "Authorization": f"Bearer {env('SUPABASE_SERVICE_KEY')}"})
                with urllib.request.urlopen(req, timeout=60) as r:
                    dati = r.read()
                if dati.strip():
                    open(loc, "wb").write(dati)
            _BASE = {(norm(v["settore"]), provincia(v["provincia"]) or v["provincia"]): v
                     for v in json.load(open(loc, encoding="utf-8")).values()}
            return _BASE
        except Exception as e:                                   # noqa: BLE001
            errore = e
            time.sleep(2 * (tentativo + 1))
    print(f"  (base dei volumi non letta: {str(errore)[:80]})")
    return {}


def voce(settore, prov):
    """La riga della base per un settore (anche col nome del fit) e una provincia, o None."""
    return base().get((SINONIMI.get(norm(settore), norm(settore)), provincia(prov)))


def domanda(settore, prov):
    """(ricerche al mese vere, parole che le fanno, riga della base) o None. Senza le parole
    generiche, e col solo mestiere quando e' piu' stretto del settore."""
    v = voce(settore, prov)
    if not v:
        return None
    parole = [t for t in (v.get("top") or []) if not GENERICHE.match(str(t.get("k", "")).strip())]
    if norm(settore) in SOLO:
        parole = [t for t in parole if SOLO[norm(settore)] in str(t.get("k", "")).lower()]
    return sum(int(t.get("n") or 0) for t in parole), parole, v


def migliaia(n):
    return f"{n:,}".replace(",", ".")


def dato_forte(settore, prov):
    """(«nella provincia di X ci sono circa N ricerche al mese di persone che cercano Y», N)
    oppure (None, motivo). Il numero e' tondo e mai sotto SOGLIA."""
    d = domanda(settore, prov)
    if not d:
        return None, "nessun dato per settore e provincia"
    n, _, v = d
    if n < SOGLIA:
        return None, f"troppo poco ({n} al mese)"
    cosa = COSA.get(norm(settore)) or COSA.get(SINONIMI.get(norm(settore), norm(settore)))
    if not cosa:
        return None, "settore senza descrizione"
    tondo = int(round(n, -2)) if n < 10000 else int(round(n, -3))
    return f"{luogo(provincia(v['provincia']) or v['provincia'])} ci sono circa {migliaia(tondo)} ricerche al mese di persone che {cosa}", tondo


def settore_e_provincia(p):
    """Settore e provincia di un lead, uguali per la mail e per l'analisi: i due fit uniti
    (il nuovo vince, come analisi_auto.fit_unito), poi la citta' della scheda. La provincia
    e' il nome ISTAT o None."""
    e = (p or {}).get("enriched") or {}
    v1, v2 = e.get("google_fit") or {}, e.get("google_fit_v2") or {}
    fit = {**v1, **{k: v for k, v in v2.items() if v not in (None, "", [], {})}}
    return fit.get("settore") or (p or {}).get("sector"), provincia(fit.get("provincia")) or provincia((p or {}).get("city"))


def dato_di(p):
    """Il dato forte di un lead, da quello che sappiamo di lui."""
    return dato_forte(*settore_e_provincia(p))
