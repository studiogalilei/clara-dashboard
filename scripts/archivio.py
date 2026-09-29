#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""L'ARCHIVIO DELLA PIPELINE (Dre, 29/9/2026).

PERCHE' ESISTE
«Dobbiamo impostare un sistema per archiviare i lead, perche' la pipeline non
puo' essere sempre piena.» Misurato quel giorno: 83 aziende in pipeline, 72
ferme da piu' di un mese, e il lavoro vero erano 11 righe. Dentro le 72 c'erano
57 «no», il piu' vecchio di 127 giorni, e 13 positivi fermi che nessuno guardava
piu' perche' erano invisibili in mezzo ai rifiuti.

COSA FA
Toglie dalla pipeline chi e' finito, e solo quello. Non cancella niente: la
riga resta con tutta la sua storia, e chi torna a scrivere rientra da solo (lo
fa un trigger nel database, schema_v62, non una persona che se lo ricorda).

CHI ESCE, con regole scritte e nessuna scorciatoia:
  - negativo, e l'ultima sua mail e' di piu' di 30 giorni fa;
  - fuori target o soppresso, sempre;
  - negativo senza data dell'ultima mail (sono vecchi di mesi).

CHI NON ESCE MAI, anche se rientrerebbe nelle regole sopra:
  - chi ha una bozza o una domanda aperta in Posta;
  - chi aspetta una risposta da noi, o e' in coda per un ricontatto;
  - clienti, prove, avvii, call fissate;
  - i positivi e i tiepidi, qualunque eta' abbiano: quelli salgono nell'ordine,
    non spariscono (src/lib/urgenza.ts).

USO
    python3 scripts/archivio.py --prova     chi uscirebbe, senza toccare niente
    python3 scripts/archivio.py             archivia, dopo il Revisore
"""
import datetime
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from stanza import sb, di_clara                              # noqa: E402

PROVA = "--prova" in sys.argv
GIORNI = 30                     # un «no» piu' vecchio di cosi' esce di scena

INTOCCABILI = ("cliente", "prova", "avvio", "call_fissata", "conoscitiva", "tecnica")
VIVI = ("positivo", "tiepido", "rinvio", "ooo", "da_classificare")


def da_archiviare():
    """Chi esce, con il motivo scritto. Nessuno esce senza un motivo leggibile."""
    oggi = datetime.date.today()
    righe = sb("GET", "/rest/v1/prospects?select=id,company,email,stage,pipeline_stage,classificazione,"
                      "last_reply_at,awaiting_us,coda,archiviato_il"
                      "&fuori=eq.true&archiviato_il=is.null&limit=1000") or []
    # chi ha qualcosa di aperto in Posta non si tocca, mai
    aperte = {x["prospect_id"] for x in (sb("GET", "/rest/v1/proposte?select=prospect_id"
                                                   "&stato=in.(aperta,approvata,in_invio)") or [])
              if x.get("prospect_id")}
    fuori = []
    for r in righe:
        if r["id"] in aperte:
            continue
        if r.get("awaiting_us") or r.get("coda"):
            continue
        fase = (r.get("pipeline_stage") or r.get("stage") or "").lower()
        if fase in INTOCCABILI:
            continue
        classe = (r.get("classificazione") or "").lower()
        if classe in VIVI:
            continue
        d = (r.get("last_reply_at") or "")[:10]
        giorni = None
        if d:
            try:
                giorni = (oggi - datetime.date.fromisoformat(d)).days
            except ValueError:
                giorni = None
        if classe in ("fuori_target", "soppresso"):
            fuori.append((r, f"{classe.replace('_', ' ')}"))
        elif classe == "negativo" and giorni is not None and giorni >= GIORNI:
            fuori.append((r, f"ha detto no {giorni} giorni fa"))
        elif classe == "negativo" and giorni is None:
            fuori.append((r, "ha detto no, senza data dell'ultima mail"))
    return fuori


def main():
    fuori = da_archiviare()
    resta = len(sb("GET", "/rest/v1/prospects?select=id&fuori=eq.true&archiviato_il=is.null&limit=1000") or []) - len(fuori)
    print(f"archivio: {len(fuori)} da togliere dalla pipeline, ne restano {resta}")
    if not fuori:
        return
    if PROVA:
        for r, motivo in fuori[:40]:
            print(f"  {(r.get('company') or r.get('email') or '')[:36]:36s} {motivo}")
        if len(fuori) > 40:
            print(f"  ... e altre {len(fuori) - 40}")
        return

    # IL REVISORE (24/9, rinominato il 29/9): davanti a ogni azione di massa. Qui e'
    # reversibile (basta svuotare archiviato_il), ma sono comunque decine di righe insieme.
    try:
        from revisore import controlla
        tenute = controlla("archivio: tolgo dalla pipeline chi ha detto no da oltre un mese",
                           [dict(r, motivo=m) for r, m in fuori],
                           chiave=lambda r: r.get("email"),
                           irreversibile=False,
                           dove="crm",          # 29/9: non tocca Smartlead, solo un campo nostro
                           motivo=(f"pipeline a {len(fuori) + resta} righe, il lavoro vero e' {resta}. "
                                   f"Si scrive solo il campo archiviato_il: la riga resta intera e "
                                   f"chi riscrive rientra da solo (trigger schema_v62)."))
        tenuti = {t["id"] for t in tenute}
        fuori = [(r, m) for r, m in fuori if r["id"] in tenuti]
    except SystemExit:
        raise
    except Exception as e:                                    # noqa: BLE001
        print(f"  (Revisore non disponibile: {str(e)[:70]}) — mi fermo")
        return

    adesso = datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")
    fatte = 0
    for r, motivo in fuori:
        sb("PATCH", f"/rest/v1/prospects?id=eq.{r['id']}",
           {"archiviato_il": adesso, "archiviato_perche": motivo[:200]})
        fatte += 1
    print(f"archivio: {fatte} archiviate, restano {resta} in pipeline")
    if fatte:
        di_clara("controllo", f"Archivio: tolte {fatte} righe dalla pipeline (no vecchi di oltre {GIORNI} giorni). "
                              f"Restano {resta}. Chi riscrive rientra da solo.")


if __name__ == "__main__":
    main()
