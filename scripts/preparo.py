#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""CLARA PREPARA LE CALL (16/9/2026).

PERCHE'
Dre: «Clara deve essere come una che cerca di rendersi il piu' utile
possibile: se abbiamo una call, in modo proattivo fa ricerche sul cliente,
prepara cose che possono servire e le mette li'».

Il momento in cui serve sapere tutto di un cliente e' i cinque minuti prima
della call, ed e' esattamente il momento in cui nessuno ha tempo di andare a
leggere la scheda. Quindi la scheda la legge Clara, la sera prima, e lascia
dodici righe: chi sono, a che punto siamo, cosa chiedere, a cosa stare
attenti. Nient'altro: se serve altro c'e' la scheda.

COSA FA
Per ogni call delle prossime 30 ore attaccata a un'azienda: raccoglie quello
che sappiamo (scheda, ultime mail e call, progetti, preventivi, quanto paga),
lo fa leggere al cervello e scrive il risultato sulla riga dell'agenda
(schema_v43). L'app lo mostra sulla call, e in Oggi.

USO
  python3 scripts/preparo.py            prepara quelle delle prossime 30 ore
  python3 scripts/preparo.py --prova    dice cosa preparerebbe, non scrive
  python3 scripts/preparo.py --ore 72   piu' avanti
"""

import datetime
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from stanza import sb                                      # noqa: E402
import cervello                                            # noqa: E402

CALL = ("conoscitiva", "tecnica", "avvio", "call", "prep")
# se la scheda non e' cambiata, la preparazione di ieri va bene: non si
# rifa' ogni ora la stessa cosa (e non si paga due volte)
FRESCA_ORE = 20


def quando(iso):
    try:
        d = datetime.datetime.fromisoformat(re.sub(r"\.\d+", "", (iso or "").replace("Z", "+00:00")))
    except Exception:
        return None
    return d if d.tzinfo else d.replace(tzinfo=datetime.timezone.utc)


def dati_di(pid):
    """Tutto quello che sappiamo di quell'azienda, in un testo solo."""
    p = (sb("GET", f"/rest/v1/prospects?select=id,company,name,email,sector,city,website,descrizione,"
                   f"stage,pipeline_stage,classificazione,canone,contratto,notes,next_action,next_action_date,"
                   f"analysis_sent_at,last_reply_at,prova_fine,enriched&id=eq.{pid}") or [None])[0]
    if not p:
        return None, None
    arr = p.pop("enriched", None) or {}
    pezzi = ["SCHEDA: " + ", ".join(f"{k}={v}" for k, v in p.items() if v not in (None, "", False) and k != "id")]
    # IL BILANCIO PRIMA DELLA CALL (Dre, 26/9): «cosi' so gia' come impostarmi, che domande
    # fare e che lingo usare». Se manca, si prende adesso da OpenAPI (una volta, 0,10 €).
    bil = arr.get("bilancio") or {}
    if not bil.get("fatturato") and not bil.get("fonte") and "--prova" not in sys.argv:
        try:
            import prezzo
            nuovo = prezzo.bilancio_openapi({**p, "enriched": arr})
            if nuovo:
                fresco = (sb("GET", f"/rest/v1/prospects?select=enriched&id=eq.{pid}") or [{}])[0]
                arr = dict(fresco.get("enriched") or {}); arr["bilancio"] = {**bil, **{k: v for k, v in nuovo.items() if v not in (None, "")}}
                sb("PATCH", f"/rest/v1/prospects?id=eq.{pid}", {"enriched": arr}); bil = arr["bilancio"]
        except Exception as e:                                # noqa: BLE001
            print(f"    bilancio non preso: {str(e)[:60]}")
    if bil.get("fatturato"):
        pezzi.append("BILANCIO (fonte " + str(bil.get("fonte") or "scheda") + "): " +
                     ", ".join(f"{k}={bil[k]}" for k in ("fatturato", "utile", "anno", "dipendenti", "forma") if bil.get(k)))
    pz = arr.get("prezzo") or {}
    if pz.get("fascia"):
        pezzi.append(f"PREZZO SUGGERITO (interno, non si dice in call): {pz['fascia'][0]}-{pz['fascia'][1]} €/mese, affidabilita' {pz.get('affidabilita')}, "
                     f"spesa Ads sostenibile ~{pz.get('spesa_ads_mese')} €/mese" + (f", flag: {'; '.join(pz['flag'])}" if pz.get("flag") else ""))
    fit = arr.get("google_fit") or {}
    if fit.get("verdetto"):
        pezzi.append("GOOGLE FIT: " + ", ".join(f"{k}={fit[k]}" for k in ("verdetto", "settore", "tipo", "cosa_fa", "ticket_min", "ticket_max", "zona", "motivo") if fit.get(k)))

    storia = sb("GET", f"/rest/v1/interactions?select=at,kind,body&prospect_id=eq.{pid}"
                       f"&order=at.desc&limit=12") or []
    if storia:
        pezzi.append("COSA CI SIAMO DETTI (dal piu' recente):\n" + "\n".join(
            f"- [{(r.get('at') or '')[:10]}, {r.get('kind')}] {(r.get('body') or '')[:700]}" for r in storia))

    prog = sb("GET", f"/rest/v1/progetti?select=nome,natura,stato,valore,scadenza,note,imparato"
                     f"&prospect_id=eq.{pid}&limit=8") or []
    if prog:
        pezzi.append("PROGETTI: " + str(prog))

    quote = sb("GET", f"/rest/v1/preventivi?select=numero,titolo,importo,mensile,stato,inviato_il"
                      f"&prospect_id=eq.{pid}&order=creato_il.desc&limit=3") or []
    if quote:
        pezzi.append("PREVENTIVI: " + str(quote))

    nome = p.get("company") or p.get("name") or p.get("email") or "questa azienda"
    return nome, "\n\n".join(pezzi)


MARCA = "── Preparazione di Clara ──"


def nell_evento(r, testo):
    """LA PREP DENTRO L'EVENTO (Dre, 24/9: vive in Google Calendar, la legge dal
    telefono prima di entrare in call). L'id dell'evento sta nel link
    (eid = base64 di «id calendario»); si scrive nella descrizione, sopra
    quello che c'era, con una marca per non duplicarla al giro dopo."""
    import base64
    import re as _re
    import urllib.parse as _up
    link = r.get("link") or ""
    m = _re.search(r"[?&]eid=([A-Za-z0-9_\-=]+)", link)
    if not m or not r.get("owner"):
        return
    try:
        raw = m.group(1) + "=" * (-len(m.group(1)) % 4)
        eid = base64.urlsafe_b64decode(raw).decode("utf-8", "replace").split(" ")[0]
        chi = (sb("GET", f"/rest/v1/google_token?select=email&user_id=eq.{r['owner']}&limit=1") or [{}])[0].get("email")
        if not chi:
            return
        from google_api import g
        base = f"https://www.googleapis.com/calendar/v3/calendars/primary/events/{_up.quote(eid)}"
        ev = g("GET", base, email=chi) or {}
        vecchia = ev.get("description") or ""
        if MARCA in vecchia:
            vecchia = vecchia.split(MARCA)[-1].split("── fine ──")[-1].strip()
        nuova = f"{MARCA}\n{testo.strip()[:3500]}\n── fine ──\n\n{vecchia}".strip()
        g("PATCH", base, {"description": nuova[:8000]}, email=chi)
        print("    scritta anche nell'evento di Google")
    except Exception as e:                                        # noqa: BLE001
        print(f"    (non scritta nell'evento: {str(e)[:100]})")


def main():
    prova = "--prova" in sys.argv
    ore = 30
    if "--ore" in sys.argv:
        ore = int(sys.argv[sys.argv.index("--ore") + 1])

    adesso = datetime.datetime.now(datetime.timezone.utc)
    # in una URL il «+» del fuso orario diventa uno spazio: si scrive alla Z
    zulu = lambda d: d.strftime("%Y-%m-%dT%H:%M:%SZ")
    fino = zulu(adesso + datetime.timedelta(hours=ore))
    righe = sb("GET", "/rest/v1/agenda?select=id,at,titolo,tipo,prospect_id,preparazione,preparata_il"
                      f"&at=gte.{zulu(adesso)}&at=lte.{fino}&order=at&limit=50") or []
    call = [r for r in righe if r.get("prospect_id") and (r.get("tipo") or "") in CALL]
    print(f"{len(call)} call attaccate a un'azienda nelle prossime {ore} ore")

    fatte = 0
    for r in call:
        fresca = quando(r.get("preparata_il"))
        if fresca and (adesso - fresca).total_seconds() < FRESCA_ORE * 3600:
            continue
        nome, dati = dati_di(r["prospect_id"])
        if not dati:
            continue
        q = quando(r["at"])
        etichetta = q.strftime("%d/%m alle %H:%M") if q else ""
        print(f"  {nome}: {etichetta}, {r.get('tipo')}")
        if prova:
            fatte += 1
            continue
        testo = cervello.preparo(dati, azienda=nome, quando=etichetta, tipo=r.get("tipo") or "call")
        if not testo:
            print("    non e' uscito niente di sensato, la lascio com'era")
            continue
        sb("PATCH", f"/rest/v1/agenda?id=eq.{r['id']}",
           {"preparazione": testo, "preparata_il": zulu(adesso)})
        nell_evento(r, testo)
        fatte += 1

    print(f"{'(prova) ' if prova else ''}preparate {fatte}")


if __name__ == "__main__":
    main()
