#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""IN CONVERSAZIONE — l'unica notifica sul telefono di Dre (20/10/2026, rifatta il 21/10).

PERCHE'
Dre, 20/10: «fino all'analisi fa tutto il sistema; quando uno risponde dopo l'analisi e' in
conversazione e passa a me». E: «se risponde e' in conversazione», anche un no. Il telefono
suona solo per questo: tutte le altre notifiche (si' da servire, prenotazioni, bozze pronte,
promemoria del foglio) sono state tolte, le mail restano come sono.
Dre, 21/10: «chiunque risponda dopo l'analisi deve essere riportato, questo non puo' sbagliare,
e deve essere veloce».

LA REGOLA (stanza.tocca_a_dre, una sola per chi suona e per il semaforo)
Un lead e' IN CONVERSAZIONE quando ha una risposta scritta da una PERSONA arrivata dopo
`analysis_sent_at`. Non contano: le risposte arrivate prima dell'analisi, le autorisposte e i
fuori ufficio (la regex collaudata del segnale, poi la lettura AI del segnale, dalla sua memoria:
la stessa risposta non si ripaga mai). Se l'AI non risponde si suona lo stesso: mai silenzio.

LA NOTIFICA SUONA OGNI VOLTA CHE LA PALLA TORNA A DRE (21/10)
Il 20/10 suonava una volta per conversazione e poi taceva per 120 giorni: chi riscriveva dopo
la risposta di Dre restava muto (il 19/10, e le 7 voci «silenziose» del 20/10). Ora:
- c'e' una mail del lead (persona) piu' recente della nostra ultima mail (interactions
  email_out, cioe' Dre da Smartlead o l'analisi, e i follow-up) e piu' recente dell'ultima mail
  sua gia' notificata: suona;
- due mail sue di fila senza una nostra in mezzo: una sola notifica;
- un'autorisposta non suona; la stessa mail non suona due volte.
Lo stato sta in snella_numeri, chiave «conversazioni»: {pid: {"dal", "aperta_il", "notificata",
"il", "ultima_notificata", "nostra_dopo", ...}}. «dal» e' la prima mail di persona dopo l'analisi;
«ultima_notificata» l'ora della mail del lead notificata (si scrive PRIMA di suonare, con
«notificata: false»; «true» quando almeno un dispositivo l'ha presa: una voce con «false» e' una
notifica non arrivata, si riprova al giro dopo, per un giorno); «nostra_dopo» l'ora della nostra
risposta arrivata dopo quella mail (la palla e' tornata al lead). Le voci vecchie (solo «dal»,
anche le «silenziose» del 20/10) valgono come notificate: il passato non suona, la prossima mail
nuova dopo una nostra risposta si'.

DI NOTTE (22-7:30, come i guasti) non suona: lo stato non si tocca e alle 7:30 il giro la trova
e la suona. Una conversazione piu' vecchia di 2 ore alla prima accensione si segna senza suonare.

IL SI' CALDO (20/10 sera). Dre: «fino all'analisi fa tutto il sistema; quando tocca a me voglio la
notifica». Un si' che il lettore AI legge CALDO («mi mandi tutto e poi ci sentiamo», un numero
lasciato) e' gia' una conversazione di Dre, anche prima dell'analisi: l'analisi gliela manda lo
stesso il sistema (INT-01, col calendario, come a ogni si'), e in piu' il lead passa a Dre:
«Da chiamare» nell'app (snella_lead, da oggi, come dal foglio) e questa stessa notifica, subito.
MA (Dre, 20/10 sera) «Da chiamare» SOLO se ha lasciato un cellulare (la firma o la scheda, mai il
centralino del sito: segnale_provvisorio.cellulare_di); se no «Da rispondere» con Dre responsabile e
la prossima azione «Vuole sentirci ma non ha lasciato un cellulare: scrivigli» (passa_a_dre).
Vale solo per la lettura del lettore sulla sua ultima mail (stanza.lettore_di), con la classe
«positivo» (se Dre l'ha cambiata, vince lui). Se Dre ha gia' toccato il lead dopo la sua mail, la
sua decisione non si tocca. Un si' non caldo non suona: lo serve il sistema.

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
from stanza import sb, quando, _a_secco, contattabile, lettore_di, tocca_a_dre, mail_notificata, scritta_da_macchina  # noqa: E402
import segnale_provvisorio as S                                 # noqa: E402
from lettura import solo_suo                                    # noqa: E402
from guasti import di_notte                                     # noqa: E402

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
    None se la lettura e' rimandata al giro dopo (il tetto delle letture pagate).
    Notte del 22/10: se il lettore ha letto proprio questa mail decide lui (stanza.scritta_da_macchina,
    la stessa regola del semaforo e del foglio); il gpt-5 del segnale resta solo dove il lettore non c'e'."""
    v = scritta_da_macchina(p, r.get("at")) if r.get("at") else None
    if v is not None:
        return not v
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


def ultima_persona(p, risposte, soglia, e_persona=persona):
    """L'ultima risposta di PERSONA arrivata dopo `soglia` (la riga di interactions), dalla piu'
    recente: un'autorisposta in cima non nasconde la persona sotto. None se non c'e',
    S.RIMANDATA se una lettura e' rimandata al giro dopo. Sotto la soglia (l'analisi, la mail
    gia' notificata, la nostra ultima) non si legge niente: non puo' suonare comunque."""
    for r in sorted(risposte, key=lambda x: x.get("at") or "", reverse=True):
        if not r.get("at") or quando(r["at"]) <= soglia:
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


def nostre_ultime(pids):
    """La nostra ultima mail per lead: {pid: datetime}. Sono le interactions email_out (tutto il
    filo nostro su Smartlead, Dre compreso: le scrive il sync) e i follow-up. Si guarda indietro
    quanto lo stato (TIENI): una nostra risposta di 4 giorni fa conta anche se la finestra delle
    mail del lead e' di 48 ore."""
    out = {}
    pids = sorted(p for p in pids if p)
    da = urllib.parse.quote(_z(adesso() - TIENI))
    for i in range(0, len(pids), 80):
        for r in sb("GET", f"/rest/v1/interactions?select=prospect_id,at&kind=in.(email_out,followup)"
                           f"&prospect_id=in.({','.join(pids[i:i + 80])})&at=gte.{da}&order=at.desc&limit=5000") or []:
            if not r.get("at"):
                continue
            t = quando(r["at"])
            if r["prospect_id"] not in out or t > out[r["prospect_id"]]:
                out[r["prospect_id"]] = t
    return out


def in_conversazione(pid):
    """Il lead ha una risposta di persona arrivata dopo l'analisi?"""
    p = (sb("GET", f"/rest/v1/prospects?select=id,company,name,analysis_sent_at,last_reply_at,classificazione,lettore:enriched->lettore&id=eq.{pid}") or [None])[0]
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


def suona(pid, p, r, caldo=False):
    """La notifica: titolo con l'azienda, l'inizio di quello che ha scritto, tocco = la scheda.
    Per un si' caldo il testo lo dice: «Vuole sentirti»."""
    detto = frase(r)[:150]
    testo = (f"Vuole sentirti: «{detto}»" if detto else "Vuole sentirti") if caldo else (frase(r)[:170] or "Ha risposto dopo l'analisi")
    return S.notifica(f"È entrato in conversazione: {azienda(p)}", testo, pid)


# ── il si' caldo, prima dell'analisi ───────────────────────────────

def caldi_del_lettore(da, stato):
    """I lead che il lettore AI ha letto CALDI sulla loro ultima mail (nella finestra), con la classe
    «positivo», contattabili e non ancora in conversazione."""
    righe = sb("GET", "/rest/v1/prospects?select=id,company,name,analysis_sent_at,last_reply_at,classificazione,fuori,stage,"
                      "pipeline_stage,no_followup,lettore:enriched->lettore&enriched->lettore->>caldo=eq.true"
                      f"&last_reply_at=gte.{urllib.parse.quote(_z(da))}&limit=300") or []
    out = []
    for p in righe:
        if p["id"] in stato or p.get("classificazione") != "positivo":
            continue
        l = lettore_di(p)
        if not l or not l.get("caldo") or not contattabile(p):
            continue
        out.append(p)
    return out


def risposta_calda(p, dal):
    """La sua mail da `dal` in poi: la prima email_in da quell'ora (l'ora della risposta letta dal
    lettore, il «dal» dello stato, o la mail notificata da riprovare)."""
    if not dal:
        return None
    t = quando(dal if str(dal).endswith("Z") or "+" in str(dal) else str(dal) + "+00:00")
    righe = sb("GET", f"/rest/v1/interactions?select=id,prospect_id,at,body&kind=eq.email_in&prospect_id=eq.{p['id']}"
                      f"&at=gte.{urllib.parse.quote(_z(t))}&order=at.asc&limit=50") or []
    righe = [r for r in righe if r.get("at") and quando(r["at"]) >= t]
    return righe[0] if righe else None


def da_chiamare(pid, inizio, p=None):
    """Il si' caldo passa a Dre, con la stessa riga dell'orecchio (segnale_provvisorio.passa_a_dre):
    «Da chiamare» da oggi se ha lasciato un cellulare (firma o scheda, mai il sito: Dre, 20/10 sera),
    se no «Da rispondere» con Dre responsabile e la mossa che dice perche'. Torna lo stato scritto.
    Se Dre ha gia' toccato il lead dopo la sua mail, vince lui: torna None."""
    r = (sb("GET", f"/rest/v1/snella_lead?select=stato,aggiornato_il&prospect_id=eq.{pid}") or [None])[0]
    if r and r.get("aggiornato_il") and quando(r["aggiornato_il"]) > inizio:
        return None
    riga = S.passa_a_dre(pid, S.cellulare_di(p or {"id": pid}), adesso())
    sb("POST", "/rest/v1/snella_lead?on_conflict=prospect_id", [riga], {"Prefer": "resolution=merge-duplicates,return=minimal"})
    return riga["stato"]


# ── il giro ────────────────────────────────────────────────────────

def _voce_nuova(v, mail, ora, caldo=False):
    """La voce dello stato prima di suonare: «non notificata» per quella mail. «dal» e «aperta_il»
    restano quelli della prima volta; «silenziosa» e «caldo» della volta prima cadono."""
    voce = {k: x for k, x in (v or {}).items() if k not in ("silenziosa", "caldo", "il")}
    voce.update({"dal": voce.get("dal") or _z(mail), "aperta_il": voce.get("aperta_il") or _z(ora),
                 "ultima_notificata": _z(mail), "nostra_dopo": None, "notificata": False})
    if caldo:
        voce["caldo"] = True
    return voce


def giro(prova=None, dal=None):
    """Chi ha la palla da Dre e non ha ancora la sua notifica: la manda (una per mail del lead).
    Torna la lista [(pid, azienda, mail, frase)] di chi suona (o suonerebbe, in prova; di notte:
    chi suonera' alle 7:30). `dal` (solo in prova): da quando guardare, partendo da uno stato vuoto."""
    prova = _a_secco() if prova is None else prova
    ora = adesso()
    if dal is not None and not prova:
        raise SystemExit("--dal e' una prova sul passato: va con --prova")
    stato = {} if dal is not None else leggi_stato()
    prima_volta = stato is None
    stato = dict(stato or {})
    notte = di_notte(ora)
    da = dal or ora - FINESTRA
    righe = [r for r in sb("GET", f"/rest/v1/interactions?select=id,prospect_id,at&kind=eq.email_in&prospect_id=not.is.null"
                                  f"&at=gte.{urllib.parse.quote(_z(da))}&order=at.asc&limit=3000") or []
             if r.get("at") and quando(r["at"]) >= da]
    ultima = {}
    for r in righe:
        ultima[r["prospect_id"]] = max(ultima.get(r["prospect_id"], ""), r["at"])
    pids = sorted(ultima)
    schede = {}
    for i in range(0, len(pids), 80):
        for p in sb("GET", f"/rest/v1/prospects?select=id,company,name,analysis_sent_at,last_reply_at,classificazione,lettore:enriched->lettore&id=in.({','.join(pids[i:i + 80])})") or []:
            schede[p["id"]] = p
    nostre = nostre_ultime(pid for pid, p in schede.items() if p.get("analysis_sent_at"))
    suonano, cambiato = [], False
    for pid, p in schede.items():
        an = p.get("analysis_sent_at")
        if not an:
            continue
        an = quando(an)
        v = stato.get(pid) if isinstance(stato.get(pid), dict) else None
        gia = mail_notificata(v)
        nostra = nostre.get(pid)
        # la nostra risposta dopo la mail notificata: la palla e' tornata al lead, si segna
        if v is not None and gia and nostra and nostra > gia and (not v.get("nostra_dopo") or quando(v["nostra_dopo"]) < nostra):
            stato[pid] = v = {**v, "nostra_dopo": _z(nostra)}
            cambiato = True
        if not tocca_a_dre(v, quando(ultima[pid]), nostra, an):
            continue                                    # nemmeno l'ultima mail (persona o no) fa tornare la palla
        soglia = max([an] + [t for t in (gia, nostra) if t])
        r = ultima_persona(p, _risposte_dopo(p), soglia)
        if not r or r == S.RIMANDATA:
            continue
        mail = quando(r["at"])
        if not tocca_a_dre(v, mail, nostra, an):
            continue
        if prima_volta and ora - mail > SEMINA:
            stato[pid] = {**_voce_nuova(v, mail, ora), "notificata": True, "silenziosa": True}   # il passato: si segna e basta
            cambiato = True
            continue
        detto = frase(r)[:120]
        print(f"  in conversazione: {azienda(p)} dal {mail.astimezone(S.ROMA):%d/%m %H:%M} «{detto}»"
              + (" (di notte: suona alle 7:30)" if notte else ""))
        suonano.append((pid, azienda(p), mail, detto))
        if prova or notte:
            continue
        voce = _voce_nuova(v, mail, ora)
        stato[pid] = voce                               # prima si scrive «non notificata», poi si suona
        scrivi_stato(stato)
        if suona(pid, p, r):
            stato[pid] = {**voce, "notificata": True, "il": _z(adesso())}
        cambiato = True
    # il si' caldo (20/10 sera): e' di Dre anche prima dell'analisi
    for p in caldi_del_lettore(da, stato):
        pid = p["id"]
        r = risposta_calda(p, (p.get("lettore") or {}).get("risposta_il"))
        if not r:
            continue
        mail = quando(r["at"])
        if prima_volta and ora - mail > SEMINA:
            stato[pid] = {**_voce_nuova(None, mail, ora, caldo=True), "notificata": True, "silenziosa": True}
            cambiato = True
            continue
        detto = frase(r)[:120]
        print(f"  si' caldo, passa a Dre: {azienda(p)} dal {mail.astimezone(S.ROMA):%d/%m %H:%M} «{detto}»"
              + (" (di notte: suona alle 7:30)" if notte else ""))
        suonano.append((pid, azienda(p), mail, detto))
        if prova or notte:
            continue
        scritto = da_chiamare(pid, mail, p)
        if scritto:
            print(f"    «{scritto}» nell'app, da oggi" + ("" if scritto == "Da chiamare" else " (nessun cellulare: gli scrive Dre)"))
        voce = _voce_nuova(None, mail, ora, caldo=True)
        stato[pid] = voce
        scrivi_stato(stato)
        if suona(pid, p, r, caldo=True):
            stato[pid] = {**voce, "notificata": True, "il": _z(adesso())}
        cambiato = True
    # le notifiche non arrivate si riprovano, per un giorno (non di notte)
    for pid, v in list(stato.items()):
        if prova or notte or not isinstance(v, dict) or v.get("notificata") or pid in {s[0] for s in suonano}:
            continue
        mail = mail_notificata(v)
        if not mail or ora - mail > RIPROVA:
            continue
        p = (sb("GET", f"/rest/v1/prospects?select=id,company,name,analysis_sent_at,last_reply_at,classificazione,lettore:enriched->lettore&id=eq.{pid}") or [None])[0]
        r = risposta_calda(p, _z(mail)) if p else None
        if not r:
            continue
        if suona(pid, p, r, caldo=bool(v.get("caldo"))):
            stato[pid] = {**v, "notificata": True, "il": _z(adesso())}
            cambiato = True
    vecchie = [pid for pid, v in stato.items() if not isinstance(v, dict) or ora - (mail_notificata(v) or ora) > TIENI]
    for pid in vecchie:
        stato.pop(pid)
    if not prova and (cambiato or prima_volta or vecchie):
        scrivi_stato(stato)
    print(f"conversazioni: {len(suonano)} {'suonerebbero' if prova else 'aspettano le 7:30' if notte else 'nuove'}, {len(stato)} in memoria")
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
