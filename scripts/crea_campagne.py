#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""LE SEI CAMPAGNE DEL 22/9/2026.

Dre ha approvato la divisione: due liste (cecchino col nome, strascico senza)
per tre angoli (non fanno ads, investono, pagano ma e' fermo). I copy sono i
suoi, verbatim: quattro gia' in uso e due nuovi per «paga ma e' fermo»,
approvati il 22/9.

REGOLE CHE QUESTO SCRIPT RISPETTA
- la variabile azienda e' {{azienda}}, come nei CSV e come a giugno. Non
  company_clean_final, che nel nostro flusso non esiste (verificato).
- niente link ne' PDF nella prima mail (playbook deliverability di Ali).
- si CREA soltanto: le campagne restano in bozza, lo Start lo da' Dre.
- prima di scrivere il copy si contano le graffe: 2 per ogni segnaposto. A
  giugno l'editor di Smartlead ruppe {{icebreaker}} e partirono 612 mail con
  il segnaposto letterale.

USO
  crea_campagne.py --prova     dice cosa farebbe, non tocca niente
  crea_campagne.py             crea davvero
"""
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request

BASE = "https://server.smartlead.ai/api/v1"


def chiave():
    for riga in open(os.path.expanduser("~/.hermes/config.yaml"), encoding="utf-8"):
        m = re.match(r"\s*SMARTLEAD_API_KEY:\s*(\S+)", riga)
        if m:
            return m.group(1).strip("\"'")
    sys.exit("manca SMARTLEAD_API_KEY in ~/.hermes/config.yaml")


K = chiave()


def api(metodo, percorso, corpo=None):
    sep = "&" if "?" in percorso else "?"
    url = f"{BASE}{percorso}{sep}api_key={K}"
    dati = json.dumps(corpo).encode() if corpo is not None else None
    req = urllib.request.Request(url, data=dati, method=metodo,
                                 headers={"User-Agent": "clara/1.0",
                                          "Content-Type": "application/json"})
    for t in range(3):
        try:
            with urllib.request.urlopen(req, timeout=90) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            corpo_err = e.read()[:300].decode(errors="replace")
            if e.code in (429, 500, 502, 503) and t < 2:
                time.sleep(4 * (t + 1)); continue
            raise RuntimeError(f"Smartlead {e.code} su {metodo} {percorso}: {corpo_err}")
        except Exception as e:
            if t < 2:
                time.sleep(4 * (t + 1)); continue
            raise


# ── i copy, verbatim da Dre ───────────────────────────────────────
FIRMA = "Cordiali saluti,\nLorenzo Fornasier\nStudio Galilei\nStudiogalilei com."
FIRMA2 = "Cordiali saluti\nLorenzo Fornasier\nStudio Galilei\nStudiogalilei com."

APERTURA = {"nome": "Buongiorno {{first_name}},", "anonimo": "Alla cortese attenzione del titolare"}

COPY = {}

# 1-2. NON FANNO ADS
for chi, ap, salve in (("nome", "Buongiorno {{first_name}},", "Buongiorno {{first_name}},"),
                       ("anonimo", "Alla cortese attenzione del titolare,", "Salve,")):
    COPY[("non_fa_ads", chi)] = [
        ("Ho dato un occhiata ad {{azienda}}",
         f"""{ap}
{'Sono' if chi=='nome' else 'sono'} Lorenzo Fornasier di Studiogalilei,
Insieme al mio collega abbiamo dato un'occhiata a {{{{azienda}}}}, {{{{icebreaker}}}},
vi faccio i miei complimenti.
Abbiamo analizzato il vostro mercato e individuato canali pubblicitari specifici e
opportunità concrete che sarebbero interessanti per la vostra azienda.
Abbiamo preparato una breve analisi che mi piacerebbe condividerle.
Se le fa piacere riceverla, gliela mando subito, senza impegno.
{FIRMA}"""),
        ("Analisi marketing per {{azienda}}",
         f"""{salve}
le avevo scritto qualche giorno fa riguardo a un'analisi marketing su {{{{azienda}}}} che avevamo preparato.
È il tipo di lavoro che facciamo prima di ogni collaborazione,
ma in questo caso gliela offriamo gratuitamente perché mi piacerebbe avere un confronto con lei.
Ho messo dentro i canali consigliati, i dati di ricerca del vostro mercato
e le opportunità concrete che al momento non state intercettando.
Se mi conferma che la mail è corretta gliela invio subito e se
la trova interessante possiamo organizzarci per una chiamata conoscitiva.
{FIRMA}"""),
        ("Ultima mail da parte mia",
         f"""{'Buongiorno {{first_name}},' if chi=='nome' else 'Buongiorno,'}
le avevo scritto un po' di giorni fa riguardo a un'analisi marketing su {{{{azienda}}}} che avevamo preparato.
È un documento pratico, non una presentazione commerciale.
L'obiettivo era mostrarle le opportunità concrete che ci sono per la vostra attività,
prima di chiederle disponibilità per una chiamata conoscitiva.
Appena ha un attimo mi faccia sapere,
se invece non fosse interessato non c'è alcun problema,
intanto vi auguro buon lavoro.
{FIRMA}"""),
    ]

# 3-4. INVESTONO (il copy «fanno ads» di Dre)
for chi, ap, salve, ogg2, ogg3ap in (
        ("nome", "Buongiorno {{first_name}},", "Buongiorno,", "{{first_name}}, aspetto solo conferma mail", "Salve {{first_name}},"),
        ("anonimo", "Alla cortese attenzione del titolare", "Salve,", "Buongiorno, aspetto solo conferma mail", "Buongiorno,")):
    terza = (f"""{ogg3ap}
le avevo scritto qualche giorno fa riguardo a un'analisi marketing su {{{{azienda}}}} che avevamo preparato.""" if chi == "nome" else
             f"""{ogg3ap}
avevo scritto qualche giorno fa riguardo a un'analisi marketing su {{{{azienda}}}} che avevamo preparato da sottoporre all'attenzione del titolare.""")
    COPY[("investe", chi)] = [
        ("Analisi marketing su {{azienda}}",
         f"""{ap}
sono Lorenzo Fornasier di Studiogalilei.
insieme al mio collega abbiamo dato un'occhiata a {{{{azienda}}}}, {{{{icebreaker}}}},
vi faccio i miei complimenti.
Collaboriamo con aziende del vostro settore, abbiamo analizzato le vostre attività pubblicitarie
e trovato alcuni margini di miglioramento sulle attuali campagne Google Ads e nuove opportunità che al momento non state intercettando.
Abbiamo preparato una breve analisi con degli spunti che penso possiate trovare interessanti,
chiedo cortesemente il consenso di inviarglielo.
{FIRMA}"""),
        (ogg2,
         f"""{salve}
le avevo scritto qualche giorno fa riguardo a un'analisi che abbiamo preparato sulle campagne di {{{{azienda}}}}.
Abbiamo guardato esternamente cosa state già facendo e individuato alcuni punti dove potrebbe esserci margine per
ottenere piu' risultati.
È il tipo di lavoro che facciamo prima di ogni collaborazione, ma in questo caso gliel'ho voluto offrire gratuitamente
perché mi piacerebbe avere un confronto diretto con lei.
Se mi conferma che la mail è corretta gliela invio subito, dopo che le ha dato un occhiata,
se lo trova interessante potremmo organizzarci per un confronto.
{FIRMA2}"""),
        ("Chiudo qui se non è il momento",
         f"""{terza}
È un documento pratico, non una presentazione commerciale.
Volevamo darle qualcosa di utile in mano prima di chiederle disponibilità per una chiamata conoscitiva.
Appena ha un attimo mi faccia sapere se questa è la mail corretta,
se invece lei non fosse interessato, mi basta un no.
{FIRMA}"""),
    ]

# 5-6. PAGA MA È FERMO (i due nuovi, approvati da Dre il 22/9)
for chi, ap, salve, ogg2, ogg3ap in (
        ("nome", "Buongiorno {{first_name}},", "Buongiorno,", "{{first_name}}, aspetto solo conferma mail", "Salve {{first_name}},"),
        ("anonimo", "Alla cortese attenzione del titolare,", "Salve,", "Buongiorno, aspetto solo conferma mail", "Buongiorno,")):
    terza = (f"""{ogg3ap}
le avevo scritto qualche giorno fa riguardo a un'analisi marketing su {{{{azienda}}}} che avevamo preparato.""" if chi == "nome" else
             f"""{ogg3ap}
avevo scritto qualche giorno fa riguardo a un'analisi marketing su {{{{azienda}}}} che avevamo preparato da sottoporre all'attenzione del titolare.""")
    COPY[("paga_ma_fermo", chi)] = [
        ("Analisi marketing su {{azienda}}",
         f"""{ap}
sono Lorenzo Fornasier di Studiogalilei.
insieme al mio collega abbiamo dato un'occhiata a {{{{azienda}}}}, {{{{icebreaker}}}},
vi faccio i miei complimenti.
Collaboriamo con aziende del vostro settore, abbiamo guardato anche le vostre campagne su Google
e ci siamo segnati un paio di spunti che secondo noi potrebbero farle rendere di più.
Abbiamo preparato una breve analisi con quello che abbiamo visto,
chiedo cortesemente il consenso di inviargliela.
{FIRMA}"""),
        (ogg2,
         f"""{salve}
le avevo scritto qualche giorno fa riguardo a un'analisi che abbiamo preparato sulle campagne di {{{{azienda}}}}.
Le abbiamo guardate da fuori e ci sono un paio di margini interessanti, a parità di quello che già investite.
È il tipo di lavoro che facciamo prima di ogni collaborazione, ma in questo caso gliel'ho voluto offrire gratuitamente
perché mi piacerebbe avere un confronto diretto con lei.
Se mi conferma che la mail è corretta gliela invio subito, dopo che le ha dato un'occhiata,
se lo trova interessante potremmo organizzarci per un confronto.
{FIRMA2}"""),
        ("Chiudo qui se non è il momento",
         f"""{terza}
È un documento pratico, non una presentazione commerciale.
Volevamo darle qualcosa di utile in mano prima di chiederle disponibilità per una chiamata conoscitiva.
Appena ha un attimo mi faccia sapere se questa è la mail corretta,
se invece lei non fosse interessato, mi basta un no.
{FIRMA}"""),
    ]

GIORNI = {"non_fa_ads": [0, 2, 3], "investe": [0, 2, 2], "paga_ma_fermo": [0, 2, 3]}

CAMPAGNE = [
    ("cecchino",  "non_fa_ads",     "nome",    "Cecchino - non fanno ads"),
    ("cecchino",  "investe",        "nome",    "Cecchino - investono"),
    ("cecchino",  "paga_ma_fermo",  "nome",    "Cecchino - pagano ma e' fermo"),
    ("strascico", "non_fa_ads",     "anonimo", "Strascico - non fanno ads"),
    ("strascico", "investe",        "anonimo", "Strascico - investono"),
    ("strascico", "paga_ma_fermo",  "anonimo", "Strascico - pagano ma e' fermo"),
]


def controlla(testo, dove):
    """Le graffe devono essere pari e 2 per segnaposto: la lezione di giugno."""
    seg = re.findall(r"\{\{([a-z_]+)\}\}", testo)
    if testo.count("{") != testo.count("}"):
        sys.exit(f"GRAFFE SBILANCIATE in {dove}")
    if testo.count("{") != len(seg) * 2:
        sys.exit(f"SEGNAPOSTO ROTTO in {dove}: {testo.count('{')} graffe per {len(seg)} segnaposto")
    for s in seg:
        if s not in ("azienda", "first_name", "icebreaker"):
            sys.exit(f"SEGNAPOSTO SCONOSCIUTO «{s}» in {dove}")
    if re.search(r"https?://|\.pdf", testo):
        sys.exit(f"LINK O PDF in {dove}: vietati nella sequenza (playbook Ali)")
    if "​" in testo or "﻿" in testo:
        sys.exit(f"CARATTERI INVISIBILI in {dove}")


def main():
    prova = "--prova" in sys.argv
    D = os.path.expanduser("~/Desktop/CAMPAGNE 22-09")

    # tutti i copy passano il cancello PRIMA di toccare Smartlead
    for (ang, chi), mails in COPY.items():
        for i, (ogg, corpo) in enumerate(mails, 1):
            controlla(ogg, f"{ang}/{chi} mail {i} oggetto")
            controlla(corpo, f"{ang}/{chi} mail {i} corpo")
    print("cancello copy: passato, tutti i segnaposto interi\n")

    acc = api("GET", "/email-accounts?offset=0&limit=200")
    lor = [a for a in acc if "lorenzo" in (a.get("from_email") or "").lower()
           or "fornasier" in (a.get("from_email") or "").lower()]
    print(f"caselle di Lorenzo disponibili: {len(lor)}\n")

    for lista, ang, chi, nome in CAMPAGNE:
        file = [f for f in os.listdir(D) if f.startswith(f"{lista.upper()}_{ang}_")]
        if not file:
            print(f"  {nome}: MANCA il file dei lead"); continue
        n = int(file[0].rsplit("_", 1)[1].split(".")[0])
        titolo = f"{nome} /{n} (22/09/2026)"
        print(f"  {titolo}")
        if prova:
            continue
        c = api("POST", "/campaigns/create", {"name": titolo, "client_id": None})
        cid = c["id"]
        api("POST", f"/campaigns/{cid}/sequences", {"sequences": [
            {"seq_number": i + 1, "seq_delay_details": {"delay_in_days": GIORNI[ang][i]},
             "subject": ogg, "email_body": corpo.replace("\n", "<br>")}
            for i, (ogg, corpo) in enumerate(COPY[(ang, chi)])]})
        print(f"     creata id {cid}, sequenza di 3 mail")


if __name__ == "__main__":
    main()
