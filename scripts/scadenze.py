#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""LE SCADENZE — la prova che finisce, Clara la mette in stanza (9/9/2026).

Dre: «il periodo di prova dura due mesi; quando finisce mi riaccordo con
loro per alzare il prezzo e si passa al retainer». Quattordici giorni prima
della fine Clara mette una domanda in stanza, una volta sola per prova:
«La prova di X finisce il D: ti riaccordi per il retainer?». Il si' crea la
task «Riaccordarsi con X» con la data; il no la chiude. Se la prova e'
finita e nessuno l'ha portata a Cliente, lo ricorda ogni giorno finche' non
si decide (in un senso o nell'altro).

USO
  python3 scripts/scadenze.py           propone
  python3 scripts/scadenze.py --prova   mostra e basta
"""

import datetime
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from stanza import sb, proponi, sb_tutte, soldi_clienti, con_soldi  # noqa: E402

PREAVVISO = 14


def main():
    prova = "--prova" in sys.argv
    oggi = datetime.date.today()
    entro = (oggi + datetime.timedelta(days=PREAVVISO)).isoformat()
    righe = sb("GET", f"/rest/v1/prospects?select=id,name,company,prova_inizio,prova_fine,canone"
                      f"&fuori=eq.true&pipeline_stage=eq.prova&prova_fine=lte.{entro}&order=prova_fine.asc&limit=200") or []
    soldi = soldi_clienti([p["id"] for p in righe])      # il canone sta in cassaforte (29/9)
    righe = [con_soldi(p, soldi) for p in righe]
    gia = {((p.get("azione") or {}).get("prova_fine"), p.get("prospect_id"))
           for p in (sb_tutte("/rest/v1/proposte?select=prospect_id,azione&tipo=eq.richiesta&limit=5000") or [])}
    fatte = 0
    for p in righe:
        if (p["prova_fine"], p["id"]) in gia:
            continue
        nome = p.get("company") or p.get("name") or "?"
        fine = datetime.date.fromisoformat(p["prova_fine"])
        giorni = (fine - oggi).days
        quando = f"finisce il {fine:%d/%m}" if giorni >= 0 else f"e' finita il {fine:%d/%m}"
        titolo = f"{nome}: la prova {quando}. Ti riaccordi per il retainer?"
        perche = f"Prova dal {p['prova_inizio'] or '?'} al {p['prova_fine']}" + (f", canone {p['canone']} €" if p.get("canone") else "")
        azione = {"prova_fine": p["prova_fine"],
                  "task": {"titolo": f"Riaccordarsi con {nome} per il retainer", "scadenza": max(oggi, fine - datetime.timedelta(days=7)).isoformat()}}
        if prova:
            print(f"  {titolo}")
            continue
        if proponi("richiesta", titolo, prospect_id=p["id"], perche=perche, azione=azione):
            fatte += 1
    print(f"scadenze: {fatte} proposte, {len(righe)} prove in scadenza")
    preventivi_scaduti(prova, oggi)
    progetti_in_scadenza(prova, oggi)


def preventivi_scaduti(prova, oggi):
    """I preventivi mandati e mai risposti (Giacomo, 15/9).

    Oggi il preventivo scaduto diventa un'etichetta ambra nella lista e li'
    resta: nessuno lo richiama, perche' niente lo mette nella giornata di
    qualcuno. Il giorno dopo la scadenza Clara lo chiede, una volta sola:
    si' e nasce la task per richiamarlo, no e si segna rifiutato a mano.
    """
    righe = sb("GET", f"/rest/v1/preventivi?select=id,numero,titolo,importo,mensile,valido_fino,prospect_id,inviato_il"
                      f"&stato=eq.inviato&valido_fino=lt.{oggi.isoformat()}&order=valido_fino.asc&limit=200") or []
    if not righe:
        print("preventivi scaduti: nessuno")
        return
    gia = {(p.get("azione") or {}).get("preventivo_id")
           for p in (sb_tutte("/rest/v1/proposte?select=azione&tipo=eq.richiesta&limit=5000") or [])}
    nomi = {}
    for q in righe:
        if q["prospect_id"] not in nomi:
            r = sb("GET", f"/rest/v1/prospects?select=company,name&id=eq.{q['prospect_id']}&limit=1") or [{}]
            nomi[q["prospect_id"]] = r[0].get("company") or r[0].get("name") or "?"
    fatte = 0
    for q in righe:
        if q["id"] in gia:
            continue
        nome = nomi[q["prospect_id"]]
        scaduto = datetime.date.fromisoformat(q["valido_fino"])
        quanto = f"{int(q['importo'] or 0)} €" + (f" piu' {int(q['mensile'])} €/mese" if q.get("mensile") else "")
        titolo = f"{nome}: il preventivo {q['numero']} e' scaduto il {scaduto:%d/%m} senza risposta. Lo richiamo?"
        perche = f"{quanto}, mandato il {q.get('inviato_il') or '?'}. Se non se ne fa niente, segnalo rifiutato dai Preventivi."
        azione = {"preventivo_id": q["id"],
                  "task": {"titolo": f"Richiamare {nome} sul preventivo {q['numero']}", "scadenza": oggi.isoformat()}}
        if prova:
            print(f"  {titolo}")
            continue
        if proponi("richiesta", titolo, prospect_id=q["prospect_id"], perche=perche, azione=azione):
            fatte += 1
    print(f"preventivi scaduti: {fatte} proposte, {len(righe)} scaduti")

def progetti_in_scadenza(prova, oggi):
    """LE SCADENZE DEL LAVORO CONSEGNATO (27/9). Qui si guardavano solo le prove e i
    preventivi: le date sui progetti non le leggeva nessuno. Il sito vetrina di
    Zafferano era scaduto il 2 settembre e per venticinque giorni non l'ha detto
    nessuno. E' anche meta' di quello che ha chiesto Carlo il 23/9 («Clara che ci
    dica: mancano tre giorni, bisognerebbe fare il check»).
    Avvisa chi segue il progetto, una volta sola per scadenza."""
    entro = (oggi + datetime.timedelta(days=PREAVVISO)).isoformat()
    righe = sb("GET", "/rest/v1/progetti?select=id,nome,cliente,scadenza,stato,chi_segue,prospect_id"
                      f"&scadenza=lte.{entro}&stato=neq.consegnato&order=scadenza.asc&limit=200") or []
    gia = {((pr.get("azione") or {}).get("progetto_scadenza"), (pr.get("azione") or {}).get("progetto_id"))
           for pr in (sb_tutte("/rest/v1/proposte?select=azione&tipo=eq.umano&limit=5000") or [])}
    chi = {(x.get("nome") or "").split(" ")[0].lower(): x["id"]
           for x in (sb("GET", "/rest/v1/profili?select=id,nome") or []) if x.get("nome")}
    fatte = 0
    for g in righe:
        if (g.get("scadenza"), g.get("id")) in gia:
            continue
        quando = datetime.date.fromisoformat(g["scadenza"])
        giorni = (quando - oggi).days
        nome = f"{g.get('cliente') or '?'}: {g.get('nome') or 'progetto'}"
        if giorni < 0:
            g_fa = abs(giorni)
            titolo = f"{nome} è scaduto il {quando:%d/%m}, {g_fa} giorn{'o' if g_fa == 1 else 'i'} fa"
        elif giorni == 0:
            titolo = f"{nome} scade oggi"
        else:
            titolo = f"{nome} scade fra {giorni} giorn{'o' if giorni == 1 else 'i'}, il {quando:%d/%m}"
        perche = f"Stato: {g.get('stato') or '?'}" + (f", lo segue {g['chi_segue']}" if g.get("chi_segue") else ", nessuno assegnato")
        # IL SITO CHE BLOCCA LA CAMPAGNA (Carlo, 28/9): «il sistema si blocca nella
        # maggior parte dei casi per il lato web... ad Alex tocca consegnare almeno
        # tre giorni prima dell'onboarding, se no a noi tocca fare tutto di corsa».
        # Quando il progetto in ritardo e' un sito e quel cliente ha anche una
        # campagna, il ritardo non e' solo suo: si dice cosa trascina.
        testo_web = f"{g.get('nome') or ''} {g.get('natura') or ''}".lower()
        if any(k in testo_web for k in ("sito", "landing", "vetrina", "web")) and g.get("prospect_id"):
            campagne = sb("GET", "/rest/v1/progetti?select=nome,tipo,chi_segue"
                                 f"&prospect_id=eq.{g['prospect_id']}&stato=neq.consegnato&limit=10") or []
            ads = [c for c in campagne if c.get("tipo") in ("onboarding", "trial")]
            if ads:
                titolo += " e tiene ferma la campagna"
                perche += f". Blocca: {ads[0].get('nome')} ({ads[0].get('chi_segue') or '?'})"
        # TUTTI GLI AVVISI VANNO ANCHE A SALVATORE (Carlo, 28/9)
        owner = chi.get((g.get("chi_segue") or "").split(" ")[0].lower())
        azione = {"progetto_scadenza": g.get("scadenza"), "progetto_id": g.get("id"),
                  "task": {"titolo": f"Chiudere o rimandare: {nome}", "scadenza": max(oggi, quando).isoformat()}}
        if prova:
            print(f"  {titolo}  ({perche})")
            continue
        if proponi("umano", titolo, prospect_id=g.get("prospect_id"), perche=perche[:280], azione=azione, owner=owner):
            fatte += 1
    print(f"progetti: {fatte} avvisi, {len(righe)} scadenze viste")


if __name__ == "__main__":
    main()
