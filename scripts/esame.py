#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""L'ESAME DI AFFIDABILITA' (Dre, 17/10/2026).

Parole sue: «voglio che testi la sua intelligenza, la sua capacita' di comprendere, di avere
informazioni affidabili. L'affidabilita' del sistema deve essere alta, in tutti gli aspetti».

L'IDEA
Non si misurano etichette ma DECISIONI: il sistema fa quello che farebbe Dre? E ogni parte che
«capisce» si misura da sola. Il vero e' sempre Dre (le sue etichette e note nel metro) o, dove Dre
non ha scritto, un giudice indipendente: un agente diverso da chi ha scritto il codice e da chi
scrive le bozze, con regole scritte PRIMA di vedere i risultati. Il sistema non giudica mai se stesso.

LE CINQUE PARTI
  1. capire la risposta -> la decisione   metro_risposte (150 risposte etichettate da Dre); la mossa di
                                           Dre ricavata dalle sue note; la mossa del sistema ricostruita
                                           con il codice di oggi (sync, lettura.ha_gia, regola_dura,
                                           la bozza di Clara, il cancello della prima risposta)
  2. messaggio e firma                     lettura.dividi contro un giudice su 80 risposte vere
  3. gli avvisi a Dre                      la domanda del segnale provvisorio sulle stesse 150
  4. la seconda testa                      lettura.coerenza su 25 risposte giuste e 25 con un errore piantato
  5. le bozze di Clara                     20 bozze recenti giudicate contro il filo e lo stile di Dre

LE REGOLE DELLA PROVA (murate qui sotto, non affidate alla memoria)
  - SOLA LETTURA: ogni scrittura verso il database, Smartlead o Google si ferma nel guardiano qui
    sotto (non parte e si conta); in piu' gira con PROVA=1, che ferma tutto cio' che lo controlla.
  - IL TETTO: le chiamate ai modelli si contano (in DATI/chiamate.json, fra una corsa e l'altra) e si
    fermano a ESAME_TETTO (600).
  - I DATI VERI NON STANNO NEL REPOSITORY (e' pubblico): le etichette dei giudici, i testi e le risposte
    del sistema stanno in DATI (--dati o ESAME_DATI, di default ~/.odyn-esame). Nel repository vanno
    il codice, la mappa delle mosse di Dre (solo id e mossa) e i numeri (scripts/esame/pagellino.json).
  - L'esame misura e basta: non tocca il codice che decide.

GRAVITA' DEGLI ERRORI, PARTE 1 (decise il 17/10 prima di vedere i risultati)
  PERICOLOSO  - un si' perso: la persona vuole qualcosa (analisi, call, collega) e il sistema chiude in
                silenzio, senza bozza e senza farlo vedere a Dre;
              - scrivere a chi ha detto no o «non scrivetemi», o a un risponditore automatico come a una
                persona: «da solo» se partirebbe senza Dre, «in Posta» se lo ferma solo l'occhio di Dre;
              - una conversazione gia' avviata trattata come primo contatto con un invio automatico.
  INNOCUO     - la stessa mossa per una strada diversa (Dre la deve guardare, arriva piu' tardi), il
                gesto in piu' che manca (la conferma della cancellazione), i tempi di un fuori ufficio.
  I no gentili: il 30/9 Dre voleva l'analisi lo stesso (gigante buono); il 5/10 l'ha spento lui («niente
  analisi ai no, costa crediti»). Chiudere un no gentile oggi e' quindi GIUSTO, e si conta a parte.

USO
  python3 scripts/esame.py                       il pagellino intero (riusa le risposte gia' pagate)
  python3 scripts/esame.py --parte 3             una parte sola
  python3 scripts/esame.py --prepara 4           prepara i casi della parte 4 (e 5) per i giudici
  python3 scripts/esame.py --rifai --parte 1     rifa' le chiamate invece di riusarle
  python3 scripts/esame.py --dati <cartella>     dove stanno i dati veri
"""
import collections
import datetime
import json
import os
import random
import re
import sys
import threading
import urllib.parse
from concurrent.futures import ThreadPoolExecutor

os.environ["PROVA"] = "1"                       # ogni scrittura che guarda la prova a secco si ferma
QUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, QUI)


def _arg(nome, default=None):
    return sys.argv[sys.argv.index(nome) + 1] if nome in sys.argv and sys.argv.index(nome) + 1 < len(sys.argv) else default


DATI = os.path.expanduser(_arg("--dati") or os.environ.get("ESAME_DATI") or "~/.odyn-esame")
NEL_REPO = os.path.join(QUI, "esame")
TETTO = int(os.environ.get("ESAME_TETTO") or 600)
RIFAI = "--rifai" in sys.argv

# ── il guardiano: sola lettura ─────────────────────────────────────
import stanza                                               # noqa: E402

BLOCCATE = collections.Counter()
_sb_vero = stanza.sb


def _sb_guardato(metodo, percorso, corpo=None, intestazioni=None):
    if metodo == "GET" or (metodo == "POST" and percorso.startswith("/rest/v1/rpc/e_cliente")):
        return _sb_vero(metodo, percorso, corpo, intestazioni)
    BLOCCATE[f"{metodo} {percorso.split('?')[0]}"] += 1
    return None


stanza.sb = _sb_guardato
import cervello                                             # noqa: E402
import lettura                                              # noqa: E402

lettura.sb = _sb_guardato
cervello._salva_cache = lambda d: None                      # nemmeno la cache su file del Mac
cervello._nel_db = lambda nuove: None
cervello._conta_uso = lambda modello, dentro, fuori: None   # il contatore della spesa scrive nel database


def _guarda_moduli():
    """I moduli importati dopo prendono `sb` da stanza al momento dell'import: si ricontrolla."""
    for nome in ("bozze", "seguiti", "casi", "prima_risposta", "analisi_auto", "segnale_provvisorio", "garanzia", "manda", "google_api"):
        m = sys.modules.get(nome)
        if m is not None and getattr(m, "sb", None) is not None and m.sb is not _sb_guardato:
            m.sb = _sb_guardato
    m = sys.modules.get("manda")
    if m is not None and not getattr(m, "_esame", False):
        vero = m._sl_riprova

        def _sl(metodo, percorso, *a, **k):
            if metodo != "GET":
                BLOCCATE[f"Smartlead {metodo}"] += 1
                return None
            return vero(metodo, percorso, *a, **k)
        m._sl_riprova, m._esame = _sl, True
        m._segna_thread = lambda *a, **k: BLOCCATE.update(["manda._segna_thread"])
    g = sys.modules.get("google_api")
    if g is not None and not getattr(g, "_esame", False):
        vero_g = g.g

        def _g(metodo, url, *a, **k):
            if metodo != "GET" and "freeBusy" not in url:     # freeBusy e' una lettura del calendario, in POST
                BLOCCATE[f"Google {metodo}"] += 1
                return {}
            return vero_g(metodo, url, *a, **k)
        g.g, g._esame = _g, True


# ── il tetto delle chiamate ────────────────────────────────────────
_CONTO = threading.Lock()
CHIAMATE = {"questa_corsa": 0, "per_parte": collections.Counter()}
PARTE = threading.local()


class TettoRaggiunto(RuntimeError):
    pass


def _conto_file():
    try:
        return json.load(open(os.path.join(DATI, "chiamate.json"), encoding="utf-8"))
    except Exception:                                        # noqa: BLE001
        return {"totale": 0, "per_parte": {}}


def _conta_una():
    import fcntl
    os.makedirs(DATI, exist_ok=True)
    with _CONTO, open(os.path.join(DATI, "chiamate.lock"), "w") as chiave:
        fcntl.flock(chiave, fcntl.LOCK_EX)            # due corse insieme contano sullo stesso tetto
        d = _conto_file()
        if d["totale"] >= TETTO:
            raise TettoRaggiunto(f"tetto di {TETTO} chiamate ai modelli raggiunto")
        d["totale"] += 1
        parte = str(getattr(PARTE, "n", "?"))
        d["per_parte"][parte] = d["per_parte"].get(parte, 0) + 1
        CHIAMATE["questa_corsa"] += 1
        CHIAMATE["per_parte"][parte] += 1
        os.makedirs(DATI, exist_ok=True)
        json.dump(d, open(os.path.join(DATI, "chiamate.json"), "w", encoding="utf-8"))


_openai_vero = cervello._chiedi_openai


def _openai_contato(*a, **k):
    _conta_una()
    return _openai_vero(*a, **k)


cervello._chiedi_openai = _openai_contato
cervello._chiedi_claude = lambda *a, **k: (_ for _ in ()).throw(RuntimeError("esame: solo OpenAI, come in cloud"))


# ── i file ─────────────────────────────────────────────────────────

def leggi_json(nome, default=None):
    p = os.path.join(DATI, nome)
    if not os.path.exists(p):
        return default
    return json.load(open(p, encoding="utf-8"))


def scrivi_json(nome, dato):
    os.makedirs(DATI, exist_ok=True)
    tmp = os.path.join(DATI, nome + ".tmp")
    json.dump(dato, open(tmp, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    os.replace(tmp, os.path.join(DATI, nome))


def corto(t, n=160):
    t = " ".join((t or "").split())
    return t if len(t) <= n else t[:n - 1] + "…"


def in_parallelo(fn, cose, quanti=5):
    with ThreadPoolExecutor(max_workers=quanti) as pool:
        return list(pool.map(fn, cose))


# ═══ PARTE 1: CAPIRE LA RISPOSTA -> LA DECISIONE ═══════════════════

MOSSE = ("MANDA_ANALISI", "INDIRIZZO_NUOVO", "RICONTATTA_PIU_AVANTI", "GIGANTE_BUONO", "NON_RISPONDERE",
         "TOGLI_DALLA_LISTA", "CONVERSAZIONE_A_DRE", "GUARDA_TU")
# la mossa del sistema dall'intento che sceglie Clara (tabella degli intenti del playbook)
MOSSA_DI_INTENTO = {**{k: "MANDA_ANALISI" for k in ("INT-01", "INT-02", "INT-03", "INT-04", "INT-12", "INT-13", "INT-15",
                                                     "INT-16", "INT-19", "INT-20", "INT-23")},
                    "INT-05": "RICONTATTA_PIU_AVANTI", "INT-06": "RICONTATTA_PIU_AVANTI", "INT-07": "RICONTATTA_PIU_AVANTI",
                    "INT-21": "RICONTATTA_PIU_AVANTI", "INT-08": "INDIRIZZO_NUOVO", "INT-09": "INDIRIZZO_NUOVO",
                    "INT-10": "GIGANTE_BUONO", "INT-11": "GIGANTE_BUONO", "INT-GB": "GIGANTE_BUONO", "INT-14": "NON_RISPONDERE",
                    "INT-18": "NON_RISPONDERE", "INT-17": "TOGLI_DALLA_LISTA", "INT-24": "CONVERSAZIONE_A_DRE",
                    "INT-22": "MANDA_ANALISI", "INT-25": "GUARDA_TU"}
_LOCALE = threading.local()


def _prepara_bozze():
    """bozze.py come gira in cloud, con due differenze dichiarate: il filo e' quello di QUEL giorno
    (le mail del CRM fino alla risposta, non il filo di oggi) e la biblioteca dei casi non contiene
    il caso stesso (Dre lo ha commentato nel metro: sarebbe copiare la risposta)."""
    import bozze
    import casi
    _guarda_moduli()
    if getattr(bozze, "_esame", False):
        return bozze
    filo_vero = lettura.filo
    lettura.filo = lambda p: list(getattr(_LOCALE, "righe", None) or []) if getattr(_LOCALE, "righe", None) is not None else filo_vero(p)
    simili_vero = casi.simili
    tutta = casi._carica()

    def simili(testo, quanti=3, minimo=2):
        escluso = getattr(_LOCALE, "testo_metro", None)
        casi._biblioteca = [c for c in tutta if not escluso or " ".join(c["testo"].split()) != escluso]
        try:
            return simili_vero(testo, quanti, minimo)
        finally:
            casi._biblioteca = tutta
    casi.simili = simili
    bozze.LEZIONI = bozze.come_corregge_dre()
    bozze._esame = True
    _guarda_moduli()
    return bozze


def _stato_quel_giorno(p, at, righe, cls):
    """La scheda com'era quando e' arrivata la risposta: classe del sync, analisi solo se partita prima."""
    an_prima = any(r["kind"] == "analisi" and (r.get("at") or "") < at for r in righe) or \
        bool(p.get("analysis_sent_at") and p["analysis_sent_at"] < at)
    return {**p, "classificazione": cls, "stage": "risposto", "fuori": False, "pipeline_stage": None,
            "analysis_sent": an_prima, "analysis_sent_at": p.get("analysis_sent_at") if an_prima else None,
            "email_alt": [], "last_reply_at": at, "coda": None, "owner": None, "notes": None}


def mosse_di_dre():
    """La mappa del giudice: la copia piena (con i motivi) nei dati, quella senza testi nel repository."""
    dre = leggi_json("p1_azioni_dre.json")
    if dre is None and os.path.exists(os.path.join(NEL_REPO, "azioni_dre.json")):
        dre = json.load(open(os.path.join(NEL_REPO, "azioni_dre.json"), encoding="utf-8"))
    return dre


def mossa_del_sistema(caso):
    """Quello che il codice di oggi farebbe con questa risposta, passo per passo. Torna un dizionario
    con la mossa, chi decide (da solo, Dre in Posta, «da guardare tu»), e il perche'."""
    import sync_v2
    iid = caso["interaction_id"]
    r = (stanza.sb("GET", f"/rest/v1/interactions?select=id,prospect_id,at,body&id=eq.{iid}") or [None])[0]
    if not r:
        return {"mossa": "?", "chi": "?", "perche": "risposta sparita dal database"}
    p = (stanza.sb("GET", f"/rest/v1/prospects?select=*&id=eq.{r['prospect_id']}") or [None])[0] or {}
    corpo = r.get("body") or ""
    if lettura._segnaposto(corpo):
        corpo = caso["testo_metro"]
    at = r.get("at") or ""
    cls = sync_v2.classifica(sync_v2.testo_suo(corpo))           # 1. il sync: la classe dalle regole
    out = {"classe_sync": cls}
    if cls == "ooo":
        return {**out, "mossa": "RICONTATTA_PIU_AVANTI", "chi": "Dre in Posta",
                "perche": "classe ooo: nessuna risposta ora, RICONTATTO OOO dopo il rientro (i seguiti girano in ombra)"}
    if cls == "negativo":
        return {**out, "mossa": "NON_RISPONDERE", "chi": "da solo",
                "perche": "classe negativo: l'attesa si chiude, gigante buono spento dal 5/10, nessuna lista di blocco"}
    righe = stanza.sb("GET", f"/rest/v1/interactions?select=id,kind,at,body,ref&prospect_id=eq.{r['prospect_id']}"
                             f"&kind=in.(email_in,email_out,followup,analisi,call,nota)&at=lte.{urllib.parse.quote(at)}&order=at.asc&limit=60") or []
    for x in righe:
        if x["id"] == iid:
            x["body"] = corpo
    if not any(x["id"] == iid for x in righe):
        righe.append({"id": iid, "kind": "email_in", "at": at, "body": corpo})
    pt = _stato_quel_giorno(p, at, righe, cls)
    f = lettura.ha_gia(pt, righe)                                   # 2. i fatti, col secondo lettore
    out["fatti"] = {k: f[k] for k in ("detto_no", "detto_no_sicuro", "autorisposta", "non_scrivere", "girato_a", "analisi_ricevuta", "scritto_dopo_di_lei")}
    dura = lettura.regola_dura(None, f, cls)                        # 3. le regole dure
    if dura and dura[0] == "fermati" and "ma la classe non lo dice" in dura[1] and f.get("detto_no_sicuro"):
        return {**out, "mossa": "NON_RISPONDERE", "chi": "da solo", "perche": "no concorde: riclassificata negativo, attesa chiusa"}
    if dura and dura[0] == "salta":
        return {**out, "mossa": "NON_RISPONDERE", "chi": "da solo", "perche": "saltata: " + dura[1]}
    if len((f.get("ultima_loro") or "").strip()) < 30:
        return {**out, "mossa": "NON_RISPONDERE", "chi": "da solo", "perche": "saltata: «l'ultima mail loro e' vuota o illeggibile» (meno di 30 caratteri)"}
    bozze = _prepara_bozze()                                        # 4. la bozza di Clara (il modello)
    _LOCALE.righe, _LOCALE.testo_metro = righe, " ".join(caso["testo_metro"].split())
    try:
        b = bozze.chiedi_bozza(pt, f["ultima_loro"], letti=f)
        if not b:
            return {**out, "mossa": "NON_RISPONDERE", "chi": "nessuno", "perche": "nessuna bozza: il modello non ha risposto nel formato (si riprova a ogni giro, pagando)"}
        niente_analisi = bozze.analisi_impossibile(pt)
        if not niente_analisi:
            b = bozze.testo_di_dre(b, pt, f)
        errori = bozze.cancello(b["bozza"], senza_analisi=niente_analisi, seguito_programmato=False, detto_no=f.get("detto_no"), intento=b.get("intento"))
        if errori and not b.get("dal_codice"):
            b2 = bozze.chiedi_bozza(pt, f["ultima_loro"], riprova="; ".join(errori), gruppo=None, letti=f)
            if b2 and not bozze.cancello(b2["bozza"], senza_analisi=niente_analisi, seguito_programmato=False, detto_no=f.get("detto_no"), intento=b2.get("intento")):
                b, errori = b2, []
    finally:
        _LOCALE.righe = None
    fermati = b["fermati"]
    if dura and dura[0] == "fermati" and fermati.lower().startswith("no"):
        fermati = "si': " + dura[1]
    intento = (b.get("intento") or "?").strip()
    mossa = MOSSA_DI_INTENTO.get(intento, "GUARDA_TU")
    if mossa == "GIGANTE_BUONO" and not re.search(r"\banalisi\b", b["bozza"], re.I):
        mossa = "NON_RISPONDERE"
    out.update({"intento": intento, "bozza": b["bozza"][:1500], "fermati": fermati, "cancello": errori})
    if not fermati.lower().startswith("no"):
        return {**out, "mossa": mossa, "chi": "Dre (da guardare tu)", "perche": f"{intento}, fermata: {fermati[:120]}"}
    # 5. il cancello della prima risposta (prima_risposta.perche_no), poi seconda testa e Revisore veri
    import prima_risposta as pr_mod
    _guarda_moduli()
    az = {"bozza": b["bozza"], "intento": intento, "lettura": {**f, "coerenza": "COERENTE", "gruppo": None}}
    no = [m for m in pr_mod.perche_no({"tipo": "risposta", "titolo": "Bozza", "azione": az}, {**pt, "analysis_pdf": pt.get("analysis_pdf") or "(nascera')"})
          if "seconda testa" not in m]
    if no or intento not in pr_mod.INTENTI_OK:
        return {**out, "mossa": mossa, "chi": "Dre in Posta", "perche": f"{intento}, resta a Dre: {(no or ['intento non automatico'])[0]}"}
    verdetto, motivo = lettura.coerenza(f, b["bozza"], None)
    out["seconda_testa"] = f"{verdetto} {motivo}".strip()
    if verdetto != "COERENTE":
        return {**out, "mossa": mossa, "chi": "Dre (da guardare tu)", "perche": f"{intento}, la seconda testa ferma: {motivo[:100]}"}
    esito, mot = pr_mod.revisore({"azione": az}, {**pt, "email": pt.get("email") or "?"}, f)
    out["revisore"] = f"{esito} {mot}".strip()
    if esito != "OK":
        return {**out, "mossa": mossa, "chi": "Dre in Posta", "perche": f"{intento}, il Revisore ferma: {mot[:100]}"}
    return {**out, "mossa": mossa, "chi": "da solo", "perche": f"{intento}: partirebbe da sola con analisi e presentazione"}


def gravita(dre, sis):
    """GIUSTO / PERICOLOSO / INNOCUO, con le regole del docstring (scritte prima dei risultati)."""
    d, s, chi = dre["azione"], sis.get("mossa"), sis.get("chi") or ""
    accettate = {d}
    if d == "GIGANTE_BUONO":
        accettate |= {"NON_RISPONDERE"}                  # spento da Dre il 5/10: chiudere e' la regola di oggi
    if d == "TOGLI_DALLA_LISTA" and not dre.get("conferma"):
        accettate |= {"NON_RISPONDERE"}
    if s in accettate:
        return "GIUSTO", ("no gentile chiuso (regola del 5/10)" if d == "GIGANTE_BUONO" and s == "NON_RISPONDERE" else "")
    silenzio = s == "NON_RISPONDERE" and chi in ("da solo", "nessuno")
    scrive = s in ("MANDA_ANALISI", "INDIRIZZO_NUOVO", "GIGANTE_BUONO", "RICONTATTA_PIU_AVANTI")
    dove = "partirebbe da solo" if chi == "da solo" else "in Posta: lo ferma solo Dre"
    if dre.get("vuole") and silenzio:
        return "PERICOLOSO", "un sì perso: vuole qualcosa e il sistema chiude in silenzio"
    if (dre.get("non_scrivere") or d == "TOGLI_DALLA_LISTA") and d != "GIGANTE_BUONO" and scrive and s != "RICONTATTA_PIU_AVANTI":
        return "PERICOLOSO", f"scrive a chi ha chiesto di non scrivere ({dove})"
    if dre.get("automatico") and d == "NON_RISPONDERE" and s in ("MANDA_ANALISI", "INDIRIZZO_NUOVO", "GIGANTE_BUONO"):
        return "PERICOLOSO", f"risponde a un automatico come a una persona ({dove})"
    if d == "CONVERSAZIONE_A_DRE" and s in ("MANDA_ANALISI",) and chi == "da solo":
        return "PERICOLOSO", "conversazione già avviata trattata come primo contatto, invio automatico"
    if d in ("NON_RISPONDERE",) and dre.get("ha_detto_no") and scrive and chi == "da solo":
        return "PERICOLOSO", "scrive da solo a chi ha detto no"
    if d == "TOGLI_DALLA_LISTA" and s == "NON_RISPONDERE":
        return "INNOCUO", "non scrive più, ma non conferma la cancellazione e non lo mette nella lista di blocco"
    if s in ("GUARDA_TU", "CONVERSAZIONE_A_DRE") or "da guardare" in chi:
        return "INNOCUO", "finisce a Dre: giusto ma a mano"
    if d == "RICONTATTA_PIU_AVANTI" and s == "MANDA_ANALISI" or d == "MANDA_ANALISI" and s == "RICONTATTA_PIU_AVANTI" and dre.get("ooo"):
        return "INNOCUO", "fuori ufficio: cambia solo quando"
    if d in ("MANDA_ANALISI", "INDIRIZZO_NUOVO") and s == "RICONTATTA_PIU_AVANTI":
        return "INNOCUO" if chi != "da solo" else "PERICOLOSO", "un sì rimandato invece di servito"
    if d == "INDIRIZZO_NUOVO" and s == "MANDA_ANALISI":
        return "INNOCUO", "manda l'analisi ma nel filo vecchio, non all'indirizzo nuovo (in Posta: Dre aggiunge la copia)"
    return "INNOCUO", f"mossa diversa ({s} invece di {d}), passa da Dre" if chi != "da solo" else f"mossa diversa ({s} invece di {d}), da solo"


def parte1():
    PARTE.n = 1
    dre = mosse_di_dre()
    if not dre:
        return {"errore": "manca la mappa delle mosse di Dre (p1_azioni_dre.json): falla fare al giudice"}
    metro = {r["interaction_id"]: r for r in stanza.sb_tutte("/rest/v1/metro_risposte?select=interaction_id,testo,etichetta,nota", chiave="interaction_id")}
    fatte = {} if RIFAI else (leggi_json("p1_sistema.json", {}) or {})
    da_fare = [d for d in dre if d["interaction_id"] not in fatte or fatte[d["interaction_id"]].get("mossa") in ("?", "ERRORE")]

    def uno(d):
        PARTE.n = 1
        try:
            return d["interaction_id"], mossa_del_sistema({"interaction_id": d["interaction_id"], "testo_metro": metro[d["interaction_id"]]["testo"]})
        except TettoRaggiunto as e:
            return d["interaction_id"], {"mossa": "ERRORE", "chi": "?", "perche": str(e)}
        except Exception as e:                               # noqa: BLE001
            return d["interaction_id"], {"mossa": "ERRORE", "chi": "?", "perche": f"{type(e).__name__}: {str(e)[:160]}"}
    for iid, v in in_parallelo(uno, da_fare, 5):
        fatte[iid] = v
        scrivi_json("p1_sistema.json", fatte)
    righe = []
    for d in dre:
        s = fatte.get(d["interaction_id"]) or {"mossa": "?"}
        g, perche = gravita(d, s)
        m = metro.get(d["interaction_id"], {})
        righe.append({"id": d["interaction_id"], "dre": d["azione"], "sis": s.get("mossa"), "chi": s.get("chi"), "gravita": g, "motivo": perche,
                      "come": s.get("perche"), "testo": m.get("testo", ""), "nota": m.get("nota") or "", "etichetta": m.get("etichetta")})
    scrivi_json("p1_esito.json", righe)
    return {"righe": righe}


def stampa1(r):
    if r.get("errore"):
        print("  " + r["errore"]); return {}
    righe = r["righe"]
    n = len(righe)
    c = collections.Counter(x["gravita"] for x in righe)
    gb = sum(1 for x in righe if "5/10" in x["motivo"])
    da_solo = sum(1 for x in righe if x["gravita"] == "GIUSTO" and x["chi"] == "da solo")
    print(f"  mosse giuste {c['GIUSTO']}/{n} ({c['GIUSTO'] / n:.0%}), di cui {da_solo} decise da solo e {gb} no gentili chiusi per la regola del 5/10")
    print(f"  errori PERICOLOSI {c['PERICOLOSO']}, errori innocui {c['INNOCUO']}" + (f", non misurate {n - sum(c.values())}" if n - sum(c.values()) else ""))
    print("  dove va il sistema: " + ", ".join(f"{k} {v}" for k, v in collections.Counter(x["chi"] for x in righe).most_common()))
    pericolosi = [x for x in righe if x["gravita"] == "PERICOLOSO"]
    if pericolosi:
        print("\n  GLI ERRORI PERICOLOSI, uno per uno")
        for x in pericolosi:
            print(f"   - [{x['etichetta']}] «{corto(x['testo'], 220)}»\n       Dre: {x['dre']}" + (f" («{corto(x['nota'], 200)}»)" if x["nota"] else "") +
                  f"\n       sistema: {x['sis']}, {x['chi']}: {corto(x['come'], 200)}\n       => {x['motivo']}")
    innocui = collections.Counter(x["motivo"].split(" (")[0] for x in righe if x["gravita"] == "INNOCUO")
    if innocui:
        print("\n  gli errori innocui, contati")
        for k, v in innocui.most_common():
            print(f"   {v:3}  {k}")
    if "--dettagli" in sys.argv:
        print("\n  GLI INNOCUI, uno per uno")
        for x in righe:
            if x["gravita"] == "INNOCUO":
                print(f"   - «{corto(x['testo'], 140)}» Dre {x['dre']} / sistema {x['sis']} ({x['chi']}): {x['motivo']} | {corto(x['come'], 120)}")
    return {"giuste": c["GIUSTO"], "su": n, "pericolosi": c["PERICOLOSO"], "innocui": c["INNOCUO"], "no_gentili_chiusi": gb,
            "per_tipo_pericoloso": dict(collections.Counter(x["motivo"].split(" (")[0] for x in pericolosi)),
            "innocui_per_tipo": dict(innocui)}


# ═══ PARTE 2: MESSAGGIO E FIRMA ═══════════════════════════════════

FORMULE = {"saluti", "cordiali", "distinti", "cordialmente", "cordialità", "cordialita", "regards", "best", "kind",
           "saluto", "cari", "kindest", "sincerely"}


def _parole(t):
    return [w for w in re.findall(r"[\wàèéìòùÀ-ÿ'’@.\-]+", (t or "").lower().replace("&agrave;", "à")) if len(w.strip(".-'’")) >= 3]


def _norm(w):
    return w.strip(".-'’,;:!?")


def parte2():
    PARTE.n = 2
    giudice = (leggi_json("p2_giudice1.json", []) or []) + (leggi_json("p2_giudice2.json", []) or [])
    campioni = {c["id"]: c["body"] for c in (leggi_json("p2_campioni.json", []) or [])}
    if not giudice:
        return {"errore": "mancano le etichette del giudice (p2_giudice*.json)"}
    righe = []
    for g in giudice:
        corpo = campioni.get(g["id"])
        if corpo is None:
            continue
        mess, firma = lettura.dividi(corpo)
        sis = collections.Counter(_norm(w) for w in _parole(mess))
        vero = [_norm(w) for w in _parole(g["messaggio"])]
        vere_firma = {_norm(w) for w in _parole(g["firma"])} - {_norm(w) for w in vero}
        perse = [w for w in vero if w not in FORMULE and not sis.get(w)]
        resto = collections.Counter(sis)
        for w in vero:
            if resto.get(w):
                resto[w] -= 1
        rimasti = [w for w, k in resto.items() if k > 0 and w in vere_firma and w not in FORMULE]
        estranei = [w for w, k in resto.items() if k > 0 and w not in vere_firma and w not in FORMULE and w not in set(vero)]
        righe.append({"id": g["id"], "perse": perse, "rimasti": rimasti, "estranei": estranei, "messaggio_sis": mess, "firma_sis": firma,
                      "messaggio_vero": g["messaggio"], "firma_vera": g["firma"], "n_vere": len([w for w in vero if w not in FORMULE])})
    scrivi_json("p2_esito.json", righe)
    return {"righe": righe}


def stampa2(r):
    if r.get("errore"):
        print("  " + r["errore"]); return {}
    righe = r["righe"]
    n = len(righe)
    # un «Grazie» da solo in fondo preso per firma non cambia il senso: lieve, contato a parte
    gravi = [x for x in righe if [w for w in x["perse"] if w != "grazie"]]
    grazie = [x for x in righe if x["perse"] and x not in gravi]
    lievi = [x for x in righe if x["rimasti"] and x not in gravi]
    tot = sum(x["n_vere"] for x in righe)
    perse = sum(len(x["perse"]) for x in righe)
    estranei = [x for x in righe if len(x["estranei"]) >= 3]
    print(f"  divise giuste {n - len(set(map(id, gravi + lievi + grazie)))}/{n}; parole del messaggio perse {perse}/{tot} ({perse / max(tot, 1):.1%}) in {len(gravi)} risposte (GRAVE)")
    print(f"  firme rimaste attaccate al messaggio: {len(lievi)} risposte (lieve), {sum(len(x['rimasti']) for x in righe)} parole di firma in tutto;"
          f" un «Grazie» finale preso per firma: {len(grazie)} (lieve)")
    if estranei:
        print(f"  testo che non e' ne' messaggio ne' firma per il giudice (la nostra mail citata, l'oggetto) rimasto nel messaggio: {len(estranei)} risposte")
    if gravi:
        print("\n  LE PAROLE PERSE (il messaggio tagliato), una per una")
        for x in gravi:
            print(f"   - perse: {', '.join(x['perse'][:14])}\n       il giudice: «{corto(x['messaggio_vero'], 200)}»\n       il sistema: «{corto(x['messaggio_sis'], 200)}»")
    if lievi and "--dettagli" in sys.argv:
        print("\n  le firme rimaste")
        for x in lievi:
            print(f"   - {', '.join(x['rimasti'][:10])}: «{corto(x['messaggio_sis'], 160)}»")
    if estranei and "--dettagli" in sys.argv:
        print("\n  il testo estraneo rimasto")
        for x in estranei:
            print(f"   - {', '.join(x['estranei'][:10])}: «{corto(x['messaggio_sis'], 160)}»")
    return {"risposte": n, "giuste": n - len(set(map(id, gravi + lievi + grazie))), "con_parole_perse": len(gravi), "grazie_finale_perso": len(grazie), "parole_perse": perse, "parole_messaggio": tot,
            "con_firma_rimasta": len(lievi), "con_testo_estraneo": len(estranei)}


# ═══ PARTE 3: GLI AVVISI A DRE ════════════════════════════════════

def segnale_del_sistema(caso):
    """La stessa lettura del giro vero (segnale_provvisorio.valuta + leggi), senza memoria e senza mail:
    l'autorisposta ovvia si salta col codice, il resto lo legge il modello sul messaggio diviso dalla firma."""
    import segnale_provvisorio as S
    _guarda_moduli()
    r = (stanza.sb("GET", f"/rest/v1/interactions?select=id,prospect_id,body&id=eq.{caso['interaction_id']}") or [None])[0] or {}
    p = (stanza.sb("GET", f"/rest/v1/prospects?select=company,name&id=eq.{r.get('prospect_id')}") or [{}])[0] or {}
    corpo = r.get("body") or caso["testo_metro"]
    if lettura._segnaposto(corpo):
        corpo = caso["testo_metro"]
    if S.automatica(corpo):
        return {"segnale": "niente", "perche": "autorisposta ovvia per il codice: non si legge"}
    testo = solo = lettura.solo_suo(corpo, con_firma=True) or corpo
    if not solo.strip():
        return {"segnale": "da_guardare", "perche": "vuota"}
    azienda = " ".join((p.get("company") or p.get("name") or "?").split())
    messaggio, firma = lettura.dividi(testo)
    try:
        grezzo = S._chiedi_ai(S.DOMANDA.format(azienda=azienda, messaggio=(messaggio or testo)[:2500], firma=(firma or "(nessuna)")[:800]))
        m = re.search(r"\{.*\}", grezzo or "", re.S)
        v = json.loads(m.group(0)) if m else None
    except TettoRaggiunto:
        raise
    except Exception as e:                                   # noqa: BLE001
        return {"segnale": "da_guardare", "perche": f"l'AI non ha risposto: {str(e)[:80]}"}
    if not isinstance(v, dict) or not all(isinstance(v.get(k), bool) for k in ("autorisposta", "caldo", "si")):
        return {"segnale": "da_guardare", "perche": "risposta del modello non leggibile"}
    seg = "niente" if v["autorisposta"] else "caldo" if v["caldo"] else "si" if v["si"] else "niente"
    return {"segnale": seg, "perche": v.get("frase") or "", "consiglio": v.get("consiglio") or "", "telefono": v.get("telefono") or "",
            "messaggio": messaggio[:600], "firma": firma[:300]}


def parte3():
    PARTE.n = 3
    dre = mosse_di_dre()
    if not dre:
        return {"errore": "manca la mappa di Dre (p1_azioni_dre.json)"}
    metro = {r["interaction_id"]: r for r in stanza.sb_tutte("/rest/v1/metro_risposte?select=interaction_id,testo,etichetta,nota", chiave="interaction_id")}
    fatte = {} if RIFAI else (leggi_json("p3_sistema.json", {}) or {})
    da_fare = [d for d in dre if d["interaction_id"] not in fatte or fatte[d["interaction_id"]].get("segnale") == "ERRORE"]

    def uno(d):
        PARTE.n = 3
        try:
            return d["interaction_id"], segnale_del_sistema({"interaction_id": d["interaction_id"], "testo_metro": metro[d["interaction_id"]]["testo"]})
        except Exception as e:                               # noqa: BLE001
            return d["interaction_id"], {"segnale": "ERRORE", "perche": f"{type(e).__name__}: {str(e)[:120]}"}
    for iid, v in in_parallelo(uno, da_fare, 6):
        fatte[iid] = v
        scrivi_json("p3_sistema.json", fatte)
    righe = []
    for d in dre:
        s = fatte.get(d["interaction_id"], {})
        m = metro.get(d["interaction_id"], {})
        atteso = set(d.get("segnale_atteso") or ["niente"])
        dato = s.get("segnale")
        if dato in atteso:
            esito = "giusto"
        elif dato == "caldo":
            esito = "falso caldo"
        elif dato == "niente" and atteso & {"si", "caldo"}:
            esito = "caldo perso" if atteso == {"caldo"} else "sì perso"
        elif dato == "si" and "caldo" in atteso:
            esito = "caldo arrivato come sì"
        elif dato == "si":
            esito = "falso sì"
        elif dato == "da_guardare":
            esito = "da guardare"
        else:
            esito = "non misurato"
        righe.append({"id": d["interaction_id"], "atteso": sorted(atteso), "dato": dato, "esito": esito, "frase": s.get("perche", ""),
                      "testo": m.get("testo", ""), "nota": m.get("nota") or "", "etichetta": m.get("etichetta")})
    scrivi_json("p3_esito.json", righe)
    return {"righe": righe}


def stampa3(r):
    if r.get("errore"):
        print("  " + r["errore"]); return {}
    righe = r["righe"]
    c = collections.Counter(x["esito"] for x in righe)
    n = len(righe)
    si_attesi = sum(1 for x in righe if set(x["atteso"]) & {"si", "caldo"} and "niente" not in x["atteso"])
    print(f"  avvisi giusti {c['giusto']}/{n} ({c['giusto'] / n:.0%})")
    print(f"  sì persi {c['sì perso']} e caldi persi {c['caldo perso']} (su {si_attesi} che dovevano suonare); falsi caldi {c['falso caldo']}; "
          f"falsi sì {c['falso sì']}; caldi arrivati come sì {c['caldo arrivato come sì']}; da guardare {c['da guardare']}")
    for titolo, quali in (("I SÌ E I CALDI PERSI (pericolosi)", ("sì perso", "caldo perso")), ("I FALSI CALDI", ("falso caldo",)),
                          ("I FALSI SÌ", ("falso sì",)), ("I CALDI ARRIVATI COME SÌ", ("caldo arrivato come sì",))):
        el = [x for x in righe if x["esito"] in quali]
        if el:
            print(f"\n  {titolo}")
            for x in el:
                print(f"   - [{x['etichetta']}] «{corto(x['testo'], 200)}»\n       atteso {'/'.join(x['atteso'])}, dato {x['dato']}"
                      + (f"; Dre: «{corto(x['nota'], 140)}»" if x["nota"] else "") + (f"; frase letta: «{corto(x['frase'], 80)}»" if x["frase"] else ""))
    return {"giusti": c["giusto"], "su": n, "si_persi": c["sì perso"], "caldi_persi": c["caldo perso"], "falsi_caldi": c["falso caldo"],
            "falsi_si": c["falso sì"], "caldi_come_si": c["caldo arrivato come sì"], "da_guardare": c["da guardare"]}


# ═══ PARTE 4: LA SECONDA TESTA ════════════════════════════════════

TIPI_ERRORE = ("nome sbagliato", "fatto inventato", "la mail non era partita", "call a chi ha detto no",
               "ripete la nostra mail", "collega inventato", "ignora una domanda")


def _ora(at):
    """L'ora di una riga del filo, qualunque formato abbia (il CRM in ISO, certe mail vecchie in RFC 2822)."""
    import email.utils
    t = str(at or "")
    try:
        d = stanza.quando(t if ("+" in t[10:] or t.endswith("Z")) else t + "+00:00")
    except ValueError:
        try:
            d = email.utils.parsedate_to_datetime(t)
        except Exception:                                    # noqa: BLE001
            return datetime.datetime(1970, 1, 1, tzinfo=datetime.timezone.utc)
    return d if d.tzinfo else d.replace(tzinfo=datetime.timezone.utc)


def prepara4():
    """25 risposte vere gia' mandate e verificate (proposte fatte dal 15/10): la bozza e i fatti del filo
    COM'ERA PRIMA dell'invio (lettura.filo, tagliato all'ora dell'invio, e lettura.ha_gia di oggi)."""
    PARTE.n = 4
    _guarda_moduli()
    import manda                                            # noqa: F401  il guardiano su Smartlead
    _guarda_moduli()
    fatte = stanza.sb("GET", "/rest/v1/proposte?select=id,at,prospect_id,azione&stato=eq.fatta&tipo=eq.risposta&at=gte.2026-10-15"
                             "&order=at.desc&limit=200") or []
    fatte = [x for x in fatte if (x.get("azione") or {}).get("bozza") and (x.get("azione") or {}).get("invio")]
    per_intento = collections.defaultdict(list)
    for x in fatte:
        per_intento[x["azione"].get("intento") or "?"].append(x)
    random.seed(17)
    quote = {"INT-02": 10, "INT-07": 6, "INT-01": 4, "FOLLOW UP 1": 2, "INT-05": 1, "INT-03": 1, "INT-08": 1}
    scelte = []
    for k, q in quote.items():
        v = per_intento.get(k, [])
        random.shuffle(v)
        scelte += v[:q]
    resto = [x for x in fatte if x not in scelte]
    scelte += resto[:max(0, 25 - len(scelte))]

    def uno(x):
        PARTE.n = 4
        p = (stanza.sb("GET", f"/rest/v1/prospects?select=*&id=eq.{x['prospect_id']}") or [{}])[0]
        partita = str((x["azione"].get("invio") or {}).get("alle") or x["at"])
        alle = datetime.datetime.fromisoformat(partita).astimezone(datetime.timezone.utc) - datetime.timedelta(minutes=3)
        righe = [r for r in lettura.filo(p) if _ora(r.get("at")) < alle]
        f = lettura.ha_gia(p, righe)
        return {"id": x["id"], "gruppo": (x["azione"].get("lettura") or {}).get("gruppo"), "intento": x["azione"].get("intento"),
                "bozza": x["azione"]["bozza"], "fatti": f, "filo": [{"kind": r["kind"], "at": r.get("at"), "body": corto(r.get("body"), 1200)} for r in righe[-8:]]}
    casi = in_parallelo(uno, scelte[:25], 4)
    scrivi_json("p4_casi.json", casi)
    print(f"parte 4: {len(casi)} casi giusti preparati in {DATI}/p4_casi.json; ora le mutazioni (p4_mutazioni.json), scritte a mano")


def parte4():
    PARTE.n = 4
    casi = leggi_json("p4_casi.json")
    mut = {m["id"]: m for m in (leggi_json("p4_mutazioni.json", []) or [])}
    if not casi or not mut:
        return {"errore": "mancano i casi (python3 scripts/esame.py --prepara 4) o le mutazioni scritte a mano (p4_mutazioni.json)"}
    fatte = {} if RIFAI else (leggi_json("p4_sistema.json", {}) or {})
    lavori = []
    for c in casi:
        lavori.append((f"{c['id']}:giusta", c, c["bozza"]))
        if c["id"] in mut:
            lavori.append((f"{c['id']}:sbagliata", c, mut[c["id"]]["bozza"]))
    da_fare = [w for w in lavori if w[0] not in fatte or fatte[w[0]]["verdetto"] == "ERRORE"]

    def uno(w):
        PARTE.n = 4
        k, c, bozza = w
        try:
            v, motivo = lettura.coerenza(c["fatti"], bozza, c.get("gruppo"))
            if "non ha risposto" in motivo:
                return k, {"verdetto": "ERRORE", "motivo": motivo}
            return k, {"verdetto": v, "motivo": motivo}
        except Exception as e:                               # noqa: BLE001
            return k, {"verdetto": "ERRORE", "motivo": str(e)[:120]}
    for k, v in in_parallelo(uno, da_fare, 5):
        fatte[k] = v
        scrivi_json("p4_sistema.json", fatte)
    righe = []
    for k, c, bozza in lavori:
        v = fatte.get(k, {})
        sbagliata = k.endswith(":sbagliata")
        righe.append({"chiave": k, "sbagliata": sbagliata, "tipo": mut.get(c["id"], {}).get("tipo") if sbagliata else None,
                      "verdetto": v.get("verdetto"), "motivo": v.get("motivo", ""), "piantato": mut.get(c["id"], {}).get("cosa") if sbagliata else None,
                      "loro": corto(c["fatti"].get("ultima_loro"), 200)})
    scrivi_json("p4_esito.json", righe)
    return {"righe": righe}


def stampa4(r):
    if r.get("errore"):
        print("  " + r["errore"]); return {}
    righe = [x for x in r["righe"] if x["verdetto"] in ("COERENTE", "INCOERENTE")]
    sb_ = [x for x in righe if x["sbagliata"]]
    gi = [x for x in righe if not x["sbagliata"]]
    presi = [x for x in sb_ if x["verdetto"] == "INCOERENTE"]
    falsi = [x for x in gi if x["verdetto"] == "INCOERENTE"]
    print(f"  errori piantati presi {len(presi)}/{len(sb_)} ({len(presi) / max(len(sb_), 1):.0%}); falsi allarmi sulle giuste {len(falsi)}/{len(gi)} ({len(falsi) / max(len(gi), 1):.0%})")
    per_tipo = collections.defaultdict(lambda: [0, 0])
    for x in sb_:
        per_tipo[x["tipo"]][1] += 1
        per_tipo[x["tipo"]][0] += x["verdetto"] == "INCOERENTE"
    print("  per tipo di errore: " + "; ".join(f"{t} {a}/{b}" for t, (a, b) in sorted(per_tipo.items())))
    mancati = [x for x in sb_ if x["verdetto"] == "COERENTE"]
    if mancati:
        print("\n  GLI ERRORI CHE LA SECONDA TESTA HA LASCIATO PASSARE (pericolosi)")
        for x in mancati:
            print(f"   - [{x['tipo']}] piantato: {x['piantato']}\n       la loro mail: «{x['loro']}»")
    if falsi:
        print("\n  I FALSI ALLARMI (mail giuste, gia' mandate e approvate, bocciate)")
        for x in falsi:
            print(f"   - «{corto(x['motivo'], 200)}»\n       la loro mail: «{x['loro']}»")
    non = [x for x in r["righe"] if x["verdetto"] not in ("COERENTE", "INCOERENTE")]
    if non:
        print(f"  non misurati (la seconda testa non ha risposto): {len(non)}")
    return {"piantati": len(sb_), "presi": len(presi), "giuste": len(gi), "falsi_allarmi": len(falsi),
            "per_tipo": {t: f"{a}/{b}" for t, (a, b) in per_tipo.items()}}


# ═══ PARTE 5: LE BOZZE DI CLARA ═══════════════════════════════════

def prepara5():
    """20 bozze recenti scritte da Clara (bozze.py: niente «scritta_da»), aperte o fatte, col filo vero
    fino al momento della bozza: le giudica un giudice indipendente contro il filo e lo stile di Dre."""
    PARTE.n = 5
    righe = stanza.sb("GET", "/rest/v1/proposte?select=id,at,stato,tipo,prospect_id,titolo,azione&tipo=eq.risposta"
                             "&stato=in.(aperta,fatta)&order=at.desc&limit=400") or []
    clara = [x for x in righe if (x.get("azione") or {}).get("bozza") and (x.get("azione") or {}).get("lettura")
             and not (x.get("azione") or {}).get("scritta_da")]
    # le piu' recenti, ma non venti follow-up col template: al massimo 6 per intento, cosi' si giudica
    # anche cio' che Clara scrive di suo (prima risposta, rinvii, inoltri, chi siete)
    per_intento, scelte = collections.Counter(), []
    for x in clara:
        k = (x["azione"].get("intento") or "?").strip().replace("FOLLOW UP 1", "FOLLOW UP")
        if per_intento[k] < 6 and len(scelte) < 20:
            per_intento[k] += 1
            scelte.append(x)
    clara = scelte
    casi = []
    for x in clara:
        p = (stanza.sb("GET", f"/rest/v1/prospects?select=company,name,email,sector,city,analysis_sent,analysis_sent_at,analysis_pdf&id=eq.{x['prospect_id']}") or [{}])[0]
        filo = stanza.sb("GET", f"/rest/v1/interactions?select=kind,at,body&prospect_id=eq.{x['prospect_id']}&kind=in.(email_in,email_out,followup,analisi)"
                                f"&at=lte.{urllib.parse.quote(x['at'])}&order=at.asc&limit=40") or []
        az = x["azione"]
        casi.append({"id": x["id"], "creata_il": x["at"], "stato": x["stato"], "intento": az.get("intento"),
                     "gruppo": (az.get("lettura") or {}).get("gruppo"), "testo_dal_codice": bool(az.get("testo_dal_codice")),
                     "allega": bool(az.get("allega")), "allega_presentazione": bool(az.get("allega_presentazione")),
                     "azienda": p.get("company"), "nome_in_scheda": p.get("name"), "settore": p.get("sector"), "citta": p.get("city"),
                     "analisi_gia_mandata": bool(p.get("analysis_sent")), "analisi_pdf_esiste": bool(p.get("analysis_pdf")),
                     "lettura": {k: (az.get("lettura") or {}).get(k) for k in ("ultima_loro", "ultima_loro_il", "ultima_nostra", "ultima_nostra_il",
                                                                              "detto_no", "autorisposta", "girato_a", "analisi_ricevuta", "coerenza", "coerenza_motivo")},
                     "filo": [{"kind": r["kind"], "at": r["at"], "body": corto(r.get("body"), 1500)} for r in filo[-10:]],
                     "bozza": az["bozza"]})
    scrivi_json("p5_casi.json", casi)
    print(f"parte 5: {len(casi)} bozze di Clara in {DATI}/p5_casi.json, per il giudice")


def parte5():
    casi = leggi_json("p5_casi.json")
    giud = leggi_json("p5_giudice.json")
    if not casi or not giud:
        return {"errore": "mancano le bozze (--prepara 5) o il giudizio (p5_giudice.json)"}
    per_id = {c["id"]: c for c in casi}
    return {"righe": [{**g, "loro": corto((per_id.get(g["id"], {}).get("lettura") or {}).get("ultima_loro"), 200),
                       "intento": per_id.get(g["id"], {}).get("intento")} for g in giud]}


def stampa5(r):
    if r.get("errore"):
        print("  " + r["errore"]); return {}
    righe = r["righe"]
    c = collections.Counter(x["verdetto"] for x in righe)
    n = len(righe)
    print(f"  partirebbero così come sono {c['PARTE']}/{n}; con un ritocco {c['RITOCCO']}; da riscrivere {c['RISCRIVERE']}; da non mandare {c['NON_MANDARE']}")
    crit = collections.Counter()
    for x in righe:
        for k, v in (x.get("criteri") or {}).items():
            if v is False:
                crit[k] += 1
    if crit:
        print("  i criteri mancati: " + ", ".join(f"{k} {v}" for k, v in crit.most_common()))
    gravi = [x for x in righe if x["verdetto"] in ("NON_MANDARE", "RISCRIVERE")]
    if gravi:
        print("\n  LE BOZZE DA RISCRIVERE O DA NON MANDARE")
        for x in gravi:
            print(f"   - [{x['verdetto']}, {x.get('intento')}] {x.get('motivo')}\n       la loro mail: «{x['loro']}»")
    return {"bozze": n, "parte": c["PARTE"], "ritocco": c["RITOCCO"], "riscrivere": c["RISCRIVERE"], "non_mandare": c["NON_MANDARE"], "criteri_mancati": dict(crit)}


# ═══ IL PAGELLINO ═════════════════════════════════════════════════

PARTI = {1: ("CAPIRE LA RISPOSTA -> LA DECISIONE", parte1, stampa1), 2: ("MESSAGGIO E FIRMA (lettura.dividi)", parte2, stampa2),
         3: ("GLI AVVISI A DRE (segnale provvisorio)", parte3, stampa3), 4: ("LA SECONDA TESTA (lettura.coerenza)", parte4, stampa4),
         5: ("LE BOZZE DI CLARA", parte5, stampa5)}


def main():
    if "--prepara" in sys.argv:
        n = int(_arg("--prepara"))
        {4: prepara4, 5: prepara5}[n]()
        return
    quali = [int(_arg("--parte"))] if "--parte" in sys.argv else sorted(PARTI)
    print(f"L'ESAME DI AFFIDABILITA' ({datetime.date.today():%d/%m/%Y}), dati in {DATI}\n")
    numeri = {}
    for n in quali:
        titolo, fa, stampa = PARTI[n]
        print(f"══ {n}. {titolo}")
        try:
            numeri[n] = stampa(fa())
        except TettoRaggiunto as e:
            print(f"  fermato: {e}")
        print()
    conto = _conto_file()
    print(f"chiamate ai modelli: {CHIAMATE['questa_corsa']} in questa corsa, {conto['totale']} in tutto (tetto {TETTO}) {conto['per_parte']}")
    print("scritture fermate dal guardiano: " + (", ".join(f"{k} x{v}" for k, v in BLOCCATE.most_common()) if BLOCCATE else "nessuna"))
    if len(quali) == len(PARTI):
        os.makedirs(NEL_REPO, exist_ok=True)
        json.dump({"il": datetime.date.today().isoformat(), "numeri": numeri, "chiamate_ai_modelli": conto["totale"]},
                  open(os.path.join(NEL_REPO, "pagellino.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()
