#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""IL DOCUMENTO SU GOOGLE (15/9/2026): quello che si modifica e si commenta.

PERCHE'
Dre (12/9): «vorrei che appena hanno concluso, Clara salvi il documento in
automatico da qualche parte, tipo Canva». Canva no: i documenti non vivono
li'. Vivono in Google, dove c'e' gia' l'archivio del cliente, i permessi, i
commenti e la storia delle versioni. Quindi i documenti formali restano PDF
(motore `src/lib/documento.ts`, che rispetta il brand al millimetro), e
quelli che devono essere letti, corretti e commentati insieme nascono come
Google Doc dentro la cartella di quel cliente.

COSA FA
Prende un modello in JSON (gli stessi di `docs/modelli/doc-*.json`), crea il
Google Doc nella cartella del cliente nel Drive condiviso, scrive il
contenuto con la gerarchia giusta (titolo, sezioni, paragrafi, elenchi) e
restituisce il link. Il link finisce anche nella Scheda dell'azienda, cosi'
si ritrova da tutte e due le parti.

USO
  python3 scripts/doc_google.py --modello docs/modelli/doc-presentazione.json --sg 12
  python3 scripts/doc_google.py --modello <file> --cliente "Klavzar"
  aggiungi --prova per vedere cosa farebbe
"""

import datetime
import json
import os
import sys
import urllib.parse

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))   # i moduli comuni stanno in scripts/
from stanza import sb                                      # noqa: E402
from google_api import g, cartella                         # noqa: E402

DOCS = "https://docs.googleapis.com/v1/documents"
DRIVE = "https://www.googleapis.com/drive/v3"
CLIENTI = "1r1jtdy1ulJHrSARauKHH20HvgP5yNMqT"    # «1 Clienti» nel Drive condiviso


def paragrafi(doc):
    """Il modello diventa una lista di (testo, stile). Stile: TITLE, SUBTITLE,
    HEADING_1, HEADING_2, NORMAL_TEXT, BULLET."""
    fuori = []
    cop = doc.get("copertina") or {}
    if cop.get("occhiello"):
        fuori.append((cop["occhiello"], "SUBTITLE"))
    if cop.get("titolo"):
        fuori.append((cop["titolo"], "TITLE"))
    if cop.get("sottotitolo"):
        fuori.append((cop["sottotitolo"], "NORMAL_TEXT"))
    if cop.get("cliente") or cop.get("riferimento"):
        riga = ", ".join(x for x in [cop.get("cliente"), cop.get("riferimento"), cop.get("data")] if x)
        fuori.append((riga, "NORMAL_TEXT"))

    for b in doc.get("blocchi", []):
        t = b.get("tipo")
        if t == "kicker":
            fuori.append((b["testo"], "SUBTITLE"))
        elif t == "h1":
            fuori.append((b["testo"], "HEADING_1"))
        elif t == "h2":
            fuori.append((b["testo"], "HEADING_2"))
        elif t == "p":
            fuori.append((b["testo"], "NORMAL_TEXT"))
        elif t == "elenco":
            for v in b.get("voci", []):
                fuori.append((v, "BULLET"))
        elif t == "riquadro":
            fuori.append((b.get("titolo", ""), "HEADING_2"))
            for v in b.get("voci", []):
                fuori.append((v, "BULLET"))
        elif t == "due_colonne":
            for lato in ("sinistra", "destra"):
                parte = b.get(lato) or {}
                fuori.append((parte.get("titolo", ""), "HEADING_2"))
                for v in parte.get("voci", []):
                    fuori.append((v, "BULLET"))
        elif t == "tappe":
            for x in b.get("tappe", []):
                fuori.append((f"{x.get('quando', '')}, {x.get('titolo', '')}", "HEADING_2"))
                fuori.append((x.get("testo", ""), "NORMAL_TEXT"))
        elif t == "numeri":
            for v in b.get("voci", []):
                fuori.append((f"{v.get('valore', '')}, {v.get('etichetta', '')}", "BULLET"))
        elif t == "tabella":
            intestazioni = [c.get("testo", "") for c in b.get("colonne", [])]
            fuori.append((" | ".join(intestazioni), "HEADING_2"))
            for r in b.get("righe", []):
                celle = [c.get("testo", "") for c in r]
                sotto = [c.get("sotto") for c in r if c.get("sotto")]
                riga = " | ".join(celle) + (f" ({', '.join(sotto)})" if sotto else "")
                fuori.append((riga, "BULLET"))
        elif t == "anagrafica":
            for c in b.get("colonne", []):
                fuori.append((c.get("titolo", ""), "HEADING_2"))
                for r in c.get("righe", []):
                    fuori.append((r, "NORMAL_TEXT"))
    return [(t.strip(), s) for t, s in fuori if (t or "").strip()]


def crea(nome, cartella_id, email=None):
    fatto = g("POST", f"{DRIVE}/files?supportsAllDrives=true&fields=id,webViewLink",
              {"name": nome, "mimeType": "application/vnd.google-apps.document",
               "parents": [cartella_id]}, email=email)
    return fatto["id"], fatto.get("webViewLink")


def riempi(doc_id, righe, email=None):
    """Prima tutto il testo in un colpo, poi gli stili sulle righe giuste:
    cosi' gli indici non si spostano sotto i piedi."""
    testo = "".join(f"{t}\n" for t, _ in righe)
    g("POST", f"{DOCS}/{doc_id}:batchUpdate",
      {"requests": [{"insertText": {"location": {"index": 1}, "text": testo}}]}, email=email)

    richieste, i = [], 1
    for t, stile in righe:
        fine = i + len(t) + 1
        vero = "NORMAL_TEXT" if stile == "BULLET" else stile
        richieste.append({"updateParagraphStyle": {
            "range": {"startIndex": i, "endIndex": fine},
            "paragraphStyle": {"namedStyleType": vero},
            "fields": "namedStyleType"}})
        if stile == "BULLET":
            richieste.append({"createParagraphBullets": {
                "range": {"startIndex": i, "endIndex": fine},
                "bulletPreset": "BULLET_DISC_CIRCLE_SQUARE"}})
        i = fine
    # a blocchi: la Docs API non ama le richieste infinite in una volta
    for k in range(0, len(richieste), 60):
        g("POST", f"{DOCS}/{doc_id}:batchUpdate", {"requests": richieste[k:k + 60]}, email=email)


def azienda(sg=None, nome=None):
    if sg:
        r = sb("GET", f"/rest/v1/prospects?select=id,company,name,sg_id&sg_id=eq.{sg}&limit=1") or []
    else:
        r = sb("GET", f"/rest/v1/prospects?select=id,company,name,sg_id&company=ilike.*{urllib.parse.quote(nome)}*&limit=1") or []
    return r[0] if r else None


def main():
    prova = "--prova" in sys.argv
    def arg(nome, difetto=None):
        return sys.argv[sys.argv.index(nome) + 1] if nome in sys.argv else difetto

    modello = arg("--modello")
    if not modello or not os.path.exists(modello):
        print("serve --modello <file.json>")
        return
    doc = json.load(open(modello))
    righe = paragrafi(doc)

    p = None
    if arg("--sg") or arg("--cliente"):
        p = azienda(arg("--sg"), arg("--cliente"))
        if not p:
            print("azienda non trovata")
            return

    nome_doc = (doc.get("copertina") or {}).get("titolo") or doc.get("tipo") or "Documento"
    if p:
        nome_doc = f"{nome_doc}, {p.get('company') or p.get('name')}"
    print(f"{nome_doc}: {len(righe)} paragrafi")
    if prova:
        for t, s in righe[:12]:
            print(f"  {s:12} {t[:70]}")
        print("  (prova: non scrivo niente)")
        return

    dove = CLIENTI
    if p:
        etichetta = f"SG-{p['sg_id']} {p.get('company') or p.get('name')}" if p.get("sg_id") else (p.get("company") or p.get("name"))
        dove = cartella(etichetta, CLIENTI)
    doc_id, link = crea(nome_doc, dove)
    riempi(doc_id, righe)
    print(f"fatto: {link}")

    if p:
        sb("POST", "/rest/v1/interactions", {
            "prospect_id": p["id"], "at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "kind": "nota", "body": f"Documento su Google: {nome_doc}\n{link}", "ref": f"gdoc:{doc_id}"})


if __name__ == "__main__":
    main()
