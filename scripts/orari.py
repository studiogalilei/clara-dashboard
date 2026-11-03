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
UNO = rf"(?:oggi|domani|{_G}\s+\d{{1,2}}\s+(?:{_M}))\s+{_ORA}"
# la frase intera della proposta: uno o due orari legati da «oppure»
FRASE = re.compile(rf"{UNO}(?:\s*,?\s+oppure\s+{UNO})?", re.I)
_PEZZO = re.compile(rf"(oggi|domani|{_G}\s+(\d{{1,2}})\s+({_M}))\s+alle\s+(?:ore\s+)?(\d{{1,2}})(?:[:.](\d{{2}}))?", re.I)
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
        elif m.group(1).lower() == "oggi":
            d = rif
        else:
            d = _anno(int(m.group(2)), MESI.index(m.group(3).lower()) + 1, rif)
        if d:
            out.append((d, int(m.group(4)), int(m.group(5) or 0)))
    return out


def _parola(d, h, mi, rif):
    ora = f"alle {h}" + (f":{mi:02d}" if mi else "")
    if d == rif + datetime.timedelta(days=1):
        return f"domani {ora}"
    if d == rif:
        return f"oggi {ora}"
    return f"{GIORNI[d.weekday()]} {d.day} {MESI[d.month - 1]} {ora}"


def a_parole(testo_esteso, rif):
    """Come si scrive nella mail il giorno `rif`: «domani alle 15:30 oppure venerdì 24 ottobre alle 11».
    Un solo orario (le proposte di prima del 22/10) resta com'era: non si indovina come era scritto."""
    orari = leggi(testo_esteso, rif)
    if len(orari) < 2:
        return testo_esteso or ""
    return " oppure ".join(_parola(d, h, mi, rif) for d, h, mi in orari)


def scaduto(testo, rif, oggi, adesso=None):
    """Uno degli orari proposti e' oggi o gia' passato? (testo scritto il giorno `rif`)
    3/11: chi ci ha proposto OGGI riceve «oggi alle 16:30» (vincoli del lead): un orario di oggi scritto
    oggi vale finche' mancano almeno 30 minuti (`adesso`, ora di Roma; se manca, l'orario di oggi e' scaduto)."""
    for d, h, mi in leggi(testo, rif):
        if d < oggi:
            return True
        if d == oggi:
            if rif < oggi or adesso is None:
                return True
            if adesso.replace(tzinfo=None) + datetime.timedelta(minutes=30) > datetime.datetime(d.year, d.month, d.day, h, mi):
                return True
    return False


# ── I VINCOLI DEL LEAD (3/11/2026) ─────────────────────────────────────────────
# Cinque si' con l'analisi pronta aspettavano Dre da giorni: la regola del 22/10 («domani oppure data X»)
# proponeva orari che ignoravano cosa il lead aveva scritto («la prossima settimana», «oggi, se ha
# disponibilita'», «telefonata, solo dopo le 15:30»), e la seconda testa giustamente fermava la mail.
# Qui si leggono, puri e senza database, i vincoli dalla sua ultima mail; chi sceglie gli orari dentro
# quei vincoli resta una funzione sola, bozze.due_orari. Le parole sono la rete: il senso lo giudica
# comunque la seconda testa, che resta accesa su ogni mail.
_INCONTRO = re.compile(r"senti|chiam|\bcall\b|parlar|telefon|videochiam|incontr|veder|disponib|organizz|appuntament|"
                       r"riunion|confront|contatt|liber[oa]?\b|meet", re.I)
_FRASI = re.compile(r"(?<=[.!?\n])\s+")
_GSET = ["lunedì", "martedì", "mercoledì", "giovedì", "venerdì"]
_GIORNO_SET = re.compile(r"\b(?<!dal )(?<!al )(?<!da )(luned|marted|mercoled|gioved|venerd)[iì]'?(?:\s+(\d{1,2}))?(?!\s*(?:al|-)\s*(?:luned|marted|mercoled|gioved|venerd|sab|dom))", re.I)
_ORA_N = r"(?:ore\s+)?(\d{1,2})(?:[:.,](\d{2}))?"


def _hm(h, m):
    h, m = int(h), int(m or 0)
    if h < 8:
        h += 12                          # «dopo le 3» e' il pomeriggio
    return h, m


def _testo(h, m):
    return f"{h}" + (f":{m:02d}" if m else "")


def vincoli(testo, scritto_il, orario_iso=None):
    """I VINCOLI DI ORARIO CHE IL LEAD HA SCRITTO nella sua ultima mail (3/11). `testo` e' il suo
    messaggio senza la firma, `scritto_il` il giorno (Roma) in cui l'ha scritto: «oggi» e «la prossima
    settimana» valgono rispetto a quel giorno, non a quando rispondiamo. `orario_iso` e' l'orario che il
    lettore AI ha capito (enriched.lettore.orario_iso), se c'e'. Torna un dizionario da salvare
    (azione.orari_vincoli), vuoto se non ha chiesto niente:
      giorno      AAAA-MM-GG, il giorno che ha proposto lui («oggi», «domani», «giovedì»)
      oggi        True se quel giorno era il suo «oggi»
      settimana   AAAA-MM-GG, il lunedi' della settimana chiesta («la prossima settimana»)
      dalle       «HH:MM», il primo inizio possibile («dopo le 15:30» -> 16:00, «dalle 15» -> 15:00)
      entro       «HH:MM», entro quando la call deve finire («sino alle 18:30»)
      ora         «HH:MM», l'ora precisa che ha proposto
      fascia      come l'ha detta lui («dopo le 15:30»), per la frase della mail
      canale      «telefono» o «video» se l'ha detto
      lunedi      True se il lunedi' l'ha messo lui
    """
    if not testo or not scritto_il:
        return {}
    t = " ".join(str(testo).split("  [firma di chi scrive")[0].split())
    low = t.lower()
    v = {}
    frasi = [f for f in _FRASI.split(low) if f.strip()] or [low]
    incontro = [f for f in frasi if _INCONTRO.search(f)]
    # il canale: video vince se lo nomina, se no il telefono se lo chiede
    if re.search(r"videochiam|video\s*call|google meet|\bmeet\b|\bzoom\b|\bteams\b", low):
        v["canale"] = "video"
    elif re.search(r"telefon|al cellulare|chiamarmi|mi chiami|mi (?:pu[oò]'?|potete|potrebbe) chiamare|chiamatemi|squillo", low):
        v["canale"] = "telefono"
    if re.search(r"\bdal\s+luned[iì]'?\s*(?:al|-)\s*", low):
        v["lunedi"] = True
    for f in incontro:
        # la settimana
        if "settimana" not in v:
            lun = scritto_il - datetime.timedelta(days=scritto_il.weekday())
            if re.search(r"prossima settimana|settimana prossima|settimana (?:che viene|entrante)", f):
                v["settimana"] = (lun + datetime.timedelta(days=7)).isoformat()
            elif re.search(r"(?:fra|tra) due settimane", f):
                v["settimana"] = (lun + datetime.timedelta(days=14)).isoformat()
            elif re.search(r"questa settimana|in settimana|entro (?:la|questa) settimana|entro venerd", f):
                v["settimana"] = lun.isoformat()
        # il giorno: «oggi», «domani», un giorno della settimana (non «ad oggi», non «oggi non posso»)
        if "giorno" not in v:
            g = None
            pulita = re.sub(r"\b(?:ad|a|fino ad|da|per) oggi\b|oggi come oggi", " ", f)
            if re.search(r"\boggi\b|in giornata|oggi pomeriggio|stamattina|questo pomeriggio", pulita) and \
                    not re.search(r"\bnon\b[^.]{0,25}\boggi\b|\boggi\b[^.]{0,15}\bnon\b", pulita):
                g = scritto_il
                v["oggi"] = True
            elif re.search(r"\bdomani\b", f) and not re.search(r"\bnon\b[^.,]{0,10}\bdomani\b|\bdomani\b[^.]{0,15}\bnon\b", f):
                g = scritto_il + datetime.timedelta(days=1)
            else:
                m = _GIORNO_SET.search(f)
                if m:
                    wd = [x[:5] for x in _GSET].index(m.group(1).lower()[:5])
                    g = scritto_il + datetime.timedelta(days=(wd - scritto_il.weekday()) % 7 or 7)
                    if m.group(2):
                        try:
                            esatto = g.replace(day=int(m.group(2)))
                            if esatto.weekday() == wd and esatto > scritto_il:
                                g = esatto
                        except ValueError:
                            pass
                    if wd == 0:
                        v["lunedi"] = True
            if g:
                v["giorno"] = g.isoformat()
                o = re.search(r"(?<!sino )(?<!fino )(?<!entro )(?<!dalle )\balle\s+" + _ORA_N, f)
                if o:
                    v["ora"] = "%d:%02d" % _hm(o.group(1), o.group(2))
        # la fascia
        if "dalle" not in v:
            m = re.search(r"dopo\s+le\s+" + _ORA_N, f)
            if m:
                h, mi = _hm(m.group(1), m.group(2))
                inizio = datetime.datetime(2000, 1, 1, h, mi) + datetime.timedelta(minutes=30)
                v["dalle"] = f"{inizio.hour}:{inizio.minute:02d}"
                v["fascia"] = f"dopo le {_testo(h, mi)}"
            else:
                m = re.search(r"(?:a partire )?dalle\s+" + _ORA_N, f)
                if m:
                    h, mi = _hm(m.group(1), m.group(2))
                    v["dalle"] = f"{h}:{mi:02d}"
                    v["fascia"] = f"dalle {_testo(h, mi)}"
        if "entro" not in v:
            m = re.search(r"(?:sino|fino|entro)\s+alle\s+" + _ORA_N + r"|prima delle\s+" + _ORA_N, f)
            if m:
                h, mi = _hm(m.group(1) or m.group(3), m.group(2) or m.group(4))
                v["entro"] = f"{h}:{mi:02d}"
                f0 = v.get("fascia") or ""
                v["fascia"] = (f"tra le {f0[len('dopo le '):]} e le {_testo(h, mi)}" if f0.startswith("dopo le ")
                               else f"{f0} alle {_testo(h, mi)}" if f0 else f"entro le {_testo(h, mi)}")
            else:
                m = re.search(r"(?:dalle\s+\d{1,2}(?:[:.]\d{2})?)\s*(?:-|/|alle)\s*" + _ORA_N, f)
                if m:
                    h, mi = _hm(m.group(1), m.group(2))
                    v["entro"] = f"{h}:{mi:02d}"
                    v["fascia"] = (v.get("fascia", "") + f" alle {_testo(h, mi)}").strip()
        if "dalle" not in v and "entro" not in v:
            senza_saluti = re.sub(r"buon(?:a|o)?\s+(?:pomeriggio|mattinata|giornata)", " ", f)
            if re.search(r"\bpomeriggio\b", senza_saluti):
                v.update({"dalle": "14:30", "fascia": "nel pomeriggio"})
            elif re.search(r"\bmattin(?:a|ata)\b", senza_saluti):
                v.update({"entro": "13:00", "fascia": "di mattina"})
    if orario_iso and "giorno" not in v:
        try:
            o = datetime.datetime.fromisoformat(str(orario_iso)[:16])
            if o.date() >= scritto_il:
                v["giorno"] = o.date().isoformat()
                if o.hour or o.minute:
                    v["ora"] = f"{o.hour}:{o.minute:02d}"
        except ValueError:
            pass
    if v.get("giorno") and v.get("settimana"):
        v.pop("settimana")                      # un giorno preciso dice gia' la settimana
    return v


def _hhmm(x):
    h, m = str(x).split(":")
    return int(h), int(m)


def finestra(v, oggi):
    """I giorni dentro il vincolo (lista di date, gia' rispetto a oggi), o None se non c'e' vincolo di giorno."""
    if v.get("giorno"):
        g = datetime.date.fromisoformat(v["giorno"])
        return [g] if g >= oggi else []
    if v.get("settimana"):
        lun = datetime.date.fromisoformat(v["settimana"])
        return [lun + datetime.timedelta(days=i) for i in range(5) if lun + datetime.timedelta(days=i) >= oggi]
    return None


def nella_fascia(h, mi, v):
    """L'orario h:mi sta nella fascia chiesta (inizio dopo «dalle», la call di un'ora finisce entro «entro»)?"""
    if v.get("ora") and v.get("giorno") and not (v.get("dalle") or v.get("entro")):
        return True
    t = h * 60 + mi
    if v.get("dalle") and t < _hhmm(v["dalle"])[0] * 60 + _hhmm(v["dalle"])[1]:
        return False
    if v.get("entro") and t + 60 > _hhmm(v["entro"])[0] * 60 + _hhmm(v["entro"])[1]:
        return False
    return True


def rispettati(esteso, v, oggi):
    """Gli orari proposti (l'esteso) stanno tutti dentro i vincoli? Puro: lo usa chi scrive la frase."""
    o = leggi(esteso, oggi)
    if not o:
        return False
    giorni = finestra(v, oggi)
    return all((giorni is None or d in giorni) and nella_fascia(h, mi, v) for d, h, mi in o)


def _quel_giorno(g, oggi):
    if g == oggi:
        return "oggi"
    if 0 < (oggi - g).days < 7:
        return GIORNI[g.weekday()] + (" scorsa" if g.weekday() == 6 else " scorso")
    if 0 < (g - oggi).days < 7:
        return GIORNI[g.weekday()]
    return f"il {g.day} {MESI[g.month - 1]}"


def premessa(v, esteso, oggi):
    """LA FRASE CHE RICONOSCE QUELLO CHE HA CHIESTO (3/11), prima di «Le propongo». Vuota se non ha
    chiesto niente. Se il vincolo e' rispettato lo dice («Come mi aveva chiesto, ci sentiamo questa
    settimana.»); se il calendario non lo permette, o il suo giorno e' passato mentre aspettava, lo
    riconosce, e gli orari sono i primi liberi piu' vicini."""
    if not v:
        return ""
    o = leggi(esteso, oggi)
    giorni = finestra(v, oggi)
    dentro_giorni = giorni is None or (bool(o) and all(d in giorni for d, _, _ in o))
    dentro_fascia = bool(o) and all(nella_fascia(h, mi, v) for _, h, mi in o)
    pezzi_come = []
    scuse = ""
    if v.get("giorno"):
        g = datetime.date.fromisoformat(v["giorno"])
        if g < oggi:
            scuse = f"Mi scusi se {_quel_giorno(g, oggi)} non sono riuscito a sentirla come mi aveva proposto."
        elif not dentro_giorni:
            scuse = f"{_quel_giorno(g, oggi).capitalize()} purtroppo ho l'agenda già piena."
        elif g != oggi or not v.get("oggi"):
            pezzi_come.append(_quel_giorno(g, oggi))
    elif v.get("settimana"):
        lun = datetime.date.fromisoformat(v["settimana"])
        lun_oggi = oggi - datetime.timedelta(days=oggi.weekday())
        if lun + datetime.timedelta(days=4) < oggi:
            scuse = "Mi scusi se le rispondo solo ora."
        elif not dentro_giorni:
            scuse = ("Questa settimana" if lun == lun_oggi else "Quella settimana") + " purtroppo ho l'agenda già piena."
        else:
            pezzi_come.append("questa settimana" if lun == lun_oggi else "la prossima settimana" if lun == lun_oggi + datetime.timedelta(days=7)
                              else f"la settimana del {lun.day} {MESI[lun.month - 1]}")
    if v.get("canale") == "telefono":
        pezzi_come.append("al telefono")
    if v.get("fascia"):
        if dentro_fascia:
            pezzi_come.append(v["fascia"])
        else:
            scuse = (scuse + " " if scuse else "") + f"{v['fascia'][:1].upper()}{v['fascia'][1:]} purtroppo nei prossimi giorni sono già impegnato."
    come = f"Come mi aveva chiesto, ci sentiamo {' '.join(pezzi_come)}." if pezzi_come else ""
    return " ".join(x for x in (scuse, come) if x)


def canale(v):
    """Come si chiama la call nella mail: «telefonata» se l'ha chiesta al telefono, se no «videochiamata»."""
    return "telefonata" if (v or {}).get("canale") == "telefono" else "videochiamata"


def applica(testo, v, esteso, oggi, premessa_vecchia=None):
    """Il canale e la premessa nella mail (3/11): «videochiamata» diventa «telefonata» se l'ha chiesta
    al telefono, e la premessa va su una riga sua prima di «Le propongo» (mai punto-spazio-e-continua).
    `premessa_vecchia` (azione.orari_premessa) si sostituisce quando gli orari si rifanno.
    Torna (testo, premessa)."""
    if not v or not testo:
        return testo, ""
    t = testo
    if canale(v) == "telefonata":
        t = re.sub(r"\bvideochiamata\b", "telefonata", t)
    p = premessa(v, esteso, oggi)
    if premessa_vecchia and premessa_vecchia in t:
        t = t.replace(premessa_vecchia + "\n", p + "\n" if p else "", 1) if premessa_vecchia + "\n" in t else t.replace(premessa_vecchia, p, 1)
    elif p:
        m = re.search(r"Le propongo\b", t)
        if m:
            t = t[:m.start()].rstrip(" ") + ("\n" if m.start() and t[m.start() - 1] != "\n" else "") + p + "\n" + t[m.start():]
    return t, p


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
