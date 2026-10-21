#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""IL FUMO DEL MATTINO (notte del 22/10/2026).

Dre, 22/10: «arriva alla radice». Una radice dei guai di ottobre: le prove passavano col finto e
cadevano col vero. La Master Inbox chiesta con limit 50 (Smartlead ne accetta 20) e' stata rotta
per ore con tutte le prove verdi, perche' le prove non chiamavano mai Smartlead; giornata.py e'
partita in cloud prima che il suo file arrivasse; i crediti OpenAI finiti il 16/10 non li ha visti
nessuno per ore.

Ogni mattina alle 7:45 (operazione «fumo»), prima che Dre si svegli:
  1. chiama DAL VIVO, in sola lettura e con i parametri veri degli script, ogni servizio esterno
     che il sistema usa: Supabase, Smartlead (campagne, export, storia di un filo, Master Inbox),
     Gmail, Calendar e Sheets di Dre, Anthropic e OpenAI (una domanda da pochi token), SearchAPI;
  2. guarda ogni operazione accesa: il suo file c'e' e si compila.
Chi cade va nel semaforo della scheda Clara (stanza.guasto «fumo:<cosa>») e alle 7:30 il telefono
puo' gia' suonare; chi torna in piedi esce da solo (stanza.guarito). guasti.py usa la stessa prova
(prova(fornitore)) per togliere un «crediti finiti» solo quando il servizio risponde davvero.

Non scrive niente nei servizi esterni: niente mail, niente campagne, niente celle.

USO
  python3 scripts/fumo.py           il giro vero (scrive i guasti)
  python3 scripts/fumo.py --prova   a video, senza scrivere i guasti
"""
import datetime
import os
import re
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from stanza import sb, env, guasto, guarito, _a_secco                  # noqa: E402

RADICE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DRE = "dramane@studiogalilei.com"


# ── i servizi, uno per uno: ognuno alza se non va ──────────────────────

def supabase():
    sb("GET", "/rest/v1/operazioni?select=chiave&limit=1")
    return "risponde"


def smartlead():
    """Le chiamate che fa il sync, con i suoi parametri: campagne, export di una attiva, la storia
    di un filo vero, la Master Inbox (limit e corpo di sync_v2, non una copia)."""
    import sync_v2 as S
    camps = [c for c in (S.sl_get("/campaigns") or []) if (c.get("status") or "").upper() == "ACTIVE"]
    if not camps:
        raise RuntimeError("nessuna campagna attiva vista")
    righe = S.sl_export(camps[0]["id"])
    p = (sb("GET", "/rest/v1/prospects?select=campaign_id,lead_id&campaign_id=not.is.null&lead_id=not.is.null"
                   "&last_reply_at=not.is.null&order=last_reply_at.desc&limit=1") or [{}])[0]
    storia = S.sl_get(f"/campaigns/{p['campaign_id']}/leads/{p['lead_id']}/message-history") if p else {}
    dal = (datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(hours=S.FRESCHE_ORE * 4)).isoformat()
    fresche = S.risposte_fresche(dal, segna=False, alza=True)
    return (f"{len(camps)} campagne attive, export di una: {len(righe)} lead, storia di un filo: "
            f"{len((storia or {}).get('history') or [])} messaggi, Master Inbox: {len(fresche)} risposte")


def _google(url):
    from google_api import g
    return g("GET", url, email=DRE)


def gmail():
    d = _google("https://gmail.googleapis.com/gmail/v1/users/me/profile")
    return f"casella di Dre: {d.get('messagesTotal')} mail"


def calendar():
    d = _google("https://www.googleapis.com/calendar/v3/calendars/primary/events?maxResults=1&singleEvents=true"
                f"&timeMin={datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')}")
    return f"calendario di Dre: {len(d.get('items') or [])} evento letto"


def sheets():
    r = sb("GET", "/rest/v1/snella_numeri?select=dati&chiave=eq.foglio") or []
    sid = ((r[0].get("dati") or {}) if r else {}).get("foglio_id")
    if not sid:
        raise RuntimeError("non so quale sia il foglio (snella_numeri «foglio» senza foglio_id)")
    d = _google(f"https://sheets.googleapis.com/v4/spreadsheets/{sid}?fields=sheets.properties.title")
    return "foglio: " + ", ".join(s["properties"]["title"] for s in d.get("sheets") or [])


def anthropic():
    import lettore
    schema = {"type": "object", "additionalProperties": False, "required": ["ok"], "properties": {"ok": {"type": "boolean"}}}
    uscita, costo = lettore.chiedi_anthropic("fumo", "Rispondi ok=true.", "prova", schema, registra="fumo")
    if not isinstance(uscita, dict) or "ok" not in uscita:
        raise RuntimeError(f"risposta strana: {str(uscita)[:80]}")
    return f"il modello del lettore risponde ({costo:.4f} $)"


def openai():
    import cervello
    testo = cervello._chiedi_openai("Rispondi solo con la parola: ok", cervello.MODELLO_OPENAI, fornitore="openai", tetto=300, sforzo="low")
    return f"{cervello.MODELLO_OPENAI} risponde ({len(testo)} caratteri)"


def searchapi():
    import crediti
    s = crediti.searchapi()
    if s["saldo"] <= 0:
        raise RuntimeError(f"crediti SearchAPI finiti ({int(s['saldo'])}/{int(s['totale'])})")
    return f"{int(s['saldo'])}/{int(s['totale'])} ricerche"


SERVIZI = {"Supabase": supabase, "Smartlead": smartlead, "Gmail": gmail, "Calendar": calendar, "Sheets": sheets,
           "Anthropic": anthropic, "OpenAI": openai, "SearchAPI": searchapi}
# il nome che stanza.FORNITORI da' a un servizio -> le prove che lo dicono vivo
DI_FORNITORE = {"Google": ("Gmail", "Calendar", "Sheets")}


def prova(fornitore):
    """True se il servizio (nome di stanza.FORNITORI) risponde adesso; None se non so provarlo."""
    nomi = DI_FORNITORE.get(fornitore) or ((fornitore,) if fornitore in SERVIZI else ())
    if not nomi:
        return None
    try:
        for n in nomi:
            SERVIZI[n]()
        return True
    except Exception as e:                                       # noqa: BLE001
        print(f"  {fornitore} ancora giu': {str(e)[:160]}")
        return False


# ── le operazioni accese: il file c'e' e si compila ────────────────────

def operazioni():
    """[(chiave, nome, problema o None)] per ogni operazione accesa con un comando."""
    import direttore
    out = []
    for op in sb("GET", "/rest/v1/operazioni?select=chiave,nome,comando,attiva&attiva=eq.true") or []:
        if not op.get("comando"):
            continue                                              # parte da un workflow suo (backup, risposta)
        f = direttore.file_del_comando(op["comando"])
        if not f:
            out.append((op["chiave"], op.get("nome"), f"comando che non so leggere: {op['comando'][:60]}"))
            continue
        percorso = os.path.join(RADICE, f)
        if not os.path.exists(percorso):
            out.append((op["chiave"], op.get("nome"), f"manca il file {f}"))
            continue
        try:
            if f.endswith(".py"):
                compile(open(percorso, encoding="utf-8").read(), f, "exec")
            out.append((op["chiave"], op.get("nome"), None))
        except SyntaxError as e:
            out.append((op["chiave"], op.get("nome"), f"non si compila: riga {e.lineno}, {e.msg}"))
    return out


def main():
    prova_a_secco = _a_secco()
    print(f"FUMO {'(prova) ' if prova_a_secco else ''}{datetime.datetime.now(datetime.timezone.utc):%Y-%m-%d %H:%M} UTC")
    caduti = 0
    for nome, f in SERVIZI.items():
        inizio = time.time()
        try:
            esito = f()
            print(f"  ok     {nome:10} {esito} ({time.time() - inizio:.1f}s)")
            guarito(f"fumo:{nome}")
        except Exception as e:                                   # noqa: BLE001
            caduti += 1
            testo = re.sub(r"api_key=[^&\s]+", "api_key=…", str(e))[:200]
            print(f"  CADUTO {nome:10} {testo}")
            guasto(f"fumo:{nome}", f"{nome} non risponde come il sistema se lo aspetta: {testo}",
                   sta_facendo="La prova del mattino lo ha visto dal vivo. Riprovo domattina; se resta, dillo ad Achille.")
    for chiave, nome, problema in operazioni():
        if problema:
            caduti += 1
            print(f"  CADUTA {chiave:18} {problema}")
            guasto(f"fumo:op:{chiave}", f"{nome or chiave}: {problema}",
                   sta_facendo="Il direttore non la lancia finché non è a posto. Dillo ad Achille.")
        else:
            guarito(f"fumo:op:{chiave}")
    print(f"fumo: {caduti} cadut{'o' if caduti == 1 else 'i'}")


if __name__ == "__main__":
    main()
