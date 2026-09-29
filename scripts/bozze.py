#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""LE BOZZE — Clara prepara la risposta, Dre approva e manda (7/9/2026).

PERCHE'
Dre: «voglio aumentare il nostro tempo di risposta. All'inizio, anche se ha
tutte le informazioni, voglio le bozze e approvo io. Quando vedo che diventa
brava, lascio che gestisca lei e mi contatta quando non sa».

COME
Per ogni persona che aspetta una risposta da noi, Clara legge il playbook
(docs/clara-sg-outbound.md), la scheda e l'ultimo messaggio, decide l'intento
(A..H), sceglie il template, scrive la bozza e la mette nella sua stanza come
proposta di tipo «risposta». Se il caso e' fra quelli in cui deve fermarsi
(prezzo insistito, richiesta legale, obiezione complessa, non si capisce),
prepara comunque la bozza migliore e la segna «da guardare tu».

Ogni bozza passa dal CANCELLO QUALITA' (lo stesso di lint_risposta.py del
3/7): trattino lungo, registro misto tu/lei, apertura secca, firma nel corpo,
promesse vietate. Se non passa, si riscrive una volta; se non passa ancora,
si mette in stanza con l'avviso invece di sparire.

NESSUNA BOZZA SENZA LETTURA (25/9/2026, dopo le quattro riprese sbagliate).
Un motore solo scrive, e prima LEGGE: il thread vero (lettura.filo, anche da
Smartlead), i fatti che il codice sa verificare (lettura.ha_gia: abbiamo gia'
scritto dopo? ha gia' l'analisi? ha detto no? autorisposta?), le regole dure
(lettura.regola_dura) e una seconda testa che confronta loro/noi/bozza
(lettura.coerenza). La lettura viaggia dentro la proposta (azione.lettura) e il
database rifiuta una «risposta» che non ce l'ha (schema_v58). I follow-up e le
riprese non scrivono piu': followup.py e strumenti/ripresa.py mettono in coda
(prospects.coda = il gruppo), e scrive questo motore, con il template di Dre.

USO
  python3 scripts/bozze.py --prova      mostra le bozze, non scrive
  python3 scripts/bozze.py              mette le bozze nella stanza
  python3 scripts/bozze.py --quanti 5
"""

import datetime
import os
import re
import sys
import urllib.request
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cervello                                            # noqa: E402
from stanza import sb, proponi, quando, senza_trattini, sb_tutte     # noqa: E402
import lettura                                             # noqa: E402
import seguiti                                             # noqa: E402

RADICE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROVA = "--prova" in sys.argv
QUANTI = int(sys.argv[sys.argv.index("--quanti") + 1]) if "--quanti" in sys.argv else 25
SOLO = [e.strip().lower() for e in sys.argv[sys.argv.index("--email") + 1].split(",")] if "--email" in sys.argv else []   # solo queste (rifare una bozza, o provare)
IN_PARALLELO = 5
PRONTE = []        # (prospect_id, nome, con_analisi): per la notifica sul telefono
CALENDARIO = "https://calendar.app.google/szPdtoZD8KqyxkmJ8"   # Dre 29/9: «questo e' il link corretto, dimentica tutto il resto»

# a chi si risponde: chi ha scritto e aspetta, e ha un intento a cui si risponde
CLASSI = ("positivo", "tiepido", "rinvio", "da_classificare", "persona_sbagliata")   # persona sbagliata: solo se ci ha dato il contatto nuovo (email_alt), 25/9
INTOCCABILI = ("cliente", "perso", "call_fissata", "rinviato")

# IL GIGANTE BUONO (Dre, 14/9): ai negativi cortesi mandiamo lo stesso
# l'analisi che avevamo preparato, una volta sola, con il calendario e un
# saluto. Mai a chi chiede di non essere contattato, cita la privacy o e'
# scortese: quelli restano fuori, e' la regola sacra. Passa dalla Posta.
QUANTI_GB = 5        # per giro, cosi' la Posta non si riempie
GIORNI_GB = 45       # oltre, «l'avevamo gia' preparata» suona strano
# «privacy» c'e' apposta: chi la nomina (anche solo in firma) non riceve niente
# la stessa regola di analisi_auto, in un posto solo (28/9): due copie divergono
def _non_toccare():
    import importlib
    return importlib.import_module("analisi_auto").NON_TOCCARE


class _Pigra:
    """Si carica alla prima domanda: analisi_auto importa bozze, e viceversa."""
    def search(self, t):
        return _non_toccare().search(t)


NON_TOCCARE = _Pigra()
ISTRUZIONE_GB = """Scrivi la risposta a un'azienda che ci ha detto di NO in modo cortese (non
interessati, hanno gia' un'agenzia, non e' il momento). L'analisi della sua zona
l'avevamo gia' preparata: gliela lasciamo lo stesso, senza chiedere niente in
cambio. Tono: il gigante buono. Grato, leggero, zero vendita, zero insistenza.

Rispondi con queste righe, poi una riga «---», poi il testo:
INTENTO: INT-GB
FERMATI: no | si': il motivo (solo se il no era in realta' scortese o chiedeva di non essere contattato)
NOTA: una riga su cosa hai usato dell'analisi
---
Il testo: registro «lei», 5-7 righe, mai il trattino lungo, niente firma.
1) ringrazia della risposta e prendi atto del no senza discuterlo;
2) di' che l'analisi della loro zona era gia' pronta e gliela lasciamo in
   allegato, con UN numero vero se c'e' (le ricerche al mese nella provincia);
3) chiudi: se un giorno vorranno piu' clienti, noi siamo qui, con {{CALENDARIO}};
4) un saluto gentile. Nessun follow-up promesso, nessuna domanda."""

# ── il cancello qualita' (da lint_risposta.py, 3/7) ─────────────────
TU = re.compile(r"\b(tu|ti|te|tuo|tua|tuoi|tue|puoi|hai|sei|vuoi|pensi|trovi|scegli)\b", re.I)
LEI = re.compile(r"\b(lei|le|la ringrazio|suo|sua|suoi|sue|puo'|può|vorra'|vorrà|preferisce)\b", re.I)
APERTURE_SECCHE = ("si'.", "sì.", "no.", "volentieri.", "certo.", "ok.", "va bene.")
PROMESSE = ("garantiamo risultati", "rendimento garantito", "successo assicurato", "senza impegno")


def cancello(testo, senza_analisi=False):
    """Torna la lista dei motivi per cui la bozza NON va bene (vuota = passa).

    `senza_analisi` e' vero quando l'analisi non esiste e non nascera' (fit NO):
    in quel caso la bozza non deve prometterla. 29/9: Elettroone ha chiesto
    l'analisi, la bozza ha risposto «le inoltro qui l'analisi», e quel documento
    non poteva nascere perche' a Trento ci sono 50 ricerche al mese.
    """
    if senza_analisi and re.search(
            r"(?:inoltro|allego|le lascio|trova|in allegato|le mando|le invio|gliela mando)"
            r"[^.]{0,40}\banalisi\b|\banalisi\b[^.]{0,30}(?:in allegato|qui sotto|allegata)", testo, re.I):
        return ["promette un'analisi che non puo' nascere (il fit dice NO): "
                "va risposto senza prometterla, dicendo il motivo"]
    if re.search(r"\[(ESCALATION|NOTA|INTERNO|FERMATI)", testo, re.I):
        return ["riga interna nel testo ([ESCALATION]/nota): il lead non deve vederla"]
    if re.search(r"rimuov\w* dalle (nostre )?liste|non la disturber|per policy lavoriamo solo", testo, re.I):
        return ["chiusura scritta da Clara: non chiude mai lei, decide Dre"]
    if re.search(r"(^|\n)\s*(salve|buongiorno|gentile|ciao)?\s*[\w.+-]+@[\w-]+\.[\w.-]+\s*[,:]", testo, re.I):
        return ["un indirizzo email usato come nome (caso Kormed, 25/9)"]
    errori = []
    low = testo.lower()
    if "—" in testo:
        errori.append("trattino lungo")
    tu, lei = TU.findall(testo), LEI.findall(testo)
    if tu and lei:
        errori.append(f"registro misto tu/lei ({', '.join(sorted(set(w.lower() for w in tu))[:3])})")
    righe = [r.strip() for r in testo.splitlines() if r.strip()]
    if righe:
        corpo = righe[1] if len(righe) > 1 and righe[0].lower().startswith(("buongiorno", "salve", "buonasera", "gentile", "ciao")) else righe[0]
        prima = corpo.split(".")[0].strip().lower() + "."
        if prima in APERTURE_SECCHE:
            errori.append(f"apertura secca «{corpo[:25]}»")
    if "lorenzo fornasier" in low and ("via francesco baracca" in low or "+39" in low):
        errori.append("firma completa nel corpo: la mette Smartlead")
    for p in PROMESSE:
        if p in low:
            errori.append(f"frase vietata «{p}»")
    return errori


def template_verbatim():
    """I TEMPLATE DI DRE, PAROLA PER PAROLA (24/9: «Clara non scrive rispettando le bozze»).
    Stanno nel bucket privato (riservato/risposte-template.md), copia del file del vault
    «Risposte (template verbatim).md». Se il bucket non risponde, si va avanti col solo playbook."""
    try:
        import tempfile, time as _t
        loc = os.path.join(tempfile.gettempdir(), "odyn-risposte-template.md")
        if not os.path.exists(loc) or _t.time() - os.path.getmtime(loc) > 3600:
            from stanza import env
            req = urllib.request.Request(f"{env('VITE_SUPABASE_URL')}/storage/v1/object/vault/riservato/risposte-template.md",
                                         headers={"apikey": env("SUPABASE_SERVICE_KEY"), "Authorization": f"Bearer {env('SUPABASE_SERVICE_KEY')}"})
            with urllib.request.urlopen(req, timeout=60) as r:
                open(loc, "wb").write(r.read())
        return "\n\n" + open(loc, encoding="utf-8").read()
    except Exception as e:                                       # noqa: BLE001
        print(f"  (template verbatim non caricati: {str(e)[:80]})")
        return ""


def playbook():
    """Il playbook outbound NON sta nel repo (22/9/2026: il repo e' pubblico
    per avere le Actions gratis, e il playbook e' il nostro metodo, non
    roba da regalare ai concorrenti). Vive nel vault privato; in cloud
    arriva dal segreto PLAYBOOK_OUTBOUND."""
    dal_segreto = os.environ.get("PLAYBOOK_OUTBOUND")
    if dal_segreto:
        return dal_segreto
    vault = os.path.expanduser(
        "~/Documents/Obsidian/studiogalilei/Sistema Operativo Studio Galilei/"
        "ODYN Cockpit/riservato/clara-sg-outbound.md")
    if os.path.exists(vault):
        return open(vault, encoding="utf-8").read()
    raise RuntimeError(
        "manca il playbook outbound: deve stare nel vault "
        "(ODYN Cockpit/riservato/clara-sg-outbound.md) oppure nel segreto "
        "PLAYBOOK_OUTBOUND del workflow")


def proposta_giorno_ora():
    """Playbook 1.0, cap. 2: futuro, feriale, almeno 48 ore avanti, mai lo
    stesso giorno; scritto sempre «giorno + data».
    24/9 (Dre: «per decidere l'ora ha guardato il mio calendario?»): adesso si'.
    Il primo buco libero di Dre nei prossimi giorni feriali, fra le 10 e le
    16:30, saltando la pausa pranzo, a un'ora di distanza da ogni evento suo."""
    giorni = ["lunedì", "martedì", "mercoledì", "giovedì", "venerdì", "sabato", "domenica"]
    mesi = ["gennaio", "febbraio", "marzo", "aprile", "maggio", "giugno", "luglio", "agosto",
            "settembre", "ottobre", "novembre", "dicembre"]
    roma = datetime.timezone(datetime.timedelta(hours=2))
    oggi = datetime.datetime.now(roma).date()
    d = oggi + datetime.timedelta(days=2)
    while d.weekday() >= 5:
        d += datetime.timedelta(days=1)
    occupati = []
    try:
        da = (d - datetime.timedelta(days=1)).isoformat(); a = (d + datetime.timedelta(days=8)).isoformat()
        for ev in sb("GET", f"/rest/v1/agenda?select=at,fonte,owner&at=gte.{da}&at=lte.{a}&limit=300") or []:
            # il calendario di Dre entra come fonte «gcal» secca (gli altri hanno la mail nella fonte)
            if (ev.get("fonte") or "gcal") == "gcal" or "dramane" in (ev.get("fonte") or ""):
                occupati.append(datetime.datetime.fromisoformat(ev["at"].replace("Z", "+00:00")).astimezone(roma))
    except Exception:
        occupati = []
    # Documento Gold (Dre): pomeriggio preferito, mai weekend, mai lunedi' a meno
    # che lo propongano loro. Quindi prima i pomeriggi della settimana, poi le mattine.
    for fascia in (((14, 30), (15, 0), (15, 30), (16, 0), (16, 30)), ((10, 0), (10, 30), (11, 0), (11, 30), (12, 0))):
      for salto in range(7):
        g = d + datetime.timedelta(days=salto)
        if g.weekday() >= 5 or g.weekday() == 0:
            continue
        for ora, minuti in fascia:
            t = datetime.datetime(g.year, g.month, g.day, ora, minuti, tzinfo=roma)
            if all(abs((t - o).total_seconds()) >= 3600 for o in occupati):
                return f"{giorni[g.weekday()]} {g.day} {mesi[g.month - 1]} alle {ora}" + (f":{minuti:02d}" if minuti else "")
    while d.weekday() in (0, 5, 6):
        d += datetime.timedelta(days=1)
    return f"{giorni[d.weekday()]} {d.day} {mesi[d.month - 1]} alle 15"


ISTRUZIONE = """Sei Clara. Prepari la risposta con l'identita' di Lorenzo; la manda lui
o Dre dopo l'ok (legge zero). Il playbook qui sopra e' la legge: fai gli 8
controlli del preflight, scegli l'intento nella tabella, applica le regole di
calendario e di stile.

SE CHIEDE L'ANALISI, SI MANDA. SEMPRE. (Dre, 29/9: «inviamo comunque e chiediamo
la call, seguiamo il playbook tutte le volte possibili»). Il playbook INT-01 dice
«manda analisi + presentazione, poi orario proposto + calendario», e non fa
eccezioni: quando una persona la chiede esplicitamente, quella e' la risposta.
Il verdetto del fit NON cambia questa regola.

Se nei fatti «analisi_non_si_puo_fare» e' vero, vuol dire solo che il mercato su
Google e' piccolo per loro (il motivo sta in «perche_niente_analisi»). Allora:
  - si manda lo stesso l'analisi, che dentro dira' la verita' scomoda;
  - si aggiunge UNA riga onesta prima della call, per esempio «le anticipo che
    nella vostra zona la domanda su Google e' bassa: nell'analisi trova i numeri
    e dove conviene spendere invece»;
  - si propone la call come sempre.
Non si rifiuta mai di mandare un documento che la persona ha chiesto. Quello che
non si fa e' prometterlo quando non esiste ancora e non verra' preparato: in quel
caso la bozza aspetta che l'analisi ci sia.

LA SCRIVANIA. Nei fatti trovi «sequenza»: TUTTO lo scambio con questa persona in
ordine di tempo, le nostre mail e le sue, piu' «quante_ne_abbiamo_mandate» e
«quante_ne_ha_scritte». Leggila tutta PRIMA di scrivere. Serve a tre cose:
  - non ripetere quello che gli abbiamo gia' detto, e non riproporre una cosa
    che ha gia' ricevuto o gia' rifiutato;
  - continuare il discorso da dove si e' fermato, non ricominciare da capo;
  - accorgerti se gli abbiamo scritto tante volte e lui ha risposto poco: in quel
    caso si abbassa il tono e non si insiste.
Se la sequenza si contraddice con l'ultima mail, vince la sequenza intera.

Rispondi ESATTAMENTE in questo formato, niente altro:

LETTURA: cosa dice l'ultima mail loro, in una riga, con le SUE parole (citala)
HA_GIA: analisi ricevuta si'/no; ha detto no si'/no; autorisposta si'/no; ci gira a: email o no
INTENTO: INT-xx (il codice della tabella)
PREFLIGHT: ok | fallito: quale controllo e perche'
FERMATI: no | si': il motivo in 10 parole (i casi del capitolo 5, o preflight fallito)
NOTA: una riga su cosa hai adattato e perche'
ATTACCO: 3-6 parole per aprire la frase dell'analisi, adattate a cosa ha scritto (es. «Va bene perfetto,» «Grazie per la conferma,»)
PERIODO: solo se rinvia, quando risentirsi con le sue parole (es. «a ottobre/novembre», «dopo le feste»); altrimenti -
---
il testo della bozza, pronto da incollare, SENZA firma (la mette Smartlead),
con {{CALENDARIO}} e {giorno data ora} gia' sostituiti coi valori che ti do.
Se FERMATI e' si', la bozza e' comunque la risposta del template come se non ti
fossi fermata: MAI una chiusura, MAI «la rimuovo dalle liste», MAI un rifiuto
scritto da te (Dre, 25/9: «Clara questo non lo deve fare»). Il dubbio va nel
campo FERMATI e nella NOTA, non nel testo. Nel testo della bozza non ci sono
mai righe interne, tag fra parentesi quadre o note per Dre.
Se INT-25 (non e' chiaro cosa vuole): due bozze alternative, separate da una
riga «=== ALTERNATIVA ===».

I TEMPLATE DI DRE SONO LA LEGGE (24/9). Qui sotto trovi «Risposte (template
verbatim)»: per ogni intento c'e' il testo che Dre vuole, parola per parola.
La bozza E' quel testo: lo copi intero e cambi SOLO (a) l'incipit, adattato a
cosa ha scritto davvero la persona («Va bene perfetto» non e' fisso), (b) nome,
azienda e slot proposto, (c) le righe che il template stesso dice di adattare.
Niente riscritture, niente frasi tue al posto delle sue, niente paragrafi in
piu'. Mappa: INT-01 e INT-02 → INTERESSATO; INT-03 e INT-04 → CHI SEI?;
INT-15 → QUAL'E' LA VOSTRA SOCIETA'?; INT-05 e INT-06 → SENTIAMOCI PIU' AVANTI;
INT-07 → RICONTATTO DOPO OUT OF OFFICE; INT-08 e INT-09 → RIMBALZO INTERNO;
INT-22 → FOLLOW UP 1; INT-23 → INTERESSATO senza la proposta di call. Per gli
altri intenti segui il playbook con lo stesso tono dei template. Il link del
calendario e' sempre {{CALENDARIO}}, non quello scritto nel template.

MAI INVENTARE (24/9, Dre): non dire mai che abbiamo letto, visto, controllato o
apprezzato qualcosa se non sta scritto nella SCHEDA o nel suo messaggio. Un
numero, un luogo, un fatto: solo dalla scheda. Se non c'e', non c'e'. Al
massimo ringrazi, senza aggiungere cose nostre.

Regole che non si discutono: registro «lei», mai «tu»; mai il trattino
lungo; mai aprire con «volentieri.» o «si'.» secchi; niente firma; il link
del calendario solo a chi e' caldo o l'ha chiesto, mai ai tiepidi o nei
follow-up; se ha chiesto lui la call non mandare l'analisi, fissa la call;
se e' un «ok» o «grazie» secco: NON fermarti, e' un consenso, gli si manda
l'analisi con due righe (23/9). Se analisi_pronta_in_allegato e' true, la
bozza dice che l'analisi e' allegata e non chiede piu' il consenso; non
fermarti mai per «allegati mancanti»: l'allegato lo mette Dre.

SE C'E' UN GRUPPO (RIPRESA, RINVIO SCADUTO, RICONTATTO OOO, FOLLOW UP 1, MINI
FOLLOW UP): non e' una risposta a una mail nuova, e' un ricontatto deciso da noi.
La bozza E' il template di quel gruppo, parola per parola, con il nome. Il codice
ha gia' verificato che il gruppo regge (per RIPRESA: che non abbiamo mai scritto
dopo la sua mail e che non ha l'analisi). Tu leggi lo stesso la sua ultima mail:
se il template stona con quello che ha scritto (una domanda precisa rimasta senza
risposta, un dettaglio che lui aspettava, un nome diverso in firma), adatta SOLO
l'incipit o fermati con il motivo. L'INTENTO per i gruppi e' RIPRESA. Nei gruppi
NON aggiungi uno slot («le propongo martedi'...»), non aggiungi righe, non
togli righe: il template e' gia' completo, cambi solo nome e incipit.

SE C'E' UN DESTINATARIO NUOVO (destinatario_effettivo diverso dall'email della
scheda): la mail PARTE a quell'indirizzo, non nel vecchio thread. Scrivi al
nuovo contatto direttamente, come prima mail a lui: niente «metto in copia»,
niente «grazie per il passaggio» rivolto a chi non la legge. Un indirizzo email
NON e' un nome: se il nome non c'e', «Salve,» secco."""


def come_corregge_dre(quante=8):
    """Le ultime bozze che Dre ha cambiato prima di mandarle: la versione di Clara
    contro la sua. Vanno nel prompt, cosi' la volta dopo Clara parte da li'.
    (23/9: «le correzioni che faccio deve ragionare, capirne il motivo e impostarsi per migliorare»)."""
    try:
        fatte = sb("GET", "/rest/v1/proposte?select=prospect_id,azione,risposta_il,risposta&tipo=eq.risposta&stato=in.(fatta,no)"
                          "&risposta_il=not.is.null&order=risposta_il.desc&limit=40") or []
    except Exception:
        return ""
    lezioni = []
    for x in fatte:
        bozza = ((x.get("azione") or {}).get("bozza") or "").strip()
        if not bozza or not x.get("prospect_id"):
            continue
        if x.get("risposta") and "pulizia" in x["risposta"]:
            continue
        if x.get("risposta") and x["risposta"].startswith("NO:"):
            lezioni.append(f"SCARTATA da Dre: {x['risposta'][3:200]}\n  la bozza era: {bozza[:300]}")
        else:
            out = sb("GET", f"/rest/v1/interactions?select=body&prospect_id=eq.{x['prospect_id']}&kind=eq.email_out"
                            f"&at=gte.{x['risposta_il'][:10]}&order=at.asc&limit=1") or []
            finale = (out[0].get("body") or "").strip() if out else ""
            if finale and finale != bozza:
                lezioni.append(f"BOZZA DI CLARA: {bozza[:350]}\nVERSIONE DI DRE: {finale[:350]}")
        if len(lezioni) >= quante:
            break
    if not lezioni:
        return ""
    return ("\n\nCOME CORREGGE DRE (le ultime volte). Guarda cosa cambia e perche': tono, lunghezza, "
            "cosa toglie, cosa aggiunge. Parti gia' da li'.\n\n" + "\n\n".join(lezioni))


def chiedi_bozza(p, ultimo, riprova=None, gruppo=None, letti=None):
    fatti = {
        "nome": p.get("name") or "", "azienda": p.get("company") or "", "email": p.get("email"),
        "classificazione": p.get("classificazione"), "stage": p.get("stage"),
        "analisi_inviata": bool(p.get("analysis_sent")), "analisi_inviata_il": (p.get("analysis_sent_at") or "")[:10],
        # 23/9: l'analisi la prepara analisi_auto.py prima delle bozze; se c'e', la bozza la allega («gliela allego qui sotto»)
        "analisi_pronta_in_allegato": bool(p.get("analysis_pdf")),
        # L'ANALISI CHE NON ARRIVERA' MAI (29/9). Elettroone ha chiesto «puo'
        # inviarmi pure l'analisi» e la bozza ha risposto «le inoltro qui
        # l'analisi»: ma il fit dice NO (50 ricerche/mese a Trento, meno di due
        # clic al giorno), quindi quell'analisi non nascera'. Promettere una cosa
        # che non arriva e' peggio che dire di no. Lo stesso su Studio Canova.
        "analisi_non_si_puo_fare": (not p.get("analysis_pdf")
                                    and ((p.get("enriched") or {}).get("google_fit") or {}).get("verdetto") == "NO"),
        "perche_niente_analisi": (((p.get("enriched") or {}).get("google_fit") or {}).get("motivo") or "")[:160]
        if (not p.get("analysis_pdf")
            and ((p.get("enriched") or {}).get("google_fit") or {}).get("verdetto") == "NO") else "",
        "ultima_sua_mail": (p.get("last_reply_at") or "")[:10], "settore": p.get("sector"), "citta": p.get("city"),
    }
    # il Google Fit di Clara (googlefit.py): il numero della zona va nel messaggio,
    # e' la personalizzazione che ha fatto rispondere Orobica e Sarci
    fit = (p.get("enriched") or {}).get("google_fit") or {}
    if fit:
        fatti["google_fit"] = {"verdetto": fit.get("verdetto"), "motivo": fit.get("motivo"), "cosa_fa": fit.get("cosa_fa"),
                               "provincia": fit.get("provincia"), "zona": fit.get("zona")}
    # LA SCRIVANIA: TUTTA LA SEQUENZA, NON DUE MESSAGGI (Dre, 28/9). Fino a oggi
    # la storia si prendeva dal CRM, che NON ha le mail partite da Smartlead: su
    # Istituto Flegreo il CRM conosceva due righe su sei, e tutte e due in arrivo.
    # Il modello scriveva senza sapere nemmeno cosa gli avevamo gia' mandato.
    # Il filo completo lo costruisce gia' lettura.filo() unendo CRM e Smartlead:
    # si usa quello. Dre: «una scrivania per lead, con le sequenze in ordine e il
    # playbook accanto, cosi' sa sempre cosa scrivere e ha sempre contesto».
    try:
        intero = lettura.filo(p)
        if intero:
            fatti["sequenza"] = [
                f"{str(x.get('at'))[:10]} {'NOI' if x.get('kind') in ('email_out', 'followup', 'analisi') else 'LORO' if x.get('kind') == 'email_in' else x.get('kind').upper()}: "
                + " ".join((x.get("body") or "").split())[:400]
                for x in intero[-12:]
            ]
            fatti["quante_ne_abbiamo_mandate"] = sum(1 for x in intero if x.get("kind") in ("email_out", "followup", "analisi"))
            fatti["quante_ne_ha_scritte"] = sum(1 for x in intero if x.get("kind") == "email_in")
        else:
            storia = sb("GET", f"/rest/v1/interactions?select=kind,at,body&prospect_id=eq.{p['id']}&kind=in.(email_in,email_out,call,nota)&order=at.desc&limit=6") or []
            fatti["sequenza"] = [f"{x['at'][:10]} {x['kind']}: {' '.join((x.get('body') or '').split())[:300]}" for x in reversed(storia)]
    except Exception as e:                                    # noqa: BLE001
        fatti["sequenza"] = [f"(non sono riuscita a ricostruire il filo: {str(e)[:60]})"]
    sintesi = (p.get("enriched") or {}).get("analisi") or {}
    if sintesi:
        fatti["analisi_sintesi"] = sintesi
    alt = p.get("email_alt") or []
    alt = (alt if isinstance(alt, list) else [alt])
    if alt and alt[0]:
        fatti["destinatario_effettivo"] = alt[0]
        fatti["nome_del_nuovo_contatto"] = ""          # se non e' nella scheda non c'e': «Salve,»
    if letti:
        fatti["fatti_verificati_dal_codice"] = {k: letti[k] for k in ("scritto_dopo_di_lei", "analisi_ricevuta", "analisi_gia_letta", "detto_no", "autorisposta", "girato_a")}
        if letti.get("ultima_nostra"):
            fatti["ultima_mail_nostra"] = f"{letti['ultima_nostra_il']}: {letti['ultima_nostra'][:400]}"
    if gruppo:
        fatti["gruppo"] = gruppo
        fatti["template_da_usare"] = gruppo
    prompt = (cervello.ruolo("preparatore") + cervello.manuale("testa", "outbound", "template") + cervello.istruzione("contesto") + "\n\n" + ISTRUZIONE + cervello.istruzione("chat") + cervello.istruzione("bozze") + LEZIONI +
              f"\n\nVALORI DA USARE: {{{{CALENDARIO}}}} = {CALENDARIO}, slot da proporre = {proposta_giorno_ora()}, oggi e' {datetime.date.today():%A %d %B %Y}"
              f"\n\nLA SCHEDA:\n{fatti}\n\nL'ULTIMO MESSAGGIO CHE HA SCRITTO:\n{ultimo[:2500]}")
    if riprova:
        prompt += f"\n\nLA BOZZA PRECEDENTE NON E' PASSATA IL CANCELLO PER: {riprova}. Riscrivila correggendo solo quello."
    grezzo = cervello._chiedi(prompt)
    m = re.search(r"\n\s*(?:-{3,}|\*{3,})\s*\n", grezzo)
    if not m:
        return None
    testa, bozza = grezzo[:m.start()], grezzo[m.end():]
    campi = {}
    for riga in testa.splitlines():
        if ":" in riga:
            k, v = riga.split(":", 1)
            campi[k.strip().upper()] = v.strip()
    bozza = bozza.strip().strip("`").strip()
    fermati = campi.get("FERMATI", "no")
    if campi.get("PREFLIGHT", "ok").lower().startswith("fallito") and fermati.lower().startswith("no"):
        fermati = "si': preflight " + campi["PREFLIGHT"]
    bozza = bozza.replace("{{CALENDARIO}}", CALENDARIO).replace("{{ CALENDARIO }}", CALENDARIO)
    bozza = senza_trattini(bozza)          # 29/9: lo toglie il codice, non un secondo giro del modello
    return {"intento": campi.get("INTENTO", "?")[:7], "template": gruppo or campi.get("INTENTO", ""),
            "fermati": fermati, "nota": campi.get("NOTA", ""), "bozza": bozza,
            "attacco": campi.get("ATTACCO", ""), "periodo": "" if campi.get("PERIODO", "-").strip() in ("-", "") else campi.get("PERIODO", ""),
            "lettura_di_clara": campi.get("LETTURA", ""), "ha_gia_di_clara": campi.get("HA_GIA", "")}


LEZIONI = ""


def testo_di_dre(b, p, letti):
    """La bozza del modello diventa il template di Dre composto dal codice, se per
    quell'intento ce n'e' uno (seguiti.risposta). Una funzione sola: la usano il
    motore e il banco di prova, cosi' si prova quello che gira davvero."""
    if not b or b.get("dal_codice"):
        return b
    giorno = proposta_giorno_ora()
    comp = seguiti.risposta(b.get("intento"), p, letti, CALENDARIO, giorno=giorno, attacco=b.get("attacco"),
                            periodo=b.get("periodo"), loro=(letti or {}).get("ultima_loro") or "")
    if comp:
        b = {**b, "bozza_modello": b["bozza"], "bozza": comp, "dal_codice": True, "giorno": giorno,
             "nota": f"il template di Dre parola per parola ({b.get('intento')}); " + (b.get("nota") or "")}
    return b


CHIUDONO = ("non c'è nessuno a cui scrivere", "nessun ricontatto")


def chiudi_attesa(p, motivo):
    """NESSUNO A CUI RISPONDERE (29/9): l'attesa si chiude col motivo nella scheda.
    Chi riscrive torna da solo (il sync rimette l'attesa). Prima restavano «in
    attesa» per sempre: caselle ticket, no senza gigante buono, soppressi, fuori
    target. Dre li vedeva fra i «da rispondere» e non c'era niente da rispondere."""
    print(f"  attesa chiusa: {(p.get('company') or p.get('name') or p.get('email') or '')[:34]}: {motivo}")
    if PROVA:
        return
    fresco = (sb("GET", f"/rest/v1/prospects?select=enriched&id=eq.{p['id']}") or [{}])[0]
    arr = dict(fresco.get("enriched") or {})
    arr["lettura_esito"] = {"motivo": motivo, "il": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")}
    sb("PATCH", f"/rest/v1/prospects?id=eq.{p['id']}", {"awaiting_us": False, "enriched": arr})


def chiudi_attese_senza_risposta():
    """Chi aspetta ma a cui non si risponde mai: chi e' gia' stato letto con un motivo che chiude (le caselle di servizio lette col
    codice di prima del 29/9, che l'attesa non la chiudeva)."""
    n = 0
    for p in sb("GET", "/rest/v1/prospects?select=id,company,name,email,classificazione,last_reply_at,enriched"
                       "&awaiting_us=eq.true&limit=500") or []:
        c = p.get("classificazione")
        esito = (p.get("enriched") or {}).get("lettura_esito") or {}
        # soppressi, fuori target e nervosi NO: il Revisore il 29/9 ha fermato anche la sola
        # chiusura dell'attesa («mai toccare chi e' fuori o soppresso»). Decide Dre.
        if c in ("soppresso", "fuori_target", "nervoso"):
            continue
        if isinstance(esito, dict) and any(k in (esito.get("motivo") or "") for k in CHIUDONO) \
                and (esito.get("il") or "") >= (p.get("last_reply_at") or "")[:19]:
            chiudi_attesa(p, esito["motivo"]); n += 1
    return n


def main():
    global LEZIONI
    print("LE BOZZE" + (" (prova: non scrive niente)" if PROVA else ""))
    if not SOLO:
        chiudi_attese_senza_risposta()
    LEZIONI = come_corregge_dre()
    if LEZIONI:
        print(f"  (Clara ha {LEZIONI.count('BOZZA DI CLARA') + LEZIONI.count('SCARTATA')} correzioni di Dre da cui partire)")
    CAMPI = ("id,name,company,email,email_alt,classificazione,stage,analysis_sent,analysis_sent_at,analysis_pdf,"
             "last_reply_at,sector,city,enriched,campaign_id,lead_id,coda,coda_il,next_action_date,campaign")
    persone = sb("GET", "/rest/v1/prospects?awaiting_us=eq.true&fuori=eq.false"
                        f"&classificazione=in.({','.join(CLASSI)})"
                        f"&select={CAMPI}&order=last_reply_at.desc&limit=300") or []
    # LA CODA (25/9): chi va ricontattato (ripresa, rinvio scaduto, dopo le ferie, follow-up).
    # Lo hanno messo in coda followup.py e ripresa.py; il testo lo scrive solo questo motore.
    in_coda = sb("GET", f"/rest/v1/prospects?coda=not.is.null&fuori=eq.false&select={CAMPI}&order=coda_il.asc&limit=300") or []
    # con una proposta aperta di qualunque tipo si aspetta Dre: se la classe e'
    # in discussione, la bozza sarebbe scritta sulla classe sbagliata
    aperte = {x["prospect_id"] for x in (sb("GET", "/rest/v1/proposte?select=prospect_id&stato=in.(aperta,approvata,in_invio)") or [])}
    if SOLO:
        persone = sb("GET", f"/rest/v1/prospects?email=in.({','.join(SOLO)})&select={CAMPI}") or []
        in_coda, aperte = [p for p in persone if p.get("coda")], set()
        persone = [p for p in persone if not p.get("coda")]

    def gia_letta(p):
        """Saltata con motivo dopo la sua ultima mail: non si rilegge ogni cinque minuti."""
        e = (p.get("enriched") or {}).get("lettura_esito") or {}
        return bool(e.get("il")) and e["il"] >= (p.get("last_reply_at") or "")[:19] and not SOLO

    candidate = []
    for p in persone:
        if p["id"] in aperte or p.get("stage") in INTOCCABILI or p.get("coda") or "usa" in (p.get("campaign") or "").lower() or gia_letta(p):
            continue
        candidate.append((p, None))
    # 29/9: chi e' in coda ma nel frattempo e' diventato perso, cliente o ha la call
    # fissata non si ricontatta, e la coda si toglie col motivo. Prima veniva saltato
    # in silenzio a ogni giro, per sempre: nove follow-up fermi dal 25/9 per aziende
    # gia' nei Persi, e il calendario diceva «arriva al prossimo giro».
    fuori_coda = []
    for p in in_coda:
        if p.get("stage") in INTOCCABILI:
            fuori_coda.append((p, f"non si ricontatta: nel frattempo e' «{p.get('stage')}»"))
            continue
        if p["id"] in aperte or p.get("coda") not in lettura.GRUPPI:
            continue
        candidate.append((p, p["coda"]))
    # CHI E' PRONTO PASSA DAVANTI (27/9). Il giro ne serve venticinque, e il
    # posto se lo prendevano quelli che aspettano un'analisi che non c'e'
    # ancora: due giorni con nove follow-up pronti fermi dietro di loro, e
    # ogni corsa che finiva con «zero bozze, ok». Chi ha tutto quello che
    # serve viene prima; chi aspetta qualcos'altro sta dietro e il suo turno
    # arriva quando l'attesa e' finita. Stessa regola dell'analisi: un lavoro
    # che non puo' riuscire non deve affamare quelli che possono.
    def pronto(voce):
        pr, gruppo = voce
        if gruppo in ("RIPRESA", "RINVIO SCADUTO", "RICONTATTO OOO") and not pr.get("analysis_pdf"):
            return 1                                          # aspetta l'analisi: dietro
        return 0
    candidate.sort(key=pronto)
    candidate = candidate[:QUANTI]

    def esito_coda(p, motivo):
        """La coda si svuota con il motivo scritto nella scheda: si vede perche' non e' partita.
        Fuori coda, lo stesso motivo resta in enriched.lettura_esito: si rilegge solo a una mail nuova."""
        if PROVA:
            return
        fresco = (sb("GET", f"/rest/v1/prospects?select=enriched&id=eq.{p['id']}") or [{}])[0]
        arr = dict(fresco.get("enriched") or {})
        adesso = datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")
        if p.get("coda"):
            arr["coda_esito"] = {"gruppo": p.get("coda"), "motivo": motivo, "il": adesso}
            sb("PATCH", f"/rest/v1/prospects?id=eq.{p['id']}", {"coda": None, "enriched": arr})
        else:
            # FUORI CODA (27/9): il motivo non bastava. Chi viene saltato restava
            # awaiting_us=true, quindi tornava ogni giorno nella lista «da rispondere»
            # di Dre pur avendo gia' un verdetto. Tre caselle di servizio (ticket
            # automatici) occupavano la lista da venerdi'. Se non c'e' nessuno a cui
            # scrivere, l'attesa si chiude: la mail resta nella storia, il motivo nella
            # scheda, e si riapre da sola se quella persona riscrive davvero.
            arr["lettura_esito"] = {"motivo": motivo, "il": adesso}
            patch = {"enriched": arr}
            if any(k in motivo for k in CHIUDONO):
                patch["awaiting_us"] = False
            sb("PATCH", f"/rest/v1/prospects?id=eq.{p['id']}", patch)

    for p, motivo in fuori_coda:
        print(f"  {(p.get('coda') or ''):15} {(p.get('company') or p.get('email') or '')[:34]:34} esce dalla coda: {motivo}")
        esito_coda(p, motivo)

    def lavora(coppia):
        p, gruppo = coppia
        nome = (p.get("company") or p.get("name") or p.get("email") or "")[:34]
        # 1. LA LETTURA: il filo vero e i fatti
        try:
            _, letti = lettura.leggi(p)
        except Exception as e:                                # noqa: BLE001
            return (p, gruppo, nome, None, [f"lettura non riuscita: {str(e)[:80]}"], None, None)
        # 2. LE REGOLE DURE
        dura = lettura.regola_dura(gruppo, letti, p.get("classificazione"))
        if dura and dura[0] == "salta":
            return (p, gruppo, nome, None, [], letti, dura)
        if gruppo in ("RIPRESA", "RINVIO SCADUTO", "RICONTATTO OOO") and not p.get("analysis_pdf"):
            # L'ATTESA NON E' INFINITA (Dre, 28/9: «se è ferma deve avvisarmi in
            # qualche modo»). Istituto Flegreo ha aspettato l'analisi per giorni
            # senza che nessuno lo dicesse: il loro sito rispondeva 500, quindi
            # l'analisi non poteva proprio nascere. Dopo due giorni si smette di
            # aspettare in silenzio e si chiede a una persona, con il motivo vero.
            fermo_da = (datetime.datetime.now(datetime.timezone.utc) - quando(p.get("coda_il") or p.get("last_reply_at") or "")).days if (p.get("coda_il") or p.get("last_reply_at")) else 0
            if fermo_da >= 2:
                return (p, gruppo, nome, None, [], letti, ("chiedi", f"aspetta l'analisi da {fermo_da} giorni e non arriva"))
            return (p, gruppo, nome, None, [], letti, ("aspetta", "l'analisi non c'e' ancora (la fa l'operazione analisi)"))
        if not gruppo and len((letti.get("ultima_loro") or "").strip()) < 30:
            return (p, gruppo, nome, None, [], letti, ("salta", "l'ultima mail loro e' vuota o illeggibile"))
        # 3. LA BOZZA. I follow-up col template li scrive il codice, parola per parola
        # (Dre 29/9, strada A): il modello qui non scrive niente. Se il codice non
        # puo' (template assente, riscrittura richiesta) scrive il motore di sempre.
        giorno = proposta_giorno_ora() if gruppo == "RICONTATTO OOO" else None
        dal_codice = seguiti.testo(gruppo, p, letti, CALENDARIO, giorno=giorno) if gruppo else None
        if dal_codice:
            b = {"intento": gruppo, "template": gruppo, "fermati": "no", "nota": "il template di Dre, parola per parola (scritto dal codice)",
                 "bozza": dal_codice, "dal_codice": True, "giorno": giorno}
        else:
            b = chiedi_bozza(p, letti["ultima_loro"], gruppo=gruppo, letti=letti)
        if not b:
            return (p, gruppo, nome, None, [], letti, None)
        niente_analisi = (not p.get("analysis_pdf")
                          and ((p.get("enriched") or {}).get("google_fit") or {}).get("verdetto") == "NO")
        # IL TESTO DI DRE (29/9: «basta seguire questo tutte le volte possibili»): se per
        # l'intento c'e' un suo template, la bozza e' quello, composto dal codice. Il testo
        # del modello resta accanto (bozza_modello). Se l'analisi non puo' nascere, no:
        # il template la promette.
        if not gruppo and not niente_analisi:
            b = testo_di_dre(b, p, letti)
        errori = cancello(b["bozza"], senza_analisi=niente_analisi)
        if errori and not b.get("dal_codice"):
            b2 = chiedi_bozza(p, letti["ultima_loro"], riprova="; ".join(errori), gruppo=gruppo, letti=letti)
            if b2 and not cancello(b2["bozza"], senza_analisi=niente_analisi):
                b, errori = b2, []
        if dura and dura[0] == "fermati" and b["fermati"].lower().startswith("no"):
            b["fermati"] = "si': " + dura[1]
        # 4. LA SECONDA TESTA
        verdetto, motivo = lettura.coerenza(letti, b["bozza"], gruppo)
        b["lettura"] = {**letti, "letta_da_clara": b.get("lettura_di_clara", ""), "ha_gia_di_clara": b.get("ha_gia_di_clara", ""),
                        "coerenza": verdetto, "coerenza_motivo": motivo, "gruppo": gruppo}
        if verdetto != "COERENTE" and b["fermati"].lower().startswith("no"):
            b["fermati"] = "si': la seconda testa dice INCOERENTE: " + motivo
        return (p, gruppo, nome, b, errori, letti, None)

    fatte, ferme, bocciate, saltate = 0, 0, 0, 0
    ferme_da_dire = []                  # chi aspetta da troppo: una domanda sola alla fine
    with ThreadPoolExecutor(max_workers=IN_PARALLELO) as pool:
        esiti = list(pool.map(lavora, candidate))
    for p, gruppo, nome, b, errori, letti, dura in esiti:
        if dura:
            print(f"  {(gruppo or 'risposta'):15} {nome:34} {dura[0]}: {dura[1]}")
            if dura[0] == "salta":
                saltate += 1
                esito_coda(p, dura[1])
            elif dura[0] == "chiedi":
                # ferma da troppo: si mette da parte e si chiede a Dre. UNA domanda
                # sola per tutte, non una a testa: otto domande insieme sono un muro,
                # e la regola e' una cosa alla volta.
                ferme_da_dire.append((p, nome, dura[1]))
            continue
        if not b:
            print(f"  ? {nome}: {errori[0] if errori else 'risposta del cervello non leggibile'}"); continue
        if errori:
            bocciate += 1
        ferma = not b["fermati"].lower().startswith("no")
        titolo = (f"Da guardare tu: {nome}" if ferma else (f"{gruppo.capitalize()}: {nome}" if gruppo else f"Bozza per {nome}")) + f", {b['intento']}"
        perche = (b["fermati"] if ferma else b["nota"])[:280] + (f", CANCELLO: {'; '.join(errori)}" if errori else "")
        if PROVA:
            print(f"\n  [{b['intento']}] {titolo}\n      LORO ({letti['ultima_loro_il']}): {letti['ultima_loro'][:400]}\n      " +
                  (f"NOI PRIMA ({letti['ultima_nostra_il']}): {letti['ultima_nostra'][:200]}\n      " if letti.get("ultima_nostra") else "") +
                  f"{perche}\n      SECONDA TESTA: {b['lettura']['coerenza']} {b['lettura']['coerenza_motivo']}\n      NOI ORA:\n" + "\n".join("        " + r for r in b["bozza"].splitlines()))
        else:
            print(f"\n  [{b['intento']}] {titolo}\n      LORO ({letti['ultima_loro_il']}): {letti['ultima_loro'][:160]}\n      {perche}\n      NOI: " + b["bozza"][:220].replace("\n", " ") + "…")
        if not PROVA:
            azione = {"bozza": b["bozza"], "intento": b["intento"], "template": b["template"], "lettura": b["lettura"]}
            if b.get("dal_codice"):
                azione["testo_dal_codice"] = True
                if b.get("giorno"):
                    azione["giorno_proposto"] = b["giorno"]
                if b.get("bozza_modello"):
                    azione["bozza_modello"] = b["bozza_modello"]
            if gruppo in ("RIPRESA", "RINVIO SCADUTO", "RICONTATTO OOO", "FOLLOW UP 1"):
                azione["allega_presentazione"] = True
            if gruppo in ("RIPRESA", "RINVIO SCADUTO", "RICONTATTO OOO"):
                azione["allega"] = True
            pid = proponi("umano" if ferma else "risposta", titolo, prospect_id=p["id"], perche=perche, azione=azione)
            if pid and gruppo:
                sb("PATCH", f"/rest/v1/prospects?id=eq.{p['id']}", {"coda": None})
            PRONTE.append((p["id"], (p.get("company") or p.get("name") or "")[:30], bool(p.get("analysis_pdf"))))
        if ferma: ferme += 1
        else: fatte += 1

    # LA DOMANDA UNICA (28/9, Dre: «se è ferma deve avvisarmi in qualche modo»).
    # Prima queste aspettavano in silenzio a ogni giro, per sempre. Il ref del
    # giorno fa si' che la domanda si riscriva una volta sola, non ogni cinque minuti.
    if ferme_da_dire:
        righe_f = "\n".join(f"- {n}: {m}" + (f" ({p.get('website')})" if p.get("website") else "")
                            for p, n, m in ferme_da_dire[:8])
        quante = len(ferme_da_dire)
        titolo_f = (f"{quante} risposte sono ferme: aspettano un'analisi che non arriva"
                    if quante > 1 else f"Ferma da giorni: {ferme_da_dire[0][1]}")
        if not PROVA:
            proponi("umano", titolo_f,
                    perche=(f"Aspettano da due giorni o piu'. Apri il loro sito: se non risponde, l'analisi non puo' nascere. "
                            f"Puoi mandarle senza l'analisi o lasciarle.\n{righe_f}")[:280],
                    azione={"ferme": [{"id": p.get("id"), "nome": n, "motivo": m, "sito": p.get("website")} for p, n, m in ferme_da_dire]},
                    ref=f"ferme:{datetime.date.today().isoformat()}")
        print(f"  {quante} ferme da troppo: l'ho chiesto a Dre in Posta")
    print(f"\n  bozze pronte {fatte}, da guardare tu {ferme}, non passate il cancello {bocciate}, saltate con motivo {saltate}")

    # ── il gigante buono: i negativi cortesi, una volta sola ────────
    negativi = sb("GET", "/rest/v1/prospects?classificazione=eq.negativo&fuori=eq.false&analysis_sent=eq.false"
                         "&select=id,name,company,email,classificazione,stage,analysis_sent,analysis_pdf,last_reply_at,sector,city,enriched,no_followup,awaiting_us"
                         "&order=last_reply_at.desc&limit=200") or []
    soppresse = sb_tutte("/rest/v1/suppressions?select=email,domain&limit=5000") or []
    mail_no = {(x.get("email") or "").lower() for x in soppresse}
    dom_no = {(x.get("domain") or "").lower() for x in soppresse if x.get("domain")}
    gb = 0
    # a chi Dre ha gia' detto no, non si riscrive: la proposta rifiutata vale
    # come risposta (prima tornava ogni giro, QA del 14/9)
    rifiutate = {x["prospect_id"] for x in (sb_tutte("/rest/v1/proposte?select=prospect_id&stato=eq.no&tipo=eq.risposta&azione->>intento=eq.INT-GB&limit=5000") or [])
                 if x.get("prospect_id")}
    def mai_gb(p, motivo):
        """Il gigante buono non arrivera' mai: se aspettava, l'attesa si chiude (29/9)."""
        if p.get("awaiting_us"):
            chiudi_attesa(p, f"ha detto no, niente gigante buono: {motivo}")

    for p in negativi:
        if p["id"] in rifiutate:
            mai_gb(p, "l'hai gia' scartato tu"); continue
        if gb >= QUANTI_GB or p["id"] in aperte or p.get("stage") in INTOCCABILI:
            continue
        mail = (p.get("email") or "").lower()
        if mail in mail_no or mail.split("@")[-1] in dom_no:
            mai_gb(p, "e' nella lista di chi non va contattato"); continue
        # anche il gigante buono legge (25/9): il suo no vero, dal filo
        try:
            _, letti = lettura.leggi(p)
        except Exception as e:                                # noqa: BLE001
            print(f"  [GB] salto {nome if False else (p.get('company') or mail)[:34]}: lettura non riuscita ({str(e)[:60]})"); continue
        testo = letti["ultima_loro"]
        # 28/9: NON_TOCCARE sulle sue righe soltanto (il caso dell'immobiliare del 28/9: «cancellarlo»
        # stava nella nostra firma GDPR citata sotto la sua risposta positiva)
        if len(testo.strip()) < 20 or NON_TOCCARE.search(lettura.solo_suo(testo)):
            mai_gb(p, "ha chiesto di non essere contattato o non ha scritto niente"); continue
        if letti["scritto_dopo_di_lei"]:
            mai_gb(p, "gli abbiamo gia' scritto dopo il suo no"); continue
        fit = (p.get("enriched") or {}).get("google_fit") or {}
        if fit.get("verdetto") == "NO" or not (fit.get("zona") or p.get("analysis_pdf")):
            mai_gb(p, "non c'e' un'analisi vera da lasciargli"); continue   # senza PDF o zona misurata non c'e' niente da lasciare
        ultimo_no = (p.get("last_reply_at") or "")[:10]
        if ultimo_no and (datetime.date.today() - datetime.date.fromisoformat(ultimo_no)).days > GIORNI_GB:
            mai_gb(p, f"il suo no ha piu' di {GIORNI_GB} giorni"); continue
        nome = (p.get("company") or p.get("name") or mail)[:34]
        fatti = {"nome": p.get("name") or "", "azienda": p.get("company") or "", "settore": p.get("sector"), "citta": p.get("city"),
                 "google_fit": {"provincia": fit.get("provincia"), "zona": fit.get("zona"), "cosa_fa": fit.get("cosa_fa")} if fit else None}
        prompt = (cervello.ruolo("preparatore") + cervello.manuale("testa") + "\n\n" + ISTRUZIONE_GB + cervello.istruzione("chat") + cervello.istruzione("bozze") + f"\n\nVALORI: {{{{CALENDARIO}}}} = {CALENDARIO}"
                  f"\n\nLA SCHEDA:\n{fatti}\n\nIL SUO NO:\n{testo[:1500]}")
        try:
            grezzo = cervello._chiedi(prompt) or ""
        except Exception as e:                      # noqa: BLE001
            print(f"  [GB] salto {nome}: il cervello non risponde ({str(e)[:80]})")
            continue
        m = re.search(r"\n\s*-{3,}\s*\n", grezzo)
        if not m:
            continue
        testa, bozza = grezzo[:m.start()], grezzo[m.end():].strip().strip("`").strip()
        fermati = next((r.split(":", 1)[1].strip() for r in testa.splitlines() if r.upper().startswith("FERMATI")), "no")
        nota = next((r.split(":", 1)[1].strip() for r in testa.splitlines() if r.upper().startswith("NOTA")), "")
        errori = cancello(bozza)
        if errori or not fermati.lower().startswith("no"):
            print(f"  [GB] salto {nome}: {fermati if not fermati.lower().startswith('no') else '; '.join(errori)}")
            continue
        # la seconda testa, anche per lui
        verdetto, motivo = lettura.coerenza(letti, bozza, "GIGANTE BUONO")
        if verdetto != "COERENTE":
            print(f"  [GB] salto {nome}: la seconda testa dice {motivo}"); continue
        lett = {**letti, "coerenza": verdetto, "coerenza_motivo": motivo, "gruppo": "GIGANTE BUONO"}
        print(f"\n  [GB] Gigante buono per {nome}\n      " + bozza[:200].replace("\n", " ") + "…")
        if not PROVA:
            PRONTE.append((p["id"], nome, True))
            proponi("risposta", f"Gigante buono per {nome}, INT-GB", prospect_id=p["id"],
                    perche=("Ci ha detto no con garbo: gli lasciamo l'analisi lo stesso, una volta sola. Allega il PDF dell'analisi. " + nota)[:280],
                    azione={"bozza": bozza, "intento": "INT-GB", "template": "INT-GB", "lettura": lett})
        gb += 1
    print(f"  giganti buoni pronti: {gb}")
    # il telefono di Dre: una riga, solo se c'e' qualcosa da approvare
    if not PROVA and (fatte or ferme):
        # LA BOZZA PRONTA ARRIVA SUL TELEFONO (Dre, 24/9): una notifica che dice chi,
        # se c'e' l'analisi, e apre la scheda giusta: leggi, Approva e manda.
        from avvisa import avvisa
        import os as _os
        base = _os.environ.get("DASHBOARD_URL", "./")
        if len(PRONTE) == 1:
            pid, nome, con_pdf = PRONTE[0]
            con = ", con l'analisi" if con_pdf else ""
            avvisa(f"Bozza pronta per {nome}{con}: apri, leggi, Approva e manda.",
                   titolo="Clara", url=f"{base}?scheda={pid}")
        else:
            nomi = ", ".join(n for _, n, _ in PRONTE[:3]) + ("…" if len(PRONTE) > 3 else "")
            pezzi = ([f"{fatte} bozze pronte ({nomi})"] if fatte else []) + ([f"{ferme} da guardare tu"] if ferme else [])
            avvisa(", ".join(pezzi) + ". Apri la Posta e approva.", titolo="Clara", url=base)


if __name__ == "__main__":
    main()
