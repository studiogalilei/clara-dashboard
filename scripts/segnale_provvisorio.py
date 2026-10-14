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

COSA FA, a ogni giro (il direttore, ordine 4: dopo sync, prima risposta, bozze e manda)
1. Le risposte dei lead delle ultime 24 ore (interactions email_in) non ancora segnalate.
2. Salta: clienti, pipeline, persi, soppressi, nervosi (stanza.contattabile, la regola
   unica), e le autorisposte ovvie (la regex collaudata di lettura.py, piu' rimbalzi e
   accettazioni del calendario) quando non c'e' un numero di telefono nel testo.
3. Una lettura AI breve per risposta (cervello: la porta OpenAI, gpt-5, sforzo basso;
   la memoria delle letture nel database: la stessa risposta non si ripaga mai).
   Dice: e' CALDO? e' un SI'? la frase chiave, il telefono, un consiglio se serve.
4. Una MAIL A DRE, solo a lui (il controllo e' in manda_mail: qualunque altro
   destinatario fa un'eccezione prima di toccare Gmail):
     CALDO       subito                      «Vuole sentirti: <azienda>»
     SI'         dopo 10 minuti, se non c'e' una nostra risposta ne' una bozza approvata
                                             «Sì da servire: <azienda>»
     DA GUARDARE l'AI non ha risposto: si segnala lo stesso, mai silenzio
   Una volta sola per lead (segnali_provvisori, unica per risposta e per azienda).
   Piu' di 3 nello stesso giro: una mail sola con l'elenco.

COSA NON FA
Mai una mail ai lead. Mai un riprovo pagato: una lettura fallita diventa «da guardare»
e si segna, non si rilegge al giro dopo. Se Gmail non manda, il segnale non si segna
(riparte al giro dopo, gratis: la lettura e' in memoria) e il giro esce in errore.

USO
  python3 scripts/segnale_provvisorio.py                  il giro vero
  python3 scripts/segnale_provvisorio.py --prova          stampa cosa manderebbe, non manda e non segna
  python3 scripts/segnale_provvisorio.py --prova --ore 48 la prova sulle ultime 48 ore, com'e' adesso
  python3 scripts/segnale_provvisorio.py --prova --storico --ore 48
                                   come sarebbe andata: un si' servito tardi (oltre 10 minuti
                                   + il giro del direttore) conta come segnalato
  python3 scripts/segnale_provvisorio.py --prova-mail --ore 48
                                   UNA mail a Dre con l'elenco, oggetto «Prova del segnale
                                   provvisorio», e i segnalati si segnano (non tornano doppi)
"""

import base64
import datetime
import hashlib
import html
import json
import os
import re
import sys
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
OROLOGIO = datetime.timedelta(minutes=20)   # il direttore passa ogni 20 minuti (direttore.yml)
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


def adesso():
    return datetime.datetime.now(datetime.timezone.utc)


def _z(t):
    return t.astimezone(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


# ── la mail: a Dre e basta ─────────────────────────────────────────

def manda_mail(a, oggetto, testo, html_corpo):
    """L'UNICA strada verso Gmail. Il destinatario puo' essere solo Dre: qualunque altro
    indirizzo (un lead, un collega, una lista) si ferma qui, prima di chiamare Google."""
    if (a or "").strip().lower() != DRE:
        raise ValueError(f"il segnale provvisorio scrive solo a Dre, non a {a!r}")
    m = MIMEMultipart("alternative")
    m["To"] = DRE
    m["From"] = DRE
    m["Subject"] = str(Header(oggetto, "utf-8"))
    m.attach(MIMEText(testo, "plain", "utf-8"))
    m.attach(MIMEText(html_corpo, "html", "utf-8"))
    grezzo = base64.urlsafe_b64encode(m.as_bytes()).decode()
    return _gmail_send(grezzo)


def _gmail_send(grezzo):
    from google_api import g
    return g("POST", "https://gmail.googleapis.com/gmail/v1/users/me/messages/send", {"raw": grezzo}, email=DRE)


# ── la lettura AI, con memoria e contatore ─────────────────────────

def _chiave(azienda, testo):
    base = "\x00".join((VERSIONE, MODELLO, DOMANDA, azienda or "", " ".join((testo or "").split())))
    return "segnale:" + hashlib.sha256(base.encode("utf-8")).hexdigest()[:24]


def _conta(modello, dentro, fuori):
    """Il contatore della spesa (uso_modelli), anche in prova: i soldi spesi sono veri."""
    SPESA["in"] += int(dentro or 0)
    SPESA["out"] += int(fuori or 0)
    SPESA["chiamate"] += 1
    try:
        sb("POST", "/rest/v1/uso_modelli", {"script": "segnale_provvisorio.py", "scopo": "segnale provvisorio",
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


def telefono_nel_testo(testo):
    """Il primo numero di telefono plausibile nel testo (rete per quando l'AI non c'e')."""
    for m in TELEFONO.finditer(testo or ""):
        c = _cifre(m.group(0))
        if 9 <= len(c) <= 13:
            return m.group(0).strip()
    return ""


def leggi(azienda, testo):
    """Una lettura per risposta, una volta sola nella vita. None = l'AI non ha risposto."""
    chiave = _chiave(azienda, testo)
    try:
        r = sb("GET", f"/rest/v1/memoria_letture?select=valore&chiave=eq.{chiave}") or []
        if r and isinstance(r[0].get("valore"), dict):
            SPESA["dalla_memoria"] += 1
            return r[0]["valore"]
    except Exception:                                            # noqa: BLE001
        pass
    try:
        grezzo = _chiedi_ai(DOMANDA.format(azienda=azienda or "?", testo=(testo or "")[:3000]))
        m = re.search(r"\{.*\}", grezzo or "", re.S)
        v = json.loads(m.group(0)) if m else None
    except Exception as e:                                       # noqa: BLE001
        print(f"  (l'AI non ha risposto: {str(e)[:100]})")
        return None
    if not isinstance(v, dict) or not all(isinstance(v.get(k), bool) for k in ("autorisposta", "caldo", "si")):
        return None
    # il telefono deve stare davvero nel testo: un numero inventato e' peggio di nessun numero
    tel = (v.get("telefono") or "").strip()
    primo = TELEFONO.search(tel)              # «Tel. 0422 918652 - Tel. 0422 1847161»: il primo e basta
    tel = primo.group(0).strip() if primo else tel
    if tel and (len(_cifre(tel)) < 8 or _cifre(tel)[-8:] not in _cifre(testo)):
        tel = ""
    v["telefono"] = tel
    try:                     # la memoria si scrive anche in prova: e' una lettura gia' pagata, non un gesto
        sb("POST", "/rest/v1/memoria_letture?on_conflict=chiave", [{"chiave": chiave, "valore": v}],
           {"Prefer": "resolution=merge-duplicates,return=minimal"})
    except Exception:                                            # noqa: BLE001
        pass
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
    """Le risposte della finestra, una per azienda (l'ultima), con la scheda e i gia' segnalati tolti."""
    da = _z(adesso() - datetime.timedelta(hours=ore))
    righe = sb("GET", f"/rest/v1/interactions?select=id,prospect_id,at,created_at,body&kind=eq.email_in"
                      f"&at=gte.{da}&prospect_id=not.is.null&order=at.asc&limit=1000") or []
    if not righe:
        return []
    pids = sorted({r["prospect_id"] for r in righe})
    gia = set()
    schede = {}
    for i in range(0, len(pids), 80):
        pezzo = ",".join(pids[i:i + 80])
        for s in sb("GET", f"/rest/v1/segnali_provvisori?select=prospect_id&prospect_id=in.({pezzo})") or []:
            gia.add(s["prospect_id"])
        for p in sb("GET", f"/rest/v1/prospects?select=id,company,name,email,phone,fuori,stage,pipeline_stage,"
                           f"no_followup,classificazione&id=in.({pezzo})") or []:
            schede[p["id"]] = p
    per_azienda = {}
    for r in righe:
        if r["prospect_id"] in gia or r["prospect_id"] not in schede:
            continue
        per_azienda.setdefault(r["prospect_id"], []).append(r)
    return [(schede[pid], rr) for pid, rr in per_azienda.items()]


def valuta(p, risposte, ora, storico=False):
    """Il segnale per un'azienda, o None. Legge dalla piu' recente: la prima che dice qualcosa vince.
    `storico`: la prova sul passato. Un si' conta come servito solo se lo e' stato entro il giro
    che l'avrebbe segnalato (10 minuti di attesa + 20 di orologio del direttore), non dopo."""
    if not contattabile(p):
        return None
    for r in sorted(risposte, key=lambda x: x.get("at") or "", reverse=True):
        corpo = r.get("body") or ""
        if automatica(corpo):
            continue
        testo = solo_suo(corpo, con_firma=True) or corpo
        letto = leggi(p.get("company") or p.get("name"), testo) if testo.strip() and not testo.lower().startswith("risposta ricevuta") else None
        base = {"interaction_id": r["id"], "prospect_id": p["id"], "azienda": p.get("company") or p.get("name") or "?",
                "persona": p.get("name") or "", "email": p.get("email") or "", "at": r.get("at")}
        if letto is None:
            return {**base, "tipo": "da_guardare", "frase": " ".join(solo_suo(corpo).split())[:160],
                    "telefono": telefono_nel_testo(testo), "consiglio": "L'AI non ha letto questa risposta: aprila tu."}
        if letto.get("autorisposta"):
            continue
        dati = {**base, "frase": letto.get("frase") or "", "telefono": letto.get("telefono") or "",
                "consiglio": letto.get("consiglio") or ""}
        if letto.get("caldo"):
            return {**dati, "tipo": "caldo"}
        if letto.get("si"):
            visto = max(quando(r["at"]), quando(r.get("created_at") or r["at"]))
            if ora - visto < ATTESA_SI:
                return {**dati, "tipo": "attesa"}            # il sistema ha ancora qualche minuto
            if p.get("stage") == "call_fissata":
                return None                                  # la call c'e' gia': un si' qui non e' da servire (visto il 13/10)
            servito = primo_servizio(p["id"], quando(r["at"]))
            if servito and (not storico or servito <= visto + ATTESA_SI + OROLOGIO):
                return None
            return {**dati, "tipo": "si", "servito_il": servito}
        return None                                          # un no, un rinvio, una domanda: il resto lo fa il sistema
    return None


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
    """Una volta sola per risposta e per azienda: il database lo garantisce (unique)."""
    return sb("POST", "/rest/v1/segnali_provvisori?on_conflict=prospect_id",
              [{"interaction_id": s["interaction_id"], "prospect_id": s["prospect_id"], "tipo": s["tipo"], "come": come}
               for s in segnali], {"Prefer": "resolution=ignore-duplicates,return=minimal"})


def togli(segnali):
    for s in segnali:
        try:
            sb("DELETE", f"/rest/v1/segnali_provvisori?interaction_id=eq.{s['interaction_id']}")
        except Exception:                                        # noqa: BLE001
            pass


def giro(ore=FINESTRA_ORE, prova=None, prova_mail=False, storico=False):
    """Il giro intero. Torna i segnali (mandati, o che si manderebbero in prova)."""
    prova = _a_secco() if prova is None else prova
    ora = adesso()
    segnali, attese = [], 0
    for p, risposte in candidati(ore):
        s = valuta(p, risposte, ora, storico=storico)
        if not s:
            continue
        if s["tipo"] == "attesa":
            attese += 1
            continue
        segnali.append(s)
    segnali.sort(key=_ordine)
    if not segnali:
        print(f"niente da segnalare ({attese} si' ancora nei 10 minuti)" if attese else "niente da segnalare")
        return []
    if prova_mail:
        aperti = sum(1 for s in segnali if not s.get("servito_il"))
        mail = [componi(segnali, oggetto="Prova del segnale provvisorio", intro=(
            f"La prova: ecco cosa ti avrei segnalato nelle ultime {ore} ore. {aperti} sono ancora aperti, in cima; "
            "quelli con «servito dopo» erano già sistemati e servono solo a vedere quando ti sarebbe arrivata la mail. "
            "Da adesso arriva da sola: subito per chi vuole sentirti, dopo 10 minuti per un sì rimasto senza risposta. "
            "Questi non te li rimando."))]
    elif len(segnali) > TANTI:
        mail = [componi(segnali)]
    else:
        mail = [componi([s]) for s in segnali]
    if prova:
        for oggetto, testo, _ in mail:
            print(f"\n(prova) A: {DRE}\n(prova) Oggetto: {oggetto}\n{testo}")
        print(f"\n(prova) {len(segnali)} segnali, {len(mail)} mail: niente mandato, niente segnato")
        return segnali
    # si segna PRIMA di mandare: se il giro muore a meta', al peggio un segnale manca, mai doppio
    segna(segnali, "prova" if prova_mail else "segnale")
    gruppi = [segnali] if (prova_mail or len(segnali) > TANTI) else [[s] for s in segnali]
    falliti = []
    for (oggetto, testo, corpo), gruppo in zip(mail, gruppi):
        try:
            manda_mail(DRE, oggetto, testo, corpo)
            print(f"mandata a Dre: {oggetto}")
        except Exception as e:                                   # noqa: BLE001
            print(f"MAIL NON MANDATA ({oggetto}): {str(e)[:160]}")
            togli(gruppo)                                        # al giro dopo riparte, la lettura e' in memoria
            falliti += gruppo
    if falliti:
        try:
            from avvisa import avvisa
            avvisa(f"Il segnale provvisorio non riesce a mandarti la mail: {len(falliti)} lead da guardare in Master Inbox",
                   titolo="Segnale provvisorio")
        except Exception:                                        # noqa: BLE001
            pass
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
    segnali = giro(ore=ore, prova=None if not prova_mail else False, prova_mail=prova_mail, storico=storico)
    print(f"letture: {SPESA['chiamate']} pagate ({SPESA['in']} token dentro, {SPESA['out']} fuori), "
          f"{SPESA['dalla_memoria']} dalla memoria; costo del giro {costo():.4f} $")
    print(f"segnali: {len(segnali)}")


if __name__ == "__main__":
    main()
