#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""LE AZIONI DI CLARA (16/9/2026).

PERCHE'
Dre: «quando invio un preventivo, Clara si mette in automatico un promemoria
e controlla se sono arrivati i soldi; se passa una settimana me lo ricorda.
Pensa alle cose che spesso si dimenticano e fai delle azioni».

Sono le cose che non si dimenticano perche' sono difficili, ma perche' non
hanno un momento: nessuno ha in agenda «controlla se quel bonifico e'
arrivato». Clara ce l'ha.

COME FUNZIONA
Ogni azione e' una riga nella tabella `azioni` (schema_v45): nome, cosa fa,
dopo quanti giorni guarda, accesa o spenta. Qui dentro c'e' il codice di
ognuna. Quando scatta, non fa: chiede. Nasce una riga nella Posta di Clara,
con dentro la cosa da fare, e la persona dice si' o no. Ogni promemoria ha
un riferimento suo (`proposte.ref`), quindi non nasce due volte.

USO
  python3 scripts/azioni.py           guarda tutte quelle accese
  python3 scripts/azioni.py --prova   dice cosa farebbe, non scrive
"""

import datetime
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from stanza import sb                                      # noqa: E402

PROVA = "--prova" in sys.argv


def adesso():
    return datetime.datetime.now(datetime.timezone.utc)


def zulu(d):
    return d.strftime("%Y-%m-%dT%H:%M:%SZ")


def giorni_fa(n):
    return zulu(adesso() - datetime.timedelta(days=n))


def data(iso):
    try:
        return datetime.datetime.fromisoformat(re.sub(r"\.\d+", "", (iso or "").replace("Z", "+00:00")))
    except Exception:
        return None


def quanti_giorni(iso):
    d = data(iso)
    return None if not d else (adesso() - d).days


def nome_di(p):
    return (p or {}).get("company") or (p or {}).get("name") or (p or {}).get("email") or "questa azienda"


def aziende(ids):
    ids = [i for i in set(ids) if i]
    if not ids:
        return {}
    lista = ",".join(f'"{i}"' for i in ids)
    righe = sb("GET", f"/rest/v1/prospects?select=id,company,name,email,chi_segue&id=in.({lista})&limit=500") or []
    return {r["id"]: r for r in righe}


def proponi(ref, tipo, titolo, perche, prospect_id=None, azione=None):
    """Una riga nella Posta. Se quel promemoria c'e' gia', non se ne fa un altro."""
    gia = sb("GET", f"/rest/v1/proposte?select=id&ref=eq.{ref}&limit=1")
    if gia:
        return False
    print(f"    -> {titolo}")
    if PROVA:
        return True
    sb("POST", "/rest/v1/proposte", {
        "tipo": tipo, "titolo": titolo, "perche": perche,
        "prospect_id": prospect_id, "azione": azione or {}, "ref": ref,
    })
    return True


# ── le azioni ───────────────────────────────────────────────────────────
# Ognuna torna quante ne ha create. La firma e' sempre (giorni).

def preventivo_senza_risposta(giorni):
    """Mandato e nessuno ha piu' detto niente."""
    quote = sb("GET", "/rest/v1/preventivi?select=id,numero,titolo,importo,prospect_id,inviato_il,stato"
                      f"&stato=eq.inviato&inviato_il=lte.{giorni_fa(giorni)}&limit=200") or []
    nomi = aziende([q.get("prospect_id") for q in quote])
    n = 0
    for q in quote:
        g = quanti_giorni(q.get("inviato_il"))
        if g is None:
            continue
        azienda = nome_di(nomi.get(q.get("prospect_id")))
        n += proponi(
            f"prev-fermo:{q['id']}", "umano",
            f"{azienda}: il preventivo {q.get('numero') or ''} è fermo da {g} giorni".replace("  ", " "),
            f"Mandato il {(q.get('inviato_il') or '')[:10]}, nessuna risposta. Lo richiami o lo lasci andare?",
            q.get("prospect_id"),
        )
    return n


def preventivo_accettato_non_pagato(giorni):
    """Ha detto si' e i soldi non si vedono."""
    quote = sb("GET", "/rest/v1/preventivi?select=id,numero,importo,prospect_id,accettato_il,pagato_il,stato"
                      f"&stato=eq.accettato&pagato_il=is.null&accettato_il=lte.{giorni_fa(giorni)}&limit=200") or []
    nomi = aziende([q.get("prospect_id") for q in quote])
    n = 0
    for q in quote:
        # i soldi potrebbero essere arrivati su Stripe senza passare da qui
        acc = data(q.get("accettato_il"))
        incassi = sb("GET", "/rest/v1/incassi?select=id&stato=in.(succeeded,paid)"
                            f"&prospect_id=eq.{q['prospect_id']}&quando=gte.{zulu(acc) if acc else giorni_fa(giorni)}&limit=1") if q.get("prospect_id") else []
        if incassi:
            continue
        g = quanti_giorni(q.get("accettato_il"))
        azienda = nome_di(nomi.get(q.get("prospect_id")))
        soldi = f"{int(float(q.get('importo') or 0))} €" if q.get("importo") else "il preventivo"
        n += proponi(
            f"prev-nonpagato:{q['id']}", "umano",
            f"{azienda}: accettato da {g} giorni, {soldi} non risulta incassato",
            "Ha detto sì ma il pagamento non si vede, né qui né su Stripe. Gli scrivi o l'hai già incassato fuori?",
            q.get("prospect_id"),
        )
    return n


def call_senza_riassunto(giorni):
    """La call e' passata e nessuno ha scritto com'e' andata."""
    da = zulu(adesso() - datetime.timedelta(days=giorni + 5))
    fino = zulu(adesso() - datetime.timedelta(days=giorni))
    righe = sb("GET", "/rest/v1/agenda?select=id,at,titolo,tipo,prospect_id"
                      f"&at=gte.{da}&at=lte.{fino}&limit=100") or []
    call = [r for r in righe if r.get("prospect_id") and (r.get("tipo") or "") in ("conoscitiva", "tecnica", "avvio", "call")]
    nomi = aziende([c["prospect_id"] for c in call])
    n = 0
    for c in call:
        da = data(c["at"])
        dopo = sb("GET", "/rest/v1/interactions?select=id"
                         f"&prospect_id=eq.{c['prospect_id']}&kind=in.(transcript,postit,nota)"
                         f"&at=gte.{zulu(da) if da else giorni_fa(giorni)}&limit=1")
        if dopo:
            continue
        azienda = nome_di(nomi.get(c["prospect_id"]))
        n += proponi(
            f"call-vuota:{c['id']}", "umano",
            f"{azienda}: la call del {(c.get('at') or '')[:10]} non ha un riassunto",
            "Due righe adesso valgono piu' di mezz'ora fra un mese. Cosa vi siete detti?",
            c["prospect_id"],
        )
    return n


def cliente_senza_canone(giorni):
    """E' diventato cliente e non si sa quanto paga."""
    righe = sb("GET", "/rest/v1/prospects?select=id,company,name,email,canone,fuori_at,pipeline_stage"
                      f"&fuori=eq.true&pipeline_stage=in.(cliente,prova)&canone=is.null"
                      f"&fuori_at=lte.{giorni_fa(giorni)}&limit=100") or []
    n = 0
    for p in righe:
        n += proponi(
            f"canone-manca:{p['id']}", "umano",
            f"{nome_di(p)}: è cliente e non sappiamo quanto paga",
            "Senza il canone i conti dello Studio sono sbagliati. Lo scrivi sulla sua scheda?",
            p["id"],
        )
    return n


def prova_che_finisce(giorni):
    """La prova finisce fra poco: e' il momento di riaccordarsi."""
    fra = (adesso() + datetime.timedelta(days=giorni)).date().isoformat()
    oggi = adesso().date().isoformat()
    righe = sb("GET", "/rest/v1/prospects?select=id,company,name,email,prova_fine"
                      f"&prova_fine=gte.{oggi}&prova_fine=lte.{fra}&limit=100") or []
    n = 0
    for p in righe:
        n += proponi(
            f"prova-finisce:{p['id']}:{p['prova_fine']}", "avanza",
            f"{nome_di(p)}: la prova finisce il {p['prova_fine'][8:10]}/{p['prova_fine'][5:7]}",
            "E' il momento di guardare i numeri insieme e dire come si continua.",
            p["id"],
            {"task": {"titolo": f"Chiamare {nome_di(p)} per il rinnovo", "scadenza": p["prova_fine"]}},
        )
    return n


def accessi_che_non_arrivano(giorni):
    """Il lavoro e' fermo perche' mancano gli accessi, e nessuno lo dice."""
    righe = sb("GET", "/rest/v1/progetti?select=id,nome,prospect_id,accessi_stato,accessi_chiesti_il,chi_segue"
                      f"&accessi_stato=eq.chiesti&accessi_chiesti_il=lte.{giorni_fa(giorni)}&limit=100") or []
    nomi = aziende([r.get("prospect_id") for r in righe])
    n = 0
    for r in righe:
        g = quanti_giorni(r.get("accessi_chiesti_il"))
        azienda = nome_di(nomi.get(r.get("prospect_id")))
        n += proponi(
            f"accessi-fermi:{r['id']}", "umano",
            f"{azienda}: gli accessi sono chiesti da {g} giorni e non sono arrivati",
            f"«{r.get('nome') or 'il progetto'}» è fermo li'. Glieli richiedi?",
            r.get("prospect_id"),
        )
    return n


def progetto_senza_imparato(giorni):
    """Consegnato e nessuno ha scritto cosa ci ha insegnato."""
    righe = sb("GET", "/rest/v1/progetti?select=id,nome,prospect_id,stato,imparato,at"
                      f"&stato=eq.consegnato&imparato=is.null&at=lte.{giorni_fa(giorni)}&limit=100") or []
    nomi = aziende([r.get("prospect_id") for r in righe])
    n = 0
    for r in righe:
        azienda = nome_di(nomi.get(r.get("prospect_id")))
        n += proponi(
            f"imparato-manca:{r['id']}", "umano",
            f"{azienda}: «{r.get('nome') or 'il progetto'}» è consegnato, cosa abbiamo imparato?",
            "Una riga sola. E' quella che il prossimo cliente dello stesso settore si ritrova gratis.",
            r.get("prospect_id"),
        )
    return n


def cliente_dimenticato(giorni):
    """Paga tutti i mesi e non lo sente nessuno da troppo."""
    righe = sb("GET", "/rest/v1/prospects?select=id,company,name,email,canone,updated_at"
                      f"&fuori=eq.true&pipeline_stage=eq.cliente&limit=200") or []
    n = 0
    for p in righe:
        ultima = sb("GET", f"/rest/v1/interactions?select=at&prospect_id=eq.{p['id']}&order=at.desc&limit=1")
        quando = (ultima or [{}])[0].get("at")
        g = quanti_giorni(quando) if quando else None
        if g is None or g < giorni:
            continue
        n += proponi(
            f"cliente-muto:{p['id']}:{adesso().date().isoformat()[:7]}", "umano",
            f"{nome_di(p)}: nessuno lo sente da {g} giorni, e paga tutti i mesi",
            "I clienti non se ne vanno per i risultati, se ne vanno per il silenzio. Una call o due righe?",
            p["id"],
        )
    return n


AZIONI = {
    "prev_fermo": preventivo_senza_risposta,
    "prev_non_pagato": preventivo_accettato_non_pagato,
    "call_vuota": call_senza_riassunto,
    "canone_manca": cliente_senza_canone,
    "prova_finisce": prova_che_finisce,
    "accessi_fermi": accessi_che_non_arrivano,
    "imparato_manca": progetto_senza_imparato,
    "cliente_muto": cliente_dimenticato,
}


def main():
    righe = sb("GET", "/rest/v1/azioni?select=*&order=ordine") or []
    if not righe:
        print("nessuna azione nel database: lancia prima scripts/azioni_prime.py")
        return
    totale = 0
    for a in righe:
        fai = AZIONI.get(a["chiave"])
        if not fai:
            print(f"  {a['chiave']}: non esiste piu' nel codice, la salto")
            continue
        if not a.get("attiva"):
            continue
        print(f"  {a['nome']} (dopo {a['giorni']} giorni)")
        try:
            n = fai(int(a.get("giorni") or 7))
        except Exception as e:
            print(f"    guasto: {str(e)[:160]}")
            if not PROVA:
                sb("PATCH", f"/rest/v1/azioni?chiave=eq.{a['chiave']}",
                   {"ultima_corsa": zulu(adesso()), "ultimo_esito": f"guasto: {str(e)[:160]}"})
            continue
        totale += n
        if not PROVA:
            sb("PATCH", f"/rest/v1/azioni?chiave=eq.{a['chiave']}",
               {"ultima_corsa": zulu(adesso()), "ultimo_esito": f"{n} promemoria" if n else "niente da dire"})
    print(f"{'(prova) ' if PROVA else ''}{totale} promemoria nuovi")


if __name__ == "__main__":
    main()
