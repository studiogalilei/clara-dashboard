#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""IL BANCO DI PROVA — la prima risposta contro quello che Dre ha mandato davvero (29/9/2026).

PERCHE'
Dre, 29/9: «verifichiamo in sandbox che scriva le mail correttamente: 70 esempi
di mail reali che sono su Smartlead, e guarda se risponde come avevo risposto
io». E' la «cartella del lavoro accettato» del video di Isenberg, e il set
d'oro della ricerca: casi veri, con la risposta giusta, su cui si riprova il
sistema prima di fidarsi.

COME
Per ogni lead che ci ha risposto e a cui abbiamo risposto noi, da Smartlead:
  1. il filo si taglia alla SUA prima risposta vera: il sistema vede solo
     quello che c'era prima che Dre scrivesse (la risposta di Dre non la vede);
  2. il Preparatore scrive la bozza come in produzione (bozze.chiedi_bozza),
     poi il cancello qualita', la seconda testa, il cancello della prima
     risposta automatica e il Revisore: la stessa strada di una mail vera;
  3. un giudice (modello diverso) confronta la bozza con la risposta di Dre e
     da' un verdetto secco: STESSA SOSTANZA, SOLO STILE, SOSTANZA DIVERSA,
     ERRORE GRAVE.
Il numero che conta: fra le mail che sarebbero PARTITE DA SOLE, quante sono
sostanza diversa o errore grave. Deve essere zero, o quasi.

NON SCRIVE NIENTE. Legge Supabase e Smartlead, scrive solo il risultato in un
file JSON (--esce). Nessuna proposta, nessun PATCH: il filo si costruisce qui
e non passa da lettura.filo (che riempie i segnaposto nel CRM).

USO
  python3 scripts/banco.py --quanti 70 --esce /percorso/banco.json
"""

import datetime
import html
import json
import os
import re
import sys
import threading
import urllib.parse
from concurrent.futures import ThreadPoolExecutor

os.environ["PROVA"] = "1"                   # cintura: nessuna proposta, qualunque cosa succeda
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from stanza import sb, quando                                  # noqa: E402
import cervello                                                # noqa: E402
import lettura                                                 # noqa: E402
import bozze                                                   # noqa: E402
import manda                                                   # noqa: E402
import prima_risposta as R                                     # noqa: E402

QUANTI = int(sys.argv[sys.argv.index("--quanti") + 1]) if "--quanti" in sys.argv else 70
ESCE = sys.argv[sys.argv.index("--esce") + 1] if "--esce" in sys.argv else "banco.json"
GIUDICE = "gpt-5" if cervello.FORNITORE == "openai" else None
CITAZIONE = re.compile(r"\n\s*(Il giorno .{5,120}ha scritto|On .{5,160}wrote|Da: |From: |-----\s*Original|Inviato da)", re.I)
_scrivi = threading.Lock()


def testo(corpo_html):
    """Da HTML di Smartlead a testo semplice, a capo compresi."""
    t = re.sub(r"(?i)<br\s*/?>|</p>|</div>", "\n", corpo_html or "")
    t = html.unescape(re.sub(r"<[^>]+>", "", t))
    return re.sub(r"\n{3,}", "\n\n", t.replace("\r", "")).strip()


def solo_suo(t):
    """La mail senza la citazione di sotto."""
    m = CITAZIONE.search(t or "")
    return (t[:m.start()] if m else t).strip()


def storia(p):
    """Il filo da Smartlead: tutte le campagne dove ha risposto, in ordine di tempo."""
    d = manda.sl("GET", f"/leads/?email={urllib.parse.quote(p['email'])}")
    righe = []
    for c in (d.get("lead_campaign_data") or []) if isinstance(d, dict) else []:
        if not c.get("last_reply_at"):
            continue
        h = manda.sl("GET", f"/campaigns/{int(c['campaign_id'])}/leads/{int(d['id'])}/message-history") or {}
        for m in h.get("history") or []:
            kind = "email_in" if m.get("type") == "REPLY" else "email_out"
            righe.append({"kind": kind, "at": str(m.get("time") or ""), "body": testo(m.get("email_body"))})
    righe.sort(key=lambda r: r["at"])
    return righe


def caso(p):
    """Taglia il filo alla sua prima risposta vera e trova la risposta di Dre dopo."""
    righe = storia(p)
    for i, r in enumerate(righe):
        if r["kind"] != "email_in" or len(solo_suo(r["body"])) < 8:
            continue
        prima = righe[:i + 1]
        fatti = lettura.ha_gia(p, prima)
        if fatti.get("autorisposta"):
            continue                         # un fuori ufficio non e' la sua risposta
        dopo = [x for x in righe[i + 1:] if x["kind"] == "email_out"]
        if not dopo:
            return None
        oro = dopo[0]
        giorni = (quando(oro["at"]) - quando(r["at"])).total_seconds() / 86400 if oro["at"] and r["at"] else 99
        if giorni > 10 or len(solo_suo(oro["body"])) < 40:
            return None                      # non e' una risposta alla sua mail, e' un'altra sequenza
        return {"prima": prima, "loro": r, "oro": oro, "fatti": fatti}
    return None


def giudica(loro, oro, bozza):
    prompt = f"""Sei il GIUDICE di Studio Galilei. Confronti due risposte alla stessa mail di un'azienda.
La prima l'ha scritta Dre, il titolare: e' quella giusta per definizione. La seconda l'ha scritta il sistema.
Non ti interessano: date e orari proposti per la call (cambiano col giorno), firma, saluti, piccole differenze di
parole. Ti interessa: la bozza fa la STESSA COSA di Dre? (manda o promette l'analisi quando lui la manda, propone
la call quando lui la propone, risponde alla domanda a cui lui risponde, non dice cose che lui non direbbe).

LA LORO MAIL:
{solo_suo(loro)[:1500]}

LA RISPOSTA DI DRE (quella giusta):
{solo_suo(oro)[:1800]}

LA BOZZA DEL SISTEMA:
{bozza[:1800]}

Verdetto, uno solo:
- STESSA: fa la stessa cosa, con parole simili o diverse;
- STILE: fa la stessa cosa ma il tono o la forma sono da ritoccare;
- SOSTANZA: fa una cosa diversa (manca l'analisi, manca la call, non risponde alla domanda, aggiunge un'offerta...);
- GRAVE: una mail che non doveva partire: nome o azienda sbagliati, promette cose false, risponde a un no, tono
  sbagliato per una persona reale, o Dre ha fatto una cosa completamente diversa (es. ha chiesto chi e' il referente).

Rispondi SOLO con una riga: «VERDETTO: motivo in venti parole»."""
    r = " ".join((cervello._chiedi(prompt, GIUDICE) or "").split()).strip("«»\"' ")
    r = re.sub(r"^VERDETTO\s*:\s*", "", r, flags=re.I)
    v = re.split(r"[:\s]", r, 1)[0].strip("*.").upper()
    return (v if v in ("STESSA", "STILE", "SOSTANZA", "GRAVE") else "?"), (r.split(":", 1)[1].strip() if ":" in r else r)[:240]


def prova_uno(p, c):
    # la scheda com'era PRIMA della risposta di Dre: analisi non ancora mandata
    # (e con quello che e' successo DOPO tolto: se oggi e' in pipeline o cliente, allora non lo era)
    ps = {**p, "analysis_sent": False, "analysis_sent_at": None, "stage": "risposto", "last_reply_at": c["loro"]["at"],
          "pipeline_stage": None, "fuori": False, "no_followup": False}
    letti = lettura.ha_gia(ps, c["prima"])
    loro = c["loro"]["body"]
    out = {"email": p["email"], "azienda": p.get("company") or p.get("name") or "", "classe": p.get("classificazione"),
           "loro_il": c["loro"]["at"][:16], "loro": solo_suo(loro)[:700], "oro": solo_suo(c["oro"]["body"])[:1200],
           "analisi_pdf": bool(p.get("analysis_pdf"))}
    b = bozze.chiedi_bozza(ps, loro, letti=letti)
    if not b:
        out["saltato"] = "il Preparatore non ha dato una bozza leggibile"; return out
    niente = not p.get("analysis_pdf") and ((p.get("enriched") or {}).get("google_fit") or {}).get("verdetto") == "NO"
    if not niente:
        b = bozze.testo_di_dre(b, ps, letti)             # 29/9: il testo di Dre, come in produzione
    out["dal_codice"] = bool(b.get("dal_codice"))
    errori = bozze.cancello(b["bozza"], senza_analisi=niente)
    verdetto, motivo = lettura.coerenza(letti, b["bozza"], None)
    ferma = not b["fermati"].lower().startswith("no") or verdetto != "COERENTE"
    pr = {"id": 0, "tipo": "umano" if ferma else "risposta", "titolo": ("Da guardare tu" if ferma else "Bozza"),
          "azione": {"bozza": b["bozza"], "intento": b["intento"],
                     "lettura": {**letti, "coerenza": verdetto, "coerenza_motivo": motivo, "gruppo": None}}}
    no = R.perche_no(pr, ps) + ([f"cancello: {'; '.join(errori)}"] if errori else [])
    rev = R.revisore(pr, ps, letti) if not no else ("-", "")
    out.update({"intento": b["intento"], "fermati": b["fermati"][:160], "coerenza": verdetto, "coerenza_motivo": motivo,
                "cancello": errori, "gate_no": no, "revisore": rev[0], "revisore_motivo": rev[1],
                "partirebbe": not no and rev[0] == "OK", "bozza": b["bozza"]})
    out["giudice"], out["giudice_motivo"] = giudica(loro, c["oro"]["body"], b["bozza"])
    return out


def rigiudica(entra, esce):
    """Il secondo giudizio (29/9). Il primo confondeva gli errori veri con il template
    che e' cambiato: le risposte di Dre di luglio non avevano la proposta con garanzia
    ne' la presentazione, quelle di oggi si'. Qui il giudice ha il template di oggi e
    la data della risposta di Dre, e una categoria in piu': TEMPLATE."""
    oggi = R._template_approvati()
    casi = {}
    for f in entra:
        for x in json.load(open(f)):
            if x and not x.get("saltato"):
                casi[x["email"]] = x

    def uno(x):
        prompt = f"""Sei il GIUDICE di Studio Galilei. Confronti la risposta che Dre ha mandato il {x['loro_il'][:10]} con la
bozza che il sistema scrive OGGI alla stessa mail. Dre nel frattempo ha aggiornato il suo template: quello di oggi e' qui
sotto ed e' approvato da lui. Se la bozza e' diversa da Dre SOLO perche' segue il template di oggi (proposta con garanzia,
presentazione allegata, frasi standard), quella non e' una differenza: e' TEMPLATE.
Ignora date, orari, firma, saluti, link del calendario diversi.

IL TEMPLATE DI OGGI (approvato):
{oggi[:6000]}

LA LORO MAIL:
{x['loro'][:1200]}

LA RISPOSTA DI DRE:
{x['oro'][:1500]}

LA BOZZA DI OGGI:
{x['bozza'][:1500]}

Verdetto, uno solo:
- STESSA: fa la stessa cosa di Dre;
- STILE: stessa cosa, forma da ritoccare;
- TEMPLATE: diversa da Dre solo dove segue il template di oggi;
- SOSTANZA: fa una cosa diversa che Dre non farebbe nemmeno oggi (manca l'analisi, manca la proposta di call, non risponde
  alla domanda, promette cose, ignora un'informazione importante della loro mail);
- GRAVE: non doveva partire (nome o azienda sbagliati, risponde a un no, tono sbagliato, dice il falso).
Rispondi SOLO con una riga: «VERDETTO: motivo in venti parole»."""
        r = " ".join((cervello._chiedi(prompt, GIUDICE) or "").split()).strip("«»\"' ")
        r = re.sub(r"^VERDETTO\s*:\s*", "", r, flags=re.I)
        v = re.split(r"[:\s]", r, 1)[0].strip("*.").upper()
        t = x["bozza"].lower()
        return {**x, "giudice2": v if v in ("STESSA", "STILE", "TEMPLATE", "SOSTANZA", "GRAVE") else "?",
                "giudice2_motivo": (r.split(":", 1)[1].strip() if ":" in r else r)[:240],
                "partirebbe_ora": bool(x.get("partirebbe")) and "analisi" in t and "calendar.app.google" in t}

    with ThreadPoolExecutor(max_workers=6) as ex:
        tutti = list(ex.map(uno, casi.values()))
    json.dump(tutti, open(esce, "w"), ensure_ascii=False, indent=1)
    from collections import Counter
    for nome, xs in (("tutti", tutti), ("partirebbero (cancello nuovo)", [x for x in tutti if x["partirebbe_ora"]])):
        print(f"  {nome:30} {len(xs):3}  {dict(Counter(x['giudice2'] for x in xs))}")


def main():
    if "--rigiudica" in sys.argv:
        i = sys.argv.index("--rigiudica")
        return rigiudica(sys.argv[i + 1].split(","), ESCE)
    bozze.LEZIONI = bozze.come_corregge_dre()         # come in produzione
    lettura.filo = lambda p: CORRENTE.get(p["id"], [])  # il filo tagliato, mai quello di oggi
    campi = ("id,name,company,email,email_alt,classificazione,stage,analysis_sent,analysis_sent_at,analysis_pdf,"
             "last_reply_at,sector,city,enriched,campaign_id,lead_id,campaign,fuori,no_followup,pipeline_stage")
    pool = sb("GET", f"/rest/v1/prospects?select={campi}&classificazione=in.(positivo,tiepido)"
                     f"&last_reply_at=not.is.null&order=last_reply_at.desc&limit=400") or []
    pool = [p for p in pool if "usa" not in (p.get("campaign") or "").lower() and p.get("email")]
    if "--inverso" in sys.argv:                          # un secondo banco dalla fine, per fare prima
        pool.reverse()
    print(f"BANCO DI PROVA: {len(pool)} lead positivi o tiepidi, ne servono {QUANTI}", flush=True)
    fatti = []

    def uno(p):
        if len([x for x in fatti if x and not x.get("saltato")]) >= QUANTI:
            return None
        try:
            c = caso(p)
        except Exception as e:                                # noqa: BLE001
            return {"email": p["email"], "saltato": f"smartlead: {str(e)[:80]}"}
        if not c:
            return None
        CORRENTE[p["id"]] = c["prima"]
        try:
            r = prova_uno(p, c)
        except Exception as e:                                # noqa: BLE001
            r = {"email": p["email"], "saltato": f"errore: {str(e)[:120]}"}
        with _scrivi:
            fatti.append(r)
            n = len([x for x in fatti if x and not x.get("saltato")])
            if r and not r.get("saltato"):
                print(f"  {n:3} {r['azienda'][:28]:28} {r.get('intento','?'):7} {'PARTE' if r.get('partirebbe') else 'a Dre':6} "
                      f"{r.get('giudice','?'):9} {r.get('giudice_motivo','')[:70]}", flush=True)
            json.dump([x for x in fatti if x], open(ESCE, "w"), ensure_ascii=False, indent=1)
        return r

    with ThreadPoolExecutor(max_workers=5) as ex:
        list(ex.map(uno, pool))
    buoni = [x for x in fatti if x and not x.get("saltato")]
    json.dump([x for x in fatti if x], open(ESCE, "w"), ensure_ascii=False, indent=1)
    parte = [x for x in buoni if x.get("partirebbe")]
    conta = lambda xs, v: sum(1 for x in xs if x.get("giudice") == v)
    print(f"\nCASI {len(buoni)}: partirebbero da soli {len(parte)}, resterebbero a Dre {len(buoni) - len(parte)}")
    for nome, xs in (("tutti", buoni), ("partirebbero", parte)):
        print(f"  {nome:13} STESSA {conta(xs, 'STESSA')}  STILE {conta(xs, 'STILE')}  SOSTANZA {conta(xs, 'SOSTANZA')}  GRAVE {conta(xs, 'GRAVE')}")


CORRENTE = {}


if __name__ == "__main__":
    main()
