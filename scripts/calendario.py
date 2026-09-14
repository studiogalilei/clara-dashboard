#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""IL CALENDARIO — Clara legge le call di Dre e le attacca ai prospect (7/9/2026).

PERCHE'
Dre: «così Clara ha il tracciato che hanno fatto i lead: Zafferano l'ho gia'
sentito ed e' quasi cliente». Le mail da sole non bastano: la call e' la tappa
che conta, e stava solo su Google Calendar.

DA DOVE LEGGE
1) L'indirizzo segreto iCal del calendario di Dre (CALENDARIO_ICS): Google
   lo da' in Impostazioni > calendario > «Indirizzo segreto in formato iCal».
   Nessuna API da attivare, nessun progetto Google Cloud: un URL, in un
   secret. Regge anni. Solo lettura, che e' quel che serve.
2) Oppure un JSON esportato (--da-json file): serve per il primo carico.

COSA FA
Per ogni evento con almeno un invitato esterno (o riconducibile a un
prospect dal titolo) scrive una riga in `agenda`: quando, titolo, tipo
(conoscitiva | tecnica | avvio | altro), link, e il prospect se lo
riconosce. Riconosce dall'email dell'invitato (email o email_alt), poi dal
dominio, poi dal nome dell'azienda nel titolo. La Scheda e la Storia leggono
`agenda` gia' da prima: da oggi non e' piu' vuota.

Non scrive mai due volte lo stesso evento: la chiave e' il link.

USO
  python3 scripts/calendario.py                  legge l'ICS e aggiorna
  python3 scripts/calendario.py --da-json f.json primo carico da un export
  python3 scripts/calendario.py --prova          mostra e non scrive
"""

import base64
import datetime
import json
import os
import re
import sys
import urllib.parse
import urllib.request
import zoneinfo

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from stanza import env, sb                                 # noqa: E402

ROMA = zoneinfo.ZoneInfo("Europe/Rome")
INDIETRO = 400      # giorni di storia da tenere (il tracciato)
AVANTI = 120        # giorni in avanti
CALENDARIO = "dramane@studiogalilei.com"

# chi e' di casa: non e' mai «il prospect»
NOSTRI = {"studiogalilei.com", "studiogalileiteam.com", "galileistudioworks.com"}
NOSTRE_EMAIL = {"carlo.dprogetti@gmail.com", "basestudiogalilei@gmail.com"}
# domini che non identificano un'azienda
GENERICI = {"gmail.com", "hotmail.com", "hotmail.it", "yahoo.com", "yahoo.it", "libero.it",
            "outlook.com", "outlook.it", "icloud.com", "live.it", "live.com", "pec.it",
            "tiscali.it", "virgilio.it", "alice.it", "group.calendar.google.com"}
PAROLE_VUOTE = {"studiogalilei", "studio", "galilei", "confronto", "call", "chiamata", "conoscitiva",
                "meeting", "srl", "srls", "spa", "snc", "sas", "italia", "italy", "group", "focus",
                "google", "ads", "progetto", "avvio", "tecnica", "tecnico", "proposta", "offerta",
                "analisi", "marketing", "sito", "dashboard", "avvocato", "follow", "workspace",
                "formazione", "controllo", "contratto", "inviare", "chiama", "chiamare", "project",
                "collaborazione", "feedback", "onboarding", "conferma", "prep", "appuntamento",
                "sede", "servizi", "presentazione", "brief", "dramane", "yigo", "carlo", "lorenzo",
                "giacomo", "email", "mail", "prima", "parte", "oggi", "torna", "check", "design",
                "consulting", "consulenza", "agency", "agenzia", "digital", "media", "web", "shop",
                "store", "casa", "italiana", "società", "societa", "company", "ecommerce", "ecomerce"}


# ---------- lettura ----------

def _srotola(testo):
    """Le righe ICS lunghe continuano con uno spazio: le riattacco."""
    righe = []
    for r in testo.replace("\r\n", "\n").split("\n"):
        if r.startswith((" ", "\t")) and righe:
            righe[-1] += r[1:]
        else:
            righe.append(r)
    return righe


def _quando(valore, parametri):
    """DTSTART in tutte le forme che Google usa → datetime UTC (o data intera)."""
    if "VALUE=DATE" in parametri or re.fullmatch(r"\d{8}", valore):
        d = datetime.datetime.strptime(valore[:8], "%Y%m%d")
        return d.replace(tzinfo=ROMA), True
    if valore.endswith("Z"):
        return datetime.datetime.strptime(valore, "%Y%m%dT%H%M%SZ").replace(tzinfo=datetime.timezone.utc), False
    m = re.search(r"TZID=([^;:]+)", parametri)
    tz = zoneinfo.ZoneInfo(m.group(1)) if m else ROMA
    return datetime.datetime.strptime(valore, "%Y%m%dT%H%M%S").replace(tzinfo=tz), False


def _link_google(uid):
    """Il link dell'evento su Google Calendar: base64 di «id calendario»."""
    ev = uid.split("@")[0]
    eid = base64.b64encode(f"{ev} {CALENDARIO}".encode()).decode().rstrip("=")
    return f"https://www.google.com/calendar/event?eid={eid}"


def _sciogli(s):
    return s.replace("\\n", "\n").replace("\\,", ",").replace("\\;", ";").replace("\\\\", "\\")


def da_ics(testo):
    eventi, corrente = [], None
    for riga in _srotola(testo):
        if riga == "BEGIN:VEVENT":
            corrente = {"invitati": [], "descrizione": "", "stato": "CONFIRMED"}
        elif riga == "END:VEVENT" and corrente is not None:
            if corrente.get("at") and corrente.get("uid"):
                corrente["link"] = corrente.get("link") or _link_google(corrente["uid"])
                eventi.append(corrente)
            corrente = None
        elif corrente is not None and ":" in riga:
            nome, valore = riga.split(":", 1)
            chiave, _, parametri = nome.partition(";")
            if chiave == "DTSTART":
                corrente["at"], corrente["giornata"] = _quando(valore, parametri)
            elif chiave == "DTEND":
                corrente["fine"], _ = _quando(valore, parametri)
            elif chiave == "SUMMARY":
                corrente["titolo"] = _sciogli(valore).strip()
            elif chiave == "DESCRIPTION":
                corrente["descrizione"] = _sciogli(valore)
            elif chiave == "UID":
                corrente["uid"] = valore.strip()
            elif chiave == "STATUS":
                corrente["stato"] = valore.strip()
            elif chiave == "ATTENDEE":
                m = re.search(r"mailto:([^\s]+)", valore, re.I)
                if m:
                    corrente["invitati"].append(m.group(1).lower())
            elif chiave == "X-GOOGLE-CONFERENCE":
                corrente["meet"] = valore.strip()
    return eventi


def da_json(percorso):
    """L'export del connettore Google Calendar (lista `events`)."""
    dati = json.load(open(percorso, encoding="utf-8"))
    eventi = []
    for e in dati.get("events", dati if isinstance(dati, list) else []):
        inizio = e.get("start", {})
        if inizio.get("dateTime"):
            at = datetime.datetime.fromisoformat(inizio["dateTime"]); giornata = False
        elif inizio.get("date"):
            at = datetime.datetime.strptime(inizio["date"][:10], "%Y-%m-%d").replace(tzinfo=ROMA); giornata = True
        else:
            continue
        fine = e.get("end", {}).get("dateTime")
        eventi.append({
            "uid": e.get("id", ""), "at": at, "giornata": giornata,
            "fine": datetime.datetime.fromisoformat(fine) if fine else None,
            "titolo": (e.get("summary") or "").strip(), "descrizione": e.get("description") or "",
            "invitati": [a.get("email", "").lower() for a in e.get("attendees", []) if a.get("email")],
            "link": e.get("htmlLink") or _link_google(e.get("id", "")),
            "meet": e.get("conferenceUrl"), "stato": (e.get("status") or "confirmed").upper(),
        })
    return eventi


# ---------- riconoscimento ----------

def _dominio(email):
    return email.split("@")[-1].lower() if "@" in email else ""


def esterni(invitati):
    return [i for i in invitati if _dominio(i) not in NOSTRI and i not in NOSTRE_EMAIL
            and not i.endswith("calendar.google.com")]


def _parole(testo):
    return {p for p in re.findall(r"[a-z0-9]{4,}", (testo or "").lower()) if p not in PAROLE_VUOTE}


def riconosci(evento, prospects):
    """Il prospect dell'evento: email, poi dominio, poi azienda nel titolo."""
    per_email, per_dominio = prospects["email"], prospects["dominio"]
    for i in esterni(evento["invitati"]):
        if i in per_email:
            return per_email[i], "email"
    for i in esterni(evento["invitati"]):
        d = _dominio(i)
        if d and d not in GENERICI and d in per_dominio:
            return per_dominio[d], "dominio"
    titolo = _parole(evento["titolo"])
    if titolo:
        # una parola basta solo se e' lunga, di UNA sola azienda e non e' un
        # nome di persona («klavzar» si, «diego» no). Altrimenti nel titolo ci
        # deve essere tutta l'azienda («bike tours» non e' «Buffalo Bike Tours»).
        for pid, parole in prospects["aziende"]:
            comuni = parole & titolo
            if not comuni:
                continue
            if any(len(p) >= 6 and prospects["conta"][p] == 1 and p not in prospects["nomi"] for p in comuni):
                return pid, "titolo"
            if len(comuni) >= 2 and comuni == parole:
                return pid, "titolo"
    return None, None


def tipo_di(titolo):
    t = (titolo or "").lower()
    if "avvio" in t or "kick" in t or "onboarding" in t:
        return "avvio"
    if any(k in t for k in ("tecnic", "proposta", "offerta", "analisi", "2'", "2º", "2°", "secondo")):
        return "tecnica"
    if any(k in t for k in ("conoscitiv", "confronto", "call", "chiamata", "meeting", "discovery")):
        return "conoscitiva"
    return "altro"


def carica_prospects():
    righe = sb("GET", "/rest/v1/prospects?select=id,name,company,email,email_alt&limit=10000") or []
    per_email, per_dominio, aziende = {}, {}, []
    for p in righe:
        mail = [p.get("email") or ""] + list(p.get("email_alt") or [])
        for m in mail:
            m = m.lower().strip()
            if m:
                per_email[m] = p["id"]
                d = _dominio(m)
                if d and d not in GENERICI:
                    per_dominio.setdefault(d, p["id"])
        parole = _parole(p.get("company") or "")
        if parole:
            aziende.append((p["id"], parole))
    nomi = {(p.get("name") or "").split(" ")[0].lower() for p in righe}
    conta = {}
    for _, parole in aziende:
        for w in parole:
            conta[w] = conta.get(w, 0) + 1
    return {"email": per_email, "dominio": per_dominio, "aziende": aziende, "conta": conta, "nomi": nomi}


# ---------- scrittura ----------

def eventi_correnti():
    """Gli eventi dalla fonte che c'e': l'ICS, o l'ultimo export salvato (CALENDARIO_JSON)."""
    url = env("CALENDARIO_ICS")
    if url:
        with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "clara-dashboard"}), timeout=60) as r:
            return da_ics(r.read().decode("utf-8", errors="replace")), "ics"
    percorso = env("CALENDARIO_JSON")
    if percorso and os.path.exists(percorso):
        return da_json(percorso), "export"
    return [], "niente"


# ── I CALENDARI DELLE PERSONE (14/9): chi e' entrato con Google ha lasciato il
# permesso di lettura sul suo calendario. Il manager vede quelli del suo pod
# (richiesta di Carlo), ognuno il suo. Dre resta sull'ICS (owner null).
def eventi_google(email):
    from google_api import g
    adesso = datetime.datetime.now(datetime.timezone.utc)
    p = urllib.parse.urlencode({"timeMin": (adesso - datetime.timedelta(days=7)).isoformat(), "timeMax": (adesso + datetime.timedelta(days=60)).isoformat(),
                                "singleEvents": "true", "orderBy": "startTime", "maxResults": 250})
    d = g("GET", f"https://www.googleapis.com/calendar/v3/calendars/primary/events?{p}", email=email) or {}
    eventi = []
    for it in d.get("items", []):
        inizio = it.get("start") or {}
        if inizio.get("dateTime"):
            at = datetime.datetime.fromisoformat(inizio["dateTime"].replace("Z", "+00:00"))
            giornata = False
        elif inizio.get("date"):
            at = datetime.datetime.fromisoformat(inizio["date"] + "T09:00:00+02:00")
            giornata = True
        else:
            continue
        eventi.append({"titolo": (it.get("summary") or "").strip(), "at": at, "giornata": giornata, "stato": (it.get("status") or "confirmed").upper(),
                       "invitati": [(a.get("email") or "").lower() for a in it.get("attendees", [])], "meet": it.get("hangoutLink"),
                       "link": it.get("htmlLink") or it.get("id"), "descrizione": it.get("description") or ""})
    return eventi


def calendari_persone(prova, prospects):
    persone = sb("GET", "/rest/v1/google_token?select=user_id,email") or []
    for u in persone:
        if u["email"] == "dramane@studiogalilei.com":
            continue                                   # il suo e' l'ICS dello Studio
        try:
            eventi = eventi_google(u["email"])
        except Exception as e:
            print(f"  calendario di {u['email']}: {str(e)[:120]}")
            continue
        esistenti = {r["link"]: r for r in (sb("GET", f"/rest/v1/agenda?select=id,link,at,titolo,prospect_id&owner=eq.{u['user_id']}&limit=3000") or []) if r.get("link")}
        nuovi = agg = 0
        for e in eventi:
            if not e["titolo"] or e["stato"] == "CANCELLED":
                continue
            pid, _ = riconosci(e, prospects)
            riga = {"at": e["at"].astimezone(datetime.timezone.utc).isoformat(), "titolo": e["titolo"][:200], "tipo": tipo_di(e["titolo"]),
                    "prospect_id": pid, "link": e.get("meet") or e["link"], "fonte": f"gcal:{u['email']}", "owner": u["user_id"]}
            vecchia = esistenti.get(riga["link"])
            if prova:
                print(f"  {u['email'][:12]:12} {e['at'].astimezone(ROMA):%d/%m %H:%M} {e['titolo'][:50]}")
                continue
            if vecchia:
                if vecchia["at"] != riga["at"] or vecchia["titolo"] != riga["titolo"]:
                    sb("PATCH", f"/rest/v1/agenda?id=eq.{vecchia['id']}", riga); agg += 1
            else:
                sb("POST", "/rest/v1/agenda", riga); nuovi += 1
        print(f"  calendario di {u['email']}: {nuovi} nuovi, {agg} aggiornati, {len(eventi)} letti")


def main():
    prova = "--prova" in sys.argv
    if "--da-json" in sys.argv:
        eventi = da_json(sys.argv[sys.argv.index("--da-json") + 1])
        fonte = "export"
    else:
        eventi, fonte = eventi_correnti()
        if fonte == "niente":
            print("manca CALENDARIO_ICS (l'indirizzo segreto iCal del calendario)")
            sys.exit(1)

    adesso = datetime.datetime.now(datetime.timezone.utc)
    da, a = adesso - datetime.timedelta(days=INDIETRO), adesso + datetime.timedelta(days=AVANTI)
    prospects = carica_prospects()
    nomi = {p["id"]: (p.get("company") or p.get("name") or "") for p in (sb("GET", "/rest/v1/prospects?select=id,name,company&limit=10000") or [])} if prova else {}
    esistenti = {r["link"]: r for r in (sb("GET", "/rest/v1/agenda?select=id,link,at,titolo,prospect_id&fonte=eq.gcal&limit=5000") or []) if r.get("link")}

    nuovi = aggiornati = saltati = 0
    for e in eventi:
        if not e.get("titolo") or e.get("stato") == "CANCELLED" or e.get("giornata"):
            continue
        if not (da <= e["at"] <= a):
            continue
        pid, come = riconosci(e, prospects)
        if not pid and not esterni(e["invitati"]):
            saltati += 1              # roba personale: non e' un impegno di lavoro con qualcuno
            continue
        riga = {"at": e["at"].astimezone(datetime.timezone.utc).isoformat(), "titolo": e["titolo"][:200],
                "tipo": tipo_di(e["titolo"]), "prospect_id": pid, "link": e.get("meet") or e["link"], "fonte": "gcal"}
        chiave = e.get("meet") or e["link"]
        vecchia = esistenti.get(chiave)
        if prova:
            print(f"  {e['at'].astimezone(ROMA):%d/%m %H:%M}  {riga['tipo']:12} {e['titolo'][:50]:50} {come or '-':8} {nomi.get(pid, '')[:30] if pid else ''}")
            continue
        if vecchia:
            cambiata = vecchia["at"] != riga["at"] or vecchia["titolo"] != riga["titolo"] or (pid and vecchia["prospect_id"] != pid)
            if cambiata:
                # il prospect scelto a mano nella Dashboard non si tocca
                if vecchia["prospect_id"] and vecchia["prospect_id"] != pid:
                    riga["prospect_id"] = vecchia["prospect_id"]
                sb("PATCH", f"/rest/v1/agenda?id=eq.{vecchia['id']}", riga)
                aggiornati += 1
        else:
            sb("POST", "/rest/v1/agenda", riga)
            nuovi += 1

    print(f"calendario ({fonte}): {nuovi} nuovi, {aggiornati} aggiornati, {saltati} personali saltati, {len(eventi)} letti")
    calendari_persone(prova, prospects)


if __name__ == "__main__":
    main()
