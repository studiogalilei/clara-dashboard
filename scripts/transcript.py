#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""IL TRANSCRIPT — Clara legge la call e propone cosa fare dopo (7/9/2026).

PERCHE'
Deciso con Dre il 7/9: Granola non ha l'API sul suo piano, quindi il
transcript lo incolla lui nella Scheda a fine call («aggiorno ogni volta lo
stato del prospect direttamente con i transcript»). Da li' in poi tocca a
Clara: legge, capisce cosa si sono detti, e propone in stanza il prossimo
passo con la data, e la fase se e' cambiata. Dre dice si' e la scheda si
aggiorna; dice no e resta com'e'. Clara propone, Dre dispone.

COSA FA
Per ogni interazione `transcript` senza ancora una proposta (la proposta
porta azione.transcript_id) chiede al cervello: riassunto in due righe,
prossimo passo, data, fase. Mette UNA proposta tipo `avanza` con
azione.prospects = {next_action, next_action_date, pipeline_stage?}.

USO
  python3 scripts/transcript.py            legge i transcript nuovi
  python3 scripts/transcript.py --prova    mostra e non scrive
  python3 scripts/transcript.py --file f   legge un file di prova, non scrive
"""

import datetime
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from stanza import sb, proponi                             # noqa: E402
import cervello                                            # noqa: E402

FASI = ("conoscitiva", "tecnica", "avvio", "prova", "cliente", "perso")
NOME = {"conoscitiva": "Conoscitiva", "tecnica": "Call tecnica", "avvio": "Avvio", "prova": "Periodo di prova", "cliente": "Cliente", "perso": "Perso"}

PROMPT = """Sei l'assistente commerciale di Studio Galilei, agenzia Google Ads.
Dre ha appena fatto una call con un'azienda e ti passa il transcript (o il suo
riassunto). Leggi e rispondi SOLO con queste quattro righe, niente altro:

RIASSUNTO: due frasi, cosa si sono detti e a che punto e' il rapporto
PROSSIMO_PASSO: una frase operativa, quello che dobbiamo fare noi (es. «mandare la proposta con i tre pacchetti», «call tecnica con Carlo»)
QUANDO: la data in formato YYYY-MM-DD se e' stata detta o si deduce (oggi e' {oggi}), altrimenti -
FASE: una fra conoscitiva | tecnica | avvio | prova | cliente | perso, oppure - se non cambia rispetto a «{fase}»

Le fasi: conoscitiva = prima call di conoscenza; tecnica = call tecnica e
proposta economica; avvio = ha accettato, si parte con l'onboarding; prova = i due
mesi di periodo di prova sono partiti (1.500 € × 2);
cliente = attivo e paga; perso = ha detto no o e' sparito dopo la proposta.
Non inventare date: se non c'e', metti -.

AZIENDA: {azienda}
FASE ATTUALE: {fase}

TRANSCRIPT:
{testo}
"""


def leggi_call(azienda, fase, testo):
    prompt = PROMPT.format(oggi=datetime.date.today().isoformat(), fase=fase or "prospect", azienda=azienda,
                           testo=" ".join(testo.split())[:12000]) + cervello.istruzione("lettura")
    fuori = {"RIASSUNTO": "", "PROSSIMO_PASSO": "", "QUANDO": "-", "FASE": "-"}
    for riga in (cervello._chiedi(prompt) or "").splitlines():
        m = re.match(r"\s*(RIASSUNTO|PROSSIMO_PASSO|QUANDO|FASE)\s*:\s*(.*)", riga)
        if m:
            fuori[m.group(1)] = m.group(2).strip()
    quando = fuori["QUANDO"] if re.fullmatch(r"\d{4}-\d{2}-\d{2}", fuori["QUANDO"]) else None
    fase_nuova = fuori["FASE"].lower().strip()
    fase_nuova = fase_nuova if fase_nuova in FASI and fase_nuova != fase else None
    return fuori["RIASSUNTO"], fuori["PROSSIMO_PASSO"], quando, fase_nuova


def main():
    prova = "--prova" in sys.argv
    if "--file" in sys.argv:
        testo = open(sys.argv[sys.argv.index("--file") + 1], encoding="utf-8").read()
        r, p, q, f = leggi_call("Azienda di prova", "conoscitiva", testo)
        print(f"  RIASSUNTO {r}\n  PASSO {p}\n  QUANDO {q}\n  FASE {f}")
        return

    gia = {(pr.get("azione") or {}).get("transcript_id")
           for pr in (sb("GET", "/rest/v1/proposte?select=azione&tipo=eq.avanza&limit=5000") or [])}
    da = (datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=60)).strftime("%Y-%m-%dT%H:%M:%SZ")
    transcript = sb("GET", f"/rest/v1/interactions?select=id,at,prospect_id,body&kind=eq.transcript&at=gte.{da}&order=at.desc&limit=200") or []
    nuovi = [t for t in transcript if t["id"] not in gia and t.get("prospect_id") and len(t.get("body") or "") > 200]
    proposte = 0
    for t in nuovi:
        p = (sb("GET", f"/rest/v1/prospects?select=id,name,company,fuori,pipeline_stage&id=eq.{t['prospect_id']}") or [None])[0]
        if not p:
            continue
        azienda = p.get("company") or p.get("name") or "?"
        fase = p.get("pipeline_stage") if p.get("fuori") else None
        riassunto, passo, quando, fase_nuova = leggi_call(azienda, fase, t["body"])
        if not passo and not fase_nuova:
            continue
        pezzi = []
        if fase_nuova:
            pezzi.append(f"fase → {NOME[fase_nuova]}")
        if passo:
            pezzi.append(f"prossimo passo: {passo}" + (f" entro il {quando[8:10]}/{quando[5:7]}" if quando else ""))
        titolo = f"{azienda}, dopo la call: " + "; ".join(pezzi)
        azione = {"transcript_id": t["id"], "prospects": {}}
        if passo:
            azione["prospects"]["next_action"] = passo[:200]
            azione["prospects"]["next_action_date"] = quando
        if fase_nuova:
            azione["prospects"]["pipeline_stage"] = fase_nuova
            if not p.get("fuori"):
                azione["prospects"].update({"fuori": True, "fuori_at": datetime.datetime.now(datetime.timezone.utc).isoformat()})
        if prova:
            print(f"  {titolo}\n      {riassunto}")
            continue
        if proponi("avanza", titolo, prospect_id=p["id"], perche=riassunto[:280], azione=azione):
            proposte += 1
    print(f"transcript: {proposte} proposte, {len(nuovi)} transcript nuovi letti")


if __name__ == "__main__":
    main()
