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

COSA NON FA
Mai una mail ai lead. Mai un riprovo pagato: una lettura fallita si scrive in memoria
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
from stanza import sb, contattabile, quando, _a_secco           # noqa: E402
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
# indirizzi dismessi e accettazioni del calendario (viste il 13/10)
AUTOMATICHE = re.compile(r"^\s*(accettato|accepted|rifiutato|declined)\s*:|recapito non (e'|è) riuscito|undeliverable|"
                         r"delivery status notification|mail delivery (failed|subsystem)|mancata consegna|"
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
- caldo: true SOLO se vuole sentirsi: chiede di essere chiamata o di parlarne, propone un giorno o un
  orario, lascia un numero perche' la si chiami, oppure e' molto carica ed entusiasta. Un semplice
  «si', mandi pure l'analisi» NON e' caldo. Un numero che sta solo nella firma standard non basta.
  Se conferma soltanto un appuntamento che ha gia' prenotato da sola, NON e' caldo: e' gia' a posto.
- si: true se vuole o accetta l'analisi o il materiale, anche solo con «confermo la mail», «la mail
  e' corretta», «mandi pure», «va bene», «valutiamo», «si' grazie», «se vuole inoltrarla».
  false se dice no, rimanda a piu' avanti, chiede di non scrivere, o chiede solo chi siamo.
- frase: la sua frase chiave, copiata dal testo, al massimo 15 parole.
- telefono: UN solo numero di telefono suo o dell'azienda (il cellulare, se c'e') se compare nel testo
  o nella firma, copiato com'e'; altrimenti stringa vuota. Mai inventarlo.
- consiglio: una riga per Dre SOLO se serve qualcosa di non ovvio (es. «propone mercoledi' mattina:
  chiamalo prima delle 10», «ci rimanda a un altro indirizzo: scrivi li'»); altrimenti stringa vuota.

L'AZIENDA: {azienda}
LA RISPOSTA:
«{testo}»"""

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
    from avvisa import avvisa
    return avvisa(testo, titolo="Segnale provvisorio")


def avvisa_ogni(motivo, testo):
    """La notifica di un guasto, non piu' di una ogni 2 ore per lo stesso motivo (Gmail ferma
    non deve suonare a ogni giro). Se la memoria non risponde si avvisa lo stesso."""
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


def _chiedi_ai(prompt):
    """La porta OpenAI di sempre (cervello._chiedi_openai), col contatore di questo script."""
    import cervello
    vero = cervello._conta_uso
    cervello._conta_uso = _conta
    try:
        return cervello._chiedi_openai(prompt, MODELLO, formato=SCHEMA, fornitore="openai", tetto=TETTO, sforzo=SFORZO)
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
        grezzo = _chiedi_ai(DOMANDA.format(azienda=azienda or "?", testo=(testo or "")[:3000]))
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
    segnali = giro(ore=ore, prova=None if not prova_mail else False, prova_mail=prova_mail, storico=storico)
    print(f"letture: {GIRO['pagate']} pagate ({SPESA['in']} token dentro, {SPESA['out']} fuori), "
          f"{SPESA['dalla_memoria']} dalla memoria; costo del giro {costo():.4f} $")
    print(f"segnali: {len(segnali)}")


if __name__ == "__main__":
    main()
