#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""LE BOZZE — Clara prepara la risposta, Dre approva e manda (7/9/2026).

PERCHE'
Dre: «voglio aumentare il nostro tempo di risposta. All'inizio, anche se ha
tutte le informazioni, voglio le bozze e approvo io. Quando vedo che diventa
brava, lascio che gestisca lei e mi contatta quando non sa».

COME
Per ogni persona che aspetta una risposta da noi, Clara legge il playbook
(docs/clara-sg-outbound.md), la scheda e l'ultimo messaggio, decide l'intento
(A..H), sceglie il template, scrive la bozza e la mette nella sua stanza come
proposta di tipo «risposta». Se il caso e' fra quelli in cui deve fermarsi
(prezzo insistito, richiesta legale, obiezione complessa, non si capisce),
prepara comunque la bozza migliore e la segna «da guardare tu».

Ogni bozza passa dal CANCELLO QUALITA' (lo stesso di lint_risposta.py del
3/7): trattino lungo, registro misto tu/lei, apertura secca, firma nel corpo,
promesse vietate. Se non passa, si riscrive una volta; se non passa ancora,
si mette in stanza con l'avviso invece di sparire.

USO
  python3 scripts/bozze.py --prova      mostra le bozze, non scrive
  python3 scripts/bozze.py              mette le bozze nella stanza
  python3 scripts/bozze.py --quanti 5
"""

import datetime
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cervello                                            # noqa: E402
from stanza import sb, proponi                             # noqa: E402

RADICE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROVA = "--prova" in sys.argv
QUANTI = int(sys.argv[sys.argv.index("--quanti") + 1]) if "--quanti" in sys.argv else 40
CALENDARIO = "https://calendar.app.google/WmgWF3rGKXCkBY41A"

# a chi si risponde: chi ha scritto e aspetta, e ha un intento a cui si risponde
CLASSI = ("positivo", "tiepido", "rinvio", "da_classificare")
INTOCCABILI = ("cliente", "perso", "call_fissata", "rinviato")

# ── il cancello qualita' (da lint_risposta.py, 3/7) ─────────────────
TU = re.compile(r"\b(tu|ti|te|tuo|tua|tuoi|tue|puoi|hai|sei|vuoi|pensi|trovi|scegli)\b", re.I)
LEI = re.compile(r"\b(lei|le|la ringrazio|suo|sua|suoi|sue|puo'|può|vorra'|vorrà|preferisce)\b", re.I)
APERTURE_SECCHE = ("si'.", "sì.", "no.", "volentieri.", "certo.", "ok.", "va bene.")
PROMESSE = ("garantiamo risultati", "rendimento garantito", "successo assicurato", "senza impegno")


def cancello(testo):
    """Torna la lista dei motivi per cui la bozza NON va bene (vuota = passa)."""
    errori = []
    low = testo.lower()
    if "—" in testo:
        errori.append("trattino lungo")
    tu, lei = TU.findall(testo), LEI.findall(testo)
    if tu and lei:
        errori.append(f"registro misto tu/lei ({', '.join(sorted(set(w.lower() for w in tu))[:3])})")
    righe = [r.strip() for r in testo.splitlines() if r.strip()]
    if righe:
        corpo = righe[1] if len(righe) > 1 and righe[0].lower().startswith(("buongiorno", "salve", "buonasera", "gentile", "ciao")) else righe[0]
        prima = corpo.split(".")[0].strip().lower() + "."
        if prima in APERTURE_SECCHE:
            errori.append(f"apertura secca «{corpo[:25]}»")
    if "lorenzo fornasier" in low and ("via francesco baracca" in low or "+39" in low):
        errori.append("firma completa nel corpo: la mette Smartlead")
    for p in PROMESSE:
        if p in low:
            errori.append(f"frase vietata «{p}»")
    return errori


def playbook():
    return open(os.path.join(RADICE, "docs", "clara-sg-outbound.md"), encoding="utf-8").read()


def proposta_giorno_ora():
    """Un giorno lavorativo entro tre giorni, alle 11 o alle 15."""
    d = datetime.date.today() + datetime.timedelta(days=1)
    while d.weekday() >= 5:
        d += datetime.timedelta(days=1)
    giorni = ["lunedì", "martedì", "mercoledì", "giovedì", "venerdì", "sabato", "domenica"]
    return f"{giorni[d.weekday()]} {d.day} alle 11"


ISTRUZIONE = """Sei Clara, che prepara la risposta per Lorenzo (la manda lui). Leggi il
playbook qui sopra: e' la legge. Poi leggi la scheda e l'ultimo messaggio
della persona, e rispondi ESATTAMENTE in questo formato, niente altro:

INTENTO: una lettera fra A B C D E F G H
TEMPLATE: il nome del template usato (o «nessuno» per F/G brevi)
FERMATI: no | si' e il motivo in 10 parole (solo nei casi del capitolo 6)
NOTA: una riga su cosa hai adattato e perche'
---
il testo della bozza, pronto da incollare, SENZA firma, con [CALENDARIO] e
[GIORNO E ORA] gia' sostituiti con i valori che ti do.

Regole che non si discutono: registro «lei», mai «tu»; mai il trattino
lungo; mai aprire con «volentieri.» o «si'.» secchi; niente firma; se
l'analisi e' gia' stata inviata non rispiegare cos'e'; se ha chiesto lui una
call non mandare l'analisi, fissa la call. Se l'ultimo messaggio e' un «ok»,
«grazie», «ricevuto» secco senza una richiesta, NON e' un interessato: metti
FERMATI: si' («messaggio ambiguo, un ok secco») e scrivi la bozza piu' corta
possibile."""


def chiedi_bozza(p, ultimo, riprova=None):
    fatti = {
        "nome": p.get("name") or "", "azienda": p.get("company") or "", "email": p.get("email"),
        "classificazione": p.get("classificazione"), "stage": p.get("stage"),
        "analisi_inviata": bool(p.get("analysis_sent")), "analisi_inviata_il": (p.get("analysis_sent_at") or "")[:10],
        "ultima_sua_mail": (p.get("last_reply_at") or "")[:10], "settore": p.get("sector"), "citta": p.get("city"),
    }
    prompt = (playbook() + "\n\n" + ISTRUZIONE + cervello.istruzione("chat") +
              f"\n\nVALORI DA USARE: [CALENDARIO] = {CALENDARIO} · [GIORNO E ORA] = {proposta_giorno_ora()}"
              f"\n\nLA SCHEDA:\n{fatti}\n\nL'ULTIMO MESSAGGIO CHE HA SCRITTO:\n{ultimo[:2500]}")
    if riprova:
        prompt += f"\n\nLA BOZZA PRECEDENTE NON E' PASSATA IL CANCELLO PER: {riprova}. Riscrivila correggendo solo quello."
    grezzo = cervello._chiedi(prompt)
    m = re.search(r"\n\s*(?:-{3,}|\*{3,})\s*\n", grezzo)
    if not m:
        return None
    testa, bozza = grezzo[:m.start()], grezzo[m.end():]
    campi = {}
    for riga in testa.splitlines():
        if ":" in riga:
            k, v = riga.split(":", 1)
            campi[k.strip().upper()] = v.strip()
    bozza = bozza.strip().strip("`").strip()
    return {"intento": campi.get("INTENTO", "?")[:1], "template": campi.get("TEMPLATE", ""),
            "fermati": campi.get("FERMATI", "no"), "nota": campi.get("NOTA", ""), "bozza": bozza}


def main():
    print("LE BOZZE" + (" (prova: non scrive niente)" if PROVA else ""))
    persone = sb("GET", "/rest/v1/prospects?awaiting_us=eq.true&fuori=eq.false"
                        f"&classificazione=in.({','.join(CLASSI)})"
                        "&select=id,name,company,email,classificazione,stage,analysis_sent,analysis_sent_at,"
                        "last_reply_at,sector,city,enriched&order=last_reply_at.desc&limit=300") or []
    righe = sb("GET", "/rest/v1/interactions?kind=eq.email_in&select=prospect_id,body&order=at.desc&limit=3000") or []
    ultima = {}
    for r in righe:
        if r.get("prospect_id") and r["prospect_id"] not in ultima:
            ultima[r["prospect_id"]] = r.get("body") or ""
    # con una proposta aperta di qualunque tipo si aspetta Dre: se la classe e'
    # in discussione, la bozza sarebbe scritta sulla classe sbagliata
    aperte = {x["prospect_id"] for x in (sb("GET", "/rest/v1/proposte?select=prospect_id&stato=eq.aperta") or [])}

    fatte, ferme, bocciate = 0, 0, 0
    for p in persone:
        if fatte + ferme >= QUANTI:
            break
        testo = ultima.get(p["id"], "")
        if len(testo.strip()) < 30 or p["id"] in aperte or p.get("stage") in INTOCCABILI:
            continue
        nome = (p.get("company") or p.get("name") or p.get("email") or "")[:34]
        b = chiedi_bozza(p, testo)
        if not b:
            print(f"  ? {nome}: risposta del cervello non leggibile"); continue
        errori = cancello(b["bozza"])
        if errori:
            b2 = chiedi_bozza(p, testo, riprova="; ".join(errori))
            if b2 and not cancello(b2["bozza"]):
                b = b2; errori = []
            else:
                bocciate += 1
        ferma = not b["fermati"].lower().startswith("no")
        titolo = (f"Da guardare tu: {nome}" if ferma else f"Bozza per {nome}") + f" · intento {b['intento']}"
        perche = (b["fermati"] if ferma else b["nota"])[:280] + (f" · CANCELLO: {'; '.join(errori)}" if errori else "")
        print(f"\n  [{b['intento']}] {titolo}\n      {perche}\n      " + b["bozza"][:220].replace("\n", " ") + "…")
        if not PROVA:
            proponi("umano" if ferma else "risposta", titolo, prospect_id=p["id"], perche=perche,
                    azione={"bozza": b["bozza"], "intento": b["intento"], "template": b["template"]})
        if ferma: ferme += 1
        else: fatte += 1

    print(f"\n  bozze pronte {fatte} · da guardare tu {ferme} · non passate il cancello {bocciate}")


if __name__ == "__main__":
    main()
