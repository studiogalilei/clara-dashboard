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
   enriched.google_fit. Da li' lo leggono la scheda, il foglio e le bozze.
   Dal 20/10 il Foglio Zone NON entra (Dre: non affidabile, caso per caso).
6. dal 20/10 anche IL META FIT (google_fit.meta): stesso sito, stesse recensioni, la Meta Ad
   Library, e un verdetto a parte; google_fit.canale dice il canale consigliato.

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
import urllib.error

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from stanza import sb, sb_tutte, env                       # noqa: E402
import cervello                                            # noqa: E402

RADICE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
QUANTI = 20          # per giro: il resto al giro dopo (ogni 15 minuti)

# ── i fogli ──────────────────────────────────────────────────────
# LA RETE SULLA PROVINCIA (28/9). Le province vere, dal file dei codici Google
# usato per misurare i volumi: se una parola del sito e' il nome di una di
# queste, e' una provincia vera, non una parola inventata dal modello.
def _province_note():
    # 29/9: prima c'era solo la copia nel vault del Mac, e in cloud il file non
    # esiste: la rete delle province non ha mai funzionato dove gira davvero, e
    # nessuno lo vedeva perche' sul Mac passava. Il file sta nel repository
    # (sono nomi pubblici), il vault resta come seconda strada.
    import pathlib
    for cand in (pathlib.Path(RADICE) / "data" / "geo_province.json",
                 pathlib.Path.home() / "Documents/Obsidian/studiogalilei/Sistema Operativo Studio Galilei/ODYN Cockpit/data/geo_province.json"):
        try:
            return set(json.load(open(cand)).keys())
        except Exception:                                    # noqa: BLE001
            continue
    return set()


_PROV = None


def _provincia_dal_testo(testo):
    """La provincia nominata nel sito, se ce n'e' una sola e chiara.

    Non indovina: cerca i nomi veri delle province italiane dentro il testo e
    accetta il piu' citato. Se ne trova due a pari merito non sceglie, perche'
    una provincia sbagliata e' peggio di nessuna provincia.
    """
    global _PROV
    if _PROV is None:
        _PROV = _province_note()
    if not _PROV or not testo:
        return ""
    t = testo.lower()
    # SOLO DOVE UNA SEDE PUO' STARE (28/9). La prima versione ha dedotto «Latina»
    # per Viaggi del Mappamondo, perche' nel sito c'era «America Latina»: una
    # destinazione turistica, non la provincia. Una provincia sbagliata e' peggio
    # di nessuna provincia, quindi il nome vale solo se sta accanto a qualcosa che
    # indica davvero una sede: un indirizzo, una sigla fra parentesi, «provincia di».
    conta = {}
    for nome in _PROV:
        n = nome.lower().split(" - ")[0]
        if len(n) < 4:
            continue
        vicino = 0
        for m in re.finditer(r"\b" + re.escape(n) + r"\b", t):
            i, j = m.start(), m.end()
            attorno = t[max(0, i - 120):min(len(t), j + 60)]
            if re.search(r"provincia di|\(\s*[a-z]{2}\s*\)|\bvia\b|\bviale\b|\bpiazza\b|\bcorso\b|"
                         r"\bsede\b|\bsedi\b|\bufficio\b|\bc\.?a\.?p\.?\b|\b\d{5}\b|"
                         r"\bsiamo a\b|\bci trov\w+\b", attorno):
                vicino += 1
        if vicino:
            conta[nome] = vicino
    if not conta:
        return ""
    ordinate = sorted(conta.items(), key=lambda x: -x[1])
    if len(ordinate) > 1 and ordinate[0][1] == ordinate[1][1]:
        # PARI MERITO (28/9). «la nostra sede e' a Bergamo, in via Roma 12»: sia
        # Bergamo sia Roma stanno accanto a un indirizzo, e a pari conteggio non
        # si sceglieva nessuno dei due. Vince chi e' nominato come SEDE, non chi
        # capita in una via: «sede a X», «provincia di X», «X (XX)», «CAP X».
        forti = {}
        for nome, _ in ordinate:
            n = nome.lower().split(" - ")[0]
            q = len(re.findall(# stretto apposta: «sede a X», «sede e' a X», «provincia di X». Non
            # «sedi a Milano e a Roma», dove non si deve scegliere.
            r"(?:sede|siamo|ci trov\w+|provincia)\W{0,3}(?:e'|è|a|in|di|si trova)?\W{0,3}(?:a|in|di)?\W{0,3}" + re.escape(n) + r"\b", t))
            q += len(re.findall(re.escape(n) + r"\s*\(\s*[a-z]{2}\s*\)", t))
            q += len(re.findall(r"\b\d{5}\s+" + re.escape(n) + r"\b", t))
            if q:
                forti[nome] = q
        if len(forti) == 1:
            return list(forti)[0]
        if len(forti) > 1:
            f = sorted(forti.items(), key=lambda x: -x[1])
            return f[0][0] if f[0][1] > f[1][1] else ""
        return ""                                            # niente lo distingue: non si sceglie
    return ordinate[0][0]


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
    except urllib.error.HTTPError as e:
        # 6/10, GIOCOPLAST: il server dice «errore 500» ma manda la pagina intera. Se c'e' una
        # pagina vera la si legge; un errore senza contenuto resta un errore
        try:
            raw = e.read(300_000).decode("utf-8", errors="replace") if e.code >= 500 else ""
        except Exception:                                    # noqa: BLE001
            raw = ""
        if len(raw) < 2000 or "<html" not in raw[:5000].lower():
            return ""
    except Exception:
        return ""
    _SEGNALI[url] = segnali_meta(raw)
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


_SEGNALI = {}


def segnali_meta(raw):
    """Quello che il codice del sito dice di Meta: il pixel (hanno gia' fatto o fanno Meta Ads),
    e se hanno Instagram o Facebook (c'e' materiale visivo da cui partire)."""
    r = raw or ""
    return {"pixel_meta": bool(re.search(r"connect\.facebook\.net|fbq\s*\(|facebook-jssdk|fbevents\.js", r, re.I)),
            "instagram": "instagram.com/" in r.lower(), "facebook": bool(re.search(r"facebook\.com/(?!tr\b|plugins|sharer)", r, re.I))}


def segnali_di(sito):
    u = sito or ""
    if u and not u.startswith("http"):
        u = "https://" + u
    return _SEGNALI.get(u) or {"pixel_meta": False, "instagram": False, "facebook": False}


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
 "settore_uguale": true se quel settore descrive DAVVERO quello che vendono (gli stessi prodotti, le stesse
   parole che la gente cerca su Google), false se e' solo il piu' vicino fra quelli disponibili
   (esempio: tende da sole e pergole non sono «verande»; una concessionaria non e' un'«officina»),
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
 "visivo": true se quello che vendono si vende con le immagini (una casa, un infisso, una cucina, un
   viaggio, un piatto, un trattamento estetico, un prodotto da vedere), false se e' un servizio che le
   foto non raccontano (consulenza, software, pratiche),
 "pubblico_definibile": true se il cliente tipo si riconosce bene per eta', zona, interessi o momento
   della vita (chi sta ristrutturando, chi ha un neonato, chi ama la bici), false se puo' essere
   chiunque o solo poche aziende specifiche,
 "categoria_sensibile": "" oppure una fra "casa" (immobili, mutui, affitti), "credito" (finanza,
   prestiti, assicurazioni), "lavoro" (offerte di lavoro, formazione per lavorare), "salute"
   (dimagrimento, integratori, cure, estetica medica), "alcol", "gioco", "adulti", "armi", "tabacco",
   "cripto", "politica": sono le categorie su cui Meta limita o vieta la pubblicita'.
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


# Dre, 20/10: «solo gente che non fa Google Ads o che lo fa male male: alcuni arrivati facevano gia'
# Google Ads». Dal Transparency Center (pull.fa_ads): tanti annunci da tanto tempo = lo fanno sul serio.
ADS_SERI = {"annunci": 10, "giorni": 90}


def giudizio_ads(ads):
    """(«no»|«poco»|«serio»|None, frase). None = non misurato."""
    if not ads or ads.get("errore"):
        return None, "Google Ads non misurato"
    if not ads.get("fa_ads"):
        return "no", "non fa Google Ads"
    n, g = ads.get("annunci") or 0, ads.get("giorni_ads") or 0
    if n >= ADS_SERI["annunci"] and g >= ADS_SERI["giorni"]:
        return "serio", f"fa gia' Google Ads con continuita' ({n} annunci, da {g} giorni)"
    return "poco", f"fa Google Ads ma poco ({n} annunci, da {g} giorni): forse lo fa male, da guardare"


def verdetto(c, zona, rec, ads=None):
    motivi = []
    if c.get("esclusione"):
        return "NO", f"{c['esclusione']}: non e' un cliente possibile"
    quanto, frase_ads = giudizio_ads(ads)
    if quanto == "serio":
        return "NO", frase_ads + ": cerchiamo chi non lo fa o lo fa male"
    if quanto == "poco":
        motivi.append(frase_ads)
    if quanto is None and ads is not None:
        motivi.append(frase_ads)                             # misura fallita: si dice (20/10)
    if not c.get("settore") or c.get("settore") == "altro":
        motivi.append("settore non fra quelli misurati")
    elif c.get("settore_uguale") is False:
        motivi.append(f"settore misurato solo per somiglianza («{c['settore']}»): i volumi non sono i loro")
    # la zona mancante NON e' un difetto del cliente: e' un dato che non abbiamo (Dre, 21/9).
    # Prima finivano PARZIALE aziende sane solo perche' la loro combinazione non era nel foglio.
    if zona is None:
        pass
    elif zona["verdetto"] == "ROSSO":
        # quando i dati si contraddicono non si boccia (30/9): tante recensioni dove «nessuno
        # cerca» vuol dire quasi sempre che i volumi misurati non sono quelli del loro settore
        if rec is not None and rec["recensioni"] >= 30:
            motivi.append(f"provincia rossa ({zona['domanda_mese']} ricerche/mese) ma {rec['recensioni']} recensioni: "
                          "i volumi forse non sono del loro settore, da verificare")
        else:
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


# ── IL META FIT (Dre, 20/10: «da ora in poi facciamo anche Meta Ads, crea il Meta fit») ──────
# Dre: «qui conta di piu' il ticket del prodotto, perche' e' demand generation: si genera la domanda
# in modo diretto; l'altra parte (Google) e' intercettare la domanda». Quindi: su Meta il valore di
# un cliente pesa piu' di tutto, e il resto (visivo, pubblico, categoria) viene dopo.
META_SERI = {"annunci": 10, "giorni": 90}
_PAROLE_VUOTE = {"srl", "srls", "snc", "sas", "spa", "s.r.l.", "s.n.c.", "s.a.s.", "di", "e", "&", "the", "group",
                 "gruppo", "studio", "agenzia", "immobiliare", "azienda", "italia", "italy"}


def _parole(nome):
    return {w for w in re.split(r"[^a-z0-9]+", (nome or "").lower()) if len(w) >= 3 and w not in _PAROLE_VUOTE}


def _annuncio_suo(ad, azienda, dom):
    """L'annuncio e' dell'azienda se il link porta al suo dominio o se il nome della pagina e' il suo."""
    sn = ad.get("snapshot") or {}
    testi = " ".join(str(sn.get(k) or "") for k in ("link_url", "caption", "page_profile_uri")).lower()
    if dom and dom.lower() in testi:
        return True
    mie, sue = _parole(azienda), _parole(ad.get("page_name") or sn.get("page_name"))
    return bool(mie) and (mie <= sue or (len(mie & sue) >= 2))


def conta_meta_ads(ads, azienda, dom, oggi=None):
    """{"fa_meta_ads", "annunci_attivi", "giorni", "pagina"} dagli annunci della Ad Library."""
    oggi = oggi or datetime.datetime.now(datetime.timezone.utc)
    suoi = [a for a in (ads or []) if _annuncio_suo(a, azienda, dom)]
    attivi = [a for a in suoi if a.get("is_active")]
    giorni = 0
    for a in suoi:
        try:
            g = (oggi - datetime.datetime.fromisoformat(str(a.get("start_date")).replace("Z", "+00:00"))).days
            giorni = max(giorni, g)
        except Exception:                                    # noqa: BLE001
            continue
    pagina = (suoi[0].get("page_name") if suoi else None)
    return {"fa_meta_ads": bool(attivi), "annunci_attivi": len(attivi), "annunci_totali": len(suoi),
            "giorni": giorni, "pagina": pagina}


def fa_meta_ads(azienda, dom):
    """La Meta Ad Library via SearchAPI (1 credito). None se la chiave manca o la ricerca fallisce."""
    if not env("SEARCHAPI_KEY") or not azienda:
        return None
    import time as _t
    d = {}
    for tentativo in (1, 2):
        try:
            import pull
            d = pull.cerca("meta_ad_library", q=azienda, country="IT")
        except Exception as e:                               # noqa: BLE001
            return {"errore": str(e)[:80]}
        if "_errore" in d:
            return {"errore": "meta: " + d["_errore"]}
        if d.get("ads"):
            break
        # 20/10: una risposta VUOTA puo' essere un nome raro senza annunci (vero zero) o un buco del servizio
        # (Roero Infissi aveva 16 annunci e risultava senza). Si distingue con una domanda di controllo su una
        # parola che ha sempre annunci: se il servizio risponde, lo zero e' vero.
        try:
            prova = pull.cerca("meta_ad_library", q="serramenti", country="IT")
        except Exception:                                    # noqa: BLE001
            prova = {}
        if prova.get("ads"):
            break
        _t.sleep(2)
    else:
        return {"errore": "meta: la Ad Library non risponde (risposta vuota anche al controllo)"}
    return conta_meta_ads(d.get("ads") or [], azienda, dom)


def giudizio_meta_ads(m):
    if not m or m.get("errore"):
        return None, "Meta Ads non misurato"
    if not m.get("fa_meta_ads"):
        return "no", "non fa Meta Ads"
    n, g = m.get("annunci_attivi") or 0, m.get("giorni") or 0
    if n >= META_SERI["annunci"] and g >= META_SERI["giorni"]:
        return "serio", f"fa gia' Meta Ads con continuita' ({n} annunci attivi, da {g} giorni)"
    return "poco", f"fa Meta Ads ma poco ({n} annunci attivi, da {g} giorni): forse lo fa male, da guardare"


META_VIETATE = ("adulti", "armi", "tabacco", "gioco")
META_LIMITATE = ("casa", "credito", "lavoro", "salute", "alcol", "cripto", "politica")


def verdetto_meta(c, rec, meta=None, segnali=None):
    """SI / PARZIALE / NO per Meta Ads, col motivo. Il ticket pesa piu' di tutto (Dre, 20/10)."""
    motivi, a_favore = [], []
    segnali = segnali or {}
    if c.get("esclusione"):
        return "NO", f"{c['esclusione']}: non e' un cliente possibile"
    quanto, frase = giudizio_meta_ads(meta)
    if quanto == "serio":
        return "NO", frase + ": cerchiamo chi non lo fa o lo fa male"
    cat = (c.get("categoria_sensibile") or "").lower()
    if cat in META_VIETATE:
        return "NO", f"categoria «{cat}»: Meta non la fa pubblicizzare"
    # il ticket: generare domanda costa, e la paga il margine di un cliente
    tmax = c.get("ticket_max") or c.get("ticket_min") or 0
    online = bool(c.get("vendita_possibile_online"))
    if tmax and tmax < 50:
        return "NO", f"ticket sotto i 50 € ({_ticket_scritto(c)}): generare la domanda costa piu' di quanto rende"
    if tmax and tmax < 300 and not online:
        return "NO", f"ticket basso ({_ticket_scritto(c)}) e non si compra online: generare la domanda non si ripaga"
    if tmax and tmax < 300:
        motivi.append(f"ticket basso ({_ticket_scritto(c)}): regge solo vendendo online con volumi")
    elif tmax and tmax < 1000:
        motivi.append(f"ticket medio ({_ticket_scritto(c)}): serve un passaggio di vendita che chiuda")
    elif tmax:
        a_favore.append(f"un cliente vale {_ticket_scritto(c)}: la domanda generata si ripaga")
    # il pubblico: Meta lo trova per chi e', non per cosa cerca
    b2b = (c.get("tipo") or "").upper() == "B2B"
    if b2b and c.get("pubblico_definibile") is False:
        return "NO", "B2B senza un pubblico riconoscibile: Meta non sa a chi mostrarlo"
    if b2b:
        motivi.append("B2B: su Meta funziona solo con un pubblico stretto e un contenuto che spiega")
    elif c.get("pubblico_definibile") is False:
        motivi.append("il cliente tipo puo' essere chiunque: difficile da mirare")
    else:
        a_favore.append("il cliente tipo si riconosce")
    if c.get("visivo") is False:
        motivi.append("non si vende con le immagini: serve un contenuto che spieghi")
    elif c.get("visivo"):
        a_favore.append("si vende con le immagini")
    come = (c.get("come_lo_cercano") or "ricerca").lower()
    if come in ("impulso", "per_pubblico", "da_spiegare"):
        a_favore.append({"impulso": "si compra d'impulso: la domanda si crea mostrandolo",
                         "per_pubblico": "il cliente si riconosce per pubblico", "da_spiegare": "va spiegato: il video lo fa"}[come])
    if quanto == "poco":
        motivi.append(frase)
    if cat in META_LIMITATE:
        motivi.append(f"categoria «{cat}»: Meta limita il targeting, si puo' fare ma con meno precisione")
    if rec is not None:
        if rec["recensioni"] < 5:
            return "NO", f"meno di 5 recensioni ({rec['recensioni']}): troppo piccolo"
        if rec["recensioni"] < 20:
            motivi.append(f"{rec['recensioni']} recensioni: piccolo, forse regge un pilot")
    if quanto is None:
        motivi.append(frase)                                 # «Meta Ads non misurato»: si dice, non si finge un si'
    if segnali.get("pixel_meta") and quanto == "no":
        a_favore.append("ha il pixel Meta sul sito: il canale lo conosce, oggi non lo usa")
    if motivi:
        return "PARZIALE", "; ".join(motivi)
    return "SI", "; ".join(a_favore) if a_favore else "nessun motivo di scarto"


def canale(google, meta):
    """Il canale consigliato dai due verdetti: entrambi, Google, Meta, o nessuno."""
    peso = {"SI": 2, "PARZIALE": 1, "NO": 0}
    g, m = peso.get(google, 0), peso.get(meta, 0)
    if g == 0 and m == 0:
        return "nessuno"
    if g == m:
        return "entrambi" if g == 2 else ("Google o Meta, con riserve")
    return "Google" if g > m else "Meta"


def _zona_sul_raggio(c, zone):
    """La domanda si misura dove l'azienda vende davvero, non dove ha la sede (Dre, 21/9).

    Un'azienda con sede a Brescia che lavora in tutta la Lombardia non ha la
    domanda di Brescia. Si sommano le zone che il sito dichiara di servire; se
    non ne dichiara nessuna, si usa la provincia della sede. Un raggio nazionale
    o estero non si misura con un foglio provinciale: si dice e basta.
    """
    settore = c.get("settore")
    # 30/9: i volumi di un settore solo «vicino» non sono i loro (Denis Tende, tende da sole lette
    # come «verande»: 10 ricerche al mese a Treviso). Meglio nessun numero che un numero di altri.
    if not settore or settore == "altro" or c.get("settore_uguale") is False:
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
    from stanza import sito_vero
    sito = sito_vero(p)                                  # 17/10: mai aruba.it o gmail.com come sito
    testo = leggi_sito(sito)
    c = capisci(azienda, testo, settori)
    # Dre, 20/10: «dimentica la roba delle zone, abbiamo visto che non e' affidabile, bisogna vedere
    # le cose caso per caso». Il Foglio Zone non entra piu' nel verdetto ne' nei messaggi.
    zona = None
    # le recensioni costano (SearchAPI): non si chiedono per chi e' gia' fuori
    rec = None if c.get("esclusione") else recensioni(azienda, c.get("provincia", ""))
    ads = None
    if not c.get("esclusione"):
        try:
            import pull
            dom = re.sub(r"^https?://(www\.)?", "", (sito or "").lower()).split("/")[0]
            ads = pull.fa_ads(dom) if dom else None
        except Exception as e:                               # noqa: BLE001
            ads = {"errore": str(e)[:80]}
    v, motivo = verdetto(c, zona, rec, ads)
    dom_meta = re.sub(r"^https?://(www\.)?", "", (sito or "").lower()).split("/")[0]
    meta_ads = None if c.get("esclusione") else fa_meta_ads(azienda, dom_meta)
    segnali = segnali_di(sito)
    vm, motivo_m = verdetto_meta(c, rec, meta_ads, segnali)
    fit = {
        "google_ads": ads,
        "meta": {"verdetto": vm, "motivo": motivo_m, "meta_ads": meta_ads, "segnali": segnali,
                 "visivo": c.get("visivo"), "pubblico_definibile": c.get("pubblico_definibile"),
                 "categoria_sensibile": c.get("categoria_sensibile") or None},
        "canale": canale(v, vm),
        "verdetto": v, "motivo": motivo, "settore": c.get("settore"), "provincia": c.get("provincia"),
        "settore_uguale": c.get("settore_uguale"),
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
        # IL TESTO DEL SITO SI TIENE (28/9). Prima si leggeva, si chiedeva al
        # modello, e poi si buttava: «sito_letto: true» ma niente testo, per tutte
        # e 265 le aziende lette. Cosi' la provincia dipendeva da quanto era
        # esplicito l'indirizzo in quel momento: 161 su 313 restavano senza, e
        # senza provincia l'analisi non trova mai i volumi (caso Cristian, La
        # Baita Case: sede a Berbenno di Valtellina, provincia vuota).
        "sito_testo": (testo or "")[:4000],
    }
    # LA RETE SULLA PROVINCIA: se il modello non l'ha trovata, la si cerca nel
    # testo. Non si inventa: si accetta solo un nome di provincia vero, scritto
    # nel sito. Meglio una provincia dedotta da una parola presente che nessuna.
    if not (fit.get("provincia") or "").strip() and testo:
        fit["provincia"] = _provincia_dal_testo(testo) or ""
        if fit["provincia"]:
            fit["provincia_da"] = "testo del sito"
    return fit


def senza_zone(gf):
    """Il verdetto di un fit gia' fatto, rifatto senza le zone (Dre, 20/10). Usa quello che il fit ha
    salvato (settore, ticket, esclusione, recensioni); come_lo_cercano non era salvato: vale «ricerca»."""
    c = {k: gf.get(k) for k in ("settore", "settore_uguale", "esclusione", "ticket_min", "ticket_max", "ticket_fonte", "cosa_fa")}
    # come_lo_cercano non era salvato: si ricava dal motivo di allora, cosi' un «si compra d'impulso» resta tale
    m = (gf.get("motivo") or "").lower()
    c["come_lo_cercano"] = ("impulso" if "impulso" in m else "da_spiegare" if "da spiegare" in m
                            else "per_pubblico" if "per pubblico" in m else gf.get("come_lo_cercano") or "ricerca")
    v, motivo = verdetto(c, None, gf.get("recensioni"))
    nuovo = dict(gf, verdetto=v, motivo=motivo, zona=None,
                 provenienza=[r for r in (gf.get("provenienza") or []) if r.get("voce") != "domanda e CPC dove vendono"])
    return nuovo


def main():
    prova = "--prova" in sys.argv
    zone, settori = carica_fogli()
    if "--senza-zone" in sys.argv:
        from revisore import controlla
        tutte = sb_tutte("/rest/v1/prospects?select=id,email,company,enriched&enriched->google_fit->zona=not.is.null")
        tutte = [p for p in tutte if ((p.get("enriched") or {}).get("google_fit") or {}).get("zona")]   # solo i fit con le zone
        righe = controlla("rifaccio il verdetto del google fit senza le zone", tutte, irreversibile=False,
                          motivo="Dre 20/10: le zone non sono affidabili", dove="crm")
        cambi = 0
        for p in righe:
            gf = p["enriched"]["google_fit"]
            nuovo = senza_zone(gf)
            if nuovo["verdetto"] != gf.get("verdetto"):
                cambi += 1
                print(f"  {gf.get('verdetto'):8} -> {nuovo['verdetto']:8} {(p.get('company') or '')[:34]:34} {nuovo['motivo'][:60]}")
            if not prova:
                en = dict(p["enriched"], google_fit=nuovo)
                sb("PATCH", f"/rest/v1/prospects?id=eq.{p['id']}", {"enriched": en}, {"Prefer": "return=minimal"})
        print(f"googlefit senza zone: {len(righe)} fit riscritti, {cambi} verdetti cambiati" + (" (prova)" if prova else ""))
        return
    if "--sospetti" in sys.argv:
        # 30/9: i fit con un volume «misurato» che non sta in piedi, fatti prima che il modello
        # dicesse se il settore e' davvero il loro (concessionarie Ford con 10 ricerche al mese).
        # Si rifanno passando dal Revisore: si riscrive solo enriched.google_fit, si puo' rifare.
        from revisore import controlla
        tutte = sb_tutte("/rest/v1/prospects?select=id,email,name,company,website,sector,city,enriched,fuori,classificazione"
                         "&enriched->google_fit->zona=not.is.null")
        def _sospetto(p):
            gf = p["enriched"]["google_fit"]
            d = (gf.get("zona") or {}).get("domanda_mese")
            # solo un volume MISURATO e basso e' sospetto: chi non ha volumi non ha niente da rifare.
            # E il Revisore (30/9) ha fermato il giro coi fuori target dentro: il fit rifatto serve
            # ai vivi e ai negativi cortesi (il gigante buono lascia loro l'analisi), non ai morti.
            if p.get("classificazione") in ("fuori_target", "soppresso", "nervoso"):
                return False
            return "settore_uguale" not in gf and d is not None and float(d) < 100
        righe = [p for p in tutte if _sospetto(p)]
        righe = controlla("rifaccio il google fit delle aziende con volumi sospetti", righe, irreversibile=False,
                          motivo="il settore era solo il piu' vicino: i volumi erano di un altro settore", dove="crm")
    elif "--rifai-meta" in sys.argv:
        # 20/10: il Meta fit e' nuovo; chi aspetta l'analisi lo riceve subito (il resto, man mano che si rifa' il fit)
        from revisore import controlla
        base = "/rest/v1/prospects?select=id,email,name,company,website,sector,city,enriched,classificazione&fuori=eq.false&analysis_sent=eq.false&limit=300"
        visti, tutte = set(), []
        for filtro in ("&awaiting_us=eq.true", "&coda=not.is.null"):
            for p in sb("GET", base + filtro) or []:
                if p["id"] in visti or p.get("classificazione") in ("negativo", "fuori_target", "soppresso"):
                    continue
                visti.add(p["id"]); tutte.append(p)
        tutte = [p for p in tutte if "meta" not in (((p.get("enriched") or {}).get("google_fit")) or {})]
        righe = controlla("rifaccio il fit con il Meta fit a chi aspetta l'analisi", tutte, irreversibile=False,
                          motivo="Dre 20/10: da ora facciamo anche Meta Ads", dove="crm")
    elif "--ricontrolla-meta-ads" in sys.argv:
        # 20/10: la Ad Library ha risposto vuoto durante il primo giro; si rimisura e si corregge solo cio' che cambia
        import time as _t
        tutte = sb("GET", "/rest/v1/prospects?select=id,company,name,email,website,enriched&fuori=eq.false&analysis_sent=eq.false"
                          "&enriched->google_fit->meta=not.is.null&limit=300") or []
        from stanza import sito_vero
        cambi = 0
        for p in tutte:
            gf = p["enriched"]["google_fit"]; m = gf["meta"]
            dom = re.sub(r"^https?://(www\.)?", "", (sito_vero(p) or "").lower()).split("/")[0]
            nuovo = fa_meta_ads(p.get("company") or p.get("name"), dom)
            _t.sleep(1)
            c = {"settore": gf.get("settore"), "settore_uguale": gf.get("settore_uguale"), "esclusione": gf.get("esclusione"),
                 "tipo": gf.get("tipo"), "ticket_min": gf.get("ticket_min"), "ticket_max": gf.get("ticket_max"),
                 "vendita_possibile_online": gf.get("vendita_possibile_online"), "visivo": m.get("visivo"),
                 "pubblico_definibile": m.get("pubblico_definibile"), "categoria_sensibile": m.get("categoria_sensibile") or "",
                 "come_lo_cercano": "ricerca"}
            vm, motivo_m = verdetto_meta(c, gf.get("recensioni"), nuovo, m.get("segnali"))
            if vm != m.get("verdetto") or (nuovo or {}).get("annunci_attivi") != (m.get("meta_ads") or {}).get("annunci_attivi"):
                cambi += 1
                print(f"  M {m.get('verdetto'):8} -> {vm:8} {(p.get('company') or '')[:30]:30} {motivo_m[:70]}")
                if not prova:
                    gf2 = dict(gf, meta=dict(m, verdetto=vm, motivo=motivo_m, meta_ads=nuovo), canale=canale(gf.get("verdetto"), vm))
                    sb("PATCH", f"/rest/v1/prospects?id=eq.{p['id']}", {"enriched": {**p["enriched"], "google_fit": gf2}}, {"Prefer": "return=minimal"})
        print(f"ricontrollo Meta Ads: {len(tutte)} fit, {cambi} cambiati" + (" (prova)" if prova else ""))
        return
    elif "--uno" in sys.argv:
        email = sys.argv[sys.argv.index("--uno") + 1]
        righe = sb("GET", f"/rest/v1/prospects?select=id,email,name,company,website,sector,city,enriched&email=eq.{urllib.parse.quote(email)}")
    else:
        righe = sb("GET", "/rest/v1/prospects?select=id,email,name,company,website,sector,city,enriched"
                          # anche chi e' in coda, non solo chi aspetta risposta (27/9): quattro aziende
                          # in «RICONTATTO OOO» aspettavano un'analisi che vuole il sito letto, e il
                          # fit non le guardava perche' guardava solo awaiting_us.
                          "&fuori=eq.false&analysis_sent=eq.false&or=(awaiting_us.eq.true,coda.not.is.null)&stage=neq.nuovo&passato_a=is.null"
                          "&or=(classificazione.is.null,classificazione.not.in.(negativo,fuori_target,soppresso))"
                          "&order=last_reply_at.desc&limit=200") or []
        # CHI NON HA IL SITO LETTO SI RIPROVA (27/9). Quattro aziende (Viaggi del
        # Mappamondo, Telemar, Mare Karina, SMART Consulting) aspettavano l'analisi
        # da giorni: il fit era gia' passato ma il sito non si era scaricato, e
        # l'analisi vuole il sito letto. Con il vecchio criterio («salta chi ha gia'
        # un google_fit») non le avrebbe riprovate mai piu'. Un fit senza il sito
        # letto e' un fit incompleto, e si rifa'.
        def _da_rifare(x):
            f = (x.get("enriched") or {}).get("google_fit")
            if not f:
                return True
            if f.get("sito_letto"):
                return False
            # 13/10: un sito che non si scarica si riprova al massimo TRE volte, a sei ore di
            # distanza. Prima si riprovava a ogni giro per sempre, pagando il modello ogni volta
            # (un'azienda valutata ogni 15 minuti per giorni). Dopo, decide Dre (bozze lo chiede).
            if int(f.get("tentativi") or 1) >= 3:
                return False
            ultimo = f.get("valutato_il") or ""
            return not ultimo or ultimo < (datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(hours=6)).isoformat()
        righe = [p for p in righe if _da_rifare(p)]
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
        print(f"  G {fit['verdetto']:8} M {fit['meta']['verdetto']:8} {nome[:30]:30} canale {fit['canale']:10} {fit['motivo'][:50]} | {fit['meta']['motivo'][:50]}")
        if prova:
            continue
        prima = (p.get("enriched") or {}).get("google_fit") or {}
        fit["valutato_il"] = datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")
        fit["tentativi"] = 1 if fit.get("sito_letto") else int(prima.get("tentativi") or 0) + 1
        patch = {"enriched": {**(p.get("enriched") or {}), "google_fit": fit}}
        if not p.get("sector") and fit.get("settore") and fit["settore"] != "altro":
            patch["sector"] = fit["settore"]
        if not p.get("provincia_fit") and fit.get("provincia"):
            pass    # la provincia sta dentro enriched.google_fit: «city» e' la citta', non la provincia
        try:
            sb("PATCH", f"/rest/v1/prospects?id=eq.{p['id']}", patch)
        except RuntimeError as e:
            # 16/10: una scheda che non si scrive non ferma il giro degli altri
            print(f"  {'?':8} {str(nome)[:34]:34} non scritta: {str(e)[:90]}")
            continue
        fatti += 1
    print(f"google fit: {fatti} valutati, {len(righe)} nel giro")


if __name__ == "__main__":
    main()
