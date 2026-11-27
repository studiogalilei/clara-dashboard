#!/usr/bin/env python3
"""IL LINKEDIN DESK, il lato della routine (27/11/2026).

Dre registra o scrive dal telefono (#/d/linkedin), la riga entra in `linkedin_post` con stato «da_scrivere».
La routine «LinkedIn Desk: scrivi i post» (Claude Code in cloud, sull'abbonamento di Dre) usa questo script:

  python3 scripts/linkedin_desk.py prendi            # prende i post da scrivere (li segna «in_scrittura»), stampa JSON
  python3 scripts/linkedin_desk.py foto <id> <file>  # scarica la foto del post, per guardarla
  python3 scripts/linkedin_desk.py salva <id> <versioni.json>   # due versioni: [{framework, caso, testo, giudice}]
  python3 scripts/linkedin_desk.py errore <id> "perche'"
  python3 scripts/linkedin_desk.py usati             # i framework usati nelle ultime due settimane (per non ripeterli)
  python3 scripts/linkedin_desk.py riempi [giorni]   # i giorni vuoti dei prossimi N (7) diventano post automatici da scrivere
  python3 scripts/linkedin_desk.py settimana         # la domenica: riempie la settimana che arriva (gli altri giorni non fa niente)
  python3 scripts/linkedin_desk.py persone           # chi riceve le persone del giorno, quante ne mancano a 20, mercato, zona
  python3 scripts/linkedin_desk.py aggiungi <utente> <persone.json>   # [{azienda, settore, citta, persona, ruolo, profilo, cerca, perche, fonte, segnale}]

Dal 27/11 (v123) ogni persona ha un post al giorno: quelli «auto» li prepara il sistema (senza dettato: tema scelto
dalla routine), quelli «mio» nascono da un audio o un testo e prendono il posto dell'automatico del loro giorno.

I testi dei post non vanno mai nel repository (e' pubblico): stanno solo nel database.
"""
import datetime
import json
import sys
import urllib.parse
import urllib.request
from zoneinfo import ZoneInfo

from stanza import CHIAVE, URL, sb, sb_tutte


def prendi():
    righe = sb("GET", "/rest/v1/linkedin_post?stato=eq.da_scrivere&order=origine.desc,uscita_il.asc.nullsfirst&limit=10"
                      "&select=id,autore,origine,uscita_il,dettato,foto,richiesta,versioni,scelta,testo")
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
    r = sb("GET", f"/rest/v1/linkedin_post?id=eq.{id_}&select=uscita_il")
    # un post con il suo giorno e' programmato: esce da solo, la persona puo' cambiarlo fino all'ora
    stato = "programmato" if r and r[0].get("uscita_il") else "bozza"
    sb("PATCH", f"/rest/v1/linkedin_post?id=eq.{id_}",
       {"versioni": versioni, "stato": stato, "richiesta": None, "scelta": 0, "testo": None, "errore": None})
    print(f"salvate {len(versioni)} versioni")


def errore(id_, perche):
    sb("PATCH", f"/rest/v1/linkedin_post?id=eq.{id_}", {"stato": "errore", "errore": perche[:400]})


def usati():
    da = (datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=14)).strftime("%Y-%m-%dT%H:%M:%SZ")
    righe = sb("GET", "/rest/v1/linkedin_post?select=versioni,scelta&stato=in.(bozza,programmato,pubblicato)"
                      f"&creato_il=gte.{da}&limit=100") or []
    print(json.dumps(sorted({(r["versioni"][r.get("scelta") or 0] or {}).get("framework", "")
                             for r in righe if r.get("versioni")} - {""}), ensure_ascii=False))


# Dre, 27/11: «so che sono 3 post a settimana e va bene cosi'; l'altra persona puo' schedulare un post nei giorni liberi».
GIORNI_AUTOMATICI = {0, 2, 4}   # lunedi', mercoledi', venerdi'


def riempi(giorni=7):
    """Per ogni persona che vuole i post automatici: lunedi', mercoledi' e venerdi' dei prossimi N giorni, se vuoti,
    ricevono un post da scrivere. Gli altri giorni restano liberi per i post della persona."""
    roma = ZoneInfo("Europe/Rome")
    oggi = datetime.datetime.now(roma).date()
    nuovi = 0
    for prof in sb("GET", "/rest/v1/linkedin_profilo?automatici=eq.true&select=utente,ora") or []:
        fino = (datetime.datetime.combine(oggi + datetime.timedelta(days=giorni + 1), datetime.time(), roma)).isoformat()
        vivi = sb("GET", f"/rest/v1/linkedin_post?autore=eq.{prof['utente']}&stato=not.in.(scartato,errore)"
                         f"&uscita_il=lt.{urllib.parse.quote(fino)}&select=uscita_il") or []
        presi = {datetime.datetime.fromisoformat(v["uscita_il"]).astimezone(roma).date() for v in vivi if v.get("uscita_il")}
        h, m = (int(x) for x in prof["ora"].split(":"))
        for i in range(1, giorni + 1):   # da domani: oggi non si riempie all'ultimo
            g = oggi + datetime.timedelta(days=i)
            if g in presi or g.weekday() not in GIORNI_AUTOMATICI:
                continue
            quando = datetime.datetime.combine(g, datetime.time(h, m), roma)
            sb("POST", "/rest/v1/linkedin_post", {"autore": prof["utente"], "origine": "auto", "stato": "da_scrivere",
                                                  "dettato": "", "uscita_il": quando.isoformat()})
            nuovi += 1
    print(f"post automatici da scrivere: {nuovi}")


def settimana():
    """Dre, 27/11: «ogni settimana, un giorno vedi tu, prepara i post per tutta la settimana». Si fa la domenica
    (ora di Roma), per i 7 giorni dopo; se la settimana che arriva e' gia' piena non si aggiunge niente."""
    if datetime.datetime.now(ZoneInfo("Europe/Rome")).weekday() != 6:
        print("non e' domenica: la settimana si prepara la domenica")
        return
    riempi(8)


PERSONE_AL_GIORNO = 20


def persone():
    """Per chi ha acceso le persone del giorno: quante ne mancano a 20 da fare, il mercato, la zona e le aziende gia' viste
    (mai riproporre la stessa azienda)."""
    fuori = []
    for prof in sb("GET", "/rest/v1/linkedin_profilo?persone=eq.true&select=utente,nome,mercato,zona") or []:
        u = prof["utente"]
        da_fare = sb("GET", f"/rest/v1/linkedin_persone?autore=eq.{u}&stato=eq.da_fare&select=id") or []
        viste = sb_tutte(f"/rest/v1/linkedin_persone?autore=eq.{u}&select=id,azienda")
        fuori.append({"utente": u, "nome": prof["nome"], "mercato": prof["mercato"], "zona": prof["zona"],
                      "mancano": max(0, PERSONE_AL_GIORNO - len(da_fare)), "gia_viste": sorted({v["azienda"] for v in viste})})
    print(json.dumps(fuori, ensure_ascii=False, indent=1))


def aggiungi(utente, file_):
    righe = json.load(open(file_, encoding="utf-8"))
    messe = 0
    for r in righe:
        if not (r.get("azienda") and r.get("perche")):
            continue
        r = {k: r.get(k) for k in ("azienda", "settore", "citta", "persona", "ruolo", "profilo", "cerca", "perche", "fonte", "segnale")}
        r["segnale"] = r["segnale"] or "annuncio"
        r["autore"] = utente
        try:
            sb("POST", "/rest/v1/linkedin_persone", r)
            messe += 1
        except RuntimeError as e:
            if "duplicate" not in str(e) and "23505" not in str(e):
                raise
    print(f"aziende aggiunte: {messe} su {len(righe)}")


if __name__ == "__main__":
    a = sys.argv[1:]
    {"prendi": lambda: prendi(), "foto": lambda: foto(a[1], a[2]), "salva": lambda: salva(a[1], a[2]),
     "errore": lambda: errore(a[1], a[2]), "usati": lambda: usati(),
     "riempi": lambda: riempi(int(a[1]) if len(a) > 1 else 7), "settimana": lambda: settimana(),
     "persone": lambda: persone(), "aggiungi": lambda: aggiungi(a[1], a[2])}[a[0]]()
