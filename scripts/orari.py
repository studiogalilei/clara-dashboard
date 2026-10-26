#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""GLI ORARI PROPOSTI PER LA CALL, IN PAROLE (22/10/2026).

Dre, 22/10: «proponi sempre due alternative: domani alle 15:30 oppure venerdi' 24 ottobre alle 11.
Domani finche' ha posti liberi: fa percepire che e' qualcosa di piu' importante».

Chi sceglie gli orari e' bozze.due_orari (il calendario vero di Dre). Qui solo il testo, puro e
senza database, cosi' lo usano tutti senza tirarsi dietro il motore delle bozze (il postino compreso):
  - `esteso`: come si salva in azione.giorno_proposto, sempre con la data
    («giovedì 23 ottobre alle 15:30 oppure venerdì 24 ottobre alle 11»);
  - `a_parole`: come si scrive nella mail, rispetto al giorno in cui la mail e' scritta
    («domani alle 15:30 oppure venerdì 24 ottobre alle 11»);
  - `scaduto`: uno degli orari e' oggi o gia' passato (la mail non puo' partire cosi').
«Domani» vale solo il giorno in cui e' scritto: per questo si salva sempre l'esteso e il giorno
della scrittura (azione.orari_scritti_il), mai la parola «domani» da sola.
"""
import datetime
import re

GIORNI = ["lunedì", "martedì", "mercoledì", "giovedì", "venerdì", "sabato", "domenica"]
MESI = ["gennaio", "febbraio", "marzo", "aprile", "maggio", "giugno", "luglio", "agosto",
        "settembre", "ottobre", "novembre", "dicembre"]
_G = r"(?:luned|marted|mercoled|gioved|venerd)[iì]'?"
_M = "|".join(MESI)
_ORA = r"alle\s+(?:ore\s+)?\d{1,2}(?:[:.]\d{2})?"
# un orario: «domani alle 15:30» o «giovedì 23 ottobre alle 15:30»
UNO = rf"(?:domani|{_G}\s+\d{{1,2}}\s+(?:{_M}))\s+{_ORA}"
# la frase intera della proposta: uno o due orari legati da «oppure»
FRASE = re.compile(rf"{UNO}(?:\s*,?\s+oppure\s+{UNO})?", re.I)
_PEZZO = re.compile(rf"(domani|{_G}\s+(\d{{1,2}})\s+({_M}))\s+alle\s+(?:ore\s+)?(\d{{1,2}})(?:[:.](\d{{2}}))?", re.I)
DISPONIBILITA_VECCHIA = "nel caso quel giorno non abbia disponibilità"
DISPONIBILITA = "nel caso non abbia disponibilità"


def calendario_per_giudici(oggi=None, giorni=21):
    """Il calendario che legge chi giudica una mail (26/10). Il Revisore della prima risposta ha
    fermato un si' perche' «il 28 ottobre 2026 e' giovedi', non mercoledi'»: era mercoledi', e la data
    l'aveva scritta il codice dal calendario vero. Un modello non sa che giorno e' oggi e i giorni
    della settimana li conta a memoria: glieli da' il codice, e gli dice di non ricontarli."""
    oggi = oggi or datetime.date.today()
    righe = [f"{GIORNI[d.weekday()]} {d.day} {MESI[d.month - 1]}"
             for d in (oggi + datetime.timedelta(days=i) for i in range(1, giorni + 1))]
    return (f"OGGI E' {GIORNI[oggi.weekday()]} {oggi.day} {MESI[oggi.month - 1]} {oggi.year}. "
            f"I prossimi giorni, dal calendario vero: {', '.join(righe)}. "
            "Le date e i giorni della settimana nella mail li ha scritti il codice da questo calendario: "
            "controllali solo contro questo elenco, mai a memoria.")


def scritto(t):
    """Un orario con la data: «giovedì 23 ottobre alle 15:30» (alle 15 senza «:00»)."""
    return f"{GIORNI[t.weekday()]} {t.day} {MESI[t.month - 1]} alle {t.hour}" + (f":{t.minute:02d}" if t.minute else "")


def esteso(orari):
    """Gli orari come si salvano (azione.giorno_proposto): sempre con la data, legati da «oppure»."""
    return " oppure ".join(scritto(t) for t in orari)


def _anno(giorno, mese, rif):
    """L'anno che mette la data piu' vicina al giorno di riferimento (gennaio scritto a ottobre e' il prossimo)."""
    try:
        d = datetime.date(rif.year, mese, giorno)
    except ValueError:
        return None
    if (d - rif).days > 180:
        d = d.replace(year=d.year - 1)
    elif (rif - d).days > 180:
        d = d.replace(year=d.year + 1)
    return d


def leggi(testo, rif):
    """Gli orari scritti nel testo, [(data, ora, minuti)], nell'ordine. «domani» e' il giorno dopo `rif`
    (il giorno in cui il testo e' stato scritto)."""
    out = []
    for m in _PEZZO.finditer(testo or ""):
        if m.group(1).lower() == "domani":
            d = rif + datetime.timedelta(days=1)
        else:
            d = _anno(int(m.group(2)), MESI.index(m.group(3).lower()) + 1, rif)
        if d:
            out.append((d, int(m.group(4)), int(m.group(5) or 0)))
    return out


def _parola(d, h, mi, rif):
    ora = f"alle {h}" + (f":{mi:02d}" if mi else "")
    if d == rif + datetime.timedelta(days=1):
        return f"domani {ora}"
    return f"{GIORNI[d.weekday()]} {d.day} {MESI[d.month - 1]} {ora}"


def a_parole(testo_esteso, rif):
    """Come si scrive nella mail il giorno `rif`: «domani alle 15:30 oppure venerdì 24 ottobre alle 11».
    Un solo orario (le proposte di prima del 22/10) resta com'era: non si indovina come era scritto."""
    orari = leggi(testo_esteso, rif)
    if len(orari) < 2:
        return testo_esteso or ""
    return " oppure ".join(_parola(d, h, mi, rif) for d, h, mi in orari)


def scaduto(testo, rif, oggi):
    """Uno degli orari proposti e' oggi o gia' passato? (testo scritto il giorno `rif`)"""
    return any(d <= oggi for d, _, _ in leggi(testo, rif))


def frase_proposta(testo):
    """La prima frase con gli orari PROPOSTI nel testo (match), o None. «Le avevo scritto martedi'
    29 settembre alle 10» e' un ricordo, non una proposta: conta solo con una parola di proposta poco prima."""
    for m in FRASE.finditer(testo or ""):
        prima = (testo or "")[max(0, m.start() - 90):m.start()]
        if re.search(r"propon|proporrei|sentirci|sentiamoci|chiamata|call|videochiamata|disponibil|che ne dice|potremmo|ci vediamo",
                     prima, re.I):
            return m
    return None


def giorno_roma(iso):
    """Il giorno (Roma) di un timestamp ISO del database, o None."""
    import zoneinfo
    if not iso:
        return None
    try:
        t = datetime.datetime.fromisoformat(str(iso).replace("Z", "+00:00"))
    except ValueError:
        try:
            return datetime.date.fromisoformat(str(iso)[:10])
        except ValueError:
            return None
    if t.tzinfo is None:
        return t.date()
    return t.astimezone(zoneinfo.ZoneInfo("Europe/Rome")).date()


def scritti_il(azione, nata_il=None):
    """Il giorno in cui gli orari della bozza sono stati scritti: quello salvato, se no l'ultimo
    ritocco, se no la nascita della proposta."""
    az = azione or {}
    for v in (az.get("orari_scritti_il"), (az.get("ritocco") or {}).get("il"), nata_il):
        g = giorno_roma(v)
        if g:
            return g
    return None
