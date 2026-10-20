#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""LA SCHEDA «CLARA» NEL FOGLIO DELLA PIPELINE (20/10/2026, «io più il sistema»).

PERCHE'
Dre, 20/10: «delle cose non mi accorgo mai perché le vedi solo tu, le scopro dopo aver perso
soldi o quando domando a te». La sera guarda il foglio: accanto alla scheda «Pipeline» ce n'e'
una seconda, «Clara», scritta dal sistema a ogni giro del foglio (10 minuti):
- in alto il SEMAFORO: verde «Tutto a posto», o rosso con cosa si e' fermato, da quando e cosa
  sta facendo il sistema per rimettersi (una riga per guasto);
- sotto, COSA HA FATTO CLARA oggi e ieri, una riga per azione, la piu' recente in alto, in
  parole di Dre.

IL SEMAFORO si accende solo per quello che costa lead o soldi (spec, punto 4):
- un si' senza analisi da piu' di un'ora, contando solo l'orario di invio (8-21); conta anche un
  rimbalzo interno (INT-08/09, «mandatelo a questo indirizzo») ancora «da_classificare» (20/10).
  CHI E' UN SI' LO DICE IL LETTORE AI (20/10 sera): prospects.classificazione == positivo, che
  sync_v2 scrive dal lettore (scripts/lettore.py). Il segnale provvisorio non decide piu': la sera
  del 20/10 accendeva 6 rossi, e 5 non erano si' («abbiamo gia' chi ci segue», «ho girato la
  mail», «non lavora piu' qui», un'obiezione);
- l'invio fermo: le ultime 3 corse di un'operazione che porta le mail in errore, o nessuna corsa
  da un'ora in orario; crediti finiti o chiave scaduta (l'ultima corsa lo dice);
- il direttore fermo (nessuna operazione da 20 minuti);
- il foglio non aggiornato da un'ora;
- un lead entrato in conversazione senza notifica partita (la chiave «conversazioni» in
  snella_numeri, scritta da chi manda la notifica: se manca, questo controllo e' spento).
- i guasti che il segnale provvisorio vede da dentro (Gmail ferma, memoria, calendario...),
  scritti da segnale_provvisorio._registra_guasto in snella_numeri «guasti_segnale».
Gli stessi guasti li suona sul telefono scripts/guasti.py (una volta, poi ogni 2 ore, poi «Risolto»).

USO
  python3 scripts/clara_foglio.py --prova     stampa semaforo e diario, non scrive niente
  (il giro vero lo fa foglio.py alla fine del suo giro: clara_foglio.scrivi(sid, ora))
"""
import datetime
import os
import re
import sys
import urllib.parse
import zoneinfo

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from stanza import sb, sb_tutte, quando, contattabile, lettore_di  # noqa: E402

ROMA = zoneinfo.ZoneInfo("Europe/Rome")
SCHEDA = "Clara"
ORE_INVIO = (8, 21)                     # la finestra della prima risposta (prima_risposta.ORE)
SI_FERMO = datetime.timedelta(minutes=60)
FOGLIO_FERMO = datetime.timedelta(minutes=60)
SILENZIO = datetime.timedelta(minutes=60)
DIRETTORE_FERMO = datetime.timedelta(minutes=30)        # la sentinella lo rianima a 20; alle 5 c'e' un buco normale di 22
CONVERSAZIONE_SENZA_NOTIFICA = datetime.timedelta(hours=1)   # conversazioni.py riprova per 24 ore: un'ora e' un guasto
SEGNALE_VISTO = datetime.timedelta(minutes=20)              # il segnale gira ogni 4-5 minuti: se non lo rivede, e' risolto
# le operazioni che portano le mail: se si fermano, si perdono lead
INVIO = {"sync_smartlead": "La lettura delle risposte da Smartlead", "analisi": "La preparazione delle analisi",
         "prima_risposta": "L'invio delle prime risposte", "seguiti": "L'invio dei follow-up",
         "manda": "L'invio delle mail"}
# crediti finiti, chiave o token scaduti: da soli non si rimettono
CHIAVE_SCADUTA = re.compile(r"insufficient_quota|credit balance|credits? (?:exhausted|finit)|billing|"
                            r"\b402\b|invalid_api_key|invalid x-api-key|\b401\b[^\n]{0,40}(?:unauthori|invalid)|"
                            r"invalid_grant|token (?:has )?(?:been )?(?:expired|revoked)|quota exceeded", re.I)

FORNITORI = (("openai", "OpenAI"), ("anthropic", "Anthropic"), ("smartlead", "Smartlead"), ("google", "Google"),
             ("searchapi", "SearchAPI"))


def _nella_finestra(t):
    r = t.astimezone(ROMA)
    return ORE_INVIO[0] <= r.hour < ORE_INVIO[1]


def _inizio_finestra(t):
    r = t.astimezone(ROMA)
    return datetime.datetime(r.year, r.month, r.day, ORE_INVIO[0], tzinfo=ROMA)


def _ora(t):
    return t.astimezone(ROMA).strftime("%H:%M")


def _minuti(td):
    return int(td.total_seconds() // 60)


def _quanto(td):
    m = _minuti(td)
    if m < 120:
        return f"{m} minuti"
    if m < 48 * 60:
        return f"{m // 60} ore"
    return f"{m // 1440} giorni"


# ── i dati ────────────────────────────────────────────────────────────

def conversazioni_aperte(numeri=None):
    """Le conversazioni aperte, dal campo che scrive chi manda la notifica «entrato in
    conversazione» (snella_numeri, chiave «conversazioni»: {pid: {"dal": iso, "notificata": bool}}).
    None se la chiave non c'e': allora il controllo «conversazione senza notifica» e' spento."""
    if numeri is None:
        r = sb("GET", "/rest/v1/snella_numeri?select=chiave,dati&chiave=eq.conversazioni") or []
        numeri = {x["chiave"]: x.get("dati") for x in r}
    if "conversazioni" not in numeri:
        return None
    return numeri.get("conversazioni") or {}


def _z(t):
    return urllib.parse.quote(t.astimezone(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"))


def _pezzi(ids, n=80):
    ids = sorted(i for i in ids if i)
    for i in range(0, len(ids), n):
        yield ",".join(ids[i:i + n])


def _nomi(pids):
    out = {}
    for pezzo in _pezzi(set(pids)):
        for p in sb("GET", f"/rest/v1/prospects?select=id,company,name&id=in.({pezzo})") or []:
            out[p["id"]] = " ".join((p.get("company") or p.get("name") or "?").split())
    return out


RIMBALZI = ("INT-08", "INT-09")
RIMBALZI_LETTORE = ("C35", "C37")       # «scriva a quest'altro indirizzo», «mette in copia un collega»


def rimbalzi_fermi(ora, gia=(), proposte=None, schede=None):
    """I RIMBALZI SONO SI' (20/10). «Provi a mandarlo a questo indirizzo, all'attenzione di X» e' un si'
    con una persona in piu', ma il sync lo lascia «da_classificare» e il segnale non lo conta come si':
    un rimbalzo fermo mezza giornata non accendeva il semaforo. Si contano le bozze INT-08/INT-09
    aperte (anche «da guardare tu») di chi e' ancora da classificare e senza analisi, con l'ora della
    sua mail. 20/10 sera: se il lettore AI ha letto la sua ultima mail, il rimbalzo e' tale solo se
    lo dice lui (C35 un indirizzo nuovo, C37 un collega in copia): «l'ho girata, vi contatteranno»
    (C36) e «non lavora piu' qui» (C39) non sono si' da servire, anche se il modello delle bozze
    aveva scritto un INT-08. `proposte` e `schede` si passano solo nelle prove."""
    if proposte is None:
        proposte = sb("GET", "/rest/v1/proposte?select=prospect_id&tipo=in.(risposta,umano)&stato=in.(aperta,approvata,in_invio)"
                             f"&azione->>intento=in.({','.join(RIMBALZI)})&prospect_id=not.is.null&limit=300") or []
    ids = {x["prospect_id"] for x in proposte if x.get("prospect_id")} - set(gia)
    if not ids:
        return []
    if schede is None:
        schede = []
        for pezzo in _pezzi(ids):
            schede += sb("GET", "/rest/v1/prospects?select=id,company,name,analysis_sent,fuori,stage,pipeline_stage,no_followup,"
                                f"classificazione,last_reply_at,lettore:enriched->lettore&id=in.({pezzo})") or []
    out = []
    for p in schede:
        if p["id"] not in ids or p.get("classificazione") != "da_classificare" or p.get("analysis_sent") or not p.get("last_reply_at"):
            continue
        letto = lettore_di(p)
        if letto and letto.get("caso") not in RIMBALZI_LETTORE:
            continue                                   # il lettore l'ha letta e non e' un rimbalzo
        t = quando(p["last_reply_at"])
        if ora - t > datetime.timedelta(days=3) or not contattabile(p):
            continue
        out.append({"prospect_id": p["id"], "azienda": " ".join((p.get("company") or p.get("name") or "?").split()), "quando": t, "bozza": True})
    return out


def si_fermi(ora, positivi=None, dopo=None, bozze=None):
    """I si' degli ultimi 3 giorni senza analisi e senza nessuna mail nostra dopo, piu' i rimbalzi
    interni ancora da classificare (rimbalzi_fermi). UN SI' E' CHI IL LETTORE HA MESSO «positivo»
    (prospects.classificazione, 20/10 sera): il segnale provvisorio non decide piu'. La sua ora e'
    quella della sua ultima mail. `positivi`, `dopo` ({pid: ultima nostra mail}) e `bozze` (pid con
    una bozza aperta, anche «da guardare tu») si passano solo nelle prove."""
    da = ora - datetime.timedelta(days=3)
    if positivi is None:
        positivi = sb("GET", "/rest/v1/prospects?select=id,company,name,analysis_sent,fuori,stage,pipeline_stage,no_followup,"
                             f"classificazione,last_reply_at&classificazione=eq.positivo&last_reply_at=gte.{_z(da)}"
                             "&order=last_reply_at.desc&limit=500") or []
    ps = {p["id"]: p for p in positivi if p.get("last_reply_at") and p.get("classificazione") == "positivo"}
    if dopo is None:
        dopo = {}
        for pezzo in _pezzi(ps):
            for x in sb("GET", f"/rest/v1/interactions?select=prospect_id,at&prospect_id=in.({pezzo})"
                               f"&kind=in.(email_out,followup)&at=gte.{_z(da)}&limit=2000") or []:
                t = quando(x["at"])
                if x["prospect_id"] not in dopo or t > dopo[x["prospect_id"]]:
                    dopo[x["prospect_id"]] = t
    if bozze is None:
        bozze = set()
        for pezzo in _pezzi(ps):
            bozze |= {x["prospect_id"] for x in sb("GET", f"/rest/v1/proposte?select=prospect_id&prospect_id=in.({pezzo})"
                                                         "&tipo=in.(risposta,umano)&stato=in.(aperta,approvata,in_invio)") or []}
    out = []
    for p in sorted(ps.values(), key=lambda p: p["last_reply_at"]):
        t = quando(p["last_reply_at"])
        if t < da or p.get("analysis_sent") or not contattabile(p):
            continue
        if dopo.get(p["id"]) and dopo[p["id"]] >= t - datetime.timedelta(minutes=30):
            continue                                       # gli abbiamo scritto: servito
        out.append({"prospect_id": p["id"], "azienda": " ".join((p.get("company") or p.get("name") or "?").split()), "quando": t,
                    "bozza": p["id"] in bozze})
    return out + rimbalzi_fermi(ora, gia=set(ps))


def leggi_semaforo(ora):
    ops = {o["chiave"]: o for o in sb("GET", "/rest/v1/operazioni?select=chiave,nome,attiva,cadenza_minuti") or []}
    corse = {}
    for c in sb_tutte(f"/rest/v1/corse?select=id,operazione,at,esito,dettaglio&at=gte.{_z(ora - datetime.timedelta(hours=3))}"):
        corse.setdefault(c["operazione"], []).append({"at": quando(c["at"]), "esito": c.get("esito"), "dettaglio": c.get("dettaglio") or ""})
    for v in corse.values():
        v.sort(key=lambda c: c["at"], reverse=True)
    ultima = max((v[0]["at"] for v in corse.values() if v), default=None)
    fog = [c for c in corse.get("foglio", []) if c["esito"] == "ok"]
    if fog:
        foglio_il = fog[0]["at"]
    else:
        r = sb("GET", "/rest/v1/corse?select=at&operazione=eq.foglio&esito=eq.ok&order=at.desc&limit=1") or []
        foglio_il = quando(r[0]["at"]) if r else None
    r = sb("GET", "/rest/v1/snella_numeri?select=dati&chiave=eq.guasti_segnale") or []
    segnale = (r[0].get("dati") if r else None) or {}
    conv = conversazioni_aperte()
    if conv:
        mute = [pid for pid, v in conv.items() if isinstance(v, dict) and not v.get("notificata")]
        nomi = _nomi(mute) if mute else {}
        conv = {pid: (dict(v, azienda=nomi.get(pid)) if pid in nomi else v) for pid, v in conv.items()}
    return {"si": si_fermi(ora), "corse": corse, "operazioni": ops, "foglio_il": foglio_il,
            "conversazioni": conv, "ultima_corsa": ultima, "segnale": segnale}


# ── il semaforo ───────────────────────────────────────────────────────

def semaforo(ora, dati=None):
    """I guasti aperti: [{"chiave", "cosa", "da", "sta_facendo"}]. Lista vuota = verde."""
    dati = dati if dati is not None else leggi_semaforo(ora)
    guasti = []
    direttore_fermo = dati.get("ultima_corsa") and ora - dati["ultima_corsa"] > DIRETTORE_FERMO
    if direttore_fermo:
        guasti.append({"chiave": "direttore", "da": dati["ultima_corsa"],
                       "cosa": f"Il sistema è fermo: nessuna operazione da {_quanto(ora - dati['ultima_corsa'])}",
                       "sta_facendo": "La sentinella lo rianima da sola ogni 15 minuti."})
    for s in dati.get("si") or []:
        partenza = max(s["quando"], _inizio_finestra(ora))
        if _nella_finestra(ora) and ora - partenza > SI_FERMO:
            guasti.append({"chiave": f"si:{s['prospect_id']}", "da": s["quando"], "pid": s["prospect_id"],
                           "cosa": f"Sì senza analisi: {s['azienda']}, ha detto sì alle {_ora(s['quando'])}",
                           "sta_facendo": ("La risposta è scritta ma non parte da sola: va guardata nella sua scheda."
                                           if s.get("bozza") else "Il sistema riprova da solo a ogni giro. Se resta qui, guarda la sua scheda.")})
    ops = dati.get("operazioni") or {}
    corse = dati.get("corse") or {}
    for chiave, op in ops.items():
        if not op.get("attiva"):
            continue
        cc = corse.get(chiave) or []
        nome = INVIO.get(chiave) or op.get("nome") or chiave
        if cc and cc[0]["esito"] == "errore" and CHIAVE_SCADUTA.search(cc[0]["dettaglio"] or "") and ora - cc[0]["at"] < SILENZIO:
            chi = next((n for k, n in FORNITORI if k in (cc[0]["dettaglio"] or "").lower()), "")
            guasti.append({"chiave": f"chiave:{chiave}", "da": cc[0]["at"],
                           "cosa": f"{nome}: crediti {chi + ' ' if chi else ''}finiti o chiave scaduta",
                           "sta_facendo": "Da solo non riparte: va ricaricato il conto o rinnovata la chiave (dillo ad Achille)."})
            continue
        if chiave not in INVIO:
            continue
        if len(cc) >= 3 and all(c["esito"] == "errore" for c in cc[:3]):
            serie = 0
            while serie < len(cc) and cc[serie]["esito"] == "errore":
                serie += 1
            guasti.append({"chiave": f"invio:{chiave}", "da": cc[serie - 1]["at"],
                           "cosa": f"{nome} è fermo: le ultime {serie} prove sono andate male",
                           "sta_facendo": "Riprova da solo ogni pochi minuti. Le mail non si perdono: partono quando riparte."})
            continue
        lenta = int(op.get("cadenza_minuti") or 0) > 15
        if not direttore_fermo and not lenta and _nella_finestra(ora) and (not cc or ora - cc[0]["at"] > SILENZIO):
            da = cc[0]["at"] if cc else ora - SILENZIO
            guasti.append({"chiave": f"invio:{chiave}", "da": da,
                           "cosa": f"{nome} non gira da {_quanto(ora - da)}" if cc else f"{nome} non gira da più di un'ora",
                           "sta_facendo": "Il direttore lo rilancia a ogni giro; la sentinella controlla ogni 15 minuti."})
    if dati.get("foglio_il") and ora - dati["foglio_il"] > FOGLIO_FERMO:
        guasti.append({"chiave": "foglio", "da": dati["foglio_il"],
                       "cosa": f"Il foglio non si aggiorna da {_quanto(ora - dati['foglio_il'])}",
                       "sta_facendo": "Riprova da solo ogni 10 minuti."})
    for pid, v in (dati.get("conversazioni") or {}).items():
        if not isinstance(v, dict) or v.get("notificata") or not v.get("dal"):
            continue
        dal = quando(v["dal"])
        if ora - dal > CONVERSAZIONE_SENZA_NOTIFICA:
            chi = v.get("azienda") or "Un lead"
            guasti.append({"chiave": f"conversazione:{pid}", "da": dal, "pid": pid,
                           "cosa": f"{chi} è in conversazione ma la notifica non è partita",
                           "sta_facendo": "La trovi nel foglio, in Conversazione: rispondi da Smartlead."})
    # i guasti che il segnale provvisorio vede da dentro (Gmail ferma, memoria, calendario,
    # conversazioni): li scrive segnale_provvisorio._registra_guasto, restano rossi finche' li rivede
    for motivo, v in (dati.get("segnale") or {}).items():
        if not isinstance(v, dict) or not v.get("il") or ora - quando(v["il"]) > SEGNALE_VISTO:
            continue
        guasti.append({"chiave": f"segnale:{motivo}", "da": quando(v.get("dal") or v["il"]),
                       "cosa": " ".join(str(v.get("testo") or motivo).split()).rstrip("."),
                       "sta_facendo": "Il segnale riprova da solo ogni 5 minuti."})
    guasti.sort(key=lambda g: g["da"])
    return guasti


# ── il diario ─────────────────────────────────────────────────────────

NO = ("negativo", "soppresso", "nervoso")
TIPO_CALL = {"conoscitiva": "conoscitiva", "tecnica": "tecnica", "avvio": "di avvio"}


def leggi_eventi(ora, giorni=2):
    oggi = ora.astimezone(ROMA).date()
    da_d = oggi - datetime.timedelta(days=giorni - 1)
    da = datetime.datetime(da_d.year, da_d.month, da_d.day, tzinfo=ROMA)
    analisi = [(p["id"], quando(p["analysis_sent_at"])) for p in
               sb_tutte(f"/rest/v1/prospects?select=id,analysis_sent_at&analysis_sent_at=gte.{_z(da)}")]
    fatte = []
    for x in sb_tutte(f"/rest/v1/proposte?select=id,prospect_id,risposta_il,ref,gruppo:azione->lettura->>gruppo,"
                      f"template:azione->>template,intento:azione->>intento&stato=eq.fatta&risposta_il=gte.{_z(da)}"):
        if x.get("prospect_id") and x.get("risposta_il"):
            gruppo = x.get("gruppo") or x.get("template") or x.get("intento") or ""
            if str(x.get("ref") or "").startswith("promemoria"):
                gruppo = "PROMEMORIA"
            fatte.append((x["prospect_id"], quando(x["risposta_il"]), gruppo))
    no = [(r["riga"], quando(r["at"])) for r in
          sb_tutte(f"/rest/v1/registro?select=id,riga,at,dopo&tabella=eq.prospects&campo=eq.classificazione&at=gte.{_z(da)}")
          if str(r.get("dopo") or "").strip('"') in NO]
    conv = []
    for pid, v in (conversazioni_aperte() or {}).items():
        if isinstance(v, dict) and v.get("dal") and quando(v["dal"]) >= da:
            conv.append((pid, quando(v["dal"])))
    call = []
    for a in sb_tutte("/rest/v1/agenda?select=id,prospect_id,at,tipo,creato_il&fonte=like.gcal*&prospect_id=not.is.null"
                      f"&tipo=in.(conoscitiva,tecnica,avvio)&or=(at.gte.{_z(da)},creato_il.gte.{_z(da)})"):
        if a.get("creato_il") and quando(a["creato_il"]) >= da:
            call.append((a["prospect_id"], quando(a["creato_il"]), a["tipo"], "fissata", quando(a["at"])))
        if da <= quando(a["at"]) <= ora:
            call.append((a["prospect_id"], quando(a["at"]), a["tipo"], "fatta", quando(a["at"])))
    pids = {x[0] for lista in (analisi, fatte, no, conv, call) for x in lista}
    return {"analisi": analisi, "fatte": fatte, "no": no, "conversazioni": conv, "call": call, "nomi": _nomi(pids)}


def diario(ora, giorni=2, eventi=None):
    """[(quando, azienda, cosa)] di oggi e ieri, il piu' recente in alto, in parole di Dre."""
    from foglio_lead import _tipo, giorno_breve
    ev = eventi if eventi is not None else leggi_eventi(ora, giorni)
    nomi = ev.get("nomi") or {}
    righe = []
    analisi = ev.get("analisi") or []
    for pid, t in analisi:
        righe.append((t, pid, "Analisi mandata"))
    for pid, t, gruppo in ev.get("fatte") or []:
        tipo = _tipo(gruppo)
        if tipo == "follow-up":
            righe.append((t, pid, "Follow-up partito"))
        elif tipo == "promemoria":
            righe.append((t, pid, "Promemoria della call mandato"))
        elif not any(a == pid and abs((a_t - t).total_seconds()) < 3600 for a, a_t in analisi):
            righe.append((t, pid, "Risposta mandata"))
    for pid, t in ev.get("no") or []:
        righe.append((t, pid, "Ha detto no"))
    for pid, t in ev.get("conversazioni") or []:
        righe.append((t, pid, "È entrato in conversazione"))
    for c in ev.get("call") or []:
        pid, t, tipo, come, at = c
        nome = TIPO_CALL.get(tipo, "")
        if come == "fissata":
            righe.append((t, pid, f"Call {nome} fissata per {giorno_breve(at)} alle {_ora(at)}"))
        else:
            righe.append((t, pid, f"Call {nome}"))
    oggi = ora.astimezone(ROMA).date()
    da = oggi - datetime.timedelta(days=giorni - 1)
    righe = [r for r in righe if da <= r[0].astimezone(ROMA).date() and r[0] <= ora + datetime.timedelta(minutes=5)]
    righe.sort(key=lambda r: r[0], reverse=True)
    return [(t, nomi.get(pid) or "?", cosa) for t, pid, cosa in righe]


# ── la scheda nel foglio ──────────────────────────────────────────────

VERDE, VERDE_T, ROSSO, ROSSO_T = "#e7f6ec", "#166534", "#fdecec", "#b42318"
COLONNE = (("Quando", 110), ("Azienda", 260), ("Cosa", 520))
RIGHE = 600


def _quando_breve(t, ora):
    r = t.astimezone(ROMA)
    oggi = ora.astimezone(ROMA).date()
    if r.date() == oggi:
        return f"oggi {r:%H:%M}"
    if r.date() == oggi - datetime.timedelta(days=1):
        return f"ieri {r:%H:%M}"
    return f"{r:%d/%m %H:%M}"


def cosa_del_guasto(g):
    """La cella «Azienda» di una riga rossa. Se il guasto riguarda un lead (ha `pid`), la cella e' il
    link alla sua scheda nel Workspace (20/10 sera, Dre: «lo vedevo, ma non potevo agire»): un clic e ci
    sono i pulsanti per mandare, non mandare o chiudere. Il foglio e' in italiano: punto e virgola nella
    formula, le virgolette nel testo raddoppiate."""
    from foglio import testo
    if not g.get("pid"):
        return testo(g["cosa"])
    from foglio_lead import link_scheda
    url = link_scheda(g["pid"])
    if not url.startswith("https://") or '"' in url:
        return testo(g["cosa"])
    t = " ".join(str(g["cosa"]).split()).replace('"', '""')
    return f'=HYPERLINK("{url}";"{t}")'


def griglia(guasti, righe_diario, ora):
    """Le righe della scheda: il semaforo, i guasti, il titolo del diario, il diario.
    Torna (valori, quante righe di guasto)."""
    from foglio import testo
    if guasti:
        testa = f"Qualcosa si è fermato ({len(guasti)}) · aggiornato alle {_ora(ora)}"
    else:
        testa = f"Tutto a posto · aggiornato alle {_ora(ora)}"
    valori = [[testa, "", ""]]
    for g in guasti:
        valori.append([f"dalle {_ora(g['da'])}" if g["da"].astimezone(ROMA).date() == ora.astimezone(ROMA).date()
                       else _quando_breve(g["da"], ora), cosa_del_guasto(g), testo(g["sta_facendo"])])
    valori.append(["", "", ""])
    valori.append(["Cosa ha fatto Clara, oggi e ieri", "", ""])
    if not righe_diario:
        valori.append(["", "Niente ancora", ""])
    for t, azienda, cosa in righe_diario:
        valori.append([_quando_breve(t, ora), testo(azienda), testo(cosa)])
    return valori, len(guasti)


def _id_scheda(sid, crea=True):
    from foglio import _g, SHEETS, rgb, NAVY
    info = _g("GET", f"{SHEETS}/{sid}?fields=sheets.properties")
    for s in info.get("sheets", []):
        if s["properties"]["title"] == SCHEDA:
            return s["properties"]["sheetId"]
    if not crea:
        return None
    nuovo = max([s["properties"]["sheetId"] for s in info.get("sheets", [])] + [0]) + 1
    from foglio import _formato, _campo
    R = [{"addSheet": {"properties": {"sheetId": nuovo, "title": SCHEDA, "index": 1, "tabColor": rgb(NAVY),
                                      "gridProperties": {"rowCount": RIGHE, "columnCount": len(COLONNE),
                                                         "frozenRowCount": 1, "hideGridlines": True}}}}]
    for i, (_, w) in enumerate(COLONNE):
        R.append({"updateDimensionProperties": {"range": {"sheetId": nuovo, "dimension": "COLUMNS", "startIndex": i, "endIndex": i + 1},
                                                "properties": {"pixelSize": w}, "fields": "pixelSize"}})
    R.append({"updateDimensionProperties": {"range": {"sheetId": nuovo, "dimension": "ROWS", "startIndex": 0, "endIndex": 1},
                                            "properties": {"pixelSize": 40}, "fields": "pixelSize"}})
    R.append({"updateDimensionProperties": {"range": {"sheetId": nuovo, "dimension": "ROWS", "startIndex": 1, "endIndex": RIGHE},
                                            "properties": {"pixelSize": 26}, "fields": "pixelSize"}})
    R.append({"mergeCells": {"range": _campo(nuovo, 0, 1, 0, len(COLONNE)), "mergeType": "MERGE_ALL"}})
    R.append({"addProtectedRange": {"protectedRange": {"range": _campo(nuovo, 0, RIGHE, 0, len(COLONNE)), "warningOnly": True,
                                                       "description": "La scrive il sistema ogni 10 minuti"}}})
    _g("POST", f"{SHEETS}/{sid}:batchUpdate", {"requests": R})
    print(f"clara: scheda «{SCHEDA}» creata")
    return nuovo


def scrivi(sid, ora, guasti=None, righe_diario=None):
    """Riscrive la scheda «Clara» del foglio (la crea se non c'e')."""
    from foglio import _g, SHEETS, _formato, _campo, NAVY, INCHIOSTRO, TENUE, BORDO, GRIGIO_CHIARO, rgb
    guasti = semaforo(ora) if guasti is None else guasti
    righe_diario = diario(ora) if righe_diario is None else righe_diario
    valori, n = griglia(guasti, righe_diario, ora)
    S = _id_scheda(sid)
    nc = len(COLONNE)
    _g("POST", f"{SHEETS}/{sid}/values:batchClear", {"ranges": [f"{SCHEDA}!A2:C{RIGHE}", f"{SCHEDA}!A1"]})
    _g("POST", f"{SHEETS}/{sid}/values:batchUpdate", {"valueInputOption": "USER_ENTERED", "data": [
        {"range": f"{SCHEDA}!A1:C{len(valori)}", "values": valori}]})
    titolo_diario = n + 2                                    # indice (da 0) della riga «Cosa ha fatto Clara»
    R = [
        _formato(_campo(S, 1, RIGHE, 0, nc), fondo="#ffffff", colore=INCHIOSTRO, grassetto=False, dim=10, a_capo="CLIP", vert="MIDDLE"),
        {"updateBorders": {"range": _campo(S, 0, RIGHE, 0, nc), "innerHorizontal": {"style": "NONE"}, "bottom": {"style": "NONE"}}},
        _formato(_campo(S, 0, 1, 0, nc), fondo=ROSSO if guasti else VERDE, colore=ROSSO_T if guasti else VERDE_T,
                 grassetto=True, dim=13, vert="MIDDLE"),
        _formato(_campo(S, titolo_diario, titolo_diario + 1, 0, nc), colore=NAVY, grassetto=True, dim=12, vert="BOTTOM",
                 a_capo="OVERFLOW_CELL"),
        {"updateDimensionProperties": {"range": {"sheetId": S, "dimension": "ROWS", "startIndex": 1, "endIndex": RIGHE},
                                       "properties": {"pixelSize": 26}, "fields": "pixelSize"}},
        _formato(_campo(S, titolo_diario + 1, RIGHE, 0, 1), colore=GRIGIO_CHIARO, dim=9),
        _formato(_campo(S, titolo_diario + 1, RIGHE, 1, 2), grassetto=True),
        _formato(_campo(S, titolo_diario + 1, RIGHE, 2, 3), colore=TENUE),
        {"updateBorders": {"range": _campo(S, titolo_diario + 1, titolo_diario + 1 + max(len(righe_diario), 1), 0, nc),
                           "innerHorizontal": {"style": "SOLID", "color": rgb(BORDO)},
                           "bottom": {"style": "SOLID", "color": rgb(BORDO)}}},
    ]
    if n:
        R.append({"updateDimensionProperties": {"range": {"sheetId": S, "dimension": "ROWS", "startIndex": 1, "endIndex": 1 + n},
                                                "properties": {"pixelSize": 46}, "fields": "pixelSize"}})
        R.append(_formato(_campo(S, 1, 1 + n, 0, nc), fondo=ROSSO, colore=ROSSO_T, a_capo="WRAP", vert="MIDDLE"))
        R.append(_formato(_campo(S, 1, 1 + n, 1, 2), grassetto=True))
    _g("POST", f"{SHEETS}/{sid}:batchUpdate", {"requests": R})
    print(f"clara: semaforo {'rosso, ' + str(n) + ' guasti' if n else 'verde'}, {len(righe_diario)} righe nel diario")
    return S


def main():
    ora = datetime.datetime.now(datetime.timezone.utc)
    g = semaforo(ora)
    print("SEMAFORO:", "verde" if not g else f"rosso ({len(g)})")
    for x in g:
        print(f"  dalle {_ora(x['da'])}  {x['cosa']}  ·  {x['sta_facendo']}")
    righe = diario(ora)
    print(f"DIARIO ({len(righe)} righe):")
    for t, az, cosa in righe[:40]:
        print(f"  {_quando_breve(t, ora):12} {az[:34]:34} {cosa}")
    if "--prova" not in sys.argv:
        from foglio import carica_stato, trova_foglio
        sid = trova_foglio(carica_stato())
        if sid:
            scrivi(sid, ora, g, righe)


if __name__ == "__main__":
    main()
