#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""IL FOLLOW-UP COME FLUSSO (24/9/2026).

Dre, 24/9: accettata l'idea «ora che Clara manda, i follow-up diventano una
fila in Posta: template FOLLOW UP 1, Approva e manda, uno dopo l'altro».

Chi: ha ricevuto l'analisi da almeno 5 giorni (playbook), non ha piu' scritto,
non e' fuori, non e' perso, non ha il «niente follow-up» (gigante buono), non
ha gia' avuto un follow-up (una mail nostra dopo l'analisi, o una proposta
FOLLOW UP 1 di qualunque stato).
Cosa (25/9, nessuna bozza senza lettura): questo script NON scrive piu' il
testo. Mette la persona IN CODA (prospects.coda = «FOLLOW UP 1» o «MINI FOLLOW
UP») e il motore delle bozze (bozze.py) legge il filo vero, applica il template
di Dre e passa dalla seconda testa. Il template sta nel file di Dre «Risposte
(template verbatim)».

USO
  python3 scripts/followup.py            propone
  python3 scripts/followup.py --prova    mostra e non propone
"""
import datetime
import os
import sys
import urllib.parse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from stanza import sb, sb_tutte                                       # noqa: E402

GIORNI = 5
QUANTI = 50
CLASSI = "positivo,tiepido,da_classificare"


def gia_avute(*template):
    """Chi ha gia' avuto quella proposta: aperta, mandata, o rifiutata da Dre («NO: ...»).
    Le proposte chiuse dagli script il 25/9 (scritte senza lettura) non contano: si rifanno."""
    rs = sb_tutte(f"/rest/v1/proposte?select=prospect_id,stato,risposta&azione->>template=in.({','.join(template)})&limit=5000") or []
    return {x["prospect_id"] for x in rs if x["stato"] != "no" or (x.get("risposta") or "").startswith("NO:")}


def con_bozza_aperta():
    """Chi ha gia' una bozza in Posta (aperta, approvata o in partenza), di qualunque tipo.
    6/10: SCUDO, Xcope e CoEHAR avevano un mini follow-up aperto dall'1/10 e intanto venivano
    rimessi in coda per il FOLLOW UP 1: due follow-up per la stessa persona, e una coda che il
    motore delle bozze non svuotava mai (salta chi ha gia' una proposta aperta)."""
    # conta una mail pronta (risposta, o «da guardare tu» col testo dentro), non una domanda: chi
    # aspetta che Dre guardi un'analisi bocciata deve restare in coda per il suo follow-up
    return {x["prospect_id"] for x in (sb_tutte("/rest/v1/proposte?select=prospect_id,tipo,azione->>bozza&tipo=in.(risposta,umano)"
                                                "&stato=in.(aperta,approvata,in_invio)&limit=5000") or [])
            if x.get("prospect_id") and (x.get("tipo") == "risposta" or x.get("bozza"))}


def in_coda(pid, gruppo):
    """In coda: il motore delle bozze la trova al prossimo giro (5 minuti) e scrive dopo aver letto."""
    sb("PATCH", f"/rest/v1/prospects?id=eq.{pid}", {"coda": gruppo, "coda_il": datetime.datetime.now(datetime.timezone.utc).isoformat()})


def mini_followup(prova, oggi):
    """IL MINI FOLLOW-UP (Dre, 25/9): a chi ha ricevuto la ripresa (analisi + call) e
    dopo sei giorni non ha risposto, due righe, una volta sola."""
    da = (oggi - datetime.timedelta(days=6)).isoformat()
    mandate = sb_tutte(f"/rest/v1/proposte?select=prospect_id,risposta_il&stato=eq.fatta&azione->>intento=eq.RIPRESA&risposta_il=lte.{da}T23:59:59&limit=2000") or []
    gia = gia_avute("MINI%20FOLLOW%20UP")
    n = 0
    for m in mandate:
        pid = m["prospect_id"]
        if not pid or pid in gia:
            continue
        p = (sb("GET", f"/rest/v1/prospects?select=id,name,company,email,last_reply_at,awaiting_us,no_followup,fuori,stage,classificazione,coda&id=eq.{pid}") or [None])[0]
        if not p or p.get("awaiting_us") or p.get("no_followup") or p.get("fuori") or p.get("stage") in ("perso", "cliente"):
            continue
        if p.get("last_reply_at") and p["last_reply_at"] > m["risposta_il"]:
            continue                                        # ha risposto dopo la ripresa: non e' un silenzio
        if p.get("classificazione") in ("negativo", "soppresso", "nervoso", "fuori_target", "persona_sbagliata"):
            continue
        if p.get("coda"):
            continue
        azienda = p.get("company") or p.get("email")
        print(f"  mini → in coda {azienda[:36]}")
        if not prova:
            in_coda(pid, "MINI FOLLOW UP")
        n += 1
    print(f"mini follow-up: {n}")


ORIZZONTE = 21          # giorni in avanti nel calendario dei follow-up


def calendario(prova, oggi):
    """I FOLLOW-UP IN ARRIVO, GIORNO PER GIORNO (Dre, 29/9). La regola e' quella
    qui sotto (main e mini_followup): chi e' gia' dovuto, e chi lo sara' nei
    prossimi 21 giorni, con la data. Lo schermo legge questa tabella e non
    rifa' i conti: una verita' sola. Una riga per azienda, il prossimo che le spetta."""
    righe = {}

    def metti(pid, gruppo, il, perche):
        if pid and (pid not in righe or il < righe[pid]["il"]):
            righe[pid] = {"prospect_id": pid, "gruppo": gruppo, "il": il, "perche": perche[:200]}

    fine = oggi + datetime.timedelta(days=ORIZZONTE)
    aperte = con_bozza_aperta()            # chi ha gia' la bozza in Posta non e' «in arrivo»: e' gia' li'
    # 1. gia' in coda: la bozza arriva al prossimo giro delle bozze
    for p in sb("GET", "/rest/v1/prospects?select=id,coda,coda_il,analysis_pdf&coda=not.is.null&fuori=eq.false"
                       "&stage=not.in.(cliente,perso,call_fissata,rinviato)&limit=1000") or []:
        if p["id"] in aperte:
            continue
        # l'attesa si dice com'e': chi aspetta un'analisi da giorni non «arriva al prossimo giro»
        ferma = p.get("coda_il") and (oggi - datetime.date.fromisoformat(p["coda_il"][:10])).days >= 2
        perche = ("in coda da " + str((oggi - datetime.date.fromisoformat(p["coda_il"][:10])).days) + " giorni"
                  + (": aspetta l'analisi" if not p.get("analysis_pdf") else "")) if ferma else "in coda: la bozza arriva al prossimo giro"
        metti(p["id"], p["coda"], oggi, perche)
    # 2. FOLLOW UP 1: analisi mandata, silenzio, GIORNI dopo (stessa regola di main)
    gia = gia_avute("FOLLOW%20UP%201", "FOLLOW%20UP%20SU%20MISURA")
    # 5/10: niente piu' finestra dei 30 giorni. Chi e' dovuto resta dovuto finche' il follow-up
    # non parte o non esce con un motivo: la finestra faceva sparire dal conto chi era indietro.
    for p in sb_tutte("/rest/v1/prospects?select=id,analysis_sent_at,last_reply_at,coda"
                       f"&analysis_sent=eq.true&awaiting_us=eq.false&no_followup=eq.false&fuori=eq.false&stage=neq.perso"
                       f"&classificazione=in.({CLASSI})") or []:
        if not p.get("analysis_sent_at") or p["id"] in gia or p.get("coda") or p["id"] in aperte:
            continue
        if p.get("last_reply_at") and p["last_reply_at"][:10] > p["analysis_sent_at"][:10]:
            continue
        inviata = datetime.date.fromisoformat(p["analysis_sent_at"][:10])
        il = inviata + datetime.timedelta(days=GIORNI)
        if il <= fine:
            metti(p["id"], "FOLLOW UP 1", max(il, oggi), f"analisi mandata il {inviata:%d/%m}, nessuna risposta")
    # 3. MINI FOLLOW UP: sei giorni dopo la ripresa
    gia_mini = gia_avute("MINI%20FOLLOW%20UP")
    for m in sb_tutte("/rest/v1/proposte?select=prospect_id,risposta_il&stato=eq.fatta&azione->>intento=eq.RIPRESA"
                       "") or []:
        if not m.get("prospect_id") or m["prospect_id"] in gia_mini or not m.get("risposta_il"):
            continue
        il = datetime.date.fromisoformat(m["risposta_il"][:10]) + datetime.timedelta(days=6)
        if il <= fine:
            metti(m["prospect_id"], "MINI FOLLOW UP", max(il, oggi), f"ripresa mandata il {m['risposta_il'][8:10]}/{m['risposta_il'][5:7]}")
    # 4. RINVIO: la data che ci hanno dato
    for p in sb("GET", "/rest/v1/prospects?select=id,next_action_date,coda&classificazione=eq.rinvio&fuori=eq.false"
                       f"&no_followup=eq.false&next_action_date=lte.{fine.isoformat()}&limit=1000") or []:
        if p.get("next_action_date") and not p.get("coda"):
            q = datetime.date.fromisoformat(p["next_action_date"][:10])
            metti(p["id"], "RINVIO SCADUTO", max(q + datetime.timedelta(days=1), oggi), f"aveva detto di risentirci il {q:%d/%m}")
    print(f"calendario dei follow-up: {len(righe)} nei prossimi {ORIZZONTE} giorni")
    if prova:
        for r in sorted(righe.values(), key=lambda r: r["il"])[:15]:
            print(f"    {r['il']:%d/%m} {r['gruppo']:15} {r['perche']}")
        return len(righe)
    adesso = datetime.datetime.now(datetime.timezone.utc).isoformat()
    corpo = [{**r, "il": r["il"].isoformat(), "aggiornato_il": adesso} for r in righe.values()]
    for i in range(0, len(corpo), 200):
        sb("POST", "/rest/v1/seguiti_calendario?on_conflict=prospect_id", corpo[i:i + 200],
           {"Prefer": "resolution=merge-duplicates,return=minimal"})
    # chi non c'e' piu' (ha risposto, e' uscito, il follow-up e' partito) esce dal calendario
    sb("DELETE", f"/rest/v1/seguiti_calendario?aggiornato_il=lt.{urllib.parse.quote(adesso)}")
    return len(righe)


def main():
    prova = "--prova" in sys.argv
    if "--calendario" in sys.argv:
        calendario(prova, datetime.date.today())
        return
    mini_followup(prova, datetime.date.today())
    oggi = datetime.date.today()
    righe = sb("GET", "/rest/v1/prospects?select=id,name,company,email,analysis_sent_at,last_reply_at,classificazione,analysis_pdf,coda"
                      f"&analysis_sent=eq.true&awaiting_us=eq.false&no_followup=eq.false&fuori=eq.false&stage=neq.perso"
                      f"&classificazione=in.({CLASSI})&order=analysis_sent_at.desc&limit=500") or []
    gia = gia_avute("FOLLOW%20UP%201", "FOLLOW%20UP%20SU%20MISURA")
    aperte = con_bozza_aperta()
    fatti = 0
    for p in righe:
        if not p.get("analysis_sent_at") or p["id"] in gia or p.get("coda") or p["id"] in aperte:
            continue
        inviata = datetime.date.fromisoformat(p["analysis_sent_at"][:10])
        if (oggi - inviata).days < GIORNI:
            continue
        if p.get("last_reply_at") and p["last_reply_at"][:10] > p["analysis_sent_at"][:10]:
            continue                                        # ha scritto lui dopo l'analisi: non e' un silenzio
        dopo = sb("GET", f"/rest/v1/interactions?select=id&prospect_id=eq.{p['id']}&kind=in.(email_out,followup)"
                         f"&at=gt.{(inviata + datetime.timedelta(days=1)).isoformat()}&limit=1") or []
        if dopo:
            continue                                        # un follow-up c'e' gia' stato
        azienda = p.get("company") or p.get("email")
        print(f"  {azienda[:36]:36} analisi del {inviata:%d/%m}  → in coda FOLLOW UP 1")
        if prova:
            fatti += 1
            continue
        in_coda(p["id"], "FOLLOW UP 1")
        fatti += 1
        if fatti >= QUANTI:
            break
    print(f"followup: {fatti} messi in coda su {len(righe)} con l'analisi mandata")
    calendario(prova, oggi)


if __name__ == "__main__":
    main()
