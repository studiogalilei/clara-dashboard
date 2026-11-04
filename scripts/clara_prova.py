"""CLARA IN PROVA: la sandbox sul vivo (3/11/2026, sera).

Dre: «prima trainare, testare il sistema in sandbox, proprio il reale sistema che poi andra' a
lavorare, finche' non arriva al livello che fa le cose bene, e rilasciarlo». Qui il cervello nuovo
(clara_sdr) decide su ogni risposta vera che entra, con gli strumenti veri (calendario, scheda,
filo di Smartlead), accanto al sistema di oggi che continua a fare il suo. Non manda niente e non
tocca Smartlead: scrive la decisione in clara_decisioni e nella scheda «Clara in prova» del foglio.
Dre, nel foglio, dice se va bene e cosa avrebbe fatto lui; il giudice indipendente vota ogni
decisione. Da li' si addestra l'identita' e si rigioca tutto il banco a ogni versione.

Uso:
  python3 scripts/clara_prova.py --email X     dalla strada veloce: decide sull'ultima risposta
  python3 scripts/clara_prova.py --giro        ogni 10 minuti: risposte senza decisione, giudice,
                                               foglio, correzioni di Dre
  --prova                                      decide e stampa, non scrive niente
"""
import datetime
import json
import os
import sys
import urllib.parse

QUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, QUI)
import clara_sdr  # noqa: E402
import lettore  # noqa: E402
from stanza import sb, sb_tutte  # noqa: E402

PROVA = os.environ.get("PROVA") == "1" or "--prova" in sys.argv
OPERAZIONE = "clara_prova"
SCHEDA = "Clara in prova"
RIGHE = 400
FINESTRA_ORE = 48          # risposte piu' vecchie non si decidono nel giro (il banco storico e' l'esame)
PER_GIRO = 15              # decisioni al massimo per giro: un tetto alla spesa, non una coda persa
TETTO_GIORNO = 25.0        # dollari al giorno per il cervello in prova (notte del 4/11: si rigioca tutto)
TETTO_GIUDICE = 10.0
COLONNE = [("Quando", 95), ("Azienda", 150), ("Il lead ha scritto", 340), ("Mossa", 100), ("Perché", 250),
           ("Testo che manderebbe", 400), ("Segnali", 150), ("Giudice", 130),
           ("Va bene? (ok / no)", 110), ("Cosa avresti fatto tu", 260), ("Note", 220), ("id", 40)]
DI_DRE = (8, 9, 10)        # le colonne gialle: I, J, K
ROMA = datetime.timezone(datetime.timedelta(hours=1))


def adesso():
    return datetime.datetime.now(datetime.timezone.utc)


def acceso():
    r = sb("GET", f"/rest/v1/operazioni?select=attiva&chiave=eq.{OPERAZIONE}") or []
    return bool(r and r[0].get("attiva"))


def _roma(iso):
    try:
        import zoneinfo
        return datetime.datetime.fromisoformat(iso.replace("Z", "+00:00")).astimezone(zoneinfo.ZoneInfo("Europe/Rome"))
    except (ValueError, TypeError, AttributeError):
        return None


# ── 1. decidere ────────────────────────────────────────────────────────────────

def _storia(p):
    h = lettore._smartlead(f"/campaigns/{p['campaign_id']}/leads/{p['lead_id']}/message-history") or {}
    return h.get("history") or []


RIFAI = "--rifai" in sys.argv       # rigioca con l'identita' nuova le decisioni ancora da fare di versioni vecchie


def gia_decisa(pid, risposta_il):
    r = sb("GET", f"/rest/v1/clara_decisioni?select=risposta_il,versione,stato&prospect_id=eq.{pid}&order=risposta_il.desc,creato_il.desc&limit=1") or []
    if not r:
        return False
    a, b = _roma(r[0]["risposta_il"]), _roma(risposta_il)
    stessa = bool(a and b and abs((a - b).total_seconds()) < 120)
    if stessa and RIFAI and r[0]["stato"] == "proposta" and r[0]["versione"] != clara_sdr.VERSIONE:
        return False                                         # da rifare con l'identita' nuova
    return stessa


def decidi_lead(p, perche=""):
    """Decide sull'ultima risposta del lead e salva. Torna la riga salvata (o la decisione, in prova)."""
    if not (p.get("campaign_id") and p.get("lead_id")):
        print("  lead senza filo Smartlead: niente")
        return None
    storia = _storia(p)
    messaggi = clara_sdr.messaggi_della_relazione(p, storia)   # Smartlead piu' le mail fuori thread del CRM
    risposte = [m for m in messaggi if m["tipo"] == "REPLY"]
    if not risposte:
        print("  nessuna risposta nel filo")
        return None
    risposta_il = risposte[-1]["il"]
    if gia_decisa(p["id"], risposta_il):
        print("  gia' decisa")
        return None
    r = clara_sdr.giudica_uno(p, storia)
    d = r["decisione"]
    riga = {"prospect_id": p["id"], "risposta_il": risposta_il, "versione": clara_sdr.VERSIONE,
            "modello": r["uso"].get("modello") or clara_sdr.MODELLO,
            "lead_testo": (r.get("lead_testo") or "")[:1500],
            "mossa": d["proposed_action"], "owner": d.get("owner"), "entro_il": d.get("due_at") or None,
            "testo": d.get("draft") or None, "perche": d.get("reason_summary"), "prove": d.get("evidence_refs") or [],
            "richiamo": d.get("callback") if d["proposed_action"] == "callback" else None,
            "segnali": r["segnali"], "uso": r["uso"], "contesto": r["contesto"]}
    print(f"  {p.get('company') or '?'}: {d['proposed_action']} (owner {d.get('owner')}, {r['uso'].get('dollari')} $)"
          + (f"; segnali: {'; '.join(r['segnali'])}" if r["segnali"] else ""))
    if PROVA:
        print("  (prova: non si salva)")
        return riga
    sb("POST", "/rest/v1/clara_decisioni?on_conflict=prospect_id,risposta_il,versione", [riga],
       {"Prefer": "resolution=ignore-duplicates,return=minimal"})
    # le decisioni vecchie ancora da fare per questo lead sono superate: il lead ha scritto di nuovo,
    # oppure (--rifai) l'identita' e' cambiata e questa e' la decisione nuova sulla stessa risposta
    sb("PATCH", f"/rest/v1/clara_decisioni?prospect_id=eq.{p['id']}&risposta_il=lt.{urllib.parse.quote(risposta_il)}&stato=in.(proposta,approvata)",
       {"stato": "superata"}, {"Prefer": "return=minimal"})
    sb("PATCH", f"/rest/v1/clara_decisioni?prospect_id=eq.{p['id']}&risposta_il=eq.{urllib.parse.quote(risposta_il)}&versione=neq.{clara_sdr.VERSIONE}&stato=eq.proposta",
       {"stato": "superata"}, {"Prefer": "return=minimal"})
    return riga


def spesa(scopo):
    try:
        return float(lettore.spesa_di_oggi(scopo) or 0)
    except Exception:                                            # noqa: BLE001
        return 0.0


def risposte_nuove(ore=None):
    """I lead con una risposta nelle ultime FINESTRA_ORE senza una decisione: i piu' recenti prima."""
    da = (adesso() - datetime.timedelta(hours=ore or FINESTRA_ORE)).strftime("%Y-%m-%dT%H:%M:%SZ")
    # solo chi aspetta noi e si puo' ancora contattare: a chi ha gia' avuto la nostra risposta, o e'
    # cliente/perso/non contattare, non serve una mossa (4/11: senza questo filtro erano 581 lead in 30 giorni)
    righe = sb_tutte(f"/rest/v1/prospects?select=*&last_reply_at=gte.{da}&lead_id=not.is.null&campaign_id=not.is.null&awaiting_us=eq.true")
    righe.sort(key=lambda r: r.get("last_reply_at") or "", reverse=True)
    from stanza import contattabile
    fuori = []
    for p in righe:
        if contattabile(p) and not gia_decisa(p["id"], p["last_reply_at"]):
            fuori.append(p)
    return fuori


def supera_vecchie():
    """Una decisione ancora «proposta» per un lead che non aspetta piu' noi (gli abbiamo risposto, o e'
    cliente/perso/non contattare) e' superata: nel Desk non deve restare un «Invia» su una cosa gia' fatta
    (4/11: 94 decisioni della prima notte erano su lead gia' serviti dal sistema vecchio)."""
    righe = sb_tutte("/rest/v1/clara_decisioni?select=id,prospect_id,prospects(awaiting_us,fuori,stage,pipeline_stage,no_followup,classificazione)&stato=eq.proposta", chiave="id")
    from stanza import contattabile
    vecchie = [r["id"] for r in righe if r.get("prospects") and (not r["prospects"].get("awaiting_us") or not contattabile({**r["prospects"], "id": None}))]
    for i in range(0, len(vecchie), 50):
        if not PROVA:
            sb("PATCH", f"/rest/v1/clara_decisioni?id=in.({','.join(vecchie[i:i + 50])})", {"stato": "superata"}, {"Prefer": "return=minimal"})
    return len(vecchie)


# ── 2. il giudice ──────────────────────────────────────────────────────────────

def giudica_nuove(massimo=30):
    import esame_clara
    righe = sb("GET", f"/rest/v1/clara_decisioni?select=*&giudice=is.null&order=creato_il.desc&limit={massimo}") or []
    fatte = 0
    for d in righe:
        if spesa("esame_clara") > TETTO_GIUDICE:
            print(f"  giudice: tetto del giorno ({TETTO_GIUDICE} $), si ferma")
            break
        r = {"contesto": d["contesto"], "segnali": d["segnali"] or [],
             "decisione": {"proposed_action": d["mossa"], "reason_summary": d["perche"], "evidence_refs": d["prove"],
                           "owner": d["owner"], "due_at": d["entro_il"], "draft": d["testo"], "callback": d["richiamo"]},
             "dopo": "(ancora niente: la decisione è di oggi; giudica la mossa e il testo per quello che si sa)"}
        try:
            g = esame_clara.giudica(r)
        except Exception as e:                                   # noqa: BLE001
            g = {"errore": str(e)[:200]}
        if not PROVA:
            sb("PATCH", f"/rest/v1/clara_decisioni?id=eq.{d['id']}", {"giudice": g}, {"Prefer": "return=minimal"})
        fatte += 1
    return fatte


# ── 3. il foglio: la scheda «Clara in prova» ───────────────────────────────────

def _id_scheda(sid):
    from foglio import _g, SHEETS, rgb, NAVY, GIALLO, _campo, _formato
    info = _g("GET", f"{SHEETS}/{sid}?fields=sheets.properties")
    for s in info.get("sheets", []):
        if s["properties"]["title"] == SCHEDA:
            return s["properties"]["sheetId"]
    nuovo = max([s["properties"]["sheetId"] for s in info.get("sheets", [])] + [0]) + 1
    nc = len(COLONNE)
    R = [{"addSheet": {"properties": {"sheetId": nuovo, "title": SCHEDA, "index": 2, "tabColor": rgb(NAVY),
                                      "gridProperties": {"rowCount": RIGHE, "columnCount": nc, "frozenRowCount": 2,
                                                         "hideGridlines": False}}}}]
    for i, (_, w) in enumerate(COLONNE):
        R.append({"updateDimensionProperties": {"range": {"sheetId": nuovo, "dimension": "COLUMNS", "startIndex": i, "endIndex": i + 1},
                                                "properties": {"pixelSize": w}, "fields": "pixelSize"}})
    R.append({"updateDimensionProperties": {"range": {"sheetId": nuovo, "dimension": "COLUMNS", "startIndex": nc - 1, "endIndex": nc},
                                            "properties": {"hiddenByUser": True}, "fields": "hiddenByUser"}})
    R.append({"mergeCells": {"range": _campo(nuovo, 0, 1, 0, nc), "mergeType": "MERGE_ALL"}})
    R.append(_formato(_campo(nuovo, 0, 1, 0, nc), colore=NAVY, grassetto=True, dim=12, vert="MIDDLE", a_capo="WRAP"))
    R.append(_formato(_campo(nuovo, 1, 2, 0, nc), fondo=NAVY, colore="#ffffff", grassetto=True, dim=10, vert="MIDDLE", a_capo="WRAP"))
    R.append(_formato(_campo(nuovo, 2, RIGHE, 0, nc), dim=10, vert="TOP", a_capo="WRAP"))
    R.append(_formato(_campo(nuovo, 2, RIGHE, DI_DRE[0], DI_DRE[-1] + 1), fondo=GIALLO))
    R.append({"setDataValidation": {"range": _campo(nuovo, 2, RIGHE, DI_DRE[0], DI_DRE[0] + 1),
                                    "rule": {"condition": {"type": "ONE_OF_LIST", "values": [{"userEnteredValue": "ok"}, {"userEnteredValue": "no"}]},
                                             "showCustomUi": True, "strict": False}}})
    R.append({"addProtectedRange": {"protectedRange": {"range": _campo(nuovo, 0, RIGHE, 0, DI_DRE[0]), "warningOnly": True,
                                                       "description": "Lo scrive il sistema: le tue colonne sono quelle gialle"}}})
    R.append({"updateDimensionProperties": {"range": {"sheetId": nuovo, "dimension": "ROWS", "startIndex": 0, "endIndex": 1},
                                            "properties": {"pixelSize": 44}, "fields": "pixelSize"}})
    _g("POST", f"{SHEETS}/{sid}:batchUpdate", {"requests": R})
    print(f"  scheda «{SCHEDA}» creata")
    return nuovo


def _giudice_breve(g):
    if not g:
        return ""
    if g.get("errore"):
        return "non votato"
    return ("PERICOLOSO: " + (g.get("errore_pericoloso") or "")[:80] if g.get("pericoloso") else "mossa " + str(g.get("mossa")))


def righe_foglio(giorni=14):
    da = (adesso() - datetime.timedelta(days=giorni)).strftime("%Y-%m-%dT%H:%M:%SZ")
    righe = sb_tutte(f"/rest/v1/clara_decisioni?select=*,prospects(company)&creato_il=gte.{da}&order=creato_il.desc")
    righe.sort(key=lambda d: (d["risposta_il"], d["creato_il"]), reverse=True)   # la risposta piu' recente in alto
    viste, fuori = set(), []
    for d in righe:                                              # l'ultima versione per ogni risposta
        k = (d["prospect_id"], d["risposta_il"][:16])
        if k in viste:
            continue
        viste.add(k)
        q = _roma(d["risposta_il"])
        fuori.append([q.strftime("%d/%m %H:%M") if q else "", ((d.get("prospects") or {}).get("company") or "")[:60],
                      (d.get("lead_testo") or "")[:700], d["mossa"] + (f"\n→ {d['owner']}" if d.get("owner") and d["owner"] != "Clara" else ""),
                      d.get("perche") or "", d.get("testo") or "", "\n".join(d.get("segnali") or []),
                      _giudice_breve(d.get("giudice")), d.get("dre_giudizio") or "", d.get("dre_mossa") or "",
                      d.get("dre_nota") or "", d["id"]])
    return fuori[:RIGHE - 2]


def scrivi_foglio(sid):
    from foglio import _g, SHEETS
    S = _id_scheda(sid)
    valori = righe_foglio()
    testa = [[f"Clara in prova: decide su ogni risposta, non manda. Versione {clara_sdr.VERSIONE}, {len(valori)} decisioni negli ultimi 14 giorni. "
              "Nelle colonne gialle: va bene? (ok / no), cosa avresti fatto tu, note. Achille le legge ogni 10 minuti."] + [""] * (len(COLONNE) - 1),
             [c for c, _ in COLONNE]]
    _g("POST", f"{SHEETS}/{sid}/values:batchClear", {"ranges": [f"{SCHEDA}!A1:L{RIGHE}"]})
    _g("POST", f"{SHEETS}/{sid}/values:batchUpdate", {"valueInputOption": "RAW", "data": [
        {"range": f"{SCHEDA}!A1:L{2 + len(valori)}", "values": testa + valori}]})
    return S, len(valori)


def leggi_correzioni(sid):
    """Le colonne gialle: quello che Dre ha scritto e nel database ancora non c'e'."""
    from foglio import _g, SHEETS
    try:
        d = _g("GET", f"{SHEETS}/{sid}/values/{urllib.parse.quote(SCHEDA + '!I3:L' + str(RIGHE))}?valueRenderOption=UNFORMATTED_VALUE")
    except RuntimeError:
        return 0
    nuove = 0
    for riga in d.get("values", []):
        riga = [str(x).strip() if x is not None else "" for x in riga] + [""] * (4 - len(riga))
        ok, mossa, nota, did = riga[:4]
        if not did or not (ok or mossa or nota):
            continue
        ok = ok.lower() if ok.lower() in ("ok", "no") else None
        r = (sb("GET", f"/rest/v1/clara_decisioni?select=dre_giudizio,dre_mossa,dre_nota&id=eq.{did}") or [None])[0]
        if not r or (r.get("dre_giudizio") == ok and (r.get("dre_mossa") or "") == mossa and (r.get("dre_nota") or "") == nota):
            continue
        if not PROVA:
            sb("PATCH", f"/rest/v1/clara_decisioni?id=eq.{did}",
               {"dre_giudizio": ok, "dre_mossa": mossa or None, "dre_nota": nota or None, "dre_il": adesso().isoformat()},
               {"Prefer": "return=minimal"})
        nuove += 1
    return nuove


def foglio():
    from foglio import carica_stato, trova_foglio
    sid = trova_foglio(carica_stato())
    if not sid:
        print("  foglio della pipeline non trovato")
        return
    corrette = leggi_correzioni(sid)
    if PROVA:
        print(f"  (prova: {len(righe_foglio())} righe pronte, {corrette} correzioni lette, niente scritto)")
        return
    _, n = scrivi_foglio(sid)
    print(f"  foglio: {n} decisioni, {corrette} correzioni nuove di Dre")


# ── il giro ────────────────────────────────────────────────────────────────────

def registra(esito, dettaglio, partita):
    if PROVA:
        return
    try:
        sb("PATCH", f"/rest/v1/operazioni?chiave=eq.{OPERAZIONE}",
           {"ultima_corsa": adesso().isoformat(), "ultimo_esito": esito, "ultimo_dettaglio": dettaglio[-500:],
            "ultima_durata_ms": int((adesso() - partita).total_seconds() * 1000)})
    except Exception:                                            # noqa: BLE001
        pass


def _arg(nome, default):
    try:
        return int(sys.argv[sys.argv.index(nome) + 1])
    except (ValueError, IndexError):
        return default


def giro():
    partita = adesso()
    if not acceso():
        print("clara_prova: spenta in operazioni")
        return
    note = []
    ore, massimo = _arg("--ore", FINESTRA_ORE), _arg("--max", PER_GIRO)
    try:
        cand = risposte_nuove(ore)
        print(f"risposte senza decisione nelle ultime {ore} ore: {len(cand)}")
        decise = 0
        for p in cand[:massimo]:
            if spesa("clara_sdr") > TETTO_GIORNO:
                note.append(f"tetto del giorno ({TETTO_GIORNO} $) raggiunto")
                break
            try:
                if decidi_lead(p):
                    decise += 1
            except Exception as e:                               # noqa: BLE001
                print(f"  {p.get('company') or '?'}: non decisa ({str(e)[:150]})")
        note.append(f"{decise} decisioni nuove" + (f" ({len(cand) - massimo} restano al prossimo giro)" if len(cand) > massimo else ""))
        note.append(f"{supera_vecchie()} superate (il lead non aspetta più noi)")
        note.append(f"{giudica_nuove()} votate dal giudice")
        foglio()
        registra("ok", "; ".join(note), partita)
    except Exception as e:                                       # noqa: BLE001
        print(f"giro caduto: {e}")
        registra("errore", "; ".join(note + [str(e)[:200]]), partita)
        raise


def uno(email):
    if not acceso():
        print("clara_prova: spenta in operazioni")
        return
    p = (sb("GET", f"/rest/v1/prospects?select=*&email=eq.{urllib.parse.quote(email)}") or [None])[0]
    if not p:
        print("lead non trovato")
        return
    decidi_lead(p)
    foglio()


def main():
    if "--giro" in sys.argv:
        giro()
    elif "--email" in sys.argv:
        uno(sys.argv[sys.argv.index("--email") + 1].strip().lower())
    else:
        sys.exit(__doc__)


if __name__ == "__main__":
    main()
