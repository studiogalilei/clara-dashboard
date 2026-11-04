#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""IL TURNO DELLA SERA (4/11/2026): chi controlla Clara e riferisce a Dre. Non fa niente, riferisce.

Dre, 4/11 mattina: «un Claude di turno che ogni giorno controlla cosa ha fatto e come, per
assicurarsi che non dica cazzate; quel Claude non fa niente, deve solo riferirmi».

Cosa fa, una volta al giorno dentro «La giornata» (giornata.py, ore 19):
1. Ogni mail che Clara ha mandato nelle ultime 24 ore la rilegge il giudice (Opus, un altro
   modello) con quello che e' successo DOPO: la mail com'e' partita davvero e la reazione del lead,
   se c'e' gia'. Il voto si salva in clara_decisioni.giudice["dopo"] (una volta sola).
2. Raccoglie le mail ferme (il giudice le ha dette pericolose, o il postino non e' riuscito), le
   cose che restano a Dre (call da fare, «decidi tu»), e la spesa del giorno.
3. Torna tutto a giornata.py, che lo scrive nella mail della sera in italiano semplice.

Uso:
  python3 scripts/clara_turno.py --prova     stampa il rapporto di oggi, non salva i voti
"""
import datetime
import json
import os
import sys
import zoneinfo

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from stanza import sb, sb_tutte  # noqa: E402

ROMA = zoneinfo.ZoneInfo("Europe/Rome")
PROVA = os.environ.get("PROVA") == "1" or "--prova" in sys.argv
NOME_MOSSA = {"send_analysis": "l’analisi", "reply": "una risposta", "offer_slots": "due orari", "book_meeting": "la conferma della call",
              "callback": "da chiamare", "escalate": "decidi tu", "wait": "aspetta", "close": "chiude"}
MAX_RILETTURE = 25          # mail rilette dal giudice per sera: un tetto alla spesa, non una coda persa
CAMPI = "id,prospect_id,risposta_il,mossa,owner,testo,testo_finale,perche,prove,richiamo,segnali,giudice,stato,errore,contesto,inviata_il,invio,creato_il,approvata_da,prospects(company,name,email)"


def _z(t):
    return t.astimezone(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _quando(iso):
    from stanza import quando
    return quando(iso)


def _azienda(d):
    p = d.get("prospects") or {}
    return " ".join((p.get("company") or p.get("name") or p.get("email") or "?").split())


def _pulisci(html_):
    import re
    import html as H
    t = re.sub(r"<br\s*/?>|</p>|</div>", "\n", html_ or "", flags=re.I)
    t = re.sub(r"<[^>]+>", "", t)
    t = H.unescape(t)
    return re.sub(r"\n{3,}", "\n\n", t).strip()


def _dopo(d):
    """Cosa c'e' nel filo DOPO la risposta del lead su cui Clara ha deciso: la nostra mail com'e' partita
    e la reazione del lead, se c'e'. Testo per il giudice."""
    import manda
    inv = d.get("invio") or {}
    cid, lid = inv.get("campagna"), inv.get("lead")
    if not (cid and lid):
        return "(non so quale filo: niente da rileggere)"
    h = manda.sl("GET", f"/campaigns/{cid}/leads/{lid}/message-history") or {}
    da = _quando(d["risposta_il"]) + datetime.timedelta(minutes=3)
    righe = []
    for m in h.get("history") or []:
        t = _quando(m.get("time"))
        if not t or t < da:
            continue
        chi = "IL LEAD" if m.get("type") == "REPLY" else "NOI (la mail partita davvero)"
        righe.append(f"{chi}, {t.astimezone(ROMA):%d/%m %H:%M}:\n{_pulisci(m.get('email_body'))[:2500]}")
    return "\n\n".join(righe) or "(la mail risulta partita ma nel filo non c'è ancora niente dopo)"


def rileggi(d):
    """Il giudice rilegge una mail mandata, con il dopo. Salva il voto in giudice.dopo. Torna il voto."""
    import esame_clara
    r = {"contesto": d.get("contesto") or "", "segnali": d.get("segnali") or [],
         "decisione": {"proposed_action": d["mossa"], "reason_summary": d.get("perche"), "evidence_refs": d.get("prove"),
                       "owner": d.get("owner"), "due_at": None, "draft": d.get("testo_finale") or d.get("testo"), "callback": d.get("richiamo")},
         "dopo": _dopo(d)}
    g = esame_clara.giudica(r)
    g["il"] = datetime.datetime.now(ROMA).isoformat()
    if not PROVA:
        nuovo = dict(d.get("giudice") or {})
        nuovo["dopo"] = g
        sb("PATCH", f"/rest/v1/clara_decisioni?id=eq.{d['id']}", {"giudice": nuovo}, {"Prefer": "return=minimal"})
    return g


def rapporto(ora=None):
    """Il rapporto delle ultime 24 ore: {"inviate", "ferme", "da_te", "spesa", "riletture"}. Ogni voce ha
    azienda, cosa, e il verdetto in una parola. Non manda e non cambia stati."""
    ora = ora or datetime.datetime.now(datetime.timezone.utc)
    da = _z(ora - datetime.timedelta(hours=24))
    inviate = sb_tutte(f"/rest/v1/clara_decisioni?select={CAMPI}&stato=eq.inviata&inviata_il=gte.{da}&order=inviata_il.asc")
    fuori_inviate, riletture = [], 0
    for d in inviate:
        g = (d.get("giudice") or {}).get("dopo")
        if not g and riletture < MAX_RILETTURE:
            try:
                g = rileggi(d)
                riletture += 1
            except Exception as e:                               # noqa: BLE001
                g = {"errore": str(e)[:150]}
        g = g or {}
        fuori_inviate.append({"id": d["id"], "pid": d["prospect_id"], "azienda": _azienda(d), "cosa": NOME_MOSSA.get(d["mossa"], d["mossa"]),
                              "quando": _quando(d["inviata_il"]), "a": (d.get("invio") or {}).get("a"),
                              "pericoloso": bool(g.get("pericoloso")), "mossa": g.get("mossa"), "testo": g.get("testo"),
                              "nota": g.get("errore_pericoloso") if g.get("pericoloso") else (g.get("nota") or ""),
                              "da_chi": d.get("approvata_da") or "", "errore": g.get("errore")})
    # ferme: una mail che non e' partita e ha un motivo scritto (giudice o postino)
    ferme = []
    for d in sb_tutte(f"/rest/v1/clara_decisioni?select={CAMPI}&stato=in.(proposta,approvata)&errore=not.is.null"
                      f"&mossa=in.(send_analysis,reply,offer_slots,book_meeting)&order=creato_il.desc"):
        ferme.append({"id": d["id"], "pid": d["prospect_id"], "azienda": _azienda(d), "cosa": NOME_MOSSA.get(d["mossa"], d["mossa"]),
                      "perche": d["errore"], "quando": _quando(d["creato_il"])})
    # a Dre: le call da fare e i «decidi tu» ancora aperti
    da_te = []
    for d in sb_tutte(f"/rest/v1/clara_decisioni?select={CAMPI}&stato=eq.proposta&mossa=in.(callback,escalate)&order=creato_il.desc"):
        ric = d.get("richiamo") or {}
        perche = d.get("perche") or ""
        if d["mossa"] == "callback" and ric.get("numero"):
            perche = f"{ric.get('numero')}" + (f", {ric.get('quando')}" if ric.get("quando") else "") + (f": {ric.get('perche')}" if ric.get("perche") else "")
        da_te.append({"id": d["id"], "pid": d["prospect_id"], "azienda": _azienda(d), "cosa": NOME_MOSSA.get(d["mossa"], d["mossa"]),
                      "perche": _breve(perche), "quando": _quando(d["creato_il"])})
    spesa = 0.0
    try:
        import lettore
        spesa = float(lettore.spesa_di_oggi("clara_sdr") or 0) + float(lettore.spesa_di_oggi("esame_clara") or 0)
    except Exception:                                            # noqa: BLE001
        pass
    decise = sb("GET", f"/rest/v1/clara_decisioni?select=mossa&creato_il=gte.{da}&limit=1000") or []
    return {"inviate": fuori_inviate, "ferme": ferme, "da_te": da_te, "spesa": round(spesa, 2), "riletture": riletture,
            "decise": len(decise), "attese": sum(1 for x in decise if x["mossa"] == "wait"), "chiuse": sum(1 for x in decise if x["mossa"] == "close")}


def _breve(testo, massimo=150):
    """La prima frase, o le prime parole fino al massimo: Dre legge una riga, non un perche' intero."""
    import re
    t = " ".join((testo or "").split())
    m = re.match(r"(.{20,%d}?[.!?])(\s|$)" % massimo, t)
    if m:
        return m.group(1)
    if len(t) <= massimo:
        return t
    return t[:massimo].rsplit(" ", 1)[0] + "…"


def _verdetto(v):
    if v.get("errore"):
        return "non riletta"
    if v.get("pericoloso"):
        return "DA GUARDARE: " + (v.get("nota") or "")[:140]
    m = {"giusta": "giusta", "accettabile": "accettabile", "sbagliata": "mossa sbagliata"}.get(v.get("mossa") or "", "")
    t = {"buono": "", "nessuno": "", "da_ritoccare": ", testo da ritoccare", "da_rifare": ", testo da rifare"}.get(v.get("testo") or "", "")
    return (m + t) or "rilettura senza voto"


def righe(rap):
    """Il rapporto in righe di testo semplice (le stesse che finiscono nella mail della sera)."""
    out = []
    n = len(rap["inviate"])
    if n:
        out.append(f"Clara ha mandato {n} mail da sola" + (f" ({rap['riletture']} rilette stasera dal giudice)" if rap.get("riletture") else "") + ":")
        for v in rap["inviate"]:
            out.append(f"- {v['azienda']}: {v['cosa']}, {v['quando'].astimezone(ROMA):%H:%M}. Rilettura: {_verdetto(v)}")
    else:
        out.append("Clara oggi non ha mandato mail.")
    out.append(f"Ha letto {rap['decise']} risposte: {rap['attese']} aspettano, {rap['chiuse']} chiuse. Spesa di oggi: {rap['spesa']:.2f} $.")
    if rap["ferme"]:
        out.append("Ferme, decidi tu:")
        for v in rap["ferme"]:
            out.append(f"- {v['azienda']}: {v['cosa']} ferma perché {v['perche']}")
    if rap["da_te"]:
        out.append("Tue:")
        for v in rap["da_te"]:
            out.append(f"- {v['azienda']}: {v['cosa']}" + (f", {v['perche']}" if v["perche"] else ""))
    return out


if __name__ == "__main__":
    print("\n".join(righe(rapporto())))
