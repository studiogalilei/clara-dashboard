#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""LA CLARA INTELLIGENTE: il lettore delle risposte (20/10/2026).

PERCHE' ESISTE
Le risposte dei lead le classificavano liste di parole (sync_v2.classifica). Il 19/10
hanno perso 4 si' («noi siamo interessati grazie», «puo' inviarmi il report») e
allargarle crea falsi si' (provato). Il senso di quello che scrive una persona lo
decide l'AI, sul testo suo (regola del 12/10); le liste restano solo come rete per
i casi gravi («Cancellami», «non scrivetemi», diffida).

DA DOVE VIENE
E' il lettore del mattone 5 di Clara nuova (~/Documents/clara-nuova,
supabase/functions/clara/: pulizia.ts, lettore.ts, modello.ts), portato in Python:
  1. la pulizia: quello che ha scritto la persona, senza la nostra mail citata,
     il nostro oggetto in testa, la firma e l'informativa (solo_suo);
  2. i fatti dal codice: a che passo risponde, se l'analisi e' gia' partita;
  3. UNA chiamata al modello, con le istruzioni e la carta dei 55 casi
     (scripts/lettore_regole.json) e l'uscita a schema fisso;
  4. le verifiche del codice, che possono solo portare a Dre (da_classificare):
     il caso esiste, i numeri e gli indirizzi stanno davvero nel messaggio, una
     macchina non dice si', la sicurezza, la rete dei casi gravi;
  5. la seconda lettura, alla cieca, sulle chiusure (un no, un automatico): se
     trova un'apertura, a Dre.
Rigiocato sulle 1.087 risposte etichettate (scripts/misure/rigioco_lettore.py).

LA CLASSE (quella del vecchio Workspace)
  positivo | negativo | ooo | rinvio | automatico | da_classificare
piu' caldo (vuole sentirsi: lo decide Dre, Clara non scrive) e non_scrivere (mai
piu' una mail). Nel database «automatico» diventa «ooo» (la sequenza riprende) e
un «non scrivetemi» diventa «soppresso»: classe_db().

QUANDO IL MODELLO NON C'E'
Senza chiave, oltre il tetto di spesa del giorno, o se il modello non risponde, si
ricade sulle liste di parole e lo si scrive (fonte «liste», motivo). Mai un blocco
muto: la scheda Clara legge il conto in snella_numeri, chiave «lettore».

L'INTERRUTTORE
operazioni.lettore (attiva) e la modalita' in snella_numeri «lettore» (dati.modo):
  ombra   il sync legge col lettore e scrive solo accanto (enriched.lettore), la
          classe resta quella delle liste;
  acceso  la classe la decide il lettore.

USO
  python3 scripts/lettore.py --conto            il conto del giorno nella scheda (l'operazione)
  python3 scripts/lettore.py --ombra [--giorni 3] lettore e liste sulle risposte vere, a video
  python3 scripts/lettore.py --riclassifica [--prova] [--cache FILE]  rilegge i positivi e i da classificare
  python3 scripts/lettore.py --modo ombra|acceso  cambia la modalita'
"""
import datetime
import hashlib
import html as ihtml
import json
import os
import re
import sys
import time
import unicodedata
import urllib.error
import urllib.request

QUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, QUI)

REGOLE = json.load(open(os.path.join(QUI, "lettore_regole.json"), encoding="utf-8"))
CASI = {c["id"]: c for c in REGOLE["casi"]}
MISURE = REGOLE["misure"]
RETE = [re.compile(e, re.I | re.M) for e in REGOLE["rete_non_scrivere"]]
RETE_MAX_CARATTERI = 20_000

CLASSI = ("positivo", "negativo", "ooo", "rinvio", "automatico", "da_classificare")

# I prezzi in dollari per milione di token (listino Anthropic, ottobre 2026).
PREZZI = {
    "claude-sonnet-5": {"in": 2.0, "out": 10.0, "cache": 0.2, "scrittura": 2.5},
    "claude-sonnet-5-5": {"in": 2.0, "out": 10.0, "cache": 0.2, "scrittura": 2.5},
    "claude-haiku-5-5": {"in": 0.10, "out": 0.50, "cache": 0.01, "scrittura": 0.125},
}
TETTO_GIORNO = 2.0          # dollari al giorno per il lettore dal vivo (circa 0,01 $ a risposta: 200 risposte)
ATTESA = 120                # secondi per una chiamata


def _env(nome):
    v = os.environ.get(nome)
    if v:
        return v
    for f in (".env.local", ".env"):
        p = os.path.join(os.path.dirname(QUI), f)
        if os.path.exists(p):
            for riga in open(p, encoding="utf-8"):
                if riga.strip().startswith(nome + "="):
                    return riga.split("=", 1)[1].strip().strip("\"'")
    return None


def modello_scelto():
    """Il modello del lettore: LETTORE_MODELLO, se no il Sonnet del cervello."""
    v = _env("LETTORE_MODELLO")
    if v:
        return v
    try:
        import cervello
        return cervello.MODELLO_CLAUDE
    except Exception:                                            # noqa: BLE001
        return "claude-sonnet-5"


# ── 1. la pulizia (pulizia.ts) ─────────────────────────────────────────────────

def normalizza(s):
    s = unicodedata.normalize("NFC", s or "")
    s = re.sub(r"\r\n?|[  ]", "\n", s)
    s = re.sub(r"[​-‍⁠﻿]", "", s)
    s = re.sub(r"[ \t ]+", " ", s)
    s = re.sub(r" *\n *", "\n", s)
    s = re.sub(r"\n{2,}", "\n", s)
    return s.strip()


def testo_da_html(h):
    b = str(h or "")
    b = re.sub(r"<(script|style|head)\b[\s\S]*?</\1>", " ", b, flags=re.I)
    b = re.sub(r"<br\s*/?>|</div>|</p>|</li>|</tr>|</h[1-6]>|</blockquote>", "\n", b, flags=re.I)
    b = re.sub(r"<[^>]+>", "", b)
    return normalizza(ihtml.unescape(b))


PAROLA = re.compile(r"[^\W_]+")
PAROLE_DI_FILA = 8
PAROLE_DOPO = 40
PARTE_NOSTRA = 0.6
PRIMA_DELLA_CITAZIONE = 400


def _parole(s):
    return [(m.group(0), m.start()) for m in PAROLA.finditer(s.lower())]


def impronte_nostre(testi):
    fuori = set()
    for t in testi:
        w = [p for p, _ in _parole(t)]
        for i in range(0, len(w) - PAROLE_DI_FILA + 1):
            fuori.add(" ".join(w[i:i + PAROLE_DI_FILA]))
    return fuori


def inizio_del_nostro(testo, impronte):
    if not impronte:
        return -1
    w = _parole(testo)
    for i in range(0, len(w) - PAROLE_DI_FILA + 1):
        if " ".join(p for p, _ in w[i:i + PAROLE_DI_FILA]) in impronte:
            return w[i][1]
    return -1


def inizio_della_citazione(testo, impronte):
    if not impronte:
        return -1
    w = _parole(testo)
    nostro = [False] * len(w)
    for i in range(0, len(w) - PAROLE_DI_FILA + 1):
        if " ".join(p for p, _ in w[i:i + PAROLE_DI_FILA]) in impronte:
            for k in range(i, i + PAROLE_DI_FILA):
                nostro[k] = True
    for i in range(len(w)):
        if not nostro[i]:
            continue
        fine = min(len(w), i + PAROLE_DOPO)
        if sum(nostro[i:fine]) >= PARTE_NOSTRA * (fine - i):
            return w[i][1]
    return -1


INTESTAZIONE_IN_LINEA = re.compile("|".join([
    r"(?:^|[\s>*])(?:da|from|de|von|mittente)\s*:\s[\s\S]{0,400}?\b(?:oggetto|subject|betreff|asunto|objet)\s*:",
    r"(?:^|\s)(?:il giorno|il|on|am|el|le)\s[^\n]{0,160}?(?:\b\d{1,2}[:.]\d{2}\b|\b(?:19|20)\d{2}\b)[^\n]{0,160}?\b(?:ha scritto|wrote|a écrit|schrieb|escribió)\s*:",
    r"-{2,}\s*(?:original message|messaggio originale|messaggio inoltrato|forwarded message)",
    r"_{5,}",
]), re.I)


def _taglia_intestazione(t):
    da = max(0, len(t) - PRIMA_DELLA_CITAZIONE)
    m = INTESTAZIONE_IN_LINEA.search(t[da:])
    return t[:da + m.start()] if m else t


def _chiave_oggetto(s):
    s = normalizza(s).lower()
    s = re.sub(r"^(?:\s*(?:re|r|i|fw|fwd|rif)\s*:\s*)+", "", s, flags=re.I)
    return re.sub(r"\s+", " ", s).strip()


def _senza_oggetto(t, oggetti):
    chiavi = sorted([o for o in (_chiave_oggetto(x) for x in oggetti) if len(o) >= 6], key=len, reverse=True)
    if not chiavi:
        return t
    testa = t.lstrip()
    w = _parole(testa)
    for o in chiavi:
        wo = [p for p, _ in _parole(o)]
        if not wo or len(w) < len(wo):
            continue
        if all(w[i][0] == p for i, p in enumerate(wo)):
            p, da = w[len(wo) - 1]
            return re.sub(r"^[\s.,:;!?-]+", "", testa[da + len(p):])
    return t


CITAZIONE = re.compile(
    r"\n\s*(?:>\s*)?(?:"
    r"-{2,}\s*(?:original message|messaggio originale|messaggio inoltrato|forwarded message)"
    r"|(?:original message|messaggio originale)\s*-*\s*(?=\n)"
    r"|(?:_{5,}\s*\n\s*)?(?:da|from|de|von|mittente)\s*:[^\n]*(?:\n[^\n]*){0,12}?\n\s*(?:>\s*)?(?:oggetto|subject|betreff|asunto|objet)\s*:"
    r"|(?:_{5,}\s*\n\s*)?(?:da|from|de|von)\s*:[^\n]{0,300}?\b(?:oggetto|subject|betreff|asunto|objet)\s*:"
    r"|(?:a|to)\s*:[^\n]{0,200}\n\s*(?:>\s*)?(?:oggetto|subject)\s*:"
    r")", re.I)
SCRITTO = re.compile(r"\b(?:ha scritto|wrote)\s*:", re.I)
ORA = re.compile(r"\b\d{1,2}[:.]\d{2}\b")
DATA = re.compile(r"\b(?:19|20)\d{2}\b|\b\d{1,2}[/.-]\d{1,2}[/.-]\d{2,4}\b")
APERTURA = re.compile(r"(?<!\w)(?:il giorno|il|on|am|el|le)\s", re.I)


def _intestazione(t):
    for m in SCRITTO.finditer(t):
        fine = m.start()
        da = max(0, fine - 200)
        pezzo = t[da:fine]
        segni = [x.start() for x in ORA.finditer(pezzo)] + [x.start() for x in DATA.finditer(pezzo)]
        if not segni:
            continue
        aperture = list(APERTURA.finditer(pezzo[:max(segni)]))
        if not aperture:
            continue
        return da + aperture[-1].start()
    return None


SALUTI = re.compile(
    r"\n\s*(?:cordiali saluti|distinti saluti|un cordiale saluto|cari saluti|in attesa di|best regards|kind regards|"
    r"--\s*$|__+\s*$|cordialit[àa]|(?:porg|invi)\w*\s[^\n]{0,20}saluti|buon lavoro|"
    r"rest\w+ a (?:sua |vostra )?(?:completa )?disposizione)", re.I | re.M)
DISCLAIMER = re.compile("|".join([
    r"informativa privacy",
    r"(?:le |l')informazioni (?:incluse|contenute|trasmesse|presenti)",
    r"questo (?:messaggio|documento|e-?mail) (?:e'|è) (?:riservat|confidenzial|destinat)",
    r"il (?:presente|contenuto del) messaggio (?:e'|è)",
    r"this (?:communication|message|e-?mail|document) is (?:confidential|intended|reserved)",
    r"reg\.? ?ue ?2016/679|regolamento \(?ue\)? ?2016/679|\bgdpr\b|privacy:\s",
    r"destinatario indicato|ai sensi dell|\*{6,}",
    r"se (?:avete|hai) ricevuto (?:questo|questa) (?:messaggio|documento|mail|comunicazione) per errore",
    r"(?:il )?presente (?:messaggio|e-?mail|comunicazione)[^.\n]{0,60}(?:destinat|riservat|confidenzial)",
    r"quest[ao] (?:mail|e-?mail|messaggio|comunicazione) (?:contiene|(?:e'|è) (?:riservat|confidenzial|destinat))",
    r"(?:se|qualora) (?:ha|avete|hai|abbia|aveste|fosse stat[oa]) ricevut\w* [^.\n]{0,40}per errore",
]), re.I)
RIGA_D_INTESTAZIONE = re.compile(
    r"^\s*(?:>\s*)*(?:da|from|de|von|inviato|sent|data|date|a|to|cc|ccn|oggetto|subject|betreff|objet|asunto|mittente|destinatario)\s*:"
    r"|^\s*-{2,}|^\s*_{5,}\s*$|\b(?:ha scritto|wrote|a écrit|schrieb|escribió)\s*:\s*$", re.I)


def _tolto_non_nostro(resto, impronte):
    r = resto
    k = inizio_del_nostro(r, impronte)
    if k >= 0:
        r = r[:k]
        base = max(0, len(r) - PRIMA_DELLA_CITAZIONE)
        tutte = list(INTESTAZIONE_IN_LINEA.finditer(r[base:]))
        if tutte:
            r = r[:base + tutte[-1].start()]
    righe = [re.sub(r"^\s*(?:>\s*)+", "", x) for x in r.split("\n")]
    r = "\n".join(x for x in righe if not RIGA_D_INTESTAZIONE.search(x)).strip()
    return r if len(PAROLA.findall(r)) >= 3 else ""


def solo_suo(testo, nostre_testi=(), nostre_oggetti=()):
    """Quello che ha scritto la persona: {con_firma, senza_firma, tolto}."""
    t = "\n" + normalizza(testo)
    t = "\n" + _senza_oggetto(t, nostre_oggetti)
    intero = t
    impronte = impronte_nostre(nostre_testi)
    c = CITAZIONE.search(t)
    if c:
        t = t[:c.start()]
    h = _intestazione(t)
    if h is not None:
        t = t[:h]
    n = inizio_della_citazione(t, impronte)
    if n >= 0:
        t = _taglia_intestazione(t[:n])
    resto = intero[len(t):]
    righe = t.split("\n")
    citate = [r for r in righe if r.lstrip().startswith(">")]
    t = "\n".join(r for r in righe if not r.lstrip().startswith(">")).strip()
    con_firma = t
    tolto = _tolto_non_nostro("\n".join(citate + [resto]), impronte)
    d = DISCLAIMER.search(t)
    if d:
        t = t[:d.start()]
    f = SALUTI.search("\n" + t)
    if f and len(t[:max(0, f.start() - 1)].strip()) >= 25:
        t = t[:max(0, f.start() - 1)]
    return {"con_firma": con_firma, "senza_firma": t.strip(), "tolto": tolto}


# ── 2. il filo e i fatti ────────────────────────────────────────────────────────

def _testo_o_none(v):
    if v is None:
        return None
    if isinstance(v, list):
        return ", ".join(map(str, v)) or None
    s = str(v).strip()
    return None if s in ("", "None") else s


def _iso(s):
    s = str(s or "")
    if not s:
        return ""
    if not re.search(r"[zZ]|[+-]\d{2}:?\d{2}$", s):
        s += "Z"
    try:
        return datetime.datetime.fromisoformat(s.replace("Z", "+00:00")).astimezone(datetime.timezone.utc).isoformat()
    except ValueError:
        return ""


def messaggi_da_smartlead(storia):
    """La message-history di Smartlead (o gia' la nostra forma) nella forma del lettore."""
    fuori = []
    for m in storia or []:
        if "tipo" in m and "testo" in m:                    # gia' nella nostra forma
            fuori.append(m)
            continue
        tipo = str(m.get("type") or "").upper()
        if tipo not in ("SENT", "REPLY"):
            continue
        try:
            seq = int(m.get("email_seq_number"))
        except (TypeError, ValueError):
            seq = None
        att = m.get("attachments")
        fuori.append({
            "tipo": tipo, "il": _iso(m.get("time")), "da": _testo_o_none(m.get("from")),
            "cc": _testo_o_none(m.get("cc")), "oggetto": _testo_o_none(m.get("subject")),
            "passo": seq if tipo == "SENT" and seq and seq > 0 else None,
            # Smartlead scrive attachments solo quando ci sono: assente vale 0 (R5.9 di Clara nuova)
            "allegati": len(att) if isinstance(att, list) else 0,
            "testo": testo_da_html(m.get("email_body")),
        })
    return sorted(fuori, key=lambda x: x["il"])


GIORNI = ["lunedì", "martedì", "mercoledì", "giovedì", "venerdì", "sabato", "domenica"]


def _roma(iso):
    try:
        import zoneinfo
        d = datetime.datetime.fromisoformat(iso).astimezone(zoneinfo.ZoneInfo("Europe/Rome"))
        return f"{GIORNI[d.weekday()]} {d:%d/%m/%Y, %H:%M}"
    except (ValueError, TypeError):
        return "?"


def _taglia(s, n):
    return s if len(s) <= n else s[:n].rstrip() + " […]"


def prepara(messaggi, indice, analisi_nel_crm=False):
    """Il testo per il lettore sulla risposta messaggi[indice] (prepara_lettura di lettore.ts)."""
    risposta = messaggi[indice]
    prima = messaggi[:indice]
    nostre = [m for m in prima if m["tipo"] == "SENT"]
    fuori_seq = [m for m in nostre if m["passo"] is None]
    testi = [m["testo"] for m in nostre]
    oggetti = [m["oggetto"] for m in nostre if m.get("oggetto")]
    pulito = solo_suo(risposta["testo"], testi, oggetti)
    fatti = {
        "il": risposta["il"],
        "passo": next((m["passo"] for m in reversed(nostre) if m["passo"] is not None), None),
        # un allegato che non si sa (None, lo storico) conta come analisi; il CRM lo sa anche lui
        "analisi_mandata": bool(analisi_nel_crm) or any(m["allegati"] is None or m["allegati"] > 0 for m in fuori_seq),
        "nostre_fuori_sequenza": len(fuori_seq),
        "sue_prima": sum(1 for m in prima if m["tipo"] == "REPLY"),
    }
    righe = ["FATTI (dal codice)",
             f"- data della risposta: {_roma(risposta['il'])} (ora italiana)",
             f"- risponde al passo {fatti['passo'] if fatti['passo'] is not None else '?'} della sequenza",
             f"- analisi già mandata: {'sì' if fatti['analisi_mandata'] else 'no'}",
             f"- nostre mail fuori sequenza prima di questa risposta: {fatti['nostre_fuori_sequenza']}",
             f"- sue risposte prima di questa: {fatti['sue_prima']}",
             "", "CASI IN FORMAZIONE", "- nessuno", "",
             "FILO (dal più vecchio; le nostre mail accorciate)"]
    visti = prima[max(0, len(prima) - MISURE["messaggi_max"]):]
    if len(visti) < len(prima):
        righe.append(f"({len(prima) - len(visti)} messaggi più vecchi non mostrati)")
    for k, m in enumerate(visti):
        chi = ("NOI" + (f" · passo {m['passo']}" if m["passo"] is not None else " · fuori sequenza")) if m["tipo"] == "SENT" else "LORO"
        righe.append(f"[{k + 1}] {chi} · {_roma(m['il'])}" + (f" · oggetto: {m['oggetto']}" if m.get("oggetto") else "")
                     + (f" · {m['allegati']} allegati" if m.get("allegati") else ""))
        corpo = m["testo"] if m["tipo"] == "SENT" else solo_suo(m["testo"], testi, oggetti)["con_firma"]
        righe.append(_taglia(corpo, MISURE["nostra_max_caratteri"]) or "(vuoto)")
    righe += ["", f"RISPOSTA DA LEGGERE · {_roma(risposta['il'])}" + (f" · da: {risposta['da']}" if risposta.get("da") else "")
              + (f" · cc: {risposta['cc']}" if risposta.get("cc") else ""),
              "TESTO PULITO:", pulito["con_firma"] or "(vuoto)"]
    if risposta["testo"].strip() != pulito["con_firma"].strip():
        righe += ["", "TESTO GREZZO (con quello che il pulito ha tolto):",
                  _taglia(risposta["testo"], MISURE["grezzo_max_caratteri"]) or "(vuoto)"]
    return {"fatti": fatti, "pulito": pulito, "testo": "\n".join(righe), "risposta": risposta,
            "nostre_testi": testi}


def istruzioni_lettore():
    carta = []
    for c in REGOLE["casi"]:
        es = f" Es.: {', '.join('«' + f + '»' for f in c['frasi'])}." if c["frasi"] else ""
        carta.append(f"{c['id']} «{c['nome']}»: {c['quando']}.{es}")
    return REGOLE["istruzioni"] + "\n\nLA CARTA DEI CASI\n" + "\n".join(carta)


# ── 3. l'uscita a schema fisso (SCHEMA_LETTORE di lettore.ts) ─────────────────

_T = {"type": ["string", "null"]}
SCHEMA_LETTORE = {
    "type": "object", "additionalProperties": False,
    "required": ["autore", "testo_suo", "caso", "caso_nuovo_nome", "caso_nuovo_descrizione", "sicurezza", "perche",
                 "porta_aperta", "porta_aperta_frase", "motivo", "caldo", "caldo_motivi", "caldo_frase", "consiglio",
                 "numeri", "orario_chiesto", "orario_iso", "data_rientro", "data_ricontatto", "indirizzi_nuovi",
                 "elementi", "saluto_nome", "tu", "non_scrivere"],
    "properties": {
        "autore": {"type": "string", "enum": ["persona", "automatico", "automatico_con_risposta_vera"]},
        "testo_suo": {"type": "string"},
        "caso": {"type": "string", "description": "C01-C55, l'id di un caso in formazione (N01...), oppure «nuovo»"},
        "caso_nuovo_nome": _T, "caso_nuovo_descrizione": _T,
        "sicurezza": {"type": "string", "enum": ["alta", "media", "bassa"]},
        "perche": {"type": "string"},
        "porta_aperta": {"type": "boolean"}, "porta_aperta_frase": _T,
        "motivo": {"type": "string", "enum": ["carico_di_lavoro", "periodo", "gia_seguiti", "budget", "altro", "nessuno"]},
        "caldo": {"type": "boolean"},
        "caldo_motivi": {"type": "array", "items": {"type": "string", "enum": [
            "vuole_sentirti", "chiede_chiamata", "lascia_numero", "propone_orario", "carico"]}},
        "caldo_frase": _T, "consiglio": _T,
        "numeri": {"type": "array", "items": {"type": "object", "additionalProperties": False, "required": ["numero", "dove"],
                                              "properties": {"numero": {"type": "string"},
                                                             "dove": {"type": "string", "enum": ["messaggio", "firma"]}}}},
        "orario_chiesto": _T,
        "orario_iso": {"type": ["string", "null"], "description": "AAAA-MM-GGTHH:MM, ora italiana, se giorno e ora si capiscono"},
        "data_rientro": _T, "data_ricontatto": _T,
        "indirizzi_nuovi": {"type": "array", "items": {"type": "object", "additionalProperties": False,
                                                       "required": ["indirizzo", "ruolo"],
                                                       "properties": {"indirizzo": {"type": "string"},
                                                                      "ruolo": {"type": "string", "enum": [
                                                                          "stessa_persona", "collega", "ufficio_generico", "altra_azienda"]}}}},
        "elementi": {"type": "array", "items": {"type": "string", "enum": [
            "domanda", "dubbio", "vincolo_di_tempo", "non_ho_ricevuto", "tramite", "giorno_o_fascia", "numero", "mi_chiami",
            "la_chiamo_io", "ironia", "scetticismo", "persona_in_copia", "tu"]}},
        "saluto_nome": _T, "tu": {"type": "boolean"}, "non_scrivere": {"type": "boolean"},
    },
}
SCHEMA_CALDO = {"type": "object", "additionalProperties": False, "required": ["caldo", "frase"],
                "properties": {"caldo": {"type": "boolean"}, "frase": _T}}
SCHEMA_SECONDA = {"type": "object", "additionalProperties": False, "required": ["apertura", "frase"],
                  "properties": {"apertura": {"type": "boolean"}, "frase": _T}}


# ── 4. il modello (Anthropic, Messages API) ─────────────────────────────────────

class Guasto(Exception):
    pass


def costo(modello, nuovi, letti, scritti, fuori):
    p = PREZZI.get(modello) or PREZZI["claude-sonnet-5"]
    return (nuovi * p["in"] + letti * p["cache"] + scritti * p["scrittura"] + fuori * p["out"]) / 1e6


def corpo_richiesta(ruolo, istruzioni, testo, schema, modello):
    """La domanda al modello: istruzioni (uguali per ogni lettura) in cache, sforzo basso, uscita a schema."""
    r_conf = REGOLE["ruoli"]["lettore" if ruolo == "lettore" else "seconda_lettura"]
    return {
        "model": modello,
        "max_tokens": r_conf["max_token"],
        "system": [{"type": "text", "text": istruzioni, "cache_control": {"type": "ephemeral"}}],
        "messages": [{"role": "user", "content": testo}],
        "output_config": {"effort": "low", "format": {"type": "json_schema", "schema": schema}},
    }


def uscita_del_messaggio(d, schema):
    """Il JSON dell'uscita, controllato nella forma. Solleva Guasto se non va."""
    if d.get("stop_reason") != "end_turn":
        raise Guasto(f"risposta incompleta ({d.get('stop_reason')})")
    testo_out = "".join(b.get("text", "") for b in d.get("content") or [] if b.get("type") == "text")
    try:
        uscita = json.loads(testo_out)
    except ValueError:
        raise Guasto("uscita non JSON")
    for k in schema["required"]:
        if k not in uscita:
            raise Guasto(f"uscita senza il campo {k}")
    return uscita


def chiedi_anthropic(ruolo, istruzioni, testo, schema, modello=None, registra="lettore"):
    """UNA chiamata: istruzioni in cache, uscita a schema fisso. Restituisce (dict, costo).
    Scrive la chiamata in uso_modelli (scopo = registra), anche quando l'uscita e' incompleta (pagata)."""
    chiave = _env("ANTHROPIC_API_KEY")
    if not chiave:
        raise Guasto("manca la chiave Anthropic")
    modello = modello or modello_scelto()
    corpo = corpo_richiesta(ruolo, istruzioni, testo, schema, modello)
    req = urllib.request.Request("https://api.anthropic.com/v1/messages", data=json.dumps(corpo).encode("utf-8"), method="POST")
    req.add_header("x-api-key", chiave)
    req.add_header("anthropic-version", "2023-06-01")
    req.add_header("content-type", "application/json")
    d = None
    for tentativo in range(3):
        try:
            with urllib.request.urlopen(req, timeout=ATTESA) as r:
                d = json.loads(r.read())
            break
        except urllib.error.HTTPError as e:
            msg = e.read().decode("utf-8", "replace")[:200]
            if e.code in (429, 500, 502, 503, 529) and tentativo < 2:
                time.sleep(3 * (tentativo + 1))
                continue
            raise Guasto(f"Anthropic {e.code}: {msg}")
        except (urllib.error.URLError, TimeoutError, OSError) as e:
            if tentativo < 2:
                time.sleep(3 * (tentativo + 1))
                continue
            raise Guasto(f"Anthropic non risponde: {e}")
    u = d.get("usage") or {}
    nuovi, letti, scritti = int(u.get("input_tokens") or 0), int(u.get("cache_read_input_tokens") or 0), int(u.get("cache_creation_input_tokens") or 0)
    fuori = int(u.get("output_tokens") or 0)
    spesa = costo(modello, nuovi, letti, scritti, fuori)
    _registra(registra, modello, nuovi, letti, scritti, fuori)
    return uscita_del_messaggio(d, schema), spesa


def _registra(scopo, modello, nuovi, letti, scritti, fuori, sconto=1.0):
    """Una riga in uso_modelli. token_in e' pesato per il prezzo (la cache letta costa un decimo,
    quella scritta un quarto in piu'): cosi' token_in x prezzo pieno e' la spesa vera, e il tetto del
    giorno si calcola dal database."""
    if not scopo:
        return
    try:
        from stanza import sb
        # anche in prova a secco: la chiamata e' pagata lo stesso, e la spesa si conta (20/10: la prova
        # della riclassifica aveva speso 2,6 $ senza una riga)
        pesati = int(round((nuovi + letti * 0.1 + scritti * 1.25) * sconto))
        sb("POST", "/rest/v1/uso_modelli", {"script": os.path.basename(sys.argv[0] or "?")[:60], "scopo": scopo,
                                             "modello": modello, "token_in": pesati, "token_out": int(round(fuori * sconto))},
           {"Prefer": "return=minimal"})
    except Exception:                                            # noqa: BLE001
        pass


def spesa_di_oggi(scopo="lettore"):
    """Quanto ha speso il lettore oggi (ora di Roma), da uso_modelli. None se non si legge."""
    try:
        import zoneinfo
        from stanza import sb_tutte
        oggi = datetime.datetime.now(zoneinfo.ZoneInfo("Europe/Rome")).replace(hour=0, minute=0, second=0, microsecond=0)
        righe = sb_tutte(f"/rest/v1/uso_modelli?select=id,modello,token_in,token_out&scopo=eq.{scopo}"
                         f"&il=gte.{oggi.astimezone(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%S')}") or []
        return sum(costo(r.get("modello"), int(r.get("token_in") or 0), 0, 0, int(r.get("token_out") or 0)) for r in righe)
    except Exception:                                            # noqa: BLE001
        return None


# ── 5. le verifiche e la decisione ──────────────────────────────────────────────

SEQUENZA_DI_CIFRE = re.compile(r"\+?\d[\d\s./()-]{4,}\d")
INDIRIZZO_EMAIL = re.compile(r"[^@\s<>\"',;()]+@[^@\s<>\"',;()]+\.[a-z]{2,}", re.I)


def _cifre(s):
    t = s.strip()
    return ("+" if t.startswith("+") else "") + re.sub(r"\D", "", t)


def _nazionale(c):
    x = c.lstrip("+")
    if x.startswith("0039"):
        x = x[4:]
    elif x.startswith("39") and len(x) in (11, 12):
        x = x[2:]
    return x


def _numeri_nel(testo):
    return {n for n in (_nazionale(_cifre(m.group(0))) for m in SEQUENZA_DI_CIFRE.finditer(testo)) if len(n) >= 6}


def rete_su(testi):
    return any(e.search(t[:RETE_MAX_CARATTERI]) for e in RETE for t in testi if t)


def verifica(l, p):
    pulito = p["pulito"]
    testo_ris = p["risposta"]["testo"]
    caso_valido = l.get("caso") in CASI
    testo_suo_nostro = inizio_del_nostro(l.get("testo_suo") or "", impronte_nostre(p["nostre_testi"])) >= 0
    nella = _numeri_nel(testo_ris)
    nostri = _numeri_nel("\n".join(p["nostre_testi"]))
    numeri, visti = [], set()
    for n in l.get("numeri") or []:
        naz = _nazionale(_cifre(str(n.get("numero") or "")))
        if len(naz) < 6 or naz not in nella or naz in nostri or naz in visti:
            continue
        visti.add(naz)
        numeri.append({"numero": str(n.get("numero")).strip(), "dove": n.get("dove")})
    motivi = [m for m in (l.get("caldo_motivi") or []) if m != "lascia_numero" or any(x["dove"] == "messaggio" for x in numeri)]
    testi_rete = [pulito["con_firma"], pulito["tolto"]]
    basso = testo_ris.lower()
    nostri_t = "\n".join(p["nostre_testi"]).lower()
    suoi = set(INDIRIZZO_EMAIL.findall((p["risposta"].get("da") or "").lower()))
    indirizzi = sorted({str(x.get("indirizzo") or "").strip().lower() for x in (l.get("indirizzi_nuovi") or [])})
    indirizzi = [x for x in indirizzi if re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", x) and x in basso and x not in nostri_t and x not in suoi]
    return {"caso_valido": caso_valido, "testo_suo_nostro": testo_suo_nostro, "numeri": numeri, "caldo_motivi": motivi,
            "rete": rete_su(testi_rete), "oltre_la_rete": any(len(t) > RETE_MAX_CARATTERI for t in testi_rete if t),
            "vuota": pulito["con_firma"].strip() == "", "indirizzi": indirizzi}


# La classe di ogni caso della carta, nel vecchio Workspace.
POSITIVI = {"C01", "C02", "C03", "C04", "C05", "C06", "C07", "C08", "C09", "C10", "C11", "C12",
            "C14", "C15", "C16", "C35", "C37"}
RINVII = {"C17", "C21", "C22", "C26"}
NEGATIVI = {"C19", "C24", "C25", "C27", "C28", "C30", "C40", "C42", "C49"}
FUORI_UFFICIO = {"C43", "C44", "C45", "C46"}
AUTOMATICI = {"C47", "C48"}
# Un no legato al momento, con uno spiraglio vero: si riprende (rinvio). Chi ha gia' un'agenzia (C27)
# con uno spiraglio no: se riscrivergli lo decide Dre (rigioco del 20/10: «siamo in fase di rifacimento
# con un'altra agenzia» letto come ripresa). C18 (critica l'analisi, anche chiudendo con un no) e C20
# (l'analisi non e' arrivata) li segue Dre.
CON_LA_PORTA = {"C19", "C25"}
# Chi e' irritato o chiede da dove abbiamo la sua mail non riceve mail automatiche: risponde Dre, se vuole.
MAI_AUTOMATICHE = {"C31", "C33"}
# Le classi con cui Clara scrive da sola (la prima risposta, la ripresa, il rientro).
SCRIVE = {"positivo", "rinvio", "ooo"}


def classe_del_caso(caso, porta_aperta=False, analisi=False):
    """La classe di un caso, prima o dopo l'analisi (la carta di Clara nuova: «prima» e «dopo»)."""
    if caso in POSITIVI:
        return "positivo"
    if caso == "C27" and porta_aperta:
        return "da_classificare"
    if caso in RINVII or (porta_aperta and caso in CON_LA_PORTA):
        # dopo l'analisi chi rimanda e' in conversazione con Dre: nessuna ripresa automatica
        return "da_classificare" if analisi else "rinvio"
    if caso in NEGATIVI:
        return "negativo"
    if caso == "C44" and not analisi:
        return "da_classificare"     # un collega a cui scrivere, prima dell'analisi: lo vede Dre
    if caso in FUORI_UFFICIO:
        return "ooo"
    if caso in AUTOMATICI:
        return "automatico"
    return "da_classificare"


def decidi(l, v, analisi=False):
    """La classe dalla lettura e dalle verifiche (decidiStato di lettore.ts, nelle classi del vecchio).
    Le difese possono solo portare a Dre (da_classificare), mai decidere un si' o un no."""
    perche = []
    caso = CASI.get(l.get("caso"))
    motivi = v["caldo_motivi"] or (["vuole_sentirti"] if caso and caso.get("caldo") else [])
    caldo = bool((l.get("caldo") or (caso and caso.get("caldo"))) and motivi and l.get("autore") != "automatico")
    non_scrivere = bool(l.get("non_scrivere"))
    if caso and caso["id"] in MAI_AUTOMATICHE:
        non_scrivere = True
        perche.append("irritato o chiede dei suoi dati: nessuna mail automatica")
    if not caso:
        classe = "da_classificare"
        perche.append(f"caso fuori dalla carta ({l.get('caso')}): a Dre")
    else:
        classe = classe_del_caso(caso["id"], bool(l.get("porta_aperta")), analisi)
        perche.append(f"{caso['id']} «{caso['nome']}»")
    if l.get("non_scrivere"):
        classe = "negativo"
        perche.append("chiede di non essere piu' contattato")
    vuole_sentirti = False
    if caldo and not non_scrivere and (caso is None or caso["id"] != "C13"):
        classe, vuole_sentirti = "positivo", True
        perche.append(f"caldo ({', '.join(motivi)}): lo chiama Dre")
    if caldo and (non_scrivere or v["rete"]):
        classe, vuole_sentirti = "da_classificare", False
        perche.append("caldo ma chiede di sparire: decide Dre")

    def a_dre(motivo):
        nonlocal classe
        if classe != "da_classificare" and not vuole_sentirti:
            classe = "da_classificare"
            perche.append(motivo)

    if v["rete"] and not non_scrivere:
        a_dre("la rete dei casi gravi ha preso una frase («non scrivetemi», dati, diffida): a Dre")
        non_scrivere = True                                  # nessuna mail automatica finche' Dre non decide
    if v["testo_suo_nostro"]:
        a_dre("il testo suo contiene un pezzo delle nostre mail: a Dre")
    if v["oltre_la_rete"] and not non_scrivere:
        a_dre("testo troppo lungo per la rete: a Dre")
    if v["vuota"] and not (caso and caso.get("automatico")):
        a_dre("la risposta non ha parole sue: a Dre")
    if caso and caso.get("indirizzo") and not v["indirizzi"] and classe in SCRIVE:
        a_dre(f"{caso['id']} vuole un indirizzo nuovo, e nella risposta non c'e': a Dre")
    if l.get("autore") == "automatico" and caso and not caso.get("automatico"):
        a_dre(f"un messaggio automatico letto come {caso['id']}: a Dre")
    if l.get("sicurezza") == "bassa" and not non_scrivere:
        a_dre("sicurezza bassa: a Dre")
    if classe in SCRIVE and not vuole_sentirti and l.get("sicurezza") != "alta":
        a_dre(f"Clara scriverebbe, ma la sicurezza e' {l.get('sicurezza')}: a Dre")
    if non_scrivere and l.get("sicurezza") == "bassa":
        classe = "da_classificare"
    return {"classe": classe, "caldo": caldo, "non_scrivere": non_scrivere, "perche": perche,
            "seconda_lettura": classe in ("negativo", "automatico")}


def testo_seconda(p):
    parti = [f"RISPOSTA:\n{p['pulito']['con_firma'] or '(vuota)'}"]
    if p["pulito"]["tolto"]:
        parti.append(f"TOLTO DALLA PULIZIA (POTREBBE ESSERE SUO):\n{p['pulito']['tolto']}")
    return "\n\n".join(parti)


# ── 6. la lettura intera ────────────────────────────────────────────────────────

def _liste(testo_lead, motivo):
    """La ricaduta: le liste di parole del sync, piu' la rete dei casi gravi. Lo dice."""
    import sync_v2
    suo = sync_v2.testo_suo(testo_lead)
    cls = sync_v2.classifica(suo)
    ns = rete_su([solo_suo(testo_da_html(testo_lead))["con_firma"]])
    if ns and cls not in ("negativo",):
        cls = "da_classificare"
    return {"classe": cls, "caldo": False, "non_scrivere": ns, "motivo": f"liste di parole ({motivo})",
            "fonte": "liste", "caso": None, "sicurezza": None, "costo": 0.0}


def leggi_risposta(testo_lead, filo=None, lead=None, chiedi=None, tetto=None, registra="lettore"):
    """Legge una risposta. testo_lead: il corpo della risposta (HTML o testo); filo: la
    message-history di Smartlead (o la nostra forma); lead: la riga di prospects (analysis_sent).
    chiedi(ruolo, istruzioni, testo, schema) -> (dict, costo): il modello; di base Anthropic.
    Restituisce {classe, caldo, non_scrivere, motivo, fonte, caso, sicurezza, costo, ...}."""
    lead = lead or {}
    messaggi = messaggi_da_smartlead(filo or [])
    corpo = testo_da_html(testo_lead)
    idx = None
    for k in range(len(messaggi) - 1, -1, -1):
        if messaggi[k]["tipo"] == "REPLY" and (not corpo or normalizza(messaggi[k]["testo"]) == corpo):
            idx = k
            break
    if idx is None:
        messaggi = messaggi + [{"tipo": "REPLY", "il": datetime.datetime.now(datetime.timezone.utc).isoformat(), "da": None,
                                "cc": None, "oggetto": None, "passo": None, "allegati": 0, "testo": corpo}]
        idx = len(messaggi) - 1
    if chiedi is None:
        if not _env("ANTHROPIC_API_KEY"):
            return _liste(testo_lead, "manca la chiave del modello")
        limite = TETTO_GIORNO if tetto is None else tetto
        speso = spesa_di_oggi()
        if speso is not None and speso >= limite:
            return _liste(testo_lead, f"tetto di spesa del giorno raggiunto: {speso:.2f} $ su {limite:.2f} $")

        def chiedi(ruolo, istr, testo, schema):
            return chiedi_anthropic(ruolo, istr, testo, schema, registra=registra)
    try:
        return leggi_filo(messaggi, idx, chiedi, analisi_nel_crm=bool(lead.get("analysis_sent")))
    except Exception as e:                                       # noqa: BLE001
        return _liste(testo_lead, f"il modello non ha risposto: {str(e)[:120]}")


def leggi_filo(messaggi, idx, chiedi, analisi_nel_crm=False):
    """La lettura di messaggi[idx] (gia' nella nostra forma). Se il modello non risponde, solleva:
    la ricaduta sulle liste la decide chi chiama (leggi_risposta); il rigioco invece si ferma."""
    p = prepara(messaggi, idx, analisi_nel_crm=analisi_nel_crm)
    spesa = 0.0
    if True:
        l, c = chiedi("lettore", istruzioni_lettore(), p["testo"], SCHEMA_LETTORE)
        spesa += c
        v = verifica(l, p)
        d = decidi(l, v, p["fatti"]["analisi_mandata"])
        seconda = None
        if d["seconda_lettura"]:
            s, c = chiedi("seconda_lettura", REGOLE["istruzioni_seconda"], testo_seconda(p), SCHEMA_SECONDA)
            spesa += c
            seconda = bool(s.get("apertura"))
            if seconda:
                d["classe"] = "da_classificare"
                frase = s.get("frase") or ""
                d["perche"].append(f"seconda lettura: un'apertura («{frase[:120]}»): a Dre")
                # un'apertura che e' un numero lasciato (scritto nel messaggio, non nostro): e' caldo
                if _numeri_nel(frase) & _numeri_nel(p["risposta"]["testo"]) - _numeri_nel("\n".join(p["nostre_testi"])):
                    d["caldo"] = True
                    d["perche"].append("lascia il suo numero: caldo")
        elif d["classe"] == "positivo" and not d["caldo"] and l.get("autore") != "automatico":
            # IL CALDO, RILETTO (20/10): un si' senza voglia di sentirsi si rilegge alla cieca, cercando
            # anche solo un accenno a parlarne («se la condividiamo ne parliamo»). Il caldo e' la cosa
            # che Dre vuole sapere subito: meglio un caldo in piu' che uno perso.
            s, c = chiedi("caldo", REGOLE["istruzioni_caldo"], testo_seconda(p), SCHEMA_CALDO)
            spesa += c
            if s.get("caldo"):
                d["caldo"] = True
                d["perche"].append(f"seconda lettura: vuole sentirsi («{(s.get('frase') or '')[:120]}»): lo chiama Dre")
    data = l.get("data_rientro") if d["classe"] == "ooo" else l.get("data_ricontatto") if d["classe"] == "rinvio" else None
    return {"classe": d["classe"], "caldo": d["caldo"], "non_scrivere": d["non_scrivere"],
            "motivo": "; ".join(d["perche"]) + (f". {l.get('perche')}" if l.get("perche") else ""),
            "fonte": "lettore", "caso": l.get("caso"), "sicurezza": l.get("sicurezza"), "autore": l.get("autore"),
            "porta_aperta": bool(l.get("porta_aperta")), "data": data if data and re.fullmatch(r"\d{4}-\d{2}-\d{2}", str(data)) else None,
            "caldo_frase": l.get("caldo_frase") if d["caldo"] else None, "numeri": v["numeri"], "seconda": seconda,
            "analisi_mandata": p["fatti"]["analisi_mandata"], "costo": round(spesa, 6)}


def classe_db(lettura):
    """La classe da scrivere in prospects.classificazione (il vincolo del database non ha «automatico»)."""
    if lettura.get("non_scrivere") and lettura.get("classe") == "negativo":
        return "soppresso"
    if lettura.get("classe") == "automatico":
        return "ooo"
    return lettura.get("classe") or "da_classificare"


# ── 7. la modalita' e il conto ──────────────────────────────────────────────────

def modo():
    """«spento», «ombra» o «acceso»: l'interruttore operazioni.lettore e snella_numeri «lettore»."""
    try:
        from stanza import sb
        op = sb("GET", "/rest/v1/operazioni?select=attiva&chiave=eq.lettore") or []
        if not op or not op[0].get("attiva"):
            return "spento"
        r = sb("GET", "/rest/v1/snella_numeri?select=dati&chiave=eq.lettore") or []
        m = ((r[0].get("dati") if r else None) or {}).get("modo")
        return m if m in ("ombra", "acceso") else "ombra"
    except Exception:                                            # noqa: BLE001
        return "spento"


def _stato():
    from stanza import sb
    r = sb("GET", "/rest/v1/snella_numeri?select=dati&chiave=eq.lettore") or []
    return dict((r[0].get("dati") if r else None) or {})


def _salva_stato(dati):
    from stanza import sb, _a_secco
    if _a_secco():
        print("(prova: non scrivo)")
        return
    sb("POST", "/rest/v1/snella_numeri?on_conflict=chiave",
       [{"chiave": "lettore", "dati": dati, "aggiornato_il": datetime.datetime.now(datetime.timezone.utc).isoformat()}],
       {"Prefer": "resolution=merge-duplicates,return=minimal"})


def conto():
    """L'operazione «lettore»: scrive nella scheda la modalita', la spesa di oggi e le ricadute sulle liste."""
    from stanza import sb_tutte
    import zoneinfo
    st = _stato()
    st.setdefault("modo", "ombra")
    st["tetto_giorno"] = TETTO_GIORNO
    speso = spesa_di_oggi()
    st["speso_oggi"] = round(speso, 4) if speso is not None else None
    oggi = datetime.datetime.now(zoneinfo.ZoneInfo("Europe/Rome")).replace(hour=0, minute=0, second=0, microsecond=0)
    da = oggi.astimezone(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")
    righe = sb_tutte("/rest/v1/prospects?select=id,enriched&enriched->lettore->>letto_il=gte." + da) or []
    lette = [(r.get("enriched") or {}).get("lettore") or {} for r in righe]
    st["lette_oggi"] = len(lette)
    st["ricadute_oggi"] = sum(1 for x in lette if x.get("fonte") == "liste")
    st["disaccordi_oggi"] = sum(1 for x in lette if x.get("liste") and x.get("classe") and x.get("liste") != x.get("classe"))
    if st["ricadute_oggi"]:
        st["avviso"] = f"Oggi {st['ricadute_oggi']} risposte lette con le liste di parole (il modello non ha risposto o il tetto e' pieno)."
    else:
        st.pop("avviso", None)
    _salva_stato(st)
    print(json.dumps(st, ensure_ascii=False))


def cambia_modo(nuovo):
    if nuovo not in ("ombra", "acceso"):
        sys.exit("modo: ombra o acceso")
    st = _stato()
    st["modo"] = nuovo
    st["modo_dal"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
    _salva_stato(st)
    print(f"lettore: {nuovo}")


# ── 8. l'ombra e la riclassifica (a video, mai testi nei file) ──────────────────

def _smartlead(path):
    import sync_v2
    return sync_v2.sl_get(path)


def _ultima_risposta(p):
    """(corpo dell'ultima risposta, filo) dal filo vero di Smartlead."""
    if not (p.get("campaign_id") and p.get("lead_id")):
        return None, None
    h = _smartlead(f"/campaigns/{p['campaign_id']}/leads/{p['lead_id']}/message-history") or {}
    msgs = h.get("history") or []
    rep = [m for m in msgs if m.get("type") == "REPLY"]
    return (rep[-1].get("email_body"), msgs) if rep else (None, None)


def ombra(giorni=3):
    from stanza import sb
    import sync_v2
    da = (datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=giorni)).strftime("%Y-%m-%dT%H:%M:%S")
    ps = sb("GET", "/rest/v1/prospects?select=id,company,email,classificazione,analysis_sent,campaign_id,lead_id,last_reply_at"
                   f"&last_reply_at=gte.{da}&order=last_reply_at.desc&limit=500") or []
    print(f"OMBRA: {len(ps)} lead con una risposta negli ultimi {giorni} giorni\n")
    tab, spesa = [], 0.0
    for p in ps:
        try:
            corpo, filo = _ultima_risposta(p)
        except Exception as e:                                   # noqa: BLE001
            print(f"  ! {p.get('company')}: filo illeggibile ({e})")
            continue
        if not corpo:
            continue
        liste = sync_v2.classifica(sync_v2.testo_suo(corpo))
        l = leggi_risposta(corpo, filo, p, registra="lettore-ombra", tetto=99)
        spesa += l.get("costo") or 0
        tab.append((p, liste, l, corpo))
        segno = "  " if liste == l["classe"] else "≠ "
        print(f"{segno}{(p.get('company') or p.get('email') or '?')[:30]:30} liste={liste:15} lettore={l['classe']:15}"
              f" {'CALDO ' if l['caldo'] else ''}{'NON-SCRIVERE ' if l['non_scrivere'] else ''}[{l.get('caso')}, {l.get('sicurezza')}, {l['fonte']}]")
    dis = [x for x in tab if x[1] != x[2]["classe"]]
    print(f"\n{len(tab)} risposte, {len(dis)} disaccordi, spesa {spesa:.3f} $\n")
    for p, liste, l, corpo in dis:
        print("=" * 90)
        print(f"{p.get('company')} · nel CRM: {p.get('classificazione')} · liste: {liste} · lettore: {l['classe']}")
        print("SUO:", " ".join(solo_suo(testo_da_html(corpo))["con_firma"].split())[:600])
        print("PERCHE':", l["motivo"][:400])
    return tab


def riclassifica(prova=True, percorso_cache=None):
    """Rilegge col lettore i lead oggi «positivo» o «da_classificare» (l'ultima risposta). Passa dal Revisore."""
    from stanza import sb
    import revisore
    cache = None
    if percorso_cache:
        cache = json.load(open(percorso_cache, encoding="utf-8")) if os.path.exists(percorso_cache) else {}
    ps = sb("GET", "/rest/v1/prospects?select=id,company,email,classificazione,analysis_sent,campaign_id,lead_id,"
                   "last_reply_at,enriched,deciso,fuori,stage,pipeline_stage,no_followup"
                   "&classificazione=in.(positivo,da_classificare)&last_reply_at=not.is.null&order=last_reply_at.desc&limit=1000") or []
    ps = [p for p in ps if not p.get("fuori") and (p.get("enriched") or {}).get("classificazione") != "manual"
          and "classificazione" not in (p.get("deciso") or {})]
    print(f"RICLASSIFICA: {len(ps)} lead positivo o da classificare (non fuori, non corretti a mano)")
    cambi, spesa = [], 0.0
    for p in ps:
        try:
            corpo, filo = _ultima_risposta(p)
        except Exception as e:                                   # noqa: BLE001
            print(f"  ! {p.get('company')}: filo illeggibile ({e})")
            continue
        if not corpo:
            continue
        # la prova a secco e il giro vero pagano il modello una volta sola: si tengono le sue risposte
        # (cache fuori dal repo), la decisione si rifa' col codice di adesso
        def chiedi(ruolo, istr, testo, schema):
            k = hashlib.sha256(json.dumps([ruolo, istr, testo], ensure_ascii=False).encode()).hexdigest()[:32]
            if cache is not None and k in cache:
                return cache[k], 0.0
            uscita, c = chiedi_anthropic(ruolo, istr, testo, schema, registra="lettore-riclassifica")
            if cache is not None:
                cache[k] = uscita
                json.dump(cache, open(percorso_cache, "w", encoding="utf-8"))
            return uscita, c
        l = leggi_risposta(corpo, filo, p, chiedi=chiedi)
        spesa += l.get("costo") or 0
        nuova = classe_db(l)
        if l["fonte"] != "lettore" or nuova == p.get("classificazione"):
            continue
        # una risposta vecchia non si risveglia: verso un si' (o una ripresa) solo se ha risposto da poco.
        # Al contrario (un si' che era un no, un'autorisposta) si corregge sempre: ferma, non manda.
        vecchia = (p.get("last_reply_at") or "") < (datetime.datetime.now(datetime.timezone.utc)
                                                     - datetime.timedelta(days=14)).strftime("%Y-%m-%dT%H:%M:%S")
        if nuova in ("positivo", "rinvio") and vecchia:
            continue
        cambi.append({"id": p["id"], "email": p.get("email"), "azienda": (p.get("company") or "")[:40],
                      "classificazione": p.get("classificazione"), "esito": nuova, "lettura": l,
                      "verifica": f"{l.get('caso')} {l.get('sicurezza')}"})
        print(f"  {p.get('classificazione'):15} -> {nuova:15} {(p.get('company') or '')[:34]:34} [{l.get('caso')}, {l.get('sicurezza')}]"
              f" {l['motivo'][:110]}")
    print(f"\n{len(cambi)} cambi su {len(ps)}, spesa {spesa:.3f} $")
    if not cambi:
        return cambi
    if prova:
        os.environ["REVISORE_PROVA"] = "1"
    tenuti = revisore.controlla("riclassifico col lettore le risposte dei lead positivo o da classificare", cambi,
                                chiave=lambda r: r.get("email"), irreversibile=False,
                                motivo="le liste di parole hanno perso si' e letto autorisposte come si': rilegge il lettore AI (mattone 5)",
                                dove="crm")
    if prova:
        print("(prova a secco: nessuna scrittura)")
        return tenuti
    adesso = datetime.datetime.now(datetime.timezone.utc).isoformat()
    scritti = lasciati = 0
    for c in tenuti:
        l = c["lettura"]
        fresco = (sb("GET", f"/rest/v1/prospects?select=enriched&id=eq.{c['id']}") or [{}])[0]
        enr = dict(fresco.get("enriched") or {})
        enr["lettore"] = _per_enriched(l, c["classificazione"], adesso)
        patch = {"classificazione": c["esito"], "enriched": enr}
        if l.get("non_scrivere"):
            patch["no_followup"] = True
        if c["esito"] in ("negativo", "soppresso", "ooo"):
            patch["awaiting_us"] = False
        try:
            sb("PATCH", f"/rest/v1/prospects?id=eq.{c['id']}", patch)
            scritti += 1
        except RuntimeError as e:
            # la classe decisa da una persona e' murata nel database (lock umano): si lascia, e si dice
            if "lock umano" not in str(e):
                raise
            lasciati += 1
            print(f"  = {c['azienda']}: la classe l'ha decisa una persona, la lascio ({c['classificazione']})")
    print(f"scritti {scritti} cambi, {lasciati} lasciati perche' decisi da una persona")
    return tenuti


def _per_enriched(l, liste, il, risposta_il=None):
    """Quello che resta nel lead: niente testo, solo la decisione e il perche'."""
    return {"classe": l.get("classe"), "caso": l.get("caso"), "sicurezza": l.get("sicurezza"), "caldo": bool(l.get("caldo")),
            "non_scrivere": bool(l.get("non_scrivere")), "fonte": l.get("fonte"), "motivo": (l.get("motivo") or "")[:300],
            "liste": liste, "letto_il": il, "risposta_il": risposta_il}


if __name__ == "__main__":
    a = sys.argv[1:]
    if "--conto" in a:
        conto()
    elif "--ombra" in a:
        ombra(int(a[a.index("--giorni") + 1]) if "--giorni" in a else 3)
    elif "--riclassifica" in a:
        riclassifica(prova="--prova" in a or os.environ.get("PROVA") == "1",
                     percorso_cache=a[a.index("--cache") + 1] if "--cache" in a else None)
    elif "--modo" in a:
        cambia_modo(a[a.index("--modo") + 1])
    else:
        print(__doc__)
