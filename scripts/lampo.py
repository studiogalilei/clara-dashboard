#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""IL LAMPO: la consegna in un giro solo (Dre, 1/10/2026).

Il 1/10, misurato dal vivo: la catena risposta → fit → analisi → bozza →
approvazione → invio impiegava da 1h15 a 3h30, non perche' i pezzi fossero
lenti (il fit sono 2-4 minuti, l'analisi 4-6) ma perche' OGNI pezzo aspettava
il giro successivo del direttore. Dre: «ci mettiamo tanto, rispondiamo piu'
veloce li'».

Questo script fa la catena intera per chi ha risposto DA POCO, in un colpo:
per ogni risposta fresca chiama gli stessi pezzi di sempre (googlefit --uno,
analisi_auto --uno, bozze --email) e poi un giro di prima_risposta e manda.
Niente logica nuova: solo la stessa sequenza senza le attese fra i giri. I
cancelli restano tutti dove sono (whitelist, analisi allegata, 5 al giorno,
finestra, Revisore del testo): il lampo accorcia il tempo, non le regole.

I pezzi grossi restano ai loro giri: il lampo tocca al massimo LAMPO_MAX
aziende per corsa, le piu' recenti, e salta chi ha gia' una proposta aperta.

USO:  python3 scripts/lampo.py [--prova]
"""
import datetime
import os
import urllib.parse
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from stanza import sb                                      # noqa: E402

PROVA = "--prova" in sys.argv
FRESCA_ORE = int(sys.argv[sys.argv.index("--ore") + 1]) if "--ore" in sys.argv else 6          # oltre, ci pensano i giri normali: il lampo e' per chi aspetta adesso
LAMPO_MAX = 4           # aziende per corsa: il giro resta corto, il direttore non si blocca
RADICE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _corri(nome, argomenti, minuti=8):
    """Un pezzo della catena, col suo limite di tempo: se sfora si va avanti (regola 4 del 28/9)."""
    try:
        r = subprocess.run([sys.executable, os.path.join(RADICE, "scripts", nome)] + argomenti,
                           capture_output=True, text=True, timeout=minuti * 60, cwd=RADICE)
        coda = (r.stdout or "").strip().splitlines()[-1:] or [""]
        print(f"  {nome} {' '.join(argomenti)[:40]:40} → {coda[0][:90]}")
        return r.returncode == 0
    except subprocess.TimeoutExpired:
        print(f"  {nome}: oltre {minuti} minuti, lo lascio al suo giro")
        return False


def fresche():
    da = urllib.parse.quote((datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(hours=FRESCA_ORE)).isoformat())
    righe = sb("GET", "/rest/v1/prospects?select=id,email,company,name,last_reply_at,analysis_pdf,enriched"
                      f"&awaiting_us=eq.true&fuori=eq.false&last_reply_at=gte.{da}"
                      "&stage=not.in.(cliente,perso,call_fissata,rinviato)"
                      "&or=(classificazione.is.null,classificazione.not.in.(negativo,fuori_target,soppresso,nervoso))"
                      "&order=last_reply_at.desc&limit=20") or []
    aperte = {x["prospect_id"] for x in (sb("GET", "/rest/v1/proposte?select=prospect_id&stato=in.(aperta,approvata,in_invio)&limit=1000") or [])}
    return [p for p in righe if p["id"] not in aperte][:LAMPO_MAX]


def main():
    care = fresche()
    extra = ["--prova"] if PROVA else []
    if not care:
        # niente di fresco, ma gli approvati rimasti (1/10: UG col PDF arrivato dopo)
        # non devono aspettare il giro di qualcun altro
        print("lampo: nessuna risposta fresca; passo comunque il testimone a postino e approvazioni")
        _corri("prima_risposta.py", extra)
        _corri("manda.py", extra)
        return
    print(f"lampo: {len(care)} risposte fresche" + (" (prova)" if PROVA else ""))
    for p in care:
        nome = (p.get("company") or p.get("name") or p["email"])[:40]
        gf = (p.get("enriched") or {}).get("google_fit") or {}
        print(f"  ─ {nome} (risposta delle {str(p['last_reply_at'])[11:16]})")
        if not gf.get("sito_letto"):
            _corri("googlefit.py", ["--uno", p["email"]] + extra)
        if not p.get("analysis_pdf"):
            _corri("analisi_auto.py", ["--uno", p["email"]] + extra, minuti=12)
        _corri("bozze.py", ["--email", p["email"]] + extra)
    # i cancelli veri: approvazione (con tutti i freni) e postino, una volta per tutti
    _corri("prima_risposta.py", extra)
    _corri("manda.py", extra)


if __name__ == "__main__":
    main()
