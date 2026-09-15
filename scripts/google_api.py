#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""GOOGLE A NOME DI CHI HA DATO IL PERMESSO (11/9/2026).

Chi entra nel Workspace con Google lascia un refresh token in google_token
(schema_v20). Da qui il runner lo scambia con un access token e parla con
Drive, Chat e Calendar a nome di quella persona. Il client id e secret sono
quelli del progetto Cloud «SG Workspace» (GOOGLE_OAUTH_CLIENT_ID/SECRET).

USO (dagli altri script)
  from google_api import g, drive_cerca, drive_testo, drive_copia, cartella
  g("GET", "https://www.googleapis.com/drive/v3/about?fields=user")
"""

import json
import os
import sys
import time
import urllib.parse
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from stanza import sb, env                                 # noqa: E402

UTENTE = env("GOOGLE_UTENTE") or "dramane@studiogalilei.com"
_cache = {}


def access_token(email=None):
    email = email or UTENTE
    c = _cache.get(email)
    if c and c["scade"] > time.time() + 60:
        return c["token"]
    righe = sb("GET", f"/rest/v1/google_token?select=refresh_token&email=eq.{urllib.parse.quote(email)}&limit=1") or []
    if not righe:
        raise RuntimeError(f"{email} non e' mai entrato con Google (manca google_token)")
    cid, sec = env("GOOGLE_OAUTH_CLIENT_ID"), env("GOOGLE_OAUTH_CLIENT_SECRET")
    if not cid or not sec:
        raise RuntimeError(f"mancano GOOGLE_OAUTH_CLIENT_ID / GOOGLE_OAUTH_CLIENT_SECRET")
    corpo = urllib.parse.urlencode({"client_id": cid, "client_secret": sec, "refresh_token": righe[0]["refresh_token"], "grant_type": "refresh_token"}).encode()
    req = urllib.request.Request("https://oauth2.googleapis.com/token", data=corpo, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            d = json.loads(r.read())
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"Google non rinnova il token di {email}: {e.read().decode()[:200]}")
    _cache[email] = {"token": d["access_token"], "scade": time.time() + int(d.get("expires_in", 3600))}
    return d["access_token"]


def g(metodo, url, corpo=None, email=None, grezzo=False, intestazioni=None):
    h = {"Authorization": "Bearer " + access_token(email), **(intestazioni or {})}
    dati = None
    if corpo is not None:
        h["Content-Type"] = "application/json"
        dati = json.dumps(corpo).encode()
    req = urllib.request.Request(url, data=dati, method=metodo, headers=h)
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            b = r.read()
            return b if grezzo else (json.loads(b) if b else None)
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"Google {e.code} su {url[:80]}: {e.read().decode()[:300]}")


# ── Drive ────────────────────────────────────────────────────────
DRIVE = "https://www.googleapis.com/drive/v3"
TUTTI = "supportsAllDrives=true&includeItemsFromAllDrives=true"


def drive_cerca(q, campi="id,name,mimeType,createdTime,modifiedTime,webViewLink,parents", quanti=100, email=None):
    p = urllib.parse.urlencode({"q": q, "fields": f"files({campi})", "pageSize": quanti, "corpora": "allDrives", "orderBy": "modifiedTime desc"})
    return (g("GET", f"{DRIVE}/files?{p}&{TUTTI}", email=email) or {}).get("files", [])


def drive_testo(file_id, email=None):
    """Un Google Doc come testo semplice."""
    return g("GET", f"{DRIVE}/files/{file_id}/export?mimeType=text/plain", email=email, grezzo=True).decode("utf-8", errors="replace")


def drive_copia(file_id, nome, cartella_id, email=None):
    return g("POST", f"{DRIVE}/files/{file_id}/copy?supportsAllDrives=true&fields=id,webViewLink", {"name": nome, "parents": [cartella_id]}, email=email)


def cartella(nome, dentro, crea=True, email=None):
    """La cartella con quel nome dentro un'altra (o che inizia cosi'); se manca la crea."""
    q = f"'{dentro}' in parents and mimeType = 'application/vnd.google-apps.folder' and trashed = false and name contains '{nome.replace(chr(39), chr(92) + chr(39))}'"
    for f in drive_cerca(q, campi="id,name", email=email):
        if f["name"].startswith(nome):
            return f["id"]
    if not crea:
        return None
    return g("POST", f"{DRIVE}/files?supportsAllDrives=true&fields=id", {"name": nome, "mimeType": "application/vnd.google-apps.folder", "parents": [dentro]}, email=email)["id"]


if __name__ == "__main__":
    print(json.dumps(g("GET", f"{DRIVE}/about?fields=user(emailAddress,displayName)"), ensure_ascii=False))
