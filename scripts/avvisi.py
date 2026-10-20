#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""GLI AVVISI — la notifica arriva a chi deve fare la cosa (24/9/2026, 20/10/2026).

1. LE TASK (24/9). Una task che Carlo manda ad Alex la deve sapere Alex, subito, con la
   scadenza: le task nuove con un destinatario diverso da chi le ha scritte, non ancora
   avvisate, vanno sul telefono del destinatario e si segnano (task.avvisata_il).

2. I GUASTI (20/10, «io più il sistema»). Dre: «voglio che arrivi l'avviso, ma settiamo bene le
   cose, non che si rompe ogni due secondi». I guasti sono quelli del semaforo della scheda
   «Clara» (clara_foglio.semaforo: solo quello che costa lead o soldi). Sul telefono di Dre:
   - un guasto nuovo: una notifica, con cosa sta facendo il sistema;
   - lo stesso guasto ancora vero: al massimo una ogni 2 ore;
   - quando torna verde: «Risolto: ...», una volta.
   Piu' guasti nello stesso giro fanno UNA notifica. Lo stato (quando e' suonato cosa) sta in
   snella_numeri, chiave «avvisi». Se un avviso suona spesso si ripara la causa, non si zittisce.
   Lo chiama anche la sentinella (workflow suo): se il direttore muore, questo giro non gira, e
   il «sistema fermo» deve arrivare lo stesso.

USO
  python3 scripts/avvisi.py           avvisa (task e guasti)
  python3 scripts/avvisi.py --prova   mostra e non manda, non scrive lo stato
"""
import datetime
import os
import sys
import zoneinfo

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from stanza import sb, env, quando                          # noqa: E402

ROMA = zoneinfo.ZoneInfo("Europe/Rome")

DASHBOARD = env("DASHBOARD_URL") or "./"
OGNI = datetime.timedelta(hours=2)
FOGLIO = "https://docs.google.com/spreadsheets/d/"


def task(prova):
    da = (datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=2)).strftime("%Y-%m-%dT%H:%M:%SZ")
    righe = sb("GET", f"/rest/v1/task?select=id,titolo,scadenza,owner,da,prospect_id&avvisata_il=is.null&fatta=eq.false&at=gte.{da}&order=at") or []
    nomi = {r["id"]: r["nome"] for r in (sb("GET", "/rest/v1/profili?select=id,nome") or [])}
    mandate = 0
    for t in righe:
        if not t.get("owner") or t.get("owner") == t.get("da"):
            continue
        chi = (nomi.get(t.get("da")) or "qualcuno").split(" ")[0]
        entro = f", entro il {t['scadenza'][8:10]}/{t['scadenza'][5:7]}" if t.get("scadenza") else ""
        testo = f"Task da {chi}: {t['titolo'][:80]}{entro}"
        url = f"{DASHBOARD}?scheda={t['prospect_id']}" if t.get("prospect_id") else DASHBOARD
        print(f"  → {nomi.get(t['owner'], t['owner'])[:20]}: {testo}")
        if prova:
            continue
        try:
            from avvisa import avvisa
            avvisa(testo, titolo="Clara", url=url, a=[t["owner"]])
        except Exception as e:                                   # noqa: BLE001
            print(f"    (notifica non partita: {str(e)[:80]})")
        sb("PATCH", f"/rest/v1/task?id=eq.{t['id']}", {"avvisata_il": datetime.datetime.now(datetime.timezone.utc).isoformat()})
        mandate += 1
    print(f"avvisi: {mandate} notifiche, {len(righe)} task guardate")


# ── i guasti ──────────────────────────────────────────────────────────

def di_notte(ora):
    """Dalle 22 alle 7:30 il telefono non suona: il guasto resta nella scheda Clara e, se e' ancora
    vero, suona alle 7:30 (il 14 e il 15/10 il direttore si e' fermato 22 minuti alle 5 del mattino)."""
    r = ora.astimezone(ROMA)
    return r.hour >= 22 or (r.hour, r.minute) < (7, 30)


def decidi(guasti, stato, ora):
    """Pura: cosa suonare adesso. guasti: quelli del semaforo; stato: {chiave: {cosa, da, primo,
    ultimo}} (ultimo: quando e' suonato l'ultima volta, None se mai). Torna ([(titolo, testo)], stato nuovo)."""
    notte = di_notte(ora)
    nuovo = {}
    da_suonare = []
    for g in guasti:
        prima = stato.get(g["chiave"])
        if prima and prima.get("risolto"):
            prima = None                                         # risolto di notte e tornato: e' un guasto nuovo
        voce = {"cosa": g["cosa"], "da": g["da"].isoformat(), "primo": (prima or {}).get("primo") or ora.isoformat(),
                "ultimo": (prima or {}).get("ultimo")}
        if not notte and (not voce["ultimo"] or ora - quando(voce["ultimo"]) >= OGNI):
            da_suonare.append((g, bool(voce["ultimo"])))
            voce["ultimo"] = ora.isoformat()
        nuovo[g["chiave"]] = voce
    # risolto: si dice solo di quello che era suonato; di notte si aspetta il mattino
    risolti = []
    for k, v in stato.items():
        if k in nuovo or not v.get("ultimo"):
            continue
        if notte:
            nuovo[k] = dict(v, risolto=True)
        else:
            risolti.append(v)
    note = []
    # (titolo, testo, lead): il titolo corto, la frase intera nel testo; il tocco apre la scheda del
    # lead se il guasto e' di un lead, se no la scheda Clara del foglio
    if len(da_suonare) == 1:
        g, ancora = da_suonare[0]
        note.append(("Ancora fermo" if ancora else "Si è fermato qualcosa", f"{g['cosa']}. {g['sta_facendo']}", g.get("pid")))
    elif da_suonare:
        note.append((f"{len(da_suonare)} cose ferme nel sistema",
                     " · ".join(g["cosa"] for g, _ in da_suonare) + ". Il dettaglio è nella scheda Clara del foglio.", None))
    if len(risolti) == 1:
        note.append(("Risolto", f"{risolti[0]['cosa']}: il sistema è ripartito.", None))
    elif risolti:
        note.append((f"Risolto: {len(risolti)} cose ripartite", " · ".join(v["cosa"] for v in risolti), None))
    return note, nuovo


def _link_clara():
    """Il tocco porta alla scheda Clara del foglio (dove c'e' la riga rossa)."""
    try:
        r = sb("GET", "/rest/v1/snella_numeri?select=dati&chiave=eq.foglio") or []
        sid = ((r[0].get("dati") or {}) if r else {}).get("foglio_id")
        return f"{FOGLIO}{sid}/edit" if sid else None
    except Exception:                                            # noqa: BLE001
        return None


def suona(titolo, testo, pid=None):
    """Una notifica a Dre. Non alza mai: un avviso che non parte si scrive nel log."""
    try:
        import segnale_provvisorio as SP
        from avvisa import avvisa
        chi = SP._dre_id()
        url = SP.link_snella(pid) if pid else (_link_clara() or SP.link_snella())
        n = avvisa(" ".join(testo.split())[:178], titolo=" ".join(titolo.split())[:60], url=url, a=[chi], tag="guasto") if chi else 0
        print(f"  notifica: {titolo} ({n} dispositivi)")
        return n
    except Exception as e:                                       # noqa: BLE001
        print(f"  (notifica non partita: {str(e)[:120]})")
        return 0


def guasti(prova=False, ora=None):
    import clara_foglio
    ora = ora or datetime.datetime.now(datetime.timezone.utc)
    aperti = clara_foglio.semaforo(ora)
    r = sb("GET", "/rest/v1/snella_numeri?select=dati&chiave=eq.avvisi") or []
    stato = ((r[0].get("dati") if r else None) or {}).get("guasti") or {}
    note, nuovo = decidi(aperti, stato, ora)
    print(f"guasti: {len(aperti)} aperti" + "".join(f"\n  ! {g['cosa']}" for g in aperti))
    for titolo, testo, pid in note:
        if prova:
            print(f"  [prova] suonerebbe: {titolo} | {testo}")
        else:
            suona(titolo, testo, pid)
    if not prova:
        sb("POST", "/rest/v1/snella_numeri?on_conflict=chiave",
           [{"chiave": "avvisi", "dati": {"guasti": nuovo, "giro": ora.isoformat()}, "aggiornato_il": ora.isoformat()}],
           {"Prefer": "resolution=merge-duplicates,return=minimal"})
    return note


def main():
    prova = "--prova" in sys.argv
    if "--solo-guasti" not in sys.argv:
        task(prova)
    guasti(prova)


if __name__ == "__main__":
    main()
