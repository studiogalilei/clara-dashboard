#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""L'ISPETTORE (Dre, 12/10/2026: «un agente che si assicuri della coerenza e della
qualita' dei nostri messaggi, che e' su Smartlead pero' non su Clara, che vede li' gli
inviati, un monitoraggio della qualita' e che nulla si rompa»; e poco dopo: «che magari
mi danno anche consigli su come aumentare il tasso di risposta»).

PERCHE' SERVE
La sentinella guarda il MOTORE (Clara ferma, risposte senza esito). Il Revisore guarda
le BOZZE prima che partano. Nessuno guardava cosa e' USCITO davvero: le sequenze che
Smartlead manda da sola, le risposte scritte a mano dalla casella, le caselle staccate,
i rimbalzi. I guasti peggiori dell'outbound sono nati li': la mail al cliente finito in
un'altra campagna, il follow-up a chi aveva gia' risposto, la riga del potenziale persa
a luglio senza che nessuno se ne accorgesse per tre mesi (risposte dopo l'analisi dal
21% all'8-15%).

COSA FA (legge e basta: su Smartlead non scrive niente, le campagne le tocca Dre)
Ogni ora, dalle 8 alle 21:
  - rilegge ogni messaggio partito dalle campagne attive e ogni risposta nostra dei
    fili (quelli che il sync porta in interactions, scritti da Clara o a mano);
  - GRAVE: sequenza a un cliente, a chi e' in pipeline o a chi ha detto no; testo con
    segnaposto o pezzi vuoti; casella scollegata; due mail nostre alla stessa persona
    in un quarto d'ora;
  - ATTENZIONE: follow-up di sequenza dopo una risposta; la stessa persona in due
    campagne; una campagna attiva che oggi non manda; rimbalzi oltre il 2%; caselle con
    reputazione bassa; una risposta arrivata su Smartlead che Clara non ha visto; la
    mail dell'analisi senza la riga del potenziale o con un numero diverso dal mercato.
Una volta al giorno (dalle 18): la pagella. Un modello rilegge ogni risposta nostra
accanto al messaggio a cui risponde e dice se e' coerente; con i numeri del giorno.
Il lunedi': i consigli. Numeri delle campagne per passo e variante, i testi delle
sequenze, il tasso di risposta dopo l'analisi: tre cose concrete da cambiare, ognuna
col dato che la giustifica e il modo di misurarla.

Ogni guaio si dice UNA volta (lo stato sta nel bucket riservato): niente Posta piena
di avvisi uguali. Se c'e' un guaio grave il workflow diventa rosso.

USO
  python3 scripts/ispettore.py              controlla (e pagella/consigli quando e' ora)
  python3 scripts/ispettore.py --prova      stampa e basta: niente Posta, niente stato
  python3 scripts/ispettore.py --pagella    forza la pagella
  python3 scripts/ispettore.py --consigli   forza i consigli
  python3 scripts/ispettore.py --semina     il primo avvio: segna come gia' detti i guai di adesso
                                            (sono il passato, Dre li sa), da li' avvisa solo i nuovi
"""
import collections
import datetime
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request
import zoneinfo

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from stanza import sb, sb_tutte, di_clara, env              # noqa: E402

PROVA = "--prova" in sys.argv or os.environ.get("PROVA") == "1"
ADESSO = datetime.datetime.now(datetime.timezone.utc)
ROMA = zoneinfo.ZoneInfo("Europe/Rome")
ORA_ROMA = ADESSO.astimezone(ROMA)
SL = "https://server.smartlead.ai/api/v1"
STATO = "ispettore/stato.json"
PIPELINE = ("call_fissata", "cliente")
HA_DETTO_NO = ("negativo", "soppresso", "nervoso", "fuori_target")
MODELLO = "gpt-5-mini"        # una chiamata al giorno e una a settimana: centesimi
RIDIRE_DOPO_ORE = 24          # lo stesso guaio si ripete in Posta solo dopo un giorno
SOGLIA_RIMBALZI = 0.02     # Playbook Deliverability (Ali): rimbalzi sotto il 2%
GENERICI = re.compile(r"@(gmail|libero|hotmail|outlook|yahoo|virgilio|alice|tiscali|live|icloud|fastwebnet|tin|email)\.", re.I)
LINK = re.compile(r"https?://|www\.|<a\s", re.I)
# un messaggio con questi pezzi non doveva partire
ROTTO = [
    (re.compile(r"\{\{|\}\}|\{[a-z_]+\}"), "segnaposto non riempito"),
    (re.compile(r"\b(undefined|None|null|NaN)\b"), "un valore vuoto scritto come parola"),
    (re.compile(r"\[(nome|azienda|citt[aà]|settore|name|company)[^\]]*\]", re.I), "segnaposto fra parentesi"),
    (re.compile(r"%[a-z_]+%", re.I), "segnaposto fra percentuali"),
    # «su , notando» o un oggetto che finisce in «su»: il nome dell'azienda era vuoto. Minuscole e con lo
    # spazio prima della punteggiatura: «per A.R. Living» e «di C.D.A.» sono sigle, non buchi (12/10)
    (re.compile(r"(?<![\w.])(su|di|per|a|ad)\s+[,.!?;:]|(?<![\w.])(su|di|per|ad)\s*$"), "una parola rimasta senza il nome dopo"),
]


# ── Smartlead, sola lettura ─────────────────────────────────────────
def _chiave_sl():
    k = env("SMARTLEAD_API_KEY")
    if k:
        return k.strip().strip("\"'")
    p = os.path.expanduser("~/.hermes/config.yaml")
    for riga in (open(p) if os.path.exists(p) else []):
        m = re.match(r"\s*SMARTLEAD_API_KEY:\s*(\S+)", riga)
        if m:
            return m.group(1).strip("\"'")
    sys.exit("manca SMARTLEAD_API_KEY")


def sl(percorso, volte=5):
    """Solo GET: l'Ispettore guarda, non tocca (le campagne le tocca Dre)."""
    url = f"{SL}{percorso}{'&' if '?' in percorso else '?'}api_key={_chiave_sl()}"
    for i in range(volte):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "odyn-ispettore"}), timeout=90) as r:
                return json.loads(r.read())
        except Exception as e:                               # noqa: BLE001
            if i == volte - 1:
                raise RuntimeError(f"Smartlead non risponde su {percorso.split('?')[0]}: {str(e)[:80]}")
            time.sleep(2 * (i + 1))


def campagne_attive():
    return [c for c in (sl("/campaigns/") or []) if c.get("status") == "ACTIVE"]


def inviati(campagna):
    """Tutti i messaggi partiti da una campagna (Smartlead non li ordina ne' li filtra per data)."""
    righe, da = [], 0
    while True:
        pezzo = (sl(f"/campaigns/{campagna['id']}/statistics?limit=1000&offset={da}") or {}).get("data") or []
        for r in pezzo:
            r["_campagna"] = campagna["name"]
            r["_cid"] = campagna["id"]
        righe += pezzo
        if len(pezzo) < 1000:
            return righe
        da += 1000


# ── il bucket riservato: lo stato e i rapporti ──────────────────────
def _bucket(metodo, nome, corpo=None):
    k = env("SUPABASE_SERVICE_KEY") or env("SUPABASE_SERVICE_ROLE_KEY")
    h = {"apikey": k, "Authorization": f"Bearer {k}"}
    if corpo is not None:
        h.update({"Content-Type": "application/json", "x-upsert": "true"})
    req = urllib.request.Request(f"{env('VITE_SUPABASE_URL').rstrip('/')}/storage/v1/object/vault/riservato/{nome}",
                                 method=metodo, headers=h,
                                 data=json.dumps(corpo, ensure_ascii=False).encode() if corpo is not None else None)
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read()


def leggi_stato():
    try:
        return json.loads(_bucket("GET", STATO) or b"{}")
    except Exception:                                        # noqa: BLE001
        return {}


def salva(nome, dati):
    if PROVA:
        return
    try:
        _bucket("POST", nome, dati)
    except Exception:                                        # noqa: BLE001
        _bucket("PUT", nome, dati)


# ── utilita' ────────────────────────────────────────────────────────
def quando(iso):
    try:
        t = datetime.datetime.fromisoformat(str(iso).replace("Z", "+00:00"))
        return t if t.tzinfo else t.replace(tzinfo=datetime.timezone.utc)
    except Exception:                                        # noqa: BLE001
        return None


def pulito(html):
    t = re.sub(r"(?is)<(style|script)[^>]*>.*?</\1>", " ", str(html or ""))
    t = re.sub(r"(?i)<br\s*/?>|</p>|</div>", "\n", t)
    t = re.sub(r"<[^>]+>", " ", t)
    t = re.sub(r"&nbsp;", " ", t)
    return re.sub(r"[ \t]+", " ", t).strip()


def senza_citazione(testo):
    """Solo il pezzo scritto ora, non il filo citato sotto."""
    return re.split(r"\n\s*(?:Il giorno .{5,80} ha scritto|On .{5,80} wrote|-{2,} ?Messaggio originale|Da: .+\n)", testo)[0]


def dominio(mail):
    m = re.search(r"@([^@\s>]+)$", str(mail or "").strip().lower())
    return m.group(1) if m else ""


def testo_rotto(oggetto, corpo):
    """I pezzi che dicono «questo messaggio e' uscito rotto». Solo il testo nostro, non la firma."""
    t = senza_citazione(pulito(corpo)).split("Business Development, Studio Galilei")[0]
    trovati = []
    for rx, cosa in ROTTO:
        for pezzo, dove in ((oggetto or "", "nell'oggetto"), (t, "nel testo")):
            m = rx.search(pezzo)
            if m:
                trovati.append(f"{cosa} {dove} («{pezzo[max(0, m.start() - 25):m.end() + 10].strip()}»)")
                break
    if oggetto is not None and not str(oggetto).strip():
        trovati.append("oggetto vuoto")
    return trovati


# ── i lead del database, per indirizzo ──────────────────────────────
def lead_per_mail():
    righe = sb_tutte("/rest/v1/prospects?select=id,company,email,email_alt,stage,classificazione,fuori,no_followup,"
                     "last_reply_at,campaign_id")
    clienti = {r["prospect_id"] for r in (sb("GET", "/rest/v1/clienti?select=prospect_id,stato&stato=neq.chiuso") or [])}
    per, dom_clienti = {}, set()
    for p in righe:
        p["_cliente"] = p["id"] in clienti or p.get("stage") == "cliente"
        for m in [p.get("email")] + list(p.get("email_alt") or []):
            if m:
                per[str(m).strip().lower()] = p
                if p["_cliente"] and not GENERICI.search(str(m)):
                    dom_clienti.add(dominio(m))
    dom_clienti.discard("")
    return per, dom_clienti


def nome(p, mail):
    return (p or {}).get("company") or mail


# ── i controlli ─────────────────────────────────────────────────────
def controlla_sequenze(righe, per, dom_clienti, da):
    """Ogni messaggio di sequenza partito dopo `da`."""
    gravi, attenzione = [], []
    for r in righe:
        t = quando(r.get("sent_time"))
        if not t or t < da:
            continue
        mail = str(r.get("lead_email") or "").strip().lower()
        p = per.get(mail)
        chi = nome(p, mail)
        passo = r.get("sequence_number") or 1
        dove = f"«{r['_campagna'][:40]}», passo {passo}"
        for x in testo_rotto(r.get("email_subject"), r.get("email_message")):
            gravi.append((f"rotto:{r.get('stats_id')}", f"{chi}: partito con {x} ({dove})"))
        if passo == 1 and LINK.search(str(r.get("email_message") or "").split("Business Development, Studio Galilei")[0]):
            attenzione.append((f"link:{r['_cid']}:{t.date()}", f"«{r['_campagna'][:40]}»: la prima mail contiene un link o un'immagine (playbook: mai link o PDF nella prima mail, finisce in spam)"))
        if p and p["_cliente"]:
            gravi.append((f"cliente:{mail}:{passo}", f"{chi} e' un CLIENTE e ha ricevuto la sequenza ({dove})"))
        elif dominio(mail) in dom_clienti:
            gravi.append((f"dominio:{mail}:{passo}", f"{chi}: stessa azienda di un cliente ({dominio(mail)}), ha ricevuto la sequenza ({dove})"))
        elif p and p.get("stage") in PIPELINE:
            gravi.append((f"pipeline:{mail}:{passo}", f"{chi} e' in pipeline ({p['stage']}) e ha ricevuto la sequenza ({dove})"))
        elif p and (p.get("classificazione") in HA_DETTO_NO or p.get("fuori")):
            gravi.append((f"no:{mail}:{passo}", f"{chi} aveva detto no ({p.get('classificazione') or 'fuori'}) e ha ricevuto la sequenza ({dove})"))
        elif p and passo >= 2 and quando(p.get("last_reply_at")) and quando(p["last_reply_at"]) < t:
            attenzione.append((f"dopo_risposta:{mail}:{passo}", f"{chi}: follow-up di sequenza partito DOPO che aveva risposto ({dove})"))
        elif p and passo >= 2 and p.get("no_followup"):
            attenzione.append((f"nofollow:{mail}:{passo}", f"{chi}: segnato «niente follow-up» ma la sequenza e' andata avanti ({dove})"))
    # la stessa persona in due campagne negli ultimi 30 giorni
    trenta = ADESSO - datetime.timedelta(days=30)
    dove_sta = collections.defaultdict(set)
    for r in righe:
        t = quando(r.get("sent_time"))
        if t and t >= trenta:
            dove_sta[str(r.get("lead_email") or "").lower()].add(r["_campagna"][:30])
    for mail, cc in dove_sta.items():
        if len(cc) > 1:
            attenzione.append((f"doppia:{mail}", f"{nome(per.get(mail), mail)} sta in {len(cc)} campagne insieme: {', '.join(sorted(cc))}"))
    return gravi, attenzione


def controlla_risposte(per_id, da):
    """Le risposte nostre dei fili (Clara o a mano dalla casella), partite dopo `da`."""
    import mercato
    gravi, attenzione = [], []
    fuori = sb_tutte(f"/rest/v1/interactions?select=id,prospect_id,at,body,casella&kind=eq.email_out"
                     f"&at=gte.{urllib.parse.quote(da.isoformat())}")
    per_lead = collections.defaultdict(list)
    for x in fuori:
        per_lead[x["prospect_id"]].append(x)
    for pid, xs in per_lead.items():
        p = per_id.get(pid) or {}
        chi = p.get("company") or "un lead"
        xs.sort(key=lambda x: x["at"])
        for a, b in zip(xs, xs[1:]):
            if (quando(b["at"]) - quando(a["at"])).total_seconds() < 900:
                gravi.append((f"doppio:{b['id']}", f"{chi}: due mail nostre in {int((quando(b['at']) - quando(a['at'])).total_seconds() // 60)} minuti"))
        for x in xs:
            corpo = senza_citazione(pulito(x.get("body")))
            for r in testo_rotto(None, x.get("body")):
                gravi.append((f"rotto:{x['id']}", f"{chi}: risposta partita con {r}"))
            if "breve presentazione dei nostri servizi" in corpo or "vasto range di servizi" in corpo:
                if "vasto range" in corpo or "però è centrata" in corpo:
                    attenzione.append((f"analisi_vecchia:{x['id']}", f"{chi}: la mail dell'analisi e' partita col testo VECCHIO (senza la riga del potenziale)"))
                frase, n = mercato.dato_di(p) if p else (None, None)
                numeri = {int(v.replace(".", "")) for v in re.findall(r"circa ([\d.]+) ricerche al mese", corpo)}
                if numeri and frase and n not in numeri:
                    attenzione.append((f"numero:{x['id']}", f"{chi}: nella mail dell'analisi c'e' {sorted(numeri)[0]} ricerche al mese, il mercato oggi dice {n}"))
    return gravi, attenzione, fuori


def controlla_salute(campagne, righe, per):
    gravi, attenzione = [], []
    for c in (sl("/email-accounts/?offset=0&limit=100") or []):
        casella = c.get("from_email") or c.get("username")
        if c.get("is_smtp_success") is False or c.get("is_imap_success") is False:
            errore = c.get("smtp_failure_error") or c.get("imap_failure_error") or ""
            gravi.append((f"casella:{casella}", f"la casella {casella} e' SCOLLEGATA ({'invio' if c.get('is_smtp_success') is False else 'ricezione'}): {str(errore)[:80]}"))
            continue
        w = c.get("warmup_details") or {}
        if w.get("blocked_reason"):
            attenzione.append((f"warmup:{casella}", f"la casella {casella} ha il warmup bloccato: {str(w['blocked_reason'])[:80]}"))
        rep = re.sub(r"[^\d.]", "", str(w.get("warmup_reputation") or ""))
        if rep and float(rep) < 90 and c.get("is_connected_to_campaign"):
            attenzione.append((f"reputazione:{casella}", f"la casella {casella} ha la reputazione al {rep}%: sotto il 90 le mail iniziano a finire in spam"))
    # campagne attive che oggi non mandano (giorni feriali, dalle 11)
    oggi = ORA_ROMA.date()
    if ORA_ROMA.weekday() < 5 and ORA_ROMA.hour >= 11:
        per_c = collections.Counter(r["_cid"] for r in righe if quando(r.get("sent_time")) and quando(r["sent_time"]).astimezone(ROMA).date() == oggi)
        for c in campagne:
            if not per_c.get(c["id"]):
                attenzione.append((f"ferma:{c['id']}:{oggi}", f"la campagna «{c['name'][:45]}» e' attiva ma oggi non ha mandato niente"))
    # rimbalzi degli ultimi 7 giorni
    sette = ADESSO - datetime.timedelta(days=7)
    for c in campagne:
        rr = [r for r in righe if r["_cid"] == c["id"] and quando(r.get("sent_time")) and quando(r["sent_time"]) >= sette]
        rb = sum(1 for r in rr if r.get("is_bounced"))
        if len(rr) >= 100 and rb / len(rr) > SOGLIA_RIMBALZI:
            attenzione.append((f"rimbalzi:{c['id']}:{oggi}", f"«{c['name'][:45]}»: {rb} rimbalzi su {len(rr)} in 7 giorni ({rb * 100 / len(rr):.1f}%, sopra il 2% la consegna peggiora per tutte le caselle)"))
    # risposte arrivate su Smartlead che Clara non ha visto
    giorno = ADESSO - datetime.timedelta(hours=24)
    for r in righe:
        t = quando(r.get("reply_time"))
        if not t or t < giorno or (ADESSO - t).total_seconds() < 3600:
            continue
        mail = str(r.get("lead_email") or "").lower()
        p = per.get(mail)
        if not p:
            attenzione.append((f"risposta_orfana:{mail}", f"{mail} ha risposto su Smartlead ({r['_campagna'][:30]}) ma non e' nel Workspace"))
            continue
        visto = sb("GET", f"/rest/v1/interactions?select=id&prospect_id=eq.{p['id']}&kind=eq.email_in"
                          f"&at=gte.{urllib.parse.quote((t - datetime.timedelta(minutes=15)).isoformat())}&limit=1")
        if not visto:
            attenzione.append((f"non_vista:{mail}:{t.date()}", f"{nome(p, mail)} ha risposto su Smartlead alle {t.astimezone(ROMA):%H:%M} e Clara non l'ha ancora vista"))
    return gravi, attenzione


# ── i numeri ────────────────────────────────────────────────────────
def numeri(campagne, righe, fuori_28):
    """Inviati, risposte e tasso per campagna e passo; il tasso di risposta dopo l'analisi."""
    sette, ventotto = ADESSO - datetime.timedelta(days=7), ADESSO - datetime.timedelta(days=28)
    oggi = ORA_ROMA.date()
    out = {"quando": ADESSO.isoformat(), "campagne": [], "oggi": {"inviati": 0, "risposte": 0}}
    for c in campagne:
        rr = [r for r in righe if r["_cid"] == c["id"]]
        voce = {"nome": c["name"], "passi": {}}
        for finestra, da in (("7g", sette), ("28g", ventotto)):
            xs = [r for r in rr if quando(r.get("sent_time")) and quando(r["sent_time"]) >= da]
            # una persona conta una volta: ha risposto a qualunque passo
            persone = {str(r.get("lead_email")).lower() for r in xs if r.get("sequence_number") == 1}
            risposto = {str(r.get("lead_email")).lower() for r in rr if r.get("reply_time")} & persone
            voce[finestra] = {"nuovi": len(persone), "risposte": len(risposto),
                              "tasso": round(len(risposto) * 100 / len(persone), 2) if persone else None,
                              "rimbalzi": sum(1 for r in xs if r.get("is_bounced"))}
        for passo in sorted({r.get("sequence_number") or 1 for r in rr}):
            xs = [r for r in rr if (r.get("sequence_number") or 1) == passo and quando(r.get("sent_time")) and quando(r["sent_time"]) >= ventotto]
            rp = sum(1 for r in xs if quando(r.get("reply_time")) and quando(r["reply_time"]) >= quando(r["sent_time"]))
            varianti = collections.Counter(str(r.get("seq_variant_id")) for r in xs)
            voce["passi"][str(passo)] = {"inviati_28g": len(xs), "risposte_dopo": rp, "varianti": dict(varianti)}
        out["oggi"]["inviati"] += sum(1 for r in rr if quando(r.get("sent_time")) and quando(r["sent_time"]).astimezone(ROMA).date() == oggi)
        out["oggi"]["risposte"] += sum(1 for r in rr if quando(r.get("reply_time")) and quando(r["reply_time"]).astimezone(ROMA).date() == oggi)
        out["campagne"].append(voce)
    # dopo l'analisi: chi la riceve risponde entro 7 giorni? (giugno 21%, luglio-ottobre 8-15%)
    analisi = [x for x in fuori_28 if "breve presentazione dei nostri servizi" in (x.get("body") or "")
               or "vasto range di servizi" in (x.get("body") or "")]
    maturi = [x for x in analisi if (ADESSO - quando(x["at"])).days >= 7]
    risposero = 0
    for x in maturi:
        t = quando(x["at"])
        if sb("GET", f"/rest/v1/interactions?select=id&prospect_id=eq.{x['prospect_id']}&kind=eq.email_in"
                     f"&at=gt.{urllib.parse.quote(t.isoformat())}&at=lt.{urllib.parse.quote((t + datetime.timedelta(days=7)).isoformat())}&limit=1"):
            risposero += 1
    out["dopo_analisi"] = {"mandate_28g": len(analisi), "misurabili": len(maturi), "risposte_7g": risposero,
                           "tasso": round(risposero * 100 / len(maturi), 1) if maturi else None, "giugno": 21.0}
    return out


# ── la pagella e i consigli (il modello legge, il codice decide cosa dire) ──
SCHEMA_PAGELLA = {"type": "json_schema", "json_schema": {"name": "pagella", "strict": True, "schema": {
    "type": "object", "additionalProperties": False, "required": ["voti"],
    "properties": {"voti": {"type": "array", "items": {
        "type": "object", "additionalProperties": False, "required": ["n", "voto", "problema"],
        "properties": {"n": {"type": "integer"}, "voto": {"type": "string", "enum": ["ok", "dubbio", "sbagliato"]},
                       "problema": {"type": "string"}}}}}}}}

PROMPT_PAGELLA = """Sei l'Ispettore di Studio Galilei, agenzia di Google Ads di Treviso. Rileggi le risposte
che abbiamo mandato oggi a lead dell'outbound. Per ognuna hai l'ultimo messaggio del lead e la nostra risposta.

Il nostro obiettivo con ogni lead e' arrivare a una chiamata conoscitiva SENZA sembrare forzati
e senza mandare messaggi sbagliati. Giudica solo cose verificabili dal testo:
- risponde a quello che la persona ha chiesto o detto? (se chiede un prezzo, un dettaglio, un orario, c'e'?)
- e' coerente col filo? (non ripete cose gia' dette, non contraddice, non ignora un «no» o un «piu' avanti»)
- e' nella lingua della persona? usa il lei? e' firmato da Lorenzo?
- c'e' qualcosa che non doveva esserci (un altro nome di azienda, numeri senza senso, promesse, tono insistente)?
«ok» se va bene, «dubbio» se una persona attenta lo correggerebbe, «sbagliato» se non doveva partire cosi'.
Nel problema una frase sola, concreta, in italiano; vuota se ok. Non inventare problemi di stile.

MESSAGGI:
{messaggi}"""

PROMPT_CONSIGLI = """Sei l'Ispettore di Studio Galilei (agenzia Google Ads, Treviso). Ogni lunedi' dai a Dre,
il CEO, al massimo TRE consigli concreti per alzare il tasso di risposta dell'outbound (cold email via
Smartlead, mittente Lorenzo; l'obiettivo e' arrivare a una chiamata conoscitiva).

Regole:
- ogni consiglio parte da un DATO qui sotto, citato col suo numero; niente consigli generici da blog;
- confronta: campagna con campagna, variante con variante dello stesso passo, oggi con giugno. Un tasso
  da solo non dice niente, la differenza si'. ATTENZIONE: passo 1 contro passo 2 NON e' un confronto di
  testi (chi risponde al passo 2 spesso risponde perche' e' il secondo contatto): non dire «il passo 2
  converte meglio quindi usa il suo testo». Per provare un testo nuovo si propone una variante A/B
  dello stesso passo, che Smartlead divide a meta';
- il link del calendario nella mail dell'analisi e' come si fissano le chiamate: si puo' cambiare come
  lo si presenta, non toglierlo;
- MAI proporre: allegati o link nella prima mail (rovinano la consegna delle cold email); numeri,
  casi o risultati che non stanno qui sotto (niente «+40% per un cliente»); togliere la richiesta di
  consenso prima di mandare l'analisi (e' una scelta voluta: mandiamo solo a chi dice si');
- l'anello che conta di piu' e' la mail con cui mandiamo l'analisi a chi ha detto si': se il suo tasso
  («dopo_analisi») e' sotto giugno, almeno un consiglio riguarda quella mail;
- dici cosa cambiare esattamente (una riga, un oggetto, un passo, un orario), perche', e come si misura
  fra due settimane (quale numero deve salire e di quanto per dire che ha funzionato);
- se un dato e' troppo piccolo per concludere (meno di 100 invii o di 10 risposte) lo dici e non ci costruisci sopra;
- le campagne le modifica Dre: tu proponi, non dai per fatto;
- italiano diretto, frasi corte, niente trattino lungo, niente fuffa, niente «se vuoi preparo...».

Rispondi in testo semplice: un titolo di una riga per consiglio, sotto due-tre righe.

I NUMERI (28 giorni, per campagna e passo; «dopo_analisi» e' quanti rispondono entro 7 giorni
alla mail con cui mandiamo l'analisi, a giugno era il 21%):
{numeri}

I TESTI DELLE SEQUENZE ATTIVE:
{sequenze}

LA MAIL CON CUI MANDIAMO L'ANALISI A CHI HA DETTO SI' (com'e' oggi, per un serramentista di Treviso):
{analisi}

I PROBLEMI TROVATI NELLE PAGELLE DELLA SETTIMANA:
{problemi}"""


def pagella(fuori, per_id):
    """Il modello rilegge ogni risposta nostra di oggi accanto al messaggio a cui risponde."""
    import cervello
    coppie = []
    for x in sorted(fuori, key=lambda x: x["at"])[-30:]:
        prima = sb("GET", f"/rest/v1/interactions?select=body,at&prospect_id=eq.{x['prospect_id']}&kind=eq.email_in"
                          f"&at=lt.{urllib.parse.quote(x['at'])}&order=at.desc&limit=1") or []
        if not prima:
            continue
        coppie.append((x, senza_citazione(pulito(prima[0]["body"]))[:1500], senza_citazione(pulito(x["body"]))[:2000]))
    if not coppie:
        return []
    testo = "\n\n".join(f"[{i}] LEAD:\n{a}\n\nNOSTRA RISPOSTA:\n{b}" for i, (_, a, b) in enumerate(coppie))
    grezzo = cervello._chiedi_openai(PROMPT_PAGELLA.format(messaggi=testo), MODELLO,
                                     formato=SCHEMA_PAGELLA, fornitore="openai", tetto=4000, sforzo="low")
    voti = json.loads(grezzo).get("voti") or []
    out = []
    for v in voti:
        if 0 <= v.get("n", -1) < len(coppie) and v.get("voto") != "ok":
            x = coppie[v["n"]][0]
            out.append({"id": x["id"], "lead": (per_id.get(x["prospect_id"]) or {}).get("company") or "un lead",
                        "voto": v["voto"], "problema": v.get("problema", "")})
    return out


def consigli(num, campagne, problemi):
    import cervello
    seq = []
    for c in campagne:
        for s in (sl(f"/campaigns/{c['id']}/sequences") or []):
            varianti = s.get("sequence_variants") or [{"subject": s.get("subject"), "email_body": s.get("email_body")}]
            for v in varianti:
                seq.append(f"«{c['name'][:40]}» passo {s.get('seq_number')} (dopo {(s.get('seq_delay_details') or {}).get('delay_in_days')} giorni)"
                           f"{' variante ' + str(v.get('variant_label')) if v.get('variant_label') else ''}:\n"
                           f"OGGETTO: {v.get('subject')}\n{pulito(v.get('email_body'))[:1200]}")
    seq = list(dict.fromkeys(seq))[:14]
    try:
        import bozze
        import seguiti
        analisi = seguiti.risposta("INT-01", {"name": "", "sector": "serramenti", "city": "Treviso", "enriched": {}}, {},
                                   "https://cal.studiogalilei.com/...", giorno="martedi' alle 15:30",
                                   testo_file=bozze.template_verbatim(), garanzia=False) or "non disponibile"
    except Exception as e:                                   # noqa: BLE001
        analisi = f"non disponibile ({str(e)[:60]})"
    prompt = PROMPT_CONSIGLI.format(analisi=analisi, numeri=json.dumps(num, ensure_ascii=False, indent=1)[:9000],
                                    sequenze="\n\n".join(seq), problemi="\n".join(problemi[-30:]) or "nessuno")
    return cervello._chiedi_openai(prompt, MODELLO, fornitore="openai", tetto=6000, sforzo="medium").strip()


# ── il giro ─────────────────────────────────────────────────────────
def main():
    stato = leggi_stato()
    detti = {k: v for k, v in (stato.get("detti") or {}).items()
             if quando(v) and (ADESSO - quando(v)).total_seconds() < 7 * 86400}
    ultimo = quando(stato.get("ultimo_giro")) or ADESSO - datetime.timedelta(hours=26)
    da = min(ultimo, ADESSO - datetime.timedelta(hours=2)) - datetime.timedelta(minutes=10)

    campagne = campagne_attive()
    righe = [r for c in campagne for r in inviati(c)]
    per, dom_clienti = lead_per_mail()
    per_id = {p["id"]: p for p in per.values()}
    print(f"ispettore: {len(campagne)} campagne attive, {len(righe)} messaggi di sequenza in archivio, "
          f"controllo da {da.astimezone(ROMA):%d/%m %H:%M}")

    g1, a1 = controlla_sequenze(righe, per, dom_clienti, da)
    g2, a2, _ = controlla_risposte(per_id, da)
    g3, a3 = controlla_salute(campagne, righe, per)
    gravi, attenzione = g1 + g2 + g3, a1 + a2 + a3

    nuovi_g = [(k, t) for k, t in gravi if k not in detti or (ADESSO - quando(detti[k])).total_seconds() > RIDIRE_DOPO_ORE * 3600]
    nuovi_a = [(k, t) for k, t in attenzione if k not in detti]
    print(f"  {len(gravi)} gravi ({len(nuovi_g)} nuovi), {len(attenzione)} da guardare ({len(nuovi_a)} nuovi)")
    for _, t in nuovi_g[:20]:
        print("  !!", t)
    for _, t in nuovi_a[:20]:
        print("  ! ", t)

    if "--semina" in sys.argv:
        for k, _ in gravi + attenzione:
            detti[k] = ADESSO.isoformat()
        stato.update({"ultimo_giro": ADESSO.isoformat(), "detti": detti, "pagella": ORA_ROMA.date().isoformat(),
                      "consigli": ORA_ROMA.date().isoformat() if ORA_ROMA.weekday() == 0 else stato.get("consigli")})
        salva(STATO, stato)
        print(f"  seminato: {len(detti)} guai segnati come gia' detti")
        return

    if (nuovi_g or nuovi_a) and not PROVA:
        righe_msg = []
        if nuovi_g:
            righe_msg.append("ISPETTORE, da fermare subito:\n- " + "\n- ".join(t for _, t in nuovi_g[:10]))
        if nuovi_a:
            righe_msg.append(("Da guardare:" if nuovi_g else "ISPETTORE, da guardare:") + "\n- " + "\n- ".join(t for _, t in nuovi_a[:12]))
        resto = len(nuovi_g) + len(nuovi_a) - min(len(nuovi_g), 10) - min(len(nuovi_a), 12)
        if resto > 0:
            righe_msg.append(f"(e altri {resto}: li ripete il prossimo giro)")
        try:
            di_clara("controllo", "\n\n".join(righe_msg), letto=False)
            for k, _ in nuovi_g[:10] + nuovi_a[:12]:
                detti[k] = ADESSO.isoformat()
        except Exception as e:                               # noqa: BLE001
            print("  (avviso non scritto:", str(e)[:80] + ")")

    # la pagella, una volta al giorno dalle 18; i consigli il lunedi' (o a richiesta)
    oggi = ORA_ROMA.date().isoformat()
    fa_pagella = "--pagella" in sys.argv or (ORA_ROMA.hour >= 18 and stato.get("pagella") != oggi)
    fa_consigli = "--consigli" in sys.argv or (ORA_ROMA.weekday() == 0 and ORA_ROMA.hour >= 8 and stato.get("consigli") != oggi)
    if fa_pagella or fa_consigli:
        ventotto = sb_tutte(f"/rest/v1/interactions?select=id,prospect_id,at,body&kind=eq.email_out"
                            f"&at=gte.{urllib.parse.quote((ADESSO - datetime.timedelta(days=35)).isoformat())}")
        num = numeri(campagne, righe, ventotto)
        if PROVA:
            print(json.dumps(num, ensure_ascii=False)[:4000])
        else:
            salva("ispettore/ultimo.json", num)
    if fa_pagella:
        inizio = datetime.datetime.combine(ORA_ROMA.date(), datetime.time(0), ROMA).astimezone(datetime.timezone.utc)
        _, _, fuori_oggi = controlla_risposte(per_id, inizio)
        try:
            voti = pagella(fuori_oggi, per_id)
        except Exception as e:                               # noqa: BLE001
            voti = []
            print("  (pagella non fatta:", str(e)[:100] + ")")
        tassi = ", ".join(f"{c['nome'].split(' /')[0]} {c['7g']['tasso']}%" for c in num["campagne"] if c["7g"]["nuovi"] >= 30)
        da_ = num["dopo_analisi"]
        dopo = f" ({da_['tasso']}%, a giugno era il 21%)" if da_["tasso"] is not None else ""
        msg = (f"ISPETTORE, la giornata: {num['oggi']['inviati']} mail di sequenza partite, {num['oggi']['risposte']} risposte, "
               f"{len(fuori_oggi)} risposte nostre.\n"
               f"Risposte in 7 giorni per campagna: {tassi or 'troppi pochi invii per dirlo'}.\n"
               f"Dopo l'analisi: {da_['risposte_7g']} su {da_['misurabili']} hanno risposto entro 7 giorni{dopo}.")
        if voti:
            msg += "\n\nRisposte da rivedere:\n- " + "\n- ".join(f"{v['lead']} ({v['voto']}): {v['problema']}" for v in voti[:10])
        elif fuori_oggi:
            msg += "\nLe risposte di oggi sono tutte coerenti col filo."
        print(msg)
        if not PROVA:
            di_clara("controllo", msg, letto=not voti)
            stato["pagella"] = oggi
            stato["problemi"] = (stato.get("problemi") or [])[-60:] + [f"{oggi} {v['lead']}: {v['problema']}" for v in voti]
            salva(f"ispettore/numeri-{oggi}.json", num)
    if fa_consigli:
        try:
            testo = consigli(num, campagne, stato.get("problemi") or [])
            print("\nCONSIGLI:\n" + testo)
            if not PROVA:
                di_clara("controllo", "ISPETTORE, tre cose per alzare le risposte (le campagne le cambi tu, io misuro):\n\n" + testo, letto=False)
                stato["consigli"] = oggi
                salva(f"ispettore/consigli-{oggi}.json", {"testo": testo, "numeri": num})
        except Exception as e:                               # noqa: BLE001
            print("  (consigli non fatti:", str(e)[:100] + ")")

    stato["ultimo_giro"] = ADESSO.isoformat()
    stato["detti"] = detti
    salva(STATO, stato)
    if nuovi_g:
        sys.exit(1)       # il workflow diventa rosso: si vede anche da GitHub


if __name__ == "__main__":
    main()
