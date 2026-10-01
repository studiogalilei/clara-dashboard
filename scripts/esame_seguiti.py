#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""L'ESAME DEI SEGUITI (Dre, 1/10/2026).

Parole sue: «vorrei trainare il sistema anche per i follow-up, in modo che quando
diventano massivi si facciano veloci e in ordine. Un modello come l'altro, con
tutte quelle domande e i commenti: così sa fare i follow-up, sa riprendere, sa
fare tutto esattamente come lo farei io».

Il formato e' quello del metro (la piattaforma: metro_casi, schema_v73):
  --prepara N   sceglie N situazioni vere in cui il sistema farebbe un seguito
                (il calendario dei follow-up) o in cui c'e' un silenzio che il
                sistema ignora. Per ognuna salva i blocchi che Dre vede, le
                mosse fra cui scegliere, e NASCOSTA la mossa del sistema.
  --misura      confronta le mosse di Dre con quelle del sistema: dove va
                d'accordo, dove Dre aspetterebbe, dove Dre chiuderebbe.

USO
  python3 scripts/esame_seguiti.py --prepara 60
  python3 scripts/esame_seguiti.py --misura
"""
import datetime
import os
import sys
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from stanza import sb, sb_tutte                            # noqa: E402

PROVA = "--prova" in sys.argv
TEMA = "seguiti"
DOMANDA = "Che mossa fai qui?"
SCELTE = [["seguito", "Follow-up ora"], ["mini", "Mini, due righe"], ["ripresa", "Ripresa, scusa nuova"],
          ["aspetto", "Aspetto ancora"], ["chiudo", "Chiudo qui"], ["altro", "Altro, lo scrivo"]]


def _giorni(da):
    try:
        return (datetime.date.today() - datetime.date.fromisoformat(str(da)[:10])).days
    except Exception:                                      # noqa: BLE001
        return None


def _blocchi(p, letti, silenzio):
    out = [{"eti": "Dove siamo", "testo": ", ".join(x for x in (
        f"tappa {p.get('tappa') or '?'}",
        "analisi mandata" + (f" {_giorni(p.get('analysis_sent_at'))} giorni fa" if p.get("analysis_sent_at") else "") if p.get("analysis_sent") else "analisi non ancora mandata",
        f"silenzio da {silenzio} giorni" if silenzio is not None else None) if x)}]
    if letti.get("ultima_loro"):
        out.append({"eti": f"L'ultima cosa che ha scritto ({letti.get('ultima_loro_il', '?')})", "testo": letti["ultima_loro"][:420]})
    if letti.get("ultima_nostra"):
        out.append({"eti": f"L'ultima cosa che abbiamo scritto noi ({letti.get('ultima_nostra_il', '?')})", "testo": letti["ultima_nostra"][:320]})
    return out


def prepara(n):
    import lettura
    gia = {r["riferimento"] for r in sb_tutte(f"/rest/v1/metro_casi?select=riferimento&tema=eq.{TEMA}", chiave="id")}
    casi = []
    # 1. chi e' nel calendario dei seguiti: il sistema UNA mossa ce l'ha gia'
    for r in sb("GET", "/rest/v1/seguiti_calendario?select=prospect_id,gruppo,il,perche&order=il.asc&limit=500") or []:
        casi.append((r["prospect_id"], {"mossa": "seguito" if r["gruppo"] in ("FOLLOW UP 1", "RICONTATTO OOO", "RINVIO SCADUTO") else "mini",
                                        "gruppo": r["gruppo"], "il": r["il"], "perche": r["perche"]}))
    # 2. i silenzi che il sistema oggi IGNORA (analisi mandata, nessuna coda, 20+ giorni):
    #    qui la mossa del sistema e' «aspetto», e l'esame dira' se Dre e' d'accordo
    nel_giro = {pid for pid, _ in casi}
    for p in sb("GET", "/rest/v1/prospects?select=id,analysis_sent_at&fuori=eq.false&awaiting_us=eq.false"
                       "&analysis_sent=eq.true&coda=is.null&no_followup=eq.false"
                       "&stage=in.(analisi_inviata,in_follow_up,risposto)"
                       "&or=(classificazione.is.null,classificazione.not.in.(negativo,fuori_target,soppresso,nervoso))"
                       "&order=analysis_sent_at.asc&limit=120") or []:
        if p["id"] not in nel_giro and (_giorni(p.get("analysis_sent_at")) or 0) >= 20:
            casi.append((p["id"], {"mossa": "aspetto", "perche": "nessuna regola lo copre: il sistema non farebbe niente"}))
    fatti = 0
    for pid, proposta in casi:
        if fatti >= n or pid in {None} or f"{pid}" in gia:
            continue
        p = (sb("GET", f"/rest/v1/prospects?select=*&id=eq.{pid}") or [None])[0]
        if not p:
            continue
        try:
            _, letti = lettura.leggi(p)
        except Exception:                                  # noqa: BLE001
            continue
        silenzio = _giorni(p.get("last_reply_at")) if p.get("last_reply_at") else _giorni(p.get("analysis_sent_at"))
        nome = p.get("company") or p.get("name") or p["email"]
        if PROVA:
            print(f"  {nome[:36]:36} sistema: {proposta.get('gruppo') or proposta['mossa']}")
            fatti += 1
            continue
        sb("POST", "/rest/v1/metro_casi?on_conflict=tema,riferimento",
           {"tema": TEMA, "prospect_id": pid, "riferimento": f"{pid}", "domanda": DOMANDA,
            "mostra": [{"eti": "Azienda", "testo": str(nome)[:120]}] + _blocchi(p, letti, silenzio),
            "scelte": SCELTE, "proposta": proposta},
           {"Prefer": "resolution=ignore-duplicates,return=minimal"})
        fatti += 1
    print(f"esame dei seguiti: {fatti} casi pronti" + (" (prova, niente scritto)" if PROVA else ""))


def misura():
    righe = [r for r in sb_tutte(f"/rest/v1/metro_casi?select=etichetta,nota,proposta,mostra&tema=eq.{TEMA}", chiave="id") if r.get("etichetta")]
    if not righe:
        print("ancora nessuna mossa di Dre: l'esame e' nella pagina «Metro»")
        return
    print(f"L'ESAME DEI SEGUITI: {len(righe)} mosse di Dre {dict(Counter(r['etichetta'] for r in righe))}\n")
    d_accordo = 0
    for r in righe:
        sua, s = r["etichetta"], (r.get("proposta") or {}).get("mossa")
        d_accordo += sua == s
    print(f"  d'accordo col sistema: {d_accordo}/{len(righe)}")
    for r in righe:
        sua, s = r["etichetta"], (r.get("proposta") or {}).get("mossa")
        if sua != s:
            nome = next((b["testo"] for b in r["mostra"] if b.get("eti") == "Azienda"), "?")
            print(f"  Dre={sua:8} sistema={s or '-':8} {nome[:36]:36} {('«' + r['nota'][:80] + '»') if r.get('nota') else ''}")


if __name__ == "__main__":
    if "--prepara" in sys.argv:
        prepara(int(sys.argv[sys.argv.index("--prepara") + 1]))
    elif "--misura" in sys.argv:
        misura()
    else:
        print(__doc__)
