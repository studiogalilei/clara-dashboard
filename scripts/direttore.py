#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""IL DIRETTORE — fa partire le operazioni alla cadenza che Dre sceglie (7/9/2026).

DOVE GIRA
In cloud, su GitHub, ogni ora (piu' il campanello di Smartlead) (.github/workflows/direttore.yml). Non sul
Mac di Dre: e' la condizione che ha messo lui, «neanche se bombardano il Mac».

COSA FA
Legge la tabella `operazioni` su Supabase: per ognuna sa ogni quanto deve
girare (cadenza_minuti), a che ora se e' giornaliera (ora_preferita), se e'
accesa, e se Dre ha premuto «fai ora». Fa partire quelle dovute, una alla
volta, e scrive com'e' andata: in `operazioni` (l'ultima) e in `corse` (tutte).
La cadenza si cambia dalla Dashboard, nella sala di controllo: qui non c'e'
nessun orologio da riscrivere.

PERCHE' GITHUB E NON UNA FUNZIONE DENTRO SUPABASE
Le operazioni sono script gia' collaudati sui dati veri (il sync riconcilia,
la rilettura protegge le correzioni a mano). Riscriverli in un'altra lingua
per farli girare dentro Supabase avrebbe voluto dire buttare il collaudo e
rifare i bug. Il cloud e' cloud in entrambi i casi; il rischio no.

USO
  python3 scripts/direttore.py                 fa partire quello che e' dovuto
  python3 scripts/direttore.py --forza brief   fa partire un'operazione adesso
  python3 scripts/direttore.py --stato         mostra la tabella e basta
"""

import datetime
import os
import subprocess
import sys
import time
import zoneinfo

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from stanza import sb                                      # noqa: E402

RADICE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROMA = zoneinfo.ZoneInfo("Europe/Rome")
ATTESA_MAX = 2400          # secondi per operazione: il sync ne vuole ~600, le bozze ~400


def adesso():
    return datetime.datetime.now(datetime.timezone.utc)


def dovuta(op):
    """Tocca a lei? Accesa, e o «fai ora», o mai girata, o e' passato il tempo."""
    if not op.get("attiva") or not op.get("comando"):
        return False
    if op.get("richiesta_ora"):
        return True
    ultima = op.get("ultima_corsa")
    if not ultima:
        return True
    u = datetime.datetime.fromisoformat(ultima.replace("Z", "+00:00"))
    ora = op.get("ora_preferita")
    if ora and op.get("cadenza_minuti", 0) >= 1440:
        # giornaliera a un'ora: e' dovuta se oggi (a Roma) e' passata quell'ora
        # e l'ultima corsa e' di un giorno precedente
        h, m = (int(x) for x in ora.split(":"))
        oggi_roma = adesso().astimezone(ROMA)
        soglia = oggi_roma.replace(hour=h, minute=m, second=0, microsecond=0)
        return oggi_roma >= soglia and u.astimezone(ROMA).date() < oggi_roma.date()
    return adesso() - u >= datetime.timedelta(minutes=op.get("cadenza_minuti", 60))


def corri(op):
    inizio = time.time()
    print(f"▶ {op['nome']}  ({op['comando']})")
    try:
        r = subprocess.run(op["comando"], shell=True, cwd=RADICE, capture_output=True,
                           text=True, timeout=ATTESA_MAX)
        esito = "ok" if r.returncode == 0 else "errore"
        uscita = (r.stdout + ("\n" + r.stderr if r.stderr else "")).strip()
    except subprocess.TimeoutExpired:
        esito, uscita = "errore", f"fermata dopo {ATTESA_MAX} secondi"
    except Exception as e:
        esito, uscita = "errore", str(e)
    durata = int((time.time() - inizio) * 1000)
    dettaglio = uscita[-2000:]
    righe = None
    for riga in reversed(uscita.splitlines()):
        for pezzo in riga.replace(":", " ").split():
            if pezzo.isdigit():
                righe = int(pezzo)
                break
        if righe is not None:
            break
    sb("PATCH", f"/rest/v1/operazioni?chiave=eq.{op['chiave']}", {
        "ultima_corsa": adesso().isoformat(), "ultimo_esito": esito,
        "ultimo_dettaglio": dettaglio[-500:], "ultima_durata_ms": durata, "richiesta_ora": False,
    })
    sb("POST", "/rest/v1/corse", {"operazione": op["chiave"], "esito": esito,
                                   "dettaglio": dettaglio, "righe": righe, "durata_ms": durata})
    print(f"  {esito} in {durata // 1000}s")
    if esito == "errore":
        print("  " + dettaglio[-400:].replace("\n", "\n  "))
    return esito


def main():
    ops = sb("GET", "/rest/v1/operazioni?select=*&order=ordine.asc") or []
    if "--stato" in sys.argv:
        for op in ops:
            print(f"  {op['chiave']:16} {'acceso' if op['attiva'] else 'spento':7} ogni {op['cadenza_minuti']:5} min  "
                  f"ultima {str(op.get('ultima_corsa') or 'mai')[:16]}  {op.get('ultimo_esito') or ''}")
        return
    # --forza accetta anche una catena: sync_smartlead,googlefit,bozze
    # (e' quella che manda Smartlead via webhook, 10/9). Nell'ordine dato.
    forza = sys.argv[sys.argv.index("--forza") + 1] if "--forza" in sys.argv else None
    fatte = 0
    if forza:
        # l'interruttore vale anche per il campanello: se Dre ha spento le bozze,
        # non si accendono da sole a ogni risposta (--anche-spente per forzare)
        anche_spente = "--anche-spente" in sys.argv
        per_chiave = {op["chiave"]: op for op in ops}
        for chiave in [c.strip() for c in forza.split(",") if c.strip()]:
            op = per_chiave.get(chiave)
            if not op:
                print(f"operazione sconosciuta: {chiave}")
            elif not op["attiva"] and not anche_spente:
                print(f"{chiave}: spenta, non la faccio partire")
            elif not op.get("comando"):
                print(f"{chiave}: non ha un comando (parte da GitHub)")
            else:
                corri(op); fatte += 1
        print(f"{fatte} operazioni fatte (forzate)")
        return
    for op in ops:
        if op.get("richiesta_ora") and not op.get("comando"):
            # «Fai ora» su una che parte da GitHub: si spegne la richiesta e si dice perche'
            sb("PATCH", f"/rest/v1/operazioni?chiave=eq.{op['chiave']}",
               {"richiesta_ora": False, "ultimo_dettaglio": "Questa parte da GitHub (backup.yml), non dal direttore"})
            continue
        if dovuta(op):
            corri(op); fatte += 1
    print(f"{fatte} operazioni fatte" if fatte else "niente di dovuto adesso")


if __name__ == "__main__":
    main()
