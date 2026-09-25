#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""LA STANZA — le mani di Clara verso il database (7/9/2026).

Due cose sole: parlare con Supabase (sb) e mettere una proposta nella stanza
(proponi). Chi legge e capisce e' cervello.py; chi decide e' Dre. Questo
file e' solo la porta di servizio, e la usano sia la rilettura sia
l'ascoltatore, cosi' la scrittura di una proposta e' una e non due.
"""

import json
import os
import urllib.error
import urllib.parse
import urllib.request

RADICE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


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


def sb(metodo, percorso, corpo=None, intestazioni=None):
    if not URL or not CHIAVE:
        raise RuntimeError("manca VITE_SUPABASE_URL o la service key in .env.local")
    req = urllib.request.Request(
        URL.rstrip("/") + percorso, method=metodo,
        data=json.dumps(corpo).encode() if corpo is not None else None,
        headers={"apikey": CHIAVE, "Authorization": "Bearer " + CHIAVE,
                 "Content-Type": "application/json", **(intestazioni or {})})
    try:
        with urllib.request.urlopen(req, timeout=40) as r:
            grezzo = r.read()
            return json.loads(grezzo) if grezzo else None
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"{e.code} {e.read()[:200].decode(errors='replace')}")


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


def proponi(tipo, titolo, prospect_id=None, perche=None, azione=None, owner=None, ref=None):
    """Una proposta nella stanza. Non scrive niente nella pipeline: solo la domanda.

    Non ne mette due uguali aperte sulla stessa persona: Dre le vedrebbe
    doppie e smetterebbe di leggerle. Con `ref` (schema_v45) la stessa
    domanda non nasce mai due volte, nemmeno dopo che e' stata chiusa: e' il
    modo giusto per le cose che ripassano ogni quarto d'ora (posta, azioni).
    """
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
        raise


def di_clara(tipo, testo, prospect_id=None, owner=None, letto=False, diario=False):
    """Una riga nella chat, a nome di Clara. `diario` marca la domanda del diario."""
    import re
    testo = re.sub(r"\s*—\s*", ": ", testo).replace("–", "-").replace("·", ",")   # la stessa di regole.ts
    return sb("POST", "/rest/v1/clara_messaggi", {
        "tipo": tipo, "testo": testo, "prospect_id": prospect_id,
        "owner": owner, "letto": letto, "diario": diario,
    }, {"Prefer": "return=representation"})
