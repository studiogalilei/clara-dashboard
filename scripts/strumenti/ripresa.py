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
LE BOZZE (25/9, nessuna bozza senza lettura): questo script NON scrive piu'.
Mette in coda (prospects.coda = il gruppo) e il motore delle bozze legge il filo
vero, verifica che il gruppo regga (mai scritto dopo la sua mail, analisi mai
ricevuta, nessun no, nessuna autorisposta), scrive col template di Dre e passa
dalla seconda testa. Il 25/9 il metodo vecchio (template alla cieca, approva
tutte) ha mandato 4 mail sbagliate su 10: Dre, «elimina subito».

USO
  python3 scripts/strumenti/ripresa.py --prova   conta e mostra
  python3 scripts/strumenti/ripresa.py           mette in coda (--ooo: il gruppo dopo le ferie)
"""
import datetime
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))   # i moduli comuni stanno in scripts/
from stanza import sb                                       # noqa: E402

GIORNI = 30

def gia_avute(*template):
    """Chi ha gia' avuto quella proposta: aperta, mandata, o rifiutata da Dre («NO: ...»).
    Le proposte chiuse dagli script il 25/9 (scritte senza lettura) non contano: si rifanno."""
    rs = sb("GET", f"/rest/v1/proposte?select=prospect_id,stato,risposta&azione->>template=in.({','.join(template)})&limit=5000") or []
    return {x["prospect_id"] for x in rs if x["stato"] != "no" or (x.get("risposta") or "").startswith("NO:")}


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
    rs = sb("GET", "/rest/v1/prospects?select=id,name,company,email,classificazione,analysis_pdf,analysis_sent,last_reply_at,next_action_date,enriched,website,coda"
                   "&last_reply_at=not.is.null&fuori=eq.false&stage=not.in.(perso,cliente)&no_followup=eq.false"
                   "&classificazione=in.(positivo,tiepido,rinvio)&campaign=not.ilike.*USA*&limit=3000") or []      # da_classificare: prima la rilettura; USA: fuori dal giro
    outs = {}
    for r in sb("GET", "/rest/v1/interactions?select=prospect_id,at&kind=in.(email_out,followup,analisi)&order=at.desc&limit=6000") or []:
        outs.setdefault(r["prospect_id"], r["at"])
    gia = gia_avute("RIPRESA", "RINVIO%20SCADUTO", "RICONTATTO%20OOO")
    out = []
    if "--ooo" in sys.argv:
        # DOPO LE FERIE (Dre, 25/9): chi ci ha risposto solo con un'assenza ha comunque risposto,
        # quindi l'analisi puo' viaggiare in allegato. Solo chi e' in target: il fit si fa qui se manca.
        import googlefit
        zone, settori = googlefit.carica_fogli()
        ooo = sb("GET", "/rest/v1/prospects?select=id,name,company,email,classificazione,analysis_pdf,analysis_sent,last_reply_at,next_action_date,enriched,website,coda"
                        "&fuori=eq.false&stage=not.in.(perso,cliente)&no_followup=eq.false&analysis_sent=eq.false&classificazione=eq.ooo&campaign=not.ilike.*USA*&limit=3000") or []
        for p in ooo:
            if p["id"] in gia or p.get("coda"):
                continue
            fit = ((p.get("enriched") or {}).get("google_fit") or {})
            if not fit.get("verdetto"):
                try:
                    fit = googlefit.valuta(p, zone, settori)
                    arr = dict(p.get("enriched") or {}); arr["google_fit"] = fit
                    sb("PATCH", f"/rest/v1/prospects?id=eq.{p['id']}", {"enriched": arr}); p["enriched"] = arr
                    print(f"  fit {fit['verdetto']:8} {(p.get('company') or p['email'])[:34]}")
                except Exception as e:                                # noqa: BLE001
                    print(f"  fit non fatto per {(p.get('company') or p['email'])[:30]}: {str(e)[:60]}"); continue
            if fit.get("verdetto") == "NO":
                continue
            out.append((p, "RICONTATTO OOO"))
        return out
    for p in rs:
        if p["id"] in gia or p.get("coda"):
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


def main():
    prova = "--prova" in sys.argv
    cand = candidati()
    print(f"candidati: {len(cand)}  " + ", ".join(f"{g} {sum(1 for _, x in cand if x == g)}" for g in sorted({g for _, g in cand})))
    print(f"  senza analisi pronta: {sum(1 for p, _ in cand if not p.get('analysis_pdf'))} (la fa l'operazione analisi, il motore aspetta)")
    fatti = 0
    for p, gruppo in cand:
        nome = (p.get("company") or p.get("email"))[:36]
        if prova:
            print(f"  {gruppo:15} {nome:36} {p['classificazione']:16} {'pdf' if p.get('analysis_pdf') else 'NO PDF'}")
            continue
        chi = gia_scritto_da_gmail(p["email"])
        if chi:
            print(f"  {gruppo:15} {nome:36} salto: gli ha già scritto {chi.split('@')[0]} da Gmail"); continue
        # una bozza «normale» gia' aperta per lui (scritta come se avesse risposto ieri)
        # non regge dopo settimane: si chiude e la coda prende il suo posto
        for v_ in sb("GET", f"/rest/v1/proposte?select=id&prospect_id=eq.{p['id']}&stato=eq.aperta&tipo=in.(risposta,umano)") or []:
            sb("PATCH", f"/rest/v1/proposte?id=eq.{v_['id']}", {"stato": "no", "risposta": f"sostituita dalla coda {gruppo} (la risposta è vecchia di settimane)", "risposta_il": datetime.datetime.now(datetime.timezone.utc).isoformat()})
        sb("PATCH", f"/rest/v1/prospects?id=eq.{p['id']}", {"coda": gruppo, "coda_il": datetime.datetime.now(datetime.timezone.utc).isoformat()})
        fatti += 1
        print(f"  {gruppo:15} {nome:36} in coda")
    print(f"ripresa: {fatti} in coda (il motore delle bozze legge e scrive al prossimo giro)")


if __name__ == "__main__":
    main()
