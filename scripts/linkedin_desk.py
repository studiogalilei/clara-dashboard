#!/usr/bin/env python3
"""IL LINKEDIN DESK, il lato della routine (27/11/2026).

Dre registra o scrive dal telefono (#/d/linkedin), la riga entra in `linkedin_post` con stato «da_scrivere».
La routine «LinkedIn Desk: scrivi i post» (Claude Code in cloud, sull'abbonamento di Dre) usa questo script:

  python3 scripts/linkedin_desk.py prendi            # prende i post da scrivere (li segna «in_scrittura»), stampa JSON
  python3 scripts/linkedin_desk.py foto <id> <file>  # scarica la foto del post, per guardarla
  python3 scripts/linkedin_desk.py salva <id> <versioni.json>   # due versioni: [{framework, caso, testo, giudice}]
  python3 scripts/linkedin_desk.py errore <id> "perche'"
  python3 scripts/linkedin_desk.py usati             # i framework usati nelle ultime due settimane (per non ripeterli)

I testi dei post non vanno mai nel repository (e' pubblico): stanno solo nel database.
"""
import datetime
import json
import sys
import urllib.parse
import urllib.request

from stanza import CHIAVE, URL, sb


def prendi():
    righe = sb("GET", "/rest/v1/linkedin_post?stato=eq.da_scrivere&order=creato_il.asc&limit=5"
                      "&select=id,autore,dettato,foto,richiesta,versioni,scelta,testo")
    presi = []
    for r in righe or []:
        # si segna solo se e' ancora da scrivere: due giri insieme non scrivono lo stesso post
        ok = sb("PATCH", f"/rest/v1/linkedin_post?id=eq.{r['id']}&stato=eq.da_scrivere",
                {"stato": "in_scrittura", "errore": None}, {"Prefer": "return=representation"})
        if ok:
            # chi scrive (v122): il suo profilo dice chi e', di cosa parla e come parla
            prof = sb("GET", f"/rest/v1/linkedin_profilo?utente=eq.{r['autore']}&select=nome,ruolo,temi,voce") if r.get("autore") else []
            r["profilo"] = prof[0] if prof else None
            presi.append(r)
    print(json.dumps(presi, ensure_ascii=False, indent=1))


def foto(id_, dove):
    r = sb("GET", f"/rest/v1/linkedin_post?id=eq.{id_}&select=foto")
    percorso = r[0]["foto"] if r else None
    if not percorso:
        print("nessuna foto")
        return
    req = urllib.request.Request(f"{URL.rstrip('/')}/storage/v1/object/linkedin/{urllib.parse.quote(percorso)}",
                                 headers={"apikey": CHIAVE, "Authorization": "Bearer " + CHIAVE})
    with urllib.request.urlopen(req, timeout=60) as f, open(dove, "wb") as out:
        out.write(f.read())
    print(dove)


def salva(id_, file_):
    versioni = json.load(open(file_, encoding="utf-8"))
    assert isinstance(versioni, list) and versioni and all(v.get("testo") and v.get("framework") for v in versioni), \
        "servono versioni con framework e testo"
    sb("PATCH", f"/rest/v1/linkedin_post?id=eq.{id_}",
       {"versioni": versioni, "stato": "bozza", "richiesta": None, "scelta": 0, "testo": None, "errore": None})
    print(f"salvate {len(versioni)} versioni")


def errore(id_, perche):
    sb("PATCH", f"/rest/v1/linkedin_post?id=eq.{id_}", {"stato": "errore", "errore": perche[:400]})


def usati():
    da = (datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=14)).strftime("%Y-%m-%dT%H:%M:%SZ")
    righe = sb("GET", "/rest/v1/linkedin_post?select=versioni,scelta&stato=in.(bozza,programmato,pubblicato)"
                      f"&creato_il=gte.{da}&limit=100") or []
    print(json.dumps(sorted({(r["versioni"][r.get("scelta") or 0] or {}).get("framework", "")
                             for r in righe if r.get("versioni")} - {""}), ensure_ascii=False))


if __name__ == "__main__":
    a = sys.argv[1:]
    {"prendi": lambda: prendi(), "foto": lambda: foto(a[1], a[2]), "salva": lambda: salva(a[1], a[2]),
     "errore": lambda: errore(a[1], a[2]), "usati": lambda: usati()}[a[0]]()
