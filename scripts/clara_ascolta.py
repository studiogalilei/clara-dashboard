#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""CLARA ASCOLTA — quello che la fa rispondere nella chat (7/9/2026).

PERCHE' ESISTE
Il pannello di Clara nella Dashboard era «un coso svolazzante che non
risponde» (Dre): dietro aveva delle espressioni regolari per «fissa una
call» e basta. Il cervello (cervello.py) gira sul Mac di Dre col suo piano
Claude, e il browser non puo' chiamarlo direttamente. Quindi questo processo
sta in ascolto: ogni pochi secondi guarda se Dre ha scritto qualcosa nella
chat, fa leggere al cervello la conversazione e lo stato delle cose, e
scrive la risposta di Clara. Il pannello la vede al prossimo giro.

Funziona da qualunque dispositivo (telefono compreso) finche' il Mac di Dre
e' acceso. Se e' spento, i messaggi restano li' e Clara risponde quando
torna: nessuna domanda si perde.

COSA NON FA
Non tocca la pipeline. Se dalla conversazione capisce che c'e' qualcosa da
cambiare, lo mette nella stanza come proposta: e' Dre che dice si'.

USO
  python3 scripts/clara_ascolta.py            resta in ascolto
  python3 scripts/clara_ascolta.py --una      un giro solo (per provare)
"""

import json
import os
import re
import sys
import time
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cervello                                            # noqa: E402
from stanza import sb, di_clara, proponi                   # noqa: E402

OGNI = 5                     # secondi fra un ascolto e l'altro
STATO = os.path.expanduser("~/.odyn-clara-ascolta.json")
PERSONA_FILE = os.path.expanduser(
    "~/Documents/Obsidian/studiogalilei/Sistema Operativo Studio Galilei/ODYN Cockpit/prompts/CLARA.md")

PERSONA_BASE = """Sei Clara, la segretaria di Studio Galilei (agenzia Google Ads). Parli con
Dre, il fondatore. Italiano informale e diretto, frasi corte, niente fuffa,
niente elenchi puntati se non servono, mai il trattino lungo. Dai del tu.
Non inventare dati: se non sai una cosa lo dici. Se Dre ti chiede di fare
qualcosa che cambia la pipeline (spostare, scartare, segnare perso, cambiare
una classificazione) NON dire che l'hai fatto: di' che glielo metti nella tua
stanza come proposta, e lui conferma da li'."""

ISTRUZIONI_RISPOSTA = """Rispondi a Dre. Massimo 4 righe, a meno che non chieda un elenco.
Se nella conversazione c'e' una cosa concreta da fare sulla pipeline, chiudi
la risposta con UNA riga nel formato esatto, da sola:
PROPOSTA | tipo | titolo | perche
dove tipo e' uno fra: classifica, scarta, perso, tornato, richiesta, data, avanza.
Se non c'e' niente da proporre, non scrivere quella riga."""


def leggi_stato():
    try:
        return json.load(open(STATO, encoding="utf-8"))
    except Exception:
        return {}


def salva_stato(s):
    try:
        json.dump(s, open(STATO, "w", encoding="utf-8"))
    except Exception:
        pass


def persona():
    base = PERSONA_BASE + cervello.istruzione("chat")
    try:
        t = open(PERSONA_FILE, encoding="utf-8").read()
        return base + "\n\nIL SUO CARATTERE E MANDATO, DAL FILE DI DRE:\n" + t[:6000]
    except Exception:
        return base


def contesto(msg):
    """Quello che Clara deve sapere per rispondere a questo messaggio."""
    pezzi = []
    # la conversazione recente di questa persona
    owner = msg.get("owner")
    filtro = f"owner.eq.{owner}" if owner else "owner.is.null"
    conv = sb("GET", f"/rest/v1/clara_messaggi?select=tipo,testo,at&or=({filtro},owner.is.null)"
                     f"&tipo=neq.saluto&order=at.desc&limit=14") or []
    righe = []
    for m in reversed(conv):
        chi = "Dre" if m["tipo"] == "dre" else "Clara"
        righe.append(f"{chi}: {' '.join(m['testo'].split())[:400]}")
    pezzi.append("LA CONVERSAZIONE FINORA:\n" + "\n".join(righe))

    # la persona di cui si parla, se c'e'
    pid = msg.get("prospect_id")
    testo = msg.get("testo", "")
    if not pid:
        # prova a riconoscere un nome d'azienda nel messaggio
        # le parole con la maiuscola in tutto il messaggio, le coppie prima
        # («Sea Quest»), poi le singole piu' lunghe. Prima provava le prime sei
        # parole e «Sea Quest Hawaii» non arrivava mai al giro
        comuni = {"Ciao", "Clara", "Dre", "Cosa", "Come", "Quando", "Chi", "Perche", "Allora", "Grazie"}
        maiuscole = [w for w in re.findall(r"\b[A-ZÀ-Ý][\w&'.-]{2,}", testo) if w not in comuni]
        candidati = [f"{a} {b}" for a, b in zip(maiuscole, maiuscole[1:])] + sorted(maiuscole, key=len, reverse=True)
        for w in candidati[:10]:
            trovati = sb("GET", f"/rest/v1/prospects?select=id&company=ilike.*{w}*&order=last_reply_at.desc.nullslast&limit=1") or []
            if trovati:
                pid = trovati[0]["id"]
                break
    if pid:
        p = (sb("GET", f"/rest/v1/prospects?id=eq.{pid}&select=company,name,email,stage,"
                       f"pipeline_stage,classificazione,last_reply_at,next_action,next_action_date,"
                       f"canone,fuori,sg_id&limit=1") or [None])[0]
        if p:
            pezzi.append("LA PERSONA DI CUI SI PARLA:\n" + json.dumps(p, ensure_ascii=False))
            ult = sb("GET", f"/rest/v1/interactions?prospect_id=eq.{pid}&select=kind,body,at"
                            f"&order=at.desc&limit=4") or []
            if ult:
                pezzi.append("LE SUE ULTIME INTERAZIONI:\n" + "\n".join(
                    f"- {u['at'][:10]} [{u['kind']}] {' '.join((u.get('body') or '').split())[:300]}"
                    for u in ult))
            msg["_pid"] = pid

    # il quadro di oggi, in due righe
    aspettano = sb("GET", "/rest/v1/prospects?awaiting_us=eq.true&fuori=eq.false"
                          "&select=company,name,classificazione,last_reply_at"
                          "&order=last_reply_at.desc&limit=6") or []
    caldi = sb("GET", "/rest/v1/prospects?awaiting_us=eq.true&fuori=eq.false&classificazione=eq.positivo"
                      "&select=company,name,last_reply_at&order=last_reply_at.asc&limit=10") or []
    if caldi:
        pezzi.append("I POSITIVI CHE ASPETTANO UNA RISPOSTA DA PIU' TEMPO (dal piu' vecchio):\n" + "\n".join(
            f"- {c.get('company') or c.get('name')}: ultima sua mail {str(c.get('last_reply_at') or '')[:10]}" for c in caldi))
    pezzi.append("OGGI: " + datetime.now().strftime("%A %d %B %Y, %H:%M") +
                 f". Gli ultimi che aspettano una risposta: " +
                 "; ".join(f"{a.get('company') or a.get('name')} [{a.get('classificazione')}]" for a in aspettano))
    return "\n\n".join(pezzi)


RIGA_PROPOSTA = re.compile(r"^\s*PROPOSTA\s*\|\s*(\w+)\s*\|\s*(.+?)\s*\|\s*(.+?)\s*$", re.M)


def rispondi(msg):
    prompt = (persona() + "\n\n" + contesto(msg) + "\n\n" + ISTRUZIONI_RISPOSTA +
              "\n\nL'ULTIMO MESSAGGIO DI DRE:\n" + msg["testo"])
    try:
        grezzo = cervello._chiedi(prompt)
    except Exception as e:
        di_clara("controllo", "Non riesco a pensare adesso: il cervello non risponde. Riprovo fra poco.",
                 owner=msg.get("owner"))
        print("  ! cervello:", str(e)[:120])
        return
    testo = grezzo.strip()
    coda = ""
    for m in RIGA_PROPOSTA.finditer(testo):
        tipo, titolo, perche = m.groups()
        if tipo in ("classifica", "scarta", "perso", "tornato", "richiesta", "data", "avanza"):
            try:
                proponi(tipo, titolo, prospect_id=msg.get("_pid"), perche=perche, owner=msg.get("owner"))
            except Exception as e:
                # la stanza non c'e' ancora (schema_v8 non applicato): la risposta
                # arriva lo stesso, la proposta si perde e lo si dice
                print("  ! proposta non salvata:", str(e)[:100])
                coda = " (Non sono riuscita a salvare la proposta: manca la mia stanza sul database.)"
    testo = (RIGA_PROPOSTA.sub("", testo).strip() + coda).strip()
    if not testo:
        testo = "Fatto: te l'ho messa nella mia stanza, confermi da li'."
    di_clara("clara", testo, prospect_id=msg.get("_pid"), owner=msg.get("owner"))
    print(f"  Clara: {' '.join(testo.split())[:90]}")


def un_giro(stato):
    ultimo = stato.get("ultimo_id", 0)
    nuovi = sb("GET", f"/rest/v1/clara_messaggi?tipo=eq.dre&id=gt.{ultimo}"
                      f"&select=id,testo,owner,prospect_id,at&order=id.asc&limit=10") or []
    for msg in nuovi:
        print(f"{datetime.now().strftime('%H:%M:%S')}  Dre: {' '.join(msg['testo'].split())[:90]}")
        rispondi(msg)
        stato["ultimo_id"] = msg["id"]
        salva_stato(stato)
    return len(nuovi)


def main():
    stato = leggi_stato()
    if "ultimo_id" not in stato:
        # al primo avvio non si risponde a tutta la storia passata
        ult = sb("GET", "/rest/v1/clara_messaggi?select=id&order=id.desc&limit=1") or [{"id": 0}]
        stato["ultimo_id"] = ult[0]["id"]
        salva_stato(stato)
    print("Clara ascolta." + (" Un giro solo." if "--una" in sys.argv else " Ctrl+C per fermarla."))
    while True:
        try:
            un_giro(stato)
        except Exception as e:
            print("  ! ", str(e)[:150])
        if "--una" in sys.argv:
            break
        time.sleep(OGNI)


if __name__ == "__main__":
    main()
