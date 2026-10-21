#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""LA GIORNATA — una mail sola a Dre, alle 19 (20/10/2026 sera).

PERCHE'
Dre, 20/10 sera: «metti delle regole anche alle mail che mi arrivano, perché me le manda un po'
a caso. A chiusura della giornata voglio UNA mail, alle 19, che mi dica cosa è stato completato,
per andare a letto sereno, col quadro del lavoro del sistema: se è andato bene, se niente si è
rotto. Una frase breve se è tutto a posto, oppure "è successo questo, la soluzione è questa"».
Negli ultimi tre giorni il segnale gli aveva mandato venti mail. Da stasera le mail di giornata
non partono piu' (segnale_provvisorio: resta solo la scheda prima di una call) e la sera arriva
questa. Alle 19, non alle 18: alle 18 c'e' ancora chi risponde alle mail.

COSA C'E' DENTRO, in quest'ordine, corto e in italiano semplice
1. Il quadro del sistema: «Il sistema ha funzionato regolarmente.» se nelle 24 ore nessun guasto
   (aperto o risolto: snella_numeri «guasti», che guasti.py tiene con lo storico del giorno; piu' il
   semaforo di adesso, clara_foglio.semaforo, e le operazioni cadute tre volte di fila oggi, dalle
   corse). Se no, una riga per guasto: «È successo: <cosa>, <quando>. Soluzione: <cosa ha fatto il
   sistema, o cosa serve da Dre>».
2. I numeri di oggi: risposte arrivate (si', no, fuori ufficio), analisi mandate, follow-up partiti,
   promemoria, call prenotate/spostate/annullate, lead entrati in conversazione, lead passati a «Da
   chiamare». Dalle stesse tabelle del diario della scheda Clara.
3. «Aspettano te» (al massimo 8 righe, col link alla scheda): chi ha scritto dopo l'analisi e non ha
   ancora una risposta sua; le risposte ferme «da guardare tu» degli ultimi due giorni; i «Da
   chiamare» di oggi (e quelli rimasti indietro). Se non c'e' niente: «Niente da parte tua.»
4. «Domani»: le call in calendario, con ora e azienda. Se nessuna: «Nessuna call.»
5. Una riga di chiusura. Niente altro, mai nomi tecnici.

UNA SOLA AL GIORNO: prima di mandare si guarda nella posta inviata di Dre; se la mail di oggi c'e'
gia' non si rimanda (il direttore la fa partire alle 19; una prova vera a mano non la raddoppia).

USO
  python3 scripts/giornata.py --prova     stampa la mail di oggi, non manda
  python3 scripts/giornata.py             la manda a Dre (operazione «giornata», ore 19)
"""
import datetime
import html
import os
import sys
import urllib.parse
import zoneinfo

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from stanza import sb, sb_tutte, quando, contattabile, _a_secco        # noqa: E402

ROMA = zoneinfo.ZoneInfo("Europe/Rome")
GIORNI = ("lun", "mar", "mer", "gio", "ven", "sab", "dom")
MAX_ASPETTANO = 8
CONVERSAZIONI_GIORNI = 14           # una conversazione piu' vecchia non si rincorre piu' da qui
DA_GUARDARE_ORE = 48                # le risposte ferme «da guardare tu» degli ultimi due giorni
SERIE_ERRORI = 3                    # un'operazione caduta tante volte di fila oggi si dice
CHIUSI = ("Perso", "Non interessato", "Non contattare", "Cliente acquisito", "Proposta inviata")
NO = ("negativo", "soppresso", "nervoso")


def adesso():
    return datetime.datetime.now(datetime.timezone.utc)


def _z(t):
    return urllib.parse.quote(t.astimezone(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"))


def _ora(t):
    return t.astimezone(ROMA).strftime("%H:%M")


def giorno_breve(t):
    r = t.astimezone(ROMA)
    return f"{GIORNI[r.weekday()]} {r:%d/%m}"


def inizio_giorno(ora, giorni_fa=0):
    r = ora.astimezone(ROMA).date() - datetime.timedelta(days=giorni_fa)
    return datetime.datetime(r.year, r.month, r.day, tzinfo=ROMA)


def _quando_breve(t, ora):
    r = t.astimezone(ROMA)
    oggi = ora.astimezone(ROMA).date()
    if r.date() == oggi:
        return f"oggi alle {r:%H:%M}"
    if r.date() == oggi - datetime.timedelta(days=1):
        return f"ieri alle {r:%H:%M}"
    return f"{giorno_breve(t)} alle {r:%H:%M}"


def _pezzi(ids, n=80):
    ids = sorted(i for i in set(ids) if i)
    for i in range(0, len(ids), n):
        yield ",".join(ids[i:i + n])


def _nomi(pids):
    out = {}
    for pezzo in _pezzi(pids):
        for p in sb("GET", f"/rest/v1/prospects?select=id,company,name&id=in.({pezzo})") or []:
            out[p["id"]] = " ".join((p.get("company") or p.get("name") or "?").split())
    return out


# ── i dati (tutta la rete sta qui) ─────────────────────────────────

def serie_di_errori(corse, nomi, soglia=SERIE_ERRORI):
    """Pura. Le operazioni cadute `soglia` volte di fila oggi: [{"chiave", "nome", "n", "da", "ripartita"}].
    corse: [{"operazione", "at", "esito"}] in ordine di tempo."""
    per_op = {}
    for c in corse:
        per_op.setdefault(c["operazione"], []).append(c)
    out = []
    for chiave, cc in per_op.items():
        cc.sort(key=lambda c: c["at"])
        serie, i = [], 0
        while i < len(cc):
            if cc[i]["esito"] != "errore":
                i += 1
                continue
            j = i
            while j < len(cc) and cc[j]["esito"] == "errore":
                j += 1
            if j - i >= soglia:
                serie.append({"chiave": chiave, "nome": nomi.get(chiave) or chiave, "n": j - i, "da": cc[i]["at"],
                              "ripartita": cc[j]["at"] if j < len(cc) else None})
            i = j
        out += serie
    return sorted(out, key=lambda s: s["da"])


def _guasti(ora, oggi0):
    """I guasti del giorno: aperti adesso (il semaforo, con cosa sta facendo il sistema) e risolti oggi
    (lo storico che tiene guasti.py). Se il semaforo non si legge lo si dice, non si tace."""
    aperti, fallito = [], None
    try:
        import clara_foglio
        aperti = clara_foglio.semaforo(ora)
    except Exception as e:                                       # noqa: BLE001
        fallito = str(e)[:120]
    r = sb("GET", "/rest/v1/snella_numeri?select=dati&chiave=eq.guasti") or []
    dati = (r[0].get("dati") if r else None) or {}
    risolti = []
    for x in dati.get("risolti") or []:
        if not isinstance(x, dict) or not x.get("risolto_il"):
            continue
        fine = quando(x["risolto_il"])
        if fine >= ora - datetime.timedelta(hours=24):
            risolti.append({"chiave": x.get("chiave"), "cosa": x.get("cosa") or "qualcosa si è fermato",
                            "da": quando(x["primo"] or x["da"]) if (x.get("primo") or x.get("da")) else fine, "risolto_il": fine})
    chiavi_aperte = {g["chiave"] for g in aperti}
    risolti = [x for x in risolti if x["chiave"] not in chiavi_aperte]
    return aperti, risolti, fallito


def leggi(ora):
    oggi0 = inizio_giorno(ora)
    domani0 = oggi0 + datetime.timedelta(days=1)
    dopodomani0 = oggi0 + datetime.timedelta(days=2)
    da_z = _z(oggi0)
    aperti, risolti, fallito = _guasti(ora, oggi0)
    # le operazioni cadute piu' volte di fila oggi (quelle che il semaforo non copre comprese)
    ops = {o["chiave"]: o.get("nome") or o["chiave"] for o in sb("GET", "/rest/v1/operazioni?select=chiave,nome") or []}
    corse = [{"operazione": c["operazione"], "at": quando(c["at"]), "esito": c.get("esito")}
             for c in sb_tutte(f"/rest/v1/corse?select=id,operazione,at,esito&at=gte.{da_z}&order=at.asc")]
    coperte = {g["chiave"].split(":", 1)[-1] for g in aperti} | {str(x.get("chiave") or "").split(":", 1)[-1] for x in risolti}
    serie = [s for s in serie_di_errori(corse, ops) if s["chiave"] not in coperte]
    # i numeri di oggi
    # chi ha scritto oggi, e com'e' letto adesso (la classe di oggi, del lettore o di Dre)
    arrivate = {x["prospect_id"] for x in sb_tutte(f"/rest/v1/interactions?select=id,prospect_id&kind=eq.email_in&at=gte.{da_z}") if x.get("prospect_id")}
    classi = {}
    for pezzo in _pezzi(arrivate):
        for p in sb("GET", f"/rest/v1/prospects?select=id,classificazione&id=in.({pezzo})") or []:
            classi[p["id"]] = p.get("classificazione") or ""
    analisi = {p["id"]: quando(p["analysis_sent_at"]) for p in sb_tutte(f"/rest/v1/prospects?select=id,analysis_sent_at&analysis_sent_at=gte.{da_z}")}
    fatte = {"follow-up": 0, "promemoria": 0, "risposta": 0}
    for x in sb_tutte(f"/rest/v1/proposte?select=id,prospect_id,risposta_il,ref,gruppo:azione->lettura->>gruppo,template:azione->>template,"
                      f"intento:azione->>intento&stato=eq.fatta&risposta_il=gte.{da_z}"):
        gruppo = (x.get("gruppo") or x.get("template") or x.get("intento") or "").upper()
        if str(x.get("ref") or "").startswith("promemoria") or "PROMEMORIA" in gruppo:
            fatte["promemoria"] += 1
        elif "FOLLOW" in gruppo or "RICONTATTO" in gruppo or "RINVIO" in gruppo:
            fatte["follow-up"] += 1
        elif x.get("prospect_id") in analisi and x.get("risposta_il") and abs((analisi[x["prospect_id"]] - quando(x["risposta_il"])).total_seconds()) < 3600:
            continue                                             # e' la mail con l'analisi: gia' contata
        else:
            fatte["risposta"] += 1
    analisi = len(analisi)
    pren = {"prenotato": 0, "spostata": 0, "cancellata": 0}
    for x in sb("GET", f"/rest/v1/prenotazioni_segnalate?select=tipo,come&quando=gte.{da_z}&tipo=in.(prenotato,spostata,cancellata)&limit=500") or []:
        if x.get("come") not in ("semina", "assorbita") and x["tipo"] in pren:
            pren[x["tipo"]] += 1
    r = sb("GET", "/rest/v1/snella_numeri?select=dati&chiave=eq.conversazioni") or []
    conv = ((r[0].get("dati") if r else None) or {})
    conv = {pid: v for pid, v in conv.items() if isinstance(v, dict) and v.get("dal")}
    entrati_oggi = sum(1 for v in conv.values() if quando(v.get("aperta_il") or v["dal"]) >= oggi0 and v.get("notificata"))
    da_chiamare = sb("GET", "/rest/v1/snella_lead?select=prospect_id,stato,richiamare_il,chiamata_il,aggiornato_il"
                            "&stato=eq.Da%20chiamare&limit=500") or []
    passati_oggi = sum(1 for x in da_chiamare if x.get("chiamata_il") and quando(x["chiamata_il"]) >= oggi0)
    numeri = {"risposte": len(arrivate), "si": sum(1 for c in classi.values() if c == "positivo"),
              "no": sum(1 for c in classi.values() if c in NO), "ooo": sum(1 for c in classi.values() if c == "ooo"),
              "analisi": analisi, "followup": fatte["follow-up"], "promemoria": fatte["promemoria"], "risposte_mandate": fatte["risposta"],
              "prenotate": pren["prenotato"], "spostate": pren["spostata"], "annullate": pren["cancellata"],
              "conversazioni": entrati_oggi, "da_chiamare": passati_oggi}
    # aspettano te
    aspettano = _aspettano(ora, oggi0, conv, da_chiamare)
    # domani: le call di Dre, dalla stessa lista dell'app (snella_numeri «call», scritta da schede.py)
    r = sb("GET", "/rest/v1/snella_numeri?select=dati&chiave=eq.call") or []
    call = (((r[0].get("dati") if r else None) or {}).get("call") or [])
    domani, viste = [], set()
    for c in call:
        if not c.get("at") or not c.get("di_dre", True) or c.get("tipo") == "annullata":
            continue
        t = quando(c["at"])
        if not domani0 <= t < dopodomani0:
            continue
        k = (t, c.get("meet") or c.get("titolo"))
        if k in viste:
            continue
        viste.add(k)
        domani.append({"at": t, "azienda": " ".join((c.get("azienda") or c.get("titolo") or "?").split()), "tipo": c.get("tipo") or ""})
    domani.sort(key=lambda c: c["at"])
    return {"guasti_aperti": aperti, "guasti_risolti": risolti, "serie_errori": serie, "controllo_fallito": fallito,
            "numeri": numeri, "aspettano": aspettano, "domani": domani}


def _automatica(testo):
    try:
        import segnale_provvisorio as SP
        return SP.automatica(testo or "")
    except Exception:                                            # noqa: BLE001
        return False


def _aspettano(ora, oggi0, conv, da_chiamare):
    """Le cose che aspettano Dre: [{"pid", "azienda", "perche", "quando"}], le piu' urgenti prima."""
    oggi = ora.astimezone(ROMA).date()
    voci = {}
    # 1. in conversazione, e l'ultima mail e' del lead
    recenti = {pid: quando(v["dal"]) for pid, v in conv.items() if ora - quando(v["dal"]) <= datetime.timedelta(days=CONVERSAZIONI_GIORNI)}
    if recenti:
        da = min(recenti.values()) - datetime.timedelta(days=1)
        posta = {}
        for pezzo in _pezzi(recenti):
            for x in sb_tutte(f"/rest/v1/interactions?select=id,prospect_id,at,kind,body&prospect_id=in.({pezzo})"
                              f"&kind=in.(email_in,email_out)&at=gte.{_z(da)}&order=at.asc"):
                posta.setdefault(x["prospect_id"], []).append(x)
        for pid, dal in recenti.items():
            ultima_sua, ultima_nostra = None, None
            for x in posta.get(pid, []):
                t = quando(x["at"])
                if x["kind"] == "email_in" and t >= dal and not _automatica(x.get("body")):
                    ultima_sua = t
                elif x["kind"] == "email_out":
                    ultima_nostra = t
            if ultima_sua and (not ultima_nostra or ultima_nostra < ultima_sua):
                voci[pid] = {"pid": pid, "quando": ultima_sua, "perche": f"ha scritto {_quando_breve(ultima_sua, ora)} e aspetta la tua risposta", "peso": 0}
    # 2. da chiamare: oggi, o rimasto indietro
    for x in da_chiamare:
        pid = x["prospect_id"]
        r = x.get("richiamare_il")
        giorno = datetime.date.fromisoformat(r) if r else None
        if giorno and giorno > oggi:
            continue
        perche = "da chiamare oggi" if (not giorno or giorno == oggi) else f"da chiamare, era per {GIORNI[giorno.weekday()]} {giorno:%d/%m}"
        t = quando(x["chiamata_il"]) if x.get("chiamata_il") else oggi0
        if pid in voci:
            voci[pid]["perche"] += f", e {perche}"
        else:
            voci[pid] = {"pid": pid, "quando": t, "perche": perche, "peso": 1}
    # 3. una risposta ferma «da guardare tu», degli ultimi due giorni
    ferme = sb("GET", "/rest/v1/proposte?select=prospect_id,at&stato=eq.aperta&tipo=eq.umano&prospect_id=not.is.null"
                      f"&at=gte.{_z(ora - datetime.timedelta(hours=DA_GUARDARE_ORE))}&order=at.desc&limit=200") or []
    for x in ferme:
        pid = x["prospect_id"]
        if pid in voci:
            continue
        voci[pid] = {"pid": pid, "quando": quando(x["at"]), "perche": "una risposta da decidere: Manda o Non mandare", "peso": 2}
    if not voci:
        return []
    # chi non e' piu' un lead (cliente, perso, in pipeline) o che Dre ha chiuso nell'app non aspetta niente
    schede = {}
    for pezzo in _pezzi(voci):
        for p in sb("GET", "/rest/v1/prospects?select=id,company,name,fuori,stage,pipeline_stage,no_followup,classificazione"
                           f"&id=in.({pezzo})") or []:
            schede[p["id"]] = p
    stati = {}
    for pezzo in _pezzi(voci):
        for x in sb("GET", f"/rest/v1/snella_lead?select=prospect_id,stato&prospect_id=in.({pezzo})") or []:
            stati[x["prospect_id"]] = x.get("stato")
    out = []
    for pid, v in voci.items():
        p = schede.get(pid)
        if not p or stati.get(pid) in CHIUSI:
            continue
        if v["peso"] != 1 and not contattabile(p):
            continue
        out.append({**v, "azienda": " ".join((p.get("company") or p.get("name") or "?").split())})
    out.sort(key=lambda v: (v["peso"], -v["quando"].timestamp()))
    return out


# ── il testo (puro: si prova con dati finti) ───────────────────────

def _n(k, uno, tanti):
    return f"{k} {uno if k == 1 else tanti}"


def quadro(dati):
    """Le righe del quadro del sistema. Una sola se e' andato tutto bene."""
    righe = []
    for g in dati.get("guasti_aperti") or []:
        righe.append(f"È successo: {g['cosa']}, dalle {_ora(g['da'])} e ancora adesso. Soluzione: {g.get('sta_facendo') or 'il sistema riprova da solo.'}")
    for g in dati.get("guasti_risolti") or []:
        righe.append(f"È successo: {g['cosa']}, dalle {_ora(g['da'])} alle {_ora(g['risolto_il'])}. "
                     "Soluzione: si è rimesso da solo, non devi fare niente.")
    for s in dati.get("serie_errori") or []:
        if s.get("ripartita"):
            righe.append(f"È successo: {s['nome']} è caduta {s['n']} volte di fila dalle {_ora(s['da'])}. "
                         f"Soluzione: è ripartita da sola alle {_ora(s['ripartita'])}.")
        else:
            righe.append(f"È successo: {s['nome']} è caduta {s['n']} volte di fila dalle {_ora(s['da'])} e non è ancora ripartita. "
                         "Soluzione: la guarda Achille, a te non serve fare niente.")
    if dati.get("controllo_fallito"):
        righe.append("Non sono riuscito a controllare il semaforo stasera: lo guarda Achille domattina.")
    if not righe:
        righe.append("Il sistema ha funzionato regolarmente.")
    return righe


def numeri(dati):
    n = dati.get("numeri") or {}
    pezzi = []
    if n.get("risposte"):
        dentro = [x for x in (f"{n['si']} sì" if n.get("si") else "", f"{n['no']} no" if n.get("no") else "",
                              f"{n['ooo']} fuori ufficio" if n.get("ooo") else "") if x]
        pezzi.append(_n(n["risposte"], "risposta arrivata", "risposte arrivate") + (f" ({', '.join(dentro)})" if dentro else ""))
    if n.get("analisi"):
        pezzi.append(_n(n["analisi"], "analisi mandata", "analisi mandate"))
    if n.get("risposte_mandate"):
        pezzi.append(_n(n["risposte_mandate"], "altra risposta mandata", "altre risposte mandate"))
    if n.get("followup"):
        pezzi.append(_n(n["followup"], "follow-up partito", "follow-up partiti"))
    if n.get("promemoria"):
        pezzi.append(_n(n["promemoria"], "promemoria di call", "promemoria di call"))
    if n.get("prenotate"):
        pezzi.append(_n(n["prenotate"], "call prenotata", "call prenotate"))
    if n.get("spostate"):
        pezzi.append(_n(n["spostate"], "call spostata", "call spostate"))
    if n.get("annullate"):
        pezzi.append(_n(n["annullate"], "call annullata", "call annullate"))
    if n.get("conversazioni"):
        pezzi.append(_n(n["conversazioni"], "lead entrato in conversazione", "lead entrati in conversazione"))
    if n.get("da_chiamare"):
        pezzi.append(_n(n["da_chiamare"], "lead passato a «Da chiamare»", "lead passati a «Da chiamare»"))
    if not pezzi:
        return "Oggi non è successo niente: nessuna risposta, nessuna mail partita."
    return "Oggi: " + ", ".join(pezzi) + "."


def link_scheda(pid):
    from foglio_lead import link_scheda as _l
    return _l(pid)


def componi(ora, dati, link=None):
    """(oggetto, testo, html). `link` si passa nelle prove."""
    link = link or link_scheda
    e = html.escape
    oggetto = f"La giornata di {giorno_breve(ora)}"
    righe_q = quadro(dati)
    riga_n = numeri(dati)
    asp = dati.get("aspettano") or []
    dom = dati.get("domani") or []
    t, h = [], []
    for r in righe_q:
        t.append(r)
        h.append(f"<p style='margin:0 0 6px;font-weight:600'>{e(r)}</p>")
    t.append("")
    t.append(riga_n)
    h.append(f"<p style='margin:12px 0 0'>{e(riga_n)}</p>")
    t += ["", "Aspettano te"]
    h.append("<p style='margin:18px 0 4px;font-weight:600'>Aspettano te</p>")
    if not asp:
        t.append("Niente da parte tua.")
        h.append("<p style='margin:0'>Niente da parte tua.</p>")
    else:
        h.append("<ul style='margin:0;padding-left:18px'>")
        for v in asp[:MAX_ASPETTANO]:
            url = link(v["pid"])
            t.append(f"- {v['azienda']}: {v['perche']}\n  {url}")
            h.append(f"<li style='margin:0 0 4px'>{e(v['azienda'])}: {e(v['perche'])}, <a href='{e(url)}'>scheda</a></li>")
        h.append("</ul>")
        if len(asp) > MAX_ASPETTANO:
            resto = f"…e {_n(len(asp) - MAX_ASPETTANO, 'altro', 'altri')} che aspettano una tua decisione: li trovi nel foglio."
            t.append(resto)
            h.append(f"<p style='margin:4px 0 0;color:#666'>{e(resto)}</p>")
    t += ["", "Domani"]
    h.append("<p style='margin:18px 0 4px;font-weight:600'>Domani</p>")
    if not dom:
        t.append("Nessuna call.")
        h.append("<p style='margin:0'>Nessuna call.</p>")
    else:
        h.append("<ul style='margin:0;padding-left:18px'>")
        for c in dom:
            tipo = f", {c['tipo']}" if c.get("tipo") and c["tipo"] != "altro" else ""
            t.append(f"- {_ora(c['at'])} {c['azienda']}{tipo}")
            h.append(f"<li style='margin:0 0 4px'>{_ora(c['at'])} {e(c['azienda'])}{e(tipo)}</li>")
        h.append("</ul>")
    sereno = not asp and not (dati.get("guasti_aperti") or dati.get("serie_errori"))
    chiusura = "Niente da fare stasera: buona serata." if sereno else "Il resto va avanti da solo. Buona serata."
    t += ["", chiusura]
    h.append(f"<p style='margin:18px 0 0'>{e(chiusura)}</p>")
    testo = "\n".join(t)
    corpo = ("<div style='font-family:-apple-system,Helvetica,Arial,sans-serif;font-size:15px;line-height:1.45;max-width:560px'>"
             + "".join(h) + "</div>")
    return oggetto, testo, corpo


# ── il giro ────────────────────────────────────────────────────────

def gia_partita(oggetto, oggi0):
    import segnale_provvisorio as SP
    return SP._gmail_inviata(oggetto, oggi0)


def main():
    ora = adesso()
    dati = leggi(ora)
    oggetto, testo, corpo = componi(ora, dati)
    if _a_secco():
        print(f"(prova) Oggetto: {oggetto}\n\n{testo}\n\n(prova) niente mandato")
        return
    import segnale_provvisorio as SP
    # notte del 22/10: «partita oggi» e' un fatto scritto da chi la manda (snella_numeri «giornata»),
    # non solo una ricerca nella posta inviata: se Gmail non rispondeva, la mail partiva una seconda volta
    giorno = ora.astimezone(ROMA).date().isoformat()
    segno = (sb("GET", "/rest/v1/snella_numeri?select=dati&chiave=eq.giornata") or [{}])[0].get("dati") or {}
    if segno.get("mandata_il") == giorno:
        print(f"la mail di oggi è già partita ({oggetto}): non la rimando")
        return
    try:
        if gia_partita(oggetto, inizio_giorno(ora)):
            print(f"la mail di oggi è già partita ({oggetto}): non la rimando")
            return
    except Exception as e:                                       # noqa: BLE001
        print(f"  (non riesco a guardare la posta inviata: {str(e)[:100]}; il segno di oggi non c'e', la mando)")
    SP.manda_mail(SP.DRE, oggetto, testo, corpo)
    sb("POST", "/rest/v1/snella_numeri?on_conflict=chiave", [{"chiave": "giornata", "dati": {"mandata_il": giorno, "oggetto": oggetto},
                                                              "aggiornato_il": ora.isoformat()}],
       {"Prefer": "resolution=merge-duplicates,return=minimal"})
    print(f"mandata a Dre: {oggetto}\n\n{testo}")


if __name__ == "__main__":
    main()
