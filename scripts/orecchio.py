#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""L'ORECCHIO: Gmail avvisa Clara quando arriva una mail (17/9/2026).

PERCHE'
Dre: «tutti gli update li voglio in realtime». Il direttore gira ogni venti
minuti, e venti minuti non sono «subito». Gmail sa avvisare (push): quando
arriva una mail manda un segnale a Pub/Sub, Pub/Sub chiama la funzione
`sveglia`, e quella fa partire il direttore adesso. Questo script tiene
acceso l'orecchio: Gmail lo spegne da solo dopo 7 giorni, quindi si rinnova
ogni giorno.

COSA SERVE (una volta)
Il canale sta nel progetto Cloud dello Studio (GOOGLE_CLOUD_PROJECT). Per
crearlo serve il permesso «cloud-platform» sul token di chi guida lo Studio:
si da' da Impostazioni, Collegamenti, «La posta in tempo reale». Fatto
quello, questo script fa tutto il resto da solo: accende Pub/Sub, crea il
canale, dice a Gmail di scriverci, punta il canale sulla funzione sveglia.

USO
  python3 scripts/orecchio.py          accende / rinnova
  python3 scripts/orecchio.py --prova  dice cosa farebbe
"""

import base64
import json
import os
import sys
import urllib.error

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from stanza import sb, env                                 # noqa: E402
from google_api import g, UTENTE                           # noqa: E402

PROVA = "--prova" in sys.argv
PROGETTO = env("GOOGLE_CLOUD_PROJECT")
CANALE = "sg-posta"
ISCRIZIONE = "sg-posta-sveglia"
PUBSUB = "https://pubsub.googleapis.com/v1"
GMAIL_PUSH = "serviceAccount:gmail-api-push@system.gserviceaccount.com"


def sveglia_url():
    base = env("VITE_SUPABASE_URL") or env("SUPABASE_URL")
    segreto = env("WEBHOOK_SEGRETO")
    if not base or not segreto:
        raise RuntimeError("mancano VITE_SUPABASE_URL o WEBHOOK_SEGRETO")
    return f"{base}/functions/v1/sveglia?chiave={segreto}&fonte=gmail"


def tenta(metodo, url, corpo=None, ok_se=(409,)):
    """Chiama Google; certi errori sono «c'e' gia'» e vanno bene."""
    try:
        return g(metodo, url, corpo)
    except RuntimeError as e:
        for codice in ok_se:
            if str(e).startswith(str(codice)):
                return None
        raise


def prepara_canale():
    """Pub/Sub acceso, canale creato, Gmail autorizzato a scriverci, canale puntato sulla sveglia."""
    if not PROGETTO:
        raise RuntimeError("manca GOOGLE_CLOUD_PROJECT")
    topic = f"projects/{PROGETTO}/topics/{CANALE}"
    sub = f"projects/{PROGETTO}/subscriptions/{ISCRIZIONE}"
    if PROVA:
        print(f"  (prova) accenderei Pub/Sub su {PROGETTO}, canale {topic}, iscrizione verso la sveglia")
        return topic
    # 1. il servizio: se e' gia' acceso non fa niente
    g("POST", f"https://serviceusage.googleapis.com/v1/projects/{PROGETTO}/services/pubsub.googleapis.com:enable", {})
    # 2. il canale
    if tenta("PUT", f"{PUBSUB}/{topic}", {}) is not None:
        print(f"  canale {CANALE} creato")
    # 3. Gmail puo' scriverci
    politica = g("POST", f"{PUBSUB}/{topic}:getIamPolicy", {}) or {}
    vincoli = politica.get("bindings") or []
    editori = next((b for b in vincoli if b.get("role") == "roles/pubsub.publisher"), None)
    if not editori:
        editori = {"role": "roles/pubsub.publisher", "members": []}
        vincoli.append(editori)
    if GMAIL_PUSH not in editori["members"]:
        editori["members"].append(GMAIL_PUSH)
        politica["bindings"] = vincoli
        g("POST", f"{PUBSUB}/{topic}:setIamPolicy", {"policy": politica})
        print("  Gmail autorizzato a scrivere sul canale")
    # 4. l'iscrizione che chiama la sveglia (mai in scadenza)
    corpo = {
        "topic": topic,
        "pushConfig": {"pushEndpoint": sveglia_url()},
        "ackDeadlineSeconds": 10,
        "expirationPolicy": {},
        "retryPolicy": {"minimumBackoff": "10s", "maximumBackoff": "600s"},
    }
    if tenta("PUT", f"{PUBSUB}/{sub}", corpo) is not None:
        print("  iscrizione creata: Pub/Sub chiama la sveglia")
    else:
        # c'e' gia': si tiene allineato l'indirizzo (il segreto puo' cambiare)
        g("PATCH", f"{PUBSUB}/{sub}", {"subscription": {"name": sub, "pushConfig": corpo["pushConfig"]}, "updateMask": "pushConfig"})
    return topic


def caselle():
    righe = sb("GET", "/rest/v1/google_token?select=email,scopes") or []
    return [r["email"] for r in righe if r.get("email") and "gmail.readonly" in (r.get("scopes") or "")]


def main():
    topic = prepara_canale()
    accese = 0
    for email in caselle():
        if PROVA:
            print(f"  (prova) direi a Gmail di avvisare per {email}")
            accese += 1
            continue
        try:
            r = g("POST", "https://gmail.googleapis.com/gmail/v1/users/me/watch",
                  {"topicName": topic, "labelIds": ["INBOX"], "labelFilterBehavior": "INCLUDE"}, email=email)
            scade = int(r.get("expiration", 0)) // 1000
            print(f"  {email}: orecchio acceso, scade fra {(scade - __import__('time').time()) / 86400:.1f} giorni")
            accese += 1
        except RuntimeError as e:
            print(f"  {email}: non riesco ({str(e)[:140]})")
    print(f"{'(prova) ' if PROVA else ''}orecchio acceso su {accese} caselle")


if __name__ == "__main__":
    try:
        main()
    except RuntimeError as e:
        m = str(e)
        if "403" in m or "insufficient" in m.lower() or "PERMISSION" in m:
            print(f"manca il permesso cloud-platform sul token di {UTENTE}: si da' da Impostazioni, Collegamenti, «La posta in tempo reale». Dettaglio: {m[:200]}")
            sys.exit(1)
        raise
