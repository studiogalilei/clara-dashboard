#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""IN CONVERSAZIONE — l'unica notifica sul telefono di Dre (20/10/2026).

PERCHE'
Dre, 20/10: «fino all'analisi fa tutto il sistema; quando uno risponde dopo l'analisi e' in
conversazione e passa a me». E: «se risponde e' in conversazione», anche un no. Il telefono
suona solo per questo: tutte le altre notifiche (si' da servire, prenotazioni, bozze pronte,
promemoria del foglio) sono state tolte, le mail restano come sono.

LA REGOLA
Un lead e' IN CONVERSAZIONE quando ha una risposta scritta da una PERSONA arrivata dopo
`analysis_sent_at`. Non contano: le risposte arrivate prima dell'analisi, le autorisposte e i
fuori ufficio (la regex collaudata del segnale, poi la lettura AI del segnale, dalla sua memoria:
la stessa risposta non si ripaga mai). Se l'AI non risponde si suona lo stesso: mai silenzio.

UNA NOTIFICA PER CONVERSAZIONE, NON PER MESSAGGIO
Lo stato sta in snella_numeri, chiave «conversazioni»: {pid: {"dal": iso, "notificata": bool, ...}}.
«dal» e' la prima risposta di persona dopo l'analisi. Si scrive «notificata: false» PRIMA di
suonare e «true» quando almeno un dispositivo l'ha presa: una conversazione con «false» e' una
notifica non arrivata (la legge il semaforo della scheda Clara) e si riprova al giro dopo, per
un giorno. Un lead che riscrive mentre la conversazione e' aperta non suona di nuovo.
Una conversazione cominciata prima della finestra (o, alla prima accensione, piu' di 2 ore fa)
si segna senza suonare: e' il passato, Dre lo sa.

DOVE GIRA
Ogni 5 minuti dentro il giro del segnale provvisorio (dopo le risposte, prima delle prenotazioni):
un guasto qui non ferma il resto. Da sola, per provarla:
  python3 scripts/conversazioni.py --prova              chi suonerebbe adesso (non scrive, non suona)
  python3 scripts/conversazioni.py --prova --dal 2026-10-19
                                   chi avrebbe suonato da quel giorno (Roma) a oggi, da zero
"""
import datetime
import os
import re
import sys
import urllib.parse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from stanza import sb, quando, _a_secco                         # noqa: E402
import segnale_provvisorio as S                                 # noqa: E402
from lettura import solo_suo                                    # noqa: E402

CHIAVE = "conversazioni"
FINESTRA = datetime.timedelta(hours=48)     # le risposte che si guardano a ogni giro
SEMINA = datetime.timedelta(hours=2)        # alla prima accensione suona solo quello piu' recente di cosi'
RIPROVA = datetime.timedelta(hours=24)      # una notifica non arrivata si riprova per un giorno
TIENI = datetime.timedelta(days=120)        # lo stato non cresce per sempre


def adesso():
    return datetime.datetime.now(datetime.timezone.utc)


def _z(t):
    return t.astimezone(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def azienda(p):
    return " ".join((p.get("company") or p.get("name") or "?").split())


def persona(p, r):
    """True se la risposta l'ha scritta una persona, False se e' un'autorisposta (o e' vuota),
    None se la lettura e' rimandata al giro dopo (il tetto delle letture pagate)."""
    corpo = r.get("body") or ""
    if S.automatica(corpo):
        return False
    testo = solo_suo(corpo, con_firma=True) or corpo
    if not testo.strip() or testo.lower().startswith("risposta ricevuta"):
        return False
    letto = S.leggi(azienda(p), testo)                  # la stessa chiave del segnale: dalla memoria
    if letto == S.RIMANDATA:
        return None
    if letto.get("fallita"):
        return True                                     # l'AI non ha letto: si suona, mai silenzio
    return not letto.get("autorisposta")


def apertura(p, risposte, e_persona=persona):
    """La prima risposta di persona dopo l'analisi (la riga di interactions), None se non c'e',
    S.RIMANDATA se una risposta piu' vecchia non e' ancora stata letta."""
    an = p.get("analysis_sent_at")
    if not an:
        return None
    an = quando(an)
    for r in sorted(risposte, key=lambda x: x.get("at") or ""):
        if not r.get("at") or quando(r["at"]) <= an:
            continue
        v = e_persona(p, r)
        if v is None:
            return S.RIMANDATA
        if v:
            return r
    return None


def _risposte_dopo(p):
    an = p.get("analysis_sent_at")
    if not an:
        return []
    return sb("GET", f"/rest/v1/interactions?select=id,prospect_id,at,body&kind=eq.email_in&prospect_id=eq.{p['id']}"
                     f"&at=gt.{urllib.parse.quote(_z(quando(an)))}&order=at.asc&limit=200") or []


def in_conversazione(pid):
    """Il lead ha una risposta di persona arrivata dopo l'analisi?"""
    p = (sb("GET", f"/rest/v1/prospects?select=id,company,name,analysis_sent_at&id=eq.{pid}") or [None])[0]
    if not p:
        return False
    r = apertura(p, _risposte_dopo(p))
    return bool(r) and r != S.RIMANDATA


# ── lo stato in snella_numeri ──────────────────────────────────────

def leggi_stato():
    """Lo stato, o None se la chiave non c'e' ancora (la prima accensione)."""
    r = sb("GET", f"/rest/v1/snella_numeri?select=dati&chiave=eq.{CHIAVE}") or []
    if not r:
        return None
    d = r[0].get("dati")
    return d if isinstance(d, dict) else {}


def scrivi_stato(stato):
    sb("POST", "/rest/v1/snella_numeri?on_conflict=chiave",
       [{"chiave": CHIAVE, "dati": stato, "aggiornato_il": _z(adesso())}],
       {"Prefer": "resolution=merge-duplicates,return=minimal"})


OGGETTO = re.compile(r"^\s*(r|re|i|rif|fw|fwd|tr)\s*:", re.I)


def frase(r):
    """L'inizio di quello che ha scritto, senza firma ne' l'oggetto in cima («R: Promemoria: ...»)."""
    righe = (solo_suo(r.get("body") or "") or "").split("\n")
    while righe and (not righe[0].strip() or OGGETTO.match(righe[0])):
        righe.pop(0)
    return " ".join(" ".join(righe).split())


def suona(pid, p, r):
    """La notifica: titolo con l'azienda, l'inizio di quello che ha scritto, tocco = la scheda."""
    return S.notifica(f"È entrato in conversazione: {azienda(p)}", frase(r)[:170] or "Ha risposto dopo l'analisi", pid)


# ── il giro ────────────────────────────────────────────────────────

def giro(prova=None, dal=None):
    """Chi e' entrato in conversazione e non ha ancora la sua notifica: la manda (una per lead).
    Torna la lista [(pid, azienda, dal, frase)] di chi suona (o suonerebbe, in prova).
    `dal` (solo in prova): da quando guardare, partendo da uno stato vuoto."""
    prova = _a_secco() if prova is None else prova
    ora = adesso()
    if dal is not None and not prova:
        raise SystemExit("--dal e' una prova sul passato: va con --prova")
    stato = {} if dal is not None else leggi_stato()
    prima_volta = stato is None
    stato = dict(stato or {})
    da = dal or ora - FINESTRA
    righe = [r for r in sb("GET", f"/rest/v1/interactions?select=id,prospect_id,at&kind=eq.email_in&prospect_id=not.is.null"
                                  f"&at=gte.{urllib.parse.quote(_z(da))}&order=at.asc&limit=3000") or []
             if r.get("at") and quando(r["at"]) >= da]
    nuovi = sorted({r["prospect_id"] for r in righe} - set(stato))
    schede = {}
    for i in range(0, len(nuovi), 80):
        for p in sb("GET", f"/rest/v1/prospects?select=id,company,name,analysis_sent_at&id=in.({','.join(nuovi[i:i + 80])})") or []:
            schede[p["id"]] = p
    ultima = {}
    for r in righe:
        ultima[r["prospect_id"]] = max(ultima.get(r["prospect_id"], ""), r["at"])
    suonano, cambiato = [], False
    for pid, p in schede.items():
        an = p.get("analysis_sent_at")
        if not an or quando(ultima[pid]) <= quando(an):
            continue                                    # nessuna risposta nuova dopo l'analisi
        r = apertura(p, _risposte_dopo(p))
        if not r or r == S.RIMANDATA:
            continue
        inizio = quando(r["at"])
        voce = {"dal": _z(inizio), "notificata": False}
        if inizio < da or (prima_volta and ora - inizio > SEMINA):
            stato[pid] = {**voce, "notificata": True, "silenziosa": True}   # il passato: si segna e basta
            cambiato = True
            continue
        detto = frase(r)[:120]
        print(f"  in conversazione: {azienda(p)} dal {inizio.astimezone(S.ROMA):%d/%m %H:%M} «{detto}»")
        suonano.append((pid, azienda(p), inizio, detto))
        if prova:
            continue
        stato[pid] = voce                               # prima si scrive «non notificata», poi si suona
        scrivi_stato(stato)
        if suona(pid, p, r):
            stato[pid] = {**voce, "notificata": True, "il": _z(adesso())}
        cambiato = True
    # le notifiche non arrivate si riprovano, per un giorno
    for pid, v in list(stato.items()):
        if prova or v.get("notificata") or pid in {s[0] for s in suonano}:
            continue
        if ora - quando(v["dal"]) > RIPROVA:
            continue
        p = (sb("GET", f"/rest/v1/prospects?select=id,company,name,analysis_sent_at&id=eq.{pid}") or [None])[0]
        r = apertura(p, _risposte_dopo(p)) if p else None
        if not r or r == S.RIMANDATA:
            continue
        if suona(pid, p, r):
            stato[pid] = {**v, "notificata": True, "il": _z(adesso())}
            cambiato = True
    vecchie = [pid for pid, v in stato.items() if ora - quando(v.get("dal") or _z(ora)) > TIENI]
    for pid in vecchie:
        stato.pop(pid)
    if not prova and (cambiato or prima_volta or vecchie):
        scrivi_stato(stato)
    print(f"conversazioni: {len(suonano)} {'suonerebbero' if prova else 'nuove'}, {len(stato)} in memoria")
    return suonano


def main():
    prova = _a_secco()
    dal = None
    if "--dal" in sys.argv:
        dal = datetime.datetime.fromisoformat(sys.argv[sys.argv.index("--dal") + 1]).replace(tzinfo=S.ROMA)
    S.GIRO.update(pagate=0, memoria_rotta=False, sonda=False, giorno_restano=None, tetto_giorno=False)
    giro(prova=prova, dal=dal)


if __name__ == "__main__":
    main()
