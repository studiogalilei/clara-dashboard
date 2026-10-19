#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""IL FOGLIO DELLA PIPELINE (19/10/2026).

PERCHE'
Dre, 19/10: «un colpo d'occhio: quanti lead ci sono e quali, in ogni fase, dall'analisi al
cliente», in un foglio Google sul modello di quello di Giacomo, con un po' di gioco. Il design
approvato sta in docs/superpowers/specs/2026-10-19-foglio-pipeline-design.md («è una roba
semplice, non complicarla, fai e basta»). L'app resta la scheda del lead; il foglio e' la vista.

COSA FA, a ogni giro (il direttore, corsia leggera, ogni 10 minuti)
1. LEGGE PRIMA DRE. Le celle gialle del foglio (la scelta della Conversazione, costo, inizio e
   fine della Prova, il retainer, la «Nota per Achille») si confrontano con quello che il sistema
   ci aveva scritto: quello che e' diverso l'ha scritto Dre. Si salva nel database e da li' non si
   riscrive piu' (vince sempre Dre). Spostare e togliere si fa col copia e incolla (Dre, 19/10 sera):
   un nome d'azienda incollato nella colonna Azienda di un'altra fase (senza id nella colonna
   nascosta) e' uno spostamento; un nome cancellato dalla sua riga e' un «togli». Gli effetti:
   - spostato in una fase: la fase nel database (pipeline_stage, come la carta del Workspace) e lo
     stato nell'app; tolto e «Perso»: perso, quindi mai piu' contattabile;
   - «Da chiamare»: entra in Oggi da chiamare; «In attesa di risposta»: dopo 5 giorni senza
     novita' un promemoria a Dre (app e notifica);
   - una nota: nelle note del lead nell'app, a nome di Dramane (le legge Achille);
   - inizio e fine della prova, il retainer: sulla scheda (il retainer va in cassaforte da solo).
2. RISCRIVE IL RESTO. Una riga in alto (titolo, settimana, quando e' stato aggiornato, come si usa),
   le 8 fasi da sinistra a destra (src/snella/stati.json) col conteggio nell'intestazione (e il MRR,
   somma dei retainer, in quella di Cliente), il piu' nuovo in cima (la Prova per scadenza).
   Niente altro: Dre, 19/10 sera: «less noise, solo concretismo».
3. LE CALL DI DRE. Gli appunti di Gemini delle sue call con un lead finiscono in «Chiamate» (Drive
   condiviso). Se in una conoscitiva o in una tecnica vi siete accordati per la call dopo con una
   data, e il giorno dopo l'invito non e' in calendario: un avviso a Dre in Oggi e sul telefono.

COSA NON FA
Nessuna mail, mai: il foglio non scrive bozze, non approva, non tocca il postino ne' Smartlead.
Non cambia nomi, numeri o mail del lead (stanno nell'app).

USO
  python3 scripts/foglio.py              il giro vero (se il foglio non c'e', lo crea in «2 Commerciale»)
  python3 scripts/foglio.py --prova      calcola e stampa, non scrive niente (ne' foglio ne' database)
  python3 scripts/foglio.py --rifai      ricostruisce la forma del foglio (dopo aver letto Dre)
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
from stanza import sb, sb_tutte, quando, proponi, _a_secco, URL, CHIAVE      # noqa: E402

PROVA = _a_secco()
ROMA = zoneinfo.ZoneInfo("Europe/Rome")
RADICE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DRE = "dramane@studiogalilei.com"

_ST = json.load(open(os.path.join(RADICE, "src", "snella", "stati.json"), encoding="utf-8"))
FASI = [f["nome"] for f in _ST["fasi"]]
INFO_FASE = {f["nome"]: f for f in _ST["fasi"]}
FASE_DI_STATO = _ST["fase_di_stato"]
FUORI = _ST["fuori_percorso"]                      # stato -> etichetta del conteggio
PREP, INVIATA, CONV, CONO, TECN, AVVIO, PROVA_F, CLIENTE = FASI
TOGLI = "Togli dal foglio"
SCELTE = ("Da chiamare", "In attesa di risposta", "Perso")
ATTESA_GIORNI = 5
CALL_GIORNI = 45
FERMO_GIORNI = 60
ALTRE = "Altre risposte"
FERMI = "Fermi da 60 giorni"
CALL = {"conoscitiva": CONO, "tecnica": TECN, "avvio": AVVIO}
LIVELLO = {CONO: 0, TECN: 1, AVVIO: 2}

COMMERCIALE = "1ipPNIf8Ep-XFIZq23u4vG8V6xJgpuo5m"     # «2 Commerciale» nel Drive condiviso Studio Galilei
CHIAMATE = "1PWqTL7hhhPr6JaYNbBfadxnojPWAlWb6"        # «Chiamate» (l'ex «5 Riunioni»)
NOME_FOGLIO = "Pipeline Studio Galilei"
SCHEDA = "Pipeline"
LAYOUT = 2                       # cambia la forma -> il foglio si ricostruisce (dopo aver letto Dre). 2: Dre, 19/10 sera, «less noise»
PRIMA = 4                        # la prima riga degli elenchi (contando da 1): titolo, intestazioni delle fasi, titoli delle colonne
RIGHE = 1000
SHEETS = "https://sheets.googleapis.com/v4/spreadsheets"
DRIVE = "https://www.googleapis.com/drive/v3"

GIORNI = ("lun", "mar", "mer", "gio", "ven", "sab", "dom")
MESI = ("gennaio", "febbraio", "marzo", "aprile", "maggio", "giugno", "luglio", "agosto", "settembre",
        "ottobre", "novembre", "dicembre")

# ── la forma: un blocco di colonne per fase ───────────────────────────
# Le celle di Dre (gialle) e quelle del sistema. L'id del lead sta in una colonna nascosta: le
# righe si riordinano a ogni giro, l'id dice di chi e' una cella che Dre ha scritto.
DI_DRE = ("scelta", "costo", "inizio", "fine", "retainer", "nota")
# Spostare e togliere un lead (Dre, 19/10 sera: «"Sposta in" non serve, posso copiare e incollare nel
# luogo giusto»): si copia il nome dell'azienda nella colonna Azienda di un'altra fase, o lo si cancella.
SPOSTA = "sposta"                # il nome interno della mossa (effetti), non una colonna
FRASE_USO = "Scrivi nelle celle gialle. Per spostare un lead copia il nome in un'altra colonna; per toglierlo cancellalo."
DETTAGLIO = {PREP: "Ha scritto", INVIATA: "Inviata", CONV: "Ultima sua", CONO: "Call", TECN: "Call", AVVIO: "Call"}


def _blocchi():
    out, col = [], 0
    for i, fase in enumerate(FASI):
        campi = [("azienda", "Azienda", 170)]
        if fase == PROVA_F:
            campi += [("costo", "Costo", 78), ("inizio", "Inizio", 86), ("fine", "Fine", 86)]
        elif fase == CLIENTE:
            campi += [("retainer", "Retainer al mese", 110)]
        else:
            campi += [("dettaglio", DETTAGLIO[fase], 84)]
        if fase == CONV:
            campi += [("scelta", "La tua scelta", 150)]
        campi += [("nota", "Nota per Achille", 170), ("id", "id", 20)]
        out.append({"fase": fase, "da": col, "campi": [c[0] for c in campi], "titoli": [c[1] for c in campi],
                    "larghezze": [c[2] for c in campi]})
        col += len(campi) + (1 if i < len(FASI) - 1 else 0)          # una colonna stretta fra i blocchi
    return out


BLOCCHI = _blocchi()
NCOL = BLOCCHI[-1]["da"] + len(BLOCCHI[-1]["campi"])


def lettera(i):
    """La colonna (da 0) in lettere: 0 -> A, 26 -> AA."""
    s = ""
    i += 1
    while i:
        i, r = divmod(i - 1, 26)
        s = chr(65 + r) + s
    return s


def colonna(b, campo):
    return b["da"] + b["campi"].index(campo)


# ── i valori: come si confrontano ─────────────────────────────────────

def _numero(v):
    if v is None or v == "":
        return ""
    if isinstance(v, (int, float)):
        return int(v) if float(v).is_integer() else round(float(v), 2)
    t = re.sub(r"[^\d,.\-]", "", str(v))
    if not t:
        return str(v).strip()
    if "," in t:                                   # 1.500,50 all'italiana
        t = t.replace(".", "").replace(",", ".")
    elif t.count(".") == 1 and len(t.split(".")[1]) == 3:
        t = t.replace(".", "")                     # 1.500 = millecinquecento
    else:
        t = t.replace(".", "", t.count(".") - 1)
    try:
        f = float(t)
    except ValueError:
        return str(v).strip()
    return int(f) if f.is_integer() else round(f, 2)


def _data(v):
    """Una data in AAAA-MM-GG da quello che c'e' nella cella (21/10/2026, 21/10/26, il numero di Sheets)."""
    if v is None or v == "":
        return ""
    if isinstance(v, (int, float)):                # il numero seriale di Sheets (giorni dal 30/12/1899)
        return (datetime.date(1899, 12, 30) + datetime.timedelta(days=int(v))).isoformat()
    t = str(v).strip()
    m = re.fullmatch(r"(\d{1,2})[/.\-](\d{1,2})[/.\-](\d{2,4})", t)
    if m:
        g_, me, a = (int(x) for x in m.groups())
        try:
            return datetime.date(a + 2000 if a < 100 else a, me, g_).isoformat()
        except ValueError:
            return t
    m = re.fullmatch(r"(\d{4})-(\d{2})-(\d{2})", t[:10])
    return t[:10] if m else t


def norma(campo, v):
    """Il valore di una cella di Dre come si salva e si confronta."""
    if campo in ("costo", "retainer"):
        return _numero(v)
    if campo in ("inizio", "fine"):
        return _data(v)
    return " ".join(str(v if v is not None else "").split()) if campo != "nota" else str(v if v is not None else "").strip()


def in_cella(campo, v):
    """Il valore come si scrive nella cella (USER_ENTERED): le date all'italiana, i numeri nudi."""
    if v == "" or v is None:
        return ""
    if campo in ("inizio", "fine") and re.fullmatch(r"\d{4}-\d{2}-\d{2}", str(v)):
        a, m, g_ = str(v).split("-")
        return f"{g_}/{m}/{a}"
    if isinstance(v, (int, float)):
        return v
    return testo(v)


def testo(v):
    """Un testo che non diventa mai una formula: un'azienda che si chiama «=...» o «+39...» resta testo."""
    t = " ".join(str(v or "").split()) if "\n" not in str(v or "") else str(v)
    return "'" + t if t[:1] in ("=", "+", "-", "@") else t


# ── lo stato del foglio nel database (snella_numeri, chiave «foglio») ──
# scritto: quello che il sistema ha messo nelle celle di Dre l'ultima volta (per capire cosa ha
# cambiato lui); dre: quello che ha scritto Dre, con la data (non si riscrive mai); mano: le fasi
# decise a mano; attesa: chi e' «In attesa di risposta»; call: gli appunti delle call gia' visti.

def carica_stato():
    r = sb("GET", "/rest/v1/snella_numeri?select=dati&chiave=eq.foglio") or []
    st = (r[0]["dati"] if r else None) or {}
    for k in ("scritto", "dre", "mano", "attesa", "call"):
        st.setdefault(k, {})
    return st


def salva_stato(st, fasi_app):
    if PROVA:
        return
    adesso_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
    sb("POST", "/rest/v1/snella_numeri?on_conflict=chiave", [
        {"chiave": "foglio", "dati": st, "aggiornato_il": adesso_iso},
        {"chiave": "fasi", "dati": fasi_app, "aggiornato_il": adesso_iso}],
       {"Prefer": "resolution=merge-duplicates,return=minimal"})


# ── i dati ────────────────────────────────────────────────────────────

CAMPI_P = ("id,company,name,email,stage,pipeline_stage,fuori,classificazione,analysis_sent,analysis_sent_at,"
           "last_reply_at,awaiting_us,prova_inizio,prova_fine,sg_id")


def _pezzi(ids, n=80):
    ids = sorted(i for i in ids if i)
    for i in range(0, len(ids), n):
        yield ",".join(ids[i:i + n])


def leggi_dati():
    schede = {r["prospect_id"]: r for r in sb_tutte(
        "/rest/v1/snella_schede?select=prospect_id,azienda,stato,ultima_risposta,analisi:scheda->analisi,"
        "aspetta:scheda->aspetta_noi,da_chiamare", chiave="prospect_id")}
    # chi ha mostrato interesse: la lettura del segnale (si', caldo), gia' fatta dall'AI
    interesse = {r["prospect_id"] for r in sb_tutte("/rest/v1/segnali_provvisori?select=id,prospect_id,tipo,come&tipo=in.(si,caldo)")
                 if r.get("come") != "prova" and r.get("prospect_id")}
    dec = {r["prospect_id"]: r for r in sb_tutte("/rest/v1/snella_lead?select=*", chiave="prospect_id")}
    clienti = {r["prospect_id"]: r for r in sb_tutte("/rest/v1/clienti?select=prospect_id,dal,stato", chiave="prospect_id")}
    # basta il calendario di Dre (deciso il 19/10: le call le fa sempre lui)
    agenda = sb_tutte("/rest/v1/agenda?select=id,at,tipo,prospect_id,titolo&fonte=eq.gcal&prospect_id=not.is.null")
    ps = {p["id"]: p for p in sb_tutte(f"/rest/v1/prospects?select={CAMPI_P}&or=(pipeline_stage.not.is.null,stage.eq.cliente)")}
    servono = (set(schede) | set(dec) | set(clienti) | {a["prospect_id"] for a in agenda if a.get("tipo") in CALL}) - set(ps)
    for pezzo in _pezzi(servono):
        for p in sb("GET", f"/rest/v1/prospects?select={CAMPI_P}&id=in.({pezzo})") or []:
            ps[p["id"]] = p
    canone = {r["prospect_id"]: r.get("canone") for r in sb_tutte("/rest/v1/soldi_clienti?select=prospect_id,canone",
                                                                     chiave="prospect_id") if r.get("canone")}
    valori = {int(r["progetto_id"]): r.get("valore") for r in sb_tutte("/rest/v1/soldi_progetti?select=progetto_id,valore",
                                                                      chiave="progetto_id")}
    retainer, prova_costo = {}, {}
    for pr in sb_tutte("/rest/v1/progetti?select=id,prospect_id,tipo,stato,valore,data_inizio,scadenza"):
        v = valori.get(int(pr["id"])) or pr.get("valore")
        if not pr.get("prospect_id") or not v or pr.get("stato") in ("chiuso", "fatto", "concluso"):
            continue
        if pr.get("tipo") == "retainer":
            retainer[pr["prospect_id"]] = retainer.get(pr["prospect_id"], 0) + v
        elif pr.get("tipo") == "trial":
            prova_costo[pr["prospect_id"]] = v
    for pid, c in canone.items():
        retainer[pid] = c                          # il canone sulla scheda vince sui progetti
    return {"ps": ps, "schede": schede, "dec": dec, "clienti": clienti, "agenda": agenda, "interesse": interesse,
            "retainer": retainer, "prova_costo": prova_costo}


def chiave_nome(nome):
    """Un nome d'azienda come si confronta: minuscolo, senza accenti, spazi e punteggiatura."""
    import unicodedata
    piatto = unicodedata.normalize("NFKD", str(nome or "")).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]", "", piatto.lower())


def chiave_azienda(p):
    """La stessa azienda con piu' contatti sta su una riga sola (tre contatti di un cliente)."""
    return chiave_nome(p.get("company")) or p["id"]


def nome_azienda(p, s=None):
    return " ".join(((s or {}).get("azienda") or p.get("company") or p.get("name") or p.get("email") or "?").split())


# ── la fase di un lead ────────────────────────────────────────────────

def _stato12(s, d):
    """Lo stato fra i 12: quello scelto da Dre nell'app, se no quello della scheda."""
    nomi = {x["nome"] for x in _ST["stati"]}
    v = (d or {}).get("stato") or (s or {}).get("stato")
    return v if v in nomi else _ST["dai_vecchi"].get(v or "", None)


def fase_di(p, s, d, call, cliente, mano, interesse=False, ora=None):
    """(fase, etichetta fuori percorso). Una sola delle due. L'ordine:
    1. la fase decisa a mano da Dre (foglio), se dopo non ha cambiato lo stato nell'app;
    2. i chiusi (non contattare, perso, no);  3. prova e cliente;
    4. le call nel calendario di Dre (la piu' avanti fra conoscitiva, tecnica, avvio);
    5. in attesa, fuori ufficio, mai risposto;  6. dalla posta: analisi da fare, inviata, conversazione."""
    d = d or {}
    if mano:
        cambiata_dopo = d.get("aggiornato_il") and quando(d["aggiornato_il"]) > quando(mano["il"]) + datetime.timedelta(minutes=2)
        if not cambiata_dopo:
            return (None, FUORI["Perso"]) if mano["fase"] == TOGLI else (mano["fase"], None)
    stato = _stato12(s, d)
    ps = p.get("pipeline_stage")
    if p.get("classificazione") in ("soppresso", "nervoso") or stato == "Non contattare":
        return None, FUORI["Non contattare"]
    if ps == "perso" or stato == "Perso" or (p.get("stage") == "perso" and not cliente):
        return None, FUORI["Perso"]
    if stato == "Non interessato":
        return None, FUORI["Non interessato"]
    if ps == "prova":
        return PROVA_F, None
    if cliente or ps == "cliente" or p.get("stage") == "cliente" or stato == "Cliente acquisito":
        return CLIENTE, None
    # le call del calendario degli ultimi 45 giorni (o future): una call di maggio senza seguito non e'
    # una trattativa aperta, e' un lead fermo (la pipeline del Workspace, se c'e', vale comunque)
    ora = ora or datetime.datetime.now(datetime.timezone.utc)
    livelli = [LIVELLO[CALL[a["tipo"]]] for a in call
               if a.get("tipo") in CALL and quando(a["at"]) >= ora - datetime.timedelta(days=CALL_GIORNI)]
    if ps in CALL:
        livelli.append(LIVELLO[CALL[ps]])
    if stato in ("Call fissata", "Proposta inviata"):
        livelli.append(LIVELLO[FASE_DI_STATO[stato]])
    if livelli:
        return (CONO, TECN, AVVIO)[max(livelli)], None
    if stato in ("Assente", "Da ricontattare", "Nessuna risposta"):
        return None, FUORI[stato]
    risposta = (s or {}).get("ultima_risposta") or p.get("last_reply_at")
    if not risposta:
        return None, FUORI["Nessuna risposta"]
    if quando(risposta) < ora - datetime.timedelta(days=FERMO_GIORNI):
        return None, FERMI                         # niente da due mesi: non e' una trattativa aperta
    inviata = analisi_il(p, s)
    if inviata:
        return (CONV if quando(risposta) > inviata + datetime.timedelta(minutes=5) else INVIATA), None
    # senza analisi: nel percorso solo chi ha mostrato interesse (la lettura dell'AI, la
    # classificazione, «da chiamare»). Le altre risposte (autorisposte, «non ci interessa» non
    # ancora classificati, persone sbagliate) stanno nei conteggi: il 19/10 erano 45 su 51.
    if not (interesse or p.get("classificazione") == "positivo" or (s or {}).get("da_chiamare") or stato == "Da chiamare"):
        return None, ALTRE
    if (s or {}).get("aspetta") is False and not p.get("awaiting_us"):
        return CONV, None                          # gli abbiamo gia' risposto senza l'analisi: la segue Dre
    return PREP, None


def analisi_il(p, s):
    if p.get("analysis_sent_at"):
        return quando(p["analysis_sent_at"])
    an = (s or {}).get("analisi") or {}
    if an.get("mandata") and an.get("il"):
        return quando(an["il"])
    return None


# ── le righe ──────────────────────────────────────────────────────────

def _giorno_corto(dt, ora):
    r = dt.astimezone(ROMA)
    oggi = ora.astimezone(ROMA).date()
    if r.date() == oggi:
        return f"oggi {r:%H:%M}"
    if r.date() == oggi - datetime.timedelta(days=1):
        return f"ieri {r:%H:%M}"
    return f"{r:%d/%m}"


def _dettaglio_call(call, fase, ora):
    tipo = {v: k for k, v in CALL.items()}[fase]
    tutte = sorted((quando(a["at"]) for a in call if a.get("tipo") == tipo))
    future = [t for t in tutte if t >= ora - datetime.timedelta(hours=1)]
    if future:
        r = future[0].astimezone(ROMA)
        return f"{GIORNI[r.weekday()]} {r:%d/%m %H:%M}", future[0]
    if tutte:
        return f"fatta {tutte[-1].astimezone(ROMA):%d/%m}", tutte[-1]
    return "", None


def valore_dre(st, pids, campo):
    """Quello che Dre ha scritto in una cella, per uno qualunque dei contatti dell'azienda (il piu' recente)."""
    scelte = [st["dre"][pid][campo] for pid in pids if campo in st["dre"].get(pid, {})]
    return max(scelte, key=lambda x: x.get("il") or "")["v"] if scelte else None


def calcola(dati, st, ora):
    """Le righe di ogni fase e i conteggi. Torna (per_fase {fase: [riga]}, fasi_app {pid: fase o etichetta})."""
    ps, schede, dec = dati["ps"], dati["schede"], dati["dec"]
    call_di = {}
    for a in dati["agenda"]:
        call_di.setdefault(a["prospect_id"], []).append(a)
    gruppi = {}
    fasi_app = {}
    for pid, p in ps.items():
        s, d = schede.get(pid), dec.get(pid)
        cliente = pid in dati["clienti"]
        f, fuori = fase_di(p, s, d, call_di.get(pid, []), cliente, st["mano"].get(pid), pid in dati["interesse"], ora)
        fasi_app[pid] = f or fuori
        gruppi.setdefault(chiave_azienda(p), []).append((pid, f, fuori))
    per_fase = {f: [] for f in FASI}
    for chiave, membri in gruppi.items():
        dentro = [(pid, f) for pid, f, _ in membri if f]
        if not dentro:
            continue
        # il contatto che si vede: il piu' avanti nel percorso, poi il piu' recente
        def peso(x):
            p, s = ps[x[0]], schede.get(x[0]) or {}
            return (FASI.index(x[1]), (s.get("ultima_risposta") or p.get("last_reply_at") or ""))
        pid, fase = max(dentro, key=peso)
        pids = [m[0] for m in membri]
        for altro in pids:
            fasi_app[altro] = fase
        p, s = ps[pid], schede.get(pid) or {}
        riga = {"id": pid, "pids": pids, "azienda": nome_azienda(p, s), "fase": fase}
        risposta = s.get("ultima_risposta") or p.get("last_reply_at")
        if fase in (PREP, CONV):
            t = quando(risposta) if risposta else None
            riga["dettaglio"], riga["ordine"] = (_giorno_corto(t, ora) if t else ""), t
        elif fase == INVIATA:
            t = analisi_il(p, s)
            riga["dettaglio"], riga["ordine"] = (_giorno_corto(t, ora) if t else ""), t
        elif fase in LIVELLO:
            tutte = [a for x in pids for a in call_di.get(x, [])]
            riga["dettaglio"], riga["ordine"] = _dettaglio_call(tutte, fase, ora)
        # le celle di Dre: quello che ha scritto lui, se no quello che sa il sistema
        sistema = {"sposta": "", "nota": "", "scelta": "",
                   "costo": next((dati["prova_costo"][x] for x in pids if x in dati["prova_costo"]), ""),
                   "inizio": p.get("prova_inizio") or "", "fine": p.get("prova_fine") or "",
                   "retainer": next((dati["retainer"][x] for x in pids if dati["retainer"].get(x)), "")}
        for campo in DI_DRE:
            v = valore_dre(st, pids, campo)
            riga[campo] = norma(campo, sistema[campo]) if v is None else v
        if fase == PROVA_F:
            riga["ordine"] = riga["fine"] or "9999"
        elif fase == CLIENTE:
            dal = next((dati["clienti"][x].get("dal") for x in pids if x in dati["clienti"] and dati["clienti"][x].get("dal")), None)
            riga["ordine"] = dal or ""
        per_fase[fase].append(riga)
    vecchio = datetime.datetime(1970, 1, 1, tzinfo=datetime.timezone.utc)
    for fase, righe in per_fase.items():
        if fase == PROVA_F:
            righe.sort(key=lambda r: (str(r["ordine"]), r["azienda"].lower()))          # la scadenza piu' vicina in cima
        elif fase == CLIENTE:
            righe.sort(key=lambda r: (str(r["ordine"]), r["azienda"].lower()), reverse=True)
        else:
            righe.sort(key=lambda r: (r.get("ordine") or vecchio, r["azienda"].lower()), reverse=True)  # il piu' nuovo in cima
    return per_fase, fasi_app


# ── le scritture di Dre ───────────────────────────────────────────────

def effetti(campo, valore, oggi):
    """Cosa fa nel database una scelta di Dre: [(tabella, cosa)]. Pura, senza scrivere (la provano
    le invarianti). Mai una mail: solo lo stato, le note e le date. tabella in prospects,
    snella_lead, snella_note; «mano» e' la fase a mano del foglio, «attesa» il promemoria."""
    adesso_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
    perso = [("prospects", {"stage": "perso", "pipeline_stage": "perso"}),
             ("snella_lead", {"stato": "Perso"})]
    if campo == "sposta":
        if valore == "":
            return [("mano", None)]
        if valore == TOGLI:
            return perso + [("mano", TOGLI)]
        if valore not in FASI:
            return []
        out = [("mano", valore)]
        pipeline = {CONO: "conoscitiva", TECN: "tecnica", AVVIO: "avvio", PROVA_F: "prova", CLIENTE: "cliente"}.get(valore)
        if pipeline:
            patch = {"pipeline_stage": pipeline, "fuori": True}
            if valore == CLIENTE:
                patch["stage"] = "cliente"
            out.append(("prospects", patch))
        stato = {PREP: "Da rispondere", INVIATA: "Analisi inviata", CONO: "Call fissata", TECN: "Call fissata",
                 AVVIO: "Call fissata", PROVA_F: "Cliente acquisito", CLIENTE: "Cliente acquisito"}.get(valore)
        if stato:
            out.append(("snella_lead", {"stato": stato}))
        return out
    if campo == "scelta":
        if valore == "Perso":
            return perso + [("mano", TOGLI)]
        if valore == "Da chiamare":
            return [("snella_lead", {"stato": "Da chiamare", "chiamata": "richiamare", "chiamata_il": adesso_iso,
                                     "richiamare_il": oggi.isoformat()}), ("attesa", None)]
        if valore == "In attesa di risposta":
            return [("snella_lead", {"prossima_mossa": "Aspettare la sua risposta (dal foglio)", "responsabile": "Dramane",
                                     "prossima_il": (oggi + datetime.timedelta(days=ATTESA_GIORNI)).isoformat()}),
                    ("attesa", adesso_iso)]
        return [("attesa", None)]
    if campo == "nota":
        return [("snella_note", {"testo": valore, "tipo": "nota", "autore_nome": "Dramane"})] if valore else []
    if campo in ("inizio", "fine"):
        if valore and not re.fullmatch(r"\d{4}-\d{2}-\d{2}", str(valore)):
            return []
        return [("prospects", {f"prova_{campo}": valore or None})]
    if campo == "retainer":
        return [("prospects", {"canone": valore})] if isinstance(valore, (int, float)) else []
    return []                                      # il costo della prova sta solo nel foglio (e qui nel database)


def scritture_di_dre(celle, st):
    """Le celle diverse da quello che il sistema ci aveva scritto: le ha scritte Dre.
    celle: {pid: {campo: valore gia' normalizzato}}. Torna [(pid, campo, valore)]."""
    out = []
    for pid, campi in celle.items():
        prima = st["scritto"].get(pid)
        if prima is None:
            continue                               # una riga che il sistema non ha mai scritto: non si indovina
        for campo, v in campi.items():
            if v != prima.get(campo, ""):
                out.append((pid, campo, v))
    return out


def applica(scritte, dati, st, ora):
    """Salva le scritture di Dre (vincono per sempre) e ne fa gli effetti sul database."""
    oggi = ora.astimezone(ROMA).date()
    righe = []
    gruppo = {}
    for pid, p in dati["ps"].items():
        gruppo.setdefault(chiave_azienda(p), []).append(pid)
    for pid, campo, v in scritte:
        p = dati["ps"].get(pid) or {"id": pid}
        pids = gruppo.get(chiave_azienda(p), [pid]) if pid in dati["ps"] else [pid]
        azienda = nome_azienda(p, dati["schede"].get(pid))
        righe.append(f"  Dre ha scritto «{campo}» = {str(v)[:60]!r} su {azienda}")
        if PROVA:
            continue
        il = datetime.datetime.now(datetime.timezone.utc).isoformat()
        for x in pids:
            st["dre"].setdefault(x, {})[campo] = {"v": v, "il": il}
        for tabella, cosa in effetti(campo, v, oggi):
            if tabella == "prospects":
                for x in pids:
                    sb("PATCH", f"/rest/v1/prospects?id=eq.{x}", cosa)
            elif tabella == "snella_lead":
                sb("POST", "/rest/v1/snella_lead?on_conflict=prospect_id", [{"prospect_id": x, **cosa} for x in pids],
                   {"Prefer": "resolution=merge-duplicates,return=minimal"})
            elif tabella == "snella_note":
                sb("POST", "/rest/v1/snella_note", {"prospect_id": pid, **cosa}, {"Prefer": "return=minimal"})
            elif tabella == "mano":
                for x in pids:
                    if cosa is None:
                        st["mano"].pop(x, None)
                    else:
                        # dopo le scritture qui sopra: l'app ha l'ora di adesso, la fase a mano la stessa
                        st["mano"][x] = {"fase": cosa, "il": datetime.datetime.now(datetime.timezone.utc).isoformat(), "da": "foglio"}
            elif tabella == "attesa":
                for x in pids:
                    if cosa is None:
                        st["attesa"].pop(x, None)
                    else:
                        st["attesa"][x] = {"il": cosa, "ricordato": False}
    return righe


# ── la settimana ──────────────────────────────────────────────────────

def settimana(ora):
    r = ora.astimezone(ROMA)
    lun = (r - datetime.timedelta(days=r.weekday())).replace(hour=0, minute=0, second=0, microsecond=0)
    return lun, lun + datetime.timedelta(days=7)


def titolo_settimana(ora):
    lun, _ = settimana(ora)
    dom = lun + datetime.timedelta(days=6)
    n = lun.isocalendar()[1]
    if lun.month == dom.month:
        return f"Settimana {n} · {lun.day}-{dom.day} {MESI[lun.month - 1]}"
    return f"Settimana {n} · {lun.day} {MESI[lun.month - 1]} - {dom.day} {MESI[dom.month - 1]}"


def _z(t):
    return t.astimezone(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def migliaia(n):
    return f"{int(round(n or 0)):,}".replace(",", ".")


def euro(n):
    return migliaia(n) + " €"


# ── il foglio ─────────────────────────────────────────────────────────

def _g(metodo, url, corpo=None):
    from google_api import g
    return g(metodo, url, corpo, email=DRE)


def sheets_acceso():
    try:
        _g("GET", f"{SHEETS}/0000000000000000000000000000000000000000000?fields=spreadsheetId")
    except RuntimeError as e:
        return "has not been used" not in str(e) and "is disabled" not in str(e) and "SERVICE_DISABLED" not in str(e)
    return True


def trova_foglio(st):
    """Il foglio nella cartella «2 Commerciale»: quello ricordato, o quello col nome giusto, o nessuno."""
    if st.get("foglio_id"):
        try:
            f = _g("GET", f"{DRIVE}/files/{st['foglio_id']}?supportsAllDrives=true&fields=id,trashed")
            if not f.get("trashed"):
                return st["foglio_id"]
        except RuntimeError:
            pass
    from google_api import drive_cerca
    q = (f"'{COMMERCIALE}' in parents and name = '{NOME_FOGLIO}' and "
         "mimeType = 'application/vnd.google-apps.spreadsheet' and trashed = false")
    trovati = drive_cerca(q, campi="id,name", email=DRE)
    return trovati[0]["id"] if trovati else None


def crea_foglio():
    f = _g("POST", f"{DRIVE}/files?supportsAllDrives=true&fields=id,webViewLink",
           {"name": NOME_FOGLIO, "mimeType": "application/vnd.google-apps.spreadsheet", "parents": [COMMERCIALE]})
    print(f"foglio: creato {f.get('webViewLink')}")
    return f["id"]


def rgb(h):
    h = h.lstrip("#")
    return {"red": int(h[0:2], 16) / 255, "green": int(h[2:4], 16) / 255, "blue": int(h[4:6], 16) / 255}


NAVY, INCHIOSTRO, TENUE, BORDO, GIALLO = "#1c2e6e", "#17191f", "#5b6170", "#e5e7ec", "#fff8db"
FONT = "Plus Jakarta Sans"


def _campo(sheet, r0, r1, c0, c1):
    return {"sheetId": sheet, "startRowIndex": r0, "endRowIndex": r1, "startColumnIndex": c0, "endColumnIndex": c1}


def _formato(rng, **f):
    campi = []
    cella = {}
    if "fondo" in f:
        cella["backgroundColor"] = rgb(f["fondo"]); campi.append("backgroundColor")
    tf = {}
    for k, v in (("colore", "foregroundColor"), ("grassetto", "bold"), ("dim", "fontSize"), ("corsivo", "italic")):
        if k in f:
            tf[v] = rgb(f[k]) if k == "colore" else f[k]
    if tf:
        tf["fontFamily"] = FONT
        cella["textFormat"] = tf; campi.append("textFormat")
    for k, nome in (("oriz", "horizontalAlignment"), ("vert", "verticalAlignment"), ("a_capo", "wrapStrategy")):
        if k in f:
            cella[nome] = f[k]; campi.append(nome)
    if "numero" in f:
        cella["numberFormat"] = f["numero"]; campi.append("numberFormat")
    return {"repeatCell": {"range": rng, "cell": {"userEnteredFormat": cella},
                           "fields": ",".join("userEnteredFormat." + c for c in campi)}}


def forma(sid, st):
    """La forma del foglio: una scheda «Pipeline» nuova, poi via le vecchie. Si fa alla nascita e
    quando cambia LAYOUT (dopo aver letto le scritture di Dre, che stanno nel database)."""
    info = _g("GET", f"{SHEETS}/{sid}?fields=sheets.properties")
    vecchie = [s["properties"]["sheetId"] for s in info.get("sheets", [])]
    nuovo = max(vecchie + [0]) + 1
    R = []
    R.append({"updateSpreadsheetProperties": {
        "properties": {"title": NOME_FOGLIO, "locale": "it_IT", "timeZone": "Europe/Rome",
                       "defaultFormat": {"textFormat": {"fontFamily": FONT, "fontSize": 10, "foregroundColor": rgb(INCHIOSTRO)},
                                         "verticalAlignment": "MIDDLE"}},
        "fields": "title,locale,timeZone,defaultFormat.textFormat,defaultFormat.verticalAlignment"}})
    R.append({"addSheet": {"properties": {"sheetId": nuovo, "title": f"{SCHEDA} {nuovo}", "index": 0,
                                          "tabColor": rgb(NAVY),
                                          "gridProperties": {"rowCount": RIGHE, "columnCount": NCOL, "frozenRowCount": PRIMA - 1,
                                                             "hideGridlines": True}}}})
    for v in vecchie:
        R.append({"deleteSheet": {"sheetId": v}})
    R.append({"updateSheetProperties": {"properties": {"sheetId": nuovo, "title": SCHEDA}, "fields": "title"}})
    S = nuovo
    # le larghezze, le colonne nascoste (l'id) e i separatori
    for b in BLOCCHI:
        for i, (campo, w) in enumerate(zip(b["campi"], b["larghezze"])):
            c = b["da"] + i
            R.append({"updateDimensionProperties": {"range": {"sheetId": S, "dimension": "COLUMNS", "startIndex": c, "endIndex": c + 1},
                                                    "properties": {"pixelSize": w, "hiddenByUser": campo == "id"},
                                                    "fields": "pixelSize,hiddenByUser"}})
        fine = b["da"] + len(b["campi"])
        if fine < NCOL:
            R.append({"updateDimensionProperties": {"range": {"sheetId": S, "dimension": "COLUMNS", "startIndex": fine, "endIndex": fine + 1},
                                                    "properties": {"pixelSize": 14}, "fields": "pixelSize"}})
    for r, h in ((0, 44), (1, 44), (2, 26)):
        R.append({"updateDimensionProperties": {"range": {"sheetId": S, "dimension": "ROWS", "startIndex": r, "endIndex": r + 1},
                                                "properties": {"pixelSize": h}, "fields": "pixelSize"}})
    R.append({"updateDimensionProperties": {"range": {"sheetId": S, "dimension": "ROWS", "startIndex": PRIMA - 1, "endIndex": RIGHE},
                                            "properties": {"pixelSize": 28}, "fields": "pixelSize"}})
    # le unioni: la riga in alto (titolo, settimana, come si usa) e le intestazioni delle fasi
    b = BLOCCHI
    fine_b = lambda x: x["da"] + len(x["campi"])                       # noqa: E731
    unioni = [(0, b[0]["da"], fine_b(b[1])), (0, b[2]["da"], fine_b(b[3])), (0, b[4]["da"], NCOL)]
    for x in b:
        unioni.append((1, x["da"], fine_b(x)))
    for r, c0, c1 in unioni:
        R.append({"mergeCells": {"range": _campo(S, r, r + 1, c0, c1), "mergeType": "MERGE_ALL"}})
    # i caratteri e i colori
    R.append(_formato(_campo(S, 0, 1, 0, fine_b(b[1])), colore=NAVY, grassetto=True, dim=20))
    R.append(_formato(_campo(S, 0, 1, b[2]["da"], fine_b(b[3])), colore=INCHIOSTRO, grassetto=True, dim=13))
    R.append(_formato(_campo(S, 0, 1, b[4]["da"], NCOL), colore=TENUE, dim=10, oriz="RIGHT", a_capo="WRAP"))
    for x in b:
        info_f = INFO_FASE[x["fase"]]
        testo_testa = "#17191f" if x["fase"] == PROVA_F else "#ffffff"
        R.append(_formato(_campo(S, 1, 2, x["da"], fine_b(x)), fondo=info_f["colore"], colore=testo_testa, grassetto=True, dim=13, a_capo="WRAP"))
        R.append(_formato(_campo(S, 2, 3, x["da"], fine_b(x)), fondo=info_f["fondo"], colore=info_f["testo"], grassetto=True, dim=9))
        R.append(_formato(_campo(S, PRIMA - 1, RIGHE, x["da"], fine_b(x)), dim=10, colore=INCHIOSTRO, a_capo="CLIP"))
        R.append(_formato(_campo(S, PRIMA - 1, RIGHE, x["da"], x["da"] + 1), grassetto=True, dim=10, colore=INCHIOSTRO))
        for campo in x["campi"]:
            c = colonna(x, campo)
            rng = _campo(S, PRIMA - 1, RIGHE, c, c + 1)
            if campo == "dettaglio":
                R.append(_formato(rng, colore=TENUE, dim=9))
            if campo in ("costo", "retainer"):
                R.append(_formato(rng, numero={"type": "CURRENCY", "pattern": '#,##0 "€"'}, oriz="RIGHT"))
            if campo in ("inizio", "fine"):
                R.append(_formato(rng, numero={"type": "DATE", "pattern": "dd/mm/yyyy"}))
            # le tendine e i controlli sulle celle di Dre
            regola = None
            if campo == "scelta":
                regola = {"condition": {"type": "ONE_OF_LIST", "values": [{"userEnteredValue": v} for v in SCELTE]},
                          "strict": True, "showCustomUi": True}
            elif campo in ("inizio", "fine"):
                regola = {"condition": {"type": "DATE_IS_VALID"}, "strict": True,
                          "inputMessage": "Una data, per esempio 21/10/2026"}
            elif campo in ("costo", "retainer"):
                regola = {"condition": {"type": "NUMBER_GREATER_THAN_EQ", "values": [{"userEnteredValue": "0"}]}, "strict": True,
                          "inputMessage": "Euro, solo il numero (es. 1500)"}
            if regola:
                R.append({"setDataValidation": {"range": rng, "rule": regola}})
            # le celle di Dre si colorano di giallo quando nella riga c'e' un lead
            if campo in DI_DRE:
                prima_az = f"${lettera(x['da'])}{PRIMA}"
                R.append({"addConditionalFormatRule": {"index": 0, "rule": {
                    "ranges": [rng], "booleanRule": {"condition": {"type": "CUSTOM_FORMULA", "values": [{"userEnteredValue": f'={prima_az}<>""'}]},
                                                     "format": {"backgroundColor": rgb(GIALLO)}}}}})
        # una riga sottile fra un lead e l'altro, solo dove c'e' un lead
        R.append({"addConditionalFormatRule": {"index": 0, "rule": {
            "ranges": [_campo(S, PRIMA - 1, RIGHE, x["da"], x["da"] + 1)],
            "booleanRule": {"condition": {"type": "NOT_BLANK"}, "format": {"textFormat": {"bold": True}}}}}})
        # l'effetto a celle (Dre, 19/10 sera: «lascia l'effetto a celle»): una riga sottile fra un
        # lead e l'altro in ogni blocco, come nella prima versione
        R.append({"updateBorders": {"range": _campo(S, 1, RIGHE, x["da"], fine_b(x)),
                                    "innerHorizontal": {"style": "SOLID", "color": rgb(BORDO)},
                                    "bottom": {"style": "SOLID", "color": rgb(BORDO)}}})
    # le celle del sistema: un avviso se Dre le tocca (si possono toccare, ma vengono riscritte)
    R.append({"addProtectedRange": {"protectedRange": {"range": _campo(S, 0, PRIMA - 1, 0, NCOL), "warningOnly": True,
                                                       "description": "Lo scrive il sistema ogni 10 minuti"}}})
    for x in b:
        for campo in x["campi"]:
            if campo not in DI_DRE and campo != "azienda":          # l'azienda la tocca Dre per spostare o togliere
                c = colonna(x, campo)
                R.append({"addProtectedRange": {"protectedRange": {"range": _campo(S, PRIMA - 1, RIGHE, c, c + 1), "warningOnly": True,
                                                                   "description": "Lo scrive il sistema ogni 10 minuti: scrivi nelle celle gialle"}}})
    _g("POST", f"{SHEETS}/{sid}:batchUpdate", {"requests": R})
    st["layout"] = LAYOUT
    st["scritto"] = {}                             # il foglio e' nuovo: le celle di Dre si riscrivono dal database
    print(f"foglio: forma fatta ({len(R)} istruzioni)")


def leggi_celle(sid):
    """Le celle di Dre del foglio, per lead: {pid: {campo: valore normalizzato}}."""
    rng = [f"{SCHEDA}!{lettera(b['da'])}{PRIMA}:{lettera(b['da'] + len(b['campi']) - 1)}{RIGHE}" for b in BLOCCHI]
    q = "&".join("ranges=" + urllib.parse.quote(r) for r in rng)
    d = _g("GET", f"{SHEETS}/{sid}/values:batchGet?{q}&valueRenderOption=UNFORMATTED_VALUE&dateTimeRenderOption=FORMATTED_STRING")
    out, incollati, tolti = {}, [], []
    for b, vr in zip(BLOCCHI, d.get("valueRanges", [])):
        for riga in vr.get("values", []):
            riga = riga + [""] * (len(b["campi"]) - len(riga))
            pid = str(riga[b["campi"].index("id")]).strip()
            azienda = " ".join(str(riga[b["campi"].index("azienda")] or "").split())
            if not re.fullmatch(r"[0-9a-f\-]{36}", pid):
                if azienda:
                    incollati.append((b["fase"], azienda))        # un nome senza id: l'ha scritto Dre
                continue
            if not azienda:
                tolti.append(pid)                                  # il nome cancellato da una riga del sistema
            out[pid] = {c: norma(c, riga[i]) for i, c in enumerate(b["campi"]) if c in DI_DRE}
    return out, incollati, tolti


def leggi_celle_v1(sid):
    """Le celle di Dre della forma vecchia (LAYOUT 1: elenchi dalla riga 9, colonna «Sposta in» prima
    della nota): si leggono una volta sola, prima di rifare il foglio, cosi' niente di suo si perde."""
    campi_v1 = []
    for b in BLOCCHI:
        c = list(b["campi"])
        c.insert(c.index("nota"), "sposta")
        campi_v1.append(c)
    da = 0
    rng = []
    for c in campi_v1:
        rng.append(f"{SCHEDA}!{lettera(da)}9:{lettera(da + len(c) - 1)}{RIGHE}")
        da += len(c) + 1
    q = "&".join("ranges=" + urllib.parse.quote(r) for r in rng)
    d = _g("GET", f"{SHEETS}/{sid}/values:batchGet?{q}&valueRenderOption=UNFORMATTED_VALUE&dateTimeRenderOption=FORMATTED_STRING")
    out = {}
    for c, vr in zip(campi_v1, d.get("valueRanges", [])):
        for riga in vr.get("values", []):
            riga = riga + [""] * (len(c) - len(riga))
            pid = str(riga[c.index("id")]).strip()
            if re.fullmatch(r"[0-9a-f\-]{36}", pid):
                out[pid] = {k: norma(k, riga[i]) for i, k in enumerate(c) if k in DI_DRE or k == "sposta"}
    return out


def mosse_di_dre(incollati, tolti, st, dati):
    """Gli spostamenti fatti col copia e incolla e i nomi cancellati. Torna ([(pid, SPOSTA, fase o TOGLI)],
    [(fase, nome) non abbinati]). Un nome incollato sotto una fase si abbina per chiave_azienda a un
    lead noto (prima chi sta gia' nel foglio); se e' gia' in quella fase non e' una mossa; se non si
    abbina a nessuno non si inventa niente: resta dov'e' e si dice nel log."""
    per_chiave = {}
    for pid, p in dati["ps"].items():
        per_chiave.setdefault(chiave_azienda(p), []).append(pid)
    mosse, ignoti = [], []
    for fase, nome in incollati:
        if fase not in FASI:
            continue
        pids = per_chiave.get(chiave_nome(nome)) or []
        nel_foglio = [x for x in pids if x in st["scritto"]]
        pid = (nel_foglio or pids or [None])[0]
        if not pid:
            ignoti.append((fase, nome))
            continue
        dove = (st["scritto"].get(pid) or {}).get("fase") or (st["mano"].get(pid) or {}).get("fase")
        if dove == fase:
            continue                                           # incollato dove sta gia': niente
        mosse.append((pid, SPOSTA, fase))
    for pid in tolti:
        if pid in st["scritto"] and (st["mano"].get(pid) or {}).get("fase") != TOGLI:
            mosse.append((pid, SPOSTA, TOGLI))
    return mosse, ignoti


def griglia(per_fase, mrr, ora, ignoti=()):
    """Tutto il foglio come righe di valori: la riga in alto, le intestazioni delle fasi, i titoli
    delle colonne, gli elenchi. I nomi incollati da Dre che non si abbinano restano in fondo alla loro
    colonna, senza id, finche' li toglie lui. Torna (righe, scritto)."""
    vuota = lambda: [""] * NCOL                                         # noqa: E731
    righe = [vuota() for _ in range(PRIMA - 1)]
    b = BLOCCHI
    righe[0][0] = NOME_FOGLIO
    righe[0][b[2]["da"]] = titolo_settimana(ora)
    r = ora.astimezone(ROMA)
    righe[0][b[4]["da"]] = f"Aggiornato {GIORNI[r.weekday()]} {r:%d/%m} alle {r:%H:%M}, ogni 10 minuti. {FRASE_USO}"
    for x in b:
        n = len(per_fase[x["fase"]])
        righe[1][x["da"]] = f"{x['fase']} · {n}" + (f" · MRR {euro(mrr)}" if x["fase"] == CLIENTE else "")
        for i, t in enumerate(x["titoli"]):
            righe[2][x["da"] + i] = "" if t == "id" else t
    liste = {f: list(v) for f, v in per_fase.items()}
    for fase, nome in ignoti:
        if fase in liste:
            liste[fase].append({"id": "", "azienda": nome, "ignoto": True})
    lunga = max((len(v) for v in liste.values()), default=0)
    scritto = {}
    for i in range(lunga):
        riga = vuota()
        for x in b:
            lista = liste[x["fase"]]
            if i >= len(lista):
                continue
            lead = lista[i]
            if lead.get("ignoto"):
                riga[x["da"]] = testo(lead["azienda"])
                continue
            for j, campo in enumerate(x["campi"]):
                v = lead.get(campo, "")
                riga[x["da"] + j] = in_cella(campo, v) if campo in DI_DRE else (lead["id"] if campo == "id" else testo(v))
            scritto[lead["id"]] = {**{c: lead.get(c, "") for c in x["campi"] if c in DI_DRE}, "fase": x["fase"]}
        righe.append(riga)
    return righe, scritto


def scrivi(sid, righe):
    ultima = lettera(NCOL - 1)
    _g("POST", f"{SHEETS}/{sid}/values:batchClear", {"ranges": [f"{SCHEDA}!A{PRIMA}:{ultima}{RIGHE}"]})
    _g("POST", f"{SHEETS}/{sid}/values:batchUpdate", {"valueInputOption": "USER_ENTERED", "data": [
        {"range": f"{SCHEDA}!A1:{ultima}{len(righe)}", "values": righe}]})


# ── «In attesa di risposta»: il promemoria dopo 5 giorni ──────────────

def promemoria_attesa(dati, st, ora):
    import segnale_provvisorio as SP
    fatti = 0
    for pid, a in list(st["attesa"].items()):
        if a.get("ricordato") or ora - quando(a["il"]) < datetime.timedelta(days=ATTESA_GIORNI):
            continue
        dopo = sb("GET", f"/rest/v1/interactions?select=id&prospect_id=eq.{pid}&kind=eq.email_in&at=gt.{_z(quando(a['il']))}&limit=1") or []
        p = dati["ps"].get(pid) or {"id": pid}
        azienda = nome_azienda(p, dati["schede"].get(pid))
        if dopo:
            a["ricordato"] = True                  # ha risposto: la conversazione e' ripartita, niente promemoria
            continue
        il = quando(a["il"]).astimezone(ROMA)
        print(f"  promemoria: {azienda} in attesa dal {il:%d/%m}")
        if PROVA:
            continue
        proponi("umano", f"{azienda}: nessuna risposta da {ATTESA_GIORNI} giorni", prospect_id=pid,
                perche=f"Nel foglio l'avevi messo «In attesa di risposta» il {il:%d/%m}. Lo chiami, gli scrivi o lo segni perso?",
                ref=f"foglio-attesa:{pid}:{a['il'][:10]}")
        SP.notifica(f"In attesa da {ATTESA_GIORNI} giorni: {azienda}", "Nessuna risposta dopo la tua scelta nel foglio. Lo chiami?", pid)
        a["ricordato"] = True
        fatti += 1
    return fatti


# ── le call di Dre: in «Chiamate», e l'avviso del link mancante ───────

DOMANDA_ACCORDO = """Sei l'assistente commerciale di Studio Galilei (agenzia Google Ads). Ti do gli appunti
(e la trascrizione, se c'e') di una {tipo} con un'azienda, fatta il {giorno}. Oggi e' il {oggi}.

Domanda: nella call vi siete accordati per la call successiva ({dopo}) con un giorno preciso?
- accordo: true solo se e' stato detto un giorno (una data, o «giovedi' prossimo», «martedi' 28»):
  allora scrivi la data in AAAA-MM-GG, calcolata dal giorno della call. Se si e' detto solo «ci
  risentiamo», «vi mando la proposta», «fissiamo piu' avanti», accordo e' false.
- tipo: «tecnica», «avvio» o «altro» (che call avete fissato).
- ora: HH:MM se detta, se no «».
- frase: la frase degli appunti che lo dice, breve e citata com'e'; «» se accordo e' false.

APPUNTI:
{testo}"""

SCHEMA_ACCORDO = {"type": "json_schema", "json_schema": {"name": "accordo", "strict": True, "schema": {
    "type": "object", "additionalProperties": False, "required": ["accordo", "tipo", "data", "ora", "frase"],
    "properties": {"accordo": {"type": "boolean"}, "tipo": {"type": "string", "enum": ["tecnica", "avvio", "altro"]},
                   "data": {"type": "string"}, "ora": {"type": "string"}, "frase": {"type": "string"}}}}}


def leggi_accordo(testo_call, tipo, giorno, oggi):
    import cervello
    dopo = "la call tecnica" if tipo == "conoscitiva" else "la call di avvio"
    prompt = DOMANDA_ACCORDO.format(tipo=f"call {tipo}", giorno=giorno.isoformat(), oggi=oggi.isoformat(), dopo=dopo,
                                    testo=" ".join(testo_call.split())[:14000])
    grezzo = cervello._chiedi_openai(prompt, cervello.MODELLO_OPENAI, formato=SCHEMA_ACCORDO, tetto=1500, sforzo="low")
    v = json.loads(grezzo) if isinstance(grezzo, str) else grezzo
    if not v.get("accordo") or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", v.get("data") or ""):
        return {"accordo": False}
    if datetime.date.fromisoformat(v["data"]) < giorno:
        return {"accordo": False, "nota": "data prima della call"}
    return {"accordo": True, "tipo": v.get("tipo") or "altro", "data": v["data"], "ora": v.get("ora") or "", "frase": (v.get("frase") or "")[:200]}


def call_di_dre(dati, st, ora):
    """Gli appunti di Gemini delle call di Dre degli ultimi 14 giorni: la copia in «Chiamate»
    (col nome della data, del tipo e dell'azienda), e dalle conoscitive e tecniche l'accordo sulla
    call dopo. Il lead si riconosce dall'evento del calendario di Dre alla stessa ora (che il
    calendario abbina per mail, dominio, sito e nome); se non e' uno solo, non si abbina."""
    from google_api import drive_cerca, drive_testo, drive_copia
    import appunti
    import calendario
    da = _z(ora - datetime.timedelta(days=14))
    q = (f"name contains 'Appunti di Gemini' and mimeType = 'application/vnd.google-apps.document' and "
         f"modifiedTime > '{da}' and trashed = false and '{DRE}' in owners")
    docs = drive_cerca(q, campi="id,name,webViewLink,createdTime", email=DRE)
    nuove = 0
    for doc in docs:
        gia = st["call"].get(doc["id"])
        if gia and gia.get("pid") and not gia.get("copia") and not PROVA:
            try:                                                 # la copia non era riuscita: si riprova
                gia["copia"] = drive_copia(doc["id"], gia["nome"][:200], CHIAMATE, email=DRE).get("id")
            except Exception as e:                               # noqa: BLE001
                print(f"    (copia in Chiamate non riuscita: {str(e)[:100]})")
        if gia or "(SG)" in doc["name"]:
            continue
        at = appunti.quando_dal_titolo(doc["name"])
        if not at:
            st["call"][doc["id"]] = {"saltata": "senza data"}
            continue
        vicini = [a for a in dati["agenda"] if abs((quando(a["at"]) - at).total_seconds()) <= 40 * 60]
        pids = {a["prospect_id"] for a in vicini}
        titolo = doc["name"].split(" - Appunti di Gemini")[0]
        tipo = next((a["tipo"] for a in vicini if a.get("tipo") in CALL), None) or calendario.tipo_di(titolo)
        di_lead = len(pids) == 1 or re.search(r"conoscitiv|tecnic|avvio", titolo, re.I)
        if not di_lead:
            st["call"][doc["id"]] = {"saltata": "riunione interna"}
            continue
        pid = next(iter(pids)) if len(pids) == 1 else None
        p = dati["ps"].get(pid) if pid else None
        if pid and not p:
            p = (sb("GET", f"/rest/v1/prospects?select={CAMPI_P}&id=eq.{pid}") or [None])[0]
        azienda = nome_azienda(p) if p else ""
        # Meet a volte lascia due documenti per la stessa call: uno basta
        stessa = f"{pid}|{at.isoformat()}" if pid else None
        if stessa and any(v.get("chiave") == stessa for v in st["call"].values()):
            st["call"][doc["id"]] = {"saltata": "doppione", "chiave": None}
            continue
        tipo_nome = {"conoscitiva": "Conoscitiva", "tecnica": "Tecnica", "avvio": "Avvio"}.get(tipo, "Chiamata")
        nome = f"{at:%Y-%m-%d} · {tipo_nome} · {azienda}" if azienda else f"{at:%Y-%m-%d} · {tipo_nome} · da abbinare · {titolo}"
        voce = {"pid": pid, "tipo": tipo, "at": at.isoformat(), "nome": nome, "chiave": stessa}
        print(f"  call: {nome[:90]}")
        if PROVA:
            continue
        try:
            voce["copia"] = drive_copia(doc["id"], nome[:200], CHIAMATE, email=DRE).get("id")
        except Exception as e:                                   # noqa: BLE001
            print(f"    (copia in Chiamate non riuscita: {str(e)[:100]})")
        if not pid:
            proponi("umano", f"Di chi e' la call «{titolo[:80]}»?", perche=(
                    "L'ho messa in «Chiamate», ma dal calendario non riconosco il lead con sicurezza. "
                    "Scrivimi l'azienda nella nota del lead o dimmelo in chat."), ref=f"call-senza-lead:{doc['id']}",
                    azione={"link": doc.get("webViewLink")})
        elif tipo in ("conoscitiva", "tecnica"):
            try:
                voce["accordo"] = leggi_accordo(drive_testo(doc["id"], email=DRE), tipo, at.date(), ora.astimezone(ROMA).date())
            except Exception as e:                               # noqa: BLE001
                print(f"    (accordo non letto, riprovo al giro dopo: {str(e)[:100]})")
                continue                                         # non si segna: si rilegge
        st["call"][doc["id"]] = voce
        nuove += 1
    return nuove


def link_mancanti(dati, st, ora):
    """Il giorno dopo la call: se vi siete accordati per la call successiva e in calendario non c'e',
    un avviso a Dre (in Oggi e sul telefono). Una volta sola per call; mai per una data gia' passata."""
    import segnale_provvisorio as SP
    oggi = ora.astimezone(ROMA).date()
    avvisi = 0
    for doc_id, v in st["call"].items():
        acc = v.get("accordo") or {}
        if not acc.get("accordo") or v.get("avvisato") or not v.get("pid"):
            continue
        at = datetime.datetime.fromisoformat(v["at"])
        if oggi < at.astimezone(ROMA).date() + datetime.timedelta(days=1) or datetime.date.fromisoformat(acc["data"]) < oggi:
            continue
        dopo = [a for a in sb("GET", f"/rest/v1/agenda?select=at,tipo&fonte=like.gcal*&prospect_id=eq.{v['pid']}"
                                     f"&at=gt.{_z(at + datetime.timedelta(minutes=60))}") or []]
        if dopo:
            v["avvisato"] = "in calendario"
            continue
        p = dati["ps"].get(v["pid"]) or {"id": v["pid"]}
        azienda = nome_azienda(p, dati["schede"].get(v["pid"]))
        giorno = datetime.date.fromisoformat(acc["data"])
        quando_detto = f"{GIORNI[giorno.weekday()]} {giorno:%d/%m}" + (f" alle {acc['ora']}" if acc.get("ora") else "")
        prossima = {"tecnica": "tecnica", "avvio": "di avvio"}.get(acc.get("tipo"), "successiva")
        print(f"  manca il link: {azienda}, call {prossima} {quando_detto}")
        if PROVA:
            continue
        proponi("umano", f"Manda il link della call {prossima} a {azienda}", prospect_id=v["pid"], perche=(
                f"Nella {v['tipo']} del {at.astimezone(ROMA):%d/%m} vi siete accordati per {quando_detto}"
                + (f": «{acc['frase'][:120]}»" if acc.get("frase") else "") + ". In calendario non c'e' ancora."),
                ref=f"link-mancante:{doc_id}")
        SP.notifica(f"Manca il link: {azienda}", f"Call {prossima} concordata per {quando_detto}, in calendario non c'e'", v["pid"])
        v["avvisato"] = ora.isoformat()
        avvisi += 1
    return avvisi


# ── il giro ───────────────────────────────────────────────────────────

def decisione_19_10(dati, st):
    """Dre, 19/10: i clienti di oggi vanno tutti nella colonna Cliente (quelli in prova li sposta lui).
    Una volta sola, come fase a mano: poi vince quello che fa Dre."""
    if st.get("clienti_19_10"):
        return
    il = datetime.datetime.now(datetime.timezone.utc).isoformat()
    for pid, p in dati["ps"].items():
        if pid in dati["clienti"] or p.get("stage") == "cliente" or p.get("pipeline_stage") in ("cliente", "prova"):
            if p.get("pipeline_stage") != "perso" and pid not in st["mano"]:
                st["mano"][pid] = {"fase": CLIENTE, "il": il, "da": "decisione di Dre del 19/10"}
    st["clienti_19_10"] = il


def main():
    ora = datetime.datetime.now(datetime.timezone.utc)
    t0 = time.time()
    st = carica_stato()
    dati = leggi_dati()
    decisione_19_10(dati, st)
    acceso = sheets_acceso()
    if not acceso:
        print("foglio: l'API di Google Sheets e' spenta nel progetto Google (686127567563): il foglio non si aggiorna")
    sid = trova_foglio(st) if acceso else None
    # 1. prima le scritture di Dre
    scritte, ignoti = [], []
    if sid and st.get("foglio_id") == sid and st.get("layout") in (1, LAYOUT):   # 1: si leggono le celle della forma vecchia prima di rifarla
        if st.get("layout") == LAYOUT:
            celle, incollati, tolti = leggi_celle(sid)
        else:
            celle, incollati, tolti = leggi_celle_v1(sid), [], []
        scritte = scritture_di_dre(celle, st)
        mosse, ignoti = mosse_di_dre(incollati, tolti, st, dati)
        scritte += mosse
        for fase, nome in ignoti:
            print(f"  incollato sotto «{fase}» ma non lo riconosco, lo lascio li': {nome[:60]}")
    for r in applica(scritte, dati, st, ora):
        print(r)
    if scritte and not PROVA:
        dati = leggi_dati()                        # gli effetti hanno cambiato le fasi
    # 2. poi il resto
    per_fase, fasi_app = calcola(dati, st, ora)
    mrr = sum(r["retainer"] for r in per_fase[CLIENTE] if isinstance(r["retainer"], (int, float)))
    print("foglio: " + " · ".join(f"{f} {len(per_fase[f])}" for f in FASI) + f" · MRR {euro(mrr)}")
    print("foglio: fuori dal percorso " + ", ".join(f"{x} {sum(1 for v in fasi_app.values() if v == x)}" for x in (ALTRE, FERMI)))
    righe, scritto = griglia(per_fase, mrr, ora, ignoti)
    if PROVA:
        print("(prova: non scrivo niente)")
    elif acceso:
        if not sid:
            sid = crea_foglio()
        if st.get("foglio_id") != sid or st.get("layout") != LAYOUT or "--rifai" in sys.argv:
            st["foglio_id"] = sid
            forma(sid, st)
        scrivi(sid, righe)
        st["scritto"] = scritto
        print(f"foglio: scritte {len(righe) - PRIMA + 1} righe, https://docs.google.com/spreadsheets/d/{sid}/edit")
    # 3. le call di Dre e i promemoria (anche se Sheets e' spento)
    try:
        n = call_di_dre(dati, st, ora)
        a = link_mancanti(dati, st, ora)
        print(f"call: {n} appunti nuovi in Chiamate, {a} avvisi di link mancante")
    except Exception as e:                                       # noqa: BLE001
        print(f"call: non lette ({str(e)[:160]})")
    print(f"attesa: {promemoria_attesa(dati, st, ora)} promemoria")
    salva_stato(st, fasi_app)
    print(f"foglio: giro in {int(time.time() - t0)}s")
    if not acceso:
        sys.exit("foglio: Google Sheets spento, serve accenderlo (console.cloud.google.com, progetto 686127567563)")


if __name__ == "__main__":
    main()
