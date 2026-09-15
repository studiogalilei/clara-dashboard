#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""AVVISA — la notifica sul telefono di Dre, Web Push (7/9/2026).

PERCHE' WEB PUSH E NON UN'APP
Dre: «una webapp che mi aggiungo in Home sull'iPhone, deve inviare
notifiche». La Dashboard e' gia' una web app installabile; il browser le da'
un indirizzo a cui mandare i messaggi, e lo salva nelle preferenze (chiave
push-iscrizioni: una lista, telefono e computer insieme). Questo script
prende quegli indirizzi e manda. Niente store, niente Telegram, niente
servizi in mezzo: lo standard del browser, che regge da anni.

COME SI ACCENDE
Le chiavi VAPID (VITE_VAPID_PUBLIC nel browser, VAPID_PRIVATE qui) sono nei
secret di GitHub e in .env.local. Dre preme «Attiva le notifiche» in
Impostazioni dalla Dashboard aperta dalla Home dell'iPhone. Serve che la
Dashboard stia su https (dopo il deploy).

Senza chiavi o senza iscrizioni avvisa() non fa niente e non rompe niente:
gli script chiamanti non devono saperlo. Gli indirizzi morti (410/404) si
tolgono da soli.

USO
  from avvisa import avvisa; avvisa("3 bozze da approvare")
  python3 scripts/avvisa.py "prova"         manda un messaggio a tutti gli iscritti
"""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from stanza import env, sb                                 # noqa: E402

DASHBOARD = env("DASHBOARD_URL") or "./"
MITTENTE = "mailto:dramane@studiogalilei.com"


def avvisa(testo, titolo="Clara", url=None, a=None):
    """Manda ai dispositivi iscritti di `a` (lista di user id; None = ai ceo). Torna quanti hanno ricevuto."""
    privata = env("VAPID_PRIVATE")
    if not privata:
        return 0
    try:
        from pywebpush import webpush, WebPushException
    except ImportError:
        print("  (pywebpush non installato: niente notifica)")
        return 0
    if a is None:
        # senza destinatari espliciti si avvisa la direzione: le bozze e le domande sono loro
        a = [r["id"] for r in (sb("GET", "/rest/v1/profili?select=id&ruolo=eq.ceo") or [])]
    righe = [r for r in (sb("GET", "/rest/v1/preferenze?select=owner,valore&chiave=eq.push-iscrizioni") or []) if r.get("owner") in a]
    mandate = 0
    for r in righe:
        iscrizioni = r.get("valore") if isinstance(r.get("valore"), list) else []
        vive = []
        for i in iscrizioni:
            if not i.get("endpoint"):
                continue
            try:
                webpush(subscription_info={"endpoint": i["endpoint"], "keys": i.get("keys") or {}},
                        data=json.dumps({"titolo": titolo, "testo": testo, "url": url or DASHBOARD}),
                        vapid_private_key=privata, vapid_claims={"sub": MITTENTE}, ttl=3600)
                mandate += 1
                vive.append(i)
            except WebPushException as e:
                codice = getattr(getattr(e, "response", None), "status_code", None)
                if codice in (404, 410):
                    print(f"  (indirizzo morto, tolto: {i['endpoint'][:40]}…)")
                    continue                          # non si tiene
                print(f"  (push non mandata: {e})")
                vive.append(i)
        if len(vive) != len(iscrizioni):
            sb("PATCH", f"/rest/v1/preferenze?owner=eq.{r['owner']}&chiave=eq.push-iscrizioni", {"valore": vive})
    return mandate


def main():
    testo = " ".join(sys.argv[1:]) or "Prova di notifica"
    n = avvisa(testo)
    print(f"mandata a {n} dispositivi" if n else "non mandata (manca VAPID_PRIVATE, pywebpush, o nessuno e' iscritto)")


if __name__ == "__main__":
    main()
