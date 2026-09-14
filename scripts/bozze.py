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
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cervello                                            # noqa: E402
from stanza import sb, proponi                             # noqa: E402

RADICE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROVA = "--prova" in sys.argv
QUANTI = int(sys.argv[sys.argv.index("--quanti") + 1]) if "--quanti" in sys.argv else 25
IN_PARALLELO = 5
CALENDARIO = "https://calendar.app.google/zNMQ2apeE5SGGwA86"   # confermato da Dre il 7/9

# a chi si risponde: chi ha scritto e aspetta, e ha un intento a cui si risponde
CLASSI = ("positivo", "tiepido", "rinvio", "da_classificare")
INTOCCABILI = ("cliente", "perso", "call_fissata", "rinviato")

# IL GIGANTE BUONO (Dre, 14/9): ai negativi cortesi mandiamo lo stesso
# l'analisi che avevamo preparato, una volta sola, con il calendario e un
# saluto. Mai a chi chiede di non essere contattato, cita la privacy o e'
# scortese: quelli restano fuori, e' la regola sacra. Passa dalla Posta.
QUANTI_GB = 10
NON_TOCCARE = re.compile(r"rimuov|cancell|non (vogliamo|voglio|desider)|non (ci|mi) contatt|non (ci|mi) scriv|privacy|gdpr|"
                         r"diffid|denunc|garante|spam|molest|smett|basta\b|lasciateci|lasciatemi|opt.?out|unsubscribe|disiscri", re.I)
ISTRUZIONE_GB = """Scrivi la risposta a un'azienda che ci ha detto di NO in modo cortese (non
interessati, hanno gia' un'agenzia, non e' il momento). L'analisi della sua zona
l'avevamo gia' preparata: gliela lasciamo lo stesso, senza chiedere niente in
cambio. Tono: il gigante buono. Grato, leggero, zero vendita, zero insistenza.

Rispondi con queste righe, poi una riga «---», poi il testo:
INTENTO: INT-GB
FERMATI: no | si': il motivo (solo se il no era in realta' scortese o chiedeva di non essere contattato)
NOTA: una riga su cosa hai usato dell'analisi
---
Il testo: registro «lei», 5-7 righe, mai il trattino lungo, niente firma.
1) ringrazia della risposta e prendi atto del no senza discuterlo;
2) di' che l'analisi della loro zona era gia' pronta e gliela lasciamo in
   allegato, con UN numero vero se c'e' (le ricerche al mese nella provincia);
3) chiudi: se un giorno vorranno piu' clienti, noi siamo qui, con {{CALENDARIO}};
4) un saluto gentile. Nessun follow-up promesso, nessuna domanda."""

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
    """Playbook 1.0, cap. 2: futuro, feriale, almeno 48 ore avanti, mai lo
    stesso giorno; scritto sempre «giorno + data»."""
    d = datetime.date.today() + datetime.timedelta(days=2)
    while d.weekday() >= 5:
        d += datetime.timedelta(days=1)
    giorni = ["lunedì", "martedì", "mercoledì", "giovedì", "venerdì", "sabato", "domenica"]
    mesi = ["gennaio", "febbraio", "marzo", "aprile", "maggio", "giugno", "luglio", "agosto",
            "settembre", "ottobre", "novembre", "dicembre"]
    return f"{giorni[d.weekday()]} {d.day} {mesi[d.month - 1]} alle 11"


ISTRUZIONE = """Sei Clara. Prepari la risposta con l'identita' di Lorenzo; la manda lui
o Dre dopo l'ok (legge zero). Il playbook qui sopra e' la legge: fai gli 8
controlli del preflight, scegli l'intento nella tabella, applica le regole di
calendario e di stile. Rispondi ESATTAMENTE in questo formato, niente altro:

INTENTO: INT-xx (il codice della tabella)
PREFLIGHT: ok | fallito: quale controllo e perche'
FERMATI: no | si': il motivo in 10 parole (i casi del capitolo 5, o preflight fallito)
NOTA: una riga su cosa hai adattato e perche'
---
il testo della bozza, pronto da incollare, SENZA firma (la mette Smartlead),
con {{CALENDARIO}} e {giorno data ora} gia' sostituiti coi valori che ti do.
Se FERMATI e' si', la bozza e' comunque la migliore che puoi, e dopo il testo
aggiungi una riga: [ESCALATION] azienda, nome, intento, cosa chiede
Se INT-25 (non e' chiaro cosa vuole): due bozze alternative, separate da una
riga «=== ALTERNATIVA ===».

Regole che non si discutono: registro «lei», mai «tu»; mai il trattino
lungo; mai aprire con «volentieri.» o «si'.» secchi; niente firma; il link
del calendario solo a chi e' caldo o l'ha chiesto, mai ai tiepidi o nei
follow-up; se ha chiesto lui la call non mandare l'analisi, fissa la call;
se e' un «ok» o «grazie» secco senza richiesta, FERMATI: si'."""


def chiedi_bozza(p, ultimo, riprova=None):
    fatti = {
        "nome": p.get("name") or "", "azienda": p.get("company") or "", "email": p.get("email"),
        "classificazione": p.get("classificazione"), "stage": p.get("stage"),
        "analisi_inviata": bool(p.get("analysis_sent")), "analisi_inviata_il": (p.get("analysis_sent_at") or "")[:10],
        "ultima_sua_mail": (p.get("last_reply_at") or "")[:10], "settore": p.get("sector"), "citta": p.get("city"),
    }
    # il Google Fit di Clara (googlefit.py): il numero della zona va nel messaggio,
    # e' la personalizzazione che ha fatto rispondere Orobica e Sarci
    fit = (p.get("enriched") or {}).get("google_fit") or {}
    if fit:
        fatti["google_fit"] = {"verdetto": fit.get("verdetto"), "motivo": fit.get("motivo"), "cosa_fa": fit.get("cosa_fa"),
                               "provincia": fit.get("provincia"), "zona": fit.get("zona")}
    prompt = (playbook() + "\n\n" + ISTRUZIONE + cervello.istruzione("chat") +
              f"\n\nVALORI DA USARE: {{{{CALENDARIO}}}} = {CALENDARIO}, slot da proporre = {proposta_giorno_ora()}, oggi e' {datetime.date.today():%A %d %B %Y}"
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
    fermati = campi.get("FERMATI", "no")
    if campi.get("PREFLIGHT", "ok").lower().startswith("fallito") and fermati.lower().startswith("no"):
        fermati = "si': preflight " + campi["PREFLIGHT"]
    return {"intento": campi.get("INTENTO", "?")[:6], "template": campi.get("INTENTO", ""),
            "fermati": fermati, "nota": campi.get("NOTA", ""), "bozza": bozza}


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

    candidate = []
    for p in persone:
        testo = ultima.get(p["id"], "")
        if len(testo.strip()) < 30 or p["id"] in aperte or p.get("stage") in INTOCCABILI:
            continue
        candidate.append((p, testo))
        if len(candidate) >= QUANTI:
            break

    def lavora(coppia):
        p, testo = coppia
        nome = (p.get("company") or p.get("name") or p.get("email") or "")[:34]
        b = chiedi_bozza(p, testo)
        if not b:
            return (p, nome, None, [])
        errori = cancello(b["bozza"])
        if errori:
            b2 = chiedi_bozza(p, testo, riprova="; ".join(errori))
            if b2 and not cancello(b2["bozza"]):
                return (p, nome, b2, [])
        return (p, nome, b, errori)

    fatte, ferme, bocciate = 0, 0, 0
    with ThreadPoolExecutor(max_workers=IN_PARALLELO) as pool:
        esiti = list(pool.map(lavora, candidate))
    for p, nome, b, errori in esiti:
        if not b:
            print(f"  ? {nome}: risposta del cervello non leggibile"); continue
        if errori:
            bocciate += 1
        ferma = not b["fermati"].lower().startswith("no")
        titolo = (f"Da guardare tu: {nome}" if ferma else f"Bozza per {nome}") + f", {b['intento']}"
        perche = (b["fermati"] if ferma else b["nota"])[:280] + (f", CANCELLO: {'; '.join(errori)}" if errori else "")
        print(f"\n  [{b['intento']}] {titolo}\n      {perche}\n      " + b["bozza"][:220].replace("\n", " ") + "…")
        if not PROVA:
            proponi("umano" if ferma else "risposta", titolo, prospect_id=p["id"], perche=perche,
                    azione={"bozza": b["bozza"], "intento": b["intento"], "template": b["template"]})
        if ferma: ferme += 1
        else: fatte += 1

    print(f"\n  bozze pronte {fatte}, da guardare tu {ferme}, non passate il cancello {bocciate}")

    # ── il gigante buono: i negativi cortesi, una volta sola ────────
    negativi = sb("GET", "/rest/v1/prospects?classificazione=eq.negativo&fuori=eq.false&analysis_sent=eq.false"
                         "&select=id,name,company,email,classificazione,stage,analysis_sent,last_reply_at,sector,city,enriched,no_followup"
                         "&order=last_reply_at.desc&limit=200") or []
    soppresse = sb("GET", "/rest/v1/suppressions?select=email,domain&limit=5000") or []
    mail_no = {(x.get("email") or "").lower() for x in soppresse}
    dom_no = {(x.get("domain") or "").lower() for x in soppresse if x.get("domain")}
    gb = 0
    for p in negativi:
        if gb >= QUANTI_GB or p["id"] in aperte or p.get("stage") in INTOCCABILI:
            continue
        testo = ultima.get(p["id"], "")
        mail = (p.get("email") or "").lower()
        if len(testo.strip()) < 20 or NON_TOCCARE.search(testo) or mail in mail_no or mail.split("@")[-1] in dom_no:
            continue
        fit = (p.get("enriched") or {}).get("google_fit") or {}
        if fit.get("verdetto") == "NO":
            continue                       # se non era un cliente possibile, l'analisi non ha senso
        nome = (p.get("company") or p.get("name") or mail)[:34]
        fatti = {"nome": p.get("name") or "", "azienda": p.get("company") or "", "settore": p.get("sector"), "citta": p.get("city"),
                 "google_fit": {"provincia": fit.get("provincia"), "zona": fit.get("zona"), "cosa_fa": fit.get("cosa_fa")} if fit else None}
        prompt = (ISTRUZIONE_GB + cervello.istruzione("chat") + f"\n\nVALORI: {{{{CALENDARIO}}}} = {CALENDARIO}"
                  f"\n\nLA SCHEDA:\n{fatti}\n\nIL SUO NO:\n{testo[:1500]}")
        grezzo = cervello._chiedi(prompt) or ""
        m = re.search(r"\n\s*-{3,}\s*\n", grezzo)
        if not m:
            continue
        testa, bozza = grezzo[:m.start()], grezzo[m.end():].strip().strip("`").strip()
        fermati = next((r.split(":", 1)[1].strip() for r in testa.splitlines() if r.upper().startswith("FERMATI")), "no")
        nota = next((r.split(":", 1)[1].strip() for r in testa.splitlines() if r.upper().startswith("NOTA")), "")
        errori = cancello(bozza)
        if errori or not fermati.lower().startswith("no"):
            print(f"  [GB] salto {nome}: {fermati if not fermati.lower().startswith('no') else '; '.join(errori)}")
            continue
        print(f"\n  [GB] Gigante buono per {nome}\n      " + bozza[:200].replace("\n", " ") + "…")
        if not PROVA:
            proponi("risposta", f"Gigante buono per {nome}, INT-GB", prospect_id=p["id"],
                    perche=("Ci ha detto no con garbo: gli lasciamo l'analisi lo stesso, una volta sola. Allega il PDF dell'analisi. " + nota)[:280],
                    azione={"bozza": bozza, "intento": "INT-GB", "template": "INT-GB"})
        gb += 1
    print(f"  giganti buoni pronti: {gb}")
    # il telefono di Dre: una riga, solo se c'e' qualcosa da approvare
    if not PROVA and (fatte or ferme):
        from avvisa import avvisa
        pezzi = ([f"{fatte} bozze da approvare"] if fatte else []) + ([f"{ferme} da guardare tu"] if ferme else [])
        avvisa(", ".join(pezzi) + ". Apri la posta e approva.")


if __name__ == "__main__":
    main()
