#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""IL LAMPO: la consegna in un giro solo (Dre, 1/10/2026).

Il 1/10, misurato dal vivo: la catena risposta → fit → analisi → bozza →
approvazione → invio impiegava da 1h15 a 3h30, non perche' i pezzi fossero
lenti (il fit sono 2-4 minuti, l'analisi 4-6) ma perche' OGNI pezzo aspettava
il giro successivo del direttore. Dre: «ci mettiamo tanto, rispondiamo piu'
veloce li'».

Questo script fa la catena intera per chi ha risposto DA POCO, in un colpo:
per ogni risposta fresca chiama gli stessi pezzi di sempre (googlefit --uno,
analisi_auto --uno, bozze --email) e poi un giro di prima_risposta e manda.
Niente logica nuova: solo la stessa sequenza senza le attese fra i giri. I
cancelli restano tutti dove sono (whitelist, analisi allegata, 5 al giorno,
finestra, Revisore del testo): il lampo accorcia il tempo, non le regole.

I pezzi grossi restano ai loro giri: il lampo tocca al massimo LAMPO_MAX
aziende per corsa, le piu' recenti, e salta chi ha gia' una proposta aperta.

USO:  python3 scripts/lampo.py [--prova]
      python3 scripts/lampo.py --email <email> [--prova]   la catena per un lead solo (la strada veloce, 21/10)
"""
import datetime
import os
import urllib.parse
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from stanza import sb, scritta_da_macchina, persona_dopo_analisi  # noqa: E402

PROVA = "--prova" in sys.argv
FRESCA_ORE = int(sys.argv[sys.argv.index("--ore") + 1]) if "--ore" in sys.argv else 6          # oltre, ci pensano i giri normali: il lampo e' per chi aspetta adesso
LAMPO_MAX = 4           # aziende per corsa: il giro resta corto, il direttore non si blocca
RADICE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _corri(nome, argomenti, minuti=8):
    """Un pezzo della catena, col suo limite di tempo: se sfora si va avanti (regola 4 del 28/9)."""
    try:
        r = subprocess.run([sys.executable, os.path.join(RADICE, "scripts", nome)] + argomenti,
                           capture_output=True, text=True, timeout=minuti * 60, cwd=RADICE)
        coda = (r.stdout or "").strip().splitlines()[-1:] or [""]
        print(f"  {nome} {' '.join(argomenti)[:40]:40} → {coda[0][:90]}")
        return r.returncode == 0
    except subprocess.TimeoutExpired:
        print(f"  {nome}: oltre {minuti} minuti, lo lascio al suo giro")
        return False


CAMPI = "id,email,company,name,classificazione,last_reply_at,analysis_pdf,analysis_sent_at,enriched"
FILTRO = ("&awaiting_us=eq.true&fuori=eq.false&stage=not.in.(cliente,perso,call_fissata,rinviato)"
          "&or=(classificazione.is.null,classificazione.not.in.(negativo,fuori_target,soppresso,nervoso))")


def di_persona(p):
    """UNA MACCHINA NON ASPETTA L'ANALISI (turno del 22/10). Il filtro qui sotto toglieva i no ma non le
    risposte automatiche: «Grazie per averci contattato, risponderò il prima possibile» entrava nella
    catena, si pagava l'analisi e nasceva una bozza di prima risposta (INT-01) per chi non aveva scritto
    niente; un fuori ufficio con la data di rientro diventava una domanda per Dre. Prima_risposta le
    fermava, ma restavano in Posta. Chi l'ha scritta lo dice la regola unica (stanza.scritta_da_macchina,
    lettore compreso): per un fuori ufficio riprende la sequenza di Smartlead, non il lampo.
    E DOPO L'ANALISI LA CONVERSAZIONE E' DI DRE (turno del 22/10, ore 15): chi risponde dopo aver
    ricevuto l'analisi resta «aspetta noi» finche' Dre non gli scrive, e il lampo lo riprendeva a ogni
    giro per sei ore (36 corse a vuoto su un lead solo). La catena del lampo finisce all'analisi: una
    conversazione la porta la notifica, non il lampo (stanza.persona_dopo_analisi, la regola unica)."""
    return not scritta_da_macchina(p) and not persona_dopo_analisi(p)


def fresche():
    da = urllib.parse.quote((datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(hours=FRESCA_ORE)).isoformat())
    righe = sb("GET", f"/rest/v1/prospects?select={CAMPI}{FILTRO}&last_reply_at=gte.{da}&order=last_reply_at.desc&limit=20") or []
    aperte = {x["prospect_id"] for x in (sb("GET", "/rest/v1/proposte?select=prospect_id&stato=in.(aperta,approvata,in_invio)&limit=1000") or [])}
    # GIA' GIUDICATA (turno del 27/10): una risposta vuota, con il verdetto delle bozze scritto dopo,
    # tornava a ogni giro per sei ore: bozze --email non guarda il verdetto. La regola e' quella del
    # giro delle bozze (bozze.letta_dopo_ultima): si riprende solo se riscrive.
    from bozze import letta_dopo_ultima
    clara = decisioni_di_clara([p["id"] for p in righe])
    righe = [p for p in righe if not chiusa_da_clara(p, clara.get(p["id"]))]
    return [p for p in righe if p["id"] not in aperte and not letta_dopo_ultima(p) and di_persona(p)][:LAMPO_MAX]


# Le mosse di Clara che non portano un'analisi: aspettare o chiudere.
SENZA_ANALISI = ("wait", "close")


def chiusa_da_clara(p, decisione):
    """Pura. GIA' DECISA DA CLARA (turno del 4/11): col Desk il vecchio giro delle bozze e' spento e il
    verdetto che letta_dopo_ultima cerca non lo scrive piu' nessuno. Una risposta vuota (il lead che rimanda
    la nostra mail «non la disturbo oltre») tornava nel lampo ogni 10 minuti per sei ore (34 corse, e a ogni
    corsa analisi_auto rileggeva il filo col secondo lettore). Se Clara ha gia' deciso su QUESTA risposta di
    aspettare o chiudere, l'analisi non serve: si riprende solo se il lead riscrive."""
    if not decisione:
        return False
    return decisione.get("mossa") in SENZA_ANALISI and \
        (decisione.get("risposta_il") or "")[:19] >= (p.get("last_reply_at") or "")[:19] != ""


def decisioni_di_clara(ids):
    """L'ultima decisione di Clara per ogni lead (prospect_id -> riga), letta in una volta."""
    if not ids:
        return {}
    try:
        righe = sb("GET", "/rest/v1/clara_decisioni?select=prospect_id,mossa,risposta_il&order=creato_il.desc"
                          f"&prospect_id=in.({','.join(ids)})&limit=200") or []
    except Exception:                                            # noqa: BLE001
        return {}                                                # nel dubbio il lampo fa il suo giro
    ultime = {}
    for r in righe:
        ultime.setdefault(r["prospect_id"], r)
    return ultime


def uno(email):
    """UN LEAD SOLO (la strada veloce, 21/10: scripts/risposta.py lo chiama appena entra un si' senza
    analisi). Gli stessi filtri di fresche(): aspetta noi, non e' chiuso, non ha una proposta aperta."""
    em = (email or "").strip().lower()
    righe = sb("GET", f"/rest/v1/prospects?select={CAMPI}{FILTRO}&email=eq.{urllib.parse.quote(em)}&limit=1") or []
    if not righe:
        print("lampo: questo lead non aspetta noi (o e' chiuso): niente da fare")
        return []
    p = righe[0]
    if not di_persona(p):
        print("lampo: risposta automatica o conversazione dopo l'analisi (e' di Dre): niente da fare")
        return []
    if chiusa_da_clara(p, decisioni_di_clara([p["id"]]).get(p["id"])):
        print("lampo: Clara ha gia' deciso di aspettare o chiudere su questa risposta: niente analisi")
        return []
    aperte = sb("GET", f"/rest/v1/proposte?select=id&prospect_id=eq.{p['id']}&stato=in.(aperta,approvata,in_invio)&limit=1") or []
    if aperte:
        print("lampo: ha gia' una proposta in corso: la porta avanti il suo giro")
        return []
    return [p]


def bozze_accese():
    """4/11: col Desk le risposte le decide Clara (clara_prova) e le approva Dre. Il lampo si ferma
    all'analisi; bozze, prima_risposta e il postino vecchio girano solo se «bozze» e' accesa in operazioni."""
    try:
        r = sb("GET", "/rest/v1/operazioni?select=attiva&chiave=eq.bozze") or []
        return bool(r and r[0].get("attiva"))
    except Exception:                                            # noqa: BLE001
        return False


def analisi_accesa():
    """12/11 (Dre: «lascia stare completamente l'analisi», outbound solo software): l'interruttore
    «analisi» spento valeva per il giro del direttore ma non per la strada veloce, che chiamava
    fit e analisi da sola a ogni si'. Ora l'interruttore vale anche qui."""
    try:
        r = sb("GET", "/rest/v1/operazioni?select=attiva&chiave=eq.analisi") or []
        return bool(r and r[0].get("attiva"))
    except Exception:                                            # noqa: BLE001
        return False


def catena(p, extra):
    """La catena di un lead: fit, analisi, bozza. Gli stessi pezzi di sempre, senza attese."""
    nome = (p.get("company") or p.get("name") or p["email"])[:40]
    gf = (p.get("enriched") or {}).get("google_fit") or {}
    print(f"  ─ {nome} (risposta delle {str(p['last_reply_at'])[11:16]})")
    if not analisi_accesa():
        print("    analisi spenta in operazioni: niente fit, niente analisi")
        if bozze_accese():
            _corri("bozze.py", ["--email", p["email"]] + extra)
        return
    if not gf.get("sito_letto"):
        _corri("googlefit.py", ["--uno", p["email"]] + extra)
    if not p.get("analysis_pdf"):
        _corri("analisi_auto.py", ["--email", p["email"]] + extra, minuti=12)
    if bozze_accese():
        _corri("bozze.py", ["--email", p["email"]] + extra)


def main():
    solo = sys.argv[sys.argv.index("--email") + 1] if "--email" in sys.argv else None
    care = uno(solo) if solo else fresche()
    extra = ["--prova"] if PROVA else []
    if not care:
        if solo:
            return
        # niente di fresco, ma gli approvati rimasti (1/10: UG col PDF arrivato dopo)
        # non devono aspettare il giro di qualcun altro
        if bozze_accese():
            print("lampo: nessuna risposta fresca; passo comunque il testimone a postino e approvazioni")
            _corri("prima_risposta.py", extra)
            _corri("manda.py", extra)
        return
    print(f"lampo: {len(care)} risposte fresche" + (" (prova)" if PROVA else ""))

    # IN PARALLELO (Dre, 2/10: «se scrivono piu' lead allo stesso tempo, li fa uno alla
    # volta o insieme? Dobbiamo accorciare»). Ogni lead ha la sua catena in un processo
    # suo: quattro insieme costano come uno. L'ordine dei pezzi dentro la catena resta.
    from concurrent.futures import ThreadPoolExecutor
    with ThreadPoolExecutor(max_workers=LAMPO_MAX) as pool:
        list(pool.map(lambda p: catena(p, extra), care))
    # i cancelli veri: approvazione (con tutti i freni) e postino, una volta per tutti (solo col vecchio automatismo acceso)
    if bozze_accese():
        _corri("prima_risposta.py", extra)
        _corri("manda.py", extra)


if __name__ == "__main__":
    main()
