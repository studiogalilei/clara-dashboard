#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""IL BACKUP NOTTURNO — una copia di tutto, fuori da Supabase (7/9/2026).

PERCHE'
Il piano gratuito di Supabase non ha backup automatici. Per un sistema che
deve durare anni, «non c'e' un punto a cui tornare» non e' accettabile. Dre
ha scelto di restare sul piano gratuito e di avere questa copia al suo posto.

COSA FA
Legge OGNI tabella (le scopre da sole: una tabella nuova entra nel backup
senza toccare niente qui) e le salva in JSON dentro un archivio compresso.
L'archivio viene cifrato con una frase (BACKUP_FRASE): senza la frase e' un
file illeggibile, per chiunque.

DOVE GIRA
In cloud, su GitHub (.github/workflows/backup.yml), ogni notte. Non sul Mac
di Dre. Le copie restano 30 giorni. Quando Drive sara' collegato, si sposta li'.

PER RIMETTERE UNA COPIA
  openssl enc -d -aes-256-cbc -pbkdf2 -in clara-backup-AAAA-MM-GG.tar.gz.enc -out copia.tar.gz
  tar xzf copia.tar.gz        # una cartella con un JSON per tabella
  poi si reinseriscono le tabelle con scripts/ripristina.py (da scrivere il
  giorno che serve: e' un POST per tabella, in ordine di dipendenza)

USO LOCALE, per provare:  python3 scripts/backup.py
"""

import datetime
import json
import os
import subprocess
import sys
import tarfile
import tempfile
import urllib.request

RADICE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def env(nome):
    v = os.environ.get(nome)
    if v:
        return v
    p = os.path.join(RADICE, ".env.local")
    if os.path.exists(p):
        for riga in open(p, encoding="utf-8"):
            if riga.strip().startswith(nome + "="):
                return riga.split("=", 1)[1].strip().strip("\"'")
    return None


URL = (env("VITE_SUPABASE_URL") or "").rstrip("/")
CHIAVE = env("SUPABASE_SERVICE_KEY") or env("SUPABASE_SERVICE_ROLE_KEY")
FRASE = env("BACKUP_FRASE")
PAGINA = 1000


def prendi(percorso, intestazioni=None):
    req = urllib.request.Request(URL + percorso, headers={
        "apikey": CHIAVE, "Authorization": "Bearer " + CHIAVE, **(intestazioni or {})})
    with urllib.request.urlopen(req, timeout=120) as r:
        return json.load(r)


def tabelle():
    """Tutte le tabelle e viste esposte, scoperte dal database stesso."""
    d = prendi("/rest/v1/")
    nomi = sorted(d.get("definitions", {}).keys())
    return [t for t in nomi if not t.startswith("v_")]   # le viste si ricalcolano


def scarica(tabella):
    """A pagine, in ordine di id quando c'e': se la tabella non ha un id
    (list_members, preferenze) si scarica senza ordine. Il primo giro in
    cloud si e' fermato proprio li' (7/9)."""
    righe, da, ordine = [], 0, "&order=id.asc"
    while True:
        try:
            pezzo = prendi(f"/rest/v1/{tabella}?select=*{ordine}&limit={PAGINA}&offset={da}")
        except Exception:
            if not ordine:
                raise
            ordine = ""
            continue
        righe.extend(pezzo)
        if len(pezzo) < PAGINA:
            return righe
        da += PAGINA


def main():
    if not URL or not CHIAVE:
        sys.exit("mancano VITE_SUPABASE_URL o la service key")
    if not FRASE:
        sys.exit("manca BACKUP_FRASE: senza la frase la copia non si cifra, e non si fa")
    oggi = datetime.date.today().isoformat()
    cartella = tempfile.mkdtemp()
    dentro = os.path.join(cartella, f"clara-backup-{oggi}")
    os.makedirs(dentro)
    totale = 0
    for t in tabelle():
        try:
            righe = scarica(t)
        except Exception as e:
            print(f"  ! {t}: {str(e)[:100]}")
            continue
        with open(os.path.join(dentro, f"{t}.json"), "w", encoding="utf-8") as f:
            json.dump(righe, f, ensure_ascii=False)
        totale += len(righe)
        print(f"  {t:18} {len(righe):6} righe")
    tgz = dentro + ".tar.gz"
    with tarfile.open(tgz, "w:gz") as tar:
        tar.add(dentro, arcname=os.path.basename(dentro))
    fuori = os.path.join(os.getcwd(), f"clara-backup-{oggi}.tar.gz.enc")
    subprocess.run(["openssl", "enc", "-aes-256-cbc", "-pbkdf2", "-salt", "-in", tgz, "-out", fuori,
                    "-pass", "env:BACKUP_FRASE"], check=True, env={**os.environ, "BACKUP_FRASE": FRASE})
    mb = os.path.getsize(fuori) / 1e6
    print(f"\n✓ {totale} righe in {fuori} ({mb:.1f} MB, cifrato)")
    # la riga nel registro della sala di controllo (se le tabelle ci sono)
    try:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        from stanza import sb
        adesso = datetime.datetime.now(datetime.timezone.utc).isoformat()
        sb("PATCH", "/rest/v1/operazioni?chiave=eq.backup",
           {"ultima_corsa": adesso, "ultimo_esito": "ok", "ultimo_dettaglio": f"{totale} righe, {mb:.1f} MB"})
        sb("POST", "/rest/v1/corse", {"operazione": "backup", "esito": "ok",
                                       "dettaglio": f"{totale} righe, {mb:.1f} MB", "righe": totale})
    except Exception:
        pass


if __name__ == "__main__":
    main()
