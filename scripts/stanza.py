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
        # 16/10: un sito con un carattere nullo (\u0000) faceva cadere ogni giro del Google Fit:
        # Postgres non accetta il nullo nel testo, quindi qui, in un punto solo, non entra mai
        data=json.dumps(corpo).replace("\\u0000", "").encode() if corpo is not None else None,
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
        corpo = e.read()[:300].decode(errors="replace")
        # 9/10: il 402 e' il database che non c'e' piu' (quota di traffico finita, piano
        # bloccato). Stanotte e' scattato alle 4:50 e per cinque ore sessanta giri del
        # direttore hanno fallito in silenzio, uno ogni cinque minuti, perche' questo
        # errore era uguale a tutti gli altri. Un database spento si dice con parole sue.
        if e.code == 402:
            raise RuntimeError(f"SUPABASE BLOCCATO (402): il progetto e' limitato, serve Dre su Billing. {corpo}")
        raise RuntimeError(f"{e.code} {corpo}")


def sb_tutte(percorso, passo=1000, chiave="id"):
    """TUTTE le righe, a pagine (29/9). Il database ne restituisce al massimo mille
    per richiesta, qualunque «limit» si chieda: calendario e Stripe cercavano fra
    mille aziende su 13.230, e nessuno se ne accorgeva perche' mille righe sembrano
    tutte. Chi vuole tutto usa questa, non un limit grande."""
    base = re.sub(r"([&?])limit=\d+&?", r"\1", percorso).rstrip("&?")
    # a pagine serve un ordine senza pari: la chiave della tabella (id, salvo dove si chiama altrimenti)
    if "order=" not in base:
        base += ("&" if "?" in base else "?") + f"order={chiave}"
    elif not re.search(rf"order=(?:[^&]*,)?{chiave}(?:\.|,|&|$)", base):
        base = re.sub(r"(order=[^&]*)", rf"\1,{chiave}.asc", base, count=1)
    sep = "&" if "?" in base else "?"
    righe, da = [], 0
    while True:
        pezzo = sb("GET", f"{base}{sep}limit={passo}&offset={da}") or []
        righe += pezzo
        if len(pezzo) < passo:
            return righe
        da += passo
