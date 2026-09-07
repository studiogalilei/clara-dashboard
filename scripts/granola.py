#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""GRANOLA — Clara legge i transcript delle call e li mette nella Storia (7/9/2026).

PERCHE'
La call e' la tappa che conta, e quello che ci si e' detti sta in Granola.
Con il transcript nella Storia, Clara sa cosa e' stato promesso e a che punto
e' il rapporto («Zafferano l'ho gia' sentito ed e' quasi cliente»).

DA DOVE LEGGE
L'API pubblica di Granola (https://public-api.granola.ai/v1), con una chiave
`grn_…` che si crea dall'app Granola (Settings > API keys; serve il piano
Business). La chiave sta in GRANOLA_API_KEY: nel .env.local e nei secret di
GitHub. La copia locale di Granola sul Mac e' cifrata: non e' una strada.

COSA FA
Prende le note (le riunioni) create dopo l'ultima che ha gia' letto, ne
scarica riassunto e transcript, riconosce il prospect (email dei
partecipanti, poi la call in `agenda` alla stessa ora, poi il titolo) e
scrive un'interazione `transcript` nella sua Storia. Le note senza prospect
riconosciuto restano fuori: niente indovinelli, e niente roba privata nel CRM.
Non scrive due volte la stessa nota: la prima riga del body e' «[granola:id]».

USO
  python3 scripts/granola.py            legge le note nuove
  python3 scripts/granola.py --tutte    rilegge gli ultimi 400 giorni
  python3 scripts/granola.py --prova    mostra e non scrive
"""

import datetime
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from stanza import env, sb                                 # noqa: E402
import calendario                                          # noqa: E402

BASE = "https://public-api.granola.ai/v1"
INDIETRO = 400
MARCA = "[granola:"


def gr(percorso):
    chiave = env("GRANOLA_API_KEY")
    if not chiave:
        print("manca GRANOLA_API_KEY (la chiave grn_… dall'app Granola)")
        sys.exit(1)
    req = urllib.request.Request(BASE + percorso, headers={
        "Authorization": "Bearer " + chiave, "Accept": "application/json", "User-Agent": "clara-dashboard"})
    for tentativo in range(3):
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                return json.loads(r.read() or b"{}")
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None
            if e.code == 429 and tentativo < 2:
                time.sleep(5); continue
            raise RuntimeError(f"Granola {e.code}: {e.read()[:200].decode(errors='replace')}")


def note_da(quando):
    """Tutte le note create dopo `quando`, pagina per pagina."""
    cursore, out = None, []
    while True:
        q = f"/notes?created_after={quando.isoformat().replace('+00:00', 'Z')}" + (f"&cursor={cursore}" if cursore else "")
        pagina = gr(q) or {}
        out += pagina.get("notes") or pagina.get("data") or []
        cursore = pagina.get("cursor") or pagina.get("next_cursor")
        if not pagina.get("hasMore") or not cursore:
            return out


def _emails(oggetto):
    """Tutte le email che compaiono da qualche parte nella nota (partecipanti, evento)."""
    return set(m.lower() for m in re.findall(r"[\w.+-]+@[\w-]+\.[\w.-]+", json.dumps(oggetto)))


def _quando_nota(n):
    for k in ("created_at", "createdAt", "date", "start_time", "startTime"):
        v = n.get(k) or (n.get("calendar_event") or {}).get(k)
        if v:
            try:
                return datetime.datetime.fromisoformat(v.replace("Z", "+00:00"))
            except ValueError:
                pass
    return None


def _testo(x):
    """Riassunto e transcript arrivano come stringa, o come lista di battute, o come blocchi."""
    if not x:
        return ""
    if isinstance(x, str):
        return x
    if isinstance(x, list):
        pezzi = []
        for b in x:
            if isinstance(b, str):
                pezzi.append(b)
            elif isinstance(b, dict):
                chi = b.get("speaker") or b.get("source") or ""
                cosa = b.get("text") or b.get("content") or b.get("markdown") or ""
                pezzi.append(f"{chi}: {cosa}" if chi and cosa else cosa)
        return "\n".join(p for p in pezzi if p)
    if isinstance(x, dict):
        return x.get("markdown") or x.get("text") or x.get("content") or json.dumps(x, ensure_ascii=False)
    return str(x)


def riconosci(n, prospects, agenda):
    emails = calendario.esterni(sorted(_emails(n)))
    for e in emails:
        if e in prospects["email"]:
            return prospects["email"][e], "email"
    for e in emails:
        d = calendario._dominio(e)
        if d and d not in calendario.GENERICI and d in prospects["dominio"]:
            return prospects["dominio"][d], "dominio"
    quando = _quando_nota(n)
    if quando:
        # la call in agenda alla stessa ora (entro 90 minuti) con un prospect
        for a in agenda:
            if a["prospect_id"] and abs((a["at"] - quando).total_seconds()) <= 90 * 60:
                return a["prospect_id"], "agenda"
    finto = {"titolo": n.get("title") or "", "invitati": []}
    pid, come = calendario.riconosci(finto, prospects)
    return pid, come


def main():
    prova = "--prova" in sys.argv
    adesso = datetime.datetime.now(datetime.timezone.utc)
    gia = {}
    for r in sb("GET", f"/rest/v1/interactions?select=id,at,body&kind=eq.transcript&body=like.{MARCA}*&limit=5000") or []:
        gia[r["body"].split("]")[0][len(MARCA):]] = r
    if "--tutte" in sys.argv or not gia:
        da = adesso - datetime.timedelta(days=INDIETRO)
    else:
        ultima = max(datetime.datetime.fromisoformat(r["at"].replace("Z", "+00:00")) for r in gia.values())
        da = ultima - datetime.timedelta(days=2)

    note = note_da(da)
    prospects = calendario.carica_prospects()
    agenda = [{"prospect_id": a["prospect_id"], "at": datetime.datetime.fromisoformat(a["at"].replace("Z", "+00:00"))}
              for a in (sb("GET", "/rest/v1/agenda?select=at,prospect_id&prospect_id=not.is.null&limit=5000") or [])]

    nuove = senza = 0
    for n in note:
        nid = n.get("id")
        if not nid or nid in gia:
            continue
        pid, come = riconosci(n, prospects, agenda)
        if not pid:
            senza += 1
            if prova:
                print(f"  ?  {(n.get('title') or '')[:60]}")
            continue
        if prova:
            print(f"  ok {(n.get('title') or '')[:60]:60} {come}")
            continue
        dettaglio = gr(f"/notes/{nid}?include=transcript") or n
        transcript = _testo(dettaglio.get("transcript"))
        if not transcript and dettaglio.get("has_transcript", True):
            transcript = _testo((gr(f"/notes/{nid}/transcript") or {}).get("transcript") or gr(f"/notes/{nid}/transcript"))
        riassunto = _testo(dettaglio.get("summary") or dettaglio.get("notes") or dettaglio.get("notes_markdown"))
        corpo = f"{MARCA}{nid}] {dettaglio.get('title') or n.get('title') or 'Call'}\n\n"
        if riassunto:
            corpo += "RIASSUNTO\n" + riassunto.strip() + "\n\n"
        if transcript:
            corpo += "TRANSCRIPT\n" + transcript.strip()
        quando = _quando_nota(dettaglio) or _quando_nota(n) or adesso
        sb("POST", "/rest/v1/interactions", {"prospect_id": pid, "kind": "transcript",
                                              "at": quando.isoformat(), "body": corpo[:200000]})
        nuove += 1
    print(f"granola: {nuove} transcript nuovi, {senza} note senza prospect, {len(note)} note lette")


if __name__ == "__main__":
    main()
