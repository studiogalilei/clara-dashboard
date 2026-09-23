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
import urllib.parse

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
AZIONI: da una a tre righe, ognuna «- [oggi|domani|YYYY-MM-DD] cosa fare», solo cose concrete promesse o decise in call (mandare X, chiamare Y, preparare Z). Poche e vere: se non ce ne sono, «- nessuna»

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


AZIONI = []        # le azioni dell'ultima call letta: (quando, cosa)
DASHBOARD = os.environ.get("DASHBOARD_URL", "https://studiogalilei.github.io/clara/")


def blocchi_in_calendario(p, azienda, riassunto, azioni, prova):
    """Le azioni della call finiscono nel calendario LO STESSO GIORNO (Dre, 23/9:
    «poche cose ma farle subito»), blocchi da 15 minuti marcati Clara, liberi,
    nel calendario «SG Scadenze» che la squadra gia' vede. Dentro: il riassunto
    e il link alla scheda. Stesso transcript, stessi blocchi: l'id e' stabile."""
    import calendario_sg as cal
    try:
        cid = cal.calendario(prova)
    except Exception as e:                                        # noqa: BLE001
        print(f"  calendario non raggiungibile: {str(e)[:100]}"); return 0
    if not cid:
        return 0
    roma = datetime.timezone(datetime.timedelta(hours=2))
    ora = datetime.datetime.now(roma)
    # il primo buco: fra mezz'ora se e' ancora giornata, se no domattina alle 9:15
    inizio = (ora + datetime.timedelta(minutes=30)).replace(second=0, microsecond=0)
    inizio = inizio.replace(minute=(inizio.minute // 15) * 15)
    if inizio.hour >= 18 or inizio.hour < 8:
        inizio = (inizio + datetime.timedelta(days=1 if inizio.hour >= 18 else 0)).replace(hour=9, minute=15)
    fatti = 0
    for i, (quando, cosa) in enumerate(azioni):
        if quando == "domani":
            t0 = (inizio + datetime.timedelta(days=1)).replace(hour=9, minute=15) + datetime.timedelta(minutes=15 * i)
        elif re.fullmatch(r"\d{4}-\d{2}-\d{2}", quando):
            t0 = datetime.datetime.fromisoformat(quando).replace(hour=9, minute=15, tzinfo=roma) + datetime.timedelta(minutes=15 * i)
        else:
            t0 = inizio + datetime.timedelta(minutes=15 * i)
        t1 = t0 + datetime.timedelta(minutes=15)
        eid = cal.id_evento(f"call-{p['id']}-{cosa}")
        corpo = {"id": eid, "summary": f"Clara: {cosa} · {azienda}"[:200],
                 "description": (f"Dalla call con {azienda}.\n{riassunto[:400]}\n\nScheda: {DASHBOARD}?scheda={p['id']}")[:900],
                 "start": {"dateTime": t0.isoformat(), "timeZone": "Europe/Rome"}, "end": {"dateTime": t1.isoformat(), "timeZone": "Europe/Rome"},
                 "transparency": "transparent", "reminders": {"useDefault": False}}
        if prova:
            print(f"  [prova] {t0:%d/%m %H:%M}  Clara: {cosa} · {azienda}"); fatti += 1; continue
        try:
            cal.g("POST", f"{cal.CAL}/calendars/{urllib.parse.quote(cid)}/events", corpo, email=cal.PADRONE); fatti += 1
        except RuntimeError as e:
            if "409" in str(e) or "duplicate" in str(e).lower():
                try:
                    cal.g("PUT", f"{cal.CAL}/calendars/{urllib.parse.quote(cid)}/events/{eid}", corpo, email=cal.PADRONE); fatti += 1
                except RuntimeError as e2:
                    print(f"  blocco non aggiornato: {str(e2)[:100]}")
            else:
                print(f"  blocco non scritto: {str(e)[:100]}")
    return fatti


def leggi_call(azienda, fase, testo):
    prompt = PROMPT.format(oggi=datetime.date.today().isoformat(), fase=fase or "prospect", azienda=azienda,
                           testo=" ".join(testo.split())[:12000]) + cervello.istruzione("lettura")
    fuori = {"RIASSUNTO": "", "PROSSIMO_PASSO": "", "QUANDO": "-", "FASE": "-"}
    azioni = []
    dentro_azioni = False
    for riga in (cervello._chiedi(prompt) or "").splitlines():
        m = re.match(r"\s*(RIASSUNTO|PROSSIMO_PASSO|QUANDO|FASE|AZIONI)\s*:\s*(.*)", riga)
        if m:
            dentro_azioni = m.group(1) == "AZIONI"
            if not dentro_azioni:
                fuori[m.group(1)] = m.group(2).strip()
            continue
        a = re.match(r"\s*-\s*\[(oggi|domani|\d{4}-\d{2}-\d{2})\]\s*(.+)", riga, re.I)
        if dentro_azioni and a and "nessuna" not in a.group(2).lower():
            azioni.append((a.group(1).lower(), a.group(2).strip()[:120]))
    AZIONI.clear(); AZIONI.extend(azioni[:3])
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
        azioni = list(AZIONI)
        if prova:
            print(f"  {titolo}\n      {riassunto}\n      azioni: {azioni}")
            blocchi_in_calendario(p, azienda, riassunto, azioni, True)
            continue
        n_blocchi = blocchi_in_calendario(p, azienda, riassunto, azioni, False)
        if n_blocchi:
            print(f"  {azienda}: {n_blocchi} blocchi in calendario")
        # 23/9 (pulizia): il riassunto va nella scheda da solo, senza chiedere.
        # Le fasi di pipeline no: quelle le muove Dre.
        from stanza import di_clara
        try:
            di_clara("nota", f"Dalla call: {riassunto[:600]}", prospect_id=p["id"])
            if azione.get("prospects", {}).get("next_action"):
                sb("PATCH", f"/rest/v1/prospects?id=eq.{p['id']}", {"next_action": azione["prospects"]["next_action"], "next_action_date": azione["prospects"].get("next_action_date")})
            proposte += 1
        except Exception as e:                                   # noqa: BLE001
            print(f"  nota non scritta: {str(e)[:80]}")
    print(f"transcript: {proposte} proposte, {len(nuovi)} transcript nuovi letti")


if __name__ == "__main__":
    main()
