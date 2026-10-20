#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""IL SEGNALE PROVVISORIO — una mail a Dre quando un lead e' caldo o un si' resta li' (14/10/2026).

PERCHE'
Dre, 14/10: «mi dai un modo piccolo per gestirmi questi che arrivano nel frattempo,
mentre continui a costruire quello serio». Il 13 e 14/10 alcuni si' sono rimasti
senza risposta e chi aveva lasciato il numero non e' arrivato a lui. Finche' il
sistema nuovo non c'e', questo guarda le risposte e gli scrive. E' PROVVISORIO:
piccolo, separato, si butta (file, riga in `operazioni`, tabella segnali_provvisori)
quando arriva il nuovo. Non tocca niente del sistema vecchio: legge e basta.

COSA FA, a ogni giro (il direttore, ordine 4: dopo sync, prima risposta, bozze e manda;
il direttore lo fa partire il database ogni 5 minuti, il sync passa ogni 5-10: «subito»
vuol dire 5-10 minuti dalla risposta)
1. Le risposte dei lead delle ultime 24 ore (interactions email_in) non ancora segnalate:
   TUTTE, non solo l'ultima (due risposte tra un giro e l'altro: si leggono tutte e due).
2. Salta: clienti, pipeline, persi, soppressi, nervosi (stanza.contattabile, la regola
   unica), e le autorisposte ovvie (la regex collaudata di lettura.py, piu' rimbalzi e
   accettazioni del calendario) quando non c'e' un numero di telefono nel testo.
3. Una lettura AI breve per risposta (cervello: la porta OpenAI, gpt-5, sforzo basso;
   la memoria delle letture nel database: la stessa risposta non si ripaga mai).
   Dice: e' CALDO? e' un SI'? la frase chiave, il telefono, un consiglio se serve.
   Al massimo 10 letture pagate per giro (le altre al giro dopo) e 150 al giorno (oltre:
   «da guardare» senza pagare). Prima di pagare si prova a scrivere la memoria: se non si
   scrive non si paga (si ripagherebbe a ogni giro), la risposta arriva «da guardare» e avvisa.
   Di piu' risposte nuove della stessa azienda vince la piu' forte: caldo, da guardare, si'.
4. Una MAIL A DRE, solo a lui (il controllo e' in manda_mail: qualunque altro
   destinatario fa un'eccezione prima di toccare Gmail):
     CALDO       subito                      «Vuole sentirti: <azienda>»
     SI'         dopo 10 minuti, se non c'e' una nostra risposta ne' una bozza approvata
                                             «Sì da servire: <azienda>»
     DA GUARDARE l'AI non ha risposto: si segnala lo stesso, mai silenzio
   Una volta sola per lead e per tipo (segnali_provvisori: unica per risposta, e per
   azienda e tipo): un lead gia' segnalato come si' che poi chiede di essere chiamato
   arriva di nuovo come caldo; due caldi dello stesso lead fanno una mail sola.
   Piu' di 3 nello stesso giro: una mail sola con l'elenco.

5. LE PRENOTAZIONI DELLE CALL (14/10, schema_v89). Dre vedeva chi prenotava la conoscitiva solo
   per caso in Gmail. A ogni giro si guarda il suo calendario (e, come rete, le mail «Appuntamento
   prenotato» / «annullato» con l'invito .ics dentro: la chiave e' l'id dell'evento, uguale dalle due
   parti, quindi una prenotazione suona una volta sola anche se la si vede due volte):
     PRENOTATO   una call nuova con qualcuno di fuori     «Prenotato: <azienda>, <giorno> alle <ora>»
                 con la SCHEDA: chi e' (nome e ruolo dalla firma), i telefoni dal piu' diretto
                 (cellulare della firma, fisso della firma, la scheda, il centralino del sito), cosa
                 fa, l'ultima cosa che ci ha scritto, l'analisi mandata col punto chiave, «Appunti:».
                 Se non si abbina a nessun lead parte lo stesso, con quello che dice la prenotazione.
     MATTINA     il giorno della call dalle 8:30 di Roma  «Oggi alle <ora>: <azienda>», la stessa scheda
     SPOSTATA    un orario nuovo (anche preso dalla pagina)  una riga
     CANCELLATA  annullata, o l'invito rifiutato         una riga
   Il lead si trova dall'agenda (il calendario ce l'ha gia' attaccato) o con calendario.riconosci.
   Il registro e' prenotazioni_segnalate (chiave unica). Solo lettura su calendario e posta.

6. IL TELEFONO (20/10): suona solo per il lead entrato in conversazione (conversazioni.py, chiamato
   da questo giro). Le mail qui sopra restano, senza notifica; le notifiche di guasto (avvisa_ogni) si'.

COSA NON FA
Mai una mail ai lead. Niente scritto sul calendario, niente su Smartlead. Mai un riprovo pagato: una lettura fallita si scrive in memoria
come fallita e diventa «da guardare», non si rilegge al giro dopo. Se Google dice di no
(un errore col codice), il segnale non si segna e riparte al giro dopo, gratis. Se invece
la risposta di Gmail si perde (rete, timeout) la mail potrebbe essere partita: il segnale
resta «incerto» e al giro dopo si cerca nella posta inviata di Dre prima di rimandarlo.
Se Gmail resta ferma, la notifica sul telefono arriva al massimo ogni 2 ore.

USO
  python3 scripts/segnale_provvisorio.py                  il giro vero
  python3 scripts/segnale_provvisorio.py --prova          stampa cosa manderebbe, non manda e non segna
  python3 scripts/segnale_provvisorio.py --prova --ore 48 la prova sulle ultime 48 ore, com'e' adesso
  python3 scripts/segnale_provvisorio.py --prova --storico --ore 48
                                   come sarebbe andata: un si' servito tardi (oltre 10 minuti
                                   + il giro del direttore) conta come segnalato
  python3 scripts/segnale_provvisorio.py --prova-mail --ore 48
                                   UNA mail a Dre con l'elenco, oggetto «Prova del segnale
                                   provvisorio», e i segnalati si segnano (non tornano doppi).
                                   Manda davvero: insieme a --prova (o PROVA=1) si rifiuta.
  python3 scripts/segnale_provvisorio.py --prova --solo-prenotazioni
                                   solo le prenotazioni, com'e' adesso
  python3 scripts/segnale_provvisorio.py --prova --alle 2026-10-15T08:31
                                   le prenotazioni come le vedrebbe il giro a quell'ora di Roma
  python3 scripts/segnale_provvisorio.py --semina [--tranne <testo>]
                                   la prima accensione: le prenotazioni gia' in calendario si segnano
                                   come note, senza mail (tranne quelle col testo nel titolo o nella mail)
"""

import base64
import datetime
import hashlib
import html
import json
import os
import re
import sys
import urllib.parse
import zoneinfo
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.header import Header

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from stanza import sb, contattabile, quando, _a_secco, env      # noqa: E402
from lettura import AUTORISPOSTA, solo_suo                       # noqa: E402

DRE = "dramane@studiogalilei.com"           # mittente e UNICO destinatario, sempre
MASTER_INBOX = "https://app.smartlead.ai/app/master-inbox"
MODELLO = "gpt-5"
SFORZO = "low"
TETTO = 2500                                # token d'uscita (ragionamento compreso) per lettura
ATTESA_SI = datetime.timedelta(minutes=10)
OROLOGIO = datetime.timedelta(minutes=10)   # il direttore parte ogni 5 minuti (cron del database), il sync ogni 5-10
PAGATE_PER_GIRO = 10                        # letture pagate al massimo in un giro: le altre al giro dopo
PAGATE_AL_GIORNO = 150                      # e in 24 ore (uso_modelli): oltre, «da guardare» senza pagare
AVVISO_OGNI = datetime.timedelta(hours=2)   # la stessa notifica di guasto non piu' spesso di cosi'
FINESTRA_ORE = 24
TANTI = 3                                   # oltre questo, una mail sola con l'elenco
PREZZO = {"gpt-5": (1.25, 10.0)}            # dollari per milione di token (dentro, fuori): banco_modelli.py
VERSIONE = "segnale2"                       # cambia la domanda -> cambia la chiave della memoria
ROMA = zoneinfo.ZoneInfo("Europe/Rome")

ORDINE_TIPO = {"caldo": 0, "da_guardare": 1, "si": 2}
OGGETTO = {"caldo": "Vuole sentirti", "si": "Sì da servire", "da_guardare": "Da guardare"}

# le autorisposte che nessuno deve leggere: quella collaudata di lettura.py, piu' rimbalzi,
# indirizzi dismessi e accettazioni del calendario (viste il 13/10); 17/10: i rimbalzi in inglese
# («Message blocked», «couldn't be delivered») e i rapporti DMARC finivano fra le risposte dei lead
AUTOMATICHE = re.compile(r"^\s*(accettato|accepted|rifiutato|declined)\s*:|recapito non (e'|è) riuscito|undeliverable|"
                         r"delivery status notification|mail delivery (failed|subsystem)|mancata consegna|"
                         r"^\s*message blocked\b|your message to \S+ (has been blocked|couldn.?t be delivered)|"
                         r"could not be delivered to|dmarc aggregate report|"
                         r"indirizzo[^.\n]{0,60}(dismess|disattivat)|verr[àa] (dismess|disattivat)", re.I | re.M)
TELEFONO = re.compile(r"(?<![\w\d])(?:\+|00)?(?:39[\s.\-]?)?(?:3\d{2}|0\d{1,3})(?:[\s.\-/]?\d){6,8}(?![\d])")
# un numero dopo queste parole non e' un telefono: partita IVA, codice fiscale, IBAN, REA
NON_TELEFONO = re.compile(r"(p\.?\s*i\.?\s*v\.?\s*a\.?|partita\s+iva|\bc\.?\s*f\.?|codice\s+fiscale|cod\.?\s*fisc\w*\.?|"
                          r"\bvat\b|\biban\b|\brea\b)[\s.:#°/-]*(?:n[°r.]?\s*)?(?:it\s*)?$", re.I)

DOMANDA = """Sei l'occhio di Dre, il titolare di Studio Galilei (agenzia di Treviso: marketing e Google Ads).
Lorenzo ha scritto a freddo a questa azienda offrendo un'analisi gratuita del loro marketing online e
chiedendo solo di confermare l'indirizzo mail per mandarla. Qui sotto la risposta della persona: puo'
contenere la sua firma e qualche pezzo della nostra mail (per esempio un oggetto come «aspetto solo
conferma mail» o «Ultima mail da parte mia» in cima): giudica solo quello che scrive LEI.

Rispondi con questi campi:
- autorisposta: true se non l'ha scritta una persona (fuori ufficio, ticket, presa in carico,
  mancata consegna, accettazione di un invito del calendario).
- caldo: true SOLO se vuole sentirsi adesso: chiede di essere chiamata o di parlarne, propone un giorno
  o un orario vicino, lascia un numero perche' la si chiami; oppure chiede di spostare una call gia'
  fissata, o non riesce a prenotare (il link del calendario non funziona). Un semplice «si', mandi pure
  l'analisi» o «si' grazie molto volentieri» NON e' caldo. Un numero che sta solo nella firma non basta.
  NON e' caldo chi rimanda a fra qualche mese («sentiamoci a settembre»), ne' chi conferma o ha gia'
  fissato da sola una call («fissato per venerdi' alle 15»): e' gia' a posto.
- si: true se vuole o accetta l'analisi o il materiale, anche solo con «confermo la mail», «la mail
  e' corretta», «mandi pure», «va bene», «valutiamo», «si' grazie», «se vuole inoltrarla».
  true anche se chiede cos'e', che tipo di analisi, o chi siamo («non ho capito cos'e'», «che analisi
  nello specifico?»): Dre a chi chiede risponde mandando l'analisi e spiegandola (note di Dre, 17/10).
  false se dice no, rimanda a piu' avanti o chiede di non scrivere.
- frase: la sua frase chiave, copiata dal testo, al massimo 15 parole.
- telefono: UN solo numero di telefono suo o dell'azienda (il cellulare, se c'e') se compare nel testo
  o nella firma, copiato com'e'; altrimenti stringa vuota. Mai inventarlo.
- consiglio: una riga per Dre SOLO se serve qualcosa di non ovvio (es. «propone mercoledi' mattina:
  chiamalo prima delle 10», «ci rimanda a un altro indirizzo: scrivi li'»); altrimenti stringa vuota.

Il messaggio e la firma ti arrivano gia' separati (17/10, Dre: leggere la firma come messaggio fa
capire il contrario). «caldo», «si» e «frase» si decidono SOLO sul MESSAGGIO. La FIRMA dice chi
scrive, il suo ruolo e i suoi numeri: un nome, un ruolo o un cellulare nella firma sono di CHI
SCRIVE, non di qualcuno a cui ci rimanda, e da soli non rendono caldo nessuno. Il telefono puoi
prenderlo dalla firma.

L'AZIENDA: {azienda}
IL MESSAGGIO:
«{messaggio}»
LA SUA FIRMA (non fa parte del messaggio):
«{firma}»"""

SCHEMA = {"type": "json_schema", "json_schema": {"name": "segnale", "strict": True, "schema": {
    "type": "object", "additionalProperties": False,
    "required": ["autorisposta", "caldo", "si", "frase", "telefono", "consiglio"],
    "properties": {"autorisposta": {"type": "boolean"}, "caldo": {"type": "boolean"}, "si": {"type": "boolean"},
                   "frase": {"type": "string"}, "telefono": {"type": "string"}, "consiglio": {"type": "string"}}}}}

SPESA = {"in": 0, "out": 0, "chiamate": 0, "dalla_memoria": 0}
# lo stato del giro: quante letture pagate, la memoria rotta, il tetto del giorno (None = da leggere)
GIRO = {"pagate": 0, "memoria_rotta": False, "sonda": False, "giorno_restano": None, "tetto_giorno": False}
RIMANDATA = "rimandata"                     # leggi(): non letta in questo giro (il tetto del giro)


class NonPartita(ValueError):
    """La mail non e' uscita di qui: destinatario sbagliato o mail che non si compone."""


def adesso():
    return datetime.datetime.now(datetime.timezone.utc)


def _z(t):
    return t.astimezone(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


# ── la mail: a Dre e basta ─────────────────────────────────────────

def manda_mail(a, oggetto, testo, html_corpo):
    """L'UNICA strada verso Gmail. Il destinatario puo' essere solo Dre: qualunque altro
    indirizzo (un lead, un collega, una lista) si ferma qui, prima di chiamare Google."""
    if (a or "").strip().lower() != DRE:
        raise NonPartita(f"il segnale provvisorio scrive solo a Dre, non a {a!r}")
    try:
        m = MIMEMultipart("alternative")
        m["To"] = DRE
        m["From"] = DRE
        m["Subject"] = str(Header(" ".join((oggetto or "").split()), "utf-8"))
        m.attach(MIMEText(testo, "plain", "utf-8"))
        m.attach(MIMEText(html_corpo, "html", "utf-8"))
        grezzo = base64.urlsafe_b64encode(m.as_bytes()).decode()
    except Exception as e:                                       # noqa: BLE001
        raise NonPartita(f"la mail non si compone: {str(e)[:120]}") from e
    return _gmail_send(grezzo)


def _gmail_send(grezzo):
    from google_api import g
    return g("POST", "https://gmail.googleapis.com/gmail/v1/users/me/messages/send", {"raw": grezzo}, email=DRE)


def non_partita(e):
    """Siamo SICURI che la mail non e' partita? Si' se non e' uscita di qui, o se Google ha
    risposto con un codice (o non ha dato il token). Un errore di rete o un timeout no:
    Gmail puo' averla consegnata e perso la risposta."""
    if isinstance(e, NonPartita):
        return True
    s = str(e)
    return isinstance(e, RuntimeError) and (s.startswith("Google ") or "google_token" in s or "GOOGLE_OAUTH" in s)


def _gmail_inviata(oggetto, dal):
    """C'e' nella posta inviata di Dre una mail con questo oggetto, partita dopo `dal`?
    (Solo lettura: gmail.readonly.) Un errore sale: chi chiama decide."""
    from google_api import g
    pulito = " ".join((oggetto or "").replace('"', " ").split())
    q = f'in:sent subject:"{pulito}" after:{int(dal.timestamp()) - 120}'
    base = "https://gmail.googleapis.com/gmail/v1/users/me/messages"
    for m in (g("GET", f"{base}?q={urllib.parse.quote(q)}&maxResults=5", email=DRE) or {}).get("messages") or []:
        d = g("GET", f"{base}/{m['id']}?format=metadata&metadataHeaders=Subject", email=DRE) or {}
        for h in (d.get("payload") or {}).get("headers") or []:
            if h.get("name", "").lower() == "subject" and " ".join(h.get("value", "").split()) == pulito:
                return True
    return False


def _avvisa(testo):
    """Dal 20/10 il segnale non suona da solo: il guasto e' gia' scritto (_registra_guasto) e lo
    suonano gli avvisi di guasto (guasti.py), con le stesse regole di tutti gli altri."""
    print(f"  guasto del segnale (lo suona guasti.py): {testo[:160]}")
    return 0


GUASTI_SEGNALE = "guasti_segnale"


def _registra_guasto(motivo, testo):
    """Il guasto visto in questo giro, in snella_numeri («guasti_segnale»: {motivo: {testo, il, dal}}):
    lo legge il semaforo della scheda Clara (clara_foglio). Finche' il segnale lo rivede resta
    rosso; se per 20 minuti non lo rivede, e' risolto. Non alza mai."""
    try:
        r = sb("GET", f"/rest/v1/snella_numeri?select=dati&chiave=eq.{GUASTI_SEGNALE}") or []
        dati = (r[0].get("dati") if r and isinstance(r[0], dict) else None) or {}
        if not isinstance(dati, dict):
            dati = {}
        prima = dati.get(motivo) if isinstance(dati.get(motivo), dict) else {}
        ora = adesso()
        dal = prima.get("dal") if prima.get("il") and ora - quando(prima["il"]) < datetime.timedelta(minutes=20) else None
        dati[motivo] = {"testo": testo[:300], "il": _z(ora), "dal": dal or _z(ora)}
        sb("POST", "/rest/v1/snella_numeri?on_conflict=chiave",
           [{"chiave": GUASTI_SEGNALE, "dati": dati, "aggiornato_il": _z(ora)}],
           {"Prefer": "resolution=merge-duplicates,return=minimal"})
    except Exception:                                            # noqa: BLE001
        pass


# ── la notifica sul telefono (17/10, ristretta il 20/10) ───────────
# Dre, 20/10: sul telefono suona UNA cosa sola, il lead entrato in conversazione (conversazioni.py,
# che usa notifica() qui sotto). Le mail del segnale e delle prenotazioni restano, senza notifica.
# notifica() non alza mai: al tocco apre la scheda del lead nella versione snella.
_IO = {}


def _dre_id():
    if "id" not in _IO:
        from avvisa import utente
        _IO["id"] = utente(DRE)
    return _IO["id"]


def _push(titolo, testo, url, tag):
    """La strada vera verso il telefono di Dre (solo lui: le mail del segnale sono sue)."""
    from avvisa import avvisa
    chi = _dre_id()
    return avvisa(testo, titolo=titolo, url=url, a=[chi], tag=tag) if chi else 0


def link_snella(pid=None):
    """Dove porta il tocco: la scheda del lead nella versione snella, o Oggi."""
    base = (env("DASHBOARD_URL") or "https://studiogalilei.github.io/clara/").split("#")[0]
    return base + (f"#/s/lead/{urllib.parse.quote(str(pid))}" if pid else "#/s/oggi")


def notifica(titolo, testo, pid=None):
    """Una notifica a Dre. Non alza MAI: il giro va avanti. Torna a quanti dispositivi e' arrivata."""
    try:
        n = _push(" ".join(titolo.split())[:60], " ".join((testo or "").split())[:178], link_snella(pid),
                  f"lead:{pid}" if pid else "oggi")
        print(f"  notifica sul telefono: {titolo} ({n} dispositivi)")
        return n
    except Exception as e:                                       # noqa: BLE001
        print(f"  (notifica non partita: {str(e)[:120]})")
        return 0


def avvisa_ogni(motivo, testo):
    """La notifica di un guasto, non piu' di una ogni 2 ore per lo stesso motivo (Gmail ferma
    non deve suonare a ogni giro). Se la memoria non risponde si avvisa lo stesso."""
    _registra_guasto(motivo, testo)
    chiave = "segnale:avviso:" + motivo
    try:
        r = sb("GET", f"/rest/v1/memoria_letture?select=valore&chiave=eq.{chiave}") or []
        il = (r[0].get("valore") or {}).get("il") if r and isinstance(r[0].get("valore"), dict) else None
        if il and adesso() - quando(il) < AVVISO_OGNI:
            return False
        sb("POST", "/rest/v1/memoria_letture?on_conflict=chiave", [{"chiave": chiave, "valore": {"il": _z(adesso())}}],
           {"Prefer": "resolution=merge-duplicates,return=minimal"})
    except Exception:                                            # noqa: BLE001
        pass
    try:
        _avvisa(testo)
    except Exception:                                            # noqa: BLE001
        pass
    return True


# ── la lettura AI, con memoria e contatore ─────────────────────────

def _chiave(azienda, testo):
    base = "\x00".join((VERSIONE, MODELLO, DOMANDA, azienda or "", " ".join((testo or "").split())))
    return "segnale:" + hashlib.sha256(base.encode("utf-8")).hexdigest()[:24]


# 14/10 (critico): le prove del collaudo avevano mangiato 143 delle 150 letture del giorno, e il
# giorno dopo i caldi sarebbero arrivati come «da guardare». Il tetto conta solo i giri veri,
# quelli del direttore in cloud; le prove si contano a parte (i soldi restano registrati).
SCOPO = "segnale provvisorio"


def _vero():
    return os.environ.get("GITHUB_ACTIONS") == "true" and not _a_secco()


def _conta(modello, dentro, fuori):
    """Il contatore della spesa (uso_modelli), anche in prova: i soldi spesi sono veri."""
    SPESA["in"] += int(dentro or 0)
    SPESA["out"] += int(fuori or 0)
    SPESA["chiamate"] += 1
    try:
        sb("POST", "/rest/v1/uso_modelli", {"script": "segnale_provvisorio.py", "scopo": SCOPO if _vero() else SCOPO + " (prova)",
                                            "modello": modello, "token_in": int(dentro or 0), "token_out": int(fuori or 0)},
           {"Prefer": "return=minimal"})
    except Exception:                                            # noqa: BLE001
        pass


def _chiedi_ai(prompt, formato=None):
    """La porta OpenAI di sempre (cervello._chiedi_openai), col contatore di questo script."""
    import cervello
    vero = cervello._conta_uso
    cervello._conta_uso = _conta
    try:
        return cervello._chiedi_openai(prompt, MODELLO, formato=formato or SCHEMA, fornitore="openai", tetto=TETTO, sforzo=SFORZO)
    finally:
        cervello._conta_uso = vero


def _cifre(t):
    return re.sub(r"\D", "", t or "")


def _non_telefono(testo, m):
    """Un numero che sembra un telefono ma non lo e': dopo «P.IVA», «C.F.», «IBAN»..., oppure
    11 cifre attaccate che iniziano con 0 (la forma della partita IVA)."""
    if NON_TELEFONO.search((testo or "")[max(0, m.start() - 30):m.start()]):
        return True
    grezzo = m.group(0).strip()
    return grezzo.isdigit() and len(grezzo) == 11 and grezzo.startswith("0")


def telefono_nel_testo(testo):
    """Il primo numero di telefono plausibile nel testo (rete per quando l'AI non c'e')."""
    for m in TELEFONO.finditer(testo or ""):
        c = _cifre(m.group(0))
        if 9 <= len(c) <= 13 and not _non_telefono(testo, m):
            return m.group(0).strip()
    return ""


def _numeri_esclusi(testo):
    return {_cifre(m.group(0)) for m in TELEFONO.finditer(testo or "") if _non_telefono(testo, m)}


def _restano_oggi():
    """Quante letture si possono ancora pagare nelle ultime 24 ore (uso_modelli). Se il
    contatore non si legge, zero: senza sapere quanto si e' speso non si spende."""
    if GIRO["giorno_restano"] is None:
        try:
            da = _z(adesso() - datetime.timedelta(hours=24))
            fatte = sb("GET", f"/rest/v1/uso_modelli?select=id&script=eq.segnale_provvisorio.py&scopo=eq.{urllib.parse.quote(SCOPO)}&il=gte.{da}"
                              f"&limit={PAGATE_AL_GIORNO + 1}") or []
            GIRO["giorno_restano"] = max(0, PAGATE_AL_GIORNO - len(fatte))
        except Exception:                                        # noqa: BLE001
            GIRO["giorno_restano"] = 0
    return GIRO["giorno_restano"]


def _ricorda(chiave, v):
    """La memoria si scrive anche in prova: e' una lettura gia' pagata, non un gesto.
    Se non si scrive, il giro smette di pagare: la prossima volta la si ripagherebbe."""
    try:
        sb("POST", "/rest/v1/memoria_letture?on_conflict=chiave", [{"chiave": chiave, "valore": v}],
           {"Prefer": "resolution=merge-duplicates,return=minimal"})
        return True
    except Exception as e:                                       # noqa: BLE001
        GIRO["memoria_rotta"] = True
        print(f"  (la memoria delle letture non si scrive: smetto di pagare in questo giro. {str(e)[:100]})")
        return False


def leggi(azienda, testo):
    """Una lettura per risposta, una volta sola nella vita. Torna la lettura, oppure
    {"fallita": True} («da guardare»: l'AI non ha risposto, il tetto del giorno, o la memoria
    che non funziona: senza memoria non si paga, la si ripagherebbe a ogni giro), oppure
    RIMANDATA (il tetto del giro: al giro dopo)."""
    chiave = _chiave(azienda, testo)
    senza_memoria = {"fallita": True, "senza_memoria": True}
    if GIRO["memoria_rotta"]:
        return senza_memoria
    try:
        r = sb("GET", f"/rest/v1/memoria_letture?select=valore&chiave=eq.{chiave}") or []
    except Exception:                                            # noqa: BLE001
        GIRO["memoria_rotta"] = True
        return senza_memoria
    if r and isinstance(r[0].get("valore"), dict):
        SPESA["dalla_memoria"] += 1
        return r[0]["valore"]
    if GIRO["pagate"] >= PAGATE_PER_GIRO:
        return RIMANDATA
    if not GIRO["sonda"]:                    # prima di pagare: la memoria si scrive? se no, non si paga
        if not _ricorda("segnale:sonda", {"il": _z(adesso())}):
            return senza_memoria
        GIRO["sonda"] = True
    if _restano_oggi() <= 0:
        GIRO["tetto_giorno"] = True
        return {"fallita": True, "tetto": True}                 # non si memorizza: domani si potra' leggere
    GIRO["pagate"] += 1
    GIRO["giorno_restano"] -= 1
    v = None
    try:
        from lettura import dividi
        messaggio, firma = dividi(testo or "")
        grezzo = _chiedi_ai(DOMANDA.format(azienda=azienda or "?", messaggio=(messaggio or testo or "")[:2500],
                                           firma=(firma or "(nessuna)")[:800]))
        m = re.search(r"\{.*\}", grezzo or "", re.S)
        v = json.loads(m.group(0)) if m else None
    except Exception as e:                                       # noqa: BLE001
        print(f"  (l'AI non ha risposto: {str(e)[:100]})")
    if not isinstance(v, dict) or not all(isinstance(v.get(k), bool) for k in ("autorisposta", "caldo", "si")):
        v = {"fallita": True}                # si ricorda anche questa: una lettura fallita non si ripaga
        _ricorda(chiave, v)
        return v
    # il telefono deve stare davvero nel testo: un numero inventato e' peggio di nessun numero
    tel = (v.get("telefono") or "").strip()
    primo = TELEFONO.search(tel)              # «Tel. 0422 918652 - Tel. 0422 1847161»: il primo e basta
    tel = primo.group(0).strip() if primo else tel
    c = _cifre(tel)
    if tel and (len(c) < 8 or c[-8:] not in _cifre(testo) or c in _numeri_esclusi(testo)
                or (tel.isdigit() and len(tel) == 11 and tel.startswith("0"))):
        tel = ""
    v["telefono"] = tel
    _ricorda(chiave, v)
    return v


# ── chi e' gia' stato servito ──────────────────────────────────────

def primo_servizio(pid, dal):
    """Quando l'abbiamo servito dopo la sua risposta: la prima nostra mail, o la bozza partita
    (risposta_il), o una bozza approvata o in invio (servita adesso). None = nessuno l'ha servito."""
    d = _z(dal)
    tempi = [quando(r["at"]) for r in sb("GET", f"/rest/v1/interactions?select=at&prospect_id=eq.{pid}&kind=eq.email_out"
                                                f"&at=gt.{d}&order=at.asc&limit=1") or [] if r.get("at")]
    for x in sb("GET", f"/rest/v1/proposte?select=stato,risposta_il&prospect_id=eq.{pid}&tipo=in.(risposta,umano)"
                       f"&stato=in.(approvata,in_invio,fatta)&at=gte.{d}") or []:
        tempi.append(quando(x["risposta_il"]) if x.get("stato") == "fatta" and x.get("risposta_il") else adesso())
    return min(tempi) if tempi else None


def automatica(testo):
    """Un'autorisposta ovvia, che non vale una lettura. Mai se c'e' un numero nel testo:
    «sono fuori, rientro il 20, mi chiami al 333...» e' una persona, la legge l'AI."""
    t = (testo or "")[:1500]
    return bool(AUTORISPOSTA.search(t) or AUTOMATICHE.search(t)) and not telefono_nel_testo(solo_suo(testo, con_firma=True))


# ── il giro ────────────────────────────────────────────────────────

def candidati(ore):
    """Le risposte della finestra non ancora segnalate, raggruppate per azienda, con la scheda
    e i tipi gia' segnalati a quell'azienda. Prima le aziende con la risposta piu' recente."""
    da = _z(adesso() - datetime.timedelta(hours=ore))
    righe = sb("GET", f"/rest/v1/interactions?select=id,prospect_id,at,created_at,body&kind=eq.email_in"
                      f"&at=gte.{da}&prospect_id=not.is.null&order=at.asc&limit=1000") or []
    if not righe:
        return []
    pids = sorted({r["prospect_id"] for r in righe})
    gia_risposte, tipi = set(), {}
    schede = {}
    for i in range(0, len(pids), 80):
        pezzo = ",".join(pids[i:i + 80])
        for s in sb("GET", f"/rest/v1/segnali_provvisori?select=prospect_id,interaction_id,tipo&prospect_id=in.({pezzo})") or []:
            gia_risposte.add(s.get("interaction_id"))
            tipi.setdefault(s["prospect_id"], set()).add(s.get("tipo"))
        for p in sb("GET", f"/rest/v1/prospects?select=id,company,name,email,phone,fuori,stage,pipeline_stage,"
                           f"no_followup,classificazione&id=in.({pezzo})") or []:
            schede[p["id"]] = p
    per_azienda = {}
    for r in righe:
        if r["id"] in gia_risposte or r["prospect_id"] not in schede:
            continue
        per_azienda.setdefault(r["prospect_id"], []).append(r)
    ultima = lambda pid: max(x.get("at") or "" for x in per_azienda[pid])  # noqa: E731
    return [(schede[pid], rr, tipi.get(pid, set())) for pid, rr in sorted(per_azienda.items(), key=lambda kv: ultima(kv[0]), reverse=True)]


def permesso(tipo, gia):
    """Un tipo si segnala una volta sola per azienda; un si' non serve piu' se c'e' gia' stato il caldo."""
    return tipo not in gia and not (tipo == "si" and "caldo" in gia)


def valuta(p, risposte, ora, gia=frozenset(), storico=False):
    """Il segnale per un'azienda, o None. Legge TUTTE le risposte nuove (dalla memoria, una volta
    sola) e tiene la piu' forte: caldo, poi da guardare, poi si'. Il si' decide per ultimo.
    `gia`: i tipi gia' segnalati a quest'azienda.
    `storico`: la prova sul passato. Un si' conta come servito solo se lo e' stato entro il giro
    che l'avrebbe segnalato (10 minuti di attesa + l'orologio del direttore), non dopo."""
    if not contattabile(p):
        return None
    azienda = " ".join((p.get("company") or p.get("name") or "?").split())
    trovati, rimandate = [], False
    for r in sorted(risposte, key=lambda x: x.get("at") or "", reverse=True):
        corpo = r.get("body") or ""
        if automatica(corpo):
            continue
        testo = solo_suo(corpo, con_firma=True) or corpo
        if not testo.strip() or testo.lower().startswith("risposta ricevuta"):
            letto = {"fallita": True, "vuota": True}
        else:
            letto = leggi(azienda, testo)
        if letto == RIMANDATA:
            rimandate = True
            continue
        base = {"interaction_id": r["id"], "prospect_id": p["id"], "azienda": azienda,
                "persona": " ".join((p.get("name") or "").split()), "email": p.get("email") or "", "at": r.get("at"), "_r": r}
        if letto.get("fallita"):
            trovati.append({**base, "tipo": "da_guardare", "frase": " ".join(solo_suo(corpo).split())[:160],
                            "telefono": telefono_nel_testo(testo),
                            "consiglio": "L'AI non ha letto questa risposta: aprila tu."})
            continue
        if letto.get("autorisposta"):
            continue
        dati = {**base, "frase": letto.get("frase") or "", "telefono": letto.get("telefono") or "",
                "consiglio": letto.get("consiglio") or ""}
        if letto.get("caldo"):
            trovati.append({**dati, "tipo": "caldo"})
        elif letto.get("si"):
            trovati.append({**dati, "tipo": "si"})
        # un no, un rinvio, una domanda: il resto lo fa il sistema (e si guarda la risposta prima)
    buoni = sorted((s for s in trovati if permesso(s["tipo"], gia)), key=lambda s: ORDINE_TIPO[s["tipo"]])
    if not buoni:
        return None
    s = buoni[0]                                         # a parita' di tipo, la piu' recente
    r = s.pop("_r")
    if rimandate and s["tipo"] != "caldo":
        return None                                      # una risposta non ancora letta potrebbe essere un caldo
    if s["tipo"] != "si":
        return s
    visto = max(quando(r["at"]), quando(r.get("created_at") or r["at"]))
    if ora - visto < ATTESA_SI:
        return {**s, "tipo": "attesa"}                   # il sistema ha ancora qualche minuto
    if p.get("stage") == "call_fissata":
        return None                                      # la call c'e' gia': un si' qui non e' da servire (visto il 13/10)
    servito = primo_servizio(p["id"], quando(r["at"]))
    if servito and (not storico or servito <= visto + ATTESA_SI + OROLOGIO):
        return None
    return {**s, "servito_il": servito}


def _tel_link(tel):
    c = _cifre(tel)
    if not c:
        return ""
    if tel.strip().startswith("+") or c.startswith("00"):
        c = c[2:] if c.startswith("00") else c
        return "+" + c
    return "+39" + c if not c.startswith("39") or len(c) <= 10 else "+" + c


def cosa_fare(s):
    if s.get("servito_il"):
        return "Niente: è stato servito dopo (qui solo per mostrarti quando ti sarebbe arrivato il segnale)."
    if s.get("consiglio"):
        return s["consiglio"]
    if s["tipo"] == "caldo":
        return "Chiamalo oggi" + (" al numero qui sopra." if s.get("telefono") else ": il numero non c'è, rispondi chiedendolo.")
    if s["tipo"] == "si":
        return "Ha detto sì e nessuno gli ha ancora risposto: mandagli l'analisi dalla Master Inbox."
    return "Apri la risposta nella Master Inbox e decidi tu."


def _blocco(s):
    """Un segnale in testo e in html."""
    quando_roma = quando(s["at"]).astimezone(ROMA).strftime("%d/%m %H:%M") if s.get("at") else ""
    chi = s["azienda"] + (f" ({s['persona']})" if s.get("persona") else "")
    tel = s.get("telefono") or ""
    t = [f"{OGGETTO[s['tipo']].upper()}: {chi}", f"  {s.get('email', '')}  risposta delle {quando_roma}",
         f"  «{s.get('frase', '')}»"]
    if tel:
        t.append(f"  Telefono: {tel}  (tel:{_tel_link(tel)})")
    poi = s.get("servito_il")
    if poi:                                   # solo nella prova sul passato: il si' e' stato servito, ma tardi
        t.append(f"  (servito poi il {poi.astimezone(ROMA).strftime('%d/%m alle %H:%M')}: il segnale sarebbe arrivato prima)")
    t.append(f"  Cosa fare: {cosa_fare(s)}")
    e = html.escape
    h = (f"<p style='margin:0 0 4px'><b>{e(OGGETTO[s['tipo']])}: {e(chi)}</b><br>"
         f"<span style='color:#666'>{e(s.get('email', ''))} · risposta delle {e(quando_roma)}</span></p>"
         f"<p style='margin:0 0 4px'>«{e(s.get('frase', ''))}»</p>")
    if tel:
        h += f"<p style='margin:0 0 4px'>Telefono: <a href='tel:{e(_tel_link(tel))}'>{e(tel)}</a></p>"
    if poi:
        h += f"<p style='margin:0 0 4px;color:#666'>Servito poi il {e(poi.astimezone(ROMA).strftime('%d/%m alle %H:%M'))}: il segnale sarebbe arrivato prima.</p>"
    h += f"<p style='margin:0 0 16px'>Cosa fare: {e(cosa_fare(s))}</p>"
    return "\n".join(t), h


def _ordine(s):
    return (ORDINE_TIPO[s["tipo"]], bool(s.get("servito_il")), s.get("at") or "")


def componi(segnali, oggetto=None, intro=""):
    """Oggetto, testo e html della mail: uno solo, o l'elenco (prima i caldi, prima gli aperti)."""
    segnali = sorted(segnali, key=_ordine)
    if not oggetto:
        if len(segnali) == 1:
            oggetto = f"{OGGETTO[segnali[0]['tipo']]}: {segnali[0]['azienda']}"
        else:
            conta = {k: sum(1 for s in segnali if s["tipo"] == k) for k in ORDINE_TIPO}
            pezzi = [f"{conta['caldo']} vogliono sentirti" if conta["caldo"] else "",
                     f"{conta['si']} sì da servire" if conta["si"] else "",
                     f"{conta['da_guardare']} da guardare" if conta["da_guardare"] else ""]
            oggetto = "Segnali: " + ", ".join(x for x in pezzi if x)
    testi, htmls = zip(*[_blocco(s) for s in segnali]) if segnali else ((), ())
    piede_t = f"\nMaster Inbox di Smartlead: {MASTER_INBOX}\n\n(il segnale provvisorio: scrive solo a te)"
    piede_h = (f"<p><a href='{MASTER_INBOX}'>Apri la Master Inbox di Smartlead</a></p>"
               "<p style='color:#999;font-size:12px'>Il segnale provvisorio: scrive solo a te.</p>")
    testo = (intro + "\n\n" if intro else "") + ("\n\n".join(testi) + "\n" if segnali else "Nessun segnale.") + piede_t
    corpo = "<div style='font-family:-apple-system,Helvetica,Arial,sans-serif;font-size:15px;line-height:1.4'>" + \
            (f"<p style='margin:0 0 16px'>{html.escape(intro)}</p>" if intro else "") + \
            ("".join(htmls) or "<p>Nessun segnale.</p>") + piede_h + "</div>"
    return oggetto, testo, corpo


def segna(segnali, come):
    """Una volta sola per risposta, e per azienda e tipo: il database lo garantisce (unique).
    Torna i segnali segnati DA QUESTO giro: uno gia' segnato da un altro giro non si rimanda."""
    fatti = sb("POST", "/rest/v1/segnali_provvisori?on_conflict=prospect_id,tipo",
               [{"interaction_id": s["interaction_id"], "prospect_id": s["prospect_id"], "tipo": s["tipo"], "come": come}
                for s in segnali], {"Prefer": "resolution=ignore-duplicates,return=representation"}) or []
    nuovi = {x.get("interaction_id") for x in fatti}
    return [s for s in segnali if s["interaction_id"] in nuovi]


def togli(segnali):
    for s in segnali:
        try:
            sb("DELETE", f"/rest/v1/segnali_provvisori?interaction_id=eq.{s['interaction_id']}")
        except Exception:                                        # noqa: BLE001
            pass


def incerti(segnali, oggetto):
    """Gmail non ha risposto: la mail forse e' partita. Il segnale resta segnato come «incerto»
    con l'oggetto, e il giro dopo guarda nella posta inviata prima di rimandarlo."""
    for s in segnali:
        try:
            sb("PATCH", f"/rest/v1/segnali_provvisori?interaction_id=eq.{s['interaction_id']}",
               {"come": "incerto", "oggetto": oggetto}, {"Prefer": "return=minimal"})
        except Exception:                                        # noqa: BLE001
            pass


def risolvi_incerti():
    """A inizio giro: i segnali «incerti» del giro prima. Partiti (nella posta inviata di Dre)
    -> segnati per davvero; non partiti -> tolti, e questo giro li rimanda. Se non si puo'
    guardare restano segnati (mai un doppione) e Dre viene avvisato. Torna quanti restano in dubbio."""
    righe = sb("GET", "/rest/v1/segnali_provvisori?select=interaction_id,oggetto,quando&come=eq.incerto") or []
    gruppi = {}
    for x in righe:
        gruppi.setdefault((x.get("oggetto") or "", x.get("quando") or ""), []).append(x)
    dubbi = 0
    for (oggetto, il), xx in gruppi.items():
        try:
            partita = bool(oggetto) and _gmail_inviata(oggetto, quando(il))
        except Exception as e:                                   # noqa: BLE001
            print(f"  (non riesco a guardare la posta inviata: {str(e)[:100]})")
            dubbi += len(xx)
            continue
        for x in xx:
            try:
                if partita:
                    sb("PATCH", f"/rest/v1/segnali_provvisori?interaction_id=eq.{x['interaction_id']}",
                       {"come": "segnale"}, {"Prefer": "return=minimal"})
                else:
                    sb("DELETE", f"/rest/v1/segnali_provvisori?interaction_id=eq.{x['interaction_id']}")
            except Exception:                                    # noqa: BLE001
                dubbi += 1
        print(f"  incerto «{oggetto}»: " + ("era partita, non la rimando" if partita else "non era partita, la rimando"))
    if dubbi:
        avvisa_ogni("incerti", f"Il segnale provvisorio non sa se {dubbi} segnali ti sono arrivati: guarda la Master Inbox")
    return dubbi


def giro(ore=FINESTRA_ORE, prova=None, prova_mail=False, storico=False):
    """Il giro intero. Torna i segnali (mandati, o che si manderebbero in prova)."""
    prova = _a_secco() if prova is None else prova
    if prova and prova_mail:
        raise SystemExit("--prova-mail manda davvero: non va insieme a --prova")
    GIRO.update(pagate=0, memoria_rotta=False, sonda=False, giorno_restano=None, tetto_giorno=False)
    if not prova:
        risolvi_incerti()
    ora = adesso()
    segnali, attese = [], 0
    for p, risposte, gia in candidati(ore):
        s = valuta(p, risposte, ora, gia=gia, storico=storico)
        if not s:
            continue
        if s["tipo"] == "attesa":
            attese += 1
            continue
        segnali.append(s)
    if GIRO["memoria_rotta"]:
        avvisa_ogni("memoria", "Il segnale provvisorio non riesce a usare la memoria delle letture: non paga "
                               "letture e le risposte nuove ti arrivano come «da guardare»")
    if GIRO["tetto_giorno"]:
        avvisa_ogni("tetto", f"Il segnale provvisorio ha finito le {PAGATE_AL_GIORNO} letture del giorno: "
                             "le risposte nuove ti arrivano come «da guardare»")
    segnali.sort(key=_ordine)
    if not segnali:
        print(f"niente da segnalare ({attese} si' ancora nei 10 minuti)" if attese else "niente da segnalare")
        return []
    if prova:
        mail = _mail(segnali, ore, prova_mail)
        for oggetto, testo, _, _ in mail:
            print(f"\n(prova) A: {DRE}\n(prova) Oggetto: {oggetto}\n{testo}")
        print(f"\n(prova) {len(segnali)} segnali, {len(mail)} mail: niente mandato, niente segnato")
        return segnali
    # si segna PRIMA di mandare: se il giro muore a meta', al peggio un segnale manca, mai doppio
    segnali = segna(segnali, "prova" if prova_mail else "segnale")
    if not segnali:
        print("niente da segnalare (gia' segnati da un altro giro)")
        return []
    falliti, dubbi = [], []
    for oggetto, testo, corpo, gruppo in _mail(segnali, ore, prova_mail):
        try:
            manda_mail(DRE, oggetto, testo, corpo)
            print(f"mandata a Dre: {oggetto}")
        except Exception as e:                                   # noqa: BLE001
            if non_partita(e):
                print(f"MAIL NON MANDATA ({oggetto}): {str(e)[:160]}")
                togli(gruppo)                                    # al giro dopo riparte, la lettura e' in memoria
                falliti += gruppo
            else:
                print(f"MAIL FORSE MANDATA ({oggetto}), Gmail non ha risposto: {str(e)[:160]}")
                incerti(gruppo, oggetto)                         # il giro dopo guarda nella posta inviata
                dubbi += gruppo
    if falliti:
        avvisa_ogni("gmail", f"Il segnale provvisorio non riesce a mandarti la mail: {len(falliti)} lead da guardare in Master Inbox")
    if falliti or dubbi:
        raise SystemExit(1)
    return segnali


def _mail(segnali, ore, prova_mail):
    """Le mail del giro, ognuna col suo gruppo di segnali: (oggetto, testo, html, gruppo)."""
    if prova_mail:
        aperti = sum(1 for s in segnali if not s.get("servito_il"))
        return [(*componi(segnali, oggetto="Prova del segnale provvisorio", intro=(
            f"La prova: ecco cosa ti avrei segnalato nelle ultime {ore} ore. {aperti} sono ancora aperti, in cima; "
            "quelli con «servito dopo» erano già sistemati e servono solo a vedere quando ti sarebbe arrivata la mail. "
            "Da adesso arriva da sola: subito per chi vuole sentirti, dopo 10 minuti per un sì rimasto senza risposta. "
            "Questi non te li rimando.")), segnali)]
    if len(segnali) > TANTI:
        return [(*componi(segnali), segnali)]
    return [(*componi([s]), [s]) for s in segnali]


# ── LE PRENOTAZIONI DELLE CALL (14/10) ─────────────────────────────
# Dre, 14/10: chi prenota la videochiamata conoscitiva dalla sua pagina di Google Calendar
# lo vedeva solo per caso in Gmail. Qui si guarda il suo calendario (e, come rete, le mail
# «Appuntamento prenotato» / «Appuntamento annullato») e gli si manda la scheda per la call.
# Solo lettura: niente si scrive sul calendario, niente su Smartlead, nessuna mail ai lead.

CAL_EVENTI = "https://www.googleapis.com/calendar/v3/calendars/primary/events"
GMAIL = "https://gmail.googleapis.com/gmail/v1/users/me/messages"
MATTINA = datetime.time(8, 30)                  # la scheda della mattina della call, ora di Roma
AVANTI_GIORNI = 120
VERSIONE_SCHEDA = "scheda1"
GIORNI = ("lunedì", "martedì", "mercoledì", "giovedì", "venerdì", "sabato", "domenica")
MESI = ("gennaio", "febbraio", "marzo", "aprile", "maggio", "giugno", "luglio", "agosto", "settembre",
        "ottobre", "novembre", "dicembre")
OGGETTO_PREN = {"prenotato": "Prenotato", "spostata": "Spostata", "cancellata": "Cancellata"}

DOMANDA_SCHEDA = """Prepari a Dre, titolare di Studio Galilei (agenzia di marketing e Google Ads), la scheda
per una videochiamata conoscitiva con un'azienda che l'ha appena prenotata. Qui sotto: chi ha prenotato,
le mail che ci ha scritto (con la firma) e cosa sappiamo dell'azienda dal Google Fit e dal suo sito.

Rispondi con questi campi:
- nome: nome e cognome della persona, come nella firma, senza titoli (Dott., Arch., Ing.); se la firma
  non c'e' quello di chi ha prenotato; vuoto se non lo sai.
- ruolo: il suo ruolo COPIATO dalla firma (es. «Amministratore Unico», «Marketing Manager»). Vuoto se la
  firma non lo dice. Mai dedurlo, mai inventarlo.
- attivita: 2-3 righe, al massimo 50 parole, su cosa fa l'azienda, per chi e dove, piu' un dettaglio utile
  per la call se c'e' (da quando esiste, chi la guida, il punto forte). SOLO da quello che c'e' qui sotto.
- ultima_frase: la frase che conta del suo ULTIMO messaggio, copiata parola per parola (al massimo 25
  parole, senza saluti ne' firma). Vuota se non ci ha mai scritto.

CHI HA PRENOTATO: {prenotato}
L'AZIENDA: {azienda}
LE SUE MAIL (dalla piu' vecchia; l'ultima e' in fondo):
{mail}

COSA SAPPIAMO DELL'AZIENDA:
{azienda_dati}"""

SCHEMA_SCHEDA = {"type": "json_schema", "json_schema": {"name": "scheda_call", "strict": True, "schema": {
    "type": "object", "additionalProperties": False, "required": ["nome", "ruolo", "attivita", "ultima_frase"],
    "properties": {"nome": {"type": "string"}, "ruolo": {"type": "string"}, "attivita": {"type": "string"},
                   "ultima_frase": {"type": "string"}}}}}


def _evento_id(uid):
    """L'id dell'evento: lo stesso dal calendario (id) e dalla mail (UID dell'invito .ics, «id@google.com»)."""
    return (uid or "").split("@")[0].strip()


def _giorno_ora(dt):
    r = dt.astimezone(ROMA)
    return f"{GIORNI[r.weekday()]} {r.day} {MESI[r.month - 1]} alle {r:%H:%M}"


def _iso(dt):
    return dt.astimezone(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%S+00:00") if dt else None


def _da_google(it):
    """Un evento dell'API di Calendar nella forma di qui (solo i campi che servono)."""
    inizio = (it.get("start") or {}).get("dateTime")
    return {"evento": it.get("id") or _evento_id(it.get("iCalUID")),
            "inizio": quando(inizio) if inizio else None,
            "titolo": (it.get("summary") or "").strip(), "descrizione": it.get("description") or "",
            "invitati": [(a.get("email") or "").lower() for a in it.get("attendees") or [] if a.get("email")],
            "rifiutati": [(a.get("email") or "").lower() for a in it.get("attendees") or []
                          if a.get("email") and a.get("responseStatus") == "declined"],
            "stato": (it.get("status") or "confirmed").lower(), "meet": it.get("hangoutLink") or "",
            "link": it.get("htmlLink") or "", "fonte": "calendario"}


def _eventi_calendario(ora):
    """Gli eventi del calendario di Dre da ieri a 120 giorni, cancellati compresi. Solo lettura."""
    from google_api import g
    eventi, pagina = [], None
    for _ in range(10):
        p = {"timeMin": _z(ora - datetime.timedelta(days=1)), "timeMax": _z(ora + datetime.timedelta(days=AVANTI_GIORNI)),
             "singleEvents": "true", "showDeleted": "true", "maxResults": 250}
        if pagina:
            p["pageToken"] = pagina
        d = g("GET", f"{CAL_EVENTI}?{urllib.parse.urlencode(p)}", email=DRE) or {}
        eventi += [_da_google(it) for it in d.get("items") or []]
        pagina = d.get("nextPageToken")
        if not pagina:
            break
    return eventi


def _parti(p):
    yield p
    for q in p.get("parts") or []:
        yield from _parti(q)


def _prenotazioni_mail(ora):
    """La rete: le mail «Appuntamento prenotato» e «Appuntamento annullato» degli ultimi 3 giorni
    nella Gmail di Dre. L'invito .ics dentro porta l'id dell'evento: la stessa prenotazione vista
    dal calendario ha la stessa chiave e non suona due volte. Solo lettura."""
    from google_api import g
    from calendario import da_ics
    q = 'subject:("Appuntamento prenotato" OR "Appuntamento annullato") newer_than:3d'
    eventi = []
    for m in (g("GET", f"{GMAIL}?q={urllib.parse.quote(q)}&maxResults=25", email=DRE) or {}).get("messages") or []:
        d = g("GET", f"{GMAIL}/{m['id']}?format=full", email=DRE) or {}
        for parte in _parti(d.get("payload") or {}):
            if parte.get("mimeType") != "text/calendar":
                continue
            b = parte.get("body") or {}
            dati = b.get("data")
            if not dati and b.get("attachmentId"):
                dati = (g("GET", f"{GMAIL}/{m['id']}/attachments/{b['attachmentId']}", email=DRE) or {}).get("data")
            if not dati:
                continue
            ics = base64.urlsafe_b64decode(dati + "=" * (-len(dati) % 4)).decode("utf-8", "replace")
            annullato = "METHOD:CANCEL" in ics
            for e in da_ics(ics):
                if e.get("giornata"):
                    continue
                eventi.append({"evento": _evento_id(e.get("uid")), "inizio": e["at"].astimezone(datetime.timezone.utc),
                               "titolo": e.get("titolo") or "", "descrizione": e.get("descrizione") or "",
                               "invitati": e.get("invitati") or [], "rifiutati": [],
                               "stato": "cancelled" if annullato or (e.get("stato") or "").upper() == "CANCELLED" else "confirmed",
                               "meet": e.get("meet") or "", "link": "", "fonte": "mail"})
            break
    return eventi


def raccogli(ora):
    """Le prenotazioni viste dal calendario e dalla posta, una per evento: il calendario vince
    (e' lo stato di adesso), la mail copre quello che il calendario non ha dato. Torna
    (eventi per chiave, calendario letto?, posta letta?)."""
    eventi, cal_ok, mail_ok = {}, True, True
    try:
        for e in _eventi_calendario(ora):
            if e["evento"]:
                eventi[e["evento"]] = e
    except Exception as ex:                                      # noqa: BLE001
        cal_ok = False
        print(f"  (il calendario di Dre non si legge: {str(ex)[:120]})")
    try:
        for e in _prenotazioni_mail(ora):
            vista = eventi.get(e["evento"])
            if not e["evento"]:
                continue
            if not vista:
                eventi[e["evento"]] = e
            elif vista.get("fonte") == "mail" and e["stato"] == "cancelled":
                eventi[e["evento"]] = e                          # due mail della stessa: l'annullamento vince
    except Exception as ex:                                      # noqa: BLE001
        mail_ok = False
        print(f"  (la posta di Dre non si legge: {str(ex)[:120]})")
    return eventi, cal_ok, mail_ok


def _esterni(ev):
    from calendario import esterni
    return esterni(ev.get("invitati") or [])


def e_prenotazione(ev):
    """Una call prenotata con qualcuno di fuori: dalla pagina delle prenotazioni («Prenotato da»,
    o la mail «Appuntamento prenotato»), o una conoscitiva messa in calendario a mano."""
    if not _esterni(ev):
        return False
    return (ev.get("fonte") == "mail" or "prenotato da" in (ev.get("descrizione") or "").lower()
            or "conoscitiv" in (ev.get("titolo") or "").lower())


def _annullata(ev):
    if ev.get("stato") == "cancelled":
        return "annullata"
    fuori = _esterni(ev)
    if fuori and all(x in (ev.get("rifiutati") or []) for x in fuori):
        return "rifiutata"
    return ""


def _noti(righe):
    """Quello che e' gia' stato segnalato, per evento: prenotato? cancellato? l'ultimo orario, le mattine."""
    noti = {}
    for r in sorted(righe, key=lambda r: (r.get("quando") or "", r.get("tipo") != "prenotato")):
        n = noti.setdefault(r["evento"], {"prenotato": False, "cancellata": False, "inizio": None, "mattine": set(),
                                          "invitato": "", "azienda": "", "prospect_id": None, "prenotato_il": None,
                                          "come_prenotato": ""})
        for k in ("invitato", "azienda", "prospect_id"):
            n[k] = r.get(k) or n[k]
        if r["tipo"] in ("prenotato", "spostata"):
            n["inizio"] = quando(r["inizio"]) if r.get("inizio") else n["inizio"]
            if r["tipo"] == "prenotato":
                n["prenotato"], n["come_prenotato"] = True, r.get("come") or ""
                n["prenotato_il"] = quando(r["quando"]) if r.get("quando") else None
        elif r["tipo"] == "cancellata":
            n["cancellata"] = True
        elif r["tipo"] == "mattina":
            n["mattine"].add(r["chiave"])
    return noti


def _alle_830(giorno):
    return datetime.datetime.combine(giorno, MATTINA, tzinfo=ROMA)


def decidi(eventi, righe, ora, calendario_ok=True):
    """I segnali da dare adesso, senza toccare niente (si prova da sola). Una prenotazione nuova
    -> «prenotato»; un orario cambiato -> «spostata» (anche quando dalla pagina si prende un altro
    orario: e' una prenotazione nuova e quella vecchia si annulla, ma per Dre e' uno spostamento);
    annullata o rifiutata -> «cancellata»; la mattina della call dalle 8:30 -> «mattina»."""
    noti = _noti(righe)
    segnali, assorbite = [], set()
    attivi = {}                                          # chi ha prenotato -> le sue prenotazioni ancora in piedi
    for k, n in noti.items():
        if n["prenotato"] and not n["cancellata"] and n["invitato"] and n["inizio"] and n["inizio"] > ora - datetime.timedelta(hours=1):
            attivi.setdefault(n["invitato"], []).append(k)
    for ev in sorted(eventi.values(), key=lambda e: e.get("inizio") or ora):
        k, n = ev["evento"], noti.get(ev["evento"])
        if _annullata(ev) or not ev.get("inizio") or ev["inizio"] <= ora:
            continue
        chi = (_esterni(ev) or [""])[0]
        base = {"evento": k, "ev": ev, "inizio": ev["inizio"], "invitato": chi or (n or {}).get("invitato", ""),
                "nota": n}
        if not n or not n["prenotato"]:
            if not e_prenotazione(ev):
                continue
            altre = [a for a in attivi.get(chi, []) if a != k] if chi else []
            if altre:
                vecchia = noti[altre[0]]
                assorbite.add(altre[0])
                segnali.append({**base, "tipo": "spostata", "prima": vecchia["inizio"], "da_evento": altre[0],
                                "chiave": f"spostata:{k}:{_iso(ev['inizio'])}",
                                "nota": vecchia})
            else:
                segnali.append({**base, "tipo": "prenotato", "chiave": f"prenotato:{k}"})
        elif n["inizio"] and abs((ev["inizio"] - n["inizio"]).total_seconds()) >= 60:
            segnali.append({**base, "tipo": "spostata", "prima": n["inizio"], "chiave": f"spostata:{k}:{_iso(ev['inizio'])}"})
    for ev in eventi.values():
        k, n = ev["evento"], noti.get(ev["evento"])
        perche = _annullata(ev)
        if not perche or not n or not n["prenotato"] or n["cancellata"] or k in assorbite:
            continue
        inizio = n["inizio"] or ev.get("inizio")
        if inizio and inizio <= ora:
            continue                                     # una call gia' passata: non serve dirlo
        segnali.append({"evento": k, "ev": ev, "inizio": inizio, "invitato": n["invitato"], "nota": n,
                        "tipo": "cancellata", "perche": perche, "chiave": f"cancellata:{k}"})
    # la mattina della call, dalle 8:30 di Roma
    oggi = ora.astimezone(ROMA).date()
    if ora.astimezone(ROMA).time() >= MATTINA:
        orari = {k: n["inizio"] for k, n in noti.items() if n["prenotato"] and not n["cancellata"] and k not in assorbite}
        for s in segnali:
            if s["tipo"] == "spostata":
                orari[s["evento"]] = s["inizio"]
            elif s["tipo"] == "cancellata":
                orari.pop(s["evento"], None)
        appena = {s["evento"] for s in segnali if s["tipo"] == "prenotato"}
        for k in list(orari):
            ev = eventi.get(k)
            if ev:
                if _annullata(ev):
                    orari.pop(k)
                else:
                    orari[k] = ev.get("inizio")
            elif calendario_ok:
                orari.pop(k)                             # il calendario risponde e l'evento non c'e' piu'
        for k, inizio in sorted(orari.items(), key=lambda kv: kv[1] or ora):
            if not inizio or k in appena or inizio <= ora or inizio.astimezone(ROMA).date() != oggi:
                continue
            n = noti.get(k) or {}
            chiave = f"mattina:{k}:{oggi.isoformat()}"
            if chiave in n.get("mattine", ()):
                continue
            # la scheda e' gia' arrivata stamattina con la prenotazione: non la si rimanda
            if n.get("come_prenotato") == "segnale" and n.get("prenotato_il") and n["prenotato_il"] >= _alle_830(oggi):
                continue
            ev = eventi.get(k)
            segnali.append({"evento": k, "ev": ev, "inizio": inizio, "invitato": n.get("invitato") or ((_esterni(ev) or [""])[0] if ev else ""),
                            "nota": n or None, "tipo": "mattina", "chiave": chiave})
    return segnali


# ── la scheda per la call ──────────────────────────────────────────

def _nazionale(c):
    if c.startswith("0039"):
        return c[4:]
    if c.startswith("39") and len(c) > 10:
        return c[2:]
    return c


def telefoni_in(testo, fonte, esclusi=frozenset()):
    """Tutti i numeri di un testo, con il tipo: cellulare (3...) o fisso (0...). Via la partita IVA
    (la regola di sempre), i fax e i numeri nostri (`esclusi`: le ultime 9 cifre)."""
    out, fine = [], 0
    for m in TELEFONO.finditer(testo or ""):
        c = _cifre(m.group(0))
        if not 9 <= len(c) <= 13 or _non_telefono(testo, m):
            continue
        prima = testo[max(fine, m.start() - 30, testo.rfind("\n", 0, m.start()) + 1):m.start()]
        fine = m.end()
        if re.search(r"fax", prima, re.I) and not re.search(r"tel|cell|mob", prima, re.I):
            continue
        naz = _nazionale(c)
        if naz[-9:] in esclusi:
            continue
        tipo = "cellulare" if naz.startswith("3") else "fisso"
        out.append({"numero": " ".join(m.group(0).split()), "tipo": tipo, "fonte": fonte, "cifre": naz})
    return out


RANGO_TEL = {("cellulare", "firma"): 0, ("cellulare", "scheda"): 1, ("fisso", "firma"): 2, ("fisso", "scheda"): 3,
             ("cellulare", "sito"): 4, ("fisso", "sito"): 5}
DA_DOVE = {"firma": "dalla firma", "scheda": "dalla scheda del Workspace", "sito": "dal sito"}


def in_gerarchia(numeri):
    """Il piu' diretto in alto: il cellulare della firma, poi il fisso della firma, poi quello che
    sta nella scheda, poi il centralino del sito. Lo stesso numero una volta sola, al posto piu' alto."""
    visti, out = set(), []
    for t in sorted(numeri, key=lambda t: RANGO_TEL.get((t["tipo"], t["fonte"]), 9)):
        if t["cifre"][-9:] in visti:
            continue
        visti.add(t["cifre"][-9:])
        tipo = "centralino" if (t["tipo"], t["fonte"]) == ("fisso", "sito") else t["tipo"]
        out.append({**t, "etichetta": f"{tipo}, {DA_DOVE.get(t['fonte'], t['fonte'])}"})
    return out


def _frase_pulita(t):
    return " ".join((t or "").replace("«", "").replace("»", "").split())


SALUTO = re.compile(r"^\s*(buongiorno|buonasera|salve|gentil\w*|egregi\w*|caro|cara|ciao|spett\w*)\b[^\n]{0,40}$", re.I)
CHIUSA = re.compile(r"^\s*(cordiali saluti|distinti saluti|saluti|un saluto|grazie(,| e)? (mille|ancora)?|a presto)\b", re.I)


def ultima_frase_semplice(testo):
    """Senza AI: il suo messaggio senza saluto, firma e chiusa, corto."""
    righe = [r.strip() for r in (solo_suo(testo) or "").split("\n") if r.strip()]
    righe = [r for r in righe if not SALUTO.match(r)]
    tenute = []
    for r in righe:
        if CHIUSA.match(r):
            break
        tenute.append(r)
    t = " ".join(tenute) or " ".join(righe)
    return (t[:197] + "...") if len(t) > 200 else t


def _leggi_scheda(prompt):
    """Una lettura per la scheda, con la memoria e il tetto del giorno della casa. None se non c'e'."""
    chiave = "scheda:" + hashlib.sha256("\x00".join((VERSIONE_SCHEDA, MODELLO, prompt)).encode("utf-8")).hexdigest()[:24]
    if GIRO["memoria_rotta"]:
        return None
    try:
        r = sb("GET", f"/rest/v1/memoria_letture?select=valore&chiave=eq.{chiave}") or []
    except Exception:                                            # noqa: BLE001
        GIRO["memoria_rotta"] = True
        return None
    if r and isinstance(r[0].get("valore"), dict):
        SPESA["dalla_memoria"] += 1
        v = r[0]["valore"]
        return None if v.get("fallita") else v
    if not GIRO["sonda"]:
        if not _ricorda("segnale:sonda", {"il": _z(adesso())}):
            return None
        GIRO["sonda"] = True
    if _restano_oggi() <= 0:
        GIRO["tetto_giorno"] = True
        return None
    GIRO["pagate"] += 1
    GIRO["giorno_restano"] -= 1
    v = None
    try:
        grezzo = _chiedi_ai(prompt, SCHEMA_SCHEDA)
        m = re.search(r"\{.*\}", grezzo or "", re.S)
        v = json.loads(m.group(0)) if m else None
    except Exception as e:                                       # noqa: BLE001
        print(f"  (l'AI non ha letto la scheda: {str(e)[:100]})")
    if not isinstance(v, dict) or not all(isinstance(v.get(k), str) for k in ("nome", "ruolo", "attivita", "ultima_frase")):
        v = {"fallita": True}
    _ricorda(chiave, v)
    return None if v.get("fallita") else v


def _dentro(pezzo, testo):
    """Il pezzo sta davvero nel testo? (spazi e maiuscole a parte)"""
    norm = lambda s: " ".join(re.sub(r"[«»\"“”]", " ", s or "").lower().split())  # noqa: E731
    return bool(norm(pezzo)) and norm(pezzo) in norm(testo)


def _attivita_semplice(p):
    """Senza AI: le righe del Google Fit, cosi' come sono."""
    e = p.get("enriched") or {}
    fit = e.get("google_fit") or e.get("google_fit_v2") or {}
    pezzi = [(fit.get("cosa_fa") or p.get("descrizione") or "").rstrip(".")]
    if fit.get("tipo") or fit.get("ticket"):
        pezzi.append(", ".join(x for x in (f"clienti {fit['tipo']}" if fit.get("tipo") else "",
                                            f"valore di un cliente {fit['ticket']} (stima)" if fit.get("ticket") else "") if x).capitalize())
    rec = fit.get("recensioni") or {}
    if isinstance(rec, dict) and rec.get("recensioni"):
        pezzi.append(f"{rec['recensioni']} recensioni su Google" + (f", voto {rec['voto']}" if rec.get("voto") else ""))
    return ". ".join(x for x in pezzi if x) + ("." if any(pezzi) else "")


def _riconosci(ev):
    """Il lead della prenotazione: l'agenda prima (il calendario ce l'ha gia' attaccato, o l'ha
    scelto Dre a mano), poi il riconoscimento di calendario.py (mail, dominio, sito, titolo, nome)."""
    meet = (ev.get("meet") or "").split("?")[0]
    if meet:
        r = sb("GET", f"/rest/v1/agenda?select=prospect_id&link=eq.{urllib.parse.quote(meet, safe='')}"
                      f"&prospect_id=not.is.null&limit=1") or []
        if r:
            return r[0]["prospect_id"]
    import calendario as C
    if "prospects" not in _CACHE:
        _CACHE["prospects"] = C.carica_prospects()
    pid, _ = C.riconosci({"invitati": ev.get("invitati") or [], "titolo": ev.get("titolo") or "",
                          "descrizione": ev.get("descrizione") or ""}, _CACHE["prospects"])
    return pid


_CACHE = {}


def _chi_ha_prenotato(ev):
    from calendario import prenotato_da
    return prenotato_da({"descrizione": re.sub(r"<[^>]+>", "\n", (ev or {}).get("descrizione") or ""),
                         "titolo": (ev or {}).get("titolo") or ""}) or ""


def _sito_della_prenotazione(ev):
    from calendario import siti_nella_descrizione
    s = siti_nella_descrizione((ev or {}).get("descrizione") or "")
    return s[0] if s else ""


def scheda(pid, ev, invitato=""):
    """Tutto quello che serve per la call, da quello che c'e' gia'. Senza lead: quello che dice
    la prenotazione (mai silenzio)."""
    chi = _chi_ha_prenotato(ev)
    sc = {"abbinata": False, "nome": chi, "ruolo": "", "email": invitato, "telefoni": [], "attivita": "",
          "ultima": "", "ultima_il": None, "analisi": None, "sito": _sito_della_prenotazione(ev),
          "azienda": "", "meet": ((ev or {}).get("meet") or "").split("?")[0], "link": (ev or {}).get("link") or ""}
    p = (sb("GET", f"/rest/v1/prospects?select=id,company,name,email,role,phone,website,descrizione,analysis_sent,"
                   f"analysis_sent_at,analysis_pdf,enriched&id=eq.{pid}") or [None])[0] if pid else None
    if not p:
        sc["azienda"] = sc["sito"] or chi or invitato or "?"
        return sc
    sc["abbinata"] = True
    sc["azienda"] = " ".join((p.get("company") or p.get("name") or sc["sito"] or chi or "?").split())
    sc["email"] = invitato or p.get("email") or ""
    e = p.get("enriched") or {}
    fit = e.get("google_fit") or e.get("google_fit_v2") or {}
    righe = sb("GET", f"/rest/v1/interactions?select=at,kind,body&prospect_id=eq.{pid}"
                      f"&kind=in.(email_in,email_out)&order=at.asc&limit=80") or []
    sue = [r for r in righe if r.get("kind") == "email_in" and (r.get("body") or "").strip() and not automatica(r["body"])]
    nostri = set()
    for r in righe:
        if r.get("kind") == "email_out":
            nostri |= {_nazionale(_cifre(m.group(0)))[-9:] for m in TELEFONO.finditer(r.get("body") or "")}
    # i numeri: la firma (tutte le sue mail, la parte sua), la scheda, il sito gia' letto
    numeri = []
    for r in sue:
        numeri += telefoni_in(solo_suo(r["body"], con_firma=True), "firma", nostri)
    for t in (p.get("phone"), e.get("phone")):
        if isinstance(t, str) and t.strip():
            numeri += telefoni_in(t, "scheda", nostri)
    numeri += telefoni_in(fit.get("sito_testo") or "", "sito", nostri)
    sc["telefoni"] = in_gerarchia(numeri)
    # l'analisi
    an = e.get("analisi") or {}
    sc["analisi"] = {"mandata": bool(p.get("analysis_sent")), "il": quando(p["analysis_sent_at"]) if p.get("analysis_sent_at") else None,
                     "link": p.get("analysis_pdf") or "", "punto": _frase_pulita(an.get("frase_forte"))}
    # chi e', cosa fa, l'ultima frase: una lettura AI (dalla memoria se c'e'), con la rete senza AI
    ultima = sue[-1] if sue else None
    if ultima:
        sc["ultima_il"] = quando(ultima["at"]) if ultima.get("at") else None
        sc["ultima"] = ultima_frase_semplice(ultima["body"])
    sc["nome"] = chi or " ".join((p.get("name") or "").split())
    sc["ruolo"] = p.get("role") or ""
    sc["attivita"] = _attivita_semplice(p)
    materiale = "\n\n".join(f"[{(r.get('at') or '')[:10]}] «{solo_suo(r['body'], con_firma=True)[:1800]}»" for r in sue[-3:])
    dati = "\n".join(x for x in (
        f"- dal Google Fit: {fit.get('cosa_fa')}" if fit.get("cosa_fa") else "",
        f"- settore: {fit.get('settore') or p.get('sector') or ''}; clienti {fit.get('tipo') or '?'}; zone: {', '.join(fit.get('zone_servite') or []) or '?'}"
        if fit else "",
        f"- descrizione nel Workspace: {p.get('descrizione')}" if p.get("descrizione") else "",
        f"- sito: {p.get('website')}" if p.get("website") else "",
        f"- dal sito: {(fit.get('sito_testo') or '')[:2500]}" if fit.get("sito_testo") else "") if x)
    if materiale or dati:
        v = _leggi_scheda(DOMANDA_SCHEDA.format(prenotato=f"{chi or '?'} <{invitato or '?'}>", azienda=sc["azienda"],
                                                mail=materiale or "(nessuna)", azienda_dati=dati or "(niente)"))
        if v:
            tutto = materiale + "\n" + chi
            if v.get("nome") and all(_dentro(w, tutto) for w in v["nome"].split()):
                sc["nome"] = " ".join(v["nome"].split())
            # il ruolo deve stare scritto nella firma: un ruolo dedotto e' peggio di nessun ruolo
            sc["ruolo"] = " ".join(v["ruolo"].split()) if v.get("ruolo") and _dentro(v["ruolo"], materiale) else sc["ruolo"]
            if v.get("attivita", "").strip():
                sc["attivita"] = " ".join(v["attivita"].split())
            if ultima and v.get("ultima_frase") and _dentro(v["ultima_frase"], ultima["body"]):
                sc["ultima"] = _frase_pulita(v["ultima_frase"])
    return sc


# ── la mail delle prenotazioni ─────────────────────────────────────

def _pezzi_scheda(sc, s):
    """La scheda, in testo e html. Un numero per riga, il piu' diretto in alto, cliccabile."""
    e = html.escape
    grigio = "color:#666"
    t, h = [], []
    quando_t = _giorno_ora(s["inizio"]) if s.get("inizio") else ""
    t.append(f"{sc['azienda']}, {quando_t}")
    h.append(f"<p style='margin:0 0 4px;font-size:17px'><b>{e(sc['azienda'])}</b></p>"
             f"<p style='margin:0 0 16px;{grigio}'>{e(quando_t)}"
             + (f" · <a href='{e(sc['meet'])}'>entra nel Meet</a>" if sc.get("meet") else "") + "</p>")
    if sc.get("meet"):
        t.append(f"Meet: {sc['meet']}")
    # chi e'
    chi = ", ".join(x for x in (sc.get("nome"), sc.get("ruolo")) if x) or "?"
    t += ["", "CHI E'", f"{chi}" + (f"  {sc['email']}" if sc.get("email") else "")]
    h.append(f"<p style='margin:0 0 12px'><b>Chi è</b><br>{e(chi)}"
             + (f"<br><span style='{grigio}'>{e(sc['email'])}</span>" if sc.get("email") else "") + "</p>")
    if not sc["abbinata"]:
        nota = "Non l'ho trovato fra i lead del Workspace: qui sotto c'è solo quello che dice la prenotazione."
        if sc.get("sito"):
            nota += f" Sito scritto nella prenotazione: {sc['sito']}."
        t.append(nota)
        h.append(f"<p style='margin:0 0 12px'>{e(nota)}</p>")
    # i numeri
    t += ["", "TELEFONI"]
    if sc["telefoni"]:
        righe_h = []
        for x in sc["telefoni"]:
            t.append(f"{x['numero']}  ({x['etichetta']})  tel:{_tel_link(x['numero'])}")
            righe_h.append(f"<a href='tel:{e(_tel_link(x['numero']))}'>{e(x['numero'])}</a> <span style='{grigio}'>{e(x['etichetta'])}</span>")
        h.append("<p style='margin:0 0 12px'><b>Telefoni</b><br>" + "<br>".join(righe_h) + "</p>")
    else:
        t.append("Nessun numero: né nella firma né nel Workspace.")
        h.append("<p style='margin:0 0 12px'><b>Telefoni</b><br>Nessun numero: né nella firma né nel Workspace.</p>")
    # cosa fa
    if sc.get("attivita"):
        t += ["", "COSA FA", sc["attivita"]]
        h.append(f"<p style='margin:0 0 12px'><b>Cosa fa</b><br>{e(sc['attivita'])}</p>")
    # l'ultima cosa che ci ha scritto
    if sc.get("ultima"):
        il = sc["ultima_il"].astimezone(ROMA).strftime("%d/%m") if sc.get("ultima_il") else ""
        t += ["", f"L'ULTIMA COSA CHE CI HA SCRITTO" + (f" ({il})" if il else ""), f"«{sc['ultima']}»"]
        h.append(f"<p style='margin:0 0 12px'><b>L'ultima cosa che ci ha scritto</b>"
                 + (f" <span style='{grigio}'>({e(il)})</span>" if il else "") + f"<br>«{e(sc['ultima'])}»</p>")
    elif sc["abbinata"]:
        t += ["", "L'ULTIMA COSA CHE CI HA SCRITTO", "Non ci ha mai scritto."]
        h.append("<p style='margin:0 0 12px'><b>L'ultima cosa che ci ha scritto</b><br>Non ci ha mai scritto.</p>")
    # cosa gli abbiamo mandato
    if sc["abbinata"]:
        a = sc.get("analisi") or {}
        if a.get("mandata"):
            il = a["il"].astimezone(ROMA).strftime("%d/%m") if a.get("il") else ""
            riga = "Sì, l'analisi" + (f" il {il}" if il else "")
            t += ["", "COSA GLI ABBIAMO MANDATO", riga + (f": {a['link']}" if a.get("link") else "")]
            hh = e(riga) + (f": <a href='{e(a['link'])}'>apri l'analisi</a>" if a.get("link") else "")
            if a.get("punto"):
                t.append(f"Il punto chiave: {a['punto']}")
                hh += f"<br>Il punto chiave: {e(a['punto'])}"
            h.append(f"<p style='margin:0 0 12px'><b>Cosa gli abbiamo mandato</b><br>{hh}</p>")
        else:
            t += ["", "COSA GLI ABBIAMO MANDATO", "No, l'analisi non gli è ancora arrivata."]
            h.append("<p style='margin:0 0 12px'><b>Cosa gli abbiamo mandato</b><br>No, l'analisi non gli è ancora arrivata.</p>")
    t += ["", "Appunti:", ""]
    h.append("<p style='margin:16px 0 28px'><b>Appunti:</b></p>")
    return t, h


def componi_prenotazione(s):
    """Oggetto, testo e html della mail per un segnale di prenotazione."""
    az = s.get("azienda") or "?"
    quando_t = _giorno_ora(s["inizio"]) if s.get("inizio") else "orario sconosciuto"
    t, h = [], []
    e = html.escape
    if s["tipo"] == "prenotato":
        oggetto = f"Prenotato: {az}, {quando_t}"
        t, h = _pezzi_scheda(s["scheda"], s)
    elif s["tipo"] == "mattina":
        oggetto = f"Oggi alle {s['inizio'].astimezone(ROMA):%H:%M}: {az}"
        t, h = _pezzi_scheda(s["scheda"], s)
    elif s["tipo"] == "spostata":
        oggetto = f"Spostata: {az}, ora {quando_t}"
        prima = _giorno_ora(s["prima"]) if s.get("prima") else "l'orario di prima"
        riga = (f"La call con {az} era {prima}: adesso è {quando_t}"
                + (" (ha preso un altro orario dalla tua pagina)." if s.get("da_evento") else ".")
                + " La scheda te la rimando la mattina della call.")
        t, h = [riga], [f"<p>{e(riga)}</p>"]
    else:
        oggetto = f"Cancellata: {az}, {quando_t}"
        riga = (f"{az} ha rifiutato l'invito per la call di {quando_t}." if s.get("perche") == "rifiutata"
                else f"La call con {az} di {quando_t} è stata annullata.")
        t, h = [riga], [f"<p>{e(riga)}</p>"]
    testo = "\n".join(t) + "\n\n(il segnale provvisorio: scrive solo a te)"
    corpo = ("<div style='font-family:-apple-system,Helvetica,Arial,sans-serif;font-size:15px;line-height:1.45;max-width:560px'>"
             + "".join(h) + "<p style='color:#999;font-size:12px'>Il segnale provvisorio: scrive solo a te.</p></div>")
    return " ".join(oggetto.split()), testo, corpo


def prepara(segnali, con_scheda=True):
    """Per ogni segnale: il lead, il nome dell'azienda, e la scheda dove serve (prenotato, mattina)."""
    for s in segnali:
        n = s.get("nota") or {}
        ev = s.get("ev") or {}
        pid = n.get("prospect_id")
        if not pid and ev:
            try:
                pid = _riconosci(ev)
            except Exception as e:                               # noqa: BLE001
                print(f"  (non riesco ad abbinare la prenotazione a un lead: {str(e)[:100]})")
        s["prospect_id"] = pid
        if con_scheda and s["tipo"] in ("prenotato", "mattina"):
            try:
                s["scheda"] = scheda(pid, ev, s.get("invitato") or "")
            except Exception as e:                               # noqa: BLE001
                print(f"  (la scheda non si compone tutta: {str(e)[:100]})")
                chi = _chi_ha_prenotato(ev)
                s["scheda"] = {"abbinata": False, "nome": chi, "ruolo": "", "email": s.get("invitato") or "", "telefoni": [],
                               "attivita": "", "ultima": "", "ultima_il": None, "analisi": None, "sito": "",
                               "azienda": n.get("azienda") or chi or s.get("invitato") or "?", "meet": "", "link": ""}
            s["azienda"] = s["scheda"]["azienda"]
        else:
            s["azienda"] = n.get("azienda") or ""
            if not s["azienda"] and pid:
                p = (sb("GET", f"/rest/v1/prospects?select=company,name&id=eq.{pid}") or [{}])[0]
                s["azienda"] = " ".join((p.get("company") or p.get("name") or "").split())
            s["azienda"] = s["azienda"] or _chi_ha_prenotato(ev) or s.get("invitato") or "?"
    return segnali


def _righe_di(s, come):
    """Le righe del registro per un segnale (la prima e' quella che decide se e' nostro)."""
    base = {"evento": s["evento"], "inizio": _iso(s.get("inizio")), "invitato": s.get("invitato") or None,
            "azienda": s.get("azienda") or None, "prospect_id": s.get("prospect_id"), "come": come}
    righe = [{**base, "chiave": s["chiave"], "tipo": s["tipo"]}]
    if s["tipo"] == "spostata" and s.get("da_evento"):
        # un altro orario preso dalla pagina: la prenotazione nuova e' nota, quella vecchia e' chiusa
        righe.append({**base, "chiave": f"prenotato:{s['evento']}", "tipo": "prenotato"})
        righe.append({**base, "evento": s["da_evento"], "chiave": f"cancellata:{s['da_evento']}", "tipo": "cancellata",
                      "inizio": _iso(s.get("prima")), "come": "assorbita"})
    return righe


def segna_prenotazioni(segnali, come="segnale"):
    """Si segna PRIMA di mandare (al peggio un segnale manca, mai doppio). La chiave e' unica
    nel database: torna solo i segnali segnati da questo giro."""
    righe = [r for s in segnali for r in _righe_di(s, come)]
    if not righe:
        return []
    fatti = sb("POST", "/rest/v1/prenotazioni_segnalate?on_conflict=chiave", righe,
               {"Prefer": "resolution=ignore-duplicates,return=representation"}) or []
    nuove = {x.get("chiave") for x in fatti}
    return [s for s in segnali if s["chiave"] in nuove]


def _chiavi_in(chiavi):
    return "chiave=in.(" + ",".join(urllib.parse.quote(f'"{c}"', safe="") for c in chiavi) + ")"


def togli_prenotazioni(s):
    try:
        sb("DELETE", f"/rest/v1/prenotazioni_segnalate?{_chiavi_in([r['chiave'] for r in _righe_di(s, '')])}")
    except Exception:                                            # noqa: BLE001
        pass


def incerte_prenotazioni(s, oggetto):
    try:
        sb("PATCH", f"/rest/v1/prenotazioni_segnalate?{_chiavi_in([r['chiave'] for r in _righe_di(s, '')])}",
           {"come": "incerto", "oggetto": oggetto}, {"Prefer": "return=minimal"})
    except Exception:                                            # noqa: BLE001
        pass


def risolvi_incerte_prenotazioni():
    """Come per le risposte: una mail forse partita si cerca nella posta inviata prima di rimandarla."""
    righe = sb("GET", "/rest/v1/prenotazioni_segnalate?select=chiave,oggetto,quando&come=eq.incerto") or []
    gruppi = {}
    for x in righe:
        gruppi.setdefault((x.get("oggetto") or "", x.get("quando") or ""), []).append(x["chiave"])
    dubbi = 0
    for (oggetto, il), chiavi in gruppi.items():
        try:
            partita = bool(oggetto) and _gmail_inviata(oggetto, quando(il))
        except Exception as e:                                   # noqa: BLE001
            print(f"  (non riesco a guardare la posta inviata: {str(e)[:100]})")
            dubbi += 1
            continue
        try:
            if partita:
                sb("PATCH", f"/rest/v1/prenotazioni_segnalate?{_chiavi_in(chiavi)}", {"come": "segnale"}, {"Prefer": "return=minimal"})
            else:
                sb("DELETE", f"/rest/v1/prenotazioni_segnalate?{_chiavi_in(chiavi)}")
        except Exception:                                        # noqa: BLE001
            dubbi += 1
        print(f"  incerto «{oggetto}»: " + ("era partita, non la rimando" if partita else "non era partita, la rimando"))
    if dubbi:
        avvisa_ogni("incerti-prenotazioni", "Il segnale provvisorio non sa se una mail su una prenotazione ti è arrivata: guarda il calendario")
    return dubbi


def giro_prenotazioni(prova=None, ora=None, semina=False, tranne=""):
    """Il giro delle prenotazioni. Torna i segnali (mandati, o che si manderebbero in prova).
    `semina`: la prima accensione. Le prenotazioni che ci sono gia' si segnano come note senza
    mandare niente (Dre le conosce), tranne quelle che contengono `tranne`."""
    prova = _a_secco() if prova is None else prova
    ora = ora or adesso()
    if not prova and not semina:
        risolvi_incerte_prenotazioni()
    eventi, cal_ok, mail_ok = raccogli(ora)
    if not cal_ok:
        avvisa_ogni("calendario", "Il segnale provvisorio non riesce a leggere il tuo calendario: le prenotazioni "
                                  "le vedo solo dalle mail «Appuntamento prenotato»" + ("" if mail_ok else ", e anche la posta è ferma"))
    da = _z(ora - datetime.timedelta(days=2))
    righe = sb("GET", f"/rest/v1/prenotazioni_segnalate?select=chiave,tipo,evento,inizio,invitato,azienda,prospect_id,quando,come"
                      f"&or=(inizio.gte.{da},quando.gte.{_z(ora - datetime.timedelta(days=30))})&limit=2000") or []
    segnali = decidi(eventi, righe, ora, calendario_ok=cal_ok)
    if semina:
        if prova:
            raise SystemExit("--semina scrive: non va insieme a --prova")
        nuove = [s for s in segnali if s["tipo"] == "prenotato"
                 and not (tranne and tranne.lower() in ((s["ev"] or {}).get("titolo", "") + " " + (s.get("invitato") or "")).lower())]
        prepara(nuove, con_scheda=False)
        fatte = segna_prenotazioni(nuove, "semina")
        print(f"semina: {len(fatte)} prenotazioni gia' in calendario segnate come note (nessuna mail)")
        return []
    if not segnali:
        print("prenotazioni: niente da segnalare")
        return []
    prepara(segnali)
    if prova:
        for s in segnali:
            oggetto, testo, _ = componi_prenotazione(s)
            print(f"\n(prova) A: {DRE}\n(prova) Oggetto: {oggetto}\n{testo}")
        print(f"\n(prova) prenotazioni: {len(segnali)} segnali: niente mandato, niente segnato")
        return segnali
    segnali = segna_prenotazioni(segnali)
    falliti, dubbi = [], []
    for s in segnali:
        oggetto, testo, corpo = componi_prenotazione(s)
        try:
            manda_mail(DRE, oggetto, testo, corpo)
            print(f"mandata a Dre: {oggetto}")
        except Exception as e:                                   # noqa: BLE001
            if non_partita(e):
                print(f"MAIL NON MANDATA ({oggetto}): {str(e)[:160]}")
                togli_prenotazioni(s)
                falliti.append(s)
            else:
                print(f"MAIL FORSE MANDATA ({oggetto}), Gmail non ha risposto: {str(e)[:160]}")
                incerte_prenotazioni(s, oggetto)
                dubbi.append(s)
    if falliti:
        avvisa_ogni("gmail", f"Il segnale provvisorio non riesce a mandarti la mail: {len(falliti)} prenotazioni da guardare nel calendario")
    if falliti or dubbi:
        raise SystemExit(1)
    return segnali


def costo():
    a, b = PREZZO.get(MODELLO, (0, 0))
    return SPESA["in"] / 1e6 * a + SPESA["out"] / 1e6 * b


def main():
    ore = int(sys.argv[sys.argv.index("--ore") + 1]) if "--ore" in sys.argv else FINESTRA_ORE
    prova_mail = "--prova-mail" in sys.argv
    storico = prova_mail or "--storico" in sys.argv
    if storico and not prova_mail and not _a_secco():
        raise SystemExit("--storico e' una prova sul passato: va con --prova")
    if prova_mail and _a_secco():
        raise SystemExit("--prova-mail manda davvero: non va insieme a --prova (o PROVA=1)")
    semina = "--semina" in sys.argv
    alle = quando(sys.argv[sys.argv.index("--alle") + 1]) if "--alle" in sys.argv else None
    if alle and not alle.tzinfo:
        alle = alle.replace(tzinfo=ROMA)
    if alle and not _a_secco():
        raise SystemExit("--alle sposta l'orologio: si usa solo con --prova")
    if semina and _a_secco():
        raise SystemExit("--semina scrive: non va insieme a --prova")
    solo_pren = "--solo-prenotazioni" in sys.argv or semina or alle is not None
    uscita, segnali, prenotazioni = 0, [], []
    if not _a_secco():
        # la notifica di prova a chi ha appena attivato le notifiche (17/10): un guasto qui non ferma niente
        try:
            from avvisa import benvenuti
            benvenuti()
        except Exception as e:                                   # noqa: BLE001
            print(f"  (prova di notifica ferma: {str(e)[:120]})")
    if not solo_pren:
        try:
            segnali = giro(ore=ore, prova=None if not prova_mail else False, prova_mail=prova_mail, storico=storico)
        except SystemExit as e:
            uscita = e.code if isinstance(e.code, int) else 1
            if isinstance(e.code, str):
                print(e.code)
    if not prova_mail and not storico and not solo_pren:
        # l'unica notifica sul telefono (20/10): il lead entrato in conversazione. Un guasto qui
        # non ferma le mail, e viceversa
        try:
            import conversazioni
            conversazioni.giro()
        except Exception as e:                                   # noqa: BLE001
            print(f"CONVERSAZIONI FERME: {str(e)[:200]}")
            avvisa_ogni("conversazioni", f"Non riesco a vedere chi entra in conversazione: {str(e)[:80]}")
            uscita = uscita or 1
    if not prova_mail and not storico:
        # le prenotazioni delle call: un guasto qui non ferma le risposte, e viceversa
        try:
            prenotazioni = giro_prenotazioni(ora=alle, semina=semina, tranne=sys.argv[sys.argv.index("--tranne") + 1]
                                             if "--tranne" in sys.argv else "")
        except SystemExit as e:
            uscita = uscita or (e.code if isinstance(e.code, int) else 1)
            if isinstance(e.code, str):
                print(e.code)
        except Exception as e:                                   # noqa: BLE001
            print(f"PRENOTAZIONI FERME: {str(e)[:200]}")
            avvisa_ogni("prenotazioni", f"Il segnale provvisorio non riesce a guardare le prenotazioni: {str(e)[:80]}")
            uscita = uscita or 1
    print(f"letture: {GIRO['pagate']} pagate ({SPESA['in']} token dentro, {SPESA['out']} fuori), "
          f"{SPESA['dalla_memoria']} dalla memoria; costo del giro {costo():.4f} $")
    print(f"segnali: {len(segnali)}, prenotazioni: {len(prenotazioni)}")
    if uscita:
        raise SystemExit(uscita)


if __name__ == "__main__":
    main()
