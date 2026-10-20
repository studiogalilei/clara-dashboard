#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""I DUE LINK E IL «PROSSIMO» DEL FOGLIO (20/10/2026, «io più il sistema»).

Accanto a ogni azienda nel foglio della pipeline: la SCHEDA nel Workspace, il FILO su
Smartlead (la conversazione del lead nella Master Inbox) e, se il sistema ha in piano un
messaggio per quel lead, quando («gio 22/10»). Sta qui e non in foglio.py perche' il foglio
per regola non nomina Smartlead ne' le proposte (invariante «nessuna mail parte dal foglio»):
questo modulo LEGGE e basta, non scrive niente da nessuna parte.

IL LINK DEL FILO (verificato il 20/10 sul codice della Master Inbox e sull'API):
la Master Inbox legge `?leadMap=<id>` e apre direttamente quel filo; l'id e' il
`campaign_lead_map_id` del lead nella sua campagna (lo stesso che l'API della Master Inbox
chiama `email_lead_map_id`). Nel database abbiamo campaign_id e lead_id, non quell'id: si
chiede una volta a Smartlead (GET /leads/?email=) e si ricorda nello stato del foglio.
Finche' non c'e', il link apre la Master Inbox filtrata sulla campagna con la mail del lead
nella ricerca (`?filterCampaignId=<campagna>&filterLeadInput=<mail>`).
"""
import datetime
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request
import zoneinfo

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from stanza import sb_tutte, env                             # noqa: E402

ROMA = zoneinfo.ZoneInfo("Europe/Rome")
INBOX = "https://app.smartlead.ai/app/master-inbox"
API = "https://server.smartlead.ai/api/v1"
GIORNI = ("lun", "mar", "mer", "gio", "ven", "sab", "dom")
MAPPE_PER_GIRO = 40              # le domande a Smartlead in un giro: le altre al giro dopo (si ricordano)
ORA_INVIO = 9                    # un messaggio «per giovedi'» parte dalla mattina


def link_scheda(pid):
    """La scheda del lead nel Workspace (la stessa strada della notifica)."""
    import segnale_provvisorio as SP
    return SP.link_snella(pid)


def link_filo(p, mappa=None):
    """La conversazione del lead su Smartlead, o None se il lead non viene da una campagna
    (aggiunto a mano: niente campagna, niente filo)."""
    p = p or {}
    if mappa:
        return f"{INBOX}?leadMap={int(mappa)}"
    if p.get("campaign_id") and p.get("lead_id"):
        q = {"filterCampaignId": int(p["campaign_id"])}
        if p.get("email"):
            q["filterLeadInput"] = p["email"]
        return f"{INBOX}?{urllib.parse.urlencode(q)}"
    return None


def _chiave_sl():
    k = env("SMARTLEAD_API_KEY")
    if k:
        return k.strip().strip("\"'")
    p = os.path.expanduser("~/.hermes/config.yaml")           # sul Mac di Dre sta in Hermes (come sync_v2)
    if os.path.exists(p):
        for riga in open(p, encoding="utf-8"):
            m = re.match(r"\s*SMARTLEAD_API_KEY:\s*(\S+)", riga)
            if m:
                return m.group(1).strip().strip("\"'")
    return None


def mappa_di(p, chiave):
    """Il campaign_lead_map_id del lead nella SUA campagna (solo lettura)."""
    url = f"{API}/leads/?email={urllib.parse.quote(p['email'])}&api_key={chiave}"
    with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "odyn-foglio"}), timeout=20) as r:
        d = json.loads(r.read() or b"{}")
    for c in (d or {}).get("lead_campaign_data") or []:
        if int(c.get("campaign_id") or 0) == int(p["campaign_id"]) and c.get("campaign_lead_map_id"):
            return int(c["campaign_lead_map_id"])
    return None


def completa_mappe(ps, pids, mappe, tetto=MAPPE_PER_GIRO):
    """Chiede a Smartlead gli id che mancano (al massimo `tetto` per giro) e li mette in `mappe`
    ({pid: id, o 0 se Smartlead non lo conosce}). Un errore non ferma il foglio."""
    chiave = _chiave_sl()
    if not chiave:
        return 0
    fatti = 0
    for pid in pids:
        p = ps.get(pid) or {}
        if pid in mappe or not (p.get("campaign_id") and p.get("lead_id") and p.get("email")):
            continue
        if fatti >= tetto:
            break
        try:
            mappe[pid] = mappa_di(p, chiave) or 0
        except Exception as e:                                   # noqa: BLE001
            print(f"  (filo non trovato su Smartlead, riprovo al giro dopo: {str(e)[:80]})")
            break
        fatti += 1
        time.sleep(0.25)                                         # Smartlead: 10 domande ogni 2 secondi
    return fatti


# ── il prossimo messaggio ─────────────────────────────────────────────

def leggi_piano():
    """Quello che il sistema ha in piano: le bozze pronte (aperte, approvate, in partenza) e il
    calendario dei follow-up (followup.py --calendario). {"proposte": {pid: [..]}, "calendario": {pid: riga}}"""
    proposte = {}
    for x in sb_tutte("/rest/v1/proposte?select=id,prospect_id,tipo,stato,titolo,at,azione"
                      "&tipo=eq.risposta&stato=in.(aperta,approvata,in_invio)"):
        if x.get("prospect_id"):
            proposte.setdefault(x["prospect_id"], []).append(x)
    calendario = {r["prospect_id"]: r for r in sb_tutte("/rest/v1/seguiti_calendario?select=prospect_id,gruppo,il",
                                                         chiave="prospect_id")}
    return {"proposte": proposte, "calendario": calendario}


def _tipo(gruppo):
    g = (gruppo or "").upper()
    if "FOLLOW" in g or "RICONTATTO" in g or "RINVIO" in g:
        return "follow-up"
    if "PROMEMORIA" in g:
        return "promemoria"
    return "risposta"


def _mattina(giorno):
    return datetime.datetime(giorno.year, giorno.month, giorno.day, ORA_INVIO, tzinfo=ROMA)


def prossimo_messaggio(pid, dati, ora=None):
    """(quando, tipo, testo) del prossimo messaggio che il sistema manda a quel lead, o None.
    Prima una bozza gia' scritta (il testo esatto; il giorno scelto da Dre se c'e', se no adesso),
    poi il calendario dei follow-up (il testo si scrive quel giorno leggendo il filo: qui vuoto)."""
    ora = ora or datetime.datetime.now(datetime.timezone.utc)
    oggi = ora.astimezone(ROMA).date()
    bozze = []
    for x in (dati.get("proposte") or {}).get(pid) or []:
        if x.get("tipo") != "risposta" or x.get("stato") not in ("aperta", "approvata", "in_invio"):
            continue
        if str(x.get("titolo") or "").startswith("Da guardare tu"):
            continue                                              # non e' un messaggio pronto: e' una domanda
        az = x.get("azione") or {}
        if not az.get("bozza"):
            continue
        gruppo = (az.get("lettura") or {}).get("gruppo") or az.get("template") or az.get("intento")
        # una bozza aperta parte da sola solo se e' un follow-up scritto dal codice (i seguiti); le
        # altre aspettano una persona: non sono «in piano»
        if x["stato"] == "aperta" and not (az.get("testo_dal_codice") and _tipo(gruppo) == "follow-up"):
            continue
        parte = str(az.get("parte_il") or "")[:10]
        giorno = datetime.date.fromisoformat(parte) if re.fullmatch(r"\d{4}-\d{2}-\d{2}", parte) else oggi
        t = _mattina(giorno) if giorno > oggi else ora
        bozze.append((t, _tipo(gruppo), az["bozza"]))
    if bozze:
        return min(bozze, key=lambda b: b[0])
    r = (dati.get("calendario") or {}).get(pid)
    if r and r.get("il"):
        giorno = max(datetime.date.fromisoformat(str(r["il"])[:10]), oggi)
        return _mattina(giorno), _tipo(r.get("gruppo")), ""
    return None


def giorno_breve(t):
    """«gio 22/10»"""
    r = t.astimezone(ROMA)
    return f"{GIORNI[r.weekday()]} {r:%d/%m}"


def prossimo_breve(pids, dati, ora=None):
    """Il prossimo messaggio dell'azienda (il piu' vicino fra i suoi contatti) in breve, o ''."""
    tutti = [m for m in (prossimo_messaggio(x, dati, ora) for x in pids) if m]
    return giorno_breve(min(tutti, key=lambda m: m[0])[0]) if tutti else ""


__all__ = ["link_scheda", "link_filo", "prossimo_messaggio", "prossimo_breve", "leggi_piano", "completa_mappe"]
