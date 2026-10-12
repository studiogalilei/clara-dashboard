#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""IL SENSO IN OMBRA: il confronto del mattino (12/10/2026).

Per sette giorni il senso nuovo (lettura.senso, senso.giudica) gira accanto al vecchio
(regex + lettore con «basta che uno dei due dica no») e non decide niente. Ogni mattina:
  - si confrontano vecchio e nuovo sulle letture di ieri;
  - ogni disaccordo va nel Metro (metro_casi, tema «senso»): Dre lo etichetta con un tocco,
    e l'etichetta dice chi dei due aveva ragione;
  - una riga nella chat: quante risposte, quanti disaccordi, e i no che Clara ha chiuso da
    sola (l'unico effetto permanente fatto senza Dre), con la frase.
L'interruttore senso_v2 lo accende Dre, dopo la misura (scripts/misura_senso.py).

  python3 scripts/senso_ombra.py            ieri
  python3 scripts/senso_ombra.py --prova    mostra, non scrive
"""
import datetime
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from stanza import sb, sb_tutte, di_clara, _a_secco             # noqa: E402

PROVA = _a_secco()


def vecchio_di(testo_suo, risposte):
    """Come il vecchio avrebbe letto lo stesso testo suo, con la stessa lettura del modello:
    le liste (DETTO_NO, AUTORISPOSTA, NON_TOCCARE, CHIEDE_ANALISI) e «basta che uno dei due»."""
    import lettura as L
    import analisi_auto as A
    lettore = L.cervello_decisioni(risposte)
    t = testo_suo or ""
    if L.frena(A.NON_TOCCARE.search(t), lettore, ("non_scrivere",)):
        return "non_scrivere"
    if L.frena(L.DETTO_NO.search(t), lettore, ("no",)):
        return "no"
    if L.frena(L.AUTORISPOSTA.search(t[:1200]), lettore, ("fuori_ufficio",)):
        return "fuori_ufficio"
    if lettore and lettore.get("etichetta") == "rinvio":
        return "rinvio"
    if L.si_acceso(A.CHIEDE_ANALISI.search(t), lettore):
        return "si"
    return "altro"


def nuovo_di(dec):
    """La decisione nuova nelle stesse sei parole del Metro."""
    dec = dec or {}
    if dec.get("grave"):
        return "non_scrivere"
    e = dec.get("etichetta")
    return {"auto": "fuori_ufficio", "si": "si", "no": "no", "rinvio": "rinvio"}.get(e, "altro")


def main():
    import lettura
    ieri = (datetime.date.today() - datetime.timedelta(days=1)).isoformat()
    oggi = datetime.date.today().isoformat()
    try:
        righe = sb_tutte(f"/rest/v1/letture?select=id,prospect_id,interaction_id,testo_suo,risposte,decisione,stato,fonte"
                         f"&letta_il=gte.{ieri}&letta_il=lt.{oggi}")
    except Exception as e:                                     # noqa: BLE001
        print(f"senso in ombra: la tabella letture non si legge ({str(e)[:80]}): schema_v81 applicato?")
        return
    diversi = []
    for r in righe:
        v, n = vecchio_di(r.get("testo_suo"), r.get("risposte")), nuovo_di(r.get("decisione"))
        if v != n:
            diversi.append((r, v, n))
    chiusi = [x for x in (sb("GET", f"/rest/v1/interactions?select=prospect_id,body&kind=eq.nota&at=gte.{ieri}&at=lt.{oggi}"
                                    "&body=like.Riclassificata%20negativo%20da%20Clara*&limit=200") or [])]
    print(f"senso in ombra, {ieri}: {len(righe)} letture, vecchio e nuovo diversi su {len(diversi)}, "
          f"no chiusi da sola {len(chiusi)} ({'acceso' if lettura.senso_acceso() else 'spento'})")
    for r, v, n in diversi[:30]:
        print(f"  [{v:>13} → {n:<13}] {(r.get('decisione') or {}).get('fonte')}: «{' '.join((r.get('testo_suo') or '').split())[:90]}»")
    if PROVA:
        return
    for r, v, n in diversi:
        try:
            sb("POST", "/rest/v1/metro_casi?on_conflict=tema,riferimento",
               {"tema": "senso", "prospect_id": r.get("prospect_id"), "riferimento": f"lettura:{r['id']}",
                "domanda": "Cosa ha risposto?", "mostra": [{"eti": "Ha scritto", "testo": (r.get("testo_suo") or "")[:1500]}],
                "scelte": lettura.SCELTE_DRE, "proposta": {"vecchio": v, "nuovo": n, "lettura_id": r["id"]}},
               {"Prefer": "resolution=ignore-duplicates,return=minimal"})
        except Exception as e:                                 # noqa: BLE001
            print(f"  (caso non messo nel Metro: {str(e)[:60]})")
    if righe or chiusi:
        frasi = "; ".join(f"«{x['body'].split('«', 1)[-1].split('»', 1)[0][:60]}»" for x in chiusi[:3] if "«" in (x.get("body") or ""))
        di_clara("controllo", f"Il senso, ieri: {len(righe)} risposte lette; vecchio e nuovo diversi su {len(diversi)}"
                              + (", da etichettare nel Metro" if diversi else "")
                              + (f". No chiusi da sola: {len(chiusi)}" + (f" ({frasi})" if frasi else "") if chiusi else "") + ".",
                 letto=not diversi and not chiusi)


if __name__ == "__main__":
    main()
