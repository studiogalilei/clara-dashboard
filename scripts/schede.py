#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""LE SCHEDE DELLA VERSIONE SNELLA (15/10/2026).

PERCHE'
Dre, 15/10: il Workspace e' pesante per quello che fa ogni giorno con le campagne outbound.
Fino a «Clara nuova» (dicembre) c'e' una shell snella (src/snella/) con tre schermate: Oggi,
Lead, Campagne. La UI non ragiona: legge quello che prepara questo script. E' PROVVISORIO
come il segnale: si butta col sistema nuovo (file, tabelle snella_*, riga in `operazioni`).

COSA FA, a ogni giro (il direttore, corsia leggera, ogni 10 minuti)
1. LE SCHEDE. Per ogni lead attivo (ha risposto negli ultimi 60 giorni, ha una call nei
   prossimi giorni, o Dre ci ha messo mano) una scheda pronta in snella_schede:
   - chi e', i telefoni in gerarchia con la fonte, cosa fa, l'ultima cosa che ha scritto,
     l'analisi si'/no col link: la stessa scheda della mail pre-call di Dre, presa da
     segnale_provvisorio.scheda() (non riscritta). L'AI non si paga mai qui: se la lettura
     c'e' gia' in memoria (una prenotazione l'ha gia' fatta) si usa, se no la scheda resta
     quella senza AI (le righe del Google Fit, la frase pulita).
   - lo stato coi nomi di Dre, dalla categoria del manuale (categorie_smartlead.categoria_nuova),
     e una prossima mossa suggerita con la data.
   - «da chiamare» e il perche': segnalato caldo dal segnale, la lettura del segnale che dice
     caldo (con il numero, se l'ha lasciato: «Ha lasciato il numero»), o la categoria «Vuole
     sentirti». Il senso lo decide l'AI del segnale, gia' pagata: niente regex sul testo (il
     15/10 una regex sui numeri prendeva 37 firme e autorisposte su 42).
     MA (Dre, 20/10 sera) «Da chiamare» SOLO se c'e' un cellulare suo (la firma o la scheda, mai il
     centralino del sito: segnale_provvisorio.cellulare_fra). Chi vuole sentirci senza un cellulare
     e' «Da rispondere» con Dre responsabile e la prossima azione che dice perche'. Le scelte a
     mano di Dre (snella_lead) vincono comunque su questo stato.
   - il filo delle mail in ordine, con la parte citata gia' separata (lettura.CITAZIONE).
   Si rifa' solo quello che e' cambiato (l'impronta: scheda del lead, mail, segnali, call),
   le schede con una risposta dell'ultima ora (la lettura del segnale arriva dopo il sync),
   e al massimo 40 schede vecchie di un giorno per giro.
2. I NUMERI in snella_numeri:
   - oggi: le risposte arrivate oggi, i si' e in quanto tempo sono stati serviti
     (segnale_provvisorio.primo_servizio), chi aspetta da piu' tempo, cosa e' in ritardo.
   - call: le call nel calendario di Dre da oggi a 7 giorni (agenda, fonte gcal) piu' le
     prenotazioni del segnale non ancora in agenda.
   - campagne (una volta all'ora): per ogni campagna attiva, 7 e 30 giorni. Mail mandate,
     aziende scritte e risposte da Smartlead (SOLO LETTURA: GET analytics-by-date); si',
     call e no dai dati del Workspace. Se Smartlead non risponde: null, la UI scrive
     «non disponibile». Mai un numero inventato.

COSA NON FA
Mai una mail, mai una scrittura su Smartlead, mai sulle tabelle del sistema vecchio: scrive
solo snella_schede e snella_numeri. Non paga letture AI.

USO
  python3 scripts/schede.py                 il giro vero
  python3 scripts/schede.py --prova         calcola e stampa i conteggi, non scrive
  python3 scripts/schede.py --tutte         rifa' tutte le schede (non solo le cambiate)
  python3 scripts/schede.py --campagne      rifa' anche i numeri delle campagne adesso
"""

import datetime
import hashlib
import html
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request
import zoneinfo
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from stanza import sb, sb_tutte, quando, env, _a_secco         # noqa: E402
import lettura as L                                            # noqa: E402
import segnale_provvisorio as S                                # noqa: E402
import categorie_smartlead as C                                # noqa: E402

PROVA = "--prova" in sys.argv or _a_secco()
TUTTE = "--tutte" in sys.argv
ROMA = zoneinfo.ZoneInfo("Europe/Rome")
VERSIONE = "schede6"                     # cambia la forma della scheda -> si rifanno tutte (6: Da chiamare solo col cellulare, 20/10 sera)
GIORNI_ATTIVI = 60
VECCHIE_PER_GIRO = 30
FRESCA = datetime.timedelta(hours=1)     # una risposta piu' giovane di cosi': la scheda si rifa' a ogni giro
SI_IN_RITARDO = datetime.timedelta(minutes=30)
CAMPAGNE_OGNI = datetime.timedelta(minutes=55)
SL_BASE = "https://server.smartlead.ai/api/v1"

# GLI STATI (Dre, 19/10): dodici, in quattro gruppi, nient'altro. La fonte unica e'
# src/snella/stati.json (la UI, questo script e le prove la leggono; il database ne ha la copia
# in snella_stati, schema_v93). Ogni stato ha un responsabile e una prossima azione di default.
_STATI_JSON = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src", "snella", "stati.json"), encoding="utf-8"))
STATI = {s["nome"]: s for s in _STATI_JSON["stati"]}

# Le categorie del manuale (categorie_smartlead.NUOVE) nei nomi di Dre. Fuori target e casella
# morta sono «Non interessato» col motivo nella prossima azione (MOTIVO); girato a un collega e'
# «Da rispondere» (c'e' un'alternativa a cui scrivere).
NOME_DI = {
    C.N_SI: "Analisi inviata", C.N_FU: "Analisi inviata", C.N_CALL_CHIESTA: "Da chiamare",
    C.N_DRE: "Da rispondere", C.N_CALL: "Call fissata", C.N_AVANTI: "Da ricontattare",
    C.N_OOO: "Assente", C.N_GIRATO: "Da rispondere", C.N_NO: "Non interessato",
    C.N_STOP: "Non contattare", C.N_FUORI: "Non interessato", C.N_MORTA: "Non interessato",
}
MOTIVO = {C.N_FUORI: "fuori target", C.N_MORTA: "casella morta"}
# chi non si chiama: le opportunita' (la call c'e' gia' o e' cliente) e i chiusi
NON_SI_CHIAMA = {s["nome"] for s in _STATI_JSON["stati"] if s["gruppo"] in ("Opportunità", "Chiusi")}
PIPELINE_CLIENTE = ("cliente", "prova", "avvio")
PIPELINE_CALL = ("conoscitiva", "tecnica")
CLASSI_NO = {"negativo", "soppresso", "nervoso"}

# L'AI qui non si paga mai: la lettura della scheda si prende dalla memoria se c'e' (l'ha
# gia' pagata la mail pre-call), se no la scheda resta quella senza AI. _restano_oggi a zero
# ferma il pagamento senza scrivere in memoria una lettura fallita; la sonda non serve.
S._restano_oggi = lambda: 0
S.GIRO["sonda"] = True


def adesso():
    return datetime.datetime.now(datetime.timezone.utc)


def _z(dt):
    return dt.astimezone(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _iso(dt):
    return dt.astimezone(datetime.timezone.utc).isoformat(timespec="seconds") if dt else None


def inizio_oggi():
    r = adesso().astimezone(ROMA)
    return r.replace(hour=0, minute=0, second=0, microsecond=0)


def in_parallelo(fn, cose, n=8):
    """La stessa lettura su tante cose, otto alla volta: il tempo e' quasi tutto attesa di rete.
    Torna [(cosa, risultato o eccezione)] nell'ordine dato."""
    def una(x):
        try:
            return x, fn(x)
        except Exception as e:                                   # noqa: BLE001
            return x, e
    with ThreadPoolExecutor(max_workers=n) as ex:
        return list(ex.map(una, cose))


def a_pezzi(ids, n=80):
    ids = sorted(i for i in ids if i)
    for i in range(0, len(ids), n):
        yield ",".join(ids[i:i + n])


# ── quello che serve a tutto il giro, letto una volta ─────────────────

CAMPI_P = ("id,company,name,email,classificazione,stage,pipeline_stage,fuori,no_followup,awaiting_us,"
           "last_reply_at,updated_at,campaign,campaign_id,followup_due,ooo_until,next_action_date,sg_id,"
           "phone,role,analysis_sent,analysis_sent_at,analysis_pdf")
# l'impronta guarda questi campi, non updated_at: il sync tocca la scheda a ogni giro (la firma di
# Smartlead in enriched) e con updated_at si rifacevano 100 schede ogni 10 minuti per niente.
# Quello che cambia solo in enriched (il Google Fit) arriva col giro delle schede vecchie di un giorno.
CAMPI_IMPRONTA = [c for c in CAMPI_P.split(",") if c not in ("id", "updated_at")]


def leggi_contesto(ora):
    da = _z(ora - datetime.timedelta(days=GIORNI_ATTIVI))
    ps = {p["id"]: p for p in sb_tutte(f"/rest/v1/prospects?select={CAMPI_P}&last_reply_at=gte.{da}")}
    # l'agenda degli ultimi 60 giorni e dei prossimi: le call vere servono allo stato e alla lista.
    # fonte «gcal» e' il calendario di Dre, «gcal:<mail>» quello di un collega
    agenda = sb_tutte(f"/rest/v1/agenda?select=id,at,titolo,tipo,prospect_id,link,fonte,creato_il"
                      f"&fonte=like.gcal*&at=gte.{_z(ora - datetime.timedelta(days=60))}")
    # chi Dre ha toccato: una decisione o una nota (17/10: anche solo una nota tiene viva la scheda)
    toccati = {r["prospect_id"] for r in sb_tutte("/rest/v1/snella_lead?select=prospect_id", chiave="prospect_id")}
    toccati |= {r["prospect_id"] for r in sb_tutte("/rest/v1/snella_note?select=id,prospect_id")}
    vicine = {a["prospect_id"] for a in agenda if a.get("prospect_id") and quando(a["at"]) >= ora - datetime.timedelta(days=1)}
    mancano = (toccati | vicine) - set(ps)
    for pezzo in a_pezzi(mancano):
        for p in sb("GET", f"/rest/v1/prospects?select={CAMPI_P}&id=in.({pezzo})") or []:
            ps[p["id"]] = p
    ids = set(ps)
    # le mail: solo id, verso e data (i corpi solo per le schede da rifare)
    mail = {}
    for pezzo in a_pezzi(ids):
        for r in sb_tutte(f"/rest/v1/interactions?select=id,prospect_id,at,kind&kind=in.(email_in,email_out)"
                          f"&prospect_id=in.({pezzo})"):
            mail.setdefault(r["prospect_id"], []).append(r)
    segnali, caldi = {}, {}
    for pezzo in a_pezzi(ids):
        for s in sb("GET", f"/rest/v1/segnali_provvisori?select=prospect_id,interaction_id,tipo,quando,come"
                           f"&prospect_id=in.({pezzo})") or []:
            if s.get("come") != "prova":
                segnali.setdefault(s["prospect_id"], set()).add(s["tipo"])
                if s["tipo"] == "caldo":
                    caldi.setdefault(s["prospect_id"], set()).add(s.get("interaction_id"))
    # l'ultimo intento delle bozze (domanda o si') e chi ci ha girato a un collega
    intenti, girati = {}, set()
    for pezzo in a_pezzi(ids):
        for x in sb("GET", f"/rest/v1/proposte?select=prospect_id,at,azione->intento,azione->lettura->girato_a"
                           f"&prospect_id=in.({pezzo})&tipo=in.(risposta,umano)&order=at.asc") or []:
            if x.get("intento"):
                intenti[x["prospect_id"]] = x["intento"]
            if x.get("girato_a"):
                girati.add(x["prospect_id"])
    clienti = {r["prospect_id"] for r in sb_tutte("/rest/v1/clienti?select=prospect_id", chiave="prospect_id")}
    gia = {r["prospect_id"]: r for r in sb_tutte("/rest/v1/snella_schede?select=prospect_id,impronta,aggiornata_il",
                                                 chiave="prospect_id")}
    return {"ps": ps, "agenda": agenda, "mail": mail, "segnali": segnali, "caldi": caldi, "intenti": intenti,
            "girati": girati, "clienti": clienti, "gia": gia}


def call_di(ctx, pid):
    """Le call vere (conoscitiva, tecnica, avvio) di un lead in agenda."""
    return [a for a in ctx["agenda"] if a.get("prospect_id") == pid and a.get("tipo") in ("conoscitiva", "tecnica", "avvio")]


def impronta(ctx, pid):
    p = ctx["ps"][pid]
    mm = ctx["mail"].get(pid, [])
    pezzi = (VERSIONE, json.dumps([p.get(c) for c in CAMPI_IMPRONTA], default=str), str(len(mm)), max((m.get("at") or "" for m in mm), default=""),
             ",".join(sorted(ctx["segnali"].get(pid, set()))), ctx["intenti"].get(pid) or "",
             "g" if pid in ctx["girati"] else "", "c" if pid in ctx["clienti"] else "",
             ",".join(sorted(a["at"] for a in call_di(ctx, pid))))
    return hashlib.sha256("|".join(pezzi).encode()).hexdigest()[:20]


def da_rifare(ctx, ora):
    fuori = []
    vecchie = []
    for pid in ctx["ps"]:
        g = ctx["gia"].get(pid)
        imp = impronta(ctx, pid)
        if TUTTE or not g or g.get("impronta") != imp:
            fuori.append(pid)
            continue
        fatta = quando(g["aggiornata_il"])
        ultima_in = max((quando(m["at"]) for m in ctx["mail"].get(pid, []) if m["kind"] == "email_in"), default=None)
        if ultima_in and ora - ultima_in < FRESCA:
            fuori.append(pid)                  # la lettura del segnale arriva dopo il sync
        elif ora - fatta > datetime.timedelta(hours=24):
            vecchie.append((fatta, pid))
    vecchie.sort()
    return fuori + [pid for _, pid in vecchie[:VECCHIE_PER_GIRO]]


# ── una scheda ─────────────────────────────────────────────────────────

HTML_VIA = re.compile(r"<(style|script|head)\b.*?</\1\s*>", re.I | re.S)


def pulito(t):
    """Un corpo che arriva in html (qualche client lo manda cosi'): via stili e tag, testo e basta."""
    t = t or ""
    if "<" in t and re.search(r"</?(div|p|br|span|style|table|html|body)\b", t, re.I):
        t = HTML_VIA.sub(" ", t)
        t = re.sub(r"<br\s*/?>|</p>|</div>", "\n", t, flags=re.I)
        t = html.unescape(re.sub(r"<[^>]+>", " ", t))
        t = "\n".join(" ".join(r.split()) for r in t.split("\n"))
    return t


def dividi(body):
    """Il messaggio e la parte citata sotto (la nostra mail, o la loro di prima)."""
    t = pulito(body).replace("\r\n", "\n").strip()
    taglio = None
    m = L.CITAZIONE.search(t)
    if m:
        taglio = m.start()
    h = L._intestazione(t[:taglio] if taglio is not None else t)
    if h is not None:
        taglio = h
    suo = t if taglio is None else t[:taglio]
    citato = "" if taglio is None else t[taglio:]
    # le righe con «>» in testa sono testo di qualcun altro anche dentro il messaggio
    righe = suo.split("\n")
    proprie = [r for r in righe if not r.lstrip().startswith(">")]
    if len(proprie) < len(righe) and not citato:
        citato = "\n".join(r for r in righe if r.lstrip().startswith(">"))
    return compatto("\n".join(proprie))[:6000], compatto(citato)[:4000]


def compatto(t):
    """Righe senza spazi in coda, al massimo una riga vuota di fila (Smartlead ne mette tante)."""
    righe = [r.rstrip() for r in (t or "").split("\n")]
    out = []
    for r in righe:
        if not r.strip() and (not out or not out[-1].strip()):
            continue
        out.append(r if r.strip() else "")
    return "\n".join(out).strip()


def lettura_segnale(azienda, corpo):
    """La lettura del segnale per questa risposta, se e' gia' in memoria (gratis). None se no."""
    testo = L.solo_suo(corpo, con_firma=True) or corpo
    try:
        r = sb("GET", f"/rest/v1/memoria_letture?select=valore&chiave=eq.{S._chiave(azienda, testo)}") or []
    except Exception:                                            # noqa: BLE001
        return None
    v = r[0].get("valore") if r else None
    return v if isinstance(v, dict) and not v.get("fallita") else None


def _giorno(d):
    """Una data (date o testo) in AAAA-MM-GG, o None."""
    if not d:
        return None
    return str(d)[:10]


def stato_di(cat, p, cliente, rispose):
    """Lo stato (uno dei 12) dalla categoria del manuale e dalla pipeline. Lo stesso ordine sta in
    snella_stato_calcolato (schema_v93) per chi non ha la scheda pronta. Se Dre ne sceglie uno a
    mano (snella_lead), vince il suo: questo e' quello che dice il sistema."""
    ps = p.get("pipeline_stage")
    if cat == C.N_STOP:
        return "Non contattare"
    if cliente or ps in PIPELINE_CLIENTE:
        return "Cliente acquisito"
    if ps == "perso":
        return "Perso"
    if cat == C.N_CALL or ps in PIPELINE_CALL:
        return "Call fissata"
    if not rispose:
        return "Nessuna risposta"
    nome = NOME_DI.get(cat) or "Da rispondere"
    # perso nel Workspace vecchio (stage): un'opportunita' chiusa, se non e' gia' un no
    if p.get("stage") == "perso" and nome != "Non interessato":
        return "Perso"
    return nome


def prossima_mossa(stato, p, call, motivo=None):
    """La prossima azione di default dello stato (stati.json) e la sua data. Dre la cambia nel
    Workspace (snella_lead): le date stanno qui, non in stati nuovi."""
    azione = STATI[stato]["azione"]
    if stato == "Call fissata":
        prossime = sorted(a["at"] for a in call if quando(a["at"]) >= adesso() - datetime.timedelta(hours=2))
        return (azione, _giorno(quando(prossime[0]).astimezone(ROMA).date())) if prossime else ("Decidere dopo la call", None)
    if stato == "Analisi inviata":
        return azione, _giorno(p.get("followup_due"))
    if stato == "Da ricontattare":
        return azione, _giorno(p.get("next_action_date") or p.get("followup_due"))
    if stato == "Assente":
        return azione, _giorno(p.get("ooo_until"))
    if stato == "Non interessato" and motivo:
        return f"{azione}: {motivo}", None
    return azione, None


def vale_il_caldo(tipi, caldi, ultima_id, lettura):
    """Il segnale «caldo» vale ancora? Si', se e' nato sulla sua ultima mail, o se la sua ultima
    mail non e' stata letta. No, se l'ultima, letta, dice non caldo (17/10)."""
    if "caldo" not in tipi:
        return False
    if ultima_id and lettura is not None and not lettura.get("caldo") and ultima_id not in caldi:
        return False
    return True


def costruisci(ctx, pid, ora):
    p = ctx["ps"][pid]
    sc = S.scheda(pid, {}, "")                 # la scheda della mail pre-call, com'e'
    righe = sb("GET", f"/rest/v1/interactions?select=id,at,kind,body&prospect_id=eq.{pid}"
                      f"&kind=in.(email_in,email_out)&order=at.asc&limit=300") or []
    filo = []
    for r in righe:
        testo, citato = dividi(r.get("body"))
        filo.append({"at": r.get("at"), "chi": "lui" if r["kind"] == "email_in" else "noi",
                     "testo": testo, "citato": citato})
    sue = [r for r in righe if r["kind"] == "email_in" and (r.get("body") or "").strip() and not S.automatica(r["body"])]
    ultima = sue[-1] if sue else None
    ultima_suo = L.solo_suo(ultima["body"], con_firma=True) if ultima else ""
    call = call_di(ctx, pid)
    cliente = pid in ctx["clienti"] or p.get("stage") == "cliente" or p.get("pipeline_stage") == "cliente"
    # fuori (passato al Workspace) non ferma la lettura della categoria: la pipeline la guarda stato_di
    cat = C.categoria_nuova({**p, "bloccato": False, "fuori": False}, ctx["intenti"].get(pid), pid in ctx["girati"], ultima_suo, call=bool(call))
    stato = stato_di(cat, p, cliente, bool(ultima or p.get("last_reply_at")))
    azienda = " ".join((p.get("company") or p.get("name") or "?").split())
    lettura = lettura_segnale(azienda, ultima["body"]) if ultima else None
    tipi = ctx["segnali"].get(pid, set())
    # 17/10: il segnale «caldo» era sulla mail di prima («l'ho girata a chi se ne
    # occupa»); poi ha riscritto «io non mi occupo di questa parte» e la lettura di quella dice
    # non caldo. Il caldo vale per la mail su cui e' nato: se la sua ultima mail, letta, non lo
    # e', lui non si chiama. Senza lettura dell'ultima il segnale resta (meglio una chiamata in piu').
    segnalato = vale_il_caldo(tipi, ctx.get("caldi", {}).get(pid, set()), ultima and ultima["id"], lettura)
    caldo = segnalato or bool(lettura and lettura.get("caldo"))
    if caldo and stato in ("Analisi inviata", "Da rispondere"):
        stato = "Da chiamare"
    # 20/10 sera: «Da chiamare» solo con un cellulare suo (firma o scheda, mai il sito). Senza, la
    # conversazione e' di Dre ma per mail: «Da rispondere», responsabile lui, e la mossa dice perche'.
    cellulare = S.cellulare_fra(sc.get("telefoni") or [])
    senza_cellulare = stato == "Da chiamare" and not cellulare
    if senza_cellulare:
        stato = "Da rispondere"
    # da chiamare (il senso lo decide l'AI, non una regex): segnalato caldo dal segnale, la lettura
    # del segnale che dice caldo (col numero se l'ha lasciato), o lo stato «Da chiamare»
    perche = []
    if segnalato:
        perche.append("Segnalato caldo")
    if lettura and lettura.get("caldo") and (lettura.get("telefono") or "").strip():
        perche.append("Ha lasciato il numero")
    elif not perche and (caldo or stato == "Da chiamare"):
        perche.append("Ha chiesto una chiamata")
    escluso = (cliente or p.get("fuori") or p.get("stage") == "perso" or p.get("pipeline_stage") == "perso"
               or p.get("classificazione") in CLASSI_NO or stato in NON_SI_CHIAMA)
    da_chiamare = bool(perche) and not escluso and cellulare is not None
    frase = ""
    if lettura and lettura.get("frase") and S._dentro(lettura["frase"], ultima["body"]):
        frase = S._frase_pulita(lettura["frase"])
    frase = " ".join(pulito(frase or sc.get("ultima") or "").split())
    mossa, mossa_il = prossima_mossa(stato, p, call, MOTIVO.get(cat))
    responsabile = STATI[stato]["responsabile"]
    if senza_cellulare and not escluso:
        mossa, mossa_il, responsabile = S.SENZA_CELLULARE, None, "Dramane"
    an = sc.get("analisi") or {}
    link = an.get("link") or ""
    percorso = ""
    m = re.search(r"/storage/v1/object/(?:sign|public)/vault/([^?]+)", link)
    if m:
        percorso = urllib.parse.unquote(m.group(1))
    elif link and not link.startswith("http"):
        link = ""                               # solo il nome del file: non si apre da qui
    telefoni = [{"numero": t["numero"], "tel": S._tel_link(t["numero"]), "etichetta": t["etichetta"], "tipo": t["tipo"], "fonte": t["fonte"]}
                for t in sc.get("telefoni") or []]
    scheda = {
        "azienda": azienda, "nome": sc.get("nome") or "", "ruolo": sc.get("ruolo") or "",
        "email": p.get("email") or "", "sg_id": p.get("sg_id"), "campagna": p.get("campaign") or "",
        "telefoni": telefoni, "attivita": sc.get("attivita") or "",
        "ultima": " ".join(pulito(sc.get("ultima") or "").split()), "ultima_il": _iso(sc.get("ultima_il")),
        "consiglio": (lettura or {}).get("consiglio") or "",
        "analisi": {"mandata": bool(an.get("mandata")), "il": _iso(an.get("il")), "link": link,
                    "percorso": percorso, "punto": an.get("punto") or ""},
        "prossima": {"mossa": mossa, "il": mossa_il, "responsabile": responsabile},
        "aspetta_noi": bool(p.get("awaiting_us")),
    }
    return {"prospect_id": pid, "azienda": azienda, "persona": scheda["nome"] or " ".join((p.get("name") or "").split()),
            "email": p.get("email") or "", "stato": stato,
            "ultima_risposta": ultima["at"] if ultima else p.get("last_reply_at"),
            "frase": frase[:300], "da_chiamare": da_chiamare, "perche_chiamare": ", ".join(perche) if da_chiamare else None,
            "scheda": scheda, "filo": filo, "impronta": impronta(ctx, pid), "aggiornata_il": _iso(ora)}


# ── i numeri ───────────────────────────────────────────────────────────

def numeri_oggi(ctx, ora):
    oggi = inizio_oggi()
    righe = sb_tutte(f"/rest/v1/interactions?select=id,prospect_id,at,body&kind=eq.email_in&at=gte.{_z(oggi)}"
                     f"&prospect_id=not.is.null")
    ps = ctx["ps"]
    mancano = {r["prospect_id"] for r in righe} - set(ps)
    for pezzo in a_pezzi(mancano):
        for p in sb("GET", f"/rest/v1/prospects?select={CAMPI_P}&id=in.({pezzo})") or []:
            ps[p["id"]] = p
    vere = [r for r in righe if r["prospect_id"] in ps and not S.automatica(r.get("body") or "")]
    chi = {r["prospect_id"] for r in vere}
    # i si' di oggi: la classe che il lettore AI ha scritto nel lead (prospects.classificazione).
    # 20/10 sera: la lettura del segnale provvisorio non decide piu' chi «ha detto si' e aspetta»
    si = {}
    az_di = lambda r: " ".join((ps[r["prospect_id"]].get("company") or ps[r["prospect_id"]].get("name") or "?").split())  # noqa: E731
    for r in sorted(vere, key=lambda r: r["at"]):
        p = ps[r["prospect_id"]]
        if p.get("classificazione") == "positivo" and r["prospect_id"] not in si and not p.get("fuori"):
            si[r["prospect_id"]] = (r, az_di(r))
    serviti, in_attesa = [], []
    serviti_il = dict(in_parallelo(lambda pid: S.primo_servizio(pid, quando(si[pid][0]["at"])), list(si)))
    for pid, (r, az) in si.items():
        at = quando(r["at"])
        fatto = serviti_il.get(pid)
        fatto = None if isinstance(fatto, Exception) else fatto
        if fatto:
            serviti.append({"prospect_id": pid, "azienda": az, "at": r["at"], "minuti": max(0, int((fatto - at).total_seconds() // 60))})
        elif ctx["ps"][pid].get("stage") != "call_fissata":
            in_attesa.append({"prospect_id": pid, "azienda": az, "at": r["at"], "minuti": int((ora - at).total_seconds() // 60)})
    # chi aspetta da piu' tempo una nostra risposta (lead vivi, ultimi 60 giorni)
    aspettano = sorted((p for p in ctx["ps"].values() if p.get("awaiting_us") and not p.get("fuori")
                        and p["id"] not in ctx["clienti"]
                        and p.get("classificazione") not in ("negativo", "soppresso", "nervoso", "ooo", "fuori_target")
                        and p.get("last_reply_at") and ora - quando(p["last_reply_at"]) <= datetime.timedelta(days=GIORNI_ATTIVI)),
                       key=lambda p: p["last_reply_at"])
    primo = aspettano[0] if aspettano else None
    ritardi = [x for x in in_attesa if x["minuti"] >= SI_IN_RITARDO.total_seconds() // 60]
    return {
        "risposte": len(chi), "messaggi": len(vere),
        "si": len(si), "serviti": serviti, "in_attesa": in_attesa,
        "media_minuti": round(sum(x["minuti"] for x in serviti) / len(serviti)) if serviti else None,
        "aspettano": len(aspettano),
        "aspetta_da_piu": {"prospect_id": primo["id"], "azienda": " ".join((primo.get("company") or primo.get("name") or "?").split()),
                           "da": primo["last_reply_at"]} if primo else None,
        "ritardo": bool(ritardi),
        "ritardi": [f"{x['azienda']}: un sì senza risposta da {x['minuti']} minuti" for x in ritardi],
    }


def numeri_call(ctx, ora):
    """Le call con i lead da oggi a 7 giorni: il calendario di Dre, e le call vere (conoscitiva,
    tecnica, avvio) nei calendari dei colleghi. La stessa call in due calendari una volta sola."""
    oggi = inizio_oggi()
    fine = oggi + datetime.timedelta(days=8)
    per_call = {}
    for a in sorted(ctx["agenda"], key=lambda a: (a["at"], a.get("fonte") != "gcal")):
        t = quando(a["at"])
        if not (oggi <= t < fine):
            continue
        di_dre = a.get("fonte") == "gcal"
        vera = a.get("tipo") in ("conoscitiva", "tecnica", "avvio")
        if not vera and not (di_dre and a.get("prospect_id")):
            continue                       # le riunioni interne non sono call con i lead
        chiave = (a["at"], (a.get("link") or "").split("?")[0] or a.get("titolo"))
        c = per_call.get(chiave)
        if c:
            c["di_dre"] = c["di_dre"] or di_dre
            c["prospect_id"] = c["prospect_id"] or a.get("prospect_id")
            continue
        per_call[chiave] = {"at": a["at"], "titolo": a.get("titolo") or "", "tipo": a.get("tipo") or "altro",
                            "prospect_id": a.get("prospect_id"), "di_dre": di_dre,
                            "di_chi": "" if di_dre else (a.get("fonte") or "").split(":", 1)[-1].split("@")[0].capitalize(),
                            "meet": (a.get("link") or "") if "meet.google" in (a.get("link") or "") else ""}
    out = list(per_call.values())
    for c in out:
        p = ctx["ps"].get(c["prospect_id"]) or {}
        c["azienda"] = " ".join((p.get("company") or p.get("name") or "").split())
        if c["di_dre"]:
            c["di_chi"] = ""
    # le prenotazioni viste dal segnale e non ancora arrivate in agenda
    try:
        pren = sb("GET", f"/rest/v1/prenotazioni_segnalate?select=evento,tipo,inizio,prospect_id,azienda,quando"
                         f"&inizio=gte.{_z(oggi)}&order=quando.asc") or []
    except Exception:                                            # noqa: BLE001
        pren = []
    ultimo = {}
    for r in pren:
        if r["tipo"] != "mattina":
            ultimo[r["evento"]] = r
    for r in ultimo.values():
        if r["tipo"] == "cancellata" or not r.get("inizio"):
            continue
        t = quando(r["inizio"])
        if not (oggi <= t < fine) or any(c["prospect_id"] == r.get("prospect_id") and c["at"][:16] == _iso(t)[:16] for c in out):
            continue
        p = ctx["ps"].get(r.get("prospect_id")) or {}
        out.append({"at": _iso(t), "titolo": "Conoscitiva prenotata", "tipo": "conoscitiva", "prospect_id": r.get("prospect_id"),
                    "azienda": " ".join((p.get("company") or p.get("name") or r.get("azienda") or "").split()), "meet": "",
                    "di_dre": True, "di_chi": ""})
    out.sort(key=lambda c: c["at"])
    return {"call": out}


def _chiave_smartlead():
    k = env("SMARTLEAD_API_KEY")
    if k:
        return k.strip().strip("\"'")
    p = os.path.expanduser("~/.hermes/config.yaml")
    if os.path.exists(p):
        for riga in open(p, encoding="utf-8"):
            m = re.match(r"\s*SMARTLEAD_API_KEY:\s*(\S+)", riga)
            if m:
                return m.group(1).strip().strip("\"'")
    return None


def _sl_leggi(percorso, chiave):
    """SOLO LETTURA su Smartlead: una GET, con tre tentativi. Nessun altro metodo esiste qui."""
    sep = "&" if "?" in percorso else "?"
    url = f"{SL_BASE}{percorso}{sep}api_key={chiave}"
    for i in range(3):
        try:
            req = urllib.request.Request(url, method="GET", headers={"User-Agent": "clara-snella/1.0"})
            with urllib.request.urlopen(req, timeout=40) as r:
                return json.loads(r.read())
        except Exception:                                        # noqa: BLE001
            if i == 2:
                raise
            time.sleep(2 * (i + 1))


def _intero(x):
    try:
        return int(x)
    except (TypeError, ValueError):
        return None


def numeri_campagne(ctx, ora):
    chiave = _chiave_smartlead()
    errore = None
    campagne = []
    if not chiave:
        errore = "manca la chiave di Smartlead"
    else:
        try:
            campagne = [c for c in (_sl_leggi("/campaigns", chiave) or []) if c.get("status") == "ACTIVE"]
        except Exception as e:                                   # noqa: BLE001
            errore = f"Smartlead non risponde ({str(e)[:80]})"
    # le risposte del Workspace per campagna: chi ha risposto nella finestra, e con che esito
    entrate = {}
    for pid, mm in ctx["mail"].items():
        for m in mm:
            if m["kind"] == "email_in":
                entrate.setdefault(pid, []).append(quando(m["at"]))
    prenotate = {}
    for a in ctx["agenda"]:
        if a.get("tipo") == "conoscitiva" and a.get("prospect_id"):
            t = quando(a.get("creato_il") or a["at"])
            prenotate[a["prospect_id"]] = min(t, prenotate.get(a["prospect_id"], t))

    def dal_workspace(cid, giorni):
        da = ora - datetime.timedelta(days=giorni)
        chi = [pid for pid, p in ctx["ps"].items() if (cid is None or p.get("campaign_id") == cid)
               and any(t >= da for t in entrate.get(pid, []))]
        classe = lambda pid: ctx["ps"][pid].get("classificazione")      # noqa: E731
        return {"risposte_lette": len(chi),
                "si": sum(1 for pid in chi if classe(pid) == "positivo"),
                "no": sum(1 for pid in chi if classe(pid) in CLASSI_NO),
                "call": sum(1 for pid, t in prenotate.items() if t >= da and pid in ctx["ps"]
                            and (cid is None or ctx["ps"][pid].get("campaign_id") == cid))}

    out = []
    for c in campagne:
        riga = {"id": c["id"], "nome": c.get("name") or "", "creata": (c.get("created_at") or "")[:10], "finestre": {}}
        for giorni in (7, 30):
            f = dal_workspace(c["id"], giorni)
            try:
                inizio = (ora - datetime.timedelta(days=giorni)).astimezone(ROMA).date().isoformat()
                a = _sl_leggi(f"/campaigns/{c['id']}/analytics-by-date?start_date={inizio}"
                              f"&end_date={ora.astimezone(ROMA).date().isoformat()}", chiave)
                f.update({"mandate": _intero(a.get("sent_count")), "aziende": _intero(a.get("unique_sent_count")),
                          "risposte": _intero(a.get("reply_count"))})
            except Exception as e:                               # noqa: BLE001
                f.update({"mandate": None, "aziende": None, "risposte": None})
                errore = errore or f"Smartlead non ha dato i numeri ({str(e)[:80]})"
            riga["finestre"][str(giorni)] = f
        out.append(riga)
    totale = {}
    for giorni in ("7", "30"):
        t = dal_workspace(None, int(giorni)) if not campagne else {
            k: sum(r["finestre"][giorni][k] for r in out) for k in ("risposte_lette", "si", "no", "call")}
        for k in ("mandate", "aziende", "risposte"):
            vals = [r["finestre"][giorni].get(k) for r in out]
            t[k] = sum(vals) if vals and all(v is not None for v in vals) else None
        totale[giorni] = t
    return {"campagne": out, "totale": totale, "errore": errore}


# ── il giro ────────────────────────────────────────────────────────────

def scrivi(tabella, righe, conflitto):
    for i in range(0, len(righe), 25):
        sb("POST", f"/rest/v1/{tabella}?on_conflict={conflitto}", righe[i:i + 25],
           {"Prefer": "resolution=merge-duplicates,return=minimal"})


def main():
    ora = adesso()
    t0 = time.time()
    ctx = leggi_contesto(ora)
    rifare = da_rifare(ctx, ora)
    print(f"schede: {len(ctx['ps'])} lead attivi, {len(rifare)} da rifare")
    fatte, rotte = [], []
    for pid, esito in in_parallelo(lambda pid: costruisci(ctx, pid, ora), rifare):
        if isinstance(esito, Exception):
            rotte.append((pid, str(esito)[:120]))
        else:
            fatte.append(esito)
    numeri = [{"chiave": "oggi", "dati": numeri_oggi(ctx, ora), "aggiornato_il": _iso(ora)},
              {"chiave": "call", "dati": numeri_call(ctx, ora), "aggiornato_il": _iso(ora)}]
    ultime = sb("GET", "/rest/v1/snella_numeri?select=aggiornato_il&chiave=eq.campagne") or []
    if "--campagne" in sys.argv or not ultime or ora - quando(ultime[0]["aggiornato_il"]) > CAMPAGNE_OGNI:
        numeri.append({"chiave": "campagne", "dati": numeri_campagne(ctx, ora), "aggiornato_il": _iso(ora)})
    chiamare = sum(1 for f in fatte if f["da_chiamare"])
    print(f"schede: rifatte {len(fatte)} ({chiamare} da chiamare), non riuscite {len(rotte)}")
    for pid, e in rotte[:5]:
        print(f"  non riuscita {pid}: {e}")
    o = numeri[0]["dati"]
    print(f"oggi: {o['risposte']} risposte, {o['si']} sì ({len(o['serviti'])} serviti, {len(o['in_attesa'])} in attesa), "
          f"{o['aspettano']} aspettano una risposta" + (", IN RITARDO" if o["ritardo"] else ""))
    print(f"call: {len(numeri[1]['dati']['call'])} da oggi a 7 giorni")
    if len(numeri) > 2:
        cc = numeri[2]["dati"]
        print(f"campagne: {len(cc['campagne'])} attive" + (f" ({cc['errore']})" if cc.get("errore") else ""))
    print(f"schede: {len(set(ctx['gia']) - set(ctx['ps']))} schede di chi non e' piu' attivo da togliere")
    if PROVA:
        print("(prova: non scrivo niente)")
        return
    scrivi("snella_schede", fatte, "prospect_id")
    scrivi("snella_numeri", numeri, "chiave")
    print(f"schede: scritte {len(fatte)} in {int(time.time() - t0)}s")
    togli_spente(ctx)
    if rotte and len(rotte) > len(fatte):
        sys.exit("schede: piu' schede rotte che fatte, guardare l'errore qui sopra")


def togli_spente(ctx):
    """Le schede di chi non e' piu' un lead attivo se ne vanno (17/10: una mail tolta dal lead,
    come un rapporto DMARC attaccato per sbaglio, lasciava la sua scheda nella lista per 60
    giorni con la frase del rapporto). Chi ha una decisione, una nota o una call resta attivo.
    Se ne andrebbero piu' di meta' (una lettura andata storta), non si tocca niente."""
    via = sorted(set(ctx["gia"]) - set(ctx["ps"]))
    if not via:
        return
    if len(via) > max(50, len(ctx["gia"]) // 2):
        print(f"schede: {len(via)} schede da togliere su {len(ctx['gia'])}: troppe, non tolgo niente")
        return
    for pezzo in a_pezzi(via):
        sb("DELETE", f"/rest/v1/snella_schede?prospect_id=in.({pezzo})")
    print(f"schede: tolte {len(via)} schede di chi non e' piu' attivo")


if __name__ == "__main__":
    main()
