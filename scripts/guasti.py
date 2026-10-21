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
A ogni giro fa anche IL CONTROLLO DI COMPLETEZZA (21/10): le risposte che la Master Inbox di
Smartlead mostra nelle ultime 2 ore devono stare nel database (prospects.last_reply_at): una che
manca da piu' di 20 minuti e' un rosso con l'azienda (risposte_perse; il risultato resta nella
chiave «guasti», «perse», e lo legge anche la scheda Clara).

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

# ── il controllo di completezza (21/10): Smartlead contro il database ──
FRESCHE_ORE = 2                                        # le risposte della Master Inbox che si confrontano
RITARDO_NORMALE = datetime.timedelta(minutes=20)       # il sync parte ogni 5 minuti e dura fino a 6: entro 20 non e' un guasto


def risposte_perse(ora, fresche, schede):
    """Pura. Le risposte che Smartlead mostra nella Master Inbox (sync_v2.risposte_fresche:
    {email: {"t", "campagna", ...}}) e che il sistema NON ha: nessuna scheda per quella mail, o
    prospects.last_reply_at piu' vecchio della risposta. Le risposte piu' giovani di RITARDO_NORMALE
    aspettano il sync. Torna guasti come quelli del semaforo, mai con la mail del lead dentro."""
    out = []
    for em, f in (fresche or {}).items():
        t = f.get("t")
        if not t:
            continue
        t = quando(t + "+00:00" if len(t) == 19 else t)
        if ora - t < RITARDO_NORMALE:
            continue
        p = (schede or {}).get(em)
        if p and (p.get("last_reply_at") or "")[:19] >= f["t"][:19]:
            continue
        if p:
            chi = " ".join((p.get("company") or p.get("name") or "un lead").split())
            out.append({"chiave": f"persa:{p['id']}", "da": t, "pid": p["id"],
                        "cosa": f"Una risposta su Smartlead non è entrata nel sistema: {chi}, alle {t.astimezone(ROMA):%H:%M}",
                        "sta_facendo": "Il sync la riprende da solo a ogni giro; intanto la trovi su Smartlead."})
        else:
            dove = f.get("campagna") or "una campagna"
            out.append({"chiave": f"persa:sl:{f.get('lead_id') or f.get('lead_map') or '?'}", "da": t,
                        "cosa": f"Una risposta su Smartlead non è entrata nel sistema: un lead di «{dove}», alle {t.astimezone(ROMA):%H:%M}",
                        "sta_facendo": "Il sync la riprende da solo a ogni giro; intanto la trovi su Smartlead."})
    return sorted(out, key=lambda g: g["da"])


def leggi_perse(ora):
    """Il controllo di completezza sui dati veri: la Master Inbox delle ultime 2 ore contro le
    schede. Se Smartlead non risponde torna [] (lo dice il rosso della Master Inbox)."""
    import urllib.parse
    import sync_v2
    fresche = sync_v2.risposte_fresche((ora - datetime.timedelta(hours=FRESCHE_ORE)).strftime("%Y-%m-%dT%H:%M:%S"), segna=False)
    if not fresche:
        return []
    schede = {}
    mails = sorted(fresche)
    for i in range(0, len(mails), 50):
        for p in sb("GET", "/rest/v1/prospects?select=id,email,company,name,last_reply_at"
                           f"&email=in.({urllib.parse.quote(','.join(mails[i:i + 50]))})") or []:
            schede[(p.get("email") or "").lower()] = p
    return risposte_perse(ora, fresche, schede)


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
    dati_semaforo = clara_foglio.leggi_semaforo(ora)
    # il controllo di completezza (21/10): Smartlead contro il database, a ogni giro dei guasti;
    # il risultato resta nella chiave «guasti» (perse) cosi' lo vede anche la scheda Clara
    try:
        perse = leggi_perse(ora)
    except Exception as e:                                       # noqa: BLE001
        print(f"  (controllo di completezza non fatto: {str(e)[:120]})")
        perse = []
    perse_scritte = {"il": ora.isoformat(), "guasti": [dict(g, da=g["da"].isoformat()) for g in perse]}
    dati_semaforo["perse"] = perse_scritte
    aperti = clara_foglio.semaforo(ora, dati_semaforo)
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
           [{"chiave": "guasti", "dati": {"aperti": nuovo, "risolti": risolti, "giro": ora.isoformat(), "perse": perse_scritte},
             "aggiornato_il": ora.isoformat()}],
           {"Prefer": "resolution=merge-duplicates,return=minimal"})
    return note


def main():
    giro("--prova" in sys.argv)


if __name__ == "__main__":
    main()
