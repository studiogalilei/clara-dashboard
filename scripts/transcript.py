#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""IL TRANSCRIPT — Clara legge la call, sposta il lead e mette in calendario le cose da fare (7/9/2026, rifatto il 24/9).

PERCHE'
Dre, 24/9: «prenda in automatico i transcript delle call e aggiorni la posizione
del lead in automatico; il manuale resta, ma voglio un sync realtime che dopo le
call aggiorna e crea task per lo stesso giorno in un blocco di mezz'ora dove
prendo in mano le cose da fare rilevate dal transcript». Prima (23/9) Clara
scriveva solo il riassunto e le fasi le muoveva Dre.

COSA FA, per ogni transcript nuovo (interazione `transcript` non ancora letta):
1. LEGGE: riassunto, prossimo passo, fase, e per la fase la frase della call che
   la giustifica (evidenza) e quanto e' sicura (sicuro | incerto).
2. AVANZAMENTO: se la fase e' cambiata, e' un passo avanti, e' fra conoscitiva,
   tecnica, avvio o prova, ed e' «sicuro», Clara sposta la carta da sola e
   scrive nella scheda perche' (l'evidenza). Cliente e perso, i passi indietro
   e i casi «incerto» NON si muovono da soli: finiscono in Posta come proposta
   con l'evidenza, e decide Dre. La mano di Dre resta: la carta si trascina
   come prima.
3. IL BLOCCO DOPO LA CALL: le cose da fare (da una a tre) vanno in UN evento di
   mezz'ora, «Clara: dopo la call con <azienda>», nel calendario SG Scadenze,
   nel primo buco libero del calendario di Dre lo stesso giorno in orario di
   lavoro (9-18, lunedi'-venerdi'), se no il primo buco del giorno dopo.
   Stesso transcript, stesso evento: se si rilegge, si aggiorna, non si duplica.
4. LA NOTA nella scheda (interazione `nota`, ref letta:<id>): riassunto, cosa ha
   fatto Clara e perche'. E' anche il segno che il transcript e' stato letto.

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
import zoneinfo

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from stanza import sb, proponi                             # noqa: E402
import cervello                                            # noqa: E402

FASI = ("conoscitiva", "tecnica", "avvio", "prova", "cliente", "perso")
NOME = {"conoscitiva": "Call Conoscitiva", "tecnica": "Call Tecnica", "avvio": "Call di Avvio", "prova": "Periodo di prova", "cliente": "Cliente", "perso": "Perso"}
DA_SOLA = ("tecnica", "avvio", "prova")        # le fasi in cui Clara sposta da sola; cliente e perso li decide Dre
ROMA = zoneinfo.ZoneInfo("Europe/Rome")
ORARIO = (9, 18)                               # orario di lavoro, ore di Roma
DURATA = 30                                    # minuti del blocco dopo la call
DASHBOARD = os.environ.get("DASHBOARD_URL", "https://studiogalilei.github.io/clara/")

PROMPT = """Sei l'assistente commerciale di Studio Galilei, agenzia Google Ads.
Dre ha appena fatto una call con un'azienda e ti passa il transcript (o il suo
riassunto). Leggi e rispondi SOLO con queste righe, niente altro:

RIASSUNTO: due frasi, cosa si sono detti e a che punto e' il rapporto
PROSSIMO_PASSO: una frase operativa, quello che dobbiamo fare noi (es. «mandare la proposta con i tre pacchetti», «call tecnica con Carlo»)
QUANDO: la data in formato YYYY-MM-DD se e' stata detta o si deduce (oggi e' {oggi}), altrimenti -
FASE: una fra conoscitiva | tecnica | avvio | prova | cliente | perso, oppure - se non cambia rispetto a «{fase}»
EVIDENZA: la frase della call, citata breve, che giustifica la FASE; «-» se FASE e' -
CERTEZZA: sicuro | incerto. Sicuro solo se la fase nuova e' stata detta o decisa in call in modo esplicito; se e' una tua deduzione, incerto
AZIONI: da una a tre righe, ognuna «- [oggi|domani|YYYY-MM-DD] cosa fare», solo cose concrete promesse o decise in call (mandare X, chiamare Y, preparare Z). Poche e vere: se non ce ne sono, «- nessuna»

Le fasi: conoscitiva = prima call di conoscenza; tecnica = call tecnica e
proposta economica; avvio = ha accettato, si parte con l'onboarding; prova = i due
mesi di periodo di prova sono partiti (1.500 € × 2);
cliente = attivo e paga; perso = ha detto no o e' sparito dopo la proposta.
Non inventare date: se non c'e', metti -. Non inventare l'evidenza: se non c'e' una frase, CERTEZZA e' incerto.

AZIENDA: {azienda}
FASE ATTUALE: {fase}

TRANSCRIPT:
{testo}
"""


class Lettura:
    def __init__(self):
        self.riassunto = ""; self.passo = ""; self.quando = None
        self.fase = None; self.evidenza = ""; self.certezza = "incerto"; self.azioni = []


def leggi_call(azienda, fase, testo):
    prompt = (cervello.manuale("testa") + "\n\n" + PROMPT.format(oggi=datetime.date.today().isoformat(), fase=fase or "prospect", azienda=azienda,
                           testo=" ".join(testo.split())[:12000]) + cervello.istruzione("lettura"))
    campi = {"RIASSUNTO": "", "PROSSIMO_PASSO": "", "QUANDO": "-", "FASE": "-", "EVIDENZA": "-", "CERTEZZA": "incerto"}
    azioni, dentro_azioni = [], False
    for riga in (cervello._chiedi(prompt) or "").splitlines():
        m = re.match(r"\s*(RIASSUNTO|PROSSIMO_PASSO|QUANDO|FASE|EVIDENZA|CERTEZZA|AZIONI)\s*:\s*(.*)", riga)
        if m:
            dentro_azioni = m.group(1) == "AZIONI"
            if not dentro_azioni:
                campi[m.group(1)] = m.group(2).strip()
            continue
        a = re.match(r"\s*-\s*\[(oggi|domani|\d{4}-\d{2}-\d{2})\]\s*(.+)", riga, re.I)
        if dentro_azioni and a and "nessuna" not in a.group(2).lower():
            azioni.append((a.group(1).lower(), a.group(2).strip()[:120]))
    L = Lettura()
    L.riassunto, L.passo = campi["RIASSUNTO"], campi["PROSSIMO_PASSO"]
    L.quando = campi["QUANDO"] if re.fullmatch(r"\d{4}-\d{2}-\d{2}", campi["QUANDO"]) else None
    f = campi["FASE"].lower().strip()
    L.fase = f if f in FASI and f != fase else None
    L.evidenza = campi["EVIDENZA"].strip(" «»\"'") if campi["EVIDENZA"].strip() not in ("", "-") else ""
    L.certezza = "sicuro" if campi["CERTEZZA"].lower().startswith("sicuro") and L.evidenza else "incerto"
    L.azioni = azioni[:3]
    return L


# ── il blocco dopo la call ──────────────────────────────────────────
def _occupati(cal, cid, da, a):
    """I periodi occupati nel calendario di Dre (il suo e SG Scadenze)."""
    try:
        r = cal.g("POST", f"{cal.CAL}/freeBusy", {"timeMin": da.isoformat(), "timeMax": a.isoformat(), "timeZone": "Europe/Rome",
                                                   "items": [{"id": "primary"}, {"id": cid}]}, email=cal.PADRONE)
        out = []
        for c in (r.get("calendars") or {}).values():
            for b in c.get("busy") or []:
                out.append((datetime.datetime.fromisoformat(b["start"].replace("Z", "+00:00")).astimezone(ROMA),
                            datetime.datetime.fromisoformat(b["end"].replace("Z", "+00:00")).astimezone(ROMA)))
        return out
    except Exception as e:                                        # noqa: BLE001
        print(f"  freeBusy non letto ({str(e)[:80]}): uso l'agenda del workspace")
        rs = sb("GET", f"/rest/v1/agenda?select=at,fine&fonte=like.gcal*&at=gte.{da.astimezone(datetime.timezone.utc).isoformat()}"
                       f"&at=lte.{a.astimezone(datetime.timezone.utc).isoformat()}") or []
        out = []
        for x in rs:
            t0 = datetime.datetime.fromisoformat(x["at"].replace("Z", "+00:00")).astimezone(ROMA)
            t1 = datetime.datetime.fromisoformat(x["fine"].replace("Z", "+00:00")).astimezone(ROMA) if x.get("fine") else t0 + datetime.timedelta(hours=1)
            out.append((t0, t1))
        return out


def primo_buco(occupati, da):
    """Il primo blocco di mezz'ora libero, in orario di lavoro, da `da` in poi (max 5 giorni)."""
    t = da.replace(second=0, microsecond=0)
    t += datetime.timedelta(minutes=(15 - t.minute % 15) % 15)
    fine_giorni = 0
    while fine_giorni < 5 * 96:
        fine_giorni += 1
        if t.weekday() >= 5 or t.hour < ORARIO[0]:
            t = (t + datetime.timedelta(days=1 if t.weekday() >= 5 or t.hour >= ORARIO[0] else 0)).replace(hour=ORARIO[0], minute=0)
            continue
        t1 = t + datetime.timedelta(minutes=DURATA)
        if t1.hour > ORARIO[1] or (t1.hour == ORARIO[1] and t1.minute > 0):
            t = (t + datetime.timedelta(days=1)).replace(hour=ORARIO[0], minute=0)
            continue
        if any(a < t1 and b > t for a, b in occupati):
            t += datetime.timedelta(minutes=15)
            continue
        return t
    return da


def blocco_dopo_call(p, azienda, L, transcript_id, prova):
    """Le cose da fare in UN blocco di mezz'ora nel primo buco utile (Dre, 24/9)."""
    cose = list(L.azioni) or ([("oggi", L.passo)] if L.passo else [])
    if not cose:
        return None
    import calendario_sg as cal
    try:
        cid = cal.calendario(prova)
    except Exception as e:                                        # noqa: BLE001
        print(f"  calendario non raggiungibile: {str(e)[:100]}"); return None
    if not cid:
        return None
    ora = datetime.datetime.now(ROMA)
    da = ora + datetime.timedelta(minutes=10)
    occupati = _occupati(cal, cid, da, da + datetime.timedelta(days=5))
    t0 = primo_buco(occupati, da)
    t1 = t0 + datetime.timedelta(minutes=DURATA)
    righe = []
    for quando, cosa in cose:
        data = f" (entro il {quando[8:10]}/{quando[5:7]})" if re.fullmatch(r"\d{4}-\d{2}-\d{2}", quando) else (" (domani)" if quando == "domani" else "")
        righe.append(f"☐ {cosa}{data}")
    corpo = {"id": cal.id_evento(f"dopo-call-{transcript_id}"),
             "summary": f"Clara: dopo la call con {azienda}"[:200],
             "description": ("Cose da fare, dalla call:\n" + "\n".join(righe) + f"\n\nIn breve: {L.riassunto[:400]}\n\nScheda: {DASHBOARD}?scheda={p['id']}")[:1200],
             "start": {"dateTime": t0.isoformat(), "timeZone": "Europe/Rome"}, "end": {"dateTime": t1.isoformat(), "timeZone": "Europe/Rome"},
             "transparency": "opaque", "reminders": {"useDefault": False, "overrides": [{"method": "popup", "minutes": 10}]}}
    if prova:
        print(f"  [prova] {t0:%a %d/%m %H:%M}-{t1:%H:%M}  Clara: dopo la call con {azienda}\n         " + "\n         ".join(righe))
        return t0
    try:
        cal.g("POST", f"{cal.CAL}/calendars/{urllib.parse.quote(cid)}/events", corpo, email=cal.PADRONE)
    except RuntimeError as e:
        if "409" in str(e) or "duplicate" in str(e).lower():
            try:
                cal.g("PUT", f"{cal.CAL}/calendars/{urllib.parse.quote(cid)}/events/{corpo['id']}", corpo, email=cal.PADRONE)
            except RuntimeError as e2:
                print(f"  blocco non aggiornato: {str(e2)[:100]}"); return None
        else:
            print(f"  blocco non scritto: {str(e)[:100]}"); return None
    return t0


# ── l'avanzamento ───────────────────────────────────────────────────
def avanzamento(p, azienda, L, transcript_id, prova):
    """Sposta da sola se e' un passo avanti sicuro fra le fasi ammesse; se no propone.
    Torna una riga per la nota."""
    if not L.fase:
        return ""
    fase = p.get("pipeline_stage") if p.get("fuori") else None
    avanti = fase is None or FASI.index(L.fase) > FASI.index(fase)
    da_sola = L.fase in DA_SOLA and avanti and L.certezza == "sicuro"
    patch = {"pipeline_stage": L.fase}
    if not p.get("fuori"):
        patch.update({"fuori": True, "fuori_at": datetime.datetime.now(datetime.timezone.utc).isoformat()})
    if L.passo:
        patch.update({"next_action": L.passo[:200], "next_action_date": L.quando})
    if da_sola:
        if not prova:
            sb("PATCH", f"/rest/v1/prospects?id=eq.{p['id']}", patch)
        return f"Spostata in {NOME[L.fase]}. Dalla call: «{L.evidenza[:200]}»"
    # cliente, perso, passi indietro o dubbio: decide Dre, con l'evidenza davanti
    if not avanti:
        motivo = "non è un passo avanti"
    elif L.fase not in DA_SOLA:
        motivo = "questa fase la decidi tu"
    else:
        motivo = "in call non è stato detto in modo esplicito"
    prova_call = f"Dalla call: «{L.evidenza[:160]}»" if L.evidenza else "Nella call non c'è una frase che lo dica chiaramente."
    perche = f"Non l'ho spostata da sola: {motivo}. {prova_call}"
    if not prova:
        proponi("avanza", f"{azienda}: dopo la call, passa a {NOME[L.fase]}?", prospect_id=p["id"], perche=perche[:280],
                azione={"transcript_id": transcript_id, "prospects": patch})
    return f"Proposto in Posta: passare a {NOME[L.fase]} ({'incerto' if L.certezza != 'sicuro' else 'decidi tu'})."


def main():
    prova = "--prova" in sys.argv
    if "--file" in sys.argv:
        testo = open(sys.argv[sys.argv.index("--file") + 1], encoding="utf-8").read()
        L = leggi_call("Azienda di prova", "conoscitiva", testo)
        print(f"  RIASSUNTO {L.riassunto}\n  PASSO {L.passo}\n  QUANDO {L.quando}\n  FASE {L.fase}\n  EVIDENZA {L.evidenza}\n  CERTEZZA {L.certezza}\n  AZIONI {L.azioni}")
        p = {"id": "prova", "fuori": True, "pipeline_stage": "conoscitiva"}
        print("  " + avanzamento(p, "Azienda di prova", L, "prova", True))
        blocco_dopo_call(p, "Azienda di prova", L, "prova", True)
        return

    lette = {r["ref"][6:] for r in (sb("GET", "/rest/v1/interactions?select=ref&ref=like.letta:*&limit=5000") or []) if r.get("ref")}
    # «at» e' l'ora della call, non quella in cui arrivano gli appunti (che
    # possono arrivare il giorno dopo): si guardano gli ultimi tre giorni. Quelli
    # piu' vecchi hanno gia' la nota di prima e non si rileggono.
    da = (datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=3)).strftime("%Y-%m-%dT%H:%M:%SZ")
    transcript = sb("GET", f"/rest/v1/interactions?select=id,at,prospect_id,body&kind=eq.transcript&at=gte.{da}&order=at.desc&limit=200") or []
    nuovi = [t for t in transcript if str(t["id"]) not in lette and t.get("prospect_id") and len(t.get("body") or "") > 200]
    fatti = 0
    for t in nuovi:
        p = (sb("GET", f"/rest/v1/prospects?select=id,name,company,fuori,pipeline_stage&id=eq.{t['prospect_id']}") or [None])[0]
        if not p:
            continue
        azienda = p.get("company") or p.get("name") or "?"
        fase = p.get("pipeline_stage") if p.get("fuori") else None
        L = leggi_call(azienda, fase, t["body"])
        if not (L.riassunto or L.passo or L.fase or L.azioni):
            print(f"  {azienda}: il cervello non ha risposto, riprovo al giro dopo"); continue
        esito = avanzamento(p, azienda, L, t["id"], prova)
        if L.passo and not L.fase and not prova:
            sb("PATCH", f"/rest/v1/prospects?id=eq.{p['id']}", {"next_action": L.passo[:200], "next_action_date": L.quando})
        t0 = blocco_dopo_call(p, azienda, L, t["id"], prova)
        blocco = f"Le cose da fare sono in calendario {t0:%A %d/%m alle %H:%M}." if t0 else ("Nessuna cosa da fare rilevata." if not L.azioni else "")
        nota = f"Dalla call: {L.riassunto[:500]}" + (f"\n{esito}" if esito else "") + (f"\n{blocco}" if blocco else "")
        print(f"  {azienda}: {esito or 'fase invariata'} {blocco}")
        if prova:
            continue
        try:
            sb("POST", "/rest/v1/interactions", {"prospect_id": p["id"], "at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                                                 "kind": "nota", "body": nota[:1500], "ref": f"letta:{t['id']}"})
            fatti += 1
        except Exception as e:                                   # noqa: BLE001
            print(f"  nota non scritta: {str(e)[:80]}")
    print(f"transcript: {fatti} call lette, {len(nuovi)} transcript nuovi")


if __name__ == "__main__":
    main()
