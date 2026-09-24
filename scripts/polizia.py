#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""IL POLIZIOTTO (Dre, 24/9/2026: «non fare mai più una cosa del genere, inserisci
un poliziotto Claude che controlla Claude»).

Il 24/9 uno script che toglieva 1.125 email catch-all ha cancellato dalle
campagne anche 5 dei 6 che avevano risposto, e con loro il thread nella Master
Inbox di Smartlead. Nessuno lo ha fermato perche' nessuno guardava.

Da qui in poi ogni azione di massa o irreversibile passa da qui, PRIMA di
partire. Il poliziotto fa tre cose, nell'ordine:

  1. LE REGOLE DURE, in codice, che non si discutono:
     - mai cancellare da una campagna chi ha risposto (last_reply_at);
     - mai toccare chi e' «fuori», bloccato o soppresso;
     - sopra la soglia (300 righe) o su un'azione irreversibile serve l'ok di Dre:
       il piano finisce in Posta come proposta e lo script si ferma.
  2. LA SECONDA TESTA: un modello diverso da quello che ha preparato l'azione
     legge il piano e un campione delle righe e risponde OK o STOP col motivo.
     Se dice STOP, non si parte.
  3. IL VERBALE: cosa si voleva fare, quante righe, cosa e' stato escluso e
     perche', chi ha detto ok. Nella chat di Clara (tipo «controllo») e a video.

USO, dentro uno script:
    from polizia import controlla
    righe = controlla("cancello lead dalle campagne", righe, chiave=lambda r: r["email"],
                      irreversibile=True, motivo="catch-all con nome inventato: 10% di bounce")
    # righe e' la lista ripulita; se il poliziotto ferma tutto, lo script esce qui.

Prova a secco: POLIZIA_PROVA=1 fa tutti i controlli e non ferma.
Ok di Dre gia' dato (per la stessa azione, dopo la proposta in Posta): POLIZIA_OK=<id proposta>.
"""
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from stanza import sb, proponi, di_clara                   # noqa: E402

SOGLIA = 300                     # sopra, serve l'ok di Dre anche se reversibile
BASE = "https://server.smartlead.ai/api/v1"


def _chiave_smartlead():
    for r in open(os.path.expanduser("~/.hermes/config.yaml"), encoding="utf-8"):
        m = re.match(r"\s*SMARTLEAD_API_KEY:\s*(\S+)", r)
        if m:
            return m.group(1).strip("\"'")
    return os.environ.get("SMARTLEAD_API_KEY", "")


def _ha_risposto(email):
    """La persona ha risposto? Si guarda nel CRM (che ricorda anche i lead che Smartlead
    ha perso) e in Smartlead. Basta un si'."""
    if not email:
        return False
    try:
        r = sb("GET", f"/rest/v1/prospects?select=last_reply_at,awaiting_us&email=eq.{urllib.parse.quote(email)}&limit=1") or []
        if r and (r[0].get("last_reply_at") or r[0].get("awaiting_us")):
            return True
    except Exception:
        return True
    k = _chiave_smartlead()
    if not k:
        return False
    try:
        req = urllib.request.Request(f"{BASE}/leads/?email={urllib.parse.quote(email)}&api_key={k}", headers={"User-Agent": "clara/1.0"})
        with urllib.request.urlopen(req, timeout=60) as r:
            d = json.loads(r.read() or b"{}")
        return any(c.get("last_reply_at") for c in (d.get("lead_campaign_data") or []))
    except Exception:
        return True          # nel dubbio, si tiene: meglio non cancellare che cancellare uno che ha risposto


def _seconda_testa(azione, motivo, n, campione, esclusi):
    """Un modello diverso legge il piano e dice OK o STOP."""
    try:
        import cervello
        prompt = f"""Sei il POLIZIOTTO di Studio Galilei. Un altro sistema vuole fare questa azione di massa
sui dati veri dell'azienda. Il tuo compito e' fermarla se e' pericolosa. Non sei gentile, sei prudente.

AZIONE: {azione}
MOTIVO DICHIARATO: {motivo}
RIGHE COINVOLTE: {n} (gia' esclusi dalle regole dure: {esclusi})
CAMPIONE (20 righe): {json.dumps(campione, ensure_ascii=False)[:3000]}

Regole della casa: mai cancellare chi ha risposto; mai toccare chi e' fuori, bloccato o soppresso;
un'azione irreversibile su piu' di 300 righe vuole l'ok esplicito di Dre; ogni cancellazione da una
campagna Smartlead cancella anche il thread della Master Inbox (successo il 24/9, 5 rispondenti persi).

Rispondi SOLO con una riga: «OK» oppure «STOP: motivo in venti parole»."""
        modello = "gpt-5" if cervello.FORNITORE == "openai" else None
        r = (cervello._chiedi(prompt, modello) or "").strip()
        return r
    except Exception as e:                                   # noqa: BLE001
        return f"STOP: il poliziotto non ha potuto leggere il piano ({str(e)[:60]})"


def controlla(azione, righe, chiave=lambda r: r.get("email"), irreversibile=True, motivo="", stato_campo="stato"):
    """Restituisce le righe che si possono toccare. Se l'azione va fermata, esce."""
    prova = os.environ.get("POLIZIA_PROVA") == "1"
    ok_dre = os.environ.get("POLIZIA_OK")
    righe = list(righe)
    verbale = [f"POLIZIOTTO su «{azione}»: {len(righe)} righe, motivo: {motivo or '-'}"]
    # 1. regole dure
    tenute, esclusi = [], {}
    for r in righe:
        e = (chiave(r) or "").lower()
        if r.get("fuori") or r.get("bloccato") or (r.get("classificazione") in ("soppresso",)):
            esclusi["fuori/bloccato/soppresso"] = esclusi.get("fuori/bloccato/soppresso", 0) + 1; continue
        if irreversibile and "cancell" in azione.lower() and _ha_risposto(e):
            esclusi["ha risposto"] = esclusi.get("ha risposto", 0) + 1; continue
        tenute.append(r)
    verbale.append(f"  regole dure: escluse {sum(esclusi.values())} {dict(esclusi) if esclusi else ''}, restano {len(tenute)}")
    # 2. la seconda testa
    campione = [{k: (str(v)[:60]) for k, v in r.items() if k in ("email", "campagna", "azienda", "classificazione", "verifica", "esito")} for r in tenute[:20]]
    giudizio = _seconda_testa(azione, motivo, len(tenute), campione, esclusi)
    verbale.append(f"  seconda testa: {giudizio[:160]}")
    fermata = giudizio.upper().startswith("STOP")
    # 3. l'ok di Dre, se serve
    serve_ok = (len(tenute) > SOGLIA) or (irreversibile and len(tenute) > 50)
    if serve_ok and not ok_dre and not prova:
        pid = proponi("umano", f"Il poliziotto chiede il tuo ok: {azione} ({len(tenute)} righe)",
                      perche=("\n".join(verbale) + "\nPer far partire: POLIZIA_OK=<id di questa proposta>")[:280],
                      azione={"polizia": {"azione": azione, "righe": len(tenute), "esclusi": esclusi, "campione": campione[:5]}})
        verbale.append(f"  serve l'ok di Dre: proposta {pid} in Posta. Mi fermo.")
        fermata = True
    testo = "\n".join(verbale)
    print(testo, flush=True)
    try:
        di_clara("controllo", testo[:900])
    except Exception:
        pass
    if fermata and not prova:
        sys.exit("fermato dal poliziotto")
    return tenute
