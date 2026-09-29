#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""LA STANZA — le mani di Clara verso il database (7/9/2026).

Due cose sole: parlare con Supabase (sb) e mettere una proposta nella stanza
(proponi). Chi legge e capisce e' cervello.py; chi decide e' Dre. Questo
file e' solo la porta di servizio, e la usano sia la rilettura sia
l'ascoltatore, cosi' la scrittura di una proposta e' una e non due.
"""

import datetime
import json
import re
import sys
import os
import urllib.error
import urllib.parse
import urllib.request

RADICE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def quando(iso):
    """La data come la scrive il database, con QUALUNQUE numero di decimali.

    Postgres scrive i microsecondi senza zeri finali («...28.13447+00:00»), e
    Python sotto la 3.11 accetta solo tre o sei cifre: chi legge quella data
    finisce in ValueError. Il cloud gira su 3.12 e non se ne accorge, il Mac su
    3.9 sì, quindi il guasto si vede solo qui e sembra un mistero. Trovato il
    26/9 in salute.py, ritrovato il 28/9 nel direttore: sta qui perché lo usino
    tutti invece di riscoprirlo ogni volta.
    """
    t = re.sub(r"\.(\d{1,6})\d*", lambda m: "." + m.group(1).ljust(6, "0"), (iso or "").replace("Z", "+00:00"))
    return datetime.datetime.fromisoformat(t)


def env(nome):
    v = os.environ.get(nome)
    if v:
        return v
    for f in (".env.local", ".env"):
        p = os.path.join(RADICE, f)
        if not os.path.exists(p):
            continue
        for riga in open(p, encoding="utf-8"):
            if riga.strip().startswith(nome + "="):
                return riga.split("=", 1)[1].strip().strip("\"'")
    return None


URL = env("VITE_SUPABASE_URL")
CHIAVE = env("SUPABASE_SERVICE_KEY") or env("SUPABASE_SERVICE_ROLE_KEY")


def _chi_scrive():
    """Il nome di chi sta scrivendo, per il registro. Il modo ovvio (il nome del
    file lanciato) fallisce quando il codice parte con «python3 -c» o dentro un
    altro script: allora il nome diventa «-c» o vuoto, e nel registro resta una
    riga anonima. Trovato il 26/9: 401 righe su 713 senza nome, cioe' dopo un
    guaio non si risaliva a chi aveva cambiato cosa. Qui si guarda anche la pila
    delle chiamate, che dice sempre da quale file arriva la scrittura."""
    nome = os.path.basename(sys.argv[0] or "").replace(".py", "")
    if nome and nome not in ("-c", "-", "python", "python3", "<stdin>"):
        return nome
    try:                      # il primo file nostro che ha chiamato, dal basso
        import traceback
        qui = os.path.dirname(os.path.abspath(__file__))
        for f in reversed(traceback.extract_stack()[:-1]):
            d = os.path.dirname(os.path.abspath(f.filename))
            base = os.path.basename(f.filename).replace(".py", "")
            if d.startswith(qui) and base not in ("stanza", "<stdin>") and not base.startswith("<"):
                return base
    except Exception:
        pass
    return "a-mano"           # scritto da una persona in una finestra, non da un'operazione


CHI_SCRIVE = _chi_scrive()


def sb(metodo, percorso, corpo=None, intestazioni=None):
    if not URL or not CHIAVE:
        raise RuntimeError("manca VITE_SUPABASE_URL o la service key in .env.local")
    req = urllib.request.Request(
        URL.rstrip("/") + percorso, method=metodo,
        data=json.dumps(corpo).encode() if corpo is not None else None,
        headers={"apikey": CHIAVE, "Authorization": "Bearer " + CHIAVE,
                 "Content-Type": "application/json",
                 # IL REGISTRO (25/9): ogni scrittura porta il nome dello script; il database
                 # lo mette in `registro` accanto a cosa e' cambiato (trigger registra_*)
                 "X-Clara-Script": CHI_SCRIVE, **(intestazioni or {})})
    try:
        with urllib.request.urlopen(req, timeout=40) as r:
            grezzo = r.read()
            dati = json.loads(grezzo) if grezzo else None
            # 29/9: il database si ferma a mille righe qualunque «limit» si chieda.
            # Se una lettura torna esattamente mille righe e ne voleva di piu', lo si dice.
            m = re.search(r"[?&]limit=(\d+)", percorso)
            if metodo == "GET" and isinstance(dati, list) and len(dati) == 1000 and m and int(m.group(1)) > 1000:
                print(f"  (attenzione: la lettura si e' fermata al tetto di 1000 righe, usa sb_tutte: {percorso[:80]})", file=sys.stderr)
            return dati
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"{e.code} {e.read()[:200].decode(errors='replace')}")


def sb_tutte(percorso, passo=1000):
    """TUTTE le righe, a pagine (29/9). Il database ne restituisce al massimo mille
    per richiesta, qualunque «limit» si chieda: calendario e Stripe cercavano fra
    mille aziende su 13.230, e nessuno se ne accorgeva perche' mille righe sembrano
    tutte. Chi vuole tutto usa questa, non un limit grande."""
    base = re.sub(r"([&?])limit=\d+&?", r"\1", percorso).rstrip("&?")
    if "order=" not in base:
        base += ("&" if "?" in base else "?") + "order=id"
    elif not re.search(r"order=[^&]*\bid\b", base):
        base = re.sub(r"(order=[^&]*)", r"\1,id.asc", base, count=1)   # a pagine serve un ordine senza pari
    sep = "&" if "?" in base else "?"
    righe, da = [], 0
    while True:
        pezzo = sb("GET", f"{base}{sep}limit={passo}&offset={da}") or []
        righe += pezzo
        if len(pezzo) < passo:
            return righe
        da += passo


def soldi_clienti(ids=None):
    """LA CASSAFORTE (Dre, 29/9: «i soldi li vediamo solo io e Giacomo»). Canone,
    fatturazione, prezzo suggerito e numeri del cliente stanno in soldi_clienti
    (schema_v67); gli script li leggono con la chiave di servizio. {prospect_id: riga}."""
    if ids is not None:
        ids = [i for i in ids if i]
        righe = []
        for i in range(0, len(ids), 100):
            righe += sb("GET", f"/rest/v1/soldi_clienti?select=*&prospect_id=in.({','.join(ids[i:i+100])})") or []
    else:
        righe = sb_tutte("/rest/v1/soldi_clienti?select=*")
    return {r["prospect_id"]: r for r in righe}


def con_soldi(p, soldi):
    """La scheda con i suoi soldi rimessi al loro posto, in memoria: canone e, dentro
    enriched, prezzo, bilancio e valore. Cosi' la logica degli script non cambia."""
    s = (soldi or {}).get((p or {}).get("id"))
    if not p or not s:
        return p
    arr = dict(p.get("enriched") or {})
    for k in ("prezzo", "bilancio", "valore"):
        if s.get(k) is not None:
            arr[k] = s[k]
    return {**p, "canone": p.get("canone") if p.get("canone") is not None else s.get("canone"), "enriched": arr}


def soldi_progetti():
    """Il valore dei progetti, dalla cassaforte: {progetto_id: valore}."""
    return {int(r["progetto_id"]): r.get("valore") for r in sb_tutte("/rest/v1/soldi_progetti?select=progetto_id,valore")}


def contattabile(p):
    """MAI UNA BOZZA A CHI NON E' PIU' UN LEAD (25/9, caso Zafferano): in pipeline
    (fuori), cliente, perso, «niente follow-up», rimosso o nervoso. La stessa
    regola sta nel database (trigger proposta_ammessa): qui serve per dirlo
    prima, con parole, e per i test."""
    if not p:
        return False
    if p.get("fuori") or p.get("stage") in ("cliente", "perso") or p.get("pipeline_stage") in ("cliente", "perso"):
        return False
    if p.get("no_followup") or p.get("classificazione") in ("soppresso", "nervoso"):
        return False
    return True


def _a_secco():
    """Siamo in una prova a secco? Si guarda la riga di comando e l'ambiente."""
    return ("--prova" in sys.argv or "--dry-run" in sys.argv
            or os.environ.get("PROVA") == "1" or os.environ.get("POLIZIA_PROVA") == "1"
            or os.environ.get("REVISORE_PROVA") == "1")


def proponi(tipo, titolo, prospect_id=None, perche=None, azione=None, owner=None, ref=None):
    """Una proposta nella stanza. Non scrive niente nella pipeline: solo la domanda.

    Non ne mette due uguali aperte sulla stessa persona: Dre le vedrebbe
    doppie e smetterebbe di leggerle. Con `ref` (schema_v45) la stessa
    domanda non nasce mai due volte, nemmeno dopo che e' stata chiusa: e' il
    modo giusto per le cose che ripassano ogni quarto d'ora (posta, azioni).

    LA PROVA A SECCO NON SCRIVE (28/9). Una prova di bozze.py lanciata con
    --prova ha creato otto proposte vere nella Posta di Dre, perche' chi aveva
    scritto quella parte (io) si era dimenticato il controllo. Il freno sta qui,
    non nei singoli script: se il comando ha --prova o PROVA=1, si stampa quello
    che si sarebbe chiesto e non si scrive niente. Cosi' vale per tutti, anche
    per il prossimo pezzo di codice che qualcuno aggiunge distrattamente.
    """
    if _a_secco():
        print(f"    (prova) chiederei: [{tipo}] {str(titolo)[:70]}")
        return None
    if ref:
        gia = sb("GET", f"/rest/v1/proposte?select=id&ref=eq.{urllib.parse.quote(ref, safe='')}&limit=1")
        if gia:
            return None
    elif prospect_id:
        gia = sb("GET", f"/rest/v1/proposte?select=id&stato=eq.aperta"
                        f"&tipo=eq.{tipo}&prospect_id=eq.{prospect_id}&limit=1")
        if gia:
            return None
    try:
        return sb("POST", "/rest/v1/proposte", {
            "tipo": tipo, "titolo": titolo[:200], "prospect_id": prospect_id,
            "perche": (perche or "")[:300] or None, "azione": azione or {}, "owner": owner,
            "ref": ref,
        }, {"Prefer": "return=representation"})
    except RuntimeError as e:
        # il database rifiuta le bozze a chi non e' piu' un lead (trigger proposta_ammessa, 25/9)
        if "proposta rifiutata" in str(e):
            print(f"  proposta rifiutata dal database (non è più un lead): {titolo[:60]}")
            return None
        if "bozza rifiutata" in str(e):                 # schema_v58: nessuna bozza senza lettura
            print(f"  bozza rifiutata dal database (senza lettura o incoerente): {titolo[:60]}")
            return None
        raise


def senza_trattini(testo):
    """Il trattino lungo lo toglie il codice, non un secondo giro del modello (29/9).
    L'analisi di Naturalia e' stata bocciata cinque giri di fila, due ore, anche per
    il trattino lungo: un difetto che si corregge con una sostituzione. Un inciso
    fra due trattini diventa una parentesi, un trattino solo diventa due punti."""
    def frase(f):
        if f.count("—") == 2:
            f = re.sub(r"\s*—\s*(.*?)\s*—\s*", r" (\1) ", f, count=1)
        return re.sub(r"\s*—\s*", ": ", f)
    return "".join(frase(f) for f in re.split(r"(?<=[.!?\n])", testo or "")).replace("–", "-")


def di_clara(tipo, testo, prospect_id=None, owner=None, letto=False, diario=False):
    """Una riga nella chat, a nome di Clara. `diario` marca la domanda del diario."""
    import re
    testo = re.sub(r"\s*—\s*", ": ", testo).replace("–", "-").replace("·", ",")   # la stessa di regole.ts
    return sb("POST", "/rest/v1/clara_messaggi", {
        "tipo": tipo, "testo": testo, "prospect_id": prospect_id,
        "owner": owner, "letto": letto, "diario": diario,
    }, {"Prefer": "return=representation"})
