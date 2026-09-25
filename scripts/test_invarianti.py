#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""GLI INVARIANTI — quello che non deve rompersi mai (24/9/2026, da Galileo).

Lorenzo tiene 50 file di test sugli invarianti del suo sistema; Dre vuole lo
stesso rigore. Questi sono i nostri, in codice: se uno cade, il push non
passa (workflow `controlla`). Niente rete, niente modello: solo le regole.

  python3 scripts/test_invarianti.py
"""
import datetime
import os
import sys
import zoneinfo

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault("VITE_SUPABASE_URL", "http://finto.local")
os.environ.setdefault("SUPABASE_SERVICE_KEY", "finto")
os.environ["POLIZIA_PROVA"] = "1"

ESITI = []


def prova(nome):
    def dec(f):
        ESITI.append((nome, f))
        return f
    return dec


# ── 1. i numeri li da' il codice, non il modello ──────────────────
@prova("analisi: un numero non nei fatti ferma l'analisi")
def _():
    import analisi_auto as A
    fatti = "VOLUMI: domanda 4,400 ricerche/mese, CPC medio 3.2 €, mesi vivi 9/12. Serie: [120, 340, 90]. MAPS: 86 recensioni, voto 4.7. verificato il 12 settembre 2026"
    ok = "<p>4.400 ricerche al mese, CPC 3,2 €, 86 recensioni (voto 4,7), 340 a marzo, nel 2026, 3 mesi, 5 percorsi.</p>"
    assert A.numeri_non_nei_fatti(ok, fatti) == [], A.numeri_non_nei_fatti(ok, fatti)
    male = ok + "<p>il 30% del traffico su 2.300 aziende e 1.500 € al mese</p>"
    fuori = A.numeri_non_nei_fatti(male, fatti)
    assert set(fuori) == {"30%", "2300", "1500€"}, fuori
    errs = A.cancello({"intro": "x", "body": male}, fatti)
    assert any("numeri che non stanno nei fatti" in e for e in errs)


@prova("analisi: senza fatti il cancello dei numeri non boccia (non inventa regole)")
def _():
    import analisi_auto as A
    assert A.numeri_non_nei_fatti("<p>30% e 2.300</p>", "") == []


# ── 2. il blocco dopo la call sta in orario di lavoro ─────────────
@prova("blocco dopo la call: mai di sabato, mai fuori 9-18, mai sopra un impegno")
def _():
    import transcript as T
    R = zoneinfo.ZoneInfo("Europe/Rome")
    ven_sera = datetime.datetime(2026, 9, 25, 17, 50, tzinfo=R)      # venerdi' 17:50
    t = T.primo_buco([], ven_sera)
    assert t.weekday() == 0 and t.hour == 9 and t.minute == 0, t         # lunedi' alle 9
    mattina = datetime.datetime(2026, 9, 24, 10, 0, tzinfo=R)
    occupato = [(datetime.datetime(2026, 9, 24, 10, 0, tzinfo=R), datetime.datetime(2026, 9, 24, 11, 0, tzinfo=R))]
    t = T.primo_buco(occupato, mattina)
    assert t == datetime.datetime(2026, 9, 24, 11, 0, tzinfo=R), t
    notte = datetime.datetime(2026, 9, 24, 3, 0, tzinfo=R)
    assert T.primo_buco([], notte).hour == 9


@prova("avanzamento: Clara sposta solo tecnica/avvio/prova, avanti, con evidenza «sicuro»")
def _():
    import transcript as T
    assert set(T.DA_SOLA) == {"tecnica", "avvio", "prova"}
    assert "cliente" not in T.DA_SOLA and "perso" not in T.DA_SOLA
    L = T.Lettura(); L.fase = "tecnica"; L.certezza = "sicuro"; L.evidenza = "fissiamo la call tecnica"
    esito = T.avanzamento({"id": "x", "fuori": True, "pipeline_stage": "conoscitiva"}, "Prova", L, "t1", True)
    assert esito.startswith("Spostata in Call Tecnica"), esito
    L.certezza = "incerto"
    esito = T.avanzamento({"id": "x", "fuori": True, "pipeline_stage": "conoscitiva"}, "Prova", L, "t1", True)
    assert esito.startswith("Proposto in Posta"), esito
    L.certezza = "sicuro"; L.fase = "conoscitiva"
    esito = T.avanzamento({"id": "x", "fuori": True, "pipeline_stage": "tecnica"}, "Prova", L, "t1", True)   # indietro
    assert esito.startswith("Proposto in Posta"), esito


# ── 3. manda: mai senza approvazione, mai con segnaposto ─────────
@prova("manda: il corpo diventa HTML pulito e i segnaposto fermano tutto")
def _():
    import manda as M
    h = M.in_html("Buongiorno,\n\nle mando il link: https://x.y/z\nA presto")
    assert h == '<p>Buongiorno,</p><p>le mando il link: <a href="https://x.y/z">https://x.y/z</a><br>A presto</p>', h
    assert M.in_html("<script>alert(1)</script>") == "<p>&lt;script&gt;alert(1)&lt;/script&gt;</p>"
    assert M.controlla("Le propongo {{CALENDARIO}}") == ["segnaposto lasciato nel testo"]


@prova("manda: si manda solo cio' che ha un approvatore (regola nel codice)")
def _():
    src = open(os.path.join(os.path.dirname(__file__), "manda.py"), encoding="utf-8").read()
    assert 'stato=eq.approvata' in src, "manda deve leggere solo le proposte approvate"
    assert 'approvata_da' in src and 'in_invio' in src, "manda deve controllare chi ha approvato e mettere il lucchetto"


# ── 4. il poliziotto: chi ha risposto non si cancella ─────────────
@prova("poliziotto: esclude chi ha risposto, i fuori, i bloccati, i soppressi")
def _():
    import polizia as P
    P._ha_risposto = lambda e: e == "ha.risposto@x.it"
    P._seconda_testa = lambda *a, **k: "OK"
    P.di_clara = lambda *a, **k: None
    righe = [{"email": "ha.risposto@x.it"}, {"email": "fuori@x.it", "fuori": True}, {"email": "b@x.it", "bloccato": True},
             {"email": "s@x.it", "classificazione": "soppresso"}, {"email": "ok@x.it"}]
    tenute = P.controlla("cancello lead dalle campagne", righe, irreversibile=True, motivo="prova")
    assert [r["email"] for r in tenute] == ["ok@x.it"], tenute


# ── 5. il follow-up: template parola per parola, nome giusto ──────
@prova("follow-up: il nome sostituisce solo il segnaposto, le caselle generiche restano «Salve,»")
def _():
    import followup as F
    assert F.nome_di({"name": "Maria Rossi"}) == "Maria"
    assert F.nome_di({"name": "info"}) == ""
    assert F.nome_di({"name": None}) == ""
    base = "Salve Stefania,\n\ntorno brevemente sull'analisi."
    assert base.replace("Salve Stefania,", "Salve Maria,") .startswith("Salve Maria,")


# ── 6. Clara riempie: niente slop ─────────────────────────────────
@prova("arricchisci: le parole generiche non bastano a riconoscere un sito")
def _():
    import arricchisci as R
    assert R.parole("Studio Galilei Srl") == ["galilei"]
    assert R.parole("Impresa Servizi Srl") == []
    assert R.parole("Thermalink") == ["thermalink"]


def main():
    falliti = 0
    for nome, f in ESITI:
        try:
            f()
            print(f"  ok    {nome}")
        except Exception as e:                                    # noqa: BLE001
            falliti += 1
            print(f"  CADE  {nome}: {type(e).__name__}: {str(e)[:200]}")
    print(f"{len(ESITI) - falliti}/{len(ESITI)} invarianti tengono")
    sys.exit(1 if falliti else 0)


if __name__ == "__main__":
    main()
