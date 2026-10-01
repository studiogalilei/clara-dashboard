#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""I SEGUITI SCRITTI DAL CODICE (Dre, 29/9/2026: «strada A»).

PERCHE'
In Posta c'erano 57 follow-up fermi, e il 25/9, l'unica volta che si e' provato
ad approvarli in blocco, 4 mail su 10 erano sbagliate: il modello li scriveva
«ispirandosi» al template, e sbagliava proprio le parti che cambiava. Per i
follow-up il testo e' di Dre, parola per parola: qui lo compone il codice, e il
modello non scrive niente.

COSA FA
Prende il template dal file di Dre («Risposte (template verbatim)», nel bucket),
mette il saluto giusto e il calendario, e basta. Il saluto:
  1. il nome con cui NOI gli abbiamo scritto l'ultima volta («Salve Maura,»):
     l'ha scelto Dre, e' quello giusto;
  2. altrimenti il nome della scheda, solo se e' un nome vero e compare nella
     sua ultima mail (la firma);
  3. altrimenti «Salve,» secco (regola del Preparatore: un nome inventato e'
     peggio di nessun nome).
Quando il template chiede una riscrittura che il codice non sa fare (il rinvio
a chi l'analisi l'ha gia' letta) o il template non c'e' (RICONTATTO OOO), torna
None: quella bozza la scrive il motore di sempre, e non parte mai da sola.
"""

import re

GRUPPI_DAL_CODICE = ("FOLLOW UP 1", "MINI FOLLOW UP", "RIPRESA", "RINVIO SCADUTO", "RICONTATTO OOO")
# come il titolo del template sta scritto nel file di Dre
_TITOLI = {"FOLLOW UP 1": r"##\s*FOLLOW UP 1\s*\n", "MINI FOLLOW UP": r"MINI FOLLOW UP \(25/9",
           "RIPRESA": r"RIPRESA \(25/9", "RINVIO SCADUTO": r"##\s*RINVIO SCADUTO",
           # 29/9: il testo di Dre c'era dal 14/7 con questo nome, e il codice non lo trovava
           "RICONTATTO OOO": r"##\s*RICONTATTO DOPO OUT OF OFFICE"}
_MESI = ["gennaio", "febbraio", "marzo", "aprile", "maggio", "giugno", "luglio", "agosto",
         "settembre", "ottobre", "novembre", "dicembre"]
_NON_NOMI = {"salve", "buongiorno", "gentile", "ciao", "info", "amministrazione", "ufficio", "segreteria",
             "direzione", "marketing", "commerciale", "staff", "team", "admin", "contatti", "vendite"}


def template(gruppo, testo_file=None):
    """Il blocco ``` subito dopo il titolo del gruppo, com'e' nel file. None se non c'e'."""
    if gruppo not in _TITOLI:
        return None
    if testo_file is None:
        import bozze
        testo_file = bozze.template_verbatim()
    m = re.search(_TITOLI[gruppo], testo_file or "")
    if not m:
        return None
    b = re.search(r"```\s*\n(.*?)```", testo_file[m.end():], re.S)
    return b.group(1).strip() if b else None


def _nome_vero(n):
    n = (n or "").strip()
    return bool(re.fullmatch(r"[A-ZÀ-Ý][a-zà-ÿ']{2,20}", n)) and n.lower() not in _NON_NOMI


def saluto(p, letti):
    """«Salve Nome,» o «Salve,». Mai un nome inventato."""
    nostra = (letti or {}).get("ultima_nostra") or ""
    m = re.match(r"\s*(?:Salve|Buongiorno|Gentile)\s+(?:Sig\.ra\s+|Sig\.\s+|Dott\.ssa\s+|Dott\.\s+)?([A-ZÀ-Ý][\wà-ÿ']+)\s*,", nostra)
    if m and _nome_vero(m.group(1)):
        return f"Salve {m.group(1)},"
    nome = ((p or {}).get("name") or "").split()
    primo = nome[0] if nome else ""
    if _nome_vero(primo) and primo.lower() in ((letti or {}).get("ultima_loro") or "").lower():
        return f"Salve {primo},"
    return "Salve,"


def giorno_passato(frase, oggi=None):
    """«giovedì 1 ottobre alle 14:30» e' gia' passato (o e' oggi)? Una mail che propone
    un giorno passato non parte da sola."""
    import datetime
    m = re.search(r"(\d{1,2})\s+(" + "|".join(_MESI) + r")", (frase or "").lower())
    if not m:
        return True                 # non si capisce che giorno e': meglio fermarsi
    oggi = oggi or datetime.date.today()
    mese = _MESI.index(m.group(2)) + 1
    anno = oggi.year + (1 if mese < oggi.month - 6 else 0)
    try:
        return datetime.date(anno, mese, int(m.group(1))) <= oggi
    except ValueError:
        return True


def testo(gruppo, p, letti, calendario, testo_file=None, giorno=None):
    """Il follow-up pronto, parola per parola. None se il codice non puo' scriverlo da solo."""
    if gruppo not in GRUPPI_DAL_CODICE:
        return None
    if gruppo == "RINVIO SCADUTO" and ((letti or {}).get("analisi_ricevuta") or (p or {}).get("analysis_sent")):
        return None            # il template chiede di riscrivere la frase dell'analisi: non e' un lavoro da codice
    t = template(gruppo, testo_file)
    if not t:
        return None
    righe = t.splitlines()
    if righe and re.match(r"\s*Salve\b", righe[0]):
        righe[0] = saluto(p, letti)
    t = "\n".join(righe)
    t = t.replace("{{CALENDARIO}}", calendario).replace("{{ CALENDARIO }}", calendario)
    if "{{GIORNO}}" in t:
        if not giorno:
            return None             # il giorno lo decide il calendario di Dre, non il codice a caso
        t = t.replace("{{GIORNO}}", giorno)
    if "[" in t or "{{" in t:
        return None            # un segnaposto che il codice non conosce: meglio non scrivere
    return t.strip()


# ── LE RISPOSTE COL TESTO DI DRE (29/9) ─────────────────────────────
# Dre, 29/9: «le bozze fanno un po' cacare, basta seguire questo tutte le volte
# possibili». Stessa strada dei follow-up: il testo lo compone il codice dal file dei
# template, parola per parola. Il modello sceglie l'intento e riempie due pezzetti
# controllati: l'attacco («Va bene perfetto» va adattato a cosa ha scritto, dice la
# nota di Dre) e, nei rinvii, il periodo («a ottobre/novembre»). Nome, giorno e
# calendario li mette il codice. Senza template (obiezioni, prezzo, inoltri) → None.

RISPOSTE = {"INT-01": "INTERESSATO", "INT-02": "INTERESSATO", "INT-23": "INTERESSATO",
            "INT-03": "CHI SEI", "INT-05": "SENTIAMOCI", "INT-06": "SENTIAMOCI"}
_TITOLI_RISPOSTE = {"INTERESSATO": r"##\s*INTERESSATO", "CHI SEI": r"##\s*CHI SEI\?",
                    "SENTIAMOCI": r"##\s*SENTIAMOCI PI", "QUAL E": r"##\s*QUAL'È LA VOSTRA SOCIET"}
# «chi siete come azienda?» vuole il template della societa', «chi e' lei?» quello di chi siamo
# (la mappa di Dre: «chi siete?» → CHI SEI?, «qual e' la vostra societa' / che agenzia siete?» → QUAL'E')
CHIEDE_SOCIETA = re.compile(r"(?:che|quale|qual\s*[eè]'?\s*la\s+vostra|di che)\s+(?:societ|agenzi|aziend)|siete\s+un'?\s*agenzia", re.I)


def _blocco(titolo_re, testo_file):
    m = re.search(titolo_re, testo_file or "")
    b = re.search(r"```\s*\n(.*?)```", testo_file[m.end():], re.S) if m else None
    return b.group(1).strip() if b else None


def _attacco(a):
    """L'attacco del modello, solo se e' corto e innocuo: niente numeri, niente promesse."""
    a = " ".join((a or "").split()).strip(" «»\"'")
    if not a or len(a.split()) > 7 or re.search(r"\d|analisi|€|garanzi|allego|propongo", a, re.I):
        return None
    a = a.rstrip(".;:!") + ("" if a.endswith(",") else ",")
    return a[0].upper() + a[1:]


def _periodo(pr):
    pr = " ".join((pr or "").split()).strip(" «»\"'.,")
    if not pr or len(pr.split()) > 6 or "\n" in pr:
        return None
    return pr


FRASE_GARANZIA = "Poi avremmo pronta anche una proposta con garanzia da farvi, ma intanto mi"
FRASE_GARANZIA_IN = "Avremmo pronta anche una proposta con garanzia da farvi, ma prima mi"


def risposta(intento, p, letti, calendario, giorno=None, attacco=None, periodo=None, testo_file=None, loro="", garanzia=None):
    """La risposta col testo di Dre, o None se per quell'intento non c'e' un suo template.

    `garanzia` (1/10, lo score di Dre: «uno se lo ricorda»): la frase della proposta
    con garanzia resta solo se lo score dice che possiamo permettercela. None = si
    calcola qui da p; nei template che non la hanno (CHI SEI, SENTIAMOCI) la stessa
    frase di Dre si AGGIUNGE quando lo score passa («quella linea ci sta in realta'»).
    """
    chiave = RISPOSTE.get((intento or "").strip())
    if chiave == "CHI SEI" and CHIEDE_SOCIETA.search(loro or ""):
        chiave = "QUAL E"
    if not chiave:
        return None
    if testo_file is None:
        import bozze
        testo_file = bozze.template_verbatim()
    t = _blocco(_TITOLI_RISPOSTE[chiave], testo_file)
    if not t:
        return None
    righe = t.splitlines()
    if righe and re.match(r"\s*Salve\b", righe[0]):
        righe[0] = saluto(p, letti)
    t = "\n".join(righe)
    if chiave == "INTERESSATO":
        t = re.sub(r"Va bene perfetto,\s*", (_attacco(attacco) or "Va bene perfetto,") + " ", t, count=1)
    if chiave == "SENTIAMOCI":
        per = _periodo(periodo)
        if not per:
            return None                  # senza sapere quando, il rinvio lo scrive una persona
        t = t.replace("a ottobre/novembre", per, 1)
    if re.search(r"Le propongo domani alle \d", t):
        if not giorno:
            return None                  # il giorno lo decide il calendario di Dre
        t = re.sub(r"Le propongo domani alle \d{1,2}(?::\d{2})?", f"Le propongo {giorno}", t)
        t = t.replace("nel caso domani non abbia disponibilità", "nel caso quel giorno non abbia disponibilità")
    t = re.sub(r"https://calendar\.app\.google/[A-Za-z0-9]+", calendario, t).replace("{{CALENDARIO}}", calendario)
    if garanzia is None:
        try:
            from garanzia import promettibile
            garanzia = promettibile(p)[0]
        except Exception:                                    # noqa: BLE001
            garanzia = False                                 # nel dubbio non si promette
    if not garanzia:
        t = t.replace(FRASE_GARANZIA + " farebbe", "Mi farebbe", 1)
    elif FRASE_GARANZIA not in t and "Mi farebbe piacere confrontarmi" in t:
        t = t.replace("Mi farebbe piacere confrontarmi", FRASE_GARANZIA_IN + " farebbe piacere confrontarmi", 1)
    if "[" in t or "{{" in t:
        return None
    return t.strip()


def converti(prova=True):
    """Le bozze di follow-up gia' in Posta, scritte dal modello, passano al testo di
    Dre parola per parola (29/9). Si tocca solo la proposta, mai la mail: la bozza del
    modello resta salvata in azione.bozza_modello. Passa dal Revisore (azione di gruppo)."""
    import os
    import sys
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from stanza import sb
    import bozze
    import lettura
    ap = sb("GET", "/rest/v1/proposte?select=id,titolo,prospect_id,azione&stato=eq.aperta&tipo=in.(risposta,umano)&prospect_id=not.is.null") or []
    righe = []
    for pr in ap:
        az = pr.get("azione") or {}
        gruppo = (az.get("lettura") or {}).get("gruppo")
        if gruppo not in GRUPPI_DAL_CODICE or az.get("testo_dal_codice"):
            continue
        p = (sb("GET", f"/rest/v1/prospects?select=id,email,email_alt,company,name,analysis_sent,campaign_id,lead_id&id=eq.{pr['prospect_id']}") or [None])[0]
        if not p:
            continue
        _, letti = lettura.leggi(p)
        giorno = bozze.proposta_giorno_ora() if gruppo == "RICONTATTO OOO" else None
        t = testo(gruppo, p, letti, bozze.CALENDARIO, giorno=giorno)
        print(f"  {gruppo:15} {(p.get('company') or p['email'])[:32]:32} {'-> testo di Dre' if t else 'resta com e (il codice non sa scriverlo)'}")
        if t:
            righe.append({"id": pr["id"], "azienda": p.get("company") or p["email"], "email": p["email"], "t": t, "az": az, "giorno": giorno})
    if not righe:
        print("niente da convertire"); return 0
    import revisore
    tenute = revisore.controlla("sostituisco il testo di bozze di follow-up NON mandate col template di Dre parola per parola",
                                righe, irreversibile=False, dove="crm",
                                motivo="strada A decisa da Dre il 29/9; la bozza del modello resta salvata accanto")
    n = 0
    for r in tenute:
        if prova:
            continue
        az = {**r["az"], "bozza_modello": r["az"].get("bozza"), "bozza": r["t"], "testo_dal_codice": True}
        if r.get("giorno"):
            az["giorno_proposto"] = r["giorno"]
        if sb("PATCH", f"/rest/v1/proposte?id=eq.{r['id']}&stato=eq.aperta", {"azione": az}, {"Prefer": "return=representation"}):
            n += 1
    print(f"convertite {n} di {len(righe)}" + (" (prova: niente scritto)" if prova else ""))
    return n


if __name__ == "__main__":
    import sys
    if "--converti" in sys.argv:
        converti(prova="--prova" in sys.argv)
