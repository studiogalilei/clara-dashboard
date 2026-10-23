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
             "direzione", "marketing", "commerciale", "staff", "team", "admin", "contatti", "vendite",
             # 23/10: «la titolare dell'agenzia» dava «Dell, piacere»: articoli e preposizioni non sono nomi
             "dell", "della", "dello", "delle", "degli", "del", "dei", "nell", "nella", "alla", "all", "sua", "suo",
             "nostra", "nostro", "mia", "mio", "che", "per", "con", "agenzia", "azienda", "ditta", "studio"}


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
    # 20/10 sera: se ha risposto un'altra persona (un collega dallo stesso dominio) il nome della
    # nostra mail e' quello sbagliato: «Salve Luca» a chi si chiama Francesco. Mittente diverso
    # dal destinatario nostro: il nome nostro non vale, e al massimo resta quello della scheda se sta nel suo testo
    da = ((letti or {}).get("ultima_loro_da") or "").strip().lower()
    a_chi = ((letti or {}).get("ultima_nostra_a") or "").strip().lower()
    altra_persona = bool(da and a_chi and da != a_chi)
    m = re.match(r"\s*(?:Salve|Buongiorno|Gentile)\s+(?:Sig\.ra\s+|Sig\.\s+|Dott\.ssa\s+|Dott\.\s+)?([A-ZÀ-Ý][\wà-ÿ']+)\s*,", nostra)
    if m and _nome_vero(m.group(1)) and not altra_persona:
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


def _del_tu(letti):
    """La nostra ultima mail nel filo da' del tu? Dalla lettura, o dal testo se la lettura e' vecchia."""
    l = letti or {}
    if "ultima_nostra_del_tu" in l:
        return bool(l["ultima_nostra_del_tu"])
    import lettura
    return lettura.da_del_tu(l.get("ultima_nostra") or "")


def testo(gruppo, p, letti, calendario, testo_file=None, giorno=None):
    """Il follow-up pronto, parola per parola. None se il codice non puo' scriverlo da solo."""
    if gruppo not in GRUPPI_DAL_CODICE:
        return None
    if _del_tu(letti):
        # 20/10 (caso 1): Dre era passato al «tu» a mano, e il template col «lei» e' partito sopra.
        # I template di Dre danno tutti del lei: dopo un tu nostro lo scrive una persona.
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
    """L'attacco del modello, solo se e' corto e innocuo: niente numeri, niente promesse.
    20/10 sera: nemmeno un fatto sul filo («grazie per il passaggio», «la metto in copia»,
    «me l'ha inoltrata»): se scriviamo direttamente al contatto nuovo e' falso, e la seconda
    testa fermava la mail per quello. Senza attacco si usa quello di Dre."""
    a = " ".join((a or "").split()).strip(" «»\"'")
    if not a or len(a.split()) > 7 or re.search(r"\d|analisi|€|garanzi|allego|propongo|passaggi|copia|inoltr|girat", a, re.I):
        return None
    if re.match(r"(?:salve|buongiorno|buonasera|gentile|egregi|ciao|spett)", a, re.I):
        return None            # il saluto lo mette il codice: «Salve,» e poi «Buongiorno Francesco,» e' un doppio saluto
    a = a.rstrip(".;:!") + ("" if a.endswith(",") else ",")
    return a[0].upper() + a[1:]


def _periodo(pr):
    pr = " ".join((pr or "").split()).strip(" «»\"'.,")
    if not pr or len(pr.split()) > 6 or "\n" in pr:
        return None
    return pr


FRASE_GARANZIA = "Poi avremmo pronta anche una proposta con garanzia da farvi, ma intanto mi"
FRASE_GARANZIA_IN = "Avremmo pronta anche una proposta con garanzia da farvi, ma prima mi"


# HA GIA' L'ANALISI E DICE «PIU' AVANTI» (Dre, 7/10, caso La Bottega del Legno: «e' un periodo
# incasinato, la leggero' con calma piu' avanti»). Il modello SENTIAMOCI e' scritto per chi
# l'analisi non l'ha ancora: gliela riallegava e proponeva una call «anche domani». Dre:
# «sentirci tra 15 giorni, lasciare il calendario, proporre una data, follow-up a 15 giorni».
DOPO_ANALISI = """Salve,

nessun problema, capisco bene: ci risentiamo fra un paio di settimane, così ha il tempo di leggere l'analisi con calma.

Le propongo {{GIORNO}}: se le va meglio un altro momento, qui trova il calendario per scegliere giorno e orario: {{CALENDARIO}}

Un saluto"""
GIORNI_DOPO_ANALISI = 15

# IL RIMBALZO INTERNO, VERSIONE CC (template di Dre del 15/7: «Reply nel thread, To: originale,
# CC: nuova mail, due righe, allegare l'analisi se esiste»). Dal 20/10 lo compone il codice:
# quel giorno un si' («provi a mandarlo a questo indirizzo che le giro, all'attenzione di X»)
# e' rimasto fermo ore perche' la bozza del modello diceva «metto in copia» e il postino non
# sapeva mettere nessuno in copia: la frase sarebbe stata falsa. Le parole sono quelle di Dre;
# le frasi vanno a capo invece di stare incollate sulla stessa riga (Dre 1/10). Chi va in copia
# lo decide il codice da quello che la persona ha scritto (bozze.in_copia), mai il modello.
RIMBALZI = ("INT-08", "INT-09")
RIMBALZO_CC = """Salve,

grazie per il passaggio, molto gentile. Metto in copia {{NUOVO}} così proseguiamo direttamente lì.

{{PIACERE}}sono Lorenzo di Studio Galilei.
In una riga: abbiamo preparato un'analisi esterna gratuita su come {{AZIENDA}} appare oggi su Google (la trova allegata), ed è il nostro modo di presentarci portando già spunti concreti.
Se le fa piacere approfondire, qui trova il calendario per scegliere il giorno più comodo.
📅 Calendario: {{CALENDARIO}}"""


def rimbalzo_cc(p, letti, calendario, cc, nome_nuovo=None):
    """Il RIMBALZO INTERNO con la nuova persona in copia. None se non c'e' nessuno da mettere in
    copia o manca l'azienda: allora lo scrive il modello e lo guarda Dre. Il nome del nuovo
    contatto solo se e' un nome vero (mai un indirizzo come nome, 25/9)."""
    cc = [str(c).strip() for c in (cc or []) if str(c).strip()]
    azienda = ((p or {}).get("company") or "").strip()
    if not cc or not azienda:
        return None
    nome = (nome_nuovo or "").strip()
    nome = nome if _nome_vero(nome) else ""
    nuovo = f"{nome} ({', '.join(cc)})" if nome else ", ".join(cc)
    t = (RIMBALZO_CC.replace("{{NUOVO}}", nuovo).replace("{{PIACERE}}", f"{nome}, piacere: " if nome else "Piacere: ")
         .replace("{{AZIENDA}}", azienda).replace("{{CALENDARIO}}", calendario))
    righe = t.splitlines()
    righe[0] = saluto(p, letti)
    t = "\n".join(righe)
    if "[" in t or "{{" in t:
        return None
    return t.strip()


def risposta(intento, p, letti, calendario, giorno=None, attacco=None, periodo=None, testo_file=None, loro="", garanzia=None,
             cc=None, nome_nuovo=None):
    """La risposta col testo di Dre, o None se per quell'intento non c'e' un suo template.

    `garanzia` (1/10, lo score di Dre: «uno se lo ricorda»): la frase della proposta
    con garanzia resta solo se lo score dice che possiamo permettercela. None = si
    calcola qui da p; nei template che non la hanno (CHI SEI, SENTIAMOCI) la stessa
    frase di Dre si AGGIUNGE quando lo score passa («quella linea ci sta in realta'»).
    """
    if (intento or "").strip() in RIMBALZI:
        return rimbalzo_cc(p, letti, calendario, cc, nome_nuovo)
    chiave = RISPOSTE.get((intento or "").strip())
    if chiave == "CHI SEI" and CHIEDE_SOCIETA.search(loro or ""):
        chiave = "QUAL E"
    if not chiave:
        return None
    if chiave == "SENTIAMOCI" and (p or {}).get("analysis_sent"):
        # l'analisi l'ha gia': niente riallegata, niente call domani. Il giorno e' quello a
        # due settimane (bozze.testo_di_dre lo sceglie cosi'); senza giorno lo scrive una persona
        if not giorno:
            return None
        righe = DOPO_ANALISI.splitlines()
        righe[0] = saluto(p, letti)
        return "\n".join(righe).replace("{{GIORNO}}", giorno).replace("{{CALENDARIO}}", calendario).strip()
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
    if (intento or "").strip() == "INT-23":
        # INT-23, VUOLE IL MATERIALE MA NON LA CALL (playbook: «mandi, dici che resti a
        # disposizione, non proponi orari; chi lo ha chiesto si irrigidisce»). Il template e'
        # INTERESSATO senza la proposta di call: il 6/10 Oikos («valuteremo l'eventuale call»)
        # stava per ricevere uno slot alle 9, in automatico.
        righe = [r for r in t.splitlines() if not re.match(r"\s*(Le propongo\b|📅|Calendario:)", r)]
        t = "\n".join("Se dopo averla letta volesse approfondire, resto a disposizione." if "confrontarmi" in r else r
                      for r in righe)
        garanzia = True                  # la frase della garanzia e' sparita con la riga: niente da togliere
    if chiave == "SENTIAMOCI":
        per = _periodo(periodo)
        if not per:
            return None                  # senza sapere quando, il rinvio lo scrive una persona
        t = t.replace("a ottobre/novembre", per, 1)
    if re.search(r"Le propongo domani alle \d", t):
        if not giorno:
            return None                  # il giorno lo decide il calendario di Dre
        # 14/10 (Dre): la call si chiama per nome, «breve videochiamata conoscitiva»
        t = re.sub(r"Le propongo domani alle \d{1,2}(?::\d{2})?", f"Le propongo una breve videochiamata conoscitiva {giorno}", t)
        # 22/10: i giorni proposti sono due («domani alle 15:30 oppure venerdì 24 ottobre alle 11»)
        t = t.replace("nel caso domani non abbia disponibilità", "nel caso non abbia disponibilità" if " oppure " in giorno
                      else "nel caso quel giorno non abbia disponibilità")
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
    if "{{DATO_FORTE}}" in t:
        # 12/10: la riga del potenziale col numero vero (mercato.py, mai il modello). Senza
        # un numero credibile la riga resta, senza numero: «...su Google. Pensiamo possa...»
        # 12/10 sera: la provincia come la sceglie il PDF, e senza un numero una particolarita'
        # vera dai dati raccolti (mercato.riga_per_mail). Mai inventata.
        try:
            from mercato import riga_per_mail
            riga = riga_per_mail(p)
        except Exception:                                    # noqa: BLE001
            riga = ""                                        # nel dubbio niente, mai un dato inventato
        t = t.replace("{{DATO_FORTE}}", riga)
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
        esteso, giorno = bozze.orari_da_proporre() if gruppo == "RICONTATTO OOO" else (None, None)
        t = testo(gruppo, p, letti, bozze.CALENDARIO, giorno=giorno)
        print(f"  {gruppo:15} {(p.get('company') or p['email'])[:32]:32} {'-> testo di Dre' if t else 'resta com e (il codice non sa scriverlo)'}")
        if t:
            righe.append({"id": pr["id"], "azienda": p.get("company") or p["email"], "email": p["email"], "t": t, "az": az, "giorno": esteso})
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
        if r["az"].get("modificata_da_dre"):
            continue                    # 22/10: il testo di Dre non lo riscrive nessuno
        az = {**r["az"], "bozza_modello": r["az"].get("bozza"), "bozza": r["t"], "testo_dal_codice": True}
        if r.get("giorno"):
            import datetime
            az.update({"giorno_proposto": r["giorno"], "orari_scritti_il": datetime.date.today().isoformat()})
        if sb("PATCH", f"/rest/v1/proposte?id=eq.{r['id']}&stato=eq.aperta", {"azione": az}, {"Prefer": "return=representation"}):
            n += 1
    print(f"convertite {n} di {len(righe)}" + (" (prova: niente scritto)" if prova else ""))
    return n


if __name__ == "__main__":
    import sys
    if "--converti" in sys.argv:
        converti(prova="--prova" in sys.argv)
