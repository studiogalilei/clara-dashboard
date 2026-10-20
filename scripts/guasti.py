#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""GLI AVVISI DI GUASTO (20/10/2026, «io più il sistema»).

Dre: «voglio che arrivi l'avviso, ma settiamo bene le cose, non che si rompe ogni due secondi».
Un solo sistema di avvisi: i guasti sono quelli del semaforo della scheda «Clara» del foglio
(clara_foglio.semaforo: solo quello che costa lead o soldi, compresi i guasti che il segnale
provvisorio vede da dentro: Gmail ferma, memoria, calendario, conversazioni). Sul telefono di Dre:
- un guasto nuovo: una notifica, con cosa sta facendo il sistema;
- lo stesso guasto ancora vero: al massimo una ogni 2 ore;
- quando torna verde: «Risolto», una volta (solo per quello che era suonato);
- dalle 22 alle 7:30 non suona: il guasto resta nella scheda Clara e, se e' ancora vero, suona
  alle 7:30.
Piu' guasti nello stesso giro fanno UNA notifica. Lo stato (quando e' suonato cosa) sta in
snella_numeri, chiave «guasti»: «aperti» adesso e «risolti» nelle ultime 48 ore (li legge la mail
della sera, scripts/giornata.py). Se un avviso suona spesso si ripara la causa, non si zittisce.
Gira ogni 10 minuti (operazione «guasti»); lo chiama anche la sentinella, dal suo workflow,
quando il direttore e' fermo (allora questa operazione non gira).

USO
  python3 scripts/guasti.py           suona quello che c'e' da suonare
  python3 scripts/guasti.py --prova   mostra e non manda, non scrive lo stato
"""
import datetime
import os
import sys
import zoneinfo

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from stanza import sb, quando                               # noqa: E402

ROMA = zoneinfo.ZoneInfo("Europe/Rome")
OGNI = datetime.timedelta(hours=2)
FOGLIO = "https://docs.google.com/spreadsheets/d/"


def di_notte(ora):
    """Dalle 22 alle 7:30 il telefono non suona (il 14 e il 15/10 il direttore si e' fermato
    22 minuti alle 5 del mattino: non e' una cosa per cui svegliare Dre)."""
    r = ora.astimezone(ROMA)
    return r.hour >= 22 or (r.hour, r.minute) < (7, 30)


def decidi(guasti, stato, ora):
    """Pura: cosa suonare adesso. guasti: quelli del semaforo; stato: {chiave: {cosa, da, primo,
    ultimo}} (ultimo: quando e' suonato l'ultima volta, None se mai). Torna
    ([(titolo, testo, pid o None)], stato nuovo)."""
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
    # il titolo corto, la frase intera nel testo; il tocco apre la scheda del lead se il guasto e'
    # di un lead, se no la scheda Clara del foglio
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
    """Il tocco porta al foglio (la scheda Clara, dove c'e' la riga rossa)."""
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


TIENI_RISOLTI = datetime.timedelta(hours=48)


def storico(stato, nuovo, risolti, ora):
    """Pura. I guasti risolti, per la mail della sera (giornata.py): un guasto che era nello stato e
    non c'e' piu' (o e' appena passato a «risolto» di notte) va nella lista, con cosa, da quando e
    quando si e' chiuso. Si tengono quelli delle ultime 48 ore. (20/10 sera)"""
    out = [x for x in (risolti or []) if isinstance(x, dict) and x.get("risolto_il") and ora - quando(x["risolto_il"]) <= TIENI_RISOLTI]
    for k, v in (stato or {}).items():
        sparito = k not in nuovo
        appena_risolto = (not sparito) and nuovo[k].get("risolto") and not v.get("risolto")
        if (sparito or appena_risolto) and not v.get("risolto"):
            out.append({"chiave": k, "cosa": v.get("cosa"), "da": v.get("da"), "primo": v.get("primo"), "risolto_il": ora.isoformat()})
    return out


def giro(prova=False, ora=None):
    import clara_foglio
    ora = ora or datetime.datetime.now(datetime.timezone.utc)
    aperti = clara_foglio.semaforo(ora)
    r = sb("GET", "/rest/v1/snella_numeri?select=dati&chiave=eq.guasti") or []
    dati = ((r[0].get("dati") if r else None) or {})
    stato = dati.get("aperti") or {}
    note, nuovo = decidi(aperti, stato, ora)
    risolti = storico(stato, nuovo, dati.get("risolti"), ora)
    print(f"guasti: {len(aperti)} aperti" + "".join(f"\n  ! {g['cosa']}" for g in aperti))
    for titolo, testo, pid in note:
        if prova:
            print(f"  [prova] suonerebbe: {titolo} | {testo}")
        else:
            suona(titolo, testo, pid)
    if not prova:
        sb("POST", "/rest/v1/snella_numeri?on_conflict=chiave",
           [{"chiave": "guasti", "dati": {"aperti": nuovo, "risolti": risolti, "giro": ora.isoformat()}, "aggiornato_il": ora.isoformat()}],
           {"Prefer": "resolution=merge-duplicates,return=minimal"})
    return note


def main():
    giro("--prova" in sys.argv)


if __name__ == "__main__":
    main()
