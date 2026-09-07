#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""AVVISA — la notifica sul telefono di Dre, via Telegram (7/9/2026).

PERCHE' TELEGRAM
Dre: «notifica su smartphone, approvo velocissimo». Serviva un canale che
arriva sul telefono senza app nostra ne' store: Telegram ha un'API per i bot
gratuita, che regge da dieci anni, e un messaggio con dentro il link alla
stanza di Clara. Quando la Dashboard sara' pubblicata (Vercel) si aggiunge il
Web Push; questo resta come seconda strada.

COME SI ACCENDE
1) Dre crea il bot con @BotFather (/newbot) e mette il token in
   TELEGRAM_BOT_TOKEN (.env.local e secret di GitHub).
2) Dre scrive «ciao» al bot, poi `python3 scripts/avvisa.py --chi` stampa il
   suo chat id: va in TELEGRAM_CHAT_ID.
Senza queste due variabili avvisa() non fa niente e non rompe niente:
gli script chiamanti non devono saperlo.

USO
  from avvisa import avvisa; avvisa("3 bozze nuove")
  python3 scripts/avvisa.py --chi           mostra chi ha scritto al bot
  python3 scripts/avvisa.py "prova"         manda un messaggio
"""

import json
import os
import sys
import urllib.parse
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from stanza import env                                     # noqa: E402

DASHBOARD = env("DASHBOARD_URL") or "http://localhost:5173"


def _tg(metodo, dati=None):
    token = env("TELEGRAM_BOT_TOKEN")
    if not token:
        return None
    req = urllib.request.Request(
        f"https://api.telegram.org/bot{token}/{metodo}",
        data=urllib.parse.urlencode(dati).encode() if dati else None)
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            return json.loads(r.read())
    except Exception as e:                                 # la notifica non deve mai fermare il lavoro
        print(f"  (telegram: {e})")
        return None


def avvisa(testo, link=None):
    """Manda il messaggio a Dre. Silenzioso se il bot non e' configurato."""
    chat = env("TELEGRAM_CHAT_ID")
    if not chat:
        return False
    if link:
        testo += f"\n{link}"
    r = _tg("sendMessage", {"chat_id": chat, "text": testo, "disable_web_page_preview": "true"})
    return bool(r and r.get("ok"))


def main():
    if "--chi" in sys.argv:
        r = _tg("getUpdates") or {}
        visti = {}
        for u in r.get("result", []):
            m = u.get("message") or {}
            c = m.get("chat") or {}
            if c.get("id"):
                visti[c["id"]] = f"{c.get('first_name', '')} {c.get('last_name', '')} @{c.get('username', '')}".strip()
        if not visti:
            print("nessuno ha ancora scritto al bot (o manca TELEGRAM_BOT_TOKEN)")
        for cid, chi in visti.items():
            print(f"  TELEGRAM_CHAT_ID={cid}   {chi}")
        return
    testo = " ".join(a for a in sys.argv[1:]) or "Clara: prova di notifica"
    print("mandato" if avvisa(testo) else "non mandato (manca TELEGRAM_BOT_TOKEN o TELEGRAM_CHAT_ID)")


if __name__ == "__main__":
    main()
