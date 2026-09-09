#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ESPORTA I THREAD — tutte le conversazioni Smartlead, leggibili (7/9/2026).

Dre: «mi puoi mandare il thread di tutte le mie conversazioni su Smartlead,
che le analizzo e rifinisco il playbook». Per ogni campagna viva, per ogni
lead che ha risposto, il filo intero: le nostre mail e le sue, con le date,
in un file Markdown per campagna dentro il vault, piu' un indice.

E gia' che si leggono i thread veri, con --riempi-archivio si riempiono i
corpi vuoti in `interactions` (274 su 738 avevano dentro solo la notifica di
Smartlead): e' il nono buco della stanza.

USO
  python3 scripts/esporta_thread.py                      scrive i file nel vault
  python3 scripts/esporta_thread.py --riempi-archivio    e riempie i corpi vuoti
"""

import datetime
import os
import re
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sync_v2 as sl                                       # noqa: E402  (gli aiutanti Smartlead)
from stanza import sb                                      # noqa: E402

VAULT = os.path.expanduser("~/Documents/Obsidian/studiogalilei/Sistema Operativo Studio Galilei/ODYN Cockpit/Thread Smartlead")
RIEMPI = "--riempi-archivio" in sys.argv
IGNORA = ("best campaign",)


def pulito(s):
    return sl.strip_html(s or "").strip()


def slug(s):
    return re.sub(r"[^a-z0-9]+", "-", (s or "").lower()).strip("-")[:60] or "campagna"


def main():
    os.makedirs(VAULT, exist_ok=True)
    campagne = [c for c in (sl.sl_get("/campaigns") or [])
                if c.get("status") != "ARCHIVED" and not any(x in (c.get("name") or "").lower() for x in IGNORA)]
    noti = sl.db_prospects()                      # email -> record, per l'id nel CRM
    vuoti = {}
    if RIEMPI:
        for r in sb("GET", "/rest/v1/interactions?kind=eq.email_in&select=id,prospect_id,at,body&limit=3000") or []:
            b = (r.get("body") or "").strip()
            if len(b) < 25 or "smartlead" in b.lower()[:200]:
                vuoti.setdefault(r["prospect_id"], []).append(r)

    indice = [f"# Thread Smartlead, tutte le conversazioni\n\n*Esportati il {datetime.date.today():%d/%m/%Y}. "
              f"Un file per campagna. Solo i lead che hanno risposto almeno una volta.*\n"]
    tot_lead, tot_msg, riempiti = 0, 0, 0

    for c in campagne:
        cid, nome = c["id"], c.get("name") or str(c["id"])
        righe = sl.sl_export(cid)
        con_reply = [r for r in righe if int(r.get("reply_count") or 0) > 0]
        print(f"[{cid}] {nome[:44]}  con risposta: {len(con_reply)}")
        out = [f"# {nome}\n\n*Campagna {cid}, {len(con_reply)} conversazioni, esportato il {datetime.date.today():%d/%m/%Y}*\n"]
        n_msg = 0
        for r in con_reply:
            em = (r.get("email") or "").strip().lower()
            lid = r.get("id") or r.get("lead_id")
            try:
                h = sl.sl_get(f"/campaigns/{cid}/leads/{lid}/message-history") or {}
            except Exception as e:
                out.append(f"\n## {r.get('company_name') or em}\n\n*thread illeggibile: {str(e)[:80]}*\n")
                continue
            msgs = h.get("history") or []
            if not msgs:
                continue
            rec = noti.get(em) or {}
            cls = rec.get("classificazione") or ""
            out.append(f"\n## {r.get('company_name') or '?'}, {(r.get('first_name') or '').strip()} {(r.get('last_name') or '').strip()}".rstrip())
            out.append(f"*{em}*, classificato oggi: **{cls or 'da classificare'}**, stage: {rec.get('stage') or '?'}\n")
            for m in msgs:
                chi = "**LORO**" if m.get("type") == "REPLY" else "noi"
                quando = (m.get("time") or "")[:16].replace("T", " ")
                corpo = sl.corpo_pulito(m.get("email_body")) if m.get("type") == "REPLY" else pulito(m.get("email_body"))
                corpo = re.sub(r"\n{3,}", "\n\n", corpo).strip()
                out.append(f"**{chi}**, {quando}\n\n{corpo[:3000] if corpo else '*(corpo vuoto)*'}\n")
                n_msg += 1
            out.append("---")
            # il nono buco: il corpo vuoto in archivio si riempie col thread vero
            if RIEMPI and rec.get("id") in vuoti:
                risposte = [m for m in msgs if m.get("type") == "REPLY"]
                for riga in vuoti[rec["id"]]:
                    at = (riga.get("at") or "")[:16]
                    match = next((m for m in risposte if (m.get("time") or "")[:16] == at), None) or (risposte[-1] if risposte else None)
                    corpo = sl.corpo_pulito(match.get("email_body")) if match else ""
                    if len(corpo.strip()) >= 25:
                        sb("PATCH", f"/rest/v1/interactions?id=eq.{riga['id']}", {"body": corpo[:800]})
                        riempiti += 1
            time.sleep(0.12)
        percorso = os.path.join(VAULT, f"{slug(nome)}.md")
        open(percorso, "w", encoding="utf-8").write("\n".join(out))
        indice.append(f"- [[Thread Smartlead/{slug(nome)}|{nome}]], {len(con_reply)} conversazioni, {n_msg} messaggi")
        tot_lead += len(con_reply); tot_msg += n_msg

    open(os.path.join(VAULT, "INDICE.md"), "w", encoding="utf-8").write("\n".join(indice) + "\n")
    print(f"\n✓ {tot_lead} conversazioni, {tot_msg} messaggi, in {VAULT}")
    if RIEMPI:
        print(f"✓ archivio: riempiti {riempiti} corpi vuoti")


if __name__ == "__main__":
    main()
