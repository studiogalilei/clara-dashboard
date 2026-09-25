#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""LA RIPRESA — i follow-up a chi ci aveva risposto e non ha piu' avuto niente (25/9/2026).

Dre, 25/9: «voglio fare i follow-up, tutti, prepara tutto e invia, con precisione
chirurgica; la solita scusa: ci siamo accorti adesso che la mail che avevamo
mandato non era partita». Tono deciso il 23/9: ammettere, allegare l'analisi,
non chiedere; il calendario solo a chi era positivo.

DUE GRUPPI
  RIPRESA        ha scritto lui per ultimo piu' di 30 giorni fa e non ha mai avuto
                 la nostra risposta (positivo, parziale o da capire dopo la rilettura)
  RINVIO SCADUTO aveva detto «risentiamoci a…» e la data e' passata

FUORI: fit NO, no_followup (gigante buono), soppressi, persona sbagliata, nervosi,
negativi, chi ha gia' avuto una nostra mail dopo la sua, chi e' in pipeline o cliente.
L'ANALISI: se manca e il fit non e' NO, si fa adesso (analisi_auto); senza analisi
non si scrive (la mail promette l'allegato).
LE BOZZE: template qui sotto, parola per parola; nome della persona se c'e'.
Vanno in Posta come «risposta», con analisi e presentazione in allegato; Dre
approva (o approva in blocco, su suo ordine) e manda.py le spedisce.

USO
  python3 scripts/ripresa.py --prova            conta e mostra i primi
  python3 scripts/ripresa.py --campione         una bozza per gruppo, in Posta (per il tono)
  python3 scripts/ripresa.py                    tutte le bozze in Posta
"""
import datetime
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from stanza import sb, proponi                              # noqa: E402

GIORNI = 30
CALENDARIO = "https://calendar.app.google/zNMQ2apeE5SGGwA86"

RIPRESA = """Salve{nome},

le avevo risposto qualche settimana fa, ma ci siamo accorti solo ora che il messaggio non era partito: le riscrivo perché non vada perso, e mi scuso per l'attesa.

Le lascio qui l'analisi esterna che avevamo preparato sulla vostra attività: uno sguardo dall'esterno su come intercettare la domanda che oggi esiste su Google per un'azienda come la vostra. Allego anche una breve presentazione di Studio Galilei, per darle un po' di contesto su chi siamo e su come lavoriamo.
{chiusura}
Un saluto"""

RINVIO = """Salve{nome},

ci eravamo detti di risentirci più avanti, e ci siamo: le riscrivo come promesso.

Le lascio qui l'analisi esterna che avevamo preparato sulla vostra attività: uno sguardo dall'esterno su come intercettare la domanda che oggi esiste su Google per un'azienda come la vostra. Allego anche una breve presentazione di Studio Galilei, per darle un po' di contesto su chi siamo e su come lavoriamo.
{chiusura}
Un saluto"""

CHIUSURA_SI = """
Se le fa piacere approfondire, qui trova il calendario per scegliere il giorno più comodo: {cal}
"""
CHIUSURA_NO = """
Se le fa piacere approfondire, mi scriva pure e ci sentiamo. In caso contrario nessun problema: l'analisi resta sua.
"""


def nome_di(p):
    n = re.sub(r"\s+", " ", (p.get("name") or "").strip()).split(" ")[0] if p.get("name") else ""
    return f" {n}" if re.fullmatch(r"[A-Za-zÀ-ÿ'\-]{2,}", n or "") and n.lower() not in ("info", "amministrazione", "ufficio", "segreteria") else ""


def bozza_per(p, gruppo):
    fit = ((p.get("enriched") or {}).get("google_fit") or {})
    chi = CHIUSURA_SI.format(cal=CALENDARIO)      # Dre, 25/9: «proporli la call», a tutti
    t = (RIPRESA if gruppo == "RIPRESA" else RINVIO).format(nome=nome_di(p), chiusura=chi)
    if fit.get("settore") and fit.get("settore") != "altro":
        t = t.replace("per un'azienda come la vostra", f"per un'azienda come la vostra")
    return t


def gia_scritto_da_gmail(email):
    """PRECISIONE (Dre): «ci siamo accorti che la mail non era partita» vale solo se
    davvero non gli abbiamo mai scritto. Si guarda anche in Gmail (Dre e Lorenzo),
    senza limite di tempo: una mail nostra a quell'indirizzo e si salta."""
    try:
        import urllib.parse
        from google_api import g
        for chi in ("dramane@studiogalilei.com", "lorenzo@studiogalilei.com"):
            q = urllib.parse.quote(f"to:{email} from:me")
            r = g("GET", f"https://gmail.googleapis.com/gmail/v1/users/me/messages?q={q}&maxResults=1", email=chi) or {}
            if r.get("messages"):
                return chi
    except Exception as e:                                        # noqa: BLE001
        print(f"    (gmail non controllabile per {email}: {str(e)[:60]})")
    return None


def candidati():
    oggi = datetime.date.today()
    rs = sb("GET", "/rest/v1/prospects?select=id,name,company,email,classificazione,analysis_pdf,analysis_sent,last_reply_at,next_action_date,enriched,website"
                   "&last_reply_at=not.is.null&fuori=eq.false&stage=not.in.(perso,cliente)&no_followup=eq.false"
                   "&classificazione=in.(positivo,tiepido,rinvio,da_classificare)&limit=3000") or []
    outs = {}
    for r in sb("GET", "/rest/v1/interactions?select=prospect_id,at&kind=in.(email_out,followup,analisi)&order=at.desc&limit=6000") or []:
        outs.setdefault(r["prospect_id"], r["at"])
    gia = {x["prospect_id"] for x in (sb("GET", "/rest/v1/proposte?select=prospect_id&azione->>template=in.(RIPRESA,RINVIO%20SCADUTO)&limit=5000") or [])}
    out = []
    for p in rs:
        if p["id"] in gia:
            continue
        fit = ((p.get("enriched") or {}).get("google_fit") or {})
        if fit.get("verdetto") == "NO":
            continue
        lr = p["last_reply_at"][:10]
        if p["classificazione"] == "rinvio":
            q = p.get("next_action_date")
            if q and q < oggi.isoformat():
                out.append((p, "RINVIO SCADUTO"))
            continue
        if (outs.get(p["id"]) or "")[:10] < lr and (oggi - datetime.date.fromisoformat(lr)).days > GIORNI:
            out.append((p, "RIPRESA"))
    return out


def con_analisi(p, prova):
    if p.get("analysis_pdf"):
        return p["analysis_pdf"]
    if prova:
        return None
    try:
        import analisi_auto
        ok = analisi_auto.lavora(p)
        if ok:
            q = (sb("GET", f"/rest/v1/prospects?select=analysis_pdf&id=eq.{p['id']}") or [{}])[0]
            return q.get("analysis_pdf")
    except Exception as e:                                        # noqa: BLE001
        print(f"    analisi non fatta: {str(e)[:100]}")
    return None


def main():
    prova = "--prova" in sys.argv
    campione = "--campione" in sys.argv
    cand = candidati()
    print(f"candidati: {len(cand)}  (RIPRESA {sum(1 for _, g in cand if g == 'RIPRESA')}, RINVIO SCADUTO {sum(1 for _, g in cand if g != 'RIPRESA')})")
    print(f"  senza analisi pronta: {sum(1 for p, _ in cand if not p.get('analysis_pdf'))}")
    fatti, visti = 0, set()
    for p, gruppo in cand:
        if campione and gruppo in visti:
            continue
        nome = (p.get("company") or p.get("email"))[:36]
        if prova:
            print(f"  {gruppo:15} {nome:36} {p['classificazione']:16} {'pdf' if p.get('analysis_pdf') else 'NO PDF'}")
            continue
        chi = gia_scritto_da_gmail(p["email"])
        if chi:
            print(f"  {gruppo:15} {nome:36} salto: gli ha già scritto {chi.split('@')[0]} da Gmail"); continue
        pdf = con_analisi(p, prova)
        if not pdf:
            print(f"  {gruppo:15} {nome:36} salto: senza analisi"); continue
        testo = bozza_per(p, gruppo)
        # una bozza «normale» gia' aperta per lui (scritta come se avesse risposto ieri)
        # non regge dopo settimane: si chiude e la ripresa prende il suo posto
        import datetime as _dt
        for v_ in sb("GET", f"/rest/v1/proposte?select=id&prospect_id=eq.{p['id']}&stato=eq.aperta&tipo=in.(risposta,umano)") or []:
            sb("PATCH", f"/rest/v1/proposte?id=eq.{v_['id']}", {"stato": "no", "risposta": "sostituita dalla ripresa del 25/9 (la risposta è vecchia di settimane)", "risposta_il": _dt.datetime.now(_dt.timezone.utc).isoformat()})
        proponi("risposta", f"{'Ripresa' if gruppo == 'RIPRESA' else 'Rinvio scaduto'}: {nome}", prospect_id=p["id"],
                perche=("Ha scritto lui per ultimo il " + p["last_reply_at"][:10] + " e non ha mai avuto risposta: la scusa di Dre, analisi e presentazione in allegato." if gruppo == "RIPRESA"
                        else "Aveva chiesto di risentirci e la data (" + str(p.get("next_action_date")) + ") è passata: ci facciamo vivi come promesso, con analisi e presentazione.")[:280],
                azione={"bozza": testo, "intento": "RIPRESA", "template": gruppo, "allega": True, "allega_presentazione": True})
        visti.add(gruppo); fatti += 1
        print(f"  {gruppo:15} {nome:36} bozza in Posta")
        if campione and len(visti) == 2:
            break
    print(f"ripresa: {fatti} bozze")


if __name__ == "__main__":
    main()
