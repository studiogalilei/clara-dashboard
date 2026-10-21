#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""GLI INVARIANTI — quello che non deve rompersi mai (24/9/2026, da Galileo).

Lorenzo tiene 50 file di test sugli invarianti del suo sistema; Dre vuole lo
stesso rigore. Questi sono i nostri, in codice: se uno cade, il push non
passa (workflow `controlla`). Niente rete, niente modello: solo le regole.

  python3 scripts/test_invarianti.py
"""
import datetime
import json
import os
import sys
import zoneinfo

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault("VITE_SUPABASE_URL", "http://finto.local")
os.environ.setdefault("SUPABASE_SERVICE_KEY", "finto")
os.environ["POLIZIA_PROVA"] = "1"
os.environ["SENZA_PUSH"] = "1"          # le prove non mandano mai una notifica vera (avvisa.py)

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
    # 6/10: una data e i modi di dire non sono numeri inventati; un numero vero accanto si', ancora
    data = ok + "<p>Analisi del 29 settembre 2026 (aggiornata il 29/9), aperti 365 giorni l'anno, 24 ore su 24.</p>"
    assert A.numeri_non_nei_fatti(data, fatti) == [], A.numeri_non_nei_fatti(data, fatti)
    assert A.numeri_non_nei_fatti(ok + "<p>29 clienti nuovi</p>", fatti) == ["29"]
    # 6/10: il nome di una norma o di un prodotto non e' un dato (SMART per «9001», Neuronica per «Microsoft 365»)
    norme = ok + "<p>Certificazioni ISO 9001, UNI EN ISO 14001:2015, ISO/IEC 27001, ISO-45001 e OHSAS 18001. Migrazioni a Microsoft 365, Office 365 e Windows 11.</p>"
    assert A.numeri_non_nei_fatti(norme, fatti) == [], A.numeri_non_nei_fatti(norme, fatti)
    assert A.numeri_non_nei_fatti(ok + "<p>9001 aziende certificate</p>", fatti) == ["9001"], "un numero vero resta un numero"
    assert A.numeri_non_nei_fatti(ok + "<p>ben 30 recensioni in casa</p>", fatti) == ["30"], "«ben 30» non e' una norma"


@prova("il sync non ribalta un no sullo stesso messaggio e legge solo la parte del lead (caso La Bussola e Panorama, 6/10)")
def _():
    import sync_v2 as S
    citata = ("Non ci interessa, gentilmente non ci contatti piu. Cordiali saluti\n\n"
              "Il giorno lun 5 ott 2026 alle 11:02 Lorenzo Fornasier <l@x.com> ha scritto:\n"
              "Abbiamo preparato una breve analisi che mi piacerebbe condividerle. Se le fa piacere riceverla, gliela mando subito")
    # un no gia' deciso resta no se il lead non ha scritto niente di nuovo
    assert S.classe_da_sync(citata, "", "negativo", False) == "negativo"
    assert S.classe_da_sync("si' mandatela pure, mi interessa", "Interested", "negativo", False) == "negativo"
    assert S.classe_da_sync("ok", "", "soppresso", False) == "soppresso"
    # e nemmeno un si': le regole del sync sono piu' grezze della rilettura che l'ha deciso
    assert S.classe_da_sync("Buongiorno, ricevuto", "", "positivo", False) == "positivo"
    assert S.classe_da_sync("Grazie non ci interessa.", "", "da_classificare", False) == "negativo", "chi non e' classificato si classifica"
    # una risposta nuova invece si rilegge
    assert S.classe_da_sync("si', mandatela pure, mi interessa", "", "negativo", True) == "positivo"
    # la nostra mail citata non conta: «mi piacerebbe» e' nostro
    assert S.classe_da_sync(citata, "", None, True) == "negativo"
    # i no di stanotte, scritti come li scrivono
    for no in ("Grazie non ci interessa.", "la ringrazio ma abbiamo già chi ci fornisce questo servizio",
               "grazie per il messaggio, in realtà abbiamo già chi si occupa di queste cose"):
        assert S.classifica(no) == "negativo", no
    assert S.classe_da_sync("in realtà abbiamo già chi si occupa di queste cose", "Information Request", None, True) == "negativo"
    # 6/10 pomeriggio: due consensi veri restavano «da classificare» e la prima risposta non partiva
    assert S.classifica("Me la mandi, senza impegno") == "positivo"
    assert S.classifica("Se vuole inviare a titolo gratuito faccia pure.") == "positivo"
    assert S.classifica("mandatela pure, grazie") == "positivo"


@prova("la rilettura blocca chi chiede la rimozione da qualunque strada passi (caso Panorama, 6/10)")
def _():
    import rilettura as R
    scritti = []
    vero = R.sb
    try:
        R.sb = lambda m, path, corpo=None, h=None: scritti.append((m, path, corpo))
        R.blocca({"email": "Info@Esempio.it"})
    finally:
        R.sb = vero
    assert scritti and scritti[0][1] == "/rest/v1/suppressions" and scritti[0][2][0]["email"] == "info@esempio.it"
    src = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "rilettura.py")).read()
    assert src.count("blocca(p)") >= 2, "la strada «decisa da sola» non blocca chi chiede la rimozione"


@prova("il sync non riapre un'attesa chiusa sulla stessa risposta, solo se il lead riscrive (6/10)")
def _():
    import sync_v2 as S
    chiusa = {"awaiting_us": False}
    assert S.attesa_da_sync(True, chiusa, False, "2026-10-05T13:17:15") is False, "la stessa risposta riapriva l'attesa di un no"
    assert S.attesa_da_sync(True, chiusa, True, "2026-10-06T09:00:00") is True, "una risposta nuova deve riaprire"
    assert S.attesa_da_sync(True, chiusa, True, "2020-01-01T00:00:00") is False, "oltre 30 giorni resta chiusa"
    assert S.attesa_da_sync(True, {"awaiting_us": True}, False, "2026-10-05T13:17:15") is True
    assert S.attesa_da_sync(True, None, True, "2026-10-06T09:00:00") is True, "un lead nuovo aspetta"
    # e il sync deve avere awaiting_us nei lead che carica, se no ogni attesa sembra chiusa (6/10, 11:43)
    src = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "sync_v2.py")).read()
    sel = src[src.index('rows = sb("GET", f"/rest/v1/prospects?select='):][:300]
    assert "awaiting_us" in sel, "il sync carica i lead senza awaiting_us: chiude le attese di chi aspetta noi"


@prova("le categorie di Dre su Smartlead: dalla classe del Workspace, mai su soppressi, fuori o fuori target (6/10)")
def _():
    import categorie_smartlead as C
    assert C.categoria_di({"classificazione": "positivo"}) == C.SI
    assert C.categoria_di({"classificazione": "positivo"}, intento="INT-03") == C.DOMANDA
    assert C.categoria_di({"classificazione": "tiepido"}) == C.DOMANDA
    assert C.categoria_di({"classificazione": "rinvio"}) == C.AVANTI and C.categoria_di({"classificazione": "ooo"}) == C.AVANTI
    assert C.categoria_di({"classificazione": "persona_sbagliata"}) == C.GIRATO
    assert C.categoria_di({"classificazione": "tiepido"}, girato=True) == C.GIRATO
    assert C.categoria_di({"classificazione": "negativo"}) == C.NO and C.categoria_di({"classificazione": "nervoso"}) == C.NO
    for c in ("soppresso", "fuori_target", "da_classificare", None):
        assert C.categoria_di({"classificazione": c}) is None, c
    assert C.categoria_di({"classificazione": "positivo", "fuori": True}) is None, "pipeline e clienti senza call non si toccano"
    # 6/10, Dre: «Meeting booked = quelli sul workspace». Chi ha una call vince su tutto...
    assert C.categoria_di({"classificazione": "positivo", "fuori": True}, call=True) == C.MEETING
    assert C.categoria_di({"classificazione": None}, call=True) == C.MEETING, "una call prenotata basta, anche senza classe"
    assert C.categoria_di({"classificazione": "rinvio"}, call=True) == C.MEETING
    # ...e vince anche su fuori target e sui no (Dre 6/10: «ogni persona che prenota finisce
    # in workspace», poi decide lui); restano fuori solo soppressi e persi
    assert C.categoria_di({"classificazione": "fuori_target"}, call=True) == C.MEETING
    assert C.categoria_di({"classificazione": "negativo"}, call=True) == C.MEETING
    assert C.categoria_di({"classificazione": "soppresso"}, call=True) is None
    assert C.categoria_di({"classificazione": "negativo", "fuori": True, "pipeline_stage": "perso"}, call=True) is None
    # chi chiede informazioni senza una classe prende la Information Request standard (Cadeddu)
    assert C.categoria_di({"classificazione": "da_classificare"}, testo="non ho capito bene di cosa si tratta, e cio che ci state proponendo?") == C.INFO
    assert C.categoria_di({"classificazione": "da_classificare"}, testo="Risposta ricevuta (Smartlead)") is None
    assert C.categoria_di({"classificazione": "da_classificare"}, testo="Thank you for your email! Your message has been received and is being reviewed by our support staff. What is your WordPress login?") is None, "un autorisponditore non chiede informazioni"
    # dal campione letto prima di scrivere (6/10)
    assert C.categoria_di({"classificazione": "ooo"}, testo="Hello, my email address has recently changed") == C.GIRATO
    assert C.categoria_di({"classificazione": "ooo"}, testo="questa casella di posta verra' dismessa in data 30.04") == C.GIRATO
    assert C.categoria_di({"classificazione": "ooo"}, testo="sono fuori ufficio fino al 12") == C.AVANTI
    assert C.categoria_di({"classificazione": "positivo"}, girato=True, testo="Ok grazie") == C.SI, "un si' con un inoltro resta un si'"
    assert C.categoria_di({"classificazione": "tiepido"}, testo="la ringrazio ma non è di nostro interesse") is None, "un no scritto non si etichetta come domanda"
    assert C.categoria_di({"classificazione": "tiepido"}, testo="mi occupo della parte commerciale, ho girato la vostra mail all'ufficio competente") == C.GIRATO


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
    senza = M.in_html("Le allego l'analisi: https://x.supabase.co/storage/v1/object/sign/vault/analisi/acme.pdf?token=abc fine.")
    assert "storage" not in senza and "allego" in senza, senza
    assert M.controlla("Le propongo {{CALENDARIO}}") == ["segnaposto lasciato nel testo"]


@prova("manda: si manda solo cio' che ha un approvatore (regola nel codice)")
def _():
    src = open(os.path.join(os.path.dirname(__file__), "manda.py"), encoding="utf-8").read()
    assert 'stato=eq.approvata' in src, "manda deve leggere solo le proposte approvate"
    assert 'approvata_da' in src and 'in_invio' in src, "manda deve controllare chi ha approvato e mettere il lucchetto"


# ── 4. il Revisore: chi ha risposto non si cancella ─────────────
@prova("Revisore: esclude chi ha risposto, i fuori, i bloccati, i soppressi")
def _():
    import revisore as P
    veri = (P._ha_risposto, P._seconda_testa, P.di_clara)
    P._ha_risposto = lambda e: e == "ha.risposto@x.it"
    P._seconda_testa = lambda *a, **k: "OK"
    P.di_clara = lambda *a, **k: None
    try:
        righe = [{"email": "ha.risposto@x.it"}, {"email": "fuori@x.it", "fuori": True}, {"email": "b@x.it", "bloccato": True},
                 {"email": "s@x.it", "classificazione": "soppresso"}, {"email": "ok@x.it"}]
        tenute = P.controlla("cancello lead dalle campagne", righe, irreversibile=True, motivo="prova")
        assert [r["email"] for r in tenute] == ["ok@x.it"], tenute
    finally:
        # 29/9: queste tre restavano finte per tutti i test dopo, e un invariante
        # vero cadeva per colpa loro. Il test che sporca ripulisce, sempre.
        P._ha_risposto, P._seconda_testa, P.di_clara = veri


# ── 5. il follow-up: template parola per parola, nome giusto ──────
@prova("mai una bozza a un cliente, a chi e' in pipeline, perso, senza follow-up o bloccato (caso Zafferano)")
def _():
    from stanza import contattabile
    assert contattabile({"fuori": False, "stage": "risposto", "classificazione": "positivo"})
    for p in ({"fuori": True, "stage": "risposto", "pipeline_stage": "prova"}, {"stage": "cliente"}, {"pipeline_stage": "cliente"},
              {"stage": "perso"}, {"no_followup": True}, {"classificazione": "soppresso"}, {"classificazione": "nervoso"}, None):
        assert not contattabile(p), p
    src = open(os.path.join(os.path.dirname(__file__), "manda.py"), encoding="utf-8").read()
    assert "contattabile(stato_p)" in src, "manda deve controllare la scheda prima di mandare"


@prova("bozze: mai una chiusura scritta da Clara, mai righe interne nel testo")
def _():
    import bozze
    assert any("riga interna" in e for e in bozze.cancello("Salve Rino,\n\ngrazie.\n\n[ESCALATION] Allegro, INT-15"))
    assert any("chiusura" in e for e in bozze.cancello("Salve,\n\nper policy lavoriamo solo con realtà indipendenti. Non la disturberò oltre e la rimuovo dalle nostre liste."))


@prova("lettura: i quattro errori del 25/9 fermano la bozza in codice, prima del modello")
def _():
    import lettura as L
    base = {"ultima_loro": "Ho letto l'analisi, grazie, ma non fa per noi.", "ultima_loro_il": "2026-08-12", "ultima_nostra": "", "ultima_nostra_il": "",
            "scritto_dopo_di_lei": 0, "analisi_ricevuta": False, "analisi_gia_letta": False, "detto_no": False, "autorisposta": False, "girato_a": []}
    # 1. gli abbiamo gia' scritto dopo la sua mail: «la mail non era partita» sarebbe una bugia
    assert L.regola_dura("RIPRESA", {**base, "scritto_dopo_di_lei": 1})[0] == "salta"
    # 2. ha gia' l'analisi: la ripresa la promette come nuova
    assert L.regola_dura("RIPRESA", {**base, "analisi_ricevuta": True})[0] == "salta"
    # 3. ha detto no: nessun ricontatto; in una risposta normale ci si ferma
    assert L.regola_dura("FOLLOW UP 1", {**base, "detto_no": True})[0] == "salta"
    assert L.regola_dura(None, {**base, "detto_no": True}, "positivo")[0] == "fermati"
    # 4. autorisposta: non e' una persona (salvo il gruppo dopo le ferie)
    assert L.regola_dura(None, {**base, "autorisposta": True}, "positivo")[0] == "fermati"
    assert L.regola_dura("RICONTATTO OOO", {**base, "autorisposta": True}, "ooo") is None
    # senza l'ultima mail loro non si scrive alla cieca, ma non si salta in silenzio ogni
    # giro: va UNA volta davanti a Dre (4/10, Salvatore: risposta con la sola firma)
    assert L.regola_dura(None, {**base, "ultima_loro": ""})[0] == "fermati"
    # i fatti si leggono dal testo vero
    assert L.DETTO_NO.search("la ringrazio ma non è di nostro interesse")
    assert L.AUTORISPOSTA.search("CONFERMIAMO L'AVVENUTA RICEZIONE. PROVVEDEREMO AD EVADERLA")
    assert L.GIA_LETTA.search("la ringrazio per il materiale che mi ha trasmesso")


@prova("bozze: ogni proposta «risposta» porta la lettura (il database la rifiuta altrimenti, schema_v58)")
def _():
    src = open(os.path.join(os.path.dirname(__file__), "bozze.py"), encoding="utf-8").read()
    # ogni proponi di tipo risposta/umano nel motore passa una azione con la lettura dentro
    import re as _re
    for m in _re.finditer(r"proponi\((?:\"umano\" if ferma else \"risposta\"|\"risposta\")[^\n]*azione=(\w+)", src):
        assert m.group(1) in ("azione",) or "lettura" in src[m.start():m.end() + 200], m.group(0)
    assert '"lettura": b["lettura"]' in src and '"lettura": lett' in src
    # nessuno scrive piu' bozze da template alla cieca: followup e ripresa mettono solo in coda
    for f in ("followup.py", "strumenti/ripresa.py"):
        t = open(os.path.join(os.path.dirname(__file__), f), encoding="utf-8").read()
        assert "proponi(" not in t, f"{f} scrive ancora proposte"
        assert '"coda"' in t


@prova("prezzo: budget dalla regola di Carlo (10-25 €/giorno), canone dal listino, tetto non circolare, mai in una mail prima della call (12/10)")
def _():
    import prezzo as Z, manda as M, mercato as K
    P = {"base": 1400, "conversione": 0.006, "tetto_quota": 1 / 3,
         "scaglioni": [[1000000, 0.02], [3000000, 0.015], [10000000, 0.01], [None, 0.005]], "quota_agenzia": 0.25,
         "margine": [[0, 0.5], [0.03, 0.7], [0.08, 1.0], [0.15, 1.2], [None, 1.4]]}
    assert Z.scaglioni(8_000_000, P["scaglioni"]) == 100000                    # a scaglioni, come l'IRPEF
    # il budget: mai fuori dai paletti, qualunque domanda gli si dia (il 15.100 nasceva da 179.720 ricerche)
    for tam, cpc in ((179720, 3.11), (5960, 3.11), (1345300, 1.89), (550, 0.45), (1650, 19.09)):
        bg, _ = K.regola_budget(tam, cpc, "prova")
        assert 10 <= bg <= 25, f"budget {bg} €/giorno fuori dai paletti per {tam} × {cpc}"
    assert K.regola_budget(1650, 19.09, "retainer")[0] == 30
    # il caso di Dre: 15.100 €/mese e 2.000-2.800 di canone → ~19 €/giorno e il listino
    b = Z.calcola({"enriched": {}}, P, {"tam": 179720, "cpc_medio": 3.11}, {"ticket_min": 300, "ticket_fonte": "stima"}, {}, (1400, 1800))
    assert b["spesa_ads_mese"] <= 750 and b["punto"] == 1400 and b["fascia"] == [1400, 1400] and b["prova"] == 1800, b
    assert b["tetto_mese"] is not None and b["tetto_mese"] < 1400 and any("supera" in f for f in b["flag"]), "il tetto non puo' piu' confermare una spesa gonfiata"
    # col bilancio in perdita: il flag resta; con i numeri della chiamata: la fascia sale, mai oltre il doppio
    c = Z.calcola({"enriched": {"bilancio": {"fatturato": 2000000, "utile": -1, "anno": 2025}}}, P, {"tam": 91020, "cpc_medio": 3.54}, {}, {}, (1400, 1800))
    assert any("rischio" in f for f in c["flag"]) and c["punto"] == 1400
    d = Z.calcola({"enriched": {"valore": {"clienti_extra_anno": 60, "valore_cliente": 5000, "margine_lordo": 0.4}}}, P, {"tam": 5960, "cpc_medio": 3.11}, {}, {}, (1400, 1800))
    assert d["affidabilita"] == "alta" and d["fascia"][0] == 1400 and 1400 < d["fascia"][1] <= 2800, d["fascia"]
    assert Z.calcola({"enriched": {}}, P, None, {}, {}, (1400, 1800)) is None                 # senza niente, niente numero
    # la mail: il prezzo e' interno prima della chiamata; dopo la tecnica il listino puo' stare in un preventivo
    assert M.controlla("il canone sarebbe 2.000 € al mese", {"enriched": {"prezzo": {"punto": 2000, "fascia": [1700, 2300]}}})
    assert M.controlla("il canone sarebbe 1.400 € al mese", {"pipeline_stage": "conoscitiva", "enriched": {"prezzo": {"punto": 1400, "fascia": [1400, 1400]}}})
    dopo = M.controlla("come da preventivo, 1.400 € al mese", {"pipeline_stage": "tecnica", "enriched": {"prezzo": {"punto": 1400, "fascia": [1400, 1400]}}})
    assert not any("interno" in x for x in dopo), dopo
    # la card Mercato della scheda legge lo stesso numero pulito
    import json
    mj = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src", "lib", "mercato.json")))
    assert mj["agenzie_immobiliari|milano"]["ricerche"] == K.domanda("agenzie_immobiliari", "Milano")[0] < 100000
    assert mj["_alias"]["pesaro"] == "pesaro e urbino" and mj["_misurato_il"] >= "2026-10-12"
    # il fit nuovo non ha piu' un budget fisso
    src = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "fit_nuovo.py")).read()
    assert "BUDGET_ADS" not in src and "regola_budget" in src


@prova("i promemoria interni non sono mail: la regola Zafferano colpisce solo chi porta un testo (26/9)")
def _():
    # Il 25/9 la regola vietava OGNI proposta per chi non e' contattabile: cosi'
    # azioni.py non riusciva piu' a dire «il preventivo e' fermo da 15 giorni»,
    # perche' quei promemoria parlano proprio di clienti. Nessuno veniva avvisato
    # di niente, in silenzio, per giorni. Il divieto vale per le MAIL, cioe' per
    # le proposte che portano azione.bozza: qui si verifica che il trigger dica
    # esattamente questo, senza bisogno di toccare il database.
    import os
    sql = open(os.path.join(os.path.dirname(__file__), "..", "supabase", "schema_v61.sql"), encoding="utf-8").read()
    riga = next(r for r in sql.splitlines() if "new.tipo in ('risposta', 'umano')" in r)
    assert "azione ? 'bozza'" in riga, "il divieto deve guardare prima se c'e' un testo da mandare"
    # e chi traduce il nome in identificativo non deve sparire: era l'altra meta' del bug
    import azioni
    assert hasattr(azioni, "chi_e"), "azioni.py deve tradurre «Carlo» nell'id della persona"


@prova("il registro sa sempre chi ha scritto, anche da «python3 -c» (26/9: 401 righe anonime su 713)")
def _():
    import stanza
    assert stanza._chi_scrive() not in ("", "-c", "-", "python", "python3"), "senza un nome, dopo un guaio non si risale a chi ha cambiato cosa"
    assert not stanza._chi_scrive().startswith("<")


@prova("il controllo di salute regge le date del database, con qualunque numero di decimali")
def _():
    import salute
    for s in ("2026-09-26T04:43:58.65214+00:00", "2026-09-26T04:43:58.123456+00:00",
              "2026-09-26T04:43:58+00:00", "2026-09-26T04:43:58.1Z"):
        assert salute.quando(s).year == 2026, f"non legge {s}"


# ── 6. Clara riempie: niente slop ─────────────────────────────────
@prova("arricchisci: le parole generiche non bastano a riconoscere un sito")
def _():
    import arricchisci as R
    assert R.parole("Studio Galilei Srl") == ["galilei"]
    assert R.parole("Impresa Servizi Srl") == []
    assert R.parole("Thermalink") == ["thermalink"]


# ── 17-19. i tre guardiani nati dal controllo del 26-27/9 ─────────
@prova("il vuoto non mente: una lettura fallita si dice, non diventa «non c'è niente»")
def _():
    import pathlib
    for f, bugia in (("Clienti.tsx", "Nessun cliente ancora"), ("Calendario.tsx", "Niente in programma")):
        t = pathlib.Path(__file__).resolve().parents[1].joinpath("src", "components", f).read_text(encoding="utf-8")
        assert bugia in t, f"{f}: sparito il vuoto che insegna"
        assert "Non sono riuscito a leggere" in t, f"{f}: il guasto non si distingue dal vuoto"
        assert "setGuaio" in t, f"{f}: nessuno registra l'errore di lettura"


@prova("chi fallisce esce dalla fila: due bocciature e l'analisi diventa una domanda")
def _():
    import analisi_auto as A
    assert A.MAX_TENTATIVI == 2
    assert A._quante_bocciature({"enriched": {"analisi": {"bocciature": 2}}}) == 2
    assert A._quante_bocciature({}) == 0
    fila = [{"enriched": {"analisi": {"bocciature": 1}}, "company": "gia' provata"},
            {"enriched": {}, "company": "mai provata"}]
    fila.sort(key=A._quante_bocciature)
    assert fila[0]["company"] == "mai provata", "chi ha gia' fallito deve passare dietro"


@prova("una riunione, una riga: gli eventi uguali del pod si uniscono coi nomi")
def _():
    import pathlib
    t = pathlib.Path(__file__).resolve().parents[1].joinpath("src", "components", "Calendario.tsx").read_text(encoding="utf-8")
    assert "const insieme = new Map<string, Voce>()" in t, "l'unione degli eventi del pod non c'e' piu'"
    assert "${a.at}|${(a.titolo ?? '').trim().toLowerCase()}" in t, "la chiave dell'unione e' cambiata"


@prova("il bottone non promette un invio che non c'è: se «manda» è spento, si dice")
def _():
    import pathlib
    src = pathlib.Path(__file__).resolve().parents[1].joinpath("src", "components")
    for f in ("ClaraVolante.tsx", "DaMandare.tsx"):
        t = src.joinpath(f).read_text(encoding="utf-8")
        assert "chkave" not in t
        assert "'manda'" in t and "operazioni" in t, f"{f}: non legge piu' se l'invio e' acceso"
        assert "non parte" in t.lower(), f"{f}: il bottone promette un invio che potrebbe non esserci"
    # e il controllo di salute se ne accorge
    t = pathlib.Path(__file__).resolve().parent.joinpath("salute.py").read_text(encoding="utf-8")
    assert "l'invio automatico è SPENTO" in t, "la salute non segnala piu' l'invio spento"


@prova("le date del database si leggono con qualunque numero di decimali, ovunque")
def _():
    import datetime
    from stanza import quando
    # Postgres scrive i microsecondi senza zeri finali: sotto Python 3.11 rompeva
    # salute.py (26/9) e il direttore (28/9), e il guasto si vedeva solo sul Mac
    for t in ("2026-09-28T06:10:28.13447+00:00", "2026-09-27T07:43:57.97532+00:00",
              "2026-09-25T14:19:38.396988+00:00", "2026-09-25T14:19:38Z", "2026-09-25T14:19:38.1+00:00"):
        d = quando(t)
        assert isinstance(d, datetime.datetime) and d.tzinfo is not None, t
    # e chi legge le date delle operazioni deve usarla, non fromisoformat a mano
    import pathlib
    t = pathlib.Path(__file__).resolve().parent.joinpath("direttore.py").read_text(encoding="utf-8")
    assert "quando(ultima)" in t, "il direttore e' tornato a leggere le date a mano"


@prova("copia e incolla: «Fatto, l'ho mandata» c'è e chiude il giro, in Posta e nella scheda")
def _():
    import pathlib
    src = pathlib.Path(__file__).resolve().parents[1].joinpath("src", "components")
    for f in ("ClaraVolante.tsx", "DaMandare.tsx"):
        t = src.joinpath(f).read_text(encoding="utf-8")
        assert "Fatto, l'ho mandata" in t, f"{f}: sparito il gesto di chi manda a mano"
        # deve chiudere il giro: la mail nella storia, l'attesa tolta, la bozza chiusa
        assert "kind: 'email_out'" in t, f"{f}: la mail mandata a mano non entra nella storia"
        assert "awaiting_us: false" in t, f"{f}: l'attesa resta accesa dopo un invio a mano"
        assert "stato: 'fatta'" in t, f"{f}: la bozza non si chiude"


@prova("una prova a secco non scrive: proponi() si ferma da solo con --prova")
def _():
    import sys, stanza, importlib
    # 28/9: una prova di bozze.py ha creato otto proposte vere nella Posta di Dre,
    # perche' il controllo stava nel singolo script invece che nel motore.
    vecchio = list(sys.argv)
    try:
        sys.argv.append("--prova")
        importlib.reload(stanza)
        assert stanza._a_secco() is True, "non riconosce piu' la prova a secco"
        assert stanza.proponi("umano", "prova invariante: non deve scrivere") is None, "una prova a secco ha scritto in Posta"
    finally:
        sys.argv[:] = vecchio
        importlib.reload(stanza)
    # e senza nessuna bandiera torna a scrivere davvero. Qui dentro non si puo'
    # provare togliendo l'ambiente, perche' questo stesso file mette POLIZIA_PROVA=1
    # in cima (riga 19): si prova in un processo pulito.
    import subprocess, pathlib
    fuori = subprocess.run(
        ["python3", "-c", "import sys; sys.path.insert(0, '.'); import stanza; print(stanza._a_secco())"],
        cwd=str(pathlib.Path(__file__).resolve().parent), capture_output=True, text=True, env={"PATH": "/usr/bin:/bin"})
    assert fuori.stdout.strip() == "False", f"senza bandiere crede di essere in prova: {fuori.stdout!r} {fuori.stderr[:200]}"


@prova("la scrivania: chi scrive vede TUTTA la sequenza, non due messaggi")
def _():
    import pathlib
    t = pathlib.Path(__file__).resolve().parent.joinpath("bozze.py").read_text(encoding="utf-8")
    # 28/9: la storia si prendeva dal CRM, che non ha le mail partite da Smartlead.
    # Su Istituto Flegreo il modello vedeva 2 righe su 6, tutte e due in arrivo,
    # e scriveva senza sapere cosa gli avevamo gia' mandato.
    assert 'fatti["sequenza"]' in t, "sparita la sequenza dai fatti"
    assert "lettura.filo(p)" in t, "la sequenza non viene piu' dal filo vero (CRM + Smartlead)"
    assert "quante_ne_abbiamo_mandate" in t, "non si conta piu' quante gliene abbiamo mandate"
    assert "LA SCRIVANIA" in t, "l'istruzione non dice piu' al modello di leggere la sequenza"


@prova("il rifiuto si cerca solo nelle SUE righe, non nella nostra mail citata sotto")
def _():
    import lettura as L
    import analisi_auto as A
    # 28/9, caso della lead immobiliare: ha risposto «si grazie sono curiosa» e il sistema
    # l'ha saltata perche' la parola «cancellarlo» stava nella NOSTRA firma sul
    # GDPR, citata sotto la sua risposta. Sei falsi allarmi su 300 risposte vere.
    vero_si = ("Buon pomeriggio, si grazie sono curiosa.\nMaria Rossi\n\n"
               "Il giorno lun 28 set 2026 alle ore 12:42 Lorenzo ha scritto:\n"
               "Le chiedo di cancellare i nostri dati. GDPR")
    assert A.NON_TOCCARE.search(vero_si), "la prova non regge: la frase deve bloccare nel testo intero"
    assert not A.NON_TOCCARE.search(L.solo_suo(vero_si)), "un si' viene ancora scambiato per un no"
    # e un no vero resta un no
    vero_no = "Non sono interessato, vi chiedo di rimuovermi dalla mailing list. Grazie"
    assert A.NON_TOCCARE.search(L.solo_suo(vero_no)), "un no vero non viene piu' riconosciuto"
    # le righe citate con «>» non contano
    assert L.solo_suo("va bene grazie\n> non ci contatti piu'").strip() == "va bene grazie"
    # 28/9, caso Cristian Porta: «sarei felice di ricevere la vostra analisi»,
    # bloccato da «privacy» dentro la SUA firma. E Giuseppe: «mandi pure
    # l'analisi», bloccato dal disclaimer legale. Su 300 risposte vere i falsi
    # allarmi erano 27 su 36 blocchi totali.
    si_con_firma = ("Sarei felice di ricevere la vostra analisi.\nCordiali saluti, Cristian\n"
                    "La Baita Case\nInformativa privacy disponibile sul nostro sito.")
    assert not A.NON_TOCCARE.search(L.solo_suo(si_con_firma)), "la firma blocca ancora un si'"
    si_con_disclaimer = ("Mandi pure l'analisi qui via mail, la leggo volentieri.\nGiuseppe\n"
                         "Le informazioni trasmesse sono destinate esclusivamente alla societa'")
    assert not A.NON_TOCCARE.search(L.solo_suo(si_con_disclaimer)), "il disclaimer blocca ancora un si'"
    # e le parole vanno prese nel loro senso: «smettere» in una frase normale non blocca
    normale = "la software house dovrebbe concludere le attivita' entro domani, poi smetteremo di aspettare"
    assert not A.NON_TOCCARE.search(L.solo_suo(normale)), "una frase normale viene scambiata per un no"
    for no in ("la smetta di mandarmi e-mail", "vi chiedo di rimuovermi dalla vostra mailing list",
               "finiscila con questi spam", "cancellami"):
        assert A.NON_TOCCARE.search(L.solo_suo(no)), f"un no vero non viene riconosciuto: {no}"


@prova("un si' con l'informativa in fondo non diventa un no, un no vero resta no (12/10)")
def _():
    import lettura as L
    import sync_v2 as S
    # 12/10: due si' approvati fermati dal postino come «ha detto no». Il «cancellare il
    # messaggio» dell'informativa, e «Buongiorno, grazie» letto come «no, grazie».
    si = ("Buongiorno, certamente potete inviarci la vs analisi.\nBuon lavoro\n"
          "Restando a disposizione porgo i migliori saluti.\n"
          "Il presente messaggio e gli eventuali allegati sono destinati esclusivamente ai destinatari indicati. "
          "Se ha ricevuto questa e-mail per errore, La invitiamo a cancellare il messaggio.")
    si2 = ("Buongiorno a lei,\nCerto che mi fa piacere riceverla, la ringrazio\nCordialità\nMario\n"
           "Questa mail contiene informazioni riservate. Qualora fosse stato ricevuto per errore "
           "si prega di cancellare la copia in proprio possesso.")
    for t in (si, si2, "Buongiorno, grazie inviateci pure la presentazione"):
        assert not L.DETTO_NO.search(L.solo_suo(t)), f"un si' letto come no: {t[:50]}"
        assert S.classifica(S.testo_suo(t)) != "negativo", f"il sync lo fa no: {t[:50]}"
    for no in ("cancellatemi dalla vostra lista", "vi prego di rimuovere il mio indirizzo",
               "no grazie", "La ringraziamo ma non siamo  interessati.",
               "Buongiorno, grazie per il suo servizio, siamo già seguiti da professionisti."):
        assert L.DETTO_NO.search(L.solo_suo(no)), f"un no vero non si riconosce piu': {no}"
        assert S.classifica(S.testo_suo(no)) == "negativo", f"il sync non lo fa no: {no}"


@prova("il testo del sito si tiene, e la provincia ha una rete se il modello non la trova")
def _():
    import googlefit as G
    import pathlib
    # 28/9: «sito_letto: true» ma il testo buttato via, per tutte e 265 le aziende
    # lette. Senza testo la provincia dipendeva dal caso: 161 su 313 restavano
    # vuote, e senza provincia l'analisi non trova mai i volumi del mercato.
    t = pathlib.Path(__file__).resolve().parent.joinpath("googlefit.py").read_text(encoding="utf-8")
    assert '"sito_testo"' in t, "il testo del sito non si salva piu'"
    # la rete trova una provincia vera nominata nel sito
    assert G._provincia_dal_testo("Via Nazionale 4, Berbenno di Valtellina, provincia di Sondrio") == "Sondrio"
    # e NON inventa. 28/9: la prima versione ha dedotto «Latina» per Viaggi del
    # Mappamondo, perche' nel sito c'era «America Latina», una destinazione
    # turistica. Il nome vale solo accanto a qualcosa che indica una sede vera.
    assert G._provincia_dal_testo("Azienda leader nel settore, contattaci") == ""
    assert G._provincia_dal_testo("sedi a Milano e a Roma, due uffici") == ""
    assert G._provincia_dal_testo("MALDIVE MAURITIUS AMERICA LATINA destinazioni") == ""
    assert G._provincia_dal_testo("viaggi in America Latina e tour a Roma") == ""
    # e riconosce una sede vera
    assert G._provincia_dal_testo("20121 Milano, via Torino 5") == "Milano"
    assert G._provincia_dal_testo("Agenzia con sede in Sondrio e filiale a Milano") == "Sondrio"


@prova("se chiede l'analisi la riceve, qualunque cosa dica il fit (playbook INT-01)")
def _():
    import analisi_auto as A
    # Dre, 29/9: «inviamo comunque e chiediamo la call, seguiamo il playbook tutte
    # le volte possibili». INT-01 dice «manda analisi + presentazione, poi orario
    # proposto + calendario», senza eccezioni per il verdetto del fit.
    for chiede in ("Può inviarmi pure l'analisi al mio indirizzo email",
                   "Buongiorno mi invii pure l'analisi",
                   "si grazie sono curiosa",
                   "confermo la mail",
                   "resto in attesa dell'analisi",
                   "grazie molto volentieri"):
        assert A.CHIEDE_ANALISI.search(chiede), f"non riconosce una richiesta: {chiede}"
    # e non scatta su chi non la chiede
    for no in ("La ringrazio per la proposta, ma al momento non siamo interessati",
               "il progetto e' in stand by, se qualcuno riprende ben volentieri",
               "Grazie per aver inviato l'e-mail. Quanto prima provvederemo a rispondere"):
        assert not A.CHIEDE_ANALISI.search(no), f"scatta dove non deve: {no[:40]}"


@prova("mai promettere un'analisi che non puo' nascere (fit NO)")
def _():
    import bozze as B
    # 29/9: Elettroone ha chiesto «puo' inviarmi pure l'analisi» e la bozza ha
    # risposto «le inoltro qui l'analisi». Ma il fit diceva NO (50 ricerche al
    # mese a Trento), quindi quel documento non sarebbe mai nato. Stesso caso su
    # Studio Canova. Promettere una cosa che non arriva e' peggio di un no.
    promette = ("Salve, grazie. Le inoltro qui l'analisi che abbiamo fatto sulla vostra azienda. "
                "Le propongo giovedì alle 15, qui il calendario: https://calendar.app.google/x")
    assert B.cancello(promette, senza_analisi=True), "una bozza promette ancora un'analisi impossibile"
    assert not B.cancello(promette, senza_analisi=False), "il cancello blocca anche quando l'analisi c'e'"
    onesta = ("Salve, grazie per il riscontro. Le dico subito una cosa: su Google la domanda "
              "nel vostro settore e nella vostra zona e' troppo bassa perche' valga la spesa. "
              "Le propongo comunque una chiacchierata: https://calendar.app.google/x")
    assert not B.cancello(onesta, senza_analisi=True), "una risposta onesta non deve essere bloccata"


@prova("l'archivio non tocca chi e' vivo, e chi riscrive rientra da solo")
def _():
    import archivio as A
    import pathlib
    # 29/9: pipeline a 83 righe, 72 ferme da oltre un mese, lavoro vero 11 righe.
    # L'archivio ne ha tolte 59, tutti «no» vecchi di mesi.
    for c in ("positivo", "tiepido", "rinvio", "ooo", "da_classificare"):
        assert c in A.VIVI, f"un {c} potrebbe finire in archivio: non deve mai"
    for f in ("cliente", "prova", "avvio", "call_fissata"):
        assert f in A.INTOCCABILI, f"un {f} potrebbe finire in archivio"
    # il risveglio sta nel database, non in uno script che qualcuno lancia
    sch = pathlib.Path(__file__).resolve().parents[1].joinpath("supabase", "schema_v62.sql").read_text(encoding="utf-8")
    assert "risveglia_se_scrive" in sch and "prospects_risveglio" in sch, "sparito il risveglio automatico"
    assert "archiviato_il := null" in sch, "chi riscrive non rientra piu' da solo"


@prova("il Revisore sa su cosa sta guardando: Smartlead o solo il nostro database")
def _():
    import inspect
    import revisore as P
    # 29/9: ha fermato un'archiviazione reversibile credendo che cancellasse i
    # thread della Master Inbox. Nessuno gli diceva la differenza. Un poliziotto
    # che ferma tutto viene disattivato, e allora non serve piu' a niente.
    assert "dove" in inspect.signature(P.controlla).parameters, "il Revisore non sa piu' dove agisce"
    # la prova vera: il piano che legge il modello cambia davvero fra i due casi
    visti = {}
    def finto(prompt, modello=None):
        visti[len(visti)] = prompt
        return "OK"
    import cervello
    vero, cervello._chiedi = cervello._chiedi, finto
    try:
        P._seconda_testa("prova", "prova", 1, [], 0, dove="smartlead")
        P._seconda_testa("prova", "prova", 1, [], 0, dove="crm")
    finally:
        cervello._chiedi = vero
    assert len(visti) == 2, "il Revisore non ha nemmeno letto il piano"
    assert "cancella anche il thread" in visti[0], "su Smartlead non avverte piu' del danno del 24/9"
    assert "niente viene cancellato" in visti[1], "sul nostro database spaventa il Revisore per niente"


@prova("i quattro ruoli: ogni agente ha il mansionario, e chi corregge non manda")
def _():
    import cervello
    import pathlib
    # 29/9, dal metodo dei quattro ruoli: ogni agente sa dove finisce il suo
    # mestiere. Il mansionario dice cosa non puo' MAI fare, e i prompt lo caricano.
    for nome in ("revisore", "preparatore", "raccolta"):
        t = cervello.ruolo(nome)
        assert t, f"manca il mansionario di {nome}"
        assert "Non puoi MAI" in t, f"il mansionario di {nome} non dice cosa non puo' fare"
    qui = pathlib.Path(__file__).resolve().parent
    for f, ruolo in (("bozze.py", "preparatore"), ("analisi_auto.py", "raccolta"), ("revisore.py", "revisore")):
        src = qui.joinpath(f).read_text(encoding="utf-8")
        assert f'ruolo("{ruolo}")' in src or "{mansionario}" in src, f"{f} non carica il suo mansionario"
    # il vecchio nome non rompe nessuno script
    import polizia
    assert polizia.controlla is __import__("revisore").controlla, "il ponte polizia->revisore e' rotto"


@prova("le correzioni di Dre restano scritte anche quando manda a mano")
def _():
    import pathlib
    # 29/9: dal 28/9 si manda copia-incollando, e «Fatto, l'ho mandata» buttava
    # via la differenza fra la bozza di Clara e il testo corretto: `lezioni`
    # era cieco. La correzione DEVE finire in azione.bozza, in tutti e due i posti.
    su = pathlib.Path(__file__).resolve().parents[1].joinpath("src", "components")
    for f in ("DaMandare.tsx", "ClaraVolante.tsx"):
        src = su.joinpath(f).read_text(encoding="utf-8")
        blocco = src[src.index("bozza_originale: p"):] if f == "ClaraVolante.tsx" else src
        # nel salvataggio di «fatta» deve viaggiare anche l'azione con la bozza corretta
        assert "stato: 'fatta', azione" in src, f"{f}: il Fatto non salva piu' la correzione"
    # e lezioni.py legge proprio quel confronto
    lz = pathlib.Path(__file__).resolve().parent.joinpath("lezioni.py").read_text(encoding="utf-8")
    assert "bozza_originale" in lz and "differenze" in lz, "lezioni.py non confronta piu' le due versioni"


@prova("la prima risposta automatica: passa solo il caso semplice, e solo a interruttori accesi")
def _():
    import datetime
    import pathlib
    import prima_risposta as R
    # 29/9: Dre vuole che la prima risposta parta da sola. E' il punto piu'
    # delicato del sistema: approva al posto di una persona. Ogni porta del
    # cancello deve restare chiusa quando deve.
    let = {"coerenza": "COERENTE", "scritto_dopo_di_lei": 0, "ultima_loro": "si' grazie, mandatemi l'analisi"}
    pr = {"id": 1, "tipo": "risposta", "titolo": "Bozza per Rossi, INT-01",
          "azione": {"bozza": "Salve,\n\necco l'analisi.\nIl calendario: https://calendar.app.google/x", "intento": "INT-01", "lettura": let}}
    p = {"id": "x", "email": "a@b.it", "classificazione": "positivo", "stage": "risposto",
         "analysis_sent": False, "analysis_pdf": "https://x/analisi.pdf",
         # 13/10: la scheda completa per la regola unica (che ora va a prendere i campi mancanti)
         "fuori": False, "pipeline_stage": None, "no_followup": False}
    assert R.perche_no(pr, p) == [], R.perche_no(pr, p)
    # 2/10: l'alias dello stesso dominio (info@ per commerciale@) non e' un rimbalzo
    assert R.perche_no({**pr, "azione": {**pr["azione"], "lettura": {**let, "girato_a": ["c@b.it"]}}}, p) == []
    # il gigante buono e' passato dalla corsia dal 2/10 al 5/10; poi Dre l'ha spento
    # («niente analisi ai no: costa crediti»). Un INT-GB oggi NON passa.
    gb_pr = {**pr, "titolo": "Gigante buono per Rossi, INT-GB",
             "azione": {**pr["azione"], "intento": "INT-GB", "lettura": {**let, "gruppo": "GIGANTE BUONO", "detto_no": True}}}
    gb_p = {**p, "classificazione": "negativo"}
    assert R.perche_no(gb_pr, gb_p) != [], "il gigante buono e' spento (Dre 5/10): non deve passare"
    def con(pr_mod=None, let_mod=None, p_mod=None, az_mod=None):
        az = {**pr["azione"], "lettura": {**let, **(let_mod or {})}, **(az_mod or {})}
        return R.perche_no({**pr, **(pr_mod or {}), "azione": az}, {**p, **(p_mod or {})})
    for caso, motivo in (
        (con(pr_mod={"tipo": "umano"}), "una bozza «da guardare tu»"),
        (con(pr_mod={"titolo": "Da guardare tu: Rossi"}), "un titolo «da guardare tu»"),
        (con(let_mod={"gruppo": "FOLLOW UP 1"}), "un follow-up"),

        (con(az_mod={"intento": "INT-13"}), "una domanda sul prezzo"),

        (con(let_mod={"coerenza": "INCOERENTE"}), "una bozza incoerente"),
        (con(let_mod={"scritto_dopo_di_lei": 1}), "chi ha gia' avuto una nostra mail dopo la sua"),
        (con(let_mod={"detto_no": True}), "chi ha detto no"),
        (con(az_mod={"intento": "INT-GB"}, let_mod={"gruppo": "GIGANTE BUONO", "detto_no": True, "non_scrivere": True}), "un GB a chi chiede di non essere contattato"),
        (con(az_mod={"intento": "INT-GB"}, let_mod={"gruppo": "GIGANTE BUONO", "detto_no": True}, p_mod={"classificazione": "nervoso"}), "un GB a un nervoso"),
        (con(let_mod={"autorisposta": True}), "un'autorisposta"),
        (con(let_mod={"girato_a": ["c@ALTRO-dominio.it"]}), "un inoltro a un collega di un'altra azienda"),
        (con(p_mod={"email_alt": ["c@b.it"]}), "un indirizzo diverso"),
        (con(let_mod={"analisi_ricevuta": True}), "chi ha gia' l'analisi"),
        (con(p_mod={"analysis_sent": True}), "chi risulta gia' averla ricevuta"),
        (con(p_mod={"analysis_pdf": None}), "senza PDF dell'analisi"),
        (con(p_mod={"classificazione": "negativo"}), "un negativo"),
        (con(p_mod={"classificazione": "rinvio"}), "un rinvio"),
        (con(p_mod={"stage": "cliente"}), "un cliente (caso Zafferano)"),
        (con(p_mod={"no_followup": True}), "chi non va ricontattato"),
        (con(az_mod={"approvata_da": "qualcuno"}), "una gia' approvata"),
        (con(az_mod={"prima_risposta": {"esito": "resta a Dre"}}), "una gia' fermata dal Revisore"),
        (con(az_mod={"bozza": "Salve,\nvolentieri la call: https://calendar.app.google/x"}), "una prima risposta senza l'analisi (Yachtspassion)"),
        (con(az_mod={"bozza": "Salve,\necco l'analisi, resto a disposizione."}), "una prima risposta senza call (Optima, Mason)"),
        (con(az_mod={"bozza": "Salve,\nin chiamata vediamo insieme l'analisi: https://calendar.app.google/x"}), "una mail che non dice che l'analisi e' allegata (Yachtspassion)"),
        # 6/10, Dre: «se non supera il Google Fit mi scrive fuori target e decido io»
        (con(p_mod={"enriched": {"google_fit_v2": {"verdetto": "NO", "motivo": "domanda sotto soglia"}}}), "un fuori target per il fit nuovo, senza decisione di Dre"),
        (con(p_mod={"enriched": {"google_fit": {"verdetto": "NO"}}}), "un fuori target per il fit vecchio, senza decisione di Dre"),
    ):
        assert caso, f"la prima risposta automatica farebbe partire {motivo}"
    # la decisione di Dre «invia comunque» riapre la corsia; quella del fit nuovo
    # vince sul vecchio (un v2 SI con un v1 NO non e' bocciato)
    assert R.perche_no(pr, {**p, "enriched": {"google_fit_v2": {"verdetto": "NO"}, "google_fit_decisione": "invia"}}) == []
    assert R.perche_no(pr, {**p, "enriched": {"google_fit_v2": {"verdetto": "SI"}, "google_fit": {"verdetto": "NO"}}}) == []
    assert R.fit_bocciato({"enriched": {"google_fit_v2": {"verdetto": "NO"}, "google_fit_decisione": "soppresso"}})
    # la finestra: lun-ven 9-17 a Roma
    roma = R.ROMA
    # regola del 9/10 sera: tutti i giorni 8-21 (in giornata, mai di notte)
    assert R.finestra(datetime.datetime(2026, 9, 29, 10, 0, tzinfo=roma))       # martedi' 10:00
    assert R.finestra(datetime.datetime(2026, 9, 29, 18, 30, tzinfo=roma))      # martedi' sera
    assert R.finestra(datetime.datetime(2026, 10, 3, 11, 0, tzinfo=roma))       # sabato
    assert not R.finestra(datetime.datetime(2026, 9, 29, 7, 59, tzinfo=roma)), "un si' non parte prima delle 8"
    assert not R.finestra(datetime.datetime(2026, 9, 29, 21, 0, tzinfo=roma)), "un si' non parte dalle 21"
    assert not R.finestra(datetime.datetime(2026, 10, 3, 3, 0, tzinfo=roma)), "un si' non parte di notte"
    # i due interruttori: tutti e due accesi, o niente
    assert R.interruttori([{"chiave": "prima_risposta", "attiva": True}, {"chiave": "manda", "attiva": True}]) is None
    assert R.interruttori([{"chiave": "prima_risposta", "attiva": True}, {"chiave": "manda", "attiva": False}])
    assert R.interruttori([{"chiave": "prima_risposta", "attiva": False}, {"chiave": "manda", "attiva": True}])
    assert R.interruttori([{"chiave": "manda", "attiva": True}]), "senza riga in tabella deve fermarsi"
    # il Revisore: passa solo un OK netto, il resto e il silenzio restano a Dre
    assert R.verdetto_revisore("OK")[0] == "OK" and R.verdetto_revisore(" ok. ")[0] == "OK"
    for r in ("STOP: prezzo", "", None, "Okay ma", "Direi OK", "NON OK"):
        assert R.verdetto_revisore(r)[0] == "STOP", f"il Revisore farebbe passare «{r}»"
    # i tetti, e la firma che manda.py pretende (approvata_da) con gli allegati
    assert R.MAX_PER_GIRO <= 15 and R.MAX_AL_GIORNO <= 60, "il fusibile c'e' sempre: senza, un lettore impazzito manderebbe a tutti"
    # il primo invio in assoluto lo guarda Dre (28/9): finche' Clara non ha mai mandato niente, non si approva da sola
    assert "mai_mandato" in pathlib.Path(R.__file__).read_text(encoding="utf-8") and "primo invio da guardare" in pathlib.Path(R.__file__).read_text(encoding="utf-8")
    assert "prima-risposta-automatica" in R.FIRMA
    src = pathlib.Path(R.__file__).read_text(encoding="utf-8")
    assert '"allega": True, "allega_presentazione": True' in src, "la prima risposta deve partire con analisi e presentazione"
    assert "stato=eq.aperta" in src, "se Dre ha gia' toccato la bozza, l'automatico non deve sovrascriverla"
    assert "reply-email-thread" not in src, "chi approva non manda: l'invio resta a manda.py"
    # l'ombra (29/9): decide e scrive, non approva mai. Basta il suo interruttore.
    assert R.interruttori([{"chiave": "prima_risposta", "attiva": True}, {"chiave": "manda", "attiva": False}], ombra=True) is None
    assert R.interruttori([{"chiave": "prima_risposta", "attiva": False}], ombra=True), "l'ombra spenta non deve girare"
    ombra = src[src.index("        if OMBRA:\n            # la decisione"):]
    ombra = ombra[:ombra.index("            continue\n") + 20]
    assert "approvata" not in ombra and "di_clara" not in ombra, "in ombra non si approva e non si fa rumore"


@prova("una call in agenda sposta la scheda solo in avanti, e solo per una conoscitiva")
def _():
    import pathlib
    import calendario as C
    # 29/9, due lead con la call prenotata e le schede ferme a «da rispondere» /
    # «in follow-up». Si sposta solo chi sta fra la risposta e la call: mai un
    # cliente, un perso, un rinviato, un nuovo (lì un evento attaccato male sposterebbe a caso)
    for f in ("cliente", "perso", "rinviato", "nuovo", "call_fissata"):
        assert f not in C.PRIMA_DELLA_CALL, f"una call in agenda potrebbe spostare un {f}"
    src = pathlib.Path(C.__file__).read_text(encoding="utf-8")
    assert "tipo=eq.conoscitiva" in src, "solo le conoscitive spostano la fase"
    assert "pipeline_stage" in src and "&stage=eq." in src, "non deve toccare chi e' in pipeline, ne' chi e' cambiato nel frattempo"
    assert "fasi_dalle_call(prova)" in src, "il calendario non chiama piu' il passo delle fasi"


@prova("il trattino lungo lo toglie il codice: non costa un giro di analisi o di bozze")
def _():
    import pathlib
    from stanza import senza_trattini
    # 29/9: l'analisi di Naturalia bocciata cinque giri di fila (due ore) anche per il trattino
    assert "—" not in senza_trattini("a — b — c. d — e")
    assert senza_trattini("La zona — verificata — regge.") == "La zona (verificata) regge."
    qui = pathlib.Path(__file__).resolve().parent
    assert "_ripulisci(chiedi(" in qui.joinpath("analisi_auto.py").read_text(encoding="utf-8"), "l'analisi non si ripulisce piu' prima del cancello"
    assert "senza_trattini(bozza)" in qui.joinpath("bozze.py").read_text(encoding="utf-8"), "la bozza non si ripulisce piu' prima del cancello"
    d = qui.joinpath("direttore.py").read_text(encoding="utf-8")
    assert '("prima_risposta", "manda")' in d, "il campanello non porta piu' la bozza fino all'invio nello stesso giro"
    assert 'not op["attiva"] and not anche_spente' in d, "nella catena un'operazione spenta deve restare spenta"


@prova("niente parte da solo a chi stiamo gia' sentendo fuori da Smartlead (Gmail, call, note, calendario, task)")
def _():
    import prima_risposta as R
    # Dre 29/9: «molto importante non mandare follow-up a chi siamo in contatto».
    # Ogni traccia che il sistema raccoglie deve bastare da sola a fermare l'invio.
    vero = R.sb
    def finto(tracce):
        def sb(metodo, percorso, *a, **k):
            for chiave, righe in tracce.items():
                if percorso.startswith(chiave):
                    return righe
            return []
        return sb
    base = {"id": "x", "notes": None, "owner": None}
    try:
        R.sb = finto({})
        assert R.contatti_fuori(base) == [], "senza tracce deve passare"
        # le righe di servizio («era in ferie») non sono un contatto con una persona
        assert R.contatti_fuori({**base, "notes": "OOO: rientra il 2026-08-20 (dal loro messaggio: \"20 agosto\")\n"
                                                    "Pulizia del 23/9 (Achille): risposta automatica o ferie ormai passate, nessuna risposta vera"}) == []
        for tracce, p, cosa in (
            ({}, {**base, "notes": "sentito al telefono"}, "una nota fuori binario"),
            ({}, {**base, "notes": "OOO: rientra il 2026-08-20 (dal loro messaggio)\nindirizzo cambiato: riscrivere a x@y.it"}, "una nota vera sotto una di servizio"),
            ({}, {**base, "owner": "uuid"}, "chi l'ha presa in carico"),
            ({"/rest/v1/interactions": [{"kind": "email_out", "at": "2026-09-20", "ref": "gmail:1"}]}, base, "una mail da Gmail"),
            ({"/rest/v1/interactions": [{"kind": "transcript", "at": "2026-09-20", "ref": "gemini:1"}]}, base, "una call registrata"),
            ({"/rest/v1/agenda": [{"at": "2026-09-30", "titolo": "Conoscitiva"}]}, base, "una call in calendario"),
            ({"/rest/v1/task": [{"id": 1}]}, base, "una task aperta"),
        ):
            R.sb = finto(tracce)
            assert R.contatti_fuori(p), f"con {cosa} una mail partirebbe da sola"
    finally:
        R.sb = vero
    import pathlib
    src = pathlib.Path(R.__file__).read_text(encoding="utf-8")
    assert "contatti_fuori(p)" in src.split("def main")[1], "il cancello non guarda piu' i contatti fuori da Smartlead"


@prova("i follow-up li scrive il codice col testo di Dre: mai un segnaposto, mai un nome inventato")
def _():
    import pathlib
    import seguiti as S
    finto = ("## FOLLOW UP 1\n\n```\nSalve Stefania,\n\ntorno sull'analisi.\nUn saluto\n```\n"
             "MINI FOLLOW UP (25/9/2026)\n```\nSalve [Nome],\n\ndue righe: {{CALENDARIO}}\n```\n")
    t = S.testo("FOLLOW UP 1", {"name": "info"}, {"ultima_nostra": "Buongiorno, ecco l'analisi"}, "https://cal", finto)
    assert t.startswith("Salve,\n"), f"un nome inventato nel saluto: {t[:30]}"
    t = S.testo("FOLLOW UP 1", {}, {"ultima_nostra": "Salve Maura, le inoltro l'analisi"}, "https://cal", finto)
    assert t.startswith("Salve Maura,"), "non usa il nome con cui Dre gli ha gia' scritto"
    t = S.testo("MINI FOLLOW UP", {}, {}, "https://cal", finto)
    assert "https://cal" in t and "[" not in t and "{{" not in t, "segnaposto rimasto nel testo"
    assert S.testo("RICONTATTO OOO", {}, {}, "x", finto) is None, "senza template il codice non deve scrivere"
    ooo = finto + "## RICONTATTO DOPO OUT OF OFFICE (29/9)\n```\nSalve [Nome],\n\nera in ferie. Le propongo {{GIORNO}}: {{CALENDARIO}}\n```\n"
    assert S.testo("RICONTATTO OOO", {}, {}, "https://cal", ooo) is None, "senza giorno dal calendario il codice non deve inventarlo"
    t = S.testo("RICONTATTO OOO", {}, {}, "https://cal", ooo, giorno="giovedì 1 ottobre alle 14:30")
    assert "giovedì 1 ottobre" in t and "{{" not in t
    import datetime as _d
    assert S.giorno_passato("giovedì 1 ottobre alle 14:30", _d.date(2026, 10, 2)), "un giorno passato deve fermare la mail"
    assert not S.giorno_passato("giovedì 1 ottobre alle 14:30", _d.date(2026, 9, 29))
    assert S.testo("RINVIO SCADUTO", {"analysis_sent": True}, {}, "x", finto) is None, "il rinvio a chi ha l'analisi va riscritto: non dal codice"
    # una verita' sola: le date le scrive followup.py, lo schermo le legge soltanto
    qui = pathlib.Path(__file__).resolve().parent
    assert "seguiti_calendario" in qui.joinpath("followup.py").read_text(encoding="utf-8")
    ui = qui.parents[0].joinpath("src", "components", "SeguitiInArrivo.tsx").read_text(encoding="utf-8")
    assert "from('seguiti_calendario')" in ui and "analysis_sent_at" not in ui, "la sezione rifa' i conti invece di leggere il calendario"
    # e il cancello dei seguiti non si fida del modello: riscrive e confronta
    pr = qui.joinpath("prima_risposta.py").read_text(encoding="utf-8")
    assert "rilettura_seguito" in pr and "testo_dal_codice" in pr


@prova("mai mille righe scambiate per tutte: chi vuole tutto usa sb_tutte, che legge a pagine")
def _():
    import glob
    import re as _re
    import stanza
    # 29/9: il database restituisce al massimo mille righe per richiesta. Calendario e
    # Stripe chiedevano «limit=10000» e cercavano fra mille aziende su 13.230.
    colpevoli = []
    qui = os.path.dirname(os.path.abspath(__file__))
    for f in glob.glob(os.path.join(qui, "*.py")) + glob.glob(os.path.join(qui, "strumenti", "*.py")):
        if f.endswith(("test_invarianti.py", "stanza.py")):
            continue
        testo = open(f, encoding="utf-8").read()
        for m in _re.finditer(r'sb\("GET",[^\n]*?limit=(\d+)', testo):
            if int(m.group(1)) > 1000:
                colpevoli.append(f"{os.path.basename(f)}: limit={m.group(1)}")
    assert not colpevoli, "letture oltre il tetto di mille righe senza sb_tutte: " + ", ".join(colpevoli[:5])
    # e sb_tutte legge davvero tutto, a pagine
    vero = stanza.sb
    pagine = {0: [{"id": i} for i in range(1000)], 1000: [{"id": i} for i in range(1000, 1500)]}
    visti = []
    def finto(metodo, percorso, *a, **k):
        visti.append(percorso)
        return pagine.get(int(_re.search(r"offset=(\d+)", percorso).group(1)), [])
    try:
        stanza.sb = finto
        assert len(stanza.sb_tutte("/rest/v1/prospects?select=id&limit=10000")) == 1500, "sb_tutte si ferma alla prima pagina"
        assert all("order=" in v for v in visti), "a pagine serve un ordine, sennò righe doppie o perse"
    finally:
        stanza.sb = vero


@prova("il calendario non aggancia un'azienda per una parola qualunque del titolo")
def _():
    import calendario as C
    # 29/9: «visita medica» → Dental Medica, «market fit» → Loprin Market Plans,
    # «(Enrico Filippini)», un colloquio, → Filippini Business Consulting, soppressa.
    aziende = [("d", C._parole("Dental Medica"), C._marchio("Dental Medica")),
               ("l", C._parole("Loprin - Market Plans"), C._marchio("Loprin - Market Plans")),
               ("f", C._parole("Filippini Business Consulting"), C._marchio("Filippini Business Consulting")),
               ("k", C._parole("Klavzar Fisioterapia"), C._marchio("Klavzar Fisioterapia"))]
    conta = {}
    for _, parole, _m in aziende:
        for w in parole:
            conta[w] = conta.get(w, 0) + 1
    P = {"email": {}, "dominio": {}, "aziende": aziende, "conta": conta, "nomi": {"enrico", "filippini"}}
    for titolo in ("Appuntamento alle 16 per visita medica", "Follow up lead in Google market fit",
                   "StudioGalilei - Chiamata conoscitiva (Enrico Filippini)"):
        assert C.riconosci({"titolo": titolo, "invitati": []}, P) == (None, None), f"aggancio sbagliato da «{titolo}»"
    assert C.riconosci({"titolo": "Call tecnica StudioGalilei - Klavzar", "invitati": []}, P)[0] == "k", "il marchio nel titolo non basta piu'"
    # e la coda non tiene per sempre chi non si ricontatta
    b = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "bozze.py"), encoding="utf-8").read()
    assert "fuori_coda" in b and "esito_coda(p, motivo)" in b, "chi e' perso o cliente resta in coda per sempre"


@prova("i soldi li vedono solo Dre e Giacomo: niente soldi dove li legge la squadra")
def _():
    import pathlib
    from stanza import con_soldi
    # 29/9, Dre: «niente soldi per gli altri, solo io e Giacomo». Il database li tiene
    # in cassaforte (schema_v67); qui le regole del codice che non devono cedere.
    qui = pathlib.Path(__file__).resolve().parent
    prep = qui.joinpath("preparo.py").read_text(encoding="utf-8")
    assert "esterni or not ev" in prep, "la preparazione puo' finire nell'evento di Google che vede anche il cliente"
    assert "PREZZO SUGGERITO" not in prep and "importo,mensile" not in prep and "stato,valore" not in prep, \
        "la preparazione della call (che la squadra vede nell'evento) contiene di nuovo soldi"
    sch = qui.parents[0].joinpath("src", "components", "Scheda.tsx").read_text(encoding="utf-8")
    assert "{riservato && p.fuori && !ePerso(p) && !soppresso && (\n              <PrezzoSuggerito" in sch, "il prezzo suggerito si vede anche a chi non e' Dre"
    # 29/9, IL RISERVATO: la preparazione e il prezzo solo a Dre, mai nell'evento di Google
    import re as _re
    assert not _re.search(r"^\s+nell_evento\(", prep, _re.M) and "/rest/v1/preparazioni" in prep, "la preparazione esce dal riservato di Dre"
    assert "{riservato && prepAperta && (" in sch and "{riservato && (\n                <button" in sch, "la preparazione si vede a chi non e' Dre"
    pv = qui.parents[0].joinpath("src", "components", "Preventivi.tsx").read_text(encoding="utf-8")
    assert "{riservato && <Prezzo />}" in pv, "il calcolatore dei prezzi si vede a chi non e' Dre"
    st = qui.parents[0].joinpath("src", "lib", "stato.ts").read_text(encoding="utf-8")
    assert "x.soldi === false" in st, "a chi non vede i soldi la pipeline direbbe «canone da mettere»"
    # con_soldi rimette i soldi solo se la cassaforte li ha dati
    p = {"id": "a", "canone": None, "enriched": {"google_fit": 1}}
    assert con_soldi(p, {}) == p
    q = con_soldi(p, {"a": {"canone": 900, "prezzo": {"punto": 1500}}})
    assert q["canone"] == 900 and q["enriched"]["prezzo"] == {"punto": 1500} and q["enriched"]["google_fit"] == 1


@prova("l'attesa si chiude quando non c'e' nessuno a cui rispondere, ma mai toccando soppressi e fuori target")
def _():
    import pathlib
    b = pathlib.Path(__file__).resolve().parent.joinpath("bozze.py").read_text(encoding="utf-8")
    # 29/9: caselle ticket e no senza gigante buono restavano «in attesa» per sempre
    assert "chiudi_attese_senza_risposta()" in b and "mai_gb(p," in b, "le attese senza risposta non si chiudono piu'"
    # e il Revisore ha deciso: soppressi, fuori target e nervosi non si toccano nemmeno cosi'
    blocco = b[b.index("def chiudi_attese_senza_risposta"):b.index("def main")]
    assert 'if c in ("soppresso", "fuori_target", "nervoso"):\n            continue' in blocco, "l'attesa si chiude anche a soppressi e fuori target"


@prova("le risposte col template di Dre: parola per parola, solo attacco, periodo, nome e giorno cambiano")
def _():
    import seguiti as S
    finto = ("## INTERESSATO (3/7)\n```\nSalve,\nVa bene perfetto, vi inoltro qui l'analisi.\nLe propongo domani alle 15:30, oppure un altro giorno nel caso domani non abbia disponibilità.\n"
             "📅 Calendario: https://calendar.app.google/VECCHIO\nA presto,\n```\n"
             "## SENTIAMOCI PIÙ AVANTI\n```\nSalve,\n\nper me va bene, ci possiamo risentire a ottobre/novembre.\n```\n")
    t = S.risposta("INT-01", {}, {"ultima_nostra": "Buongiorno Maura, le avevo scritto"}, "https://cal/NUOVO",
                   giorno="giovedì 1 ottobre alle 14:30", attacco="Grazie per la conferma", testo_file=finto)
    assert t.startswith("Salve Maura,\nGrazie per la conferma, vi inoltro qui l'analisi."), t[:80]
    assert "Le propongo una breve videochiamata conoscitiva giovedì 1 ottobre alle 14:30" in t and "nel caso quel giorno" in t and "https://cal/NUOVO" in t and "VECCHIO" not in t
    # l'attacco del modello non puo' promettere niente: se ci prova, resta quello di Dre
    t = S.risposta("INT-01", {}, {}, "x", giorno="g", attacco="Le allego l'analisi con 30% di sconto", testo_file=finto)
    assert "Va bene perfetto, vi inoltro" in t
    assert S.risposta("INT-01", {}, {}, "x", giorno=None, testo_file=finto) is None, "senza giorno dal calendario il codice non inventa"
    assert S.risposta("INT-05", {}, {}, "x", periodo=None, testo_file=finto) is None, "un rinvio senza periodo lo scrive una persona"
    assert "risentire a gennaio" in S.risposta("INT-05", {}, {}, "x", periodo="a gennaio", testo_file=finto)
    assert S.risposta("INT-12", {}, {}, "x", testo_file=finto) is None, "un'obiezione non ha template: niente testo dal codice"


@prova("la nostra mail citata non e' mai testo suo, anche senza a capo e senza «il giorno»")
def _():
    import lettura as L
    import analisi_auto as A
    # 29/9: 95 risposte su 688 si portavano dietro la nostra mail («Il 16/07/2026 16:37, X ha scritto:»)
    no = "Non siamo interessati, grazie Il 03/08/2026 10:12, Mario Bianchi ha scritto: le mando l'analisi della vostra zona?"
    assert L.solo_suo(no) == "Non siamo interessati, grazie", L.solo_suo(no)
    assert not A.CHIEDE_ANALISI.search(L.solo_suo(no)), "una nostra frase citata fa passare un no per un si'"
    assert L.solo_suo("ok grazie On Wed, Jul 15, 2026 at 4:37 PM Mario <m@x.it> wrote: hello") == "ok grazie"
    assert L.solo_suo("Il 2026-07-07 10:22 Mario Bianchi ha scritto: > abbiamo dato un'occhiata") == "", "chi non scrive niente non chiede niente"
    # senza data non e' una citazione: e' lui che racconta
    assert L.solo_suo("Va bene alle 16:30, il collega ha scritto: ok", con_firma=True).endswith("ha scritto: ok")


@prova("il calendario riconosce chi prenota con la mail personale, ma solo nome e cognome in UNA azienda")
def _():
    import calendario as C
    # 30/9: una conoscitiva prenotata con una Gmail non si agganciava a nessuno
    P = {"email": {}, "dominio": {}, "aziende": [], "conta": {}, "nomi": set(),
         "cerca_nome": lambda n: {"Mario Bianchi": {"az1"}, "Luca Verdi": {"az1", "az2"}}.get(n, set())}
    e = {"titolo": "StudioGalilei - Chiamata conoscitiva (Mario Bianchi)", "invitati": ["mario.b1980@gmail.com"],
         "descrizione": "<b>Prenotato da</b>\nMario Bianchi\nmario.b1980@gmail.com"}
    assert C.prenotato_da(e) == "Mario Bianchi" and C.riconosci(e, P) == ("az1", "nome nelle mail")
    assert C.riconosci({**e, "titolo": "Chiamata conoscitiva (Luca Verdi)", "descrizione": ""}, P) == (None, None), "due aziende: non si sceglie a caso"
    assert C.riconosci({**e, "titolo": "Pranzo (Mario Bianchi)", "descrizione": ""}, P) == (None, None), "un impegno che non e' una call non si aggancia"
    assert C.riconosci({**e, "titolo": "Chiamata conoscitiva (Mario)", "descrizione": ""}, P) == (None, None), "il solo nome non basta"


@prova("fermo da e l'avanzamento: una regola sola, in regole.ts, per ogni schermata")
def _():
    import pathlib
    src = pathlib.Path(__file__).resolve().parent.parent / "src"
    # 30/9: quattro orologi diversi per «fermo da», e dalla scheda non si entrava in pipeline
    for f in ("components/Scheda.tsx", "components/Radar.tsx", "components/Analytics.tsx"):
        assert "ultimoMovimento(" in (src / f).read_text(encoding="utf-8"), f"{f} conta il fermo a modo suo"
    for f in ("components/Scheda.tsx", "components/Lista.tsx"):
        assert "entraInConoscitiva()" in (src / f).read_text(encoding="utf-8"), f"{f} fa entrare in pipeline con una regola sua"


@prova("le schermate nuove muovono le aziende solo con le regole del percorso")
def _():
    import pathlib, re
    d = pathlib.Path(__file__).resolve().parent.parent / "src" / "components" / "aziende"
    # 30/9: la regola per spostare un lead stava dentro la bacheca, e la scheda ne aveva mezza copia.
    # Nelle schermate nuove nessuno scrive stage, pipeline_stage o fuori a mano: passa tutto da percorso.mossa()
    for f in d.glob("*.tsx"):
        t = f.read_text(encoding="utf-8")
        assert not re.search(r"(stage|pipeline_stage|fuori)\s*:", t), f"{f.name} scrive la fase a mano"
    assert "mossa(" in (d / "Aziende.tsx").read_text(encoding="utf-8")
    sql = (pathlib.Path(__file__).resolve().parent.parent / "supabase" / "schema_v72.sql").read_text(encoding="utf-8")
    assert "create or replace function tappa_di" in sql and "trg_tappa" in sql, "la tappa unica non la tiene piu' il database"


@prova("il fit non boccia con i volumi di un altro settore, e il rosso non vince su 30+ recensioni")
def _():
    import googlefit as G
    # 30/9, Denis Tende: tende da sole lette come «verande», 10 ricerche/mese a Treviso, verdetto NO
    # con 80 recensioni a 4,9. Il settore solo «vicino» non porta volumi; i dati che si
    # contraddicono non bocciano, chiedono una verifica.
    c = {"settore": "verande", "settore_uguale": False, "ticket_max": 9000, "cosa_fa": "tende da sole"}
    assert G._zona_sul_raggio(c, {}) is None, "un settore solo somigliante porta ancora i volumi di altri"
    rosso = {"verdetto": "ROSSO", "domanda_mese": 10, "cpc": 0.5}
    v, motivo = G.verdetto({"settore": "verande", "ticket_max": 9000}, rosso, {"recensioni": 80, "voto": 4.9})
    assert v != "NO", f"80 recensioni in provincia «rossa» bocciate: {motivo}"
    v, _m = G.verdetto({"settore": "verande", "ticket_max": 9000}, rosso, {"recensioni": 8, "voto": 4.9})
    assert v == "NO", "senza recensioni che contraddicono, il rosso deve ancora fermare"


@prova("«finita nello spam» e' un si' che ci avvisa, non un'accusa")
def _():
    import analisi_auto as A
    # 1/10: Nigris e UG Rent, analisi promesse e bloccate perche' «spam» stava nel racconto
    for si in ("l'e-mail era finita nello spam, attendiamo le informazioni",
               "la sua mail era finita nella cartella spam, attendiamo con piacere"):
        assert not A.NON_TOCCARE.search(si), f"un si' col filtro spam viene ancora bloccato: {si[:40]}"
    for no in ("smettetela con questo spam", "questo è spam, vi segnalo al garante"):
        assert A.NON_TOCCARE.search(no), f"un'accusa di spam non frena piu': {no[:40]}"


@prova("l'automatico e' solo la consegna della prima risposta con l'analisi, nient'altro")
def _():
    import pathlib
    import prima_risposta as PR
    # 1/10, Dre: «questo intero sistema e' solo per la consegna delle analisi: la prima
    # risposta, con l'analisi e la presentazione. Le conversazioni me le gestisco io».
    # INT-GB aggiunto il 2/10 e TOLTO il 5/10 su ordine di Dre («non inviamo piu' le
    # analisi ai no: sta spendendo tanti crediti anche per chi ha detto no»)
    # INT-02 TOLTO il 12/10 su ordine di Dre: «quando chiedono di sentirsi la palla passa a me»
    assert PR.INTENTI_OK == ("INT-01", "INT-03", "INT-23"), "la lista degli intenti automatici e' cambiata senza Dre"
    t = pathlib.Path(PR.__file__).read_text(encoding="utf-8")
    assert "ALLEGA_ANALISI.search(testo)" in t, "l'automatico puo' partire senza consegnare l'analisi"
    assert "non e' una prima risposta" in t, "l'automatico non controlla piu' che sia la PRIMA risposta"
    m = pathlib.Path(PR.__file__).parent.joinpath("manda.py").read_text(encoding="utf-8")
    assert "allega_presentazione" in m and "sg-presentazione" in m, "la presentazione non viaggia piu' con la prima risposta"


@prova("al messaggero non si propone la call: il meeting e' con la persona giusta")
def _():
    import bozze as B
    # 1/10, Daniel/EnergetiKa: chiedevamo l'email di Manuel E proponevamo la call a Daniel.
    # Dre: «a noi interessa il meeting con la persona; al messaggero si chiede il favore».
    male = ("Mi lascia l'indirizzo email di Manuel? Intanto le lascio l'analisi. "
            "Le propongo una breve chiamata conoscitiva martedì alle 14:30: https://calendar.app.google/x")
    assert any("persona giusta" in e for e in B.cancello(male)), "la call al messaggero passa ancora"
    bene = "Mi lascia l'indirizzo email di Manuel? Intanto le lascio l'analisi. Appena ho il contatto scrivo direttamente a lui."
    assert B.cancello(bene) == [], B.cancello(bene)
    # in copia la persona giusta c'e': la call si puo' proporre
    cc = "Metto in copia manuel@azienda.it così proseguiamo lì. Le propongo martedì alle 14:30: https://calendar.app.google/x"
    assert B.cancello(cc) == [], B.cancello(cc)
    # 14/10, Urbis: scrivere all'indirizzo giusto e dirlo non e' chiedere il contatto di un altro
    giusto = ("Vi scrivo qui perché mi è stato indicato come l'indirizzo di riferimento per Urbis. "
              "Vi propongo una breve videochiamata conoscitiva giovedì alle 16: https://calendar.app.google/x")
    assert not any("persona giusta" in e for e in B.cancello(giusto)), B.cancello(giusto)
    chiesta = "Potrebbe girarmi l'email di Manuel? Le propongo una breve videochiamata conoscitiva martedì: https://calendar.app.google/x"
    assert any("persona giusta" in e for e in B.cancello(chiesta)), "una richiesta col «potrebbe» passa"


@prova("il ritmo umano ha i denti: punto-spazio-e-continua tre volte blocca, l'a capo no")
def _():
    import bozze as B
    import seguiti as S
    # 1/10, Dre: «punto spazio e continua fa capire che e' una scrittura delle AI»
    ai = ("Grazie mille. Le mando il documento. Allego anche la presentazione. "
          "Le propongo martedì alle 14:30: https://calendar.app.google/x")
    assert any("punto-spazio" in e for e in B.cancello(ai)), "lo stile AI passa ancora"
    umano = ("Grazie mille, le mando il documento,\ne allego anche la presentazione.\n"
             "Le propongo martedì alle 14:30: https://calendar.app.google/x")
    assert B.cancello(umano) == [], B.cancello(umano)
    # i template di Dre vanno a capo dopo il punto: devono passare cosi' come sono
    # (template finto con la stessa struttura: gli invarianti non toccano la rete)
    finto = ("## INTERESSATO (3/7)\n```\nSalve,\nVa bene perfetto, vi inoltro qui l'analisi che abbiamo fatto.\n"
             "Questo è un modo per presentarci a voi portando già spunti concreti.\n"
             "Ci occupiamo di marketing e intelligenza artificiale.\nAbbiamo un vasto range di servizi (le allego anche un doc di presentazione).\n\n"
             "L'analisi però è centrata principalmente sulla comunicazione su Google.\n"
             "Poi avremmo pronta anche una proposta con garanzia da farvi, ma intanto mi farebbe piacere confrontarmi con lei.\n"
             "Le propongo domani alle 15:30, oppure un altro giorno nel caso domani non abbia disponibilità.\n"
             "📅 Calendario: https://calendar.app.google/V\nA presto,\n```\n")
    t = S.risposta("INT-01", {}, {}, "https://calendar.app.google/x", giorno="martedì 6 ottobre alle 14:30", testo_file=finto, garanzia=True)
    assert t and B.cancello(t) == [], f"il template verbatim di Dre non passa il suo stesso ritmo: {t and B.cancello(t)}"


@prova("i si' hanno la precedenza: il gigante buono non parte se restano si', e ha finestra larga")
def _():
    import prima_risposta as PR
    import datetime
    # 5/10, Dre: «i si' subito, i no solo se non ci sono si' non ancora inviati; e i no
    # possono partire anche fuori orario, basta non dopo le 21:30»
    lun = datetime.datetime(2026, 10, 6, tzinfo=PR.ROMA)
    sab = datetime.datetime(2026, 10, 10, tzinfo=PR.ROMA)
    assert PR.finestra(lun.replace(hour=10)) and PR.finestra(lun.replace(hour=20)), "la finestra dei si' e' 8-21 (9/10 sera)"
    assert PR.finestra(sab.replace(hour=10)), "dal 9/10 i si' partono anche di sabato"
    assert not PR.finestra(lun.replace(hour=22)), "un si' non parte dopo le 21"
    assert PR.finestra(lun.replace(hour=20), "INT-GB") and PR.finestra(sab.replace(hour=10), "INT-GB"), "i no non hanno la finestra larga"
    assert not PR.finestra(lun.replace(hour=22), "INT-GB"), "un no parte dopo le 21:30"


@prova("un no concorde delle due teste aggiorna la classe da solo, un no dubbioso resta a Dre")
def _():
    import lettura as L
    # 5/10, casainromagna: la classe diceva positivo, la mail un no chiaro. Concordi -> si risolve.
    assert L.leggi.__doc__ is not None  # esiste
    src = open(L.__file__, encoding="utf-8").read()
    assert "detto_no_sicuro" in src, "manca il no concorde in lettura"
    import re
    assert re.search(r'detto_no_sicuro.*\n.*not lettore\.get\("dubbio"\)', src) or "not lettore.get(\"dubbio\")" in src, "il no concorde non esige il modello sicuro"
    srcb = open(L.__file__.replace("lettura", "bozze"), encoding="utf-8").read()
    assert "detto_no_sicuro" in srcb and "classificazione\": \"negativo" in srcb, "bozze non riclassifica il no concorde"


@prova("a chi dice no, mai una data: porta aperta e' consegnare, non riproporre")
def _():
    import bozze as B
    # 1/10, caso Matteo: «inviamo l'analisi ma non proponiamo l'appuntamento con una
    # data. Al massimo lasciamo il calendario li' sotto». La seconda testa lo aveva
    # gia' fiutato da sola; ora e' una regola col suo nome.
    con_data = "Capisco, le lascio l'analisi.\nSe in futuro le va, le propongo martedì 6 ottobre alle 14:30: https://calendar.app.google/x"
    assert any("ha detto no" in e for e in B.cancello(con_data, detto_no=True)), "una data dopo un no passa ancora"
    assert B.cancello(con_data, detto_no=False) == [], "la stessa frase a chi NON ha detto no deve passare"
    senza = "Capisco, grazie del riscontro,\ne le lascio l'analisi in allegato.\nSe in futuro vorrà più clienti, o AI e software su misura, noi ci siamo: qui sotto le lascio il calendario.\nhttps://calendar.app.google/x"
    assert B.cancello(senza, detto_no=True) == [], B.cancello(senza, detto_no=True)


@prova("la sentinella vede e dice, non opera")
def _():
    import pathlib
    t = pathlib.Path(__file__).resolve().parent.joinpath("sentinella.py").read_text(encoding="utf-8")
    # 1/10: chi sorveglia non tocca i dati, se no un bug del guardiano diventa un guaio doppio
    for vietato in ('"PATCH"', '"POST"', '"DELETE"', "proponi("):
        assert vietato not in t, f"la sentinella opera ({vietato}): deve solo vedere e avvisare"
    assert "di_clara(" in t, "la sentinella non avvisa piu' nessuno"
    w = pathlib.Path(__file__).resolve().parent.parent.joinpath(".github", "workflows", "sentinella.yml").read_text(encoding="utf-8")
    assert "direttore.yml" in w and "cancel" in w, "la sentinella non rianima piu' il direttore bloccato"


@prova("il lampo accorcia il tempo, non le regole: orchestra e basta, non scrive mai")
def _():
    import pathlib
    t = pathlib.Path(__file__).resolve().parent.joinpath("lampo.py").read_text(encoding="utf-8")
    # 1/10: la catena veloce chiama i pezzi di sempre; se scrivesse in proprio,
    # avremmo una seconda strada senza cancelli accanto a quella controllata
    for vietato in ("proponi(", '"PATCH"', '"POST"', "sl(", "reply-email-thread"):
        assert vietato not in t, f"lampo.py fa da solo ({vietato}): deve solo chiamare i pezzi coi loro cancelli"
    for pezzo in ("googlefit.py", "analisi_auto.py", "bozze.py", "prima_risposta.py", "manda.py"):
        assert pezzo in t, f"la catena ha perso un pezzo: {pezzo}"


@prova("leggono in due: un freno basta da solo, un via mai da un dubbio")
def _():
    import lettura as L
    # 30/9, verdetto del metro: il modello entra ai quattro posti delle regex
    assert L.frena(True, None, ("no",)), "la regex da sola non frena piu'"
    assert L.frena(False, {"etichetta": "non_scrivere", "dubbio": True}, ("non_scrivere",)), "il modello in dubbio non frena: un dubbio deve poter fermare"
    assert not L.frena(False, None, ("no",)), "senza nessuna opinione si frena a caso"
    assert L.si_acceso(True, None), "la regex di sempre non accende piu' il si'"
    assert L.si_acceso(False, {"etichetta": "si", "dubbio": False})
    assert not L.si_acceso(False, {"etichetta": "si", "dubbio": True}), "un dubbio ha acceso un si'"
    assert not L.si_acceso(False, None), "il si' si accende senza nessuno che lo dica"
    assert not L.si_acceso(True, {"etichetta": "no", "dubbio": False}), "il modello dice no e il si' parte lo stesso"


@prova("la biblioteca dei casi: esempi di Dre nelle bozze, e senza rete non rompe niente")
def _():
    import casi
    import pathlib
    # 30/9, Dre: «ogni caso e' unico; un'intelligenza che migliora sui casi unici»
    casi._biblioteca = [{"testo": "non siamo interessati, abbiamo gia' un'agenzia", "etichetta": "no",
                         "nota": "analisi comunque e porta aperta", "parole": casi._parole("non siamo interessati, abbiamo gia' un'agenzia")}]
    blocco = casi.simili("grazie ma non siamo interessati, ci segue gia' un'agenzia")
    assert "porta aperta" in blocco and "GIUDICATI DA DRE" in blocco
    assert casi.simili("tutt'altra cosa qui dentro oggi") == "", "un caso che non somiglia entra lo stesso nel prompt"
    casi._biblioteca = None
    b = pathlib.Path(__file__).resolve().parent.joinpath("bozze.py").read_text(encoding="utf-8")
    assert b.count("casi.simili(") >= 2, "le bozze non pescano piu' i casi di Dre"


@prova("le due regole del dare-avere: mai l'analisi «insieme» in call, mai chiudere a volo")
def _():
    import bozze as B
    # 30/9, Dre coi perche': se promettiamo di spiegarla, in call si vende e la vendita
    # si rovina; chi resta «a disposizione» non torna, e servono pipeline di recupero.
    cal = " Le propongo giovedì alle 15: https://calendar.app.google/x"
    assert any("conoscitiva" in e for e in B.cancello("Vediamo insieme l'analisi in call." + cal))
    assert any("disposizione" in e for e in B.cancello("Le allego l'analisi. Resto a disposizione." + cal))
    assert any("a volo" in e for e in B.cancello("Le allego l'analisi.\nBuona giornata."))
    assert B.cancello("Le inoltro l'analisi." + cal) == []
    assert B.cancello("Perfetto, confermo venerdì 2 ottobre alle 15:00.") == []
    assert B.cancello("Le inoltro l'analisi. Le scrivo io martedì 13 ottobre per fissare.") == []


@prova("INT-23 e il cancello (20/10 sera): senza call passa, con la call dentro no, e a chi ha chiuso non si risponde")
def _():
    import bozze as B
    import prima_risposta as PR
    # Regola contro regola: INT-23 («mi mandi il materiale, niente call», Dre 1/10) e' fra gli intenti
    # automatici, ma cadeva SEMPRE al cancello «chiusa a volo» del 30/9 (a chi chiude non si propone la
    # call). Il cancello ora, per INT-23, verifica che la call NON ci sia e che l'analisi ci sia: non
    # che la persona abbia lasciato un prossimo punto di contatto, perche' l'ha scelto lei (si fa viva).
    int23 = ("Salve,\nVa bene perfetto, vi inoltro qui l'analisi che abbiamo fatto sulla vostra azienda.\n"
             "Le allego anche una breve presentazione dei nostri servizi.\n\n"
             "L'analisi è centrata sulla comunicazione su Google.\n"
             "Se dopo averla letta volesse approfondire, resto a disposizione.\n\nA presto,")
    assert B.cancello(int23, intento="INT-23") == [], B.cancello(int23, intento="INT-23")
    con_call = int23.replace("resto a disposizione", "le propongo una breve videochiamata conoscitiva giovedì alle 15: https://calendar.app.google/x")
    assert any("propone la call" in e for e in B.cancello(con_call, intento="INT-23")), "una INT-23 con la call dentro passa ancora"
    assert any("senza l'analisi" in e for e in B.cancello("Salve,\ngrazie, resto a disposizione.\nA presto,", intento="INT-23")), \
        "una INT-23 che non dice di allegare l'analisi passa: il materiale e' l'unica cosa che manda"
    # per tutti gli altri le due regole del 30/9 restano com'erano
    assert any("a volo" in e for e in B.cancello(int23)) and any("disposizione" in e for e in B.cancello(int23))
    assert any("a volo" in e for e in B.cancello(int23, intento="INT-01"))
    # il postino e approva passano l'intento al cancello: lo stesso testo passa da manda.controlla
    import manda
    assert manda.controlla(int23, None, intento="INT-23") == [], manda.controlla(int23, None, intento="INT-23")
    assert any("a volo" in e for e in manda.controlla(int23, None, intento="INT-01"))
    # a chi ha chiuso non si risponde in automatico, ne' INT-01 ne' INT-23: il no lo dice la lettura
    for intento in ("INT-01", "INT-23"):
        pr = {"tipo": "risposta", "titolo": "Bozza per X", "azione": {"bozza": int23, "intento": intento,
                                                                       "lettura": {"coerenza": "COERENTE", "detto_no": True}}}
        assert "ha detto no" in PR.perche_no(pr, None), f"{intento} a chi ha chiuso passerebbe il cancello della prima risposta"
    # una regex sola per «l'analisi e' allegata»: quella del cancello
    assert PR.ALLEGA_ANALISI is B.ALLEGA_ANALISI


@prova("la prima risposta segue il lettore: C04 (mandatela, vi cerchiamo noi) e' INT-23 senza call, un caldo e' INT-01 (20/10 sera)")
def _():
    import bozze as B
    # il caso di stasera: «inviateci pure il materiale e se dovessimo valutare vi ricontatteremo» (C04, non
    # caldo), il modello diceva INT-01 e proponeva uno slot a chi ha detto che si fa vivo lui
    p = {"last_reply_at": "2026-10-09T14:33:00", "enriched": {"lettore": {"fonte": "lettore", "classe": "positivo", "caso": "C04",
                                                                           "caldo": False, "risposta_il": "2026-10-09T14:33:00"}}}
    b = B.intento_col_lettore({"intento": "INT-01", "template": "INT-01", "bozza": "x", "nota": ""}, p)
    assert b["intento"] == "INT-23" and b["template"] == "INT-23", b
    # un caldo resta INT-01 anche se il modello diceva INT-23 (regola del 20/10 sera, caso C05)
    caldo = {**p, "enriched": {"lettore": {**p["enriched"]["lettore"], "caso": "C05", "caldo": True}}}
    assert B.intento_col_lettore({"intento": "INT-23", "template": "INT-23", "bozza": "x", "nota": ""}, caldo)["intento"] == "INT-01"
    # C01 («si', me la mandi») non si tocca: INT-01 resta INT-01; e senza una lettura valida non si cambia niente
    c01 = {**p, "enriched": {"lettore": {**p["enriched"]["lettore"], "caso": "C01"}}}
    assert B.intento_col_lettore({"intento": "INT-01", "template": "INT-01", "bozza": "x", "nota": ""}, c01)["intento"] == "INT-01"
    vecchia = {**p, "last_reply_at": "2026-10-12T09:00:00"}       # la lettura e' di una mail precedente
    assert B.intento_col_lettore({"intento": "INT-01", "template": "INT-01", "bozza": "x", "nota": ""}, vecchia)["intento"] == "INT-01"
    # nei gruppi (ricontatti) non si tocca niente
    assert B.intento_col_lettore({"intento": "INT-01", "template": "INT-01", "bozza": "x", "nota": ""}, p, gruppo="RIPRESA")["intento"] == "INT-01"


@prova("la garanzia solo col punteggio: mai promessa a chi non regge, aggiunta dove regge")
def _():
    import garanzia as G
    import seguiti as S
    # 1/10, Dre: «uno score fatto bene; se non siamo sicurissimi non la scriviamo, uno se lo ricorda»
    forte = {"enriched": {"google_fit": {"verdetto": "SI", "zona": {"verdetto": "VERDE", "cpc": 0.5},
                                          "recensioni": {"recensioni": 40}, "ticket_max": 5000}}}
    debole = {"enriched": {"google_fit": {"verdetto": "PARZIALE", "zona": None, "recensioni": {"recensioni": 3}, "ticket_max": 200}}}
    assert G.promettibile(forte)[0] and not G.promettibile(debole)[0]
    assert not G.promettibile({"enriched": {"google_fit": {"verdetto": "SI", "settore_uguale": False, "zona": {"verdetto": "VERDE"}}}})[0], "volumi di un altro settore e promettiamo lo stesso"
    assert not G.promettibile({})[0], "senza fit si promette a scatola chiusa"
    finto = ("## INTERESSATO (3/7)\n```\nSalve,\nVa bene perfetto, vi inoltro qui l'analisi.\n"
             "Poi avremmo pronta anche una proposta con garanzia da farvi, ma intanto mi farebbe piacere confrontarmi con lei.\n"
             "Le propongo domani alle 15:30, oppure un altro giorno nel caso domani non abbia disponibilità.\n"
             "📅 Calendario: https://calendar.app.google/V\nA presto,\n```\n"
             "## CHI SEI? (3/7)\n```\nSalve,\nmolto piacere.\nMi farebbe piacere confrontarmi con lei.\n📅 https://calendar.app.google/V\n```\n")
    senza = S.risposta("INT-01", {}, {}, "https://cal/N", giorno="g", testo_file=finto, garanzia=False)
    assert "garanzia" not in senza and "Mi farebbe piacere confrontarmi" in senza, "la frase resta anche quando lo score dice no"
    con = S.risposta("INT-03", {}, {}, "https://cal/N", giorno="g", testo_file=finto, garanzia=True)
    assert "proposta con garanzia" in con, "dove lo score passa, la linea di Dre ci sta (1/10)"


@prova("il lettore unico: un dubbio puo' solo fermare, mai sbloccare")
def _():
    import cervello as C
    base = {"autorisposta": 0.0, "detto_no": 0.0, "non_contattare": 0.0, "vuole_analisi": 0.0, "vuole_call": 0.0, "rinvio": 0.0}
    assert C.decisioni(None)["blocca"], "senza lettura non si procede"
    d = C.decisioni({**base, "vuole_analisi": 1.0, "non_contattare": 0.2})
    assert d["etichetta"] == "non_scrivere" and d["blocca"], "un 20% di «non scrivetemi» ferma anche un sì pieno"
    d = C.decisioni({**base, "vuole_analisi": 0.9, "detto_no": 0.3})
    assert d["etichetta"] == "si" and d["dubbio"], "un sì con un no in vista non decide da solo"
    assert not C.decisioni({**base, "vuole_call": 0.95})["dubbio"]


@prova("il metro: Dre etichetta senza vedere cosa ne pensa il modello")
def _():
    import pathlib
    import re as _re
    m = pathlib.Path(__file__).resolve().parent.parent.joinpath("src", "components", "Metro.tsx").read_text(encoding="utf-8")
    # il controllo vero: nessuna SELECT carica la proposta (nominarla nei commenti e' lecito)
    for sel in _re.findall(r"select\('([^']*)'\)", m):
        assert "proposta" not in sel, f"la pagina del metro legge la proposta del sistema: select('{sel}')"


@prova("i silenzi: senza un follow-up partito nessuno finisce nei Persi")
def _():
    import silenzi as S
    import datetime as _dt
    oggi = _dt.date.today()
    vecchia = (oggi - _dt.timedelta(days=40)).isoformat()
    p = {"id": "x", "company": "Prova", "analysis_sent_at": vecchia, "last_reply_at": None,
         "next_action_date": None, "ooo_until": None}
    scritti = []
    vero_sb = S.sb
    try:
        # analisi di 40 giorni fa, nessun follow-up partito: resta viva
        S.sb = lambda m, path, corpo=None, h=None: ([p] if path.startswith("/rest/v1/prospects?select") else
                                                      (scritti.append(corpo) if m == "PATCH" else []))
        S.main()
        assert not scritti, "un lead senza follow-up partito e' finito nei Persi"
        # follow-up partito 20 giorni fa, silenzio da allora: esce
        fu = (oggi - _dt.timedelta(days=20)).isoformat()
        S.sb = lambda m, path, corpo=None, h=None: ([p] if path.startswith("/rest/v1/prospects?select") else
                                                      [{"at": fu + "T10:00:00"}] if "interactions" in path else
                                                      (scritti.append(corpo) if m == "PATCH" else []))
        S.main()
        assert scritti and scritti[0]["stage"] == "perso", "dopo il follow-up e 10 giorni di silenzio deve uscire"
    finally:
        S.sb = vero_sb


@prova("la giornata non e' finita: una bozza di follow-up in Posta non chiude la giornata")
def _():
    import battito as B
    vero = B.sb_tutte
    try:
        B.sb_tutte = lambda path, **k: []
        assert B.giornata("2026-10-06")[0].startswith("GIORNATA CHIUSA")
        B.sb_tutte = lambda path, **k: ([{"prospect_id": "x", "stato": "aperta", "azione": {"template": "FOLLOW UP 1"}}]
                                        if "/proposte" in path else [])
        assert B.giornata("2026-10-06")[0].startswith("GIORNATA APERTA"), "una bozza ferma e' un follow-up non partito"
        B.sb_tutte = lambda path, **k: ([{"id": "y", "company": "Si' senza analisi"}] if "/prospects" in path else [])
        assert B.giornata("2026-10-06")[0].startswith("GIORNATA APERTA"), "un si' senza analisi tiene aperta la giornata"
    finally:
        B.sb_tutte = vero


@prova("la rilettura non cambia classe leggendo la notifica di Smartlead")
def _():
    import rilettura as R
    assert R.segnaposto("Risposta ricevuta (Smartlead) - apri il thread per leggerla")
    assert R.segnaposto("")
    assert not R.segnaposto("Buongiorno, sì mi interessa ricevere l'analisi che mi avete proposto, grazie")
    assert R.illeggibile({"classe": "da_classificare", "perche": "messaggio di sistema, non risposta umana"})
    assert R.illeggibile({"classe": "da_classificare", "perche": "testo non disponibile"})


@prova("la rilettura legge solo la parte del lead, mai la nostra mail citata (caso WATER WAY, 6/10)")
def _():
    import rilettura as R
    vuota = "Il 2026-08-03 13:22 Lorenzo Fornasier ha scritto: Buongiorno Daniele, abbiamo preparato una breve analisi. Se le fa piacere riceverla, gliela mando subito"
    assert R.parte_sua(vuota) == "", "una risposta che cita solo noi non ha niente da leggere"
    vera = "mi incuriosisce vediamo e poi fissiamo un appuntamento Il giorno lun 10 ago 2026 alle ore 13:42 Lorenzo Fornasier < l@x.com > ha scritto: Buongiorno Lisa, gliela mando subito"
    assert "gliela mando" not in R.parte_sua(vera) and "mi incuriosisce" in R.parte_sua(vera)
    assert R.parte_sua("mandi") == "mandi", "una risposta corta ma vera si legge"


@prova("la stessa ora non si propone a piu' di tre persone insieme (caso mercoledi' 7 alle 16, 6/10)")
def _():
    import bozze as Bz
    vero = Bz.sb
    vero_occ = Bz.occupato_google
    Bz.occupato_google = lambda da, a: []     # la prova non guarda il calendario vero
    try:
        Bz.sb = lambda m, path, corpo=None, h=None: []
        primo = Bz.proposta_giorno_ora()
        Bz.sb = lambda m, path, corpo=None, h=None: ([{"giorno_proposto": primo}] * 3 if "proposte" in path else [])
        secondo = Bz.proposta_giorno_ora()
        assert secondo != primo, f"proposto di nuovo {primo} con tre bozze aperte che lo propongono gia'"
        Bz.sb = lambda m, path, corpo=None, h=None: ([{"giorno_proposto": primo}] * 2 if "proposte" in path else [])
        assert Bz.proposta_giorno_ora() == primo, "con due bozze l'ora resta libera"
    finally:
        Bz.sb = vero
        Bz.occupato_google = vero_occ


@prova("INT-23, vuole il materiale ma non la call: si manda l'analisi e non si propone nessun orario (caso Oikos, 6/10)")
def _():
    import bozze as Bz
    import seguiti as S
    vero = Bz.template_verbatim()
    # 8/10: se il bucket non risponde questo invariante cadeva dicendo «INT-23 e' rotto», che e'
    # falso e manda a cercare nel posto sbagliato. Il template che manca e' un guasto suo, e lo dice.
    assert vero and "INTERESSATO" in vero, \
        "template di Dre non scaricato dal bucket (riservato/risposte-template.md): non e' INT-23 a essere rotto"
    t = S.risposta("INT-23", {}, {}, "https://cal/NUOVO", giorno="giovedì 8 ottobre alle 15:30", testo_file=vero, garanzia=True)
    assert t, "INT-23 deve avere il suo testo dal template di Dre"
    assert "Le propongo" not in t and "giovedì 8 ottobre" not in t, "INT-23 propone comunque un orario: il playbook dice di non farlo"
    assert "calendar" not in t and "cal/NUOVO" not in t and "Calendario" not in t, "INT-23 non spinge il calendario"
    assert "confrontarmi" not in t and "a disposizione" in t, "si dice che restiamo a disposizione, come dice il playbook"
    assert "vi inoltro qui l'analisi" in t and "presentazione" in t, "l'analisi e la presentazione restano"
    # senza giorno dal calendario INT-23 si scrive lo stesso (non serve un orario)
    assert S.risposta("INT-23", {}, {}, "x", giorno=None, testo_file=vero, garanzia=False)
    # INT-01 resta com'era: propone l'orario
    assert "Le propongo una breve videochiamata conoscitiva giovedì 8 ottobre alle 15:30" in S.risposta("INT-01", {}, {}, "x", giorno="giovedì 8 ottobre alle 15:30", testo_file=vero)


@prova("i template di Dre: se il bucket non risponde si usa l'ultima copia buona, non il vuoto (6/10)")
def _():
    import tempfile, urllib.request as U
    import bozze as Bz
    loc = os.path.join(tempfile.gettempdir(), "odyn-risposte-template.md")
    # 8/10: prima, se la cache non c'era, questo invariante la CANCELLAVA alla fine. Il giro dopo
    # il test di INT-23 doveva riscaricare dal bucket e cadeva se la rete tossiva: un invariante
    # che avvelena quelli dopo di se'. Ora la copia buona si prende prima e si rimette sempre.
    if not os.path.exists(loc):
        Bz.template_verbatim()
    prima = open(loc, encoding="utf-8").read() if os.path.exists(loc) else None
    vero, vero_sleep = U.urlopen, Bz.time.sleep if hasattr(Bz, "time") else None
    try:
        open(loc, "w", encoding="utf-8").write("## INTERESSATO\n```\nSalve,\nciao\n```\n")
        os.utime(loc, (0, 0))                              # vecchia: va riscaricata
        def giu(*a, **k):
            raise OSError("bucket giu'")
        U.urlopen = giu
        import time as T
        dorme, T.sleep = T.sleep, (lambda s: None)
        try:
            t = Bz.template_verbatim()
        finally:
            T.sleep = dorme
        assert "Salve," in t, "con il bucket giu' i template sparivano"
    finally:
        U.urlopen = vero
        if prima is not None:
            open(loc, "w", encoding="utf-8").write(prima)
        elif os.path.exists(loc):
            os.remove(loc)


@prova("dopo il 25 ottobre (ora solare) la call non si propone sopra un impegno di Dre (6/10)")
def _():
    import types
    import bozze as Bz
    vero_sb, vero_dt = Bz.sb, Bz.datetime
    vero_occ = Bz.occupato_google
    Bz.occupato_google = lambda da, a: []     # la prova non guarda il calendario vero

    class Venerdi23(datetime.datetime):
        @classmethod
        def now(cls, tz=None):
            return datetime.datetime(2026, 10, 23, 7, 0, tzinfo=datetime.timezone.utc).astimezone(tz)
    try:
        Bz.datetime = types.SimpleNamespace(datetime=Venerdi23, timedelta=datetime.timedelta,
                                            timezone=datetime.timezone, date=datetime.date)
        # martedi' 27 ottobre alle 14:30 di Roma, che in ora solare sono le 13:30 UTC
        Bz.sb = lambda m, path, corpo=None, h=None: ([{"at": "2026-10-27T13:30:00+00:00", "fonte": "gcal"}] if "agenda" in path else [])
        g = Bz.proposta_giorno_ora()
        assert g != "martedì 27 ottobre alle 14:30", "proposta proprio sopra l'impegno di Dre: il fuso era fisso all'ora legale"
        assert g == "martedì 27 ottobre alle 15:30", f"atteso il primo buco a un'ora dall'impegno, proposto {g}"
    finally:
        Bz.sb, Bz.datetime = vero_sb, vero_dt
        Bz.occupato_google = vero_occ


@prova("il giorno proposto e' il primo giorno lavorativo utile da domani, non 48 ore dopo (Dre, 14/10: «la velocita' e' tutto»)")
def _():
    import bozze as Bz, types
    vero_sb, vero_dt = Bz.sb, Bz.datetime
    vero_occ = Bz.occupato_google
    Bz.occupato_google = lambda da, a: []     # la prova non guarda il calendario vero

    def giorno_da(anno, mese, giorno):
        class Finto(datetime.datetime):
            @classmethod
            def now(cls, tz=None):
                return datetime.datetime(anno, mese, giorno, 8, 0, tzinfo=datetime.timezone.utc).astimezone(tz)
        Bz.datetime = types.SimpleNamespace(datetime=Finto, timedelta=datetime.timedelta,
                                            timezone=datetime.timezone, date=datetime.date)
        return Bz.proposta_giorno_ora()
    try:
        Bz.sb = lambda m, path, corpo=None, h=None: []
        assert giorno_da(2026, 10, 14).startswith("giovedì 15 ottobre"), "mercoledi': si propone giovedi', il giorno dopo"
        assert giorno_da(2026, 10, 16).startswith("martedì 20 ottobre"), "venerdi': niente weekend, niente lunedi', quindi martedi'"
        # domani pieno di impegni: si va al giorno dopo, non alla settimana dopo
        pieno = [{"at": f"2026-10-15T{h:02d}:00:00+00:00", "fonte": "gcal"} for h in range(7, 16)]
        Bz.sb = lambda m, path, corpo=None, h=None: (pieno if "agenda" in path else [])
        assert giorno_da(2026, 10, 14).startswith("venerdì 16 ottobre"), "giovedi' pieno: venerdi', non piu' avanti"
    finally:
        Bz.sb, Bz.datetime = vero_sb, vero_dt
        Bz.occupato_google = vero_occ


@prova("analisi: il cliente non vede etichette nostre, segnaposto, gergo, ne' «verificato» di settimane fa; il nome solo se e' una persona (14/10)")
def _():
    import analisi_auto as A
    E = A.errori_visibili
    assert any("etichette" in e for e in E("Siete un Tipo B: il fit è buono.")), "etichette interne passano"
    assert any("etichette" in e for e in E("Stima da Keyword Planner per il settore.")), "Keyword Planner passa"
    assert any("segnaposto" in e for e in E("Chi vuole vendere casa a [comune] cerca una valutazione.")), "[comune] passa"
    assert any("gergo" in e for e in E("Una landing page con CTA chiara porta lead.")), "il gergo passa"
    assert any("verificato" in e for e in E("Verificato dal vivo il 21 settembre 2026.", fresca=False)), "verificato vecchio passa"
    assert not E("Verificato il 13 ottobre 2026: tre annunci attivi.", fresca=True), "una verifica fresca si puo' dire"
    pulito = ("Da quanto abbiamo visto non si notano vostri annunci su Google. Chi cerca un installatore a Savona "
              "scrive «caldaia a condensazione prezzo»: e' la domanda che porta a un sopralluogo. Napoli (NA), 2026.")
    assert not E(pulito), E(pulito)
    assert not E("Energy Fit e Copy Service a Treviso", nomi=["Energy Fit", "Copy Service"]), "un nome d'azienda non e' gergo"
    # il nome in copertina
    assert A.persona({"name": "Pietro Palermo", "company": "RE/MAX Stella Polare"}) == "Pietro Palermo"
    assert A.persona({"name": "Termocalor", "company": "Termocalor Srl"}) == "", "il nome dell'azienda come persona"
    assert A.persona({"name": "", "email": "mario.rossi@x.it"}) == "", "un nome indovinato dall'indirizzo"
    assert A.persona({"name": "info@x.it"}) == ""
    # la raccolta
    oggi = datetime.datetime.now(datetime.timezone.utc)
    assert A.raccolta_fresca({"raccolto_il": (oggi - datetime.timedelta(days=2)).isoformat()})
    assert not A.raccolta_fresca({"raccolto_il": "2026-09-21T10:00:00+00:00"}) or oggi.date() < datetime.date(2026, 9, 29)
    assert not A.raccolta_fresca({}), "senza data non e' fresca"
    # i fatti che legge il modello: niente etichette ne' «?»
    s = {"raccolta": {"raccolto_il": "2026-09-21T10:00:00+00:00", "fa_ads": False}, "ultime": [], "dominio": "x.it", "provincia": None,
         "fit": {"settore": "caldaie", "verdetto": "SI", "due_cose_scomode": "sito lento"}, "volumi": None}
    f = A.fatti_in_testo(s, {"company": "X"})
    assert "TIPO" not in f and "Provincia: ?" not in f and "(dal fit)" not in f, f[:400]
    assert "NON NOTA" in f and "da NON citare" in f and "PIU' DI UNA SETTIMANA FA" in f
    # il controllo finale usa tutto questo e boccia (le due bocciature portano alla domanda, come prima)
    an = {"intro": A.CHIUSURA, "body": "<p>Una landing per [comune]. Verificato dal vivo il 21 settembre.</p>", "bars": []}
    errs = " ".join(A.cancello(an, "Azienda: X", fresca=False))
    assert "gergo" in errs and "segnaposto" in errs and "verificato" in errs, errs


@prova("segnale provvisorio: il tetto del giorno conta solo i giri veri in cloud, non le prove (14/10, il collaudo aveva mangiato 143 letture su 150)")
def _():
    import segnale_provvisorio as SP
    vero = os.environ.get("GITHUB_ACTIONS")
    try:
        os.environ.pop("GITHUB_ACTIONS", None)
        assert not SP._vero(), "una prova sul Mac conta nel tetto dei giri veri"
        os.environ["GITHUB_ACTIONS"] = "true"
        assert SP._vero() or SP._a_secco()
    finally:
        if vero is None:
            os.environ.pop("GITHUB_ACTIONS", None)
        else:
            os.environ["GITHUB_ACTIONS"] = vero
    src = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "segnale_provvisorio.py")).read()
    assert "scopo=eq." in src, "il tetto deve contare solo lo scopo dei giri veri"


@prova("una chiamata lunga che scade non si ripete: pagata una volta, non tre (14/10, analisi oltre i 3 minuti)")
def _():
    import cervello as C, socket as so
    chiamate = []
    vero_open, vero_sleep, vera_chiave = C.urllib.request.urlopen, C.time.sleep, C._env

    def scade(req, timeout=None):
        chiamate.append(timeout)
        raise so.timeout("timed out")
    try:
        C.urllib.request.urlopen, C.time.sleep = scade, (lambda s: None)
        C._env = lambda n: "chiave-finta"
        try:
            C._chiedi_openai("x", "gpt-5", fornitore="openai")
        except RuntimeError as e:
            assert "non la ripeto" in str(e), e
        assert chiamate == [C.ATTESA_LUNGA], f"la chiamata lunga e' partita {len(chiamate)} volte: {chiamate}"
        chiamate.clear()
        try:
            C._chiedi_openai("x", "gpt-5", fornitore="openai", tetto=C.TETTO_USCITA["lettura"])
        except RuntimeError:
            pass
        assert chiamate == [C.ATTESA_MAX] * 3, f"una lettura corta riprova come prima: {chiamate}"
    finally:
        C.urllib.request.urlopen, C.time.sleep, C._env = vero_open, vero_sleep, vera_chiave


@prova("la presentazione: alla prima risposta si', salvo un no esplicito; nei follow-up solo se chiesta (14/10, Accomodando)")
def _():
    import manda as M
    assert M.con_presentazione(True, {}) is True, "la prima risposta porta la presentazione"
    assert M.con_presentazione(True, {"allega_presentazione": False}) is False, "un no esplicito non si rispetta"
    assert M.con_presentazione(False, {}) is False and M.con_presentazione(False, {"allega_presentazione": True}) is True


@prova("il giorno proposto rispetta il calendario vero di Dre, inviti compresi (14/10, riunione di venerdi' con Lorenzo)")
def _():
    import bozze as Bz, types, zoneinfo
    roma = zoneinfo.ZoneInfo("Europe/Rome")
    vero_sb, vero_dt, vero_occ = Bz.sb, Bz.datetime, Bz.occupato_google

    class Mercoledi(datetime.datetime):
        @classmethod
        def now(cls, tz=None):
            return datetime.datetime(2026, 10, 14, 8, 0, tzinfo=datetime.timezone.utc).astimezone(tz)
    try:
        Bz.datetime = types.SimpleNamespace(datetime=Mercoledi, timedelta=datetime.timedelta, timezone=datetime.timezone,
                                            date=datetime.date, time=datetime.time)
        Bz.sb = lambda m, path, corpo=None, h=None: []
        # giovedi' 15 occupato dalle 14 alle 17 (un invito, che l'agenda non vede): la call non ci finisce sopra
        Bz.occupato_google = lambda da, a: [(datetime.datetime(2026, 10, 15, 14, 0, tzinfo=roma), datetime.datetime(2026, 10, 15, 17, 0, tzinfo=roma))]
        g = Bz.proposta_giorno_ora()
        assert g.startswith("giovedì 15 ottobre alle 1") and not any(f"alle {o}" in g for o in ("14:30", "15", "15:30", "16", "16:30")), g
        assert g in ("giovedì 15 ottobre alle 10", "giovedì 15 ottobre alle 10:30", "giovedì 15 ottobre alle 11", "giovedì 15 ottobre alle 11:30", "giovedì 15 ottobre alle 12"), g
        # finito l'impegno alle 15:45, alle 16 si puo'
        Bz.occupato_google = lambda da, a: [(datetime.datetime(2026, 10, 15, 13, 0, tzinfo=roma), datetime.datetime(2026, 10, 15, 15, 45, tzinfo=roma))]
        assert Bz.proposta_giorno_ora() == "giovedì 15 ottobre alle 16", Bz.proposta_giorno_ora()
    finally:
        Bz.sb, Bz.datetime, Bz.occupato_google = vero_sb, vero_dt, vero_occ


@prova("un no con parole in mezzo resta un no, e la nostra frase citata «se non fosse interessato» non conta (14/10, Piergentili)")
def _():
    import sync_v2 as S
    for no in ("Grazie Lorenzo, non sono al momento interessato. Buona serata.",
               "Non sono momentaneamente interessato a questo servizio da voi offerto",
               "la ringrazio ma non siamo momentamente interessati al servizio .",
               "al momento non son interessato in quanto collaboro gia'"):
        assert S.classifica(no) == "negativo", f"un no letto come {S.classifica(no)}: {no}"
        import lettura as L, categorie_smartlead as CS
        assert L.DETTO_NO.search(no) and CS.NO_SCRITTO.search(no), f"la stessa regola manca in lettura o nelle etichette: {no}"
    assert S.classifica("Sì, sono interessato, me la mandi") == "positivo"
    assert S.classifica("Buongiorno, valutiamo certo. Mi faccia sapere, se invece non fosse interessato non c'è alcun problema") != "negativo", \
        "la nostra frase ipotetica citata fa diventare no un si'"


@prova("una bozza senza separatore si riprova una volta, non sparisce in silenzio (14/10, Accomodando)")
def _():
    import bozze as Bz, cervello as C, io, contextlib
    risposte = ["LETTURA: x\nINTENTO: INT-01\nSalve,\nla mail senza separatore", "LETTURA: x\nINTENTO: INT-01\nFERMATI: no\n---\nSalve,\nla mail"]
    chiamate = []
    vero = C._chiedi
    try:
        C._chiedi = lambda prompt, modello=None: (chiamate.append(1), risposte[len(chiamate) - 1])[1]
        Bz.proposta_giorno_ora, vero_g = (lambda *a, **k: "giovedì 15 ottobre alle 16"), Bz.proposta_giorno_ora
        try:
            with contextlib.redirect_stdout(io.StringIO()):
                b = Bz.chiedi_bozza({"company": "X", "email": "x@x.it", "enriched": {}}, "ok, me la mandi")
        finally:
            Bz.proposta_giorno_ora = vero_g
        assert len(chiamate) == 2 and b and b["bozza"].startswith("Salve"), (len(chiamate), b)
    finally:
        C._chiedi = vero


@prova("il direttore in due corsie: ogni operazione in una sola, e il postino misura il lucchetto da quando e' preso (15/10)")
def _():
    import direttore as D, manda as M, datetime as dt
    tutte = [op["chiave"] for op in (D.sb("GET", "/rest/v1/operazioni?select=chiave") or [])]
    assert tutte, "nessuna operazione letta"
    for c in tutte:
        assert D.corsia_di(c) in ("leggera", "pesante")
    for c in ("segnale", "manda", "prima_risposta", "sync_smartlead"):
        assert D.corsia_di(c) == "leggera", f"{c} non deve aspettare le analisi"
    for c in ("analisi", "lampo", "bozze", "googlefit"):
        assert D.corsia_di(c) == "pesante"
    ora = dt.datetime(2026, 10, 15, 12, 0, tzinfo=M.ROMA)
    vecchia_appena_presa = {"at": "2026-10-14T09:00:00+02:00", "risposta_il": "2026-10-15T11:58:00+02:00"}
    assert M.eta_lucchetto(vecchia_appena_presa, ora) < M.LUCCHETTO_APPESO_MIN, "una bozza di ieri appena presa sembra appesa"
    assert M.eta_lucchetto({"at": "2026-10-15T11:00:00+02:00"}, ora) >= M.LUCCHETTO_APPESO_MIN
    src = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".github", "workflows", "direttore.yml")).read()
    assert "--corsia leggera" in src and "--corsia pesante" in src and "group: direttore-leggera" in src


@prova("il postino risponde a chi ha scritto, se e' della stessa azienda da un altro indirizzo (15/10, Techno Pool)")
def _():
    import manda as M
    r = lambda fr: {"type": "REPLY", "from": fr}
    assert M.chi_ha_risposto(r("Mario Rossi <mario@azienda.it>"), "info@azienda.it") == "mario@azienda.it"
    assert M.chi_ha_risposto(r("info@azienda.it"), "info@azienda.it") is None, "stesso indirizzo: niente da cambiare"
    assert M.chi_ha_risposto(r("x@altro-dominio.it"), "info@azienda.it") is None, "un altro dominio non si segue da solo"
    assert M.chi_ha_risposto(r("noreply@azienda.it"), "info@azienda.it") is None
    assert M.chi_ha_risposto({"type": "SENT", "from": "a@azienda.it"}, "info@azienda.it") is None


@prova("il postino risponde nel filo dove il lead ha risposto per ultimo, non nel primo che trova (15/10, EnergetiKa)")
def _():
    import manda as M
    storie = {(100, 7): {"history": [{"type": "REPLY", "time": "2026-05-27T09:28:00Z", "message_id": "vecchio"}]},
              (200, 7): {"history": [{"type": "SENT", "time": "2026-09-28T08:00:00Z"},
                                     {"type": "REPLY", "time": "2026-10-01T10:00:00Z", "message_id": "nuovo"}]}}
    vero_sl, vero_segna = M._sl_riprova, M._segna_thread
    try:
        M._sl_riprova = lambda m, path: (storie.get((int(path.split("/")[2]), int(path.split("/")[4]))) if "message-history" in path
                                        else {"id": 7, "lead_campaign_data": [{"campaign_id": 100, "last_reply_at": "2026-05-27"}, {"campaign_id": 200, "last_reply_at": "2026-10-01"}]})
        M._segna_thread = lambda *a: None
        cid, lid, ultima = M.thread({"email": "x@azienda.it", "campaign_id": 100, "lead_id": 7, "enriched": {}})
        assert (cid, ultima["message_id"]) == (200, "nuovo"), f"filo sbagliato: {cid}"
    finally:
        M._sl_riprova, M._segna_thread = vero_sl, vero_segna


@prova("il sync legge anche le campagne archiviate: una risposta in un filo vecchio deve entrare (15/10, EnergetiKa)")
def _():
    src = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "sync_v2.py")).read()
    assert '!= "ARCHIVED"' not in src, "il sync salta di nuovo le campagne archiviate"


@prova("l'approvazione rifa' la seconda testa sul testo che parte: una riscrittura incoerente si ferma (15/10, Maori Group)")
def _():
    import approva as A, lettura as L
    vero_leggi, vera_coer = L.leggi, L.coerenza
    try:
        L.leggi = lambda p: (None, {"ultima_loro": "ho girato la sua mail a chi se ne occupa"})
        L.coerenza = lambda letti, testo, gruppo=None, cc=None: ("INCOERENTE", "nessun collega ha girato il contatto") if "collega mi ha girato" in testo else ("COERENTE", "")
        assert A.seconda_testa({}, "il suo collega mi ha girato il suo contatto")[0] == "INCOERENTE"
        assert A.seconda_testa({}, "mi può dire a chi ha girato la mia mail?")[0] == "COERENTE"
        L.leggi = lambda p: (_ for _ in ()).throw(RuntimeError("smartlead giu'"))
        assert A.seconda_testa({}, "x")[0] == "NON LETTA", "se la lettura cade, si approva lo stesso"
    finally:
        L.leggi, L.coerenza = vero_leggi, vera_coer


@prova("le bozze: l'errore di un lead non fa crollare il giro, e una classe decisa da una persona non si tocca (16/10, 68 $ in una notte)")
def _():
    src = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "bozze.py")).read()
    assert "pool.map(lavora_sicuro, candidate)" in src, "un errore su un lead fa di nuovo crollare tutto il giro dopo aver pagato"
    assert '"lock umano" in str(e)' in src, "la classe decisa da una persona fa crollare il giro"


@prova("le analisi ferme: una domanda sola aperta, quelle dei giorni prima si chiudono (6/10)")
def _():
    import bozze as Bz
    vero = Bz.sb
    chiuse = []
    try:
        aperte = [{"id": 1, "ref": "ferme:2026-10-04"}, {"id": 2, "ref": "ferme:2026-10-05"}, {"id": 3, "ref": "ferme:2026-10-06"}]
        Bz.sb = lambda m, path, corpo=None, h=None: (aperte if m == "GET" else chiuse.append((path, corpo)))
        Bz.supera_ferme("2026-10-06")
        ids = sorted(int(p.split("eq.")[1]) for p, _ in chiuse)
        assert ids == [1, 2], f"chiuse {ids}: vanno chiuse solo quelle dei giorni prima"
        assert all(c["stato"] == "no" for _, c in chiuse)
    finally:
        Bz.sb = vero


@prova("la salute del sistema: una domanda sola aperta, non una al giorno (6/10)")
def _():
    import salute as Sa
    vero = Sa.sb
    chiuse = []
    try:
        aperte = [{"id": 7, "ref": "salute:2026-10-05"}, {"id": 8, "ref": "salute:2026-10-06"}]
        Sa.sb = lambda m, path, corpo=None, h=None: (aperte if m == "GET" else chiuse.append(path))
        Sa.supera_vecchie("2026-10-06")
        assert chiuse == ["/rest/v1/proposte?id=eq.7"], chiuse
    finally:
        Sa.sb = vero


@prova("la rilettura cambia classe solo se la nuova lettura si ripete due volte di fila (6/10)")
def _():
    import rilettura as R
    p = {"enriched": {}}
    assert R.conferma(p, "negativo") == "aspetta", "una lettura sola non cambia la classe"
    p = {"enriched": {"lettura_candidata": {"classe": "negativo"}}}
    assert R.conferma(p, "negativo") == "applica", "due letture uguali di fila la cambiano"
    assert R.conferma(p, "tiepido") == "aspetta", "una lettura diversa dalla candidata riparte da capo"
    assert R.conferma({"enriched": {}}, "soppresso") == "applica", "la richiesta di rimozione vale subito"


@prova("il timer del follow-up: analisi + 5 giorni, ma il giorno di Dre vince, in un campo suo (6-7/10)")
def _():
    import followup as F
    import datetime as _dt
    inviata = _dt.date(2026, 10, 1)
    assert F.giorno_follow_up(inviata, {}) == (_dt.date(2026, 10, 6), False)
    assert F.giorno_follow_up(inviata, {"follow_up_il": "2026-10-20"}) == (_dt.date(2026, 10, 20), True)
    # una data rotta non ferma il giro: si torna alla regola dei 5 giorni
    assert F.giorno_follow_up(inviata, {"follow_up_il": "boh"}) == (_dt.date(2026, 10, 6), False)
    # 7/10: la data detta dal LEAD (next_action_date, rinvio) non e' il giorno di Dre
    assert F.giorno_follow_up(inviata, {"next_action_date": "2027-01-10"}) == (_dt.date(2026, 10, 6), False)


@prova("il giorno di Dre ferma anche la CODA, non solo lo schermo (caccia ai bug 6/10)")
def _():
    import followup as F
    import datetime as _dt
    vecchia = (_dt.date.today() - _dt.timedelta(days=20)).isoformat()
    lontano = (_dt.date.today() + _dt.timedelta(days=15)).isoformat()
    p = {"id": "x", "company": "Prova", "email": "a@b.it", "analysis_sent_at": vecchia, "last_reply_at": None,
         "coda": None, "follow_up_il": lontano}
    messi = []
    vero = (F.sb, F.sb_tutte, F.in_coda, F.calendario, F.mini_followup, F._fu)
    try:
        F._fu = lambda: ",follow_up_il"
        F.sb = lambda m, path, corpo=None, h=None: [p] if path.startswith("/rest/v1/prospects?select") else []
        F.sb_tutte = lambda path, **k: []
        F.in_coda = lambda pid, gruppo: messi.append(pid)
        F.calendario = lambda prova, oggi: None
        F.mini_followup = lambda prova, oggi: 0
        F.main()
        assert not messi, "accodato prima del giorno scelto da Dre"
        p["follow_up_il"] = None
        F.main()
        assert messi == ["x"], "senza giorno scelto, analisi+5 deve accodare"
    finally:
        F.sb, F.sb_tutte, F.in_coda, F.calendario, F.mini_followup, F._fu = vero


@prova("il Google Fit si legge in un modo solo: il nuovo vince, la decisione di Dre riapre (7/10)")
def _():
    from stanza import fit_di, fit_bocciato
    v1no = {"google_fit": {"verdetto": "NO", "motivo": "vecchio"}}
    assert fit_di({"enriched": v1no})[:2] == ("NO", "vecchio")
    assert fit_bocciato({"enriched": v1no})
    # caso SAD Sanificazioni: v1 NO ma v2 FORSE -> non e' fuori target, per NESSUN copione
    assert not fit_bocciato({"enriched": {**v1no, "google_fit_v2": {"verdetto": "FORSE"}}})
    assert fit_bocciato({"enriched": {"google_fit_v2": {"verdetto": "NO", "motivo": "portale"}}})
    assert not fit_bocciato({"enriched": {"google_fit_v2": {"verdetto": "NO"}, "google_fit_decisione": "invia"}})
    assert fit_bocciato({"enriched": {"google_fit_v2": {"verdetto": "NO"}, "google_fit_decisione": "soppresso"}})
    # bozze.py e prima_risposta usano QUESTA regola, non una copia
    import pathlib
    qui = pathlib.Path(__file__).parent
    for f in ("bozze.py", "prima_risposta.py"):
        t = qui.joinpath(f).read_text(encoding="utf-8")
        assert 'get("google_fit") or {}).get("verdetto") == "NO"' not in t, f"{f} legge ancora solo il fit vecchio"


@prova("«Invia comunque» passa sopra alle esclusioni dell'analisi, il sito illeggibile no (7/10)")
def _():
    import analisi_auto as A
    agenzia = {"enriched": {"google_fit": {"verdetto": "NO", "sito_letto": True, "esclusione": "agenzia"}}}
    assert not A.servita(agenzia)
    assert A.servita({"enriched": {**agenzia["enriched"], "google_fit_decisione": "invia"}})
    assert not A.servita({"enriched": {"google_fit": {"verdetto": "NO"}, "google_fit_decisione": "invia"}}), "senza sito letto non si genera"
    # e la bozza non promette un'analisi che con «invia comunque» non puo' nascere
    import bozze as B
    assert B.analisi_impossibile({"enriched": {"google_fit": {"verdetto": "NO"}, "google_fit_decisione": "invia"}})
    assert not B.analisi_impossibile({"enriched": {"google_fit": {"verdetto": "NO", "sito_letto": True}, "google_fit_decisione": "invia"}})
    assert not B.analisi_impossibile({"analysis_pdf": "x.pdf", "enriched": {"google_fit": {"verdetto": "NO"}}})
    # il fit nuovo vale come sito letto solo se ha capito cosa fanno (revisione 7/10)
    assert A.servita({"enriched": {"google_fit_v2": {"verdetto": "SI", "cosa_fa": "serramenti"}}})
    assert not A.servita({"enriched": {"google_fit_v2": {"verdetto": "FORSE", "cosa_fa": None, "motivo": "il sito non si legge"}}})
    # Keyword Planner caduto ma sito letto: si genera lo stesso
    assert A.servita({"enriched": {"google_fit_v2": {"verdetto": "FORSE", "cosa_fa": "serramenti", "errore": "planner giu'"}}})
    # il brief dell'analisi legge il fit unito: il nuovo vince, il vecchio riempie
    u = A.fit_unito({"enriched": {"google_fit": {"verdetto": "NO", "settore": "infissi", "cosa_fa": "vecchio"},
                                  "google_fit_v2": {"verdetto": "FORSE", "cosa_fa": "nuovo", "motivo": "m"}}})
    assert (u["verdetto"], u["cosa_fa"], u["settore"]) == ("FORSE", "nuovo", "infissi")


@prova("una bozza di follow-up col giorno spostato da Dre non parte prima di quel giorno (caso Jaam, 7/10)")
def _():
    import prima_risposta as R
    import datetime as _dt
    domani = (_dt.date.today() + _dt.timedelta(days=1)).isoformat()
    pr = {"tipo": "risposta", "titolo": "FU", "azione": {"parte_il": domani, "lettura": {"gruppo": "FOLLOW UP 1"}}}
    assert any("giorno scelto da Dre" in m for m in R.perche_no_seguito(pr, {"email": "a@b.it"}))
    pr["azione"]["parte_il"] = _dt.date.today().isoformat()
    assert not any("giorno scelto da Dre" in m for m in R.perche_no_seguito(pr, {"email": "a@b.it"}))


@prova("il FOLLOW UP 1 non si mette in coda a chi ha gia' una bozza aperta in Posta (caso SCUDO, 6/10)")
def _():
    import followup as F
    import datetime as _dt
    vecchia = (_dt.date.today() - _dt.timedelta(days=20)).isoformat()
    p = {"id": "x", "company": "Prova", "email": "a@b.it", "analysis_sent_at": vecchia, "last_reply_at": None, "coda": None}
    messi = []
    vero = (F.sb, F.sb_tutte, F.in_coda, F.calendario)
    try:
        F.sb = lambda m, path, corpo=None, h=None: [p] if path.startswith("/rest/v1/prospects?select") else []
        F.sb_tutte = lambda path, **k: [{"prospect_id": "x", "tipo": "risposta"}] if "stato=in.(aperta" in path else []
        F.in_coda = lambda pid, gruppo: messi.append(pid)
        F.calendario = lambda prova, oggi: None
        F.main()
        assert not messi, "messo in coda per il FOLLOW UP 1 con una bozza gia' aperta"
        # una domanda aperta (l'analisi bocciata, da guardare) non e' una bozza: si va in coda lo stesso
        F.sb_tutte = lambda path, **k: [{"prospect_id": "x", "tipo": "umano", "bozza": None}] if "stato=in.(aperta" in path else []
        F.main()
        assert messi == ["x"], "una domanda senza mail dentro non deve togliere il follow-up"
    finally:
        F.sb, F.sb_tutte, F.in_coda, F.calendario = vero


@prova("la prima risposta: una bozza gia' decisa da un altro giro non si approva sopra (caso casainromagna, 6/10)")
def _():
    import prima_risposta as PR
    vero = PR.sb
    viste = []
    try:
        PR.sb = lambda m, path, corpo=None, h=None: (viste.append(path) or [])
        assert PR.segna({"id": 5}, {"x": 1}, {"stato": "approvata"}, prima_decisione=True) is False
        assert "azione->prima_risposta=is.null" in viste[-1] and "stato=eq.aperta" in viste[-1], viste[-1]
    finally:
        PR.sb = vero


@prova("il postino prende una mail solo se e' ancora approvata: mai due invii uguali (caso Pircher e Maura, 1/10)")
def _():
    import manda as M
    vero = M.sb
    chiamate = []
    try:
        M.sb = lambda m, path, corpo=None, h=None: (chiamate.append((m, path, corpo, h)) or [])
        assert M.prendi({"id": 9}) is False, "se un altro postino l'ha gia' presa non si manda"
        m, path, corpo, h = chiamate[-1]
        assert m == "PATCH" and "stato=eq.approvata" in path and corpo.get("stato") == "in_invio" and corpo.get("risposta_il"), corpo
        assert h and "return=representation" in h.get("Prefer", ""), "senza la risposta non si sa se la presa e' riuscita"
        M.sb = lambda m, path, corpo=None, h=None: [{"id": 9}]
        assert M.prendi({"id": 9}) is True
    finally:
        M.sb = vero


@prova("il sync riconosce l'analisi consegnata anche con «le allego» (caso Boris, 6/10)")
def _():
    import sync_v2 as S
    assert S.consegna_analisi("salve alberto, l'analisi che le allego lo dice apertamente")
    assert S.consegna_analisi("perfetto, come promesso le inoltro qui l'analisi che abbiamo preparato")
    assert S.consegna_analisi("le lascio qui l'analisi che avevamo preparato su the right side")
    assert not S.consegna_analisi("abbiamo preparato una breve analisi che mi piacerebbe condividerle. se le fa piacere riceverla, gliela mando subito")
    assert not S.consegna_analisi("le avevo scritto qualche giorno fa riguardo a un'analisi marketing che avevamo preparato")


@prova("una bozza in attesa non propone mai un giorno gia' passato (6/10)")
def _():
    import bozze as Bz
    import datetime as _dt
    oggi = _dt.date(2026, 10, 6)
    assert Bz.orario_scaduto("Le propongo martedì 29 settembre alle 14:30, oppure", oggi) == "martedì 29 settembre alle 14:30"
    assert Bz.orario_scaduto("Le propongo martedì 6 ottobre alle 14:30", oggi), "oggi stesso conta come scaduto: arriverebbe tardi"
    assert Bz.orario_scaduto("Le propongo giovedì 8 ottobre alle 15", oggi) is None
    assert Bz.orario_scaduto("Le propongo lunedì 11 gennaio alle 15", oggi) is None, "gennaio e' dell'anno prossimo"
    assert Bz.orario_scaduto("Le propongo martedì 14 luglio alle 15", oggi), "luglio scritto a ottobre e' passato"
    assert Bz.orario_scaduto("le avevo scritto martedì 29 settembre alle 10 e non ci siamo sentiti", oggi) is None, "un ricordo non e' una proposta"


@prova("una sigla in maiuscolo non e' un «tu» (caso TI.EMME.TI, 5/10)")
def _():
    import bozze as Bz
    e = Bz.cancello("Salve Mario,\n\nle scrivo per TI.EMME.TI: le propongo una chiamata giovedì, qui trova il calendario https://calendar.app.google/x\n\nUn saluto")
    assert not any("registro misto" in x for x in e), e
    e2 = Bz.cancello("Salve Mario,\n\nti scrivo e le propongo una chiamata giovedì: https://calendar.app.google/x\n\nUn saluto")
    assert any("registro misto" in x for x in e2), "un tu vero insieme al lei deve ancora essere bocciato"


@prova("i follow-up non hanno un tetto, solo un ammortizzatore di 5 in piu' per casella (Dre, 6/10)")
def _():
    import prima_risposta as R
    # «se tanti cadono nello stesso quinto giorno dovremmo aspettare?» No: il numero deve
    # reggere un giorno pieno (5 per casella), non fermare chi e' dovuto
    assert R.MAX_SEGUITI_AL_GIORNO >= 5 * R.CASELLE_IN_CAMPAGNA >= 300, R.MAX_SEGUITI_AL_GIORNO
    # e i giri nella finestra devono poterci arrivare davvero (revisione 7/10: era 5 x 24 = 120)
    assert R.MAX_PER_GIRO_SEGUITI * R.GIRI_NELLA_FINESTRA >= R.MAX_SEGUITI_AL_GIORNO
    # la prima risposta automatica: dal 9/10 sera niente tetto operativo («invia tutti in
    # giornata finche' non finiscono i si'»), solo un fusibile che non deve sparire
    assert 15 < R.MAX_AL_GIORNO <= 60, R.MAX_AL_GIORNO


@prova("il battito nomina il si' che nessuno prende (caso SOLPOWER, 7/10)")
def _():
    import battito as B
    dati = {
        "prospects": [{"id": "a", "company": "Fermo Srl", "email": "a@x.it", "coda": None},
                      {"id": "b", "company": "Con Bozza", "email": "b@x.it", "coda": None},
                      {"id": "c", "company": "In Coda", "email": "c@x.it", "coda": "RIPRESA"}],
        "seguiti_calendario": [], "proposte": [{"prospect_id": "b", "stato": "aperta", "azione": {}}],
    }
    vero = B.sb_tutte
    try:
        B.sb_tutte = lambda path, **k: next((v for t, v in dati.items() if f"/rest/v1/{t}?" in path), [])
        righe = B.giornata("2026-10-07")
    finally:
        B.sb_tutte = vero
    fermi = [r for r in righe if "FERMO" in r]
    assert len(fermi) == 1 and "Fermo Srl" in fermi[0], righe


@prova("un ripreso dall'archivio non torna in archivio in silenzio, nemmeno il giorno della scadenza (7/10)")
def _():
    import silenzi as S
    import datetime as _dt
    oggi = _dt.date.today().isoformat()
    vecchia = (_dt.date.today() - _dt.timedelta(days=60)).isoformat()
    seguito = (_dt.date.today() - _dt.timedelta(days=30)).isoformat()
    p = {"id": "x", "company": "Prova", "analysis_sent_at": vecchia, "last_reply_at": None, "next_action_date": oggi, "ooo_until": None}
    scritti, domande = [], []
    vero = (S.sb, S.ultimo_seguito, S.ripreso_dopo, S.proponi_scaduto)
    try:
        def finto(m, path, corpo=None, h=None):
            if m == "PATCH":
                scritti.append(corpo)
            return [p] if path.startswith("/rest/v1/prospects?select") else []
        S.sb = finto
        S.ultimo_seguito = lambda q: seguito
        S.ripreso_dopo = lambda q, s: True
        S.proponi_scaduto = lambda q: domande.append(q["id"])
        S.main()
        assert not scritti, "il giorno della scadenza l'ha riarchiviato"
        p["next_action_date"] = None
        S.main()
        assert not scritti and domande == ["x"], "un ripreso scaduto deve diventare una domanda, non un archivio silenzioso"
    finally:
        S.sb, S.ultimo_seguito, S.ripreso_dopo, S.proponi_scaduto = vero


@prova("chi ha gia' l'analisi e dice «piu' avanti»: niente riallegata, data a due settimane, follow-up dopo l'invio (Dre 7/10, La Bottega del Legno)")
def _():
    import seguiti as S
    import manda as M
    p = {"email": "acquisti@x.it", "name": "Paola", "analysis_sent": True}
    t = S.risposta("INT-06", p, {}, "https://calendar.app.google/x", giorno="martedì 21 ottobre alle 15", testo_file="")
    assert t and "analisi" in t and "inoltro" not in t.lower() and "allego" not in t.lower(), t
    assert "martedì 21 ottobre alle 15" in t and "calendar.app.google" in t and "domani" not in t, t
    # senza giorno lo scrive una persona; chi l'analisi non l'ha ancora resta sul modello di Dre
    assert S.risposta("INT-06", p, {}, "c", giorno=None, testo_file="") is None
    assert S.risposta("INT-06", {**p, "analysis_sent": False}, {}, "c", giorno="x", testo_file="") is None, "senza periodo e senza template non deve inventare"
    # il postino applica solo i campi permessi, con valori sani
    assert M.dopo_invio({"dopo_invio": {"classificazione": "rinvio", "next_action_date": "2026-10-22", "next_action": "x", "stage": "cliente"}}) == \
        {"classificazione": "rinvio", "next_action_date": "2026-10-22", "next_action": "x"}
    assert M.dopo_invio({"dopo_invio": {"classificazione": "soppresso", "next_action_date": "domani"}}) == {}
    assert M.dopo_invio({}) == {}


@prova("la seconda risposta di un lead non si perde: i fili caldi si rileggono anche col contatore fermo (7/10, La Bottega del Legno)")
def _():
    import sync_v2 as S
    from datetime import datetime, timezone, timedelta
    ieri = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
    vecchio = (datetime.now(timezone.utc) - timedelta(days=90)).isoformat()
    known = {
        "caldo@x.it": {"awaiting_us": False, "classificazione": "positivo", "analysis_sent_at": ieri, "enriched": {}},
        "freddo@x.it": {"awaiting_us": False, "classificazione": "positivo", "analysis_sent_at": vecchio, "last_reply_at": vecchio, "enriched": {}},
        "chiuso@x.it": {"awaiting_us": False, "classificazione": "soppresso", "analysis_sent_at": ieri, "enriched": {}},
        "aspetta@x.it": {"awaiting_us": True, "classificazione": "positivo", "analysis_sent_at": ieri, "enriched": {}},
    }
    assert S.fili_caldi(known) == {"caldo@x.it"}, S.fili_caldi(known)
    # la rotazione: i meno riletti per primi, al massimo CALDI_PER_GIRO
    tanti = {f"l{i}@x.it": {"awaiting_us": False, "classificazione": "positivo", "analysis_sent_at": ieri,
                             "enriched": {"sl_riletto_il": f"2026-10-0{i % 9 + 1}"}} for i in range(S.CALDI_PER_GIRO + 10)}
    scelti = S.fili_caldi(tanti)
    assert len(scelti) == S.CALDI_PER_GIRO
    assert all(tanti[e]["enriched"]["sl_riletto_il"] <= min(tanti[x]["enriched"]["sl_riletto_il"] for x in tanti if x not in scelti) for e in scelti)


@prova("una risposta a un follow-up di oggi su un filo vecchio si vede subito, e a mesi di distanza l'analisi si rialleg a (UNO Capital, Quisto, 7/10)")
def _():
    import sync_v2 as S
    from datetime import datetime, timezone, timedelta
    vecchio = (datetime.now(timezone.utc) - timedelta(days=90)).isoformat()
    known = {"luglio@x.it": {"id": "p1", "awaiting_us": False, "classificazione": "positivo",
                             "analysis_sent_at": vecchio, "last_reply_at": vecchio, "enriched": {}}}
    assert S.fili_caldi(known) == set(), "senza un nostro invio recente il filo vecchio resta freddo"
    assert S.fili_caldi(known, frozenset({"p1"})) == {"luglio@x.it"}, "un nostro follow-up recente lo rende caldo"
    src = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "bozze.py"), encoding="utf-8").read()
    assert 'timedelta(days=30)).isoformat():\n                azione["allega"] = True' in src, "analisi di piu' di 30 giorni: si rialleg a"


@prova("un rinvio con la data entra in coda da solo quando la data arriva, ma solo dal 7/10 in poi: il passato lo decide Dre (La Fonte, 7/10)")
def _():
    import followup as F
    import datetime
    assert F.MOTORE_RINVII_DAL == datetime.date(2026, 10, 7)
    src = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "followup.py"), encoding="utf-8").read()
    assert "rinvii_scaduti(prova, datetime.date.today())" in src, "il motore dei rinvii gira nel giro orario"
    assert "next_action_date=gte." in src and "coda=is.null" in src, "solo date nuove, e mai sopra una coda gia' piena"


@prova("un follow-up non parte verso chi nel frattempo ha detto no o non e' la persona giusta, e il timer dell'analisi non riparte a ogni invio (controllo dal vivo del 7/10)")
def _():
    base = os.path.dirname(os.path.abspath(__file__))
    m = open(os.path.join(base, "manda.py"), encoding="utf-8").read()
    assert '("negativo", "persona_sbagliata")' in m, "manda deve fermare i follow-up ai negativi e alle persone sbagliate"
    assert 'if p.get("analysis_sent") else' in m, "analysis_sent_at si scrive solo al primo invio"
    f = open(os.path.join(base, "followup.py"), encoding="utf-8").read()
    assert '[:10] > p["analysis_sent_at"][:10]' not in f, "il confronto va fatto sull'ora: chi risponde lo stesso giorno dell'analisi non e' muto"
    assert "stage.in.(cliente,perso,call_fissata,rinviato)" in f, "il calendario esclude le call fissate da ogni passo"
    assert "pid in morti or pid in aperte" in f, "i filtri del calendario valgono per tutti i passi, dentro metti()"
    assert "onorati" in f, "un rinvio gia' onorato dalla ripresa non e' scaduto"


@prova("il nome dell'azienda arriva anche dal campo «azienda» di Smartlead, e un nome scritto a mano non si sovrascrive (7/10, Studio Nigris)")
def _():
    import sync_v2 as S
    assert S.azienda_di({"company_name": "", "custom_fields": '{"azienda":"Studio Nigris","icebreaker":"x"}'}) == "Studio Nigris"
    assert S.azienda_di({"company_name": "Vetrocom", "custom_fields": '{"azienda":"Altro"}'}) == "Vetrocom"
    assert S.azienda_di({"company_name": None, "custom_fields": {"azienda": " Pircher "}}) == "Pircher"
    assert S.azienda_di({"company_name": "", "custom_fields": "non json"}) == ""
    assert S.azienda_di({}) == ""
    src = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "sync_v2.py"), encoding="utf-8").read()
    assert '"company_name": azienda_di(r)' in src, "la sincronizzazione deve leggere il nome con azienda_di"
    assert 'not (rec.get("company") or "").strip()' in src, "il nome si riempie solo se vuoto"
    assert "select=id,email,company," in src, "senza company letto, il riempimento non sa se il nome c'e' gia'"


@prova("la preparazione della conoscitiva chiede da 8 a 10 domande dal generico al preciso, col linguaggio del settore (regola di Dre del 12/8, ripresa il 7/10)")
def _():
    import cervello as C
    # il prompt della conoscitiva porta la regola; le altre call restano corte
    assert "dal generico al preciso" in C.REGOLA_CONOSCITIVA and "8" in C.REGOLA_CONOSCITIVA
    assert "parole del LORO mestiere" in C.REGOLA_CONOSCITIVA
    vero = C._chiedi
    try:
        tre = "Chi sono: x\n\nLe domande\n1. a\n2. b\n3. c\n"
        C._chiedi = lambda prompt: tre
        assert C.preparo("x" * 200, tipo="conoscitiva") is None, "con 3 domande la conoscitiva non deve passare"
        otto = "Chi sono: x\n\nLe domande\n" + "\n".join(f"{i}. domanda {i}" for i in range(1, 9))
        C._chiedi = lambda prompt: otto
        assert C.preparo("x" * 200, tipo="conoscitiva"), "con 8 domande deve passare"
        visto = {}
        C._chiedi = lambda prompt: (visto.setdefault("p", prompt), "Chi sono: un'azienda di prova\n\nCosa chiedere\n- una domanda vera sul preventivo")[1]
        assert C.preparo("x" * 200, tipo="tecnica") and "dal generico al preciso" not in visto["p"]
    finally:
        C._chiedi = vero


@prova("ogni copione importa le funzioni della stanza che chiama (caso calendario.py, 7/10)")
def _():
    # 6/10: in calendario.py «proponi» era finito dentro il commento dell'import. La prima
    # persona fuori target che prenotava una call avrebbe fatto cadere il giro, e l'avviso
    # a Dre non sarebbe mai nato. Qui si controlla ogni copione, con lo scope vero (revisione
    # 7/10): conta cio' che e' noto al modulo e alla funzione che usa il nome, e ogni uso del
    # nome, non solo le chiamate dirette.
    import ast, pathlib
    qui = pathlib.Path(__file__).resolve().parent
    stanza_f = {n.name for n in ast.parse((qui / "stanza.py").read_text(encoding="utf-8")).body if isinstance(n, ast.FunctionDef)}

    def noti_in(corpo):
        out = set()
        for n in corpo:
            for m in ast.walk(n) if not isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) else [n]:
                if isinstance(m, (ast.Import, ast.ImportFrom)):
                    out |= {(a.asname or a.name).split(".")[0] for a in m.names}
                elif isinstance(m, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                    out.add(m.name)
                elif isinstance(m, ast.Name) and isinstance(m.ctx, ast.Store):
                    out.add(m.id)
        return out

    mancano = []
    for f in sorted(list(qui.glob("*.py")) + list(qui.glob("strumenti/*.py"))):
        if f.name in ("stanza.py", "test_invarianti.py"):
            continue
        t = ast.parse(f.read_text(encoding="utf-8"))
        if any(isinstance(n, ast.ImportFrom) and n.module == "stanza" and any(a.name == "*" for a in n.names) for n in ast.walk(t)):
            continue
        del_modulo = noti_in(t.body)

        def visita(nodo, noti):
            for figlio in ast.iter_child_nodes(nodo):
                if isinstance(figlio, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)):
                    args = figlio.args
                    locali = noti | {a.arg for a in args.args + args.kwonlyargs + args.posonlyargs}
                    if not isinstance(figlio, ast.Lambda):
                        locali |= noti_in(figlio.body) | {m.id for m in ast.walk(figlio) if isinstance(m, ast.Name) and isinstance(m.ctx, ast.Store)}
                        locali |= {(a.asname or a.name).split(".")[0] for m in ast.walk(figlio) if isinstance(m, (ast.Import, ast.ImportFrom)) for a in m.names}
                    visita(figlio, locali)
                elif isinstance(figlio, ast.Name) and isinstance(figlio.ctx, ast.Load) and figlio.id in stanza_f and figlio.id not in noti:
                    mancano.append(f"{f.name}:{figlio.lineno} {figlio.id}")
                else:
                    visita(figlio, noti)
        visita(t, del_modulo)
    assert not mancano, "funzioni della stanza usate e mai importate: " + ", ".join(mancano[:8])


# ── il filo di Smartlead si registra, non si indovina (Dre, 7/10) ──
@prova("il filo vero si prende da enriched.sl_thread, e l'ultima risposta si scegle per DATA (7/10)")
def _():
    import manda as M
    # 1. l'ultima risposta del lead e' la piu' recente per data, non l'ultima della lista.
    #    Smartlead non garantisce l'ordine: prima si citava un messaggio vecchio.
    storia = {"history": [
        {"type": "REPLY", "message_id": "vecchio", "time": "2026-06-01T10:00:00"},
        {"type": "SENT",  "message_id": "nostro",  "time": "2026-07-01T10:00:00"},
        {"type": "REPLY", "message_id": "NUOVO",   "time": "2026-09-30T18:00:00"},
        {"type": "REPLY", "message_id": "mezzo",   "time": "2026-08-15T09:00:00"},
    ]}
    assert M._ultima_sua(storia)["message_id"] == "NUOVO", "l'ultima risposta del lead va scelta per data"
    assert M._ultima_sua({"history": []}) is None, "senza risposte del lead non si inventa un filo"

    # 2. l'ordine dei candidati: prima il filo segnato, poi il CRM, SOLO ALLORA la ricerca per email.
    #    Il 7/10 un lead in piu' campagne poteva ricevere la risposta nel filo di un'altra conversazione.
    chiamate, segnati = [], []
    def finto(metodo, path, *a, **k):
        chiamate.append(path)
        if path.startswith("/leads/"):
            return {"id": 999, "lead_campaign_data": [{"campaign_id": 777, "last_reply_at": "2026-10-01"}]}
        if "/campaigns/111/leads/222/" in path:
            return {"history": [{"type": "REPLY", "message_id": "giusto", "time": "2026-09-01T10:00:00"}]}
        return {"history": []}
    vecchio_sl, vecchio_segna = M._sl_riprova, M._segna_thread
    M._sl_riprova = finto
    M._segna_thread = lambda *a, **k: segnati.append(a)
    try:
        cid, lid, ultima = M.thread({"id": "p1", "email": "x@y.it", "campaign_id": 333, "lead_id": 444,
                                     "enriched": {"sl_thread": {"campaign_id": 111, "lead_id": 222,
                                                                "message_id": "giusto"}}})
    finally:
        M._sl_riprova, M._segna_thread = vecchio_sl, vecchio_segna
    assert (cid, lid) == (111, 222), f"col filo segnato si parte da quello, non dall'email (preso {cid}/{lid})"
    assert ultima["message_id"] == "giusto"
    primo = next((c for c in chiamate if "/leads/" in c or "/campaigns/" in c), "")
    assert "/campaigns/111/leads/222/" in primo, f"il filo segnato va provato PRIMO, invece: {primo}"
    assert not segnati, "se il filo segnato e' ancora valido non lo si riscrive a ogni invio"


# ── la fase 0 del sistema nuovo (8/10): clienti, lock umano, filo intero ──
@prova("fase 0 (v78): chi e' cliente lo dice una tabella, il lock umano e' nello schema, il filo si registra intero (8/10)")
def _():
    v78 = open(os.path.join(os.path.dirname(__file__), "..", "supabase", "schema_v78.sql"), encoding="utf-8").read()
    # 1. la tabella clienti, e il cancello delle proposte la guarda
    assert "create table if not exists clienti" in v78, "manca la tabella clienti"
    assert "e_cliente(new.prospect_id)" in v78, "proposta_ammessa deve guardare anche clienti, non solo stage"
    # 2. il lock umano: un trigger BEFORE UPDATE che rifiuta il ruolo di servizio sui campi decisi
    assert "trg_lock_umano_prospects on prospects" in v78 and "before update" in v78, "il lock umano deve essere un trigger before update"
    assert "e_servizio()" in v78 and "service_role" in v78, "il lock distingue il ruolo di servizio dal token"
    assert "raise exception 'lock umano" in v78, "il lock deve RIFIUTARE, non avvisare"
    assert "'manual'" in v78, "le classificazioni gia' segnate manual dal Workspace restano protette"
    for c in ("classificazione", "stage", "no_followup", "fuori"):
        assert f"'{c}'" in v78, f"il campo {c} deve essere fra i protetti"
    # 3. il filo intero: message_id con indice unico, e il sync che scrive tutto
    assert "message_id" in v78 and "create unique index" in v78, "serve message_id con indice unico per scrivere il filo senza doppioni"
    src = open(os.path.join(os.path.dirname(__file__), "sync_v2.py"), encoding="utf-8").read()
    assert "nostre[-2:]" not in src, "sync_v2 registrava solo le ultime due mail nostre: il filo va scritto intero"
    assert "for m in tutte_nostre" in src and "def _filo_intero" in src, "sync_v2 scrive tutte le nostre, e aspetta v78 senza rompersi"
    # 4. lo schema completo e' allineato (il hook lo pretende, ma qui si dice prima)
    completo = open(os.path.join(os.path.dirname(__file__), "..", "supabase", "schema_completo.sql"), encoding="utf-8").read()
    assert "-- v78" in completo and "trg_lock_umano_prospects" in completo, "schema_completo.sql non contiene v78"


@prova("INT-23 passa il cancello della prima risposta SENZA calendario, e viene fermato se lo mette (9/10)")
def _():
    import prima_risposta as R
    base = {"tipo": "risposta", "titolo": "Bozza", "azione": {
        "intento": "INT-23", "lettura": {"coerenza": "COERENTE"},
        "bozza": "Salve,\nVa bene perfetto, vi inoltro qui l'analisi che abbiamo fatto sulla vostra azienda.\nRestiamo a disposizione.\nA presto,"}}
    motivi = R.perche_no(base, None)
    assert not any("calendario" in m for m in motivi), f"INT-23 senza calendario veniva bocciato: {motivi}"
    con = {**base, "azione": {**base["azione"], "bozza": base["azione"]["bozza"] + "\n📅 https://calendar.app.google/x"}}
    assert any("INT-23 non deve spingere il calendario" in m for m in R.perche_no(con, None)), "INT-23 col calendario deve fermarsi"
    int01 = {**base, "azione": {**base["azione"], "intento": "INT-01"}}
    assert any("non lascia il calendario" in m for m in R.perche_no(int01, None)), "INT-01 senza calendario resta bocciato"


@prova("il numero del mercato: uno solo, pulito dal portale, uguale in mail, analisi e no gentili (12/10)")
def _():
    import mercato as M, seguiti as S, analisi_auto as A
    # 1. niente parole generiche: le agenzie di Milano non sono un milione (era 1.345.300, «immobiliare» = il portale)
    n = M.domanda("agenzie_immobiliari", "Milano")[0]
    assert 10000 < n < 100000, f"Milano agenzie: {n}"
    frase = M.dato_forte("serramenti", "Milano")[0]
    assert frase and "ricerche al mese di persone che cercano" in frase, "si dice «ricerche», non «persone»: una persona ne fa piu' d'una"
    # 14/10: alle agenzie il numero di chi compra non si da' (vogliono chi vende)
    assert M.dato_forte("agenzie_immobiliari", "Milano")[0] is None, "alle agenzie il numero di chi cerca casa"
    # 2. i nomi del fit trovano la base; il mestiere stretto prende solo la sua parola
    assert M.dato_forte("fotovoltaico", "Torino")[0], "fotovoltaico (fit) deve trovare fotovoltaico_casa (base)"
    pb = M.dato_forte("porte_blindate", "Roma")[1]
    tot = M.domanda("serramenti", "Roma")[0]
    assert pb < tot, f"porte blindate {pb} non puo' essere il totale dei serramenti {tot}"
    # 3. senza dato, nessun numero (un settore fuori dalla base, una provincia che non e' italiana)
    assert M.dato_forte("altro", "Milano")[0] is None and M.dato_forte("agenzie_immobiliari", "London")[0] is None
    # 4. la mail dei si': il numero dal codice, la riga del potenziale, niente «pero'» ne' segnaposto
    vero = __import__("bozze").template_verbatim()
    p = {"name": "", "sector": "serramenti", "city": "Bologna", "enriched": {}}
    t = S.risposta("INT-01", p, {}, "https://cal/x", giorno="martedì 13 ottobre alle 15:30", testo_file=vero, garanzia=False)
    assert t and M.dato_forte("serramenti", "Bologna")[0] in t, "la mail dei si' deve portare il dato forte"
    ag = S.risposta("INT-01", {"name": "", "sector": "agenzie_immobiliari", "city": "Bologna", "enriched": {}}, {}, "https://cal/x",
                    giorno="martedì 13 ottobre alle 15:30", testo_file=vero, garanzia=False)
    assert ag and "cercano casa" not in ag and "ricerche al mese" not in ag, "a un'agenzia il numero di chi compra (14/10)"
    assert "su chi vuole vendere casa o farla valutare nella provincia di Bologna" in ag, "la mail dell'agenzia dice a chi parla l'analisi"
    fatti = A.fatti_in_testo({"raccolta": {}, "ultime": [], "fit": {"settore": "agenzie_immobiliari"}, "dominio": "x.it", "provincia": "Bologna",
                              "volumi": A.volumi("agenzie_immobiliari", "Bologna")}, {"company": "X"})
    assert "chi COMPRA" in fatti and "solo chi cerca davvero il servizio" not in fatti, "l'analisi deve sapere che quel numero e' chi compra"
    assert "Pensiamo possa essere un canale molto interessante" in t and "però è centrata" not in t and "vasto range" not in t
    assert "{{" not in t and "[" not in t
    senza = S.risposta("INT-01", {"name": "", "sector": "altro", "city": "Pesaro", "enriched": {}}, {}, "https://cal/x",
                       giorno="martedì 13 ottobre alle 15:30", testo_file=vero, garanzia=False)
    assert senza and "su Google. Pensiamo possa essere" in senza and "ricerche al mese" not in senza, "senza dato: la riga senza numero"
    # 5. l'analisi riceve lo stesso numero, senza il portale
    v = A.volumi("agenzie_immobiliari", "Milano")
    assert v["tam"] == M.domanda("agenzie_immobiliari", "Milano")[0] and not any(x["k"] == "immobiliare" for x in v["top"])



@prova("la provincia si riconosce da nome, sigla e comune, e la base le ha tutte (12/10)")
def _():
    import mercato as M
    casi = {"Pesaro": "Pesaro e Urbino", "MI": "Milano", "Roma (RM)": "Roma", "Carbonia": "Sud Sardegna",
            "Rovereto": "Trento", "Monza": "Monza e della Brianza", "Verbania": "Verbano-Cusio-Ossola",
            "Provincia della Spezia": "La Spezia", "Spezia": "La Spezia", "Bolzano - Alto Adige": "Bolzano/Bozen",
            "None": None, "": None, "London": None}
    for t, atteso in casi.items():
        assert M.provincia(t) == atteso, f"{t!r} -> {M.provincia(t)!r}, atteso {atteso!r}"
    # le 107 province per i settori della base: un si' di Siracusa o di Pesaro riceve il numero
    for st in ("serramenti", "agenzie_immobiliari", "fotovoltaico_casa", "pompe_calore_casa"):
        manca = [p for p in json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "province_it.json")))["province"]
                 if not M.voce(st, p)]
        assert not manca, f"{st}: mancano {len(manca)} province nella base ({manca[:5]})"
    frase = M.dato_forte("serramenti", "Reggio Emilia")[0]
    assert frase and frase.startswith("nella provincia di Reggio Emilia"), frase
    # mail e analisi scelgono la stessa provincia
    p = {"sector": "serramenti", "city": "Carbonia", "enriched": {"google_fit": {"settore": "serramenti", "provincia": ""}}}
    assert M.settore_e_provincia(p) == ("serramenti", "Sud Sardegna")
    assert "settore_e_provincia(p)" in open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "analisi_auto.py")).read()


@prova("l'Ispettore guarda e non tocca, e riconosce i guasti veri senza falsi allarmi (12/10)")
def _():
    import ispettore as I
    src = open(I.__file__).read()
    corpo_sl = src[src.index("def sl("):src.index("def campagne_attive")]
    assert "method" not in corpo_sl and "data=" not in corpo_sl, "su Smartlead l'Ispettore fa solo GET: le campagne le tocca Dre"
    assert src.count("server.smartlead.ai") == 1, "un solo punto che parla con Smartlead"
    # testi rotti: si', le sigle no
    for o, t in [("Analisi marketing su ", "x"), ("Ok", "ho dato un occhiata a , notando"), ("Ciao {{first_name}}", "x"), ("x", "Gentile None,")]:
        assert I.testo_rotto(o, t), f"doveva vedere il guasto: {o!r} {t!r}"
    for o, t in [("Analisi marketing per A.R. Living", "x"), ("x", "le campagne di C.D.A. Tecnologie"), ("x", "grazie a voi, a presto")]:
        assert not I.testo_rotto(o, t), f"falso allarme: {o!r} {t!r} -> {I.testo_rotto(o, t)}"
    # chi non doveva ricevere la sequenza
    ieri = (I.ADESSO - I.datetime.timedelta(days=1)).isoformat()
    adesso = I.ADESSO.isoformat()
    per = {"c@cliente.example": {"id": 1, "company": "C", "_cliente": True},
           "p@pipe.example": {"id": 2, "company": "P", "_cliente": False, "stage": "call_fissata"},
           "n@no.example": {"id": 3, "company": "N", "_cliente": False, "classificazione": "negativo"},
           "r@risp.example": {"id": 4, "company": "R", "_cliente": False, "last_reply_at": ieri},
           "ok@ok.example": {"id": 5, "company": "OK", "_cliente": False}}
    righe = [{"lead_email": m, "sent_time": adesso, "sequence_number": 2, "_campagna": "X", "_cid": 1,
              "email_subject": "Analisi marketing su Azienda", "email_message": "Buongiorno", "stats_id": m}
             for m in list(per) + ["collega@cliente.example"]]
    gravi, attenzione = I.controlla_sequenze(righe, per, {"cliente.example"}, I.ADESSO - I.datetime.timedelta(hours=2))
    g = " ".join(t for _, t in gravi)
    assert "CLIENTE" in g and "stessa azienda di un cliente" in g and "pipeline" in g and "detto no" in g, g
    assert any("DOPO che aveva risposto" in t for _, t in attenzione)
    assert not any("OK" == t.split(":")[0] for _, t in gravi + attenzione), "il lead pulito non va segnalato"
    wf = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".github", "workflows", "ispettore.yml")).read()
    assert "schedule" in wf and "contents: read" in wf and "scripts/ispettore.py" in wf


@prova("il Manuale di Clara applicato (12/10): niente indirizzi di lead nel repo, niente DELETE su Smartlead, festività, privacy, regole")
def _():
    import re, subprocess, datetime as dt
    radice = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    # 1. il repo e' pubblico: nessun indirizzo di lead nei file versionati (divieto 20)
    EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)*\.[a-z]{2,}")
    NOSTRI = re.compile(r"studiogalilei|galileistudio|galilei|esempio|example|\.invalid|noreply|anthropic|supabase|github|vercel|google|"
                        r"gserviceaccount|stripe|smartlead|openai|sentry|w3\.org|schema\.org|carlo\.dprogetti|@x\.it|@y\.it|@b\.it|"
                        r"@x\.com|altro-dominio|@cliente\.|@no\.|@ok\.|@pipe\.|@risp\.|@\d+x\b|@acme\.|@azienda\.it|mario\.b1980", re.I)
    file = subprocess.run(["git", "ls-files"], cwd=radice, capture_output=True, text=True).stdout.split()
    sporchi = {}
    for f in file:
        if re.search(r"\.(png|jpe?g|gif|pdf|woff2?|ico|zip|lock|mjs)$|package-lock|^\.agents/|OFL\.txt$", f):
            continue
        try:
            t = open(os.path.join(radice, f), encoding="utf-8", errors="ignore").read()
        except OSError:
            continue
        trovati = [e for e in EMAIL.findall(t) if not NOSTRI.search(e)]
        if trovati:
            sporchi[f] = len(trovati)
    assert not sporchi, f"indirizzi che sembrano di lead nel repo pubblico: {sporchi}"
    # 2. mai DELETE su Smartlead: si mette in pausa (divieto 16, il 24/9 la cancellazione ha tolto i thread)
    for f in file:
        if f.startswith("scripts/") and f.endswith(".py") and f != "scripts/test_invarianti.py":
            t = open(os.path.join(radice, f), encoding="utf-8", errors="ignore").read()
            assert not re.search(r"\bsl\(\s*[\"']DELETE", t), f"{f}: DELETE su Smartlead"
    # 3. il giorno proposto salta le festività (01 C, giorni_esclusi)
    import bozze
    assert bozze.festivo(dt.date(2026, 12, 8)) and bozze.festivo(dt.date(2027, 3, 29)) and not bozze.festivo(dt.date(2026, 12, 9))
    # 4. il freno «non contattare» non scatta sul disclaimer privacy (gesto 13)
    import cervello
    d = cervello.DOMANDE["non_contattare"]
    assert "cita la privacy" not in d and "NON contano" in d, d
    # 5. le regole del documento 01 stanno nel database, una per riga
    from stanza import sb
    rr = sb("GET", "/rest/v1/regole?select=chiave,stato&limit=200") or []
    chiavi = {r["chiave"] for r in rr}
    assert {"calendario", "budget_giorno", "followup_1", "archiviato_per_silenzio", "finestra_si"} <= chiavi, sorted(chiavi)[:10]
    # 6. una risposta svuota la coda dei follow-up (trigger v80)
    v80 = open(os.path.join(radice, "supabase", "schema_v80.sql")).read()
    assert "svuota_coda_se_scrive" in v80 and "new.coda := null" in v80


@prova("i filtri del manuale su Smartlead: dodici nomi, stesse protezioni di prima, il follow-up ha il suo (12/10)")
def _():
    import categorie_smartlead as C
    N = C.categoria_nuova
    assert len(C.NUOVE) == len(set(C.NUOVE)) == 12
    assert C.N_SI == "Analisi" and C.N_CALL == "Conoscitiva" and C.N_FU == "Follow-up"
    assert N({"classificazione": "positivo", "stage": "in_follow_up"}) == C.N_FU, "chi ha avuto il follow-up sta in Follow-up"
    assert N({"classificazione": "positivo"}) == C.N_SI and N({"classificazione": "positivo"}, intento="INT-02") == C.N_CALL_CHIESTA
    assert N({"classificazione": "tiepido"}) == C.N_DRE and N({"classificazione": "positivo"}, intento="INT-03") == C.N_DRE
    assert N({"classificazione": "rinvio"}) == C.N_AVANTI and N({"classificazione": "ooo"}) == C.N_OOO
    assert N({"classificazione": "negativo"}) == C.N_NO and N({"classificazione": "soppresso"}) == C.N_STOP
    assert N({"classificazione": "fuori_target"}) == C.N_FUORI
    assert N({"classificazione": "da_classificare"}, testo="Delivery has failed to these recipients") == C.N_MORTA
    assert N({"classificazione": "persona_sbagliata"}) == C.N_GIRATO
    # le protezioni del 6/10 restano: pipeline senza call no; la call vince tranne soppressi e persi
    assert N({"classificazione": "positivo", "fuori": True}) is None
    assert N({"classificazione": "negativo"}, call=True) == C.N_CALL and N({"classificazione": "soppresso"}, call=True) == C.N_STOP
    assert N({"classificazione": "negativo", "fuori": True, "pipeline_stage": "perso"}, call=True) is None
    assert N({"classificazione": "positivo"}, testo="grazie ma non ci interessa") is None, "un si' con un no scritto non si etichetta"
    # un'etichetta nostra non torna indietro come classe (niente giro chiuso col sync)
    import sync_v2
    assert not set(C.NUOVE) & set(sync_v2.CAT_HINT), "il sync non deve leggere le categorie del manuale come classi"


@prova("chi prenota la conoscitiva si riconosce anche dal sito scritto nel modulo (12/10)")
def _():
    import calendario as K
    P = {"email": {}, "dominio": {}, "aziende": [], "conta": {}, "nomi": set(),
         "sito": {"rossi-ferramenta.it": "p1"}}
    ev = {"titolo": "Chiamata Conoscitiva Studiogalilei - (Mario Rossi)", "invitati": ["lead1@esempio.invalid"],
          "descrizione": "Prenotato da<br>Mario Rossi<br>lead1@esempio.invalid<br>Sito web<br>https://www.rossi-ferramenta.it/<br>"
                         "Partecipa con Google Meet: https://meet.google.com/abc-defg-hij"}
    assert K.riconosci(ev, P) == ("p1", "sito"), K.riconosci(ev, P)
    # un evento che non e' una call non si aggancia dal sito
    assert K.riconosci({**ev, "titolo": "Pranzo"}, P) == (None, None)
    # Meet, Google e le mail non sono siti
    assert K.siti_nella_descrizione(ev["descrizione"]) == ["rossi-ferramenta.it"]


@prova("chi chiede di sentirsi passa a Dre: mai la risposta automatica col nostro giorno (12/10)")
def _():
    import prima_risposta as R
    import categorie_smartlead as C
    assert not set(R.INTENTI_CALL) & set(R.INTENTI_OK), "una richiesta di call partirebbe da sola"
    assert set(R.INTENTI_CALL) == set(C.INTENTI_CALL), "prima risposta e filtri devono dire la stessa cosa"
    assert C.categoria_nuova({"classificazione": "positivo"}, intento="INT-02") == "Vuole sentirti"


@prova("la posta legge solo la casella di Dre (12/10)")
def _():
    import posta as P
    import stanza
    vero = P.sb
    P.sb = lambda *a, **k: [{"email": e, "user_id": "u", "scopes": "gmail.readonly"} for e in
                            ("dramane@studiogalilei.com", "collega@studiogalilei.com", "altro@studiogalilei.com")]
    try:
        assert [r["email"] for r in P.caselle()] == ["dramane@studiogalilei.com"]
        assert P.caselle("collega@studiogalilei.com") == []
    finally:
        P.sb = vero


@prova("una risposta gia' letta non si ripaga: la memoria delle letture sta nel database (13/10)")
def _():
    import cervello as C
    import tempfile
    salvato, chiamate = {}, []
    vero = (C._dal_db, C._nel_db, C._chiedi_openai, C.CACHE, C._CACHE_VIVA)
    C._dal_db = lambda chiavi: {k: salvato[k] for k in chiavi if k in salvato}
    C._nel_db = lambda nuove: salvato.update(nuove)
    def finto(*a, **k):
        chiamate.append(1)
        return '{' + ", ".join(f'"{d}": 0.9' if d == "vuole_analisi" else f'"{d}": 0.0' for d in C.DOMANDE) + ', "rinvio_quando": "", "girato_a": [], "domanda": "", "perche": "x"}'
    C._chiedi_openai = finto
    try:
        for giro in range(2):                     # due runner nuovi del cloud: file vuoto ogni volta
            C.CACHE = tempfile.mktemp(suffix=".json")
            C._CACHE_VIVA = None
            assert C.classifica_risposta("mandi pure l'analisi, grazie", modello="gpt-5")["vuole_analisi"] == 0.9
        assert len(chiamate) == 1, f"la stessa risposta pagata {len(chiamate)} volte"
    finally:
        C._dal_db, C._nel_db, C._chiedi_openai, C.CACHE, C._CACHE_VIVA = vero


@prova("niente giri pagati in tondo: regola unica con schede parziali, Google Fit a tentativi, Revisore che ricorda (13/10)")
def _():
    import stanza as St
    vero_sb = St.sb
    # una scheda parziale (senza no_followup) non deve passare per contattabile
    St.sb = lambda m, path, *a, **k: ([{"fuori": False, "stage": "in_follow_up", "pipeline_stage": None,
                                        "no_followup": True, "classificazione": "positivo"}]
                                       if path.startswith("/rest/v1/prospects") else False)
    try:
        assert St.contattabile({"id": "x", "classificazione": "positivo"}) is False, "una scheda parziale passa la regola"
    finally:
        St.sb = vero_sb
    # un cliente della tabella clienti non e' contattabile anche se i campi del lead non lo dicono
    St.sb = lambda m, path, *a, **k: (True if "e_cliente" in path else [])
    try:
        assert St.contattabile({"id": "x", "fuori": False, "stage": "nuovo", "pipeline_stage": None,
                                "no_followup": False, "classificazione": None}) is False
    finally:
        St.sb = vero_sb
    import pathlib
    g = pathlib.Path(__file__).with_name("googlefit.py").read_text(encoding="utf-8")
    assert "tentativi" in g and ">= 3" in g, "Google Fit deve smettere dopo tre tentativi su un sito che non si scarica"
    r = pathlib.Path(__file__).with_name("revisore.py").read_text(encoding="utf-8")
    assert "_dal_db" in r and "ref=ref_piano" in r, "il Revisore deve ricordare il giudizio e fare una card sola per piano"
    b = pathlib.Path(__file__).with_name("bozze.py").read_text(encoding="utf-8")
    assert "if not contattabile(p):" in b and "la bozza non e' nata" in b, "le bozze devono chiedere alla regola prima di pagare"


# ── il segnale provvisorio (14/10): scrive solo a Dre, una volta sola, mai ai clienti ──
class _SegnaleFinto:
    """Un database finto e stateful per segnale_provvisorio: risposte, scheda, segnali, memoria
    delle letture, Gmail. Si aggiungono risposte tra un giro e l'altro con `scrive`."""

    def __init__(self, scheda, letture, servito=False, memoria_rotta=False, gmail=None, n_aziende=1):
        self.ora = datetime.datetime.now(datetime.timezone.utc)
        self.scheda, self.letture, self.servito = scheda, letture, servito
        self.memoria_rotta, self.gmail = memoria_rotta, gmail      # gmail: None=ok, "no"=Google 500, "timeout"
        self.risposte, self.segnati, self.memoria, self.mail, self.ai, self.avvisi = [], [], {}, [], [], []
        self.uso, self.inviate, self.n_aziende = 0, [], n_aziende
        self.notifiche, self.push_rotta = [], False

    def scrive(self, testo, minuti_fa=60, pid="p1"):
        at = (self.ora - datetime.timedelta(minutes=minuti_fa)).strftime("%Y-%m-%dT%H:%M:%S+00:00")
        self.risposte.append({"id": f"i{len(self.risposte) + 1}", "prospect_id": pid, "at": at, "created_at": at, "body": testo})

    def sb(self, m, path, corpo=None, *a, **k):
        import re as _re
        if path.startswith("/rest/v1/interactions") and "kind=eq.email_in" in path:
            return [dict(r) for r in self.risposte]
        if path.startswith("/rest/v1/interactions"):
            return [{"id": "o1", "at": self.ora.strftime("%Y-%m-%dT%H:%M:%S+00:00")}] if self.servito else []
        if path.startswith("/rest/v1/proposte") or path.startswith("/rest/v1/uso_modelli"):
            return []
        if path.startswith("/rest/v1/segnali_provvisori"):
            if m == "GET" and "come=eq.incerto" in path:
                return [dict(x) for x in self.segnati if x.get("come") == "incerto"]
            if m == "GET":
                return [dict(x) for x in self.segnati]
            if m == "POST":
                fatti = []
                for r in corpo:
                    if not any((x["prospect_id"], x["tipo"]) == (r["prospect_id"], r["tipo"]) or x["interaction_id"] == r["interaction_id"]
                               for x in self.segnati):
                        x = {**r, "quando": self.ora.strftime("%Y-%m-%dT%H:%M:%S+00:00")}
                        self.segnati.append(x)
                        fatti.append(dict(x))
                return fatti
            iid = _re.search(r"interaction_id=eq\.([^&]+)", path).group(1)
            if m == "DELETE":
                self.segnati[:] = [x for x in self.segnati if x["interaction_id"] != iid]
            if m == "PATCH":
                for x in self.segnati:
                    if x["interaction_id"] == iid:
                        x.update(corpo)
            return None
        if path.startswith("/rest/v1/prospects"):
            return [{"id": f"p{n}", "company": f"Azienda Finta {n}", "name": "Mario", "email": "m@finta.invalid", **self.scheda}
                    for n in range(1, self.n_aziende + 1)]
        if "e_cliente" in path:
            return self.scheda.get("_cliente", False)
        if path.startswith("/rest/v1/memoria_letture"):
            if self.memoria_rotta:
                if m == "POST":
                    raise RuntimeError("500 memoria rotta")
                return []
            if m == "GET":
                c = path.split("chiave=eq.")[1]
                return [{"valore": self.memoria[c]}] if c in self.memoria else []
            for r in corpo:
                self.memoria[r["chiave"]] = r["valore"]
            return None
        return None

    def chiedi(self, prompt):
        self.ai.append(prompt)
        for chiave, v in self.letture.items():
            if chiave in prompt:
                if v is None:
                    raise RuntimeError("OpenAI 429: insufficient_quota")
                return json.dumps(v)
        return json.dumps({"autorisposta": False, "caldo": False, "si": False, "frase": "", "telefono": "", "consiglio": ""})

    def manda(self, grezzo):
        if self.gmail == "no":
            raise RuntimeError("Google 500 su https://gmail.googleapis.com: backend error")
        if self.gmail == "timeout":
            self.inviate.append(grezzo)                          # Gmail la consegna, ma la risposta si perde
            raise TimeoutError("The read operation timed out")
        self.mail.append(grezzo)
        return {"id": "x"}

    def inviata(self, oggetto, dal):
        import base64
        import email
        from email.header import decode_header, make_header
        for g in self.inviate:
            m = email.message_from_bytes(base64.urlsafe_b64decode(g))
            if str(make_header(decode_header(m["Subject"]))) == oggetto:
                return True
        return False

    def giro(self):
        import segnale_provvisorio as S
        import stanza as St
        vero = (S.sb, St.sb, S._chiedi_ai, S._gmail_send, S._gmail_inviata, S._avvisa, S._push)
        S.sb = St.sb = self.sb
        S._chiedi_ai, S._gmail_send, S._gmail_inviata = self.chiedi, self.manda, self.inviata
        S._avvisa = self.avvisi.append
        S._push = self.push
        try:
            self.segnali = S.giro(ore=24, prova=False)
            return [s["tipo"] for s in self.segnali]
        except SystemExit:
            return "uscito"
        finally:
            S.sb, St.sb, S._chiedi_ai, S._gmail_send, S._gmail_inviata, S._avvisa, S._push = vero

    def push(self, titolo, testo, url, tag):
        if self.push_rotta:
            raise RuntimeError("push.apple.com 500: servizio giu'")
        self.notifiche.append({"titolo": titolo, "testo": testo, "url": url, "mail_prima": len(self.mail)})
        return 1


SCHEDA_LEAD = {"fuori": False, "stage": "risposto", "pipeline_stage": None, "no_followup": False, "classificazione": "positivo"}
CALDO = {"autorisposta": False, "caldo": True, "si": True, "frase": "mi chiami domani", "telefono": "333 1234567", "consiglio": ""}
SI = {**CALDO, "caldo": False, "telefono": "", "frase": "la mail e' corretta"}


@prova("segnale provvisorio: il destinatario e' solo Dre, qualunque altro indirizzo si ferma prima di Gmail")
def _():
    import base64
    import email
    import segnale_provvisorio as S
    partite = []
    vero = S._gmail_send
    S._gmail_send = lambda grezzo: partite.append(grezzo)
    try:
        for altro in ("m@finta.invalid", "lorenzo@studiogalilei.com", "dramane@studiogalilei.com, m@finta.invalid", "", None):
            try:
                S.manda_mail(altro, "x", "x", "<p>x</p>")
                raise AssertionError(f"ha accettato {altro!r}")
            except ValueError:
                pass
        assert partite == [], "una mail e' partita verso un destinatario che non e' Dre"
        S.manda_mail("dramane@studiogalilei.com", "Vuole sentirti: X\nBcc: m@finta.invalid", "t", "<p>t</p>")
        m = email.message_from_bytes(base64.urlsafe_b64decode(partite[0]))
        assert m["To"] == "dramane@studiogalilei.com" and not m["Cc"] and not m["Bcc"], (m["To"], m["Cc"], m["Bcc"])
    finally:
        S._gmail_send = vero
    t = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "segnale_provvisorio.py"), encoding="utf-8").read()
    assert t.count("_gmail_send(") == 2, "Gmail si chiama solo da manda_mail"
    assert "messages/send" not in t.split("def _gmail_send")[0] and t.count("messages/send") == 1, "una sola strada che manda"


@prova("segnale provvisorio: un caldo produce un segnale una volta sola, col numero cliccabile")
def _():
    import base64
    import email
    import segnale_provvisorio as S
    f = _SegnaleFinto(SCHEDA_LEAD, {"mi chiami domani": CALDO})
    f.scrive("Buongiorno, mi chiami domani al 333 1234567")
    assert f.giro() == ["caldo"] and f.mail == [] and len(f.segnati) == 1, (f.mail, f.segnati)
    # 20/10 sera: il caldo non e' piu' una mail (e' la notifica + «Da chiamare»); il testo resta per --prova-mail
    _, _, corpo = S.componi(f.segnali)
    assert "tel:+393331234567" in corpo and "master-inbox" in corpo, corpo[:300]
    assert f.giro() == [] and len(f.segnati) == 1, "lo stesso caldo e' stato segnalato due volte"
    f.scrive("Mi richiami pure domani mattina, mi chiami domani", minuti_fa=2)  # un secondo caldo: niente segnale nuovo
    assert f.giro() == [] and len(f.segnati) == 1 and f.mail == [], "due caldi dello stesso lead hanno fatto due segnali"


@prova("segnale provvisorio: un lead gia' segnalato come si' che poi chiede di essere chiamato arriva come caldo")
def _():
    f = _SegnaleFinto(SCHEDA_LEAD, {"La mail e' corretta": SI, "mi chiami domani": CALDO})
    f.scrive("La mail e' corretta", minuti_fa=60)
    assert f.giro() == ["si"] and len(f.segnati) == 1 and f.mail == []
    f.scrive("Buongiorno, mi chiami domani al 333 1234567", minuti_fa=1)
    assert f.giro() == ["caldo"] and len(f.segnati) == 2, "il caldo dopo un si' si e' perso"
    assert f.giro() == [] and len(f.segnati) == 2 and f.mail == []
    # al contrario, un si' dopo il caldo non suona: il caldo l'ha gia' portato a Dre
    f = _SegnaleFinto(SCHEDA_LEAD, {"La mail e' corretta": SI, "mi chiami domani": CALDO})
    f.scrive("Buongiorno, mi chiami domani al 333 1234567", minuti_fa=60)
    assert f.giro() == ["caldo"]
    f.scrive("La mail e' corretta", minuti_fa=30)
    assert f.giro() == [] and len(f.segnati) == 1, "un si' dopo il caldo ha fatto un secondo segnale"


@prova("segnale provvisorio: due risposte tra un giro e l'altro si leggono tutte, vince il caldo")
def _():
    f = _SegnaleFinto(SCHEDA_LEAD, {"mi chiami domani": CALDO, "quanto costa": {**SI, "si": False}})
    f.scrive("Buongiorno, mi chiami domani al 333 1234567", minuti_fa=9)
    f.scrive("Ah, e quanto costa?", minuti_fa=4)
    assert f.giro() == ["caldo"] and f.mail == [] and len(f.ai) == 2, (len(f.mail), len(f.ai))
    # un caldo e poi un si' che il sistema ha gia' servito: il caldo resta
    f = _SegnaleFinto(SCHEDA_LEAD, {"mi chiami domani": CALDO, "La mail e' corretta": SI}, servito=True)
    f.scrive("Buongiorno, mi chiami domani al 333 1234567", minuti_fa=9)
    f.scrive("La mail e' corretta", minuti_fa=4)
    assert f.giro() == ["caldo"] and f.mail == []


@prova("segnale provvisorio: un cliente, chi e' in pipeline o soppresso non produce segnali (e non si paga la lettura)")
def _():
    for scheda in ({**SCHEDA_LEAD, "_cliente": True}, {**SCHEDA_LEAD, "fuori": True, "pipeline_stage": "conoscitiva"},
                   {**SCHEDA_LEAD, "classificazione": "soppresso"}, {**SCHEDA_LEAD, "stage": "cliente"}):
        f = _SegnaleFinto(scheda, {"mi chiami": CALDO})
        f.scrive("Mi chiami domani al 333 1234567")
        assert f.giro() == [] and f.mail == [] and f.segnati == [] and f.ai == [], scheda


@prova("segnale provvisorio: senza AI c'e' comunque il segnale («da guardare»), e non si ripaga al giro dopo")
def _():
    f = _SegnaleFinto(SCHEDA_LEAD, {"valutiamo": None})
    f.scrive("Buongiorno, valutiamo volentieri")
    assert f.giro() == ["da_guardare"] and f.mail == [] and len(f.segnati) == 1
    assert f.giro() == [] and len(f.ai) == 1 and f.mail == [], "una lettura fallita si e' ripagata o rimandata"
    # AI ferma e Gmail ferma insieme: la lettura fallita si ricorda, non si ripaga a ogni giro
    # (20/10 sera: senza mail di giornata, Gmail ferma non tocca il segnale)
    f = _SegnaleFinto(SCHEDA_LEAD, {"valutiamo": None}, gmail="no")
    f.scrive("Buongiorno, valutiamo volentieri")
    assert [f.giro() for _ in range(4)] == [["da_guardare"], [], [], []] and len(f.segnati) == 1
    assert len(f.ai) == 1, f"con AI e Gmail ferme la lettura si e' pagata {len(f.ai)} volte"
    assert f.avvisi == [] and f.mail == [], (f.avvisi, f.mail)


@prova("segnale provvisorio: un si' aspetta 10 minuti, e se l'abbiamo gia' servito tace")
def _():
    f = _SegnaleFinto(SCHEDA_LEAD, {"corretta": SI})
    f.scrive("La mail e' corretta", minuti_fa=3)
    assert f.giro() == [] and f.mail == [], "un si' di 3 minuti fa non deve ancora suonare"
    f = _SegnaleFinto(SCHEDA_LEAD, {"corretta": SI}, servito=True)
    f.scrive("La mail e' corretta")
    assert f.giro() == [] and f.mail == [], "un si' gia' servito ha suonato"
    f = _SegnaleFinto(SCHEDA_LEAD, {"corretta": SI})
    f.scrive("La mail e' corretta")
    assert f.giro() == ["si"] and len(f.segnati) == 1 and f.mail == []


@prova("segnale provvisorio: la spesa ha un tetto per giro, e con la memoria rotta smette di pagare")
def _():
    import segnale_provvisorio as S
    f = _SegnaleFinto(SCHEDA_LEAD, {"mi chiami": CALDO}, n_aziende=15)
    for n in range(1, 16):
        f.scrive(f"Mi chiami pure, sono il numero {n}", minuti_fa=n, pid=f"p{n}")
    f.giro()
    assert len(f.ai) == S.PAGATE_PER_GIRO, f"un giro ha pagato {len(f.ai)} letture"
    f.giro()
    assert len(f.ai) == 15, "le letture rimandate non sono state fatte al giro dopo"
    f = _SegnaleFinto(SCHEDA_LEAD, {"no grazie": {**SI, "si": False}}, memoria_rotta=True, n_aziende=3)
    for n in range(1, 4):
        f.scrive(f"No grazie, non ci interessa ({n})", pid=f"p{n}")
    primo = f.giro()
    for _ in range(4):
        f.giro()
    assert f.ai == [] and f.avvisi, f"con la memoria rotta: {len(f.ai)} letture in 5 giri, avvisi {f.avvisi}"
    assert primo == ["da_guardare"] or primo == ["da_guardare"] * 3, f"con la memoria rotta nessun segnale: {primo}"
    # senza poter leggere la memoria non si paga affatto
    f = _SegnaleFinto(SCHEDA_LEAD, {}, n_aziende=1)
    f.scrive("No grazie")
    vero = f.sb
    def rotta(m, path, *a, **k):
        if path.startswith("/rest/v1/memoria_letture") and m == "GET" and "segnale:avviso" not in path:
            raise RuntimeError("500")
        return vero(m, path, *a, **k)
    f.sb = rotta
    assert f.giro() == ["da_guardare"] and f.ai == [], "senza memoria leggibile ha pagato una lettura, o ha taciuto"
    # il tetto del giorno: oltre, «da guardare» senza pagare
    f = _SegnaleFinto(SCHEDA_LEAD, {"mi chiami": CALDO})
    f.scrive("Mi chiami domani al 333 1234567")
    vero2 = f.sb
    f.sb = lambda m, path, *a, **k: ([{"id": n} for n in range(S.PAGATE_AL_GIORNO + 1)]
                                     if path.startswith("/rest/v1/uso_modelli") else vero2(m, path, *a, **k))
    assert f.giro() == ["da_guardare"] and f.ai == [] and f.avvisi, "oltre il tetto del giorno ha pagato o taciuto"


@prova("segnale provvisorio: Gmail ferma o lenta non tocca i segnali di giornata, che non sono piu' mail (20/10 sera)")
def _():
    f = _SegnaleFinto(SCHEDA_LEAD, {"mi chiami": CALDO}, gmail="timeout")
    f.scrive("Buongiorno, mi chiami domani al 333 1234567")
    assert f.giro() == ["caldo"] and f.inviate == [] and f.mail == []
    assert [x["come"] for x in f.segnati] == ["segnale"], f.segnati
    f.gmail = None
    assert f.giro() == [] and f.mail == [], "il caldo e' stato segnalato due volte"
    f = _SegnaleFinto(SCHEDA_LEAD, {"mi chiami": CALDO}, gmail="no")
    f.scrive("Buongiorno, mi chiami domani al 333 1234567")
    assert f.giro() == ["caldo"] and len(f.segnati) == 1 and len(f.ai) == 1 and f.avvisi == []


@prova("segnale provvisorio: una partita IVA non e' un telefono, un fisso vero si'")
def _():
    import segnale_provvisorio as S
    assert S.telefono_nel_testo("Sono fuori ufficio fino al 20. P.IVA 01234567890") == ""
    assert S.telefono_nel_testo("Mario Rossi srl - Partita IVA: IT 01234567890 - C.F. 01234567890") == ""
    assert S.automatica("Sono fuori ufficio fino al 20/10, rientro lunedi'. P.IVA 01234567890")
    assert S.telefono_nel_testo("Rossi srl, P. IVA 34512345678, Treviso") == ""
    assert S.telefono_nel_testo("cod. fiscale 34512345678 - cell 333 7654321") == "333 7654321"
    assert S.telefono_nel_testo("mi chiami allo 0422 1847161") == "0422 1847161"
    assert S.telefono_nel_testo("cell. 333 1234567") == "333 1234567"


@prova("segnale provvisorio: --prova-mail insieme a --prova si rifiuta (manderebbe davvero)")
def _():
    import segnale_provvisorio as S
    vero = sys.argv
    sys.argv = ["segnale_provvisorio.py", "--prova", "--prova-mail"]
    try:
        S.main()
        raise AssertionError("--prova --prova-mail e' partito")
    except SystemExit as e:
        assert "prova-mail" in str(e.code), e.code
    finally:
        sys.argv = vero


# ── le prenotazioni delle call (14/10): la scheda a Dre, una volta sola, la mattina di nuovo ──
_ROMA = zoneinfo.ZoneInfo("Europe/Rome")
_FIRMA = ("Buongiorno Lorenzo,\nvolentieri, ci sentiamo in call.\nCordiali saluti\nMario Rossi\nDirettore commerciale\n"
          "Rossi Finta srl - P.IVA 01234567890\nTel. 0422 123456 - Cell. 333 1234567\nFax 0422 654321")


class _PrenotazioniFinte:
    """Calendario, posta e database finti per il giro delle prenotazioni. Ogni giro ha il suo orologio."""

    def __init__(self, abbinata=True):
        self.cal, self.posta, self.righe, self.mail, self.ai, self.avvisi = {}, {}, [], [], [], []
        self.cal_rotto, self.abbinata = False, abbinata
        self.notifiche, self.push_rotta = [], False
        self.scheda = {"id": "p1", "company": "Rossi Finta", "name": "Mario", "email": "mario@rossi.invalid", "role": None,
                       "phone": "0422 999888", "website": "https://rossi.invalid", "descrizione": "Fa porte blindate a Treviso.",
                       "analysis_sent": True, "analysis_sent_at": "2026-10-13T09:00:00+00:00",
                       "analysis_pdf": "https://finto.local/analisi.pdf",
                       "enriched": {"analisi": {"frase_forte": "Le ricerche di chi deve cambiare la porta valgono piu' di tutto."},
                                    "google_fit": {"cosa_fa": "Porte blindate per privati", "tipo": "B2C",
                                                   "sito_testo": "Contatti: centralino 0422 777666, oppure 0422 123456"}}}
        self.storia = [{"at": "2026-10-12T09:00:00+00:00", "kind": "email_out", "body": "Lorenzo, t. +39 371 000 0000"},
                       {"at": "2026-10-13T09:00:00+00:00", "kind": "email_in", "body": _FIRMA},
                       {"at": "2026-10-13T10:00:00+00:00", "kind": "email_in", "body": "Accettato: StudioGalilei - Chiamata conoscitiva"}]

    def evento(self, eid, giorno, ora_, chi="mario@rossi.invalid", stato="confirmed", dove="cal", rifiutato=False):
        inizio = datetime.datetime.fromisoformat(f"{giorno}T{ora_}").replace(tzinfo=_ROMA).astimezone(datetime.timezone.utc)
        e = {"evento": eid, "inizio": inizio, "titolo": "StudioGalilei - Chiamata conoscitiva  (Mario Rossi)",
             "descrizione": f"<b>Prenotato da</b>\nMario Rossi\n{chi}", "invitati": ["dramane@studiogalilei.com", chi],
             "rifiutati": [chi] if rifiutato else [], "stato": stato, "meet": f"https://meet.google.com/{eid}", "link": "",
             "fonte": "calendario" if dove == "cal" else "mail"}
        (self.cal if dove == "cal" else self.posta)[eid] = e
        return e

    def sb(self, m, path, corpo=None, *a, **k):
        import urllib.parse as up
        if path.startswith("/rest/v1/prenotazioni_segnalate"):
            if m == "GET":
                return [dict(r) for r in self.righe if "come=eq.incerto" not in path or r.get("come") == "incerto"]
            if m == "POST":
                fatte = []
                for r in corpo:
                    if not any(x["chiave"] == r["chiave"] for x in self.righe):
                        x = {**r, "quando": self.ora.strftime("%Y-%m-%dT%H:%M:%S+00:00")}
                        self.righe.append(x)
                        fatte.append(dict(x))
                return fatte
            chiavi = [c.strip('"') for c in up.unquote(path.split("chiave=in.(")[1].rsplit(")", 1)[0]).split('","')]
            if m == "DELETE":
                self.righe[:] = [x for x in self.righe if x["chiave"] not in chiavi]
            if m == "PATCH":
                for x in self.righe:
                    if x["chiave"] in chiavi:
                        x.update(corpo)
            return None
        if path.startswith("/rest/v1/prospects"):
            return [dict(self.scheda)] if self.abbinata and "id=eq.p1" in path else []
        if path.startswith("/rest/v1/interactions"):
            return [dict(r) for r in self.storia] if "prospect_id=eq.p1" in path else []
        if path.startswith("/rest/v1/memoria_letture") or path.startswith("/rest/v1/uso_modelli"):
            return [] if m == "GET" else None
        return None

    def chiedi(self, prompt, formato=None):
        self.ai.append(prompt)
        return json.dumps({"nome": "Mario Rossi", "ruolo": "Direttore commerciale", "attivita": "Fa porte blindate a Treviso.",
                           "ultima_frase": "volentieri, ci sentiamo in call."})

    def manda(self, grezzo):
        import base64
        import email
        from email.header import decode_header, make_header
        m = email.message_from_bytes(base64.urlsafe_b64decode(grezzo))
        corpo = "".join(p.get_payload(decode=True).decode() for p in m.walk() if p.get_content_type() == "text/html")
        self.mail.append({"a": m["To"], "cc": m["Cc"], "bcc": m["Bcc"], "oggetto": str(make_header(decode_header(m["Subject"]))),
                          "html": corpo})
        return {"id": "x"}

    def giro(self, giorno, ora_):
        import segnale_provvisorio as S
        import stanza as St
        self.ora = datetime.datetime.fromisoformat(f"{giorno}T{ora_}").replace(tzinfo=_ROMA).astimezone(datetime.timezone.utc)
        prima = len(self.mail)

        def cal(ora):
            if self.cal_rotto:
                raise RuntimeError("Google 500 su calendar")
            return [dict(e) for e in self.cal.values()]
        vero = (S.sb, St.sb, S._eventi_calendario, S._prenotazioni_mail, S._riconosci, S._chiedi_ai, S._gmail_send,
                S._gmail_inviata, S._avvisa, S.adesso, S._push)
        S._push = self.push
        S.sb = St.sb = self.sb
        S._eventi_calendario, S._prenotazioni_mail = cal, lambda ora: [dict(e) for e in self.posta.values()]
        S._riconosci = lambda ev: "p1" if self.abbinata else None
        S._chiedi_ai, S._gmail_send, S._gmail_inviata, S._avvisa = self.chiedi, self.manda, lambda o, d: False, self.avvisi.append
        S.adesso = lambda: self.ora
        S.GIRO.update(pagate=0, memoria_rotta=False, sonda=False, giorno_restano=None, tetto_giorno=False)
        try:
            segnali = S.giro_prenotazioni(prova=False, ora=self.ora)
        finally:
            (S.sb, St.sb, S._eventi_calendario, S._prenotazioni_mail, S._riconosci, S._chiedi_ai, S._gmail_send,
             S._gmail_inviata, S._avvisa, S.adesso, S._push) = vero
        # i segnali segnati in questo giro (20/10 sera: solo la «mattina» e' anche una mail, in .mail)
        self.ultime_mail = [x["oggetto"] for x in self.mail[prima:]]
        return [S.componi_prenotazione(s)[0] for s in segnali]

    def push(self, titolo, testo, url, tag):
        if self.push_rotta:
            raise TimeoutError("web.push.apple.com: timed out")
        self.notifiche.append({"titolo": titolo, "testo": testo, "url": url, "mail_prima": len(self.mail)})
        return 1


@prova("prenotazioni: la mail va solo a Dre, e dal calendario e da Smartlead non si scrive niente")
def _():
    import re as _re
    f = _PrenotazioniFinte()
    f.evento("ev1", "2026-10-23", "11:00")
    f.giro("2026-10-14", "15:00")
    assert f.mail == [], "la prenotazione non e' piu' una mail (20/10 sera)"
    f.giro("2026-10-23", "08:31")
    assert len(f.mail) == 1 and all(x["a"] == "dramane@studiogalilei.com" and not x["cc"] and not x["bcc"] for x in f.mail), f.mail
    t = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "segnale_provvisorio.py"), encoding="utf-8").read()
    metodi = _re.findall(r'\bg\("(\w+)"', t)
    assert metodi.count("POST") == 1 and set(metodi) == {"GET", "POST"}, f"verso Google solo letture, e la mail: {metodi}"
    assert "smartlead.ai/api" not in t and "calendars/primary/events/" not in t, "il segnale non tocca Smartlead ne' gli eventi"


@prova("prenotazioni: una prenotazione da' un segnale solo, anche vista dal calendario e dalla mail")
def _():
    f = _PrenotazioniFinte()
    f.evento("ev1", "2026-10-23", "11:00")
    f.evento("ev1", "2026-10-23", "11:00", dove="posta")
    assert f.giro("2026-10-14", "15:00") == ["Prenotato: Rossi Finta, venerdì 23 ottobre alle 11:00"], f.mail
    assert f.giro("2026-10-14", "15:05") == [], "la stessa prenotazione ha suonato due volte"
    f.cal_rotto = True                                    # il calendario si ferma: resta la mail, ma e' gia' nota
    assert f.giro("2026-10-14", "15:10") == [] and f.avvisi, "con il calendario fermo: doppione, o nessun avviso"
    # solo dalla mail (il calendario fermo dall'inizio): parte, e quando il calendario torna non si ripete
    g = _PrenotazioniFinte()
    g.cal_rotto = True
    g.evento("ev2", "2026-10-23", "11:00", dove="posta")
    assert len(g.giro("2026-10-14", "15:00")) == 1
    g.cal_rotto = False
    g.evento("ev2", "2026-10-23", "11:00")
    assert g.giro("2026-10-14", "15:05") == []
    assert g.ai == [], "la scheda (una lettura AI) si prepara solo la mattina della call, per la mail che parte"


@prova("prenotazioni: la mattina della call alle 8:30 la scheda torna, una volta (e non se e' arrivata stamattina)")
def _():
    f = _PrenotazioniFinte()
    f.evento("ev1", "2026-10-23", "11:00")
    f.giro("2026-10-14", "15:00")
    assert f.giro("2026-10-23", "08:25") == [], "la scheda della mattina e' partita prima delle 8:30"
    assert f.giro("2026-10-23", "08:31") == ["Oggi alle 11:00: Rossi Finta"], f.mail[-1]["oggetto"]
    h = f.mail[-1]["html"]
    assert "Appunti:" in h and "tel:+393331234567" in h and "Direttore commerciale" in h and "apri l'analisi" in h, h[:400]
    assert f.giro("2026-10-23", "08:40") == [] and f.giro("2026-10-23", "10:00") == [], "la scheda della mattina e' tornata due volte"
    assert f.giro("2026-10-23", "11:30") == []
    # prenotata stamattina alle 9 per le 15 (20/10 sera): la «Prenotato» non e' piu' una mail, quindi la
    # scheda arriva al giro dopo come «Oggi alle», una volta
    g = _PrenotazioniFinte()
    g.evento("ev2", "2026-10-23", "15:00")
    assert g.giro("2026-10-23", "09:00") == ["Prenotato: Rossi Finta, venerdì 23 ottobre alle 15:00"] and g.mail == []
    assert g.giro("2026-10-23", "09:05") == ["Oggi alle 15:00: Rossi Finta"] and len(g.mail) == 1
    assert g.giro("2026-10-23", "09:10") == [] and len(g.mail) == 1
    # una prenotazione gia' nota prima dell'accensione (semina): la mattina la scheda arriva
    s = _PrenotazioniFinte()
    s.evento("ev3", "2026-10-23", "15:00")
    s.righe.append({"chiave": "prenotato:ev3", "tipo": "prenotato", "evento": "ev3", "inizio": "2026-10-23T13:00:00+00:00",
                    "invitato": "mario@rossi.invalid", "azienda": "", "prospect_id": None, "come": "semina",
                    "quando": "2026-10-23T07:00:00+00:00"})
    assert s.giro("2026-10-23", "09:00") == ["Oggi alle 15:00: Rossi Finta"]


@prova("prenotazioni: se non si abbina a nessun lead la mail parte lo stesso, con quello che c'e'")
def _():
    f = _PrenotazioniFinte(abbinata=False)
    f.evento("ev1", "2026-10-23", "11:00", chi="anna@altra.invalid")
    assert f.giro("2026-10-14", "15:00") == ["Prenotato: Mario Rossi, venerdì 23 ottobre alle 11:00"] and f.mail == []
    assert f.giro("2026-10-23", "08:31") == ["Oggi alle 11:00: Mario Rossi"], f.mail
    h = f.mail[0]["html"]
    assert "trovato fra i lead" in h and "anna@altra.invalid" in h and "Appunti:" in h, h[:400]
    # anche se il riconoscimento si rompe
    import segnale_provvisorio as S
    g = _PrenotazioniFinte()
    g.evento("ev2", "2026-10-23", "11:00")
    vero = g.sb
    g.sb = lambda m, path, *a, **k: (_ for _ in ()).throw(RuntimeError("500")) if path.startswith("/rest/v1/prospects") else vero(m, path, *a, **k)
    assert len(g.giro("2026-10-14", "15:00")) == 1, "con la scheda rotta la prenotazione e' rimasta muta"
    assert S.componi_prenotazione  # noqa: B018


@prova("prenotazioni: i numeri in gerarchia (cellulare della firma, fisso, scheda, centralino), senza fax ne' partita IVA")
def _():
    f = _PrenotazioniFinte()
    f.evento("ev1", "2026-10-23", "11:00")
    f.giro("2026-10-14", "15:00")
    f.giro("2026-10-23", "08:31")
    h = f.mail[0]["html"]
    ordine = [h.find(f"tel:{n}") for n in ("+393331234567", "+390422123456", "+390422999888", "+390422777666")]
    assert all(i > 0 for i in ordine) and ordine == sorted(ordine), ordine
    assert "cellulare, dalla firma" in h and "fisso, dalla firma" in h and "dalla scheda del Workspace" in h and "centralino, dal sito" in h
    assert "654321" not in h and "01234567890" not in h and "3710000000" not in h, "un fax, una partita IVA o un numero nostro tra i telefoni"
    assert h.count("tel:+390422123456") == 1, "lo stesso numero due volte"
    assert "1." not in h.split("Telefoni")[1].split("</p>")[0], "i numeri non si numerano"


@prova("prenotazioni: spostata e cancellata, una riga sola (anche quando dalla pagina si prende un altro orario)")
def _():
    f = _PrenotazioniFinte()
    f.evento("ev1", "2026-10-23", "11:00")
    f.giro("2026-10-14", "15:00")
    f.evento("ev1", "2026-10-23", "15:00")
    assert f.giro("2026-10-14", "16:00") == ["Spostata: Rossi Finta, ora venerdì 23 ottobre alle 15:00"]
    assert f.giro("2026-10-14", "16:05") == []
    f.cal["ev1"]["stato"] = "cancelled"
    assert f.giro("2026-10-14", "17:00") == ["Cancellata: Rossi Finta, venerdì 23 ottobre alle 15:00"]
    assert f.giro("2026-10-14", "17:05") == []
    # dalla pagina: nuova prenotazione e la vecchia annullata -> una «spostata», niente «cancellata»
    g = _PrenotazioniFinte()
    g.evento("ev1", "2026-10-23", "11:00")
    g.giro("2026-10-14", "15:00")
    g.evento("ev2", "2026-10-26", "10:00")
    g.cal["ev1"]["stato"] = "cancelled"
    assert g.giro("2026-10-14", "16:00") == ["Spostata: Rossi Finta, ora lunedì 26 ottobre alle 10:00"], [x["oggetto"] for x in g.mail]
    assert g.giro("2026-10-14", "16:05") == []
    assert g.giro("2026-10-26", "08:31") == ["Oggi alle 10:00: Rossi Finta"]
    # l'invito rifiutato e' una cancellazione
    r = _PrenotazioniFinte()
    r.evento("ev1", "2026-10-23", "11:00")
    r.giro("2026-10-14", "15:00")
    r.evento("ev1", "2026-10-23", "11:00", rifiutato=True)
    assert r.giro("2026-10-14", "16:00") == ["Cancellata: Rossi Finta, venerdì 23 ottobre alle 11:00"]


@prova("versione snella: schede.py legge e basta (scrive solo snella_*, su Smartlead solo GET) e non paga letture")
def _():
    import re as _re
    sorgente = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "schede.py"), encoding="utf-8").read()
    # ogni scrittura nel database va nelle tabelle della versione snella
    for metodo, percorso in _re.findall(r'sb\(\s*"(POST|PATCH|DELETE|PUT)"\s*,\s*f?"([^"]+)"', sorgente):
        assert percorso.startswith("/rest/v1/{tabella}") or percorso.startswith("/rest/v1/snella_"), (metodo, percorso)
    assert 'scrivi("snella_schede"' in sorgente and 'scrivi("snella_numeri"' in sorgente
    assert len(_re.findall(r"\bscrivi\(", sorgente)) == 3, "scrivi() usata fuori dalle due tabelle snella"
    # su Smartlead una sola porta, in sola lettura; niente manda.py, niente postino
    assert 'method="GET"' in sorgente and not _re.search(r'method="(POST|PATCH|DELETE|PUT)"', sorgente)
    assert "import manda" not in sorgente and "from manda" not in sorgente
    import schede
    assert schede.S._restano_oggi() == 0, "le schede non devono mai pagare una lettura AI"
    import categorie_smartlead as C
    assert set(schede.NOME_DI) == set(C.NUOVE), "una categoria del manuale senza il nome di Dre"
    import direttore
    assert direttore.corsia_di("schede") == "leggera"


@prova("i 12 stati di Dre (19/10): dodici e nient'altro, ognuno col responsabile e l'azione; i vecchi passano ai nuovi; il database ha la stessa copia")
def _():
    import json as _json, re as _re
    radice = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    st = _json.load(open(os.path.join(radice, "src", "snella", "stati.json"), encoding="utf-8"))
    nomi = [x["nome"] for x in st["stati"]]
    assert nomi == ["Da chiamare", "Da rispondere", "Analisi inviata", "Call fissata", "Proposta inviata", "Cliente acquisito",
                    "Da ricontattare", "Assente", "Nessuna risposta", "Non interessato", "Perso", "Non contattare"], nomi
    assert st["gruppi"] == ["Da gestire oggi", "Opportunità", "In attesa", "Chiusi"]
    for x in st["stati"]:
        assert x["gruppo"] in st["gruppi"] and x["responsabile"] in ("Dramane", "Claude") and x["azione"].strip(), x
    # i nomi vecchi (snella del 15/10 e i calcolati) finiscono tutti in uno dei 12
    vecchi = {"No grazie": "Non interessato", "Non scrivere più": "Non contattare", "Fuori ufficio": "Assente",
              "Conoscitiva": "Call fissata", "Analisi mandata": "Analisi inviata", "Vuole sentirti": "Da chiamare",
              "Follow-up": "Analisi inviata", "Da riprendere": "Da ricontattare", "In conversazione": "Da rispondere"}
    for v, n in vecchi.items():
        assert st["dai_vecchi"][v] == n, (v, st["dai_vecchi"].get(v))
    assert set(st["dai_vecchi"].values()) <= set(nomi)
    # il database: snella_stati ha le stesse righe, snella_nome_nuovo la stessa mappa, e snella_lead
    # accetta solo i 12 (la chiave verso snella_stati, non un elenco a parte)
    sql = open(os.path.join(radice, "supabase", "schema_v92.sql"), encoding="utf-8").read()
    righe = _re.findall(r"\('([^']+)',\s+(\d+),\s+'([^']+)',\s+'(\w+)',\s+'(\w+)',\s+'((?:[^']|'')+)'", sql)
    assert [(r[0], int(r[1]), r[2], r[3], r[4], r[5].replace("''", "'")) for r in righe] == \
        [(x["nome"], i + 1, x["gruppo"], x["tono"], x["responsabile"], x["azione"]) for i, x in enumerate(st["stati"])], righe
    mappa = dict(_re.findall(r"when '([^']+)' then '([^']+)'", sql.split("function snella_nome_nuovo", 1)[1].split("$$;", 1)[0]))
    assert mappa == st["dai_vecchi"], mappa
    assert "foreign key (stato) references snella_stati" in sql
    # schede.py: ogni categoria va in uno dei 12, ogni stato ha un'azione, il caldo porta a Da chiamare
    import schede
    import categorie_smartlead as C
    assert set(schede.NOME_DI.values()) <= set(nomi)
    p = {"classificazione": "positivo", "stage": "in_follow_up", "last_reply_at": "2026-10-18"}
    assert schede.stato_di(C.N_FU, p, False, True) == "Analisi inviata"
    assert schede.stato_di(C.N_NO, p, False, True) == "Non interessato"
    assert schede.stato_di(C.N_STOP, p, True, True) == "Non contattare", "il blocco vince anche sul cliente"
    assert schede.stato_di(None, {**p, "pipeline_stage": "prova"}, False, True) == "Cliente acquisito"
    assert schede.stato_di(C.N_SI, {**p, "pipeline_stage": "perso"}, False, True) == "Perso"
    assert schede.stato_di(C.N_SI, {**p, "stage": "perso"}, False, True) == "Perso"
    assert schede.stato_di(C.N_NO, {**p, "stage": "perso"}, False, True) == "Non interessato"
    assert schede.stato_di(None, {**p, "pipeline_stage": "conoscitiva"}, False, True) == "Call fissata"
    assert schede.stato_di(None, {}, False, False) == "Nessuna risposta"
    assert schede.stato_di(None, p, False, True) == "Da rispondere"
    for n in nomi:
        azione, _ = schede.prossima_mossa(n, {}, [])
        assert azione.strip(), n
    assert schede.prossima_mossa("Non interessato", {}, [], "casella morta")[0] == "Fermare la sequenza: casella morta"
    assert schede.NON_SI_CHIAMA == {"Call fissata", "Proposta inviata", "Cliente acquisito", "Non interessato", "Perso", "Non contattare"}
    # la UI non scrive piu' i nomi vecchi (si traducono da stati.json)
    for f in os.listdir(os.path.join(radice, "src", "snella")):
        if f.endswith((".ts", ".tsx")) and not f.endswith(".test.ts"):
            t = open(os.path.join(radice, "src", "snella", f), encoding="utf-8").read()
            t = "\n".join(r for r in t.splitlines() if not r.lstrip().startswith(("//", "*", "/*")))
            for v in vecchi:
                if v == "Conoscitiva":
                    continue                    # e' anche il nome del tipo di call (Oggi), non solo lo stato vecchio
                assert f"'{v}'" not in t, f"{f} usa ancora lo stato vecchio «{v}»"


@prova("Da chiamare SOLO con un cellulare suo, dalla firma o dalla scheda, mai dal sito (Dre, 20/10 sera); le scelte a mano restano")
def _():
    import segnale_provvisorio as S
    import schede
    import foglio as F
    import orecchio as O
    nostra = "Studio Galilei\nTel. 02 00000000\nCell. 345 0000000"
    firma_cell = "Va bene, sentiamoci.\n\nMario Rossi\nCell. 333 0000001"
    firma_fisso = "Va bene, sentiamoci.\n\nMario Rossi\nTel. 02 00000001"
    p = {"id": "p1", "phone": None, "enriched": {"google_fit": {"sito_testo": "Contatti: 02 00000002, cell. 334 0000002"}}}
    out = {"kind": "email_out", "body": nostra}
    # caldo con un cellulare in firma: si chiama; solo il fisso in firma: no; solo il centralino (o un cellulare) del sito: no
    assert S.cellulare_di(p, [out, {"kind": "email_in", "body": firma_cell}]) == "333 0000001"
    assert S.cellulare_di(p, [out, {"kind": "email_in", "body": firma_fisso}]) is None
    assert S.cellulare_di(p, [out]) is None, "il sito e' il centralino, anche se il numero inizia per 3"
    assert S.si_puo_chiamare(p, [out, {"kind": "email_in", "body": firma_cell}]) and not S.si_puo_chiamare(p, [out])
    # il cellulare della scheda del Workspace vale; il nostro numero nella sua mail no; il fisso della scheda no
    assert S.cellulare_di({**p, "phone": "+39 335 0000003"}, [out]) == "+39 335 0000003"
    assert S.cellulare_di({**p, "phone": "02 00000003"}, [out]) is None
    assert S.cellulare_di(p, [out, {"kind": "email_in", "body": "Richiamatemi al 345 0000000"}]) is None, "e' il nostro numero"
    # la stessa regola sui telefoni gia' in gerarchia (quelli della scheda dell'app)
    ger = S.in_gerarchia(S.numeri_di(p, [out, {"kind": "email_in", "body": firma_cell}]))
    assert S.cellulare_fra(ger) == "333 0000001" and ger[0]["etichetta"] == "cellulare, dalla firma"
    assert S.cellulare_fra([]) is None and S.cellulare_fra(None) is None
    # la riga che passa il lead a Dre: col cellulare «Da chiamare» da oggi, senza «Da rispondere» con Dre e il perche'
    ora = datetime.datetime(2026, 10, 20, 16, 0, tzinfo=datetime.timezone.utc)
    r = S.passa_a_dre("p1", "333 0000001", ora)
    assert r["stato"] == "Da chiamare" and r["chiamata"] == "richiamare" and r["richiamare_il"] == "2026-10-20", r
    r = S.passa_a_dre("p1", None, ora)
    assert r["stato"] == "Da rispondere" and r["responsabile"] == "Dramane" and r["prossima_mossa"] == S.SENZA_CELLULARE and "chiamata" not in r, r
    assert S.SENZA_CELLULARE == "Vuole sentirci ma non ha lasciato un cellulare: scrivigli"
    # schede.py: il cancello sta dopo il caldo e prima di «da_chiamare»; i telefoni portano tipo e fonte alla UI
    src = open(schede.__file__, encoding="utf-8").read()
    assert 'cellulare = S.cellulare_fra(sc.get("telefoni") or [])' in src
    assert 'senza_cellulare = stato == "Da chiamare" and not cellulare' in src and 'if senza_cellulare:\n        stato = "Da rispondere"' in src
    assert 'da_chiamare = bool(perche) and not escluso and cellulare is not None' in src
    assert 'mossa, mossa_il, responsabile = S.SENZA_CELLULARE, None, "Dramane"' in src
    assert '"tipo": t["tipo"], "fonte": t["fonte"]' in src and schede.VERSIONE != "schede5", "le schede si rifanno tutte con la regola nuova"
    # la UI: la lista «Da chiamare» di Oggi vuole il cellulare, e il numero grande e' quello
    radice = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    regole = open(os.path.join(radice, "src", "snella", "regole.ts"), encoding="utf-8").read()
    assert "export function cellulareDi" in regole and "|| !cellulareDi(r.scheda)) continue" in regole
    oggi = open(os.path.join(radice, "src", "snella", "Oggi.tsx"), encoding="utf-8").read()
    assert "const primo = cellulareDi(s) ?? s?.telefoni[0]" in oggi
    # le scelte a mano di Dre restano: il foglio scrive «Da chiamare» senza guardare il numero, e l'app non passa di qui
    chiama = dict(F.effetti("scelta", "Da chiamare", datetime.date(2026, 10, 20)))["snella_lead"]
    assert chiama["stato"] == "Da chiamare" and chiama["chiamata"] == "richiamare"
    assert "cellulare" not in open(F.__file__, encoding="utf-8").read().split("def effetti", 1)[1].split("\ndef ", 1)[0]
    # l'orecchio e il si' caldo passano dalla stessa riga
    assert "SP.passa_a_dre(pid, cellulare, ora)" in open(O.__file__, encoding="utf-8").read()


@prova("versione snella: il caldo vale per la mail su cui e' nato; i rimbalzi e i DMARC non sono risposte (17/10)")
def _():
    import schede
    # caldo sulla mail di prima, l'ultima letta dice non caldo: non si chiama
    assert not schede.vale_il_caldo({"caldo"}, {"m1"}, "m2", {"caldo": False})
    # caldo nato proprio sull'ultima: vale
    assert schede.vale_il_caldo({"caldo"}, {"m2"}, "m2", {"caldo": False})
    # l'ultima non e' stata letta: il segnale resta
    assert schede.vale_il_caldo({"caldo"}, {"m1"}, "m2", None)
    assert not schede.vale_il_caldo(set(), set(), "m2", {"caldo": True})
    import segnale_provvisorio as S
    assert S.automatica("Message blocked\nYour message to a@b.it has been blocked. See technical details below")
    assert S.automatica("Your message to a.b@x.com couldn't be delivered. a.b wasn't found at x.com")
    assert S.automatica("This is a DMARC aggregate report for studiogalilei.com")
    assert not S.automatica("Va bene, il messaggio l'ho letto: ci sentiamo lunedi'")
    # le schede di chi non e' piu' attivo si tolgono, ma mai in massa (una lettura storta)
    chiamate = []
    vero = schede.sb
    schede.sb = lambda metodo, percorso, *a, **k: chiamate.append((metodo, percorso))
    try:
        schede.togli_spente({"gia": {"a": {}, "b": {}, "c": {}}, "ps": {"a": {}}})
        assert chiamate == [("DELETE", "/rest/v1/snella_schede?prospect_id=in.(b,c)")], chiamate
        chiamate.clear()
        schede.togli_spente({"gia": {str(i): {} for i in range(200)}, "ps": {"1": {}}})
        assert chiamate == [], "199 schede su 200 da togliere: e' una lettura storta, non si tocca niente"
    finally:
        schede.sb = vero


@prova("versione snella: il testo citato si separa, l'html diventa testo, le righe vuote non si accumulano")
def _():
    import schede
    suo, citato = schede.dividi("Va bene, mi chiami domani.\n\n\n\nMario\n\nIl giorno lun 12 ott 2026 alle 10:00 Lorenzo <x@esempio.it> ha scritto:\n> la nostra mail")
    assert suo == "Va bene, mi chiami domani.\n\nMario", suo
    assert citato.startswith("Il giorno lun 12 ott") and "la nostra mail" in citato
    assert schede.dividi("<div>Ciao<br>a presto</div><style>p{color:red}</style>")[0] == "Ciao\na presto"


@prova("seconda testa: vede a chi era partita la nostra ultima mail e chi ha scritto la loro (16/10)")
def _():
    import lettura
    vero = lettura.secondo_lettore
    lettura.secondo_lettore = lambda t: None
    try:
        righe = [{"kind": "email_out", "at": "2026-10-12T07:02", "body": "prima mail", "a": "info@azienda.it"},
                 {"kind": "email_in", "at": "2026-10-12T07:32", "body": "Buongiorno, le confermo che l'indirizzo e' giusto. Mi invii pure l'analisi, grazie. Mario",
                  "mittente": "mario@azienda.it"},
                 {"kind": "email_out", "at": "2026-10-12T08:00", "body": "ecco l'analisi", "a": "info@azienda.it"}]
        f = lettura.ha_gia({"email": "info@azienda.it", "email_alt": ["mario@azienda.it"]}, righe)
    finally:
        lettura.secondo_lettore = vero
    assert f["ultima_nostra_a"] == "info@azienda.it" and f["ultima_loro_da"] == "mario@azienda.it", f
    # la nostra ultima mail intera: il giorno proposto sta spesso in fondo (16/10)
    lettura.secondo_lettore = lambda t: None
    try:
        lunga = "a fine luglio mi aveva risposto di risentirci a settembre. " * 8 + "Le propongo mercoledì 14 ottobre alle 15:30."
        f = lettura.ha_gia({"email": "info@azienda.it"}, righe[:2] + [{"kind": "email_out", "at": "2026-10-13T08:00", "body": lunga}])
    finally:
        lettura.secondo_lettore = vero
    assert "mercoledì 14 ottobre alle 15:30" in f["ultima_nostra"], f["ultima_nostra"][-80:]
    src = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "lettura.py")).read()
    assert "mandata a ' + f['ultima_nostra_a']" in src and "scritta da ' + f['ultima_loro_da']" in src
    assert "REGOLA DEI COSTI" in src, "la seconda testa deve sapere che i costi si danno in call (16/10)"


@prova("postino: il fuori ufficio di un collega non cambia il destinatario (16/10)")
def _():
    import manda
    ooo = {"type": "REPLY", "from": "Claudia <claudia@azienda.it>",
           "email_body": "<p>Grazie per il messaggio. Sono fuori ufficio fino al 19 agosto.</p>"}
    assert manda.chi_ha_risposto(ooo, "servizi@azienda.it") is None
    vera = {"type": "REPLY", "from": "Domenico <domenico@azienda.it>",
            "email_body": "Buongiorno, sono io che seguo il marketing: mi mandi pure l'analisi, sentiamoci mercoledi'."}
    assert manda.chi_ha_risposto(vera, "info@azienda.it") == "domenico@azienda.it"


@prova("cancello: «fai da te» non e' un tu, «puoi» si' (16/10)")
def _():
    import bozze
    base = "Buongiorno Enea, le propongo una breve videochiamata conoscitiva: https://calendar.app.google/x\nA presto,"
    assert not any("registro misto" in e for e in bozze.cancello("Vale la domanda dei progetti, non il fai da te.\n" + base))
    assert any("registro misto" in e for e in bozze.cancello("Se vuoi ne parliamo.\n" + base))


@prova("stanza: il carattere nullo non arriva mai al database (16/10)")
def _():
    import json
    corpo = {"t": "sito\x00 con nullo"}
    assert "\\u0000" in json.dumps(corpo)
    src = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "stanza.py")).read()
    assert 'json.dumps(corpo).replace("\\\\u0000", "")' in src
    # anche chi scrive sul database senza passare da stanza (sync delle mail, clara)
    qui = os.path.dirname(os.path.abspath(__file__))
    assert 'json.dumps(body).replace("\\\\u0000", "")' in open(os.path.join(qui, "sync_v2.py")).read()
    assert open(os.path.join(qui, "clara.py")).read().count('json.dumps(dati).replace("\\\\u0000", "")') >= 1


@prova("orari offerti: contano anche le mail gia' partite (16/10)")
def _():
    src = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "bozze.py")).read()
    assert "and(stato.eq.fatta,risposta_il.gte.{dieci})" in src


@prova("posta: un servizio di posta (aruba.it) non indica un'azienda, un rapporto DMARC non e' una mail (17/10)")
def _():
    import posta
    servizio = "aruba.it"
    rubrica = {"email": {}, "dominio": {servizio: "lead-aruba"}, "aziende": [], "conta": {}, "indice": {}}
    trovato = posta.trova(rubrica, ["dmarc-report" + "@" + servizio], "Report Domain: esempio.it")
    assert not trovato or trovato[0] != "lead-aruba", trovato
    assert posta.AUTOMATICI.search("dmarc" + "@" + servizio)
    # e un servizio di posta non e' mai il sito dell'azienda (Google Fit e analisi)
    import stanza
    assert stanza.sito_vero({"website": "https://www." + servizio, "email": "x" + "@" + servizio}) == ""
    assert stanza.sito_vero({"website": "", "email": "x" + "@" + "azienda.it"}) == "https://azienda.it"
    assert stanza.sito_vero({"website": "", "email": "x" + "@" + "gmail.com"}) == ""


@prova("lettura: il messaggio si separa dalla firma anche senza «saluti», e non perde parole (Dre, 17/10)")
def _():
    import lettura as L
    at = "@"
    m, f = L.dividi("Ho girato la sua mail a chi all'interno dell azienda se ne occupa\n\nDaniele Rossi\nBrand Sales Manager\n"
                    "Mobile: 3401234567\nEmail:daniele" + at + "azienda.it\nStrada di Busseto 18, Siena - 53100")
    assert m == "Ho girato la sua mail a chi all'interno dell azienda se ne occupa" and "Mobile" in f, (m, f)
    m, _ = L.dividi("Buonasera,\nLa ringraziamo ma non siamo\nInteressati.\nCordialmente.\nSabrina")
    assert "Interessati" in m, m
    m, _ = L.dividi("Gentile mittente,\nPer future comunicazioni la preghiamo di inviare un messaggio al seguente indirizzo:\n"
                    "roberta" + at + "azienda.it\n______\nDear sender")
    assert "roberta" + at + "azienda.it" in m, m
    m, _ = L.dividi("Gentile mittente, presa in carico.\nLa informiamo che per argomenti amministrativi e' necessario scrivere ad "
                    "amministrazione" + at + "azienda.it .\nGrazie")
    assert "amministrazione" + at in m, m
    m, _ = L.dividi("Ho dato un occhiata ad Studio Rossi Ok la invii, grazie\n\nCordiali saluti\nMirco Rossi Geometra\nSTUDIO ROSSI")
    assert "Ok la invii" in m, m
    m, _ = L.dividi("Buongiorno, aspetto solo conferma mail\n\nSe vuole possiamo sentirci mercoledi'.\nSaluti\nD. Rossi\ncell 3290000000")
    assert m.startswith("Se vuole possiamo sentirci") and "cell" not in m, m
    m, _ = L.dividi("Buongiorno, mi chiami pure domani al 347 1234567 dopo le 15\nMario Rossi")
    assert "347 1234567" in m, m
    m, f = L.dividi("Buongiorno,\nva bene.\nMario Rossi")
    assert "va bene" in m and f == "Mario Rossi", (m, f)
    # esame del 17/10: l'indirizzo nuovo dopo «si prega di scrivere» andato a capo, e la risposta sotto la citazione
    m, _ = L.dividi("Buongiorno,\nquesta casella non e' piu' attiva, si prega di scrivere\nalla nuova email: gino" + at + "azienda.it\nGrazie")
    assert "gino" + at + "azienda.it" in m, m
    m, _ = L.dividi("Il giorno lun 12 ott 2026 alle 10:00 Lorenzo <l" + at + "azienda.it> ha scritto:\n> la nostra mail\n\nOk, mandatemela pure.\nMario")
    assert m == "Ok, mandatemela pure.", m
    m, _ = L.dividi("Il 2026-08-03 13:22 Lorenzo Fornasier ha scritto: Buongiorno Daniele,&nbsp; abbiamo preparato un'analisi. "
                    "Cordiali saluti, Lorenzo Fornasier&nbsp; Studio Galilei Studiogalilei com.&nbsp; Buonasera, La ringrazio. Mi mandi pure.")
    assert m.startswith("Buonasera, La ringrazio. Mi mandi pure"), m
    src = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "bozze.py")).read()
    assert 'not re.search(r"[A-Za-zÀ-ÿ]{2,}", suo)' in src, "un sì corto non si salta piu' per lunghezza"


@prova("l'esame di affidabilita' non scrive: database, Smartlead e Google si fermano nel guardiano; un sì perso e' pericoloso (17/10)")
def _():
    import importlib
    import stanza
    import cervello
    import lettura as L
    salvati = (stanza.sb, L.sb, cervello._chiedi_openai, cervello._chiedi_claude, cervello._salva_cache, cervello._nel_db,
               cervello._conta_uso, os.environ.get("PROVA"))
    try:
        E = importlib.import_module("esame")
        assert stanza.sb("PATCH", "/rest/v1/prospects?id=eq.1", {"x": 1}) is None
        assert stanza.sb("POST", "/rest/v1/proposte", {"x": 1}) is None
        assert L.sb("DELETE", "/rest/v1/interactions?id=eq.1") is None
        assert E.BLOCCATE["PATCH /rest/v1/prospects"] == 1 and E.BLOCCATE["POST /rest/v1/proposte"] == 1, E.BLOCCATE
        dre_si = {"azione": "MANDA_ANALISI", "vuole": True}
        assert E.gravita(dre_si, {"mossa": "NON_RISPONDERE", "chi": "da solo"})[0] == "PERICOLOSO"
        assert E.gravita(dre_si, {"mossa": "MANDA_ANALISI", "chi": "Dre in Posta"})[0] == "GIUSTO"
        assert E.gravita({"azione": "GIGANTE_BUONO"}, {"mossa": "NON_RISPONDERE", "chi": "da solo"})[0] == "GIUSTO"
        assert E.gravita({"azione": "TOGLI_DALLA_LISTA", "non_scrivere": True}, {"mossa": "MANDA_ANALISI", "chi": "da solo"})[0] == "PERICOLOSO"
        assert E.gravita({"azione": "NON_RISPONDERE", "automatico": True}, {"mossa": "MANDA_ANALISI", "chi": "da solo"})[0] == "PERICOLOSO"
    finally:
        stanza.sb, L.sb, cervello._chiedi_openai, cervello._chiedi_claude, cervello._salva_cache, cervello._nel_db, cervello._conta_uso, prova_ = salvati
        if prova_ is None:
            os.environ.pop("PROVA", None)
        else:
            os.environ["PROVA"] = prova_


# ── le notifiche sul telefono (17/10): accanto alla mail, mai al posto suo ──
def _con_letture(f):
    """schede.py, importato da una prova prima, azzera le letture pagabili del segnale (e' voluto:
    le schede non pagano). Qui servono le letture vere del segnale."""
    def dentro():
        import segnale_provvisorio as S
        vero = S._restano_oggi

        def restano():
            if S.GIRO["giorno_restano"] is None:
                S.GIRO["giorno_restano"] = S.PAGATE_AL_GIORNO
            return S.GIRO["giorno_restano"]
        S._restano_oggi = restano
        try:
            return f()
        finally:
            S._restano_oggi = vero
    dentro.__name__ = f.__name__
    return dentro


@prova("notifica: il segnale e le prenotazioni non suonano sul telefono, e dal 20/10 sera non mandano mail di giornata")
@_con_letture
def _():
    f = _SegnaleFinto(SCHEDA_LEAD, {"mi chiami domani": CALDO})
    f.scrive("Buongiorno, mi chiami domani al 333 1234567")
    assert f.giro() == ["caldo"] and f.mail == [] and f.notifiche == [], (f.mail, f.notifiche)
    assert [x.get("come") for x in f.segnati] == ["segnale"], f.segnati
    p = _PrenotazioniFinte()
    p.evento("ev1", "2026-10-23", "11:00")
    assert p.giro("2026-10-14", "15:00") and p.mail == [] and p.notifiche == [], p.notifiche
    p.cal["ev1"]["stato"] = "cancelled"
    p.giro("2026-10-15", "10:00")
    assert p.mail == [] and p.notifiche == [], p.notifiche


# ── la giornata (20/10 sera): una mail sola alle 19, e dal segnale solo la scheda pre-call ──
@prova("dal segnale parte una mail a Dre solo per la scheda prima di una call (20/10 sera, Dre: «me le manda un po' a caso»)")
@_con_letture
def _():
    import segnale_provvisorio as S
    # le risposte: caldo, si', da guardare -> si segnano, nessuna mail
    for testo, letture in (("Buongiorno, mi chiami domani al 333 1234567", {"mi chiami domani": CALDO}),
                           ("La mail e' corretta", {"corretta": SI}), ("Buongiorno, valutiamo volentieri", {"valutiamo": None})):
        f = _SegnaleFinto(SCHEDA_LEAD, letture)
        f.scrive(testo)
        assert f.giro() and f.mail == [] and len(f.segnati) == 1, (testo, f.mail, f.segnati)
    assert S._mail([{"tipo": "caldo", "azienda": "X", "interaction_id": "i1", "prospect_id": "p1"}], 24, False) == []
    # le prenotazioni: prenotato, spostata, cancellata -> si segnano, nessuna mail; la mattina della call -> UNA mail
    p = _PrenotazioniFinte()
    p.evento("ev1", "2026-10-23", "11:00")
    assert p.giro("2026-10-14", "15:00") == ["Prenotato: Rossi Finta, venerdì 23 ottobre alle 11:00"] and p.mail == []
    p.evento("ev1", "2026-10-23", "15:00")
    assert p.giro("2026-10-14", "16:00") == ["Spostata: Rossi Finta, ora venerdì 23 ottobre alle 15:00"] and p.mail == []
    assert p.giro("2026-10-23", "08:31") == ["Oggi alle 15:00: Rossi Finta"] and [m["oggetto"] for m in p.mail] == ["Oggi alle 15:00: Rossi Finta"]
    assert p.mail[0]["a"] == "dramane@studiogalilei.com" and "Appunti:" in p.mail[0]["html"]
    p.cal["ev1"]["stato"] = "cancelled"
    assert p.giro("2026-10-23", "09:00") == ["Cancellata: Rossi Finta, venerdì 23 ottobre alle 15:00"] and len(p.mail) == 1
    # nel sorgente: manda_mail(DRE, ...) solo nei due giri, e il giro delle risposte la chiama solo su quello che _mail torna
    src = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "segnale_provvisorio.py"), encoding="utf-8").read()
    assert src.count("manda_mail(DRE,") == 2, src.count("manda_mail(DRE,")
    assert 'if s["tipo"] != "mattina":\n            print(f"segnata senza mail' in src, "una prenotazione che non e' la mattina parte per mail"
    assert "giornata.py" in src, "il segnale deve dire dove e' finito il quadro: la mail della sera"


@prova("la giornata (20/10 sera): «funziona regolarmente» solo senza guasti, con un guasto risolto c'e' la soluzione, al massimo 8 righe per Dre")
def _():
    import datetime, giornata as G
    roma = G.ROMA
    ora = datetime.datetime(2026, 10, 20, 19, tzinfo=roma)
    alle = lambda h, m=0: datetime.datetime(2026, 10, 20, h, m, tzinfo=roma)        # noqa: E731
    link = lambda pid: f"https://finto.local/#/s/lead/{pid}"                         # noqa: E731
    base = {"guasti_aperti": [], "guasti_risolti": [], "serie_errori": [], "controllo_fallito": None,
            "numeri": {"risposte": 31, "si": 5, "no": 15, "ooo": 4, "analisi": 6, "followup": 38, "promemoria": 0, "risposte_mandate": 0,
                       "prenotate": 0, "spostate": 0, "annullate": 1, "conversazioni": 5, "da_chiamare": 3},
            "aspettano": [], "domani": []}
    oggetto, testo, corpo = G.componi(ora, base, link=link)
    assert oggetto == "La giornata · mar 20/10", oggetto
    assert testo.splitlines()[0] == "Il sistema ha funzionato regolarmente." and "Soluzione" not in testo
    assert "31 risposte arrivate (5 sì, 15 no, 4 fuori ufficio)" in testo and "38 follow-up partiti" in testo and "1 call annullata" in testo
    assert "Niente da parte tua." in testo and "Nessuna call." in testo and testo.strip().splitlines()[-1] == "Niente da fare stasera: buona serata."
    # un guasto risolto da solo: niente «regolarmente», c'e' la soluzione
    d = dict(base, guasti_risolti=[{"chiave": "invio:manda", "cosa": "L'invio delle mail è fermo", "da": alle(10, 40), "risolto_il": alle(11, 5)}])
    _, t, _ = G.componi(ora, d, link=link)
    assert "funzionato regolarmente" not in t and t.startswith("È successo: L'invio delle mail è fermo, dalle 10:40 alle 11:05. Soluzione:"), t.splitlines()[0]
    # un guasto ancora aperto: la soluzione e' quella del semaforo
    d = dict(base, guasti_aperti=[{"chiave": "foglio", "cosa": "Il foglio non si aggiorna da 2 ore", "da": alle(17), "sta_facendo": "Riprova da solo ogni 10 minuti."}])
    _, t, _ = G.componi(ora, d, link=link)
    assert t.startswith("È successo: Il foglio non si aggiorna da 2 ore, dalle 17:00 e ancora adesso. Soluzione: Riprova da solo ogni 10 minuti."), t.splitlines()[0]
    assert t.strip().splitlines()[-1] == "Il resto va avanti da solo. Buona serata."
    # un'operazione caduta tre volte di fila e ripartita
    corse = [{"operazione": "schede", "at": alle(9, m), "esito": e} for m, e in ((0, "errore"), (10, "errore"), (20, "errore"), (30, "ok"))]
    corse += [{"operazione": "foglio", "at": alle(9, m), "esito": e} for m, e in ((0, "errore"), (10, "ok"), (20, "errore"), (30, "errore"))]
    serie = G.serie_di_errori(corse, {"schede": "Le schede"})
    assert [(s["nome"], s["n"], s["ripartita"]) for s in serie] == [("Le schede", 3, alle(9, 30))], serie
    _, t, _ = G.componi(ora, dict(base, serie_errori=serie), link=link)
    assert "È successo: Le schede è caduta 3 volte di fila dalle 09:00. Soluzione: è ripartita da sola alle 09:30." in t, t
    # «Aspettano te»: al massimo 8 righe, col link alla scheda, e il resto detto in una riga
    asp = [{"pid": f"p{i}", "azienda": f"Azienda {i}", "perche": "ha scritto oggi alle 10:00 e aspetta la tua risposta", "quando": alle(10)} for i in range(11)]
    _, t, h = G.componi(ora, dict(base, aspettano=asp, domani=[{"at": datetime.datetime(2026, 10, 21, 10, 30, tzinfo=roma), "azienda": "Rossi srl", "tipo": "conoscitiva"}]), link=link)
    blocco = t.split("Aspettano te\n", 1)[1].split("\n\nDomani", 1)[0].splitlines()
    assert len([r for r in blocco if r.startswith("- ")]) == 8 and blocco[-1].startswith("…e 3 altri"), blocco
    assert "https://finto.local/#/s/lead/p0" in t and h.count("<li") == 9 and "- 10:30 Rossi srl, conoscitiva" in t
    # mai parole tecniche
    for brutta in ("prospect", "proposta", "snella", "operazion", "corse", "registro", "commit", "interaction", "semaforo"):
        assert brutta not in t.lower().replace("aspettano una tua decisione", ""), brutta
    # lo storico dei guasti risolti che tiene guasti.py per questa mail
    import guasti as A
    t0 = datetime.datetime(2026, 10, 20, 9, tzinfo=datetime.timezone.utc)
    stato = {"invio:manda": {"cosa": "L'invio è fermo", "da": t0.isoformat(), "primo": t0.isoformat(), "ultimo": t0.isoformat()}}
    r = A.storico(stato, {}, [], t0 + datetime.timedelta(hours=1))
    assert [(x["chiave"], x["cosa"], x["risolto_il"]) for x in r] == [("invio:manda", "L'invio è fermo", (t0 + datetime.timedelta(hours=1)).isoformat())], r
    assert A.storico(stato, stato, r, t0 + datetime.timedelta(hours=2)) == r, "ancora aperto: niente di nuovo"
    assert A.storico({}, {}, r, t0 + datetime.timedelta(days=3)) == [], "piu' vecchio di 48 ore: via"
    di_notte = {"invio:manda": dict(stato["invio:manda"], risolto=True)}
    assert len(A.storico(stato, di_notte, [], t0 + datetime.timedelta(hours=1))) == 1, "risolto di notte: conta lo stesso"
    assert A.storico(di_notte, di_notte, [], t0 + datetime.timedelta(hours=2)) == [], "gia' segnato risolto: non si raddoppia"
    # l'operazione: giornaliera alle 19, nella corsia leggera; la prova a secco non manda
    import direttore
    assert direttore.corsia_di("giornata") == "leggera"
    sql = open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "supabase", "schema_v96.sql"), encoding="utf-8").read()
    assert "('giornata'" in sql and "'python3 scripts/giornata.py', 1440, '19:00'" in sql, "l'operazione «giornata» alle 19"
    src = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "giornata.py"), encoding="utf-8").read()
    assert "if _a_secco():" in src and src.count("manda_mail(") == 1 and "gia_partita(" in src, "una mail sola, e mai in prova"


@prova("notifica: un indirizzo morto (410 o 404) si toglie, un errore qualunque no, e gli altri dispositivi ricevono")
def _():
    import avvisa as A

    class Rifiuto(Exception):
        def __init__(self, codice):
            super().__init__(f"Push failed: {codice}")
            self.response = type("R", (), {"status_code": codice})()
    mandate = []

    def webpush(subscription_info, **k):
        e = subscription_info["endpoint"]
        if "morto" in e:
            raise Rifiuto(410 if "410" in e else 404)
        if "giu" in e:
            raise Rifiuto(500)
        mandate.append((e, json.loads(k["data"])))
    lista = [{"endpoint": "https://push.finto/vivo", "keys": {}}, {"endpoint": "https://push.finto/morto-410", "keys": {}},
             {"endpoint": "https://push.finto/morto-404", "keys": {}}, {"endpoint": "https://push.finto/giu", "keys": {}}]
    scritte = []

    def sb(m, path, corpo=None, *a, **k):
        if m == "GET" and "preferenze" in path:
            return [{"owner": "u1", "valore": [dict(x) for x in lista]}]
        if m == "PATCH":
            scritte.append((path, corpo))
        return None
    vero = (A._libreria, A.sb, A.env, os.environ.pop("SENZA_PUSH", None))
    A._libreria, A.sb = (lambda: (webpush, Rifiuto)), sb
    A.env = lambda n: "finta" if n == "VAPID_PRIVATE" else None
    try:
        n = A.avvisa("Rossi Finta: «mi chiami»", titolo="Vuole sentirti", url="https://x/#/s/lead/p1", a=["u1"], tag="lead:p1")
    finally:
        A._libreria, A.sb, A.env = vero[:3]
        os.environ["SENZA_PUSH"] = "1"
    assert n == 1 and [e for e, _ in mandate] == ["https://push.finto/vivo"], mandate
    assert mandate[0][1] == {"titolo": "Vuole sentirti", "testo": "Rossi Finta: «mi chiami»", "url": "https://x/#/s/lead/p1", "tag": "lead:p1"}
    assert len(scritte) == 1, scritte
    rimaste = [x["endpoint"] for x in scritte[0][1]["valore"]]
    assert rimaste == ["https://push.finto/vivo", "https://push.finto/giu"], f"dovevano restare il vivo e quello giu': {rimaste}"
    # e le prove non mandano mai: SENZA_PUSH spegne tutto prima di leggere le iscrizioni
    assert A.avvisa("x") == 0


@prova("notifica: la prova va solo al dispositivo appena attivato, una volta, e dopo tre errori si ferma")
def _():
    import avvisa as A
    lista = [{"endpoint": "https://push.finto/vecchio", "keys": {}},
             {"endpoint": "https://push.finto/nuovo", "keys": {}, "benvenuto": "da-mandare"},
             {"endpoint": "https://push.finto/giu", "keys": {}, "benvenuto": "da-mandare"}]
    mandate = []

    def manda_a(i, testo, **k):
        if "giu" in i["endpoint"]:
            raise RuntimeError("500")
        mandate.append(i["endpoint"])
        return True

    def sb(m, path, corpo=None, *a, **k):
        if m == "GET":
            return [{"owner": "u1", "valore": [dict(x) for x in lista]}]
        lista[:] = corpo["valore"]
    vero = (A.manda_a, A.sb, A.env, os.environ.pop("SENZA_PUSH", None))
    A.manda_a, A.sb = manda_a, sb
    A.env = lambda n: "finta" if n == "VAPID_PRIVATE" else None
    try:
        for _giro in range(4):
            A.benvenuti()
    finally:
        A.manda_a, A.sb, A.env = vero[:3]
        os.environ["SENZA_PUSH"] = "1"
    assert mandate == ["https://push.finto/nuovo"], f"la prova doveva partire una volta sola, al nuovo: {mandate}"
    stati = {x["endpoint"].rsplit("/", 1)[1]: x.get("benvenuto") for x in lista}
    assert stati["vecchio"] is None and stati["giu"] == "fallito" and stati["nuovo"].startswith("20"), stati


@prova("web app: l'icona sulla Home apre la versione snella su Oggi, e il tocco su una notifica apre il suo indirizzo")
def _():
    import re as _re
    radice = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    leggi = lambda *p: open(os.path.join(radice, *p), encoding="utf-8").read()   # noqa: E731
    v = leggi("vite.config.ts")
    start = _re.search(r"start_url:\s*'([^']+)'", v).group(1)
    scope = _re.search(r"scope:\s*'([^']+)'", v).group(1)
    assert start == "./#/s/oggi" and scope == "./", (start, scope)
    assert "display: 'standalone'" in v, "senza standalone l'iPhone non da' le notifiche"
    uso = leggi("src", "snella", "uso.tsx")
    rx = _re.search(r"return /(.+)/\.test\(hash\)", uso).group(1)
    assert _re.match(rx.replace("\\/", "/"), "#" + start.split("#", 1)[1]), "lo start_url non e' un indirizzo della versione snella"
    h = leggi("index.html")
    for meta in ("apple-mobile-web-app-capable", "apple-mobile-web-app-title", "viewport-fit=cover", 'sizes="180x180"'):
        assert meta in h, f"manca {meta} in index.html"
    assert os.path.exists(os.path.join(radice, "public", "apple-touch-icon.png")), "manca l'icona per l'iPhone"
    sw = leggi("public", "push.js")
    assert "notificationclick" in sw and "data.url" in sw.replace("dati.url", "data.url"), "il tocco sulla notifica non apre il suo indirizzo"


@prova("calendario: il fuso di Outlook («W. Europe Standard Time») non ferma la lettura (17/10)")
def _():
    import calendario
    d, _ = calendario._quando("20261019T110000", ";TZID=W. Europe Standard Time")
    assert d.utcoffset().total_seconds() == 7200, d
    d, _ = calendario._quando("20261019T110000", ";TZID=Fuso Inventato")
    assert d.tzinfo is not None


@prova("promemoria della conoscitiva: il giorno lavorativo prima, il testo di Dre col suo numero (19/10)")
def _():
    import datetime, promemoria as P
    assert P.giorno_della_call(datetime.date(2026, 10, 23)) == datetime.date(2026, 10, 26)   # venerdi' -> lunedi'
    assert P.giorno_della_call(datetime.date(2026, 10, 20)) == datetime.date(2026, 10, 21)
    assert P.quando_detto(datetime.date(2026, 10, 23), datetime.date(2026, 10, 26)) == "lunedì"
    t = P.testo("domani")
    assert "ci vediamo domani" in t and "371 116 9430" in t and "Dramane" in t
    import bozze
    assert not bozze.cancello(t), bozze.cancello(t)


@prova("foglio della pipeline (19/10): le scritture di Dre si leggono prima e non si riscrivono mai")
def _():
    import datetime, foglio as F
    st = {"scritto": {"a": {"retainer": 1100, "nota": "", "sposta": ""}}, "dre": {}, "mano": {}, "attesa": {}, "call": {}}
    # una cella uguale a quella che il sistema aveva scritto non e' di Dre; una diversa si'
    assert F.scritture_di_dre({"a": {"retainer": 1100, "nota": "", "sposta": ""}}, st) == []
    assert F.scritture_di_dre({"a": {"retainer": 2000, "nota": "", "sposta": ""}}, st) == [("a", "retainer", 2000)]
    assert F.scritture_di_dre({"b": {"retainer": 5}}, st) == [], "una riga mai scritta dal sistema non si indovina"
    # la cella di Dre vince sul dato del database, giro dopo giro
    ora = datetime.datetime(2026, 10, 19, 12, tzinfo=datetime.timezone.utc)
    dati = {"ps": {"a": {"id": "a", "company": "Prova srl", "stage": "cliente", "pipeline_stage": "cliente"}},
            "schede": {}, "dec": {}, "clienti": {"a": {"prospect_id": "a", "dal": "2026-05-01"}}, "agenda": [],
            "retainer": {"a": 1100}, "prova_costo": {}, "interesse": set()}
    st["dre"]["a"] = {"retainer": {"v": 2000, "il": ora.isoformat()}}
    per_fase, _ = F.calcola(dati, st, ora)
    assert per_fase[F.CLIENTE][0]["retainer"] == 2000, per_fase[F.CLIENTE]
    righe, scritto = F.griglia(per_fase, 2000, ora)
    assert scritto["a"]["retainer"] == 2000 and 2000 in righe[F.PRIMA - 1] and scritto["a"]["fase"] == F.CLIENTE
    assert "MRR 2.000 €" in righe[1][F.BLOCCHI[-2]["da"]] and righe[0][0] == F.NOME_FOGLIO
    assert not any("Settimana" in str(c) or "Aggiornato " in str(c) for c in righe[0]), "via la settimana e la frase lunga (Dre, 19/10 sera)"
    assert "sposta" not in F.DI_DRE and not any("sposta" in b["campi"] for b in F.BLOCCHI), "la tendina «Sposta in» non c'e' piu' (Dre, 19/10)"
    # le date e i numeri tornano uguali da come si scrivono a come si rileggono (se no ogni giro
    # sembrerebbe una scrittura di Dre)
    for campo, v in (("inizio", "2026-10-07"), ("costo", 1500), ("retainer", 1100.5), ("nota", "Richiamarlo")):
        assert F.norma(campo, F.in_cella(campo, v)) == v, (campo, v, F.in_cella(campo, v))
    assert F.norma("inizio", "7/10/26") == "2026-10-07" and F.norma("costo", "1.500 €") == 1500
    # un nome d'azienda non diventa mai una formula nel foglio
    assert F.testo("=IMPORTXML(1)").startswith("'") and F.testo("+39 333").startswith("'")


@prova("foglio della pipeline: «Perso» e «Togli» rendono il lead non contattabile; «Da chiamare» lo porta in Oggi")
def _():
    import datetime, foglio as F
    from stanza import contattabile
    oggi = datetime.date(2026, 10, 19)
    lead = {"fuori": False, "stage": "risposto", "pipeline_stage": None, "no_followup": False, "classificazione": "positivo"}
    assert contattabile(lead)
    for campo, valore in (("scelta", "Perso"), (F.SPOSTA, F.TOGLI)):
        p = dict(lead)
        for tabella, cosa in F.effetti(campo, valore, oggi):
            if tabella == "prospects":
                p.update(cosa)
        assert not contattabile(p), (campo, valore, p)
        assert ("snella_lead", {"stato": "Perso"}) in F.effetti(campo, valore, oggi)
    p = dict(lead)
    for tabella, cosa in F.effetti(F.SPOSTA, F.CLIENTE, oggi):
        if tabella == "prospects":
            p.update(cosa)
    assert not contattabile(p), "un cliente spostato dal foglio non si contatta"
    chiama = dict(F.effetti("scelta", "Da chiamare", oggi))["snella_lead"]
    assert chiama["chiamata"] == "richiamare" and chiama["richiamare_il"] == "2026-10-19" and chiama["stato"] == "Da chiamare"
    attesa = dict(F.effetti("scelta", "In attesa di risposta", oggi))
    assert attesa["snella_lead"]["prossima_il"] == "2026-10-24" and attesa["attesa"]


@prova("foglio della pipeline: spostare = copiare il nome in un'altra colonna, togliere = cancellarlo; un nome sconosciuto non fa niente (Dre, 19/10 sera)")
def _():
    import foglio as F
    dati = {"ps": {"a": {"id": "a", "company": "Rossi & Figli S.r.l."}, "b": {"id": "b", "company": "Verdi Serramenti"},
                   "b2": {"id": "b2", "company": "Verdi Serramenti"}, "c": {"id": "c", "company": "Bianchi"}}}
    st = {"scritto": {"a": {"fase": F.INVIATA}, "b": {"fase": F.CONV}, "c": {"fase": F.CONO}}, "mano": {}, "dre": {}}
    # il nome incollato sotto un'altra fase, anche scritto diverso (maiuscole, accenti, punteggiatura)
    mosse, ignoti = F.mosse_di_dre([(F.PROVA_F, "ROSSI & figli s.r.l."), (F.CLIENTE, "VERDI SERRAMENTI")], [], st, dati)
    assert mosse == [("a", F.SPOSTA, F.PROVA_F), ("b", F.SPOSTA, F.CLIENTE)] and not ignoti, (mosse, ignoti)
    assert F.chiave_nome("Città Più S.p.A.") == F.chiave_nome("citta piu spa")
    # incollato dove sta gia': non e' una mossa. Un nome che non si conosce: niente, e si tiene da parte
    mosse, ignoti = F.mosse_di_dre([(F.CONV, "Verdi Serramenti"), (F.CLIENTE, "Azienda Inventata")], [], st, dati)
    assert mosse == [] and ignoti == [(F.CLIENTE, "Azienda Inventata")]
    # il nome cancellato dalla riga del sistema = togli; una riga che il sistema non ha scritto no
    mosse, _ = F.mosse_di_dre([], ["c", "zz"], st, dati)
    assert mosse == [("c", F.SPOSTA, F.TOGLI)]
    # taglia e incolla (il primo caso vero, 19/10 sera): la riga vecchia senza nome non e' un togli
    mosse, _ = F.mosse_di_dre([(F.PROVA_F, "Bianchi")], ["c"], st, dati)
    assert mosse == [("c", F.SPOSTA, F.PROVA_F)], mosse
    # e gli ignoti restano nel foglio, in fondo alla loro colonna, senza id
    import datetime
    righe, scritto = F.griglia({f: [] for f in F.FASI}, 0, datetime.datetime(2026, 10, 19, tzinfo=datetime.timezone.utc), ignoti)
    assert righe[F.PRIMA - 1][F.BLOCCHI[-2]["da"]] == "Azienda Inventata" and "Azienda Inventata" not in str(scritto)


@prova("foglio della pipeline: la data sopra un blocco cambia solo se il blocco cambia (Dre, 19/10 sera)")
def _():
    import datetime, foglio as F
    t0 = datetime.datetime(2026, 10, 19, 14, 0, tzinfo=datetime.timezone.utc)
    t1 = t0 + datetime.timedelta(minutes=10)
    t2 = t1 + datetime.timedelta(minutes=10)
    lead = lambda i, d="oggi 10:00": {"id": i, "azienda": "Azienda " + i, "dettaglio": d}      # noqa: E731
    st = {}
    per_fase = {f: [] for f in F.FASI}
    per_fase[F.INVIATA] = [lead("a"), lead("b")]
    date = F.date_blocchi(per_fase, st, t0)
    assert all(d == t0 for d in date.values()), "alla nascita tutti i blocchi hanno la data della nascita"
    date = F.date_blocchi(per_fase, st, t1)
    assert all(d == t0 for d in date.values()), "un giro senza cambiamenti non cambia le date"
    per_fase[F.CONV] = [lead("c")]
    date = F.date_blocchi(per_fase, st, t2)
    assert date[F.CONV] == t2 and date[F.INVIATA] == t0 and date[F.CLIENTE] == t0, date
    per_fase[F.INVIATA][0]["dettaglio"] = "ieri 10:00"
    t3 = t2 + datetime.timedelta(minutes=10)
    assert F.date_blocchi(per_fase, st, t3)[F.INVIATA] == t3, "cambia il dettaglio di un lead: il blocco e' cambiato"
    righe, _ = F.griglia(per_fase, 0, t3, (), F.date_blocchi(per_fase, st, t3))
    assert righe[0][0] == F.NOME_FOGLIO and righe[0][1].startswith("Ultima modifica lun 19/10")
    assert righe[0][F.BLOCCHI[1]["da"]] == "Ultima modifica lun 19/10 16:30", righe[0][F.BLOCCHI[1]["da"]]
    assert righe[0][F.BLOCCHI[2]["da"]] == "Ultima modifica lun 19/10 16:20"


@prova("foglio della pipeline, Progetti (Dre, 19/10 sera): una riga nuova nasce dal foglio, Dre vince, cancellata = tolta")
def _():
    import datetime, foglio as F
    ora = datetime.datetime(2026, 10, 19, 17, tzinfo=datetime.timezone.utc)
    st = {}
    clienti = {F.chiave_nome("Rossi Srl"): "pid-rossi"}
    # una riga col cliente e senza id: un progetto nuovo, collegato al cliente per nome, «In corso» se manca lo stato
    F.progetti_dal_foglio([{"id": "", "cliente": "ROSSI srl", "progetto": "Sito", "importo": 2500, "consegna": "2026-11-15",
                            "stato": "", "nota": ""}], st, clienti, ora)
    (pid, p), = st["progetti"].items()
    assert pid == "pr-1" and p["stato"] == "In corso" and p["prospect_id"] == "pid-rossi" and p["importo"] == 2500
    # al giro dopo la riga ha il suo id; quello che Dre cambia vince e resta
    F.progetti_dal_foglio([{"id": "pr-1", "cliente": "ROSSI srl", "progetto": "Sito", "importo": 2800, "consegna": "2026-11-15",
                            "stato": "Consegnato", "nota": "manca il logo"}], st, clienti, ora)
    assert p["importo"] == 2800 and p["stato"] == "Consegnato" and p["nota"] == "manca il logo"
    righe = F.righe_progetti(st)
    assert righe[0]["id"] == "pr-1" and righe[0]["importo"] == 2800, "il foglio riscrive il valore di Dre, non un altro"
    # una riga vuota senza id non crea niente; una riga col suo id svuotata e' «tolta», non persa
    F.progetti_dal_foglio([{"id": "", "cliente": "", "progetto": "", "importo": "", "consegna": "", "stato": "", "nota": ""}], st, clienti, ora)
    assert list(st["progetti"]) == ["pr-1"]
    F.progetti_dal_foglio([{"id": "pr-1", "cliente": "", "progetto": "", "importo": "", "consegna": "", "stato": "", "nota": ""}], st, clienti, ora)
    assert st["progetti"]["pr-1"]["tolto_il"] and st["progetti"]["pr-1"]["importo"] == 2800 and F.righe_progetti(st) == []
    # l'ordine: In corso per consegna piu' vicina, poi Consegnato, poi Pagato
    st2 = {"progetti": {"a": {"cliente": "A", "stato": "Pagato", "consegna": "2026-10-01"},
                        "b": {"cliente": "B", "stato": "In corso", "consegna": "2026-12-01"},
                        "c": {"cliente": "C", "stato": "Consegnato", "consegna": "2026-10-10"},
                        "d": {"cliente": "D", "stato": "In corso", "consegna": "2026-11-01"}}}
    assert [r["id"] for r in F.righe_progetti(st2)] == ["d", "b", "c", "a"]
    # l'intestazione: la somma degli importi non ancora pagati
    vista = {f: [] for f in F.FASI}
    vista[F.PROGETTI] = [{"id": "x", "azienda": "X", "cliente": "X", "importo": 1000, "stato": "In corso"},
                         {"id": "y", "azienda": "Y", "cliente": "Y", "importo": 500, "stato": "Pagato"}]
    righe, scritto = F.griglia(vista, 0, ora)
    assert righe[1][F.BLOCCHI[-1]["da"]] == "Progetti · 2 · una tantum 1.000 € (in corso)" and "x" not in scritto


@prova("foglio della pipeline: nessuna mail parte dal foglio (niente postino, bozze, Gmail o Smartlead)")
def _():
    import datetime, re as _re, foglio as F
    radice = os.path.dirname(os.path.abspath(__file__))
    src = open(os.path.join(radice, "foglio.py"), encoding="utf-8").read()
    codice = "\n".join(r for r in src.splitlines() if not r.lstrip().startswith("#"))
    codice = _re.sub(r'"""[\s\S]*?"""', "", codice)
    for vietato in ("import manda", "from manda", "import lettura", "import bozze", "prima_risposta", "gmail", "smartlead",
                    "/proposte", "manda_mail", "postino"):
        assert vietato not in codice.lower(), f"foglio.py tocca «{vietato}»"
    assert set(_re.findall(r'proponi\("(\w+)"', codice)) == {"umano"}, "il foglio fa solo domande a Dre, mai bozze"
    oggi = datetime.date(2026, 10, 19)
    for campo in (*F.DI_DRE, F.SPOSTA):
        for v in ("", "x", 100, "2026-10-21", F.TOGLI, *F.FASI, *F.SCELTE):
            for tabella, _ in F.effetti(campo, v, oggi):
                assert tabella in ("prospects", "snella_lead", "snella_note", "mano", "attesa"), (campo, v, tabella)
    import direttore
    assert direttore.corsia_di("foglio") == "leggera"


@prova("sync: «grazie per la disponibilità ma abbiamo già un'agenzia» e' un no, non un si' (19/10)")
def _():
    import sync_v2 as S
    assert S.classifica("Grazie per la vostra disponibilità ma già abbiamo una agenzia che ci segue.") == "negativo"
    assert S.classifica("Nel ringraziarvi per la disponibilità, abbiamo un'agenzia che si occupa della comunicazione.") == "negativo"
    assert S.classifica("Grazie per la disponibilità, va bene mandi pure l'analisi.") == "positivo"
    assert S.classifica("Sono disponibile per una call domani alle 15.") == "positivo"


@prova("calendario: un appunto senza invitati non e' una call (19/10)")
def _():
    import calendario as C
    at = "@"
    assert C.tipo_evento({"titolo": "preparare la bozza di proposta da inviare ad Anthony", "invitati": []}) == "altro"
    assert C.tipo_evento({"titolo": "Bozza di proposta e analisi", "invitati": ["dramane" + at + "studiogalilei.com"]}) == "altro"
    # una call col nome esplicito resta una call anche se l'invitato esterno manca (prenotata a mano da Dre)
    assert C.tipo_evento({"titolo": "StudioGalilei - Chiamata conoscitiva (Mario Rossi)", "invitati": []}) == "conoscitiva"
    # ma una prenotazione di prova fatta da uno di noi no
    assert C.tipo_evento({"titolo": "StudioGalilei - Chiamata conoscitiva (Carlo)", "invitati": ["carlo" + at + "studiogalilei.com"],
                          "descrizione": "<b>Prenotato da</b> Carlo carlo" + at + "studiogalilei.com"}) == "altro"
    assert C.tipo_evento({"titolo": "Call Tecnica e proposta", "invitati": ["mario" + at + "azienda.it"]}) == "tecnica"
    assert C.tipo_evento({"titolo": "45 Min with Carlo | Performance Marketing (Mario Rossi)", "invitati": ["mario" + at + "azienda.it"]}) == "tecnica"


@prova("sync: «Cancellami» e' un no (collaudo 19/10)")
def _():
    import sync_v2 as S
    assert S.classifica("Cancellami") == "negativo"
    assert S.classifica("Cancellateci dalla lista") == "negativo"


# ── una notifica sola: il lead entrato in conversazione (20/10) ──
class _ConversazioniFinte:
    """Un database finto per conversazioni.py: un lead con l'analisi mandata, le sue risposte,
    la memoria delle letture e lo stato in snella_numeri. Le notifiche si contano in `notifiche`."""

    def __init__(self, analisi_ore_fa=48, letture=None, stato=None):
        self.ora = datetime.datetime.now(datetime.timezone.utc)
        self.analisi = (self.ora - datetime.timedelta(hours=analisi_ore_fa)).strftime("%Y-%m-%dT%H:%M:%S+00:00") \
            if analisi_ore_fa is not None else None
        self.letture = letture or {}
        self.risposte, self.memoria, self.notifiche, self.ai = [], {}, [], []
        self.stato = stato                          # None = la chiave non c'e' ancora (la prima accensione)
        self.dispositivi = 1                        # 0 = la notifica non arriva a nessuno
        self.caldo = False                          # il lettore AI ha letto calda la sua ultima mail (20/10 sera)
        self.snella_lead = {}                       # le decisioni nell'app (quello che scrive «Da chiamare»)

    def scrive(self, testo, minuti_fa=30, pid="p1"):
        at = (self.ora - datetime.timedelta(minutes=minuti_fa)).strftime("%Y-%m-%dT%H:%M:%S+00:00")
        self.risposte.append({"id": f"i{len(self.risposte) + 1}", "prospect_id": pid, "at": at, "created_at": at, "body": testo, "kind": "email_in"})

    def sb(self, m, path, corpo=None, *a, **k):
        import re as _re
        import urllib.parse as _u
        path = _u.unquote(path)
        if path.startswith("/rest/v1/interactions"):
            rr = [dict(r) for r in self.risposte]
            pid = _re.search(r"prospect_id=eq\.([^&]+)", path)
            return [r for r in rr if not pid or r["prospect_id"] == pid.group(1)]
        if path.startswith("/rest/v1/prospects"):
            ultima = max((r["at"] for r in self.risposte), default=None)
            riga = {"id": "p1", "company": "Azienda Finta", "name": "Mario", "analysis_sent_at": self.analisi,
                    "stage": "in_follow_up", "pipeline_stage": None, "classificazione": "positivo", "fuori": False,
                    "no_followup": False, "last_reply_at": ultima}
            if "lettore" in path:                   # la domanda dei caldi del lettore
                if not self.caldo or not self.risposte:
                    return []
                prima = min(r["at"] for r in self.risposte)
                riga["lettore"] = {"fonte": "lettore", "classe": "positivo", "caldo": True, "caso": "C05", "risposta_il": prima[:19]}
            return [riga]
        if path.startswith("/rest/v1/snella_lead"):
            if m == "GET":
                pid = _re.search(r"prospect_id=eq\.([^&]+)", path)
                return [dict(self.snella_lead[pid.group(1)])] if pid and pid.group(1) in self.snella_lead else []
            for r in corpo:
                self.snella_lead[r["prospect_id"]] = {**self.snella_lead.get(r["prospect_id"], {}), **r}
            return None
        if path.startswith("/rest/v1/snella_numeri"):
            if m == "GET":
                return [{"dati": json.loads(json.dumps(self.stato))}] if self.stato is not None else []
            self.stato = json.loads(json.dumps(corpo[0]["dati"]))
            return None
        if path.startswith("/rest/v1/memoria_letture"):
            if m == "GET":
                c = path.split("chiave=eq.")[1]
                return [{"valore": self.memoria[c]}] if c in self.memoria else []
            for r in corpo:
                self.memoria[r["chiave"]] = r["valore"]
            return None
        return []

    def chiedi(self, prompt):
        self.ai.append(prompt)
        for chiave, v in self.letture.items():
            if chiave in prompt:
                return json.dumps(v)
        return json.dumps({"autorisposta": False, "caldo": False, "si": False, "frase": "", "telefono": "", "consiglio": ""})

    def push(self, titolo, testo, url, tag):
        if self.dispositivi:
            self.notifiche.append({"titolo": titolo, "testo": testo, "url": url})
        return self.dispositivi

    def giro(self, prova=False):
        import conversazioni as C
        import segnale_provvisorio as S
        import stanza as St
        vero = (C.sb, S.sb, St.sb, S._chiedi_ai, S._push, S._restano_oggi, C.adesso)
        C.sb = S.sb = St.sb = self.sb
        # schede.py, importato da una prova prima, azzera le letture pagabili: qui servono
        S._chiedi_ai, S._push, S._restano_oggi, C.adesso = self.chiedi, self.push, lambda: 100, lambda: self.ora
        S.GIRO.update(pagate=0, memoria_rotta=False, sonda=False, giorno_restano=100, tetto_giorno=False)
        try:
            return C.giro(prova=prova)
        finally:
            C.sb, S.sb, St.sb, S._chiedi_ai, S._push, S._restano_oggi, C.adesso = vero


FUORI_UFFICIO = {"autorisposta": True, "caldo": False, "si": False, "frase": "", "telefono": "", "consiglio": ""}


@prova("conversazione: chi risponde dopo l'analisi suona UNA volta, anche se scrive due volte (20/10)")
def _():
    f = _ConversazioniFinte(stato={})
    f.scrive("Grazie per l'analisi, ci sentiamo la settimana prossima per capire i costi", minuti_fa=20)
    f.giro()
    assert len(f.notifiche) == 1, f.notifiche
    n = f.notifiche[0]
    assert n["titolo"].startswith("È entrato in conversazione") and "Azienda Finta" in n["titolo"], n
    assert n["url"].endswith("#/s/lead/p1"), n["url"]
    assert f.stato["p1"]["notificata"] is True and f.stato["p1"]["dal"], f.stato
    f.scrive("Ah, dimenticavo: ci mandi anche un preventivo?", minuti_fa=2)
    f.giro()
    f.giro()
    assert len(f.notifiche) == 1, f"la stessa conversazione ha suonato {len(f.notifiche)} volte"


@prova("conversazione: un fuori ufficio dopo l'analisi non suona, ne' l'ovvio ne' quello che legge l'AI (20/10)")
def _():
    f = _ConversazioniFinte(stato={})
    f.scrive("Sono fuori ufficio fino al 26 ottobre, rispondero' al mio rientro.")
    f.giro()
    assert f.notifiche == [] and "p1" not in f.stato and f.ai == [], (f.notifiche, f.stato)
    # un fuori ufficio col cellulare non e' «ovvio»: lo legge l'AI, e l'AI dice autorisposta
    f = _ConversazioniFinte(stato={}, letture={"assente fino": FUORI_UFFICIO})
    f.scrive("Messaggio automatico: sono assente fino a lunedi', per urgenze 333 1234567")
    f.giro()
    assert f.notifiche == [] and "p1" not in f.stato, (f.notifiche, f.stato)


@prova("conversazione: un «no grazie» dopo l'analisi suona (Dre: «se risponde e' in conversazione»)")
def _():
    f = _ConversazioniFinte(stato={}, letture={"non siamo interessati": {**FUORI_UFFICIO, "autorisposta": False}})
    f.scrive("Grazie per l'analisi ma non siamo interessati.")
    f.giro()
    assert len(f.notifiche) == 1 and f.stato["p1"]["notificata"] is True, (f.notifiche, f.stato)


@prova("conversazione: prima dell'analisi nessuna risposta suona, e senza analisi nemmeno")
def _():
    f = _ConversazioniFinte(analisi_ore_fa=1, stato={})
    f.scrive("Si', mandatemi pure l'analisi", minuti_fa=120)       # il si' arrivato prima dell'analisi
    f.giro()
    assert f.notifiche == [] and "p1" not in f.stato, (f.notifiche, f.stato)
    f = _ConversazioniFinte(analisi_ore_fa=None, stato={})
    f.scrive("Si', mandatemi pure l'analisi")
    f.giro()
    assert f.notifiche == [] and "p1" not in f.stato, (f.notifiche, f.stato)


@prova("conversazione: una notifica che non arriva resta «non notificata» e riparte, una volta sola")
def _():
    f = _ConversazioniFinte(stato={})
    f.dispositivi = 0
    f.scrive("Grazie, ci risentiamo a novembre")
    f.giro()
    assert f.notifiche == [] and f.stato["p1"]["notificata"] is False, f.stato
    f.dispositivi = 1
    f.giro()
    f.giro()
    assert len(f.notifiche) == 1 and f.stato["p1"]["notificata"] is True, (f.notifiche, f.stato)


@prova("conversazione: la prova a secco non scrive e non suona; la prima accensione non fa suonare il passato")
def _():
    f = _ConversazioniFinte(stato={})
    f.scrive("Grazie, ci risentiamo a novembre")
    trovate = f.giro(prova=True)
    assert f.notifiche == [] and f.stato == {} and len(trovate) == 1, (f.notifiche, f.stato, trovate)
    # la chiave non c'e' ancora: le conversazioni vecchie di ore si segnano senza suonare
    f = _ConversazioniFinte(stato=None)
    f.scrive("Grazie, ci risentiamo a novembre", minuti_fa=300)
    f.giro()
    assert f.notifiche == [] and f.stato["p1"]["notificata"] is True, (f.notifiche, f.stato)
    # una conversazione cominciata giorni fa (prima della finestra) non suona alla risposta nuova
    f = _ConversazioniFinte(analisi_ore_fa=24 * 10, stato={})
    f.scrive("Grazie, ci risentiamo a novembre", minuti_fa=60 * 24 * 5)
    f.scrive("Eccomi, ora possiamo sentirci", minuti_fa=10)
    f.giro()
    assert f.notifiche == [] and f.stato["p1"]["notificata"] is True, (f.notifiche, f.stato)


@prova("notifiche: sul telefono suona solo la conversazione; segnali, prenotazioni, bozze e foglio restano mail o Posta")
def _():
    import pathlib
    cartella = pathlib.Path(__file__).parent
    for nome in ("foglio.py", "bozze.py"):
        t = (cartella / nome).read_text(encoding="utf-8")
        assert ".notifica(" not in t and "avvisa(" not in t, f"{nome} manda ancora una notifica sul telefono"
    s = (cartella / "segnale_provvisorio.py").read_text(encoding="utf-8")
    assert "notifica_segnali" not in s and "notifica_prenotazione" not in s, "il segnale manda ancora le sue notifiche"
    chiamanti = sorted(f.name for f in cartella.glob("*.py") if f.name != "test_invarianti.py"
                       and ("SP.notifica(" in f.read_text(encoding="utf-8") or "S.notifica(" in f.read_text(encoding="utf-8")))
    assert chiamanti == ["conversazioni.py"], chiamanti


@prova("foglio: link e prossimo (20/10): la scheda, il filo su Smartlead, il prossimo messaggio")
def _():
    import datetime, foglio as F, foglio_lead as L
    assert L.link_scheda("x").endswith("#/s/lead/x")
    assert L.link_filo({}) is None and L.link_filo({"company": "Aggiunto a mano"}) is None, "senza campagna niente filo"
    assert L.link_filo({"campaign_id": 7, "lead_id": 9}, 123).endswith("/app/master-inbox?action=INBOX&leadMap=123")
    assert "filterCampaignId=7" in L.link_filo({"campaign_id": 7, "lead_id": 9, "email": "a" + "@b.it"})
    ora = datetime.datetime(2026, 10, 20, 9, tzinfo=datetime.timezone.utc)            # martedi'
    giovedi = "2026-10-22"
    fu = {"id": 1, "prospect_id": "p1", "tipo": "risposta", "stato": "approvata", "titolo": "Bozza per X",
          "azione": {"bozza": "Buongiorno, le riscrivo...", "parte_il": giovedi, "lettura": {"gruppo": "FOLLOW UP 1"}}}
    m = L.prossimo_messaggio("p1", {"proposte": {"p1": [fu]}, "calendario": {}}, ora)
    assert m and m[0].date().isoformat() == giovedi and m[1] == "follow-up" and m[2].startswith("Buongiorno"), m
    assert L.prossimo_messaggio("p1", {"proposte": {}, "calendario": {}}, ora) is None
    # una bozza aperta che aspetta una persona non e' in piano; un follow-up del codice si'
    aperta = dict(fu, stato="aperta", azione=dict(fu["azione"], lettura={"gruppo": "INT-08"}))
    assert L.prossimo_messaggio("p1", {"proposte": {"p1": [aperta]}, "calendario": {}}, ora) is None
    aperta["azione"] = dict(fu["azione"], testo_dal_codice=True)
    assert L.prossimo_messaggio("p1", {"proposte": {"p1": [aperta]}, "calendario": {}}, ora)[1] == "follow-up"
    # una domanda a Dre non e' un messaggio; il calendario dei follow-up si'
    domanda = dict(fu, titolo="Da guardare tu: X")
    cal = {"p1": {"prospect_id": "p1", "gruppo": "FOLLOW UP 1", "il": "2026-10-23"}}
    m = L.prossimo_messaggio("p1", {"proposte": {"p1": [domanda]}, "calendario": cal}, ora)
    assert m[0].date().isoformat() == "2026-10-23" and m[2] == "", m
    assert L.prossimo_breve(["p1"], {"proposte": {}, "calendario": cal}, ora) == "ven 23/10"
    # nel foglio: le colonne strette dei link accanto all'azienda, il «prossimo» dove il sistema scrive
    for b in F.BLOCCHI[:-1]:
        assert b["campi"][:3] == ["azienda", "scheda", "filo"], b["campi"]
    assert {b["fase"] for b in F.BLOCCHI if "prossimo" in b["campi"]} == {F.PREP, F.INVIATA, F.CONV}
    dati = {"ps": {"a": {"id": "a", "company": "Prova srl", "last_reply_at": "2026-10-19T08:00:00+00:00",
                         "analysis_sent_at": "2026-10-15T08:00:00+00:00", "campaign_id": 7, "lead_id": 9},
                   "b": {"id": "b", "company": "A mano srl", "last_reply_at": "2026-10-19T08:00:00+00:00",
                         "analysis_sent_at": "2026-10-19T09:00:00+00:00"}},
            "schede": {}, "dec": {}, "clienti": {}, "agenda": [], "retainer": {}, "prova_costo": {}, "interesse": set(),
            "piano": {"proposte": {}, "calendario": {"b": {"prospect_id": "b", "gruppo": "FOLLOW UP 1", "il": "2026-10-22"}}}}
    st = {"scritto": {}, "dre": {}, "mano": {}, "attesa": {}, "call": {}, "mappe": {"a": 555}}
    per_fase, _ = F.calcola(dati, st, ora)
    righe, _ = F.griglia(per_fase, 0, ora)
    b = next(x for x in F.BLOCCHI if x["fase"] == F.CONV)
    riga = next(r for r in righe[F.PRIMA - 1:] if r[b["da"]] == "Prova srl")
    assert riga[F.colonna(b, "filo")] == '=HYPERLINK("https://app.smartlead.ai/app/master-inbox?action=INBOX&leadMap=555";"filo")', riga
    assert riga[F.colonna(b, "scheda")].startswith('=HYPERLINK("') and '#/s/lead/a"' in riga[F.colonna(b, "scheda")]
    b2 = next(x for x in F.BLOCCHI if x["fase"] == F.INVIATA)
    riga2 = next(r for r in righe[F.PRIMA - 1:] if r[b2["da"]] == "A mano srl")
    assert riga2[F.colonna(b2, "filo")] == "", "un lead senza filo: cella vuota, il foglio non cade"
    assert riga2[F.colonna(b2, "prossimo")] == "'gio 22/10", "testo, non una data"


@prova("scheda Clara (20/10): il semaforo vede i guasti che costano lead, il diario parla come Dre")
def _():
    import datetime, clara_foglio as C
    roma = C.ROMA
    alle = lambda h, m=0: datetime.datetime(2026, 10, 20, h, m, tzinfo=roma)        # noqa: E731
    vuoto = lambda: {"si": [], "corse": {}, "operazioni": {}, "foglio_il": None, "conversazioni": None, "ultima_corsa": None}  # noqa: E731
    assert C.semaforo(alle(11), vuoto()) == [], "nessun problema: verde"
    # un si' arrivato 61 minuti fa alle 11, senza analisi: guasto. Lo stesso alle 23: niente
    d = vuoto()
    d["si"] = [{"prospect_id": "p1", "azienda": "Rossi srl", "quando": alle(9, 59)}]
    g = C.semaforo(alle(11), d)
    assert len(g) == 1 and "Rossi srl" in g[0]["cosa"] and g[0]["da"] == alle(9, 59) and g[0]["sta_facendo"], g
    # 20/10 sera: la riga rossa di un lead porta alla sua scheda (un clic e ci sono i pulsanti); le altre restano testo
    valori, n = C.griglia(g + [{"chiave": "foglio", "da": alle(9, 50), "cosa": "Il foglio non si aggiorna da 1 ora", "sta_facendo": "Riprova."}], [], alle(11))
    assert n == 2 and valori[1][1].startswith('=HYPERLINK("https://') and "#/s/lead/p1" in valori[1][1] and '";"Sì senza analisi: Rossi srl' in valori[1][1], valori[1]
    assert valori[2][1] == "Il foglio non si aggiorna da 1 ora", valori[2]
    assert C.cosa_del_guasto({"pid": "p9", "cosa": 'Rossi "srl"'}).endswith(';"Rossi ""srl""")'), "le virgolette raddoppiate, la formula non si rompe"
    d["si"] = [{"prospect_id": "p1", "azienda": "Rossi srl", "quando": alle(21, 59)}]
    assert C.semaforo(alle(23), d) == []
    # arrivato alle 7: alle 8:30 non e' ancora fermo (l'invio parte alle 8), alle 9:01 si'
    d["si"] = [{"prospect_id": "p1", "azienda": "Rossi srl", "quando": alle(7)}]
    assert C.semaforo(alle(8, 30), d) == [] and len(C.semaforo(alle(9, 1), d)) == 1
    # tre corse di manda in errore: l'invio e' fermo
    d = vuoto()
    d["operazioni"] = {"manda": {"chiave": "manda", "nome": "Clara manda", "attiva": True, "cadenza_minuti": 5}}
    d["corse"] = {"manda": [{"at": alle(10, 50 - 5 * i), "esito": "errore", "dettaglio": "boh"} for i in range(3)]}
    g = C.semaforo(alle(11), d)
    assert len(g) == 1 and g[0]["chiave"] == "invio:manda" and g[0]["da"] == alle(10, 40), g
    d["corse"]["manda"][0]["esito"] = "ok"
    assert C.semaforo(alle(11), d) == [], "l'ultima corsa e' andata: non e' fermo"
    # nessuna corsa da piu' di un'ora, in orario: fermo; di notte no
    d["corse"] = {"manda": [{"at": alle(9, 50), "esito": "ok", "dettaglio": ""}]}
    assert [x["chiave"] for x in C.semaforo(alle(11), d)] == ["invio:manda"]
    assert C.semaforo(alle(23), d) == [], "di notte il silenzio non e' un guasto"
    # i crediti finiti: anche un'operazione qualunque, se l'ultima corsa lo dice
    d["corse"] = {"manda": [{"at": alle(10, 55), "esito": "errore", "dettaglio": "Error code: 429 insufficient_quota"}]}
    assert [x["chiave"] for x in C.semaforo(alle(11), d)] == ["chiave:manda"]
    # il foglio fermo da piu' di un'ora; il direttore fermo
    d = vuoto()
    d["foglio_il"] = alle(9, 50)
    assert [x["chiave"] for x in C.semaforo(alle(11), d)] == ["foglio"]
    d = vuoto()
    d["ultima_corsa"] = alle(10, 35)
    assert C.semaforo(alle(11), d) == [], "25 minuti senza corse: la sentinella lo rianima, non e' ancora un guasto"
    d["ultima_corsa"] = alle(10, 25)
    assert [x["chiave"] for x in C.semaforo(alle(11), d)] == ["direttore"]
    # la conversazione senza notifica: spenta finche' la chiave non c'e'
    d = vuoto()
    d["conversazioni"] = {"p1": {"dal": alle(9, 50).isoformat(), "notificata": False, "azienda": "Rossi srl"},
                          "p2": {"dal": alle(9, 50).isoformat(), "notificata": True},
                          "p3": {"dal": alle(10, 30).isoformat(), "notificata": False}}
    assert [x["chiave"] for x in C.semaforo(alle(11), d)] == ["conversazione:p1"], "senza notifica da piu' di un'ora; mezz'ora no (riprova)"
    # 20/10 sera: si misura da quando il giro l'ha aperta, non dalla sua mail (il si' caldo letto ore dopo)
    d["conversazioni"] = {"p4": {"dal": alle(7).isoformat(), "aperta_il": alle(10, 50).isoformat(), "notificata": False, "caldo": True, "azienda": "Calda srl"},
                          "p5": {"dal": alle(7).isoformat(), "aperta_il": alle(9, 50).isoformat(), "notificata": False, "caldo": True, "azienda": "Calda srl"}}
    g = C.semaforo(alle(11), d)
    assert [x["chiave"] for x in g] == ["conversazione:p5"] and "vuole sentirti" in g[0]["cosa"], g
    # i guasti del segnale provvisorio confluiscono qui: rossi finche' il segnale li rivede (20 minuti)
    d = vuoto()
    d["segnale"] = {"gmail": {"testo": "Il segnale non riesce a mandarti la mail", "il": alle(10, 55).isoformat(), "dal": alle(9).isoformat()},
                    "memoria": {"testo": "vecchio", "il": alle(10, 20).isoformat()}}
    g = C.semaforo(alle(11), d)
    assert [x["chiave"] for x in g] == ["segnale:gmail"] and g[0]["da"] == alle(9), g
    assert C.conversazioni_aperte({}) is None
    # il diario: la riga piu' recente in alto, parole di Dre
    eventi = {"analisi": [("p1", alle(9))], "fatte": [("p2", alle(10), "FOLLOW UP 1"), ("p3", alle(10, 30), "PROMEMORIA")],
              "no": [("p4", alle(8))], "conversazioni": [("p5", alle(10, 45))], "call": [], "nomi": {
                  "p1": "Uno srl", "p2": "Due srl", "p3": "Tre srl", "p4": "Quattro srl", "p5": "Cinque srl"}}
    righe = C.diario(alle(11), eventi=eventi)
    assert [r[1] for r in righe] == ["Cinque srl", "Tre srl", "Due srl", "Uno srl", "Quattro srl"], righe
    cose = " ".join(r[2] for r in righe)
    for frase in ("Analisi mandata", "Follow-up partito", "Ha detto no", "È entrato in conversazione"):
        assert frase in cose, (frase, cose)
    for tecnico in ("prospect", "proposta", "FOLLOW UP 1", "INT-", "classificazione"):
        assert tecnico not in cose, tecnico
    # 20/10 sera: un rimbalzo interno «da_classificare» e' un si' fermo, e il semaforo lo deve vedere
    vero_cont = C.contattabile
    try:
        C.contattabile = lambda p: not p.get("fuori")
        proposte = [{"prospect_id": "r1"}, {"prospect_id": "r2"}, {"prospect_id": "r3"}, {"prospect_id": "r4"}, {"prospect_id": "s1"}]
        schede = [{"id": "r1", "company": "Falegnameria Finta", "classificazione": "da_classificare", "analysis_sent": False, "fuori": False, "last_reply_at": alle(8, 56).isoformat()},
                  {"id": "r2", "company": "Gia' Servita", "classificazione": "da_classificare", "analysis_sent": True, "fuori": False, "last_reply_at": alle(8).isoformat()},
                  {"id": "r3", "company": "Positiva srl", "classificazione": "positivo", "analysis_sent": False, "fuori": False, "last_reply_at": alle(8).isoformat()},
                  {"id": "r4", "company": "In Pipeline", "classificazione": "da_classificare", "analysis_sent": False, "fuori": True, "last_reply_at": alle(8).isoformat()},
                  {"id": "s1", "company": "Col Segnale", "classificazione": "da_classificare", "analysis_sent": False, "fuori": False, "last_reply_at": alle(8).isoformat()}]
        r = C.rimbalzi_fermi(alle(11), gia={"s1"}, proposte=proposte, schede=schede)
        assert [x["azienda"] for x in r] == ["Falegnameria Finta"] and r[0]["quando"] == alle(8, 56) and r[0]["bozza"], r
        # 20/10 sera: se il lettore ha letto la sua ultima mail, decide lui cos'e' un rimbalzo
        lett = lambda caso: {"fonte": "lettore", "caso": caso, "classe": "da_classificare", "risposta_il": alle(8, 56).isoformat()[:19]}  # noqa: E731
        girata = {**schede[0], "id": "r5", "company": "L'ho Girata", "lettore": lett("C36")}
        indirizzo = {**schede[0], "id": "r6", "company": "Altro Indirizzo", "lettore": lett("C35")}
        vecchia = {**schede[0], "id": "r7", "company": "Lettura Vecchia", "lettore": {**lett("C36"), "risposta_il": "2026-10-01T08:00:00"}}
        r2 = C.rimbalzi_fermi(alle(11), proposte=[{"prospect_id": "r5"}, {"prospect_id": "r6"}, {"prospect_id": "r7"}], schede=[girata, indirizzo, vecchia])
        assert [x["azienda"] for x in r2] == ["Altro Indirizzo", "Lettura Vecchia"], [x["azienda"] for x in r2]
        d = vuoto()
        d["si"] = r
        g = C.semaforo(alle(11), d)
        assert len(g) == 1 and "Falegnameria Finta" in g[0]["cosa"] and "8:56" in g[0]["cosa"], g
        assert C.rimbalzi_fermi(alle(11), proposte=[], schede=schede) == []
        src_c = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "clara_foglio.py"), encoding="utf-8").read()
        assert "rimbalzi_fermi(ora, gia=" in src_c, "si_fermi deve sommare i rimbalzi"
    finally:
        C.contattabile = vero_cont
    # la scheda Clara e i link leggono e basta: niente scritture nel database, niente mail
    import re as _re
    for nome in ("clara_foglio.py", "foglio_lead.py"):
        src = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), nome), encoding="utf-8").read()
        assert not _re.search(r'sb\("(?:POST|PATCH|DELETE)', src) and "proponi(" not in src and "import manda" not in src, nome
        assert "method=" not in src and "data=" not in src, f"{nome}: a Smartlead solo domande (GET)"


@prova("avvisi di guasto (20/10): una notifica alla prima volta, poi ogni 2 ore, poi «Risolto»")
def _():
    import datetime, guasti as A
    t0 = datetime.datetime(2026, 10, 20, 9, tzinfo=datetime.timezone.utc)
    g = [{"chiave": "invio:manda", "cosa": "L'invio è fermo", "da": t0, "sta_facendo": "Riprova ogni 5 minuti."}]
    note, st = A.decidi(g, {}, t0)
    assert len(note) == 1 and "L'invio è fermo" in note[0][0] + note[0][1], note
    note, st = A.decidi(g, st, t0 + datetime.timedelta(minutes=30))
    assert note == [], "lo stesso guasto dopo 30 minuti: zitto"
    note, st = A.decidi(g, st, t0 + datetime.timedelta(hours=2, minutes=1))
    assert len(note) == 1, "dopo 2 ore: di nuovo"
    note, st = A.decidi(g, st, t0 + datetime.timedelta(hours=2, minutes=20))
    assert note == []
    note, st = A.decidi([], st, t0 + datetime.timedelta(hours=3))
    assert len(note) == 1 and note[0][0].startswith("Risolto") and "L'invio è fermo" in note[0][1] and st == {}, (note, st)
    assert all(len(n[0]) <= 40 for n in note), "il titolo sta sul telefono senza tagli"
    note, st = A.decidi([], st, t0 + datetime.timedelta(hours=3, minutes=10))
    assert note == [], "risolto una volta sola"
    # di notte (22-7:30) il telefono non suona: il guasto aspetta il mattino, se e' ancora vero
    notte = datetime.datetime(2026, 10, 20, 21, 30, tzinfo=datetime.timezone.utc)        # 23:30 a Roma
    note, st = A.decidi(g, {}, notte)
    assert note == [] and st["invio:manda"]["ultimo"] is None
    note, st = A.decidi(g, st, notte + datetime.timedelta(hours=8, minutes=10))         # 7:40
    assert len(note) == 1 and not note[0][0].startswith("Ancora"), note
    # nato e finito di notte: nessun «Risolto» per una cosa mai suonata
    note, st = A.decidi(g, {}, notte)
    note, st = A.decidi([], st, notte + datetime.timedelta(hours=1))
    note2, st = A.decidi([], st, notte + datetime.timedelta(hours=9))
    assert note == [] and note2 == [] and st == {}
    # un sistema solo: il segnale scrive i suoi guasti, non suona da solo; avvisi.py resta alle task
    import inspect, segnale_provvisorio as S, avvisi as T
    assert "from avvisa" not in inspect.getsource(S._avvisa) and "_registra_guasto(" in inspect.getsource(S.avvisa_ogni)
    assert "semaforo" not in inspect.getsource(T)
    # tre guasti nuovi insieme: una notifica sola, non tre
    tre = [dict(g[0], chiave=f"si:{i}", cosa=f"Sì fermo {i}") for i in range(3)]
    note, st = A.decidi(tre, {}, t0)
    assert len(note) == 1 and "3" in note[0][0], note


@prova("bozze: chi risponde di persona dopo l'analisi e' in conversazione, niente bozza (Dre 20/10: «faccio io»)")
def _():
    import bozze
    p = {"id": "x", "analysis_sent_at": "2026-10-10T09:00:00+00:00", "last_reply_at": "2026-10-12T08:00:00+00:00"}
    persona = {"at": "2026-10-12T08:00:00+00:00", "body": "Grazie, l'ho letta. Possiamo sentirci giovedi'?"}
    prima = {"at": "2026-10-09T08:00:00+00:00", "body": "Si', mandatemi l'analisi"}
    ooo = {"at": "2026-10-12T08:00:00+00:00", "body": "Sono fuori ufficio fino al 20 ottobre. Risposta automatica."}
    assert bozze.in_conversazione(p, [prima, persona]) is True, "una persona dopo l'analisi e' una conversazione"
    assert bozze.in_conversazione({**p, "last_reply_at": prima["at"]}, [prima]) is False, "il si' prima dell'analisi non e' una conversazione"
    assert bozze.in_conversazione(p, [prima, ooo]) is False, "un fuori ufficio dopo l'analisi non e' una persona"
    assert bozze.in_conversazione({"id": "x", "analysis_sent_at": None}, [persona]) is False, "senza analisi non c'e' conversazione"
    # la mail non e' ancora nel database ma la data dice che ha risposto dopo: nel dubbio, scrive Dre
    assert bozze.in_conversazione(p, []) is True
    # e il motore lo chiede prima di pagare la bozza, per chi aspetta e per chi e' in coda
    src = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "bozze.py")).read()
    assert src.count("in_conversazione(p, risposte_dopo") >= 2, "il controllo deve stare su chi aspetta e su chi e' in coda"


@prova("orecchio: una mail che annulla la call riporta il lead a «Da chiamare» e ferma il promemoria, nient'altro (20/10)")
def _():
    import orecchio as O
    utc = datetime.timezone.utc
    at = datetime.datetime(2026, 10, 19, 9, 3, tzinfo=utc)
    lead = "mario" + "@" + "esempio.invalid"
    ev = {"evento": "ev1", "inizio": datetime.datetime(2026, 10, 21, 9, 0, tzinfo=utc), "stato": "confirmed",
          "titolo": "StudioGalilei - Chiamata conoscitiva (Mario Rossi)", "invitati": [lead, "dramane" + "@" + "studiogalilei.com"],
          "descrizione": "", "pid": "p1"}
    vecchia = {**ev, "evento": "ev0", "inizio": datetime.datetime(2026, 10, 15, 9, 0, tzinfo=utc)}
    appunto = {**ev, "evento": "ev2", "titolo": "preparare la proposta", "invitati": []}
    # la call giusta: la prossima dopo la mail, del lead (per invitato o per lead), mai un appunto o una passata
    assert O.call_del_lead(lead, None, [vecchia, appunto, ev], at)["evento"] == "ev1"
    assert O.call_del_lead("altro" + "@" + "esempio.invalid", "p1", [ev], at)["evento"] == "ev1"
    assert O.call_del_lead("altro" + "@" + "esempio.invalid", "p9", [ev], at) is None
    # il caso del 19/10: «ho avuto un imprevisto e devo annullare l'appuntamento»
    testo = "Buongiorno ho avuto un imprevisto e devo annullare l'appuntamento. Le faccio sapere io"
    assert O.decidi("R: Promemoria: Chiamata conoscitiva", testo, {"cosa": "annulla", "sicuro": True, "perche": "x"})[0] == "annulla"
    assert O.decidi("Re: call", "Possiamo spostarla a venerdi'?", {"cosa": "sposta", "sicuro": True, "perche": "x"})[0] == "sposta"
    assert O.decidi("Rifiutato: Chiamata conoscitiva", "", None)[0] == "annulla", "il rifiuto dell'invito e' un annullamento"
    # due teste: senza le parole o senza il lettore sicuro, non si tocca niente
    assert O.decidi("Re: analisi", "Grazie, ci vediamo mercoledi'", {"cosa": "annulla", "sicuro": True, "perche": "x"})[0] is None
    assert O.decidi("Re: analisi", testo, {"cosa": "annulla", "sicuro": False, "perche": "x"})[0] is None
    assert O.decidi("Re: analisi", testo, None)[0] is None, "senza il lettore AI non si agisce"
    assert O.decidi("Accettato: Chiamata conoscitiva", "non riesco a trovare il link", None)[0] is None
    # quello che Dre ha gia' deciso vince (collaudo 20/10: il lead del 19/10 Dre l'aveva gia' segnato perso)
    dopo = (at + datetime.timedelta(hours=1)).isoformat()
    prima = (at - datetime.timedelta(days=2)).isoformat()
    assert O.gia_deciso({"stage": "risposto"}, None, [], at) is None
    assert O.gia_deciso({"stage": "risposto"}, {"stato": "Call fissata", "aggiornato_il": prima}, [{"at": prima}], at) is None
    assert O.gia_deciso({"stage": "perso"}, None, [], at)
    assert O.gia_deciso({"stage": "risposto"}, {"stato": "Perso", "aggiornato_il": prima}, [], at)
    assert O.gia_deciso({"stage": "risposto"}, {"stato": "Call fissata", "aggiornato_il": dopo}, [], at)
    assert O.gia_deciso({"stage": "risposto"}, None, [{"at": dopo}], at), "una nota di Dre dopo la mail: ci ha gia' pensato lui"
    # le tre scritture, e solo quelle. Col cellulare «Da chiamare»; senza (20/10 sera) «Da rispondere», gli scrive Dre
    s = O.scritture("p1", "ev1", "annulla", datetime.date(2026, 10, 19), cellulare="333 0000000")
    assert [t for t, _ in s] == ["snella_lead", "snella_note", "promemoria"]
    assert s[0][1]["stato"] == "Da chiamare" and s[0][1]["chiamata"] == "richiamare" and s[1][1]["testo"] == "Achille: ha annullato la call per mail"
    assert s[2][1]["ref"] == "promemoria:ev1", "il promemoria si ferma con il ref che promemoria.py controlla"
    s = O.scritture("p1", "ev1", "annulla", datetime.date(2026, 10, 19))
    assert s[0][1]["stato"] == "Da rispondere" and s[0][1]["responsabile"] == "Dramane" and "chiamata" not in s[0][1], s[0][1]
    assert "non ha lasciato un cellulare" in s[0][1]["prossima_mossa"] and "annullato" in s[0][1]["prossima_mossa"], s[0][1]
    assert "spostare" in O.scritture("p1", "ev1", "sposta", datetime.date(2026, 10, 19))[0][1]["prossima_mossa"]
    assert "phone,enriched" in open(O.__file__, encoding="utf-8").read(), "l'orecchio legge la scheda per sapere se c'e' un cellulare"
    import promemoria
    assert "ref=eq.{ref}" in open(promemoria.__file__).read(), "promemoria.py deve saltare la call se il ref esiste gia'"
    # non manda, non tocca il calendario, non scrive bozze
    src = open(O.__file__).read()
    for vietato in ("import manda", "proponi(", "messages/send", "drafts", '"PATCH", f"{CAL', "/events/", "smartlead"):
        assert vietato not in src, f"l'orecchio non deve contenere {vietato}"
    assert O.e_nostro("dramane" + "@" + "studiogalilei.com") and O.e_nostro("calendar-notification" + "@" + "google.com")


@prova("categorie Smartlead: un pezzo per giro sotto la soglia, i freschi prima, e una card sola del Revisore (20/10)")
def _():
    import categorie_smartlead as CS
    righe = [{"email": f"x{i}@esempio.invalid", "classificazione": "negativo", "risposta_il": f"2026-10-{1 + i % 28:02d}"} for i in range(870)]
    righe += [{"email": "s@esempio.invalid", "classificazione": "soppresso", "risposta_il": "2026-10-30"}]
    righe.sort(key=lambda r: r["risposta_il"], reverse=True)
    ora, dopo = CS.pezzo_del_giro(righe)
    import revisore
    assert 0 < len(ora) <= revisore.SOGLIA, "ogni giro deve stare sotto la soglia del Revisore, o si ferma per sempre"
    assert len(ora) + len(dopo) == 870 and all(r["classificazione"] != "soppresso" for r in ora + dopo), "i soppressi non rubano il posto"
    assert ora[0]["risposta_il"] >= dopo[0]["risposta_il"], "le risposte fresche prima"
    # un'autorisposta con il si' di classe non e' «Analisi» (campione del 20/10)
    pos = {"classificazione": "positivo", "stage": "risposto"}
    assert CS.categoria_nuova(pos, testo="Buongiorno, la mail è stata ricevuta. Verrà visionata nei giorni di ufficio.") == CS.N_OOO
    assert CS.categoria_nuova(pos, testo="Il nostro ufficio è chiuso fino a giovedì. Risponderemo alla vostra e-mail giovedì.") == CS.N_OOO
    assert CS.categoria_nuova(pos, testo="Sì, mandatemi pure l'analisi, grazie") == CS.N_SI
    # un perso (ha annullato e Dre l'ha chiuso) non e' «Conoscitiva» anche se la call resta in agenda
    assert CS.categoria_nuova({"classificazione": "rinvio", "stage": "perso"}, testo="devo annullare l'appuntamento", call=True) is None
    assert CS.categoria_nuova({"classificazione": "positivo", "stage": "call_fissata"}, call=True) == CS.N_CALL
    src = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "revisore.py")).read()
    assert "gia_aperta" in src and "stato=eq.aperta&azione->revisore->>azione" in src, "una domanda aperta per azione, non una per giro"


@prova("foglio: una call annullata per mail non e' piu' una «Chiamata conoscitiva» (20/10)")
def _():
    import foglio as F
    ann = F.call_annullate([{"prospect_id": "p1", "azione": {"call_at": "2026-10-21T15:00:00+02:00"}},
                            {"prospect_id": "p2", "azione": {}}, {"prospect_id": None, "azione": {"call_at": "2026-10-21T15:00:00+02:00"}}])
    assert ann == {("p1", "2026-10-21T13:00")}
    assert F.call_annullata({"prospect_id": "p1", "at": "2026-10-21T13:00:00+00:00"}, ann)
    assert not F.call_annullata({"prospect_id": "p1", "at": "2026-10-28T13:00:00+00:00"}, ann)   # la call rifissata resta
    assert not F.call_annullata({"prospect_id": "p2", "at": "2026-10-21T13:00:00+00:00"}, ann)
    import orecchio as O
    righe = dict((t, r) for t, r in O.scritture("p1", "ev1", "annulla", datetime.date(2026, 10, 20), "2026-10-21T15:00:00+02:00"))
    assert righe["promemoria"]["call_at"] == "2026-10-21T15:00:00+02:00"


# ── I TRE FOLLOW-UP SBAGLIATI DEL 20/10 (38 partiti da soli, 3 sbagliati) ──────────
_FU1_FINTO = "## FOLLOW UP 1\n```\nSalve,\n\ntorno brevemente sull'analisi che le avevo inviato qualche giorno fa.\n\nVolevo sapere se ha avuto occasione di leggerla.\n\nUn saluto\n```\n"


@prova("un sollecito a mano dopo l'analisi E' il follow-up: non ne nasce un secondo, e dopo un «tu» niente template col «lei» (20/10, caso 1)")
def _():
    import lettura as L
    import seguiti as S
    import prima_risposta as R
    p = {"id": "p1", "email": "info@alloggi-finti.invalid", "company": "Alloggi Brevi Finti", "analysis_sent": True,
         "analysis_sent_at": "2026-10-11T06:04:23.75+00:00"}
    righe = [{"kind": "email_out", "at": "2026-10-09T09:42:20", "body": "Salve, le avevo scritto qualche giorno fa riguardo a un'analisi marketing."},
             {"kind": "email_in", "at": "2026-10-09T16:28:52", "body": "ciao Lorenzo, manda pure il materiale, lo sottoporro' al nostro marketing interno. Cordialmente", "mittente": "tizio@posta-finta.invalid"},
             {"kind": "email_out", "at": "2026-10-11T06:04:50", "a": "info@alloggi-finti.invalid",
              "body": "Salve,\n\ngrazie, vi inoltro qui l'analisi che abbiamo fatto sulla vostra azienda.\n\nUn saluto\n\nLorenzo\nBusiness Development\n\n"
                      "Questo messaggio è riservato al destinatario indicato (Reg. UE 2016/679). Se l'hai ricevuto per errore, ti chiediamo di avvisarci e di cancellarlo."}]
    sollecito = {"kind": "email_out", "at": "2026-10-16T09:58:43", "a": "info@alloggi-finti.invalid",
                 "body": "Ciao, ti riscrivo sull'analisi di Alloggi Brevi Finti che ti avevo mandato l'11 ottobre. Mi avevi detto che l'avresti girata al marketing. Fammi sapere.\n\nIl giorno ven 9 ott 2026 alle ore 16:28 Tizio <tizio@posta-finta.invalid> ha scritto:\n> le avevo scritto"}
    vero = L.secondo_lettore
    L.secondo_lettore = lambda t: None
    try:
        prima = L.ha_gia(p, righe)
        dopo = L.ha_gia(p, righe + [sollecito])
    finally:
        L.secondo_lettore = vero
    # con la sola analisi dopo la sua mail il follow-up e' dovuto
    assert not prima["nostre_dopo_analisi"] and not prima["ultima_nostra_del_tu"], prima
    assert L.regola_dura("FOLLOW UP 1", prima) is None
    # il sollecito a mano (da qualunque casella nostra) conta come follow-up gia' fatto
    assert dopo["nostre_dopo_analisi"] == ["2026-10-16"], dopo["nostre_dopo_analisi"]
    esito = L.regola_dura("FOLLOW UP 1", dopo)
    assert esito and esito[0] == "salta" and "16/10" in esito[1], esito
    # e l'ultima nostra da' del tu: il template col lei non si scrive da solo (la cita non conta)
    assert dopo["ultima_nostra_del_tu"] is True
    assert L.da_del_tu("Salve, le avevo scritto riguardo a un'analisi. Ti.Emme.Ti srl") is False, "una sigla non e' un tu"
    assert L.da_del_tu("Salve, grazie, vi inoltro qui l'analisi che abbiamo fatto sulla vostra azienda") is False
    assert S.testo("FOLLOW UP 1", p, prima, "https://calendar.app.google/x", testo_file=_FU1_FINTO), "col lei il codice scrive"
    assert S.testo("FOLLOW UP 1", p, dopo, "https://calendar.app.google/x", testo_file=_FU1_FINTO) is None, "dopo un tu il template col lei non parte"
    assert S.testo("FOLLOW UP 1", p, {"ultima_nostra": "Ciao, ti riscrivo: hai visto l'analisi?"}, "c", testo_file=_FU1_FINTO) is None, "anche su una lettura vecchia senza il campo"
    # il cancello dei seguiti, rileggendo il filo adesso, ferma e chiude anche se la bozza era gia' nata
    pr = {"id": 1, "at": "2026-10-16T10:14:16+00:00", "azione": {"lettura": {**prima, "gruppo": "FOLLOW UP 1", "coerenza": "COERENTE"}}}
    motivo, chiudi = R.seguito_cambiato(pr, dopo, pr["azione"]["lettura"])
    assert motivo and "sollecito" in motivo and chiudi, (motivo, chiudi)
    assert R.seguito_cambiato(pr, prima, pr["azione"]["lettura"]) == (None, False)


@prova("due schede della stessa azienda ricevono UN follow-up; un «Doppione» o un «fermato da Dre» non si rigenera mai (20/10, caso 2)")
def _():
    import followup as F
    import prima_risposta as R
    import datetime as _dt
    assert F.chiusa_per_sempre("NO: non mi piace")
    assert F.chiusa_per_sempre("chiusa da Achille (15/10, scaglione 1, nessuna mail): Doppione: la stessa agenzia riceve il follow-up nel filo di un collega")
    assert F.chiusa_per_sempre("fermato da Dre in Posta")
    assert F.chiusa_per_sempre("chiusa da Achille (15/10): Follow-up già fatto a mano")
    assert not F.chiusa_per_sempre("chiusa il 25/9: scritta senza lettura del filo; la rifà il motore nuovo")
    assert not F.chiusa_per_sempre("")
    # la famiglia: stesso dominio (non generico) o stessa azienda, e il follow-up gia' avuto da una sorella
    ieri = (_dt.datetime.now(_dt.timezone.utc) - _dt.timedelta(days=5)).isoformat()
    vecchia = (_dt.date.today() - _dt.timedelta(days=20)).isoformat()
    servita = {"id": "a", "email": "mario@posta-finta.invalid", "company": "Agenzia Immobiliare Finta", "analysis_sent_at": vecchia, "last_reply_at": None, "coda": None}
    gemella = {"id": "b", "email": "info@agenziafinta.invalid", "company": "Agenzia Immobiliare Finta", "analysis_sent_at": vecchia, "last_reply_at": None, "coda": None}
    dominio = {"id": "c", "email": "ufficio@posta-finta.invalid", "company": "Altra Cosa", "analysis_sent_at": vecchia, "last_reply_at": None, "coda": None}
    estranea = {"id": "d", "email": "x@terza.invalid", "company": "Terza Srl", "analysis_sent_at": vecchia, "last_reply_at": None, "coda": None}
    proposte = [{"prospect_id": "a", "stato": "fatta", "risposta": "Mandata da Clara", "at": ieri},
                {"prospect_id": "b", "stato": "no", "risposta": "chiusa da Achille: Doppione: la stessa agenzia ha il follow-up nel filo di Mario", "at": ieri}]
    schede = [servita, gemella, dominio, estranea]

    def sb_finto(m, path, corpo=None, h=None):
        if "/rest/v1/prospects?select=id,name,company,email,analysis_sent_at" in path:
            return [gemella, dominio, estranea]
        if path.startswith("/rest/v1/prospects?select=id,email,company&id=in."):
            ids = path.split("id=in.(")[1].split(")")[0].split(",")
            return [s for s in schede if s["id"] in ids]
        if "/rest/v1/interactions" in path:
            return []
        return []

    def sb_tutte_finto(path, **k):
        if "/rest/v1/proposte?select=prospect_id,stato,risposta" in path:
            return proposte
        return []
    messi = []
    vero = (F.sb, F.sb_tutte, F.in_coda, F.calendario, F.mini_followup, F.rinvii_scaduti, F._fu)
    try:
        F._fu = lambda: ""
        F.sb, F.sb_tutte = sb_finto, sb_tutte_finto
        F.in_coda = lambda pid, gruppo: messi.append(pid)
        F.calendario = lambda prova, oggi: None
        F.mini_followup = lambda prova, oggi: 0
        F.rinvii_scaduti = lambda prova, oggi: 0
        F._FAMIGLIA = None
        # «b» e' chiusa come Doppione: non si rigenera. «c» e' lo stesso dominio di «a»: niente. «d» parte.
        assert "b" in F.gia_avute("FOLLOW%20UP%201"), "un Doppione conta come gia' avuto"
        sorella = F.famiglia_servita()
        assert sorella(gemella) and "Agenzia Immobiliare Finta" in sorella(gemella), sorella(gemella)
        assert sorella(dominio), "stesso dominio vero: stessa famiglia"
        assert sorella(estranea) is None
        assert sorella({"email": ""}) is None and sorella({"email": "chi@" + "gmail.com", "company": ""}) is None, "un dominio generico non fa famiglia"
        F.main()
        assert messi == ["d"], messi
        # il cancello dei seguiti vede la stessa cosa, prima di approvare
        pr = {"tipo": "risposta", "titolo": "FU", "at": ieri, "azione": {"testo_dal_codice": True, "lettura": {"gruppo": "FOLLOW UP 1", "coerenza": "COERENTE"}}}
        vero_c = R.contattabile
        R.contattabile = lambda p: True
        try:
            assert any("stessa azienda" in m for m in R.perche_no_seguito(pr, {**dominio, "last_reply_at": None})), R.perche_no_seguito(pr, dominio)
            assert not any("stessa azienda" in m for m in R.perche_no_seguito(pr, {**estranea, "last_reply_at": None}))
            assert not any("stessa azienda" in m for m in R.perche_no_seguito(pr, {"email": ""})), "senza scheda non si rompe"
        finally:
            R.contattabile = vero_c
    finally:
        F.sb, F.sb_tutte, F.in_coda, F.calendario, F.mini_followup, F.rinvii_scaduti, F._fu = vero
        F._FAMIGLIA = None


@prova("una mail del lead dopo la nascita della bozza (o dopo l'analisi) ferma il follow-up e lo chiude, al cancello e al postino (20/10, caso 3)")
def _():
    import prima_risposta as R
    import manda as M
    nata = "2026-10-18T06:41:49.68+00:00"
    pr = {"id": 7, "tipo": "risposta", "titolo": "Follow up 1: X", "at": nata, "prospect_id": "p3",
          "azione": {"testo_dal_codice": True, "template": "FOLLOW UP 1", "approvata_da": "seguito-automatico", "automatica": True, "bozza": "Salve,\n\ntorno sull'analisi.",
                     "lettura": {"gruppo": "FOLLOW UP 1", "coerenza": "COERENTE", "ultima_loro_il": "2026-10-13", "ultima_loro": "La mail e' corretta.", "scritto_dopo_di_lei": 1}}}
    p = {"id": "p3", "email": "info@stile-finto.invalid", "company": "Stile Finto", "analysis_sent": True, "analysis_sent_at": "2026-10-13T08:01:30+00:00",
         "last_reply_at": "2026-10-13T07:52:24+00:00", "fuori": False, "stage": "in_follow_up", "pipeline_stage": None, "no_followup": False, "classificazione": "positivo"}
    vero_c, vero_f = R.contattabile, R.sorella_servita
    R.contattabile = lambda p: True
    R.sorella_servita = lambda p: None
    try:
        assert not [m for m in R.perche_no_seguito(pr, p) if "dopo" in m], R.perche_no_seguito(pr, p)
        # il 19/10 il lead scrive «confermo indirizzo»: la scheda lo sa (last_reply_at) prima ancora di rileggere il filo
        p2 = {**p, "last_reply_at": "2026-10-19T09:08:03+00:00"}
        no = R.perche_no_seguito(pr, p2)
        assert any("ha scritto" in m and "19/10" in m for m in no), no
        # e rileggendo il filo adesso: la sua mail nuova ferma e CHIUDE, anche se noi non abbiamo scritto niente
        vecchia = pr["azione"]["lettura"]
        letti = {**vecchia, "ultima_loro_il": "2026-10-19", "ultima_loro_at": "2026-10-19T09:08:03", "ultima_loro": "Buongiorno, confermo indirizzo.",
                 "scritto_dopo_di_lei": 0, "loro_dopo_analisi": "2026-10-19", "nostre_dopo_analisi": []}
        motivo, chiudi = R.seguito_cambiato(pr, letti, vecchia)
        assert motivo and "ha riscritto" in motivo and chiudi, (motivo, chiudi)
        # la lettura di prima (nessuna mail nuova) non ferma niente
        assert R.seguito_cambiato(pr, {**vecchia, "ultima_loro_at": "2026-10-13T07:52:24", "loro_dopo_analisi": "", "nostre_dopo_analisi": []}, vecchia) == (None, False)
    finally:
        R.contattabile, R.sorella_servita = vero_c, vero_f
    # il postino: l'ultima risposta del lead su Smartlead e' dopo la nascita della bozza → non parte, chiusa col motivo
    assert M.superata(pr, p, "2026-10-19T09:08:03.000Z"), "una mail del lead dopo la bozza deve fermare"
    assert M.superata(pr, p, "2026-10-13T07:52:24") is None, "la mail a cui la bozza risponde non la supera"
    assert M.superata({**pr, "azione": {**pr["azione"], "template": "INT-01"}}, p, "2026-10-19T09:08:03") , "vale per ogni bozza nata prima della sua mail"
    # dentro il giro vero del postino: niente POST a Smartlead, proposta chiusa con il motivo scritto
    chiamate, spedite = [], []
    vero = (M.sb, M.thread, M.controlla, M.contattabile, M.con_soldi, M.soldi_clienti, M.sl, M.di_clara, M.pulizia)
    try:
        def sb_finto(m, path, corpo=None, h=None):
            chiamate.append((m, path, corpo))
            if m == "GET" and "stato=eq.approvata" in path:
                return [pr]
            if m == "GET" and path.startswith("/rest/v1/prospects?select=id,email"):
                return [p]
            if m == "GET" and path.startswith("/rest/v1/prospects?select=fuori"):
                return [p]
            if m == "PATCH" and "stato=eq.approvata" in path:
                return [{"id": 7}]                       # il lucchetto riesce: senza il freno nuovo si spedirebbe
            return []
        M.sb = sb_finto
        M.thread = lambda p: (1, 2, {"type": "REPLY", "time": "2026-10-19T09:08:03.000Z", "message_id": "m", "stats_id": "s", "email_body": "confermo"})
        M.controlla = lambda *a, **k: []
        M.contattabile = lambda p: True
        M.con_soldi, M.soldi_clienti = (lambda p, s: p), (lambda ids=None: {})
        M.sl = lambda m, path, corpo=None: spedite.append(path)
        M.di_clara = lambda *a, **k: None
        M.pulizia = lambda: 0
        assert "--prova" not in sys.argv
        M.main()
    finally:
        M.sb, M.thread, M.controlla, M.contattabile, M.con_soldi, M.soldi_clienti, M.sl, M.di_clara, M.pulizia = vero
    assert not spedite, "il postino ha spedito a chi aveva appena risposto"
    chiuse = [c for m, path, c in chiamate if m == "PATCH" and "proposte?id=eq.7" in path and (c or {}).get("stato") == "no"]
    assert chiuse and "ha riscritto" in chiuse[0]["risposta"] and "19/10" in chiuse[0]["risposta"], chiuse
@prova("calendario: un evento annullato nel calendario diventa «annullata» in agenda (20/10)")
def _():
    import calendario as C
    assert C.da_annullare({"stato": "CANCELLED"}, {"id": 1, "tipo": "conoscitiva"})
    assert not C.da_annullare({"stato": "CANCELLED"}, {"id": 1, "tipo": "annullata"})   # gia' fatto
    assert not C.da_annullare({"stato": "CANCELLED"}, None)                             # mai stata in agenda
    assert not C.da_annullare({"stato": "CONFIRMED"}, {"id": 1, "tipo": "conoscitiva"})
    assert "annullata" not in C.CALL if hasattr(C, "CALL") else True
    # il feed iCal non porta gli annullati: una riga sparita nel periodo si annulla, ma non con un feed sospetto
    da, a = datetime.datetime(2026, 10, 1, tzinfo=datetime.timezone.utc), datetime.datetime(2026, 11, 30, tzinfo=datetime.timezone.utc)
    es = {f"l{i}": {"id": i, "link": f"l{i}", "at": "2026-10-19T13:00:00+00:00", "tipo": "conoscitiva", "titolo": "x"} for i in range(40)}
    visti = {f"l{i}" for i in range(1, 40)}
    fuori, motivo = C.sparite(es, visti, da, a, 183)
    assert [r["id"] for r in fuori] == [0] and motivo is None
    assert C.sparite(es, visti, da, a, 10) == ([], C.sparite(es, visti, da, a, 10)[1]) and "sospetto" in C.sparite(es, visti, da, a, 10)[1]
    assert C.sparite(es, set(), da, a, 183)[0] == []                      # tutte sparite: feed rotto, niente
    es["l0"]["at"] = "2026-01-05T10:00:00+00:00"
    assert C.sparite(es, visti, da, a, 183)[0] == []                      # fuori dal periodo letto: non si giudica


@prova("foglio: un lead «Da chiamare» con l'analisi gia' mandata sta in Conversazione (20/10)")
def _():
    import foglio as F
    ora = datetime.datetime(2026, 10, 20, 12, tzinfo=datetime.timezone.utc)
    p = {"id": "p1", "classificazione": "positivo", "last_reply_at": "2026-10-01T10:00:00+00:00",
         "analysis_sent_at": "2026-10-02T10:00:00+00:00", "pipeline_stage": None, "stage": None}
    d = {"stato": "Da chiamare", "aggiornato_il": "2026-10-20T11:00:00+00:00"}
    fase, _ = F.fase_di(p, None, d, [], None, None, ora=ora)
    assert fase == F.CONV, fase
    fase2, _ = F.fase_di(p, None, None, [], None, None, ora=ora)
    assert fase2 == F.INVIATA, fase2


# ── 20/10: il rimbalzo interno, con la nuova persona in copia davvero ────────
_LETTI_RIMBALZO = {"ultima_loro": "PROVI A MANDARLO A QUESTO INDIRIZZO CHE LE GIRO, ABBIAMO UNA COMMERCIALE CON UN SOCIO: "
                                  "INFO@NUOVA-AZIENDA.INVALID, ALL'ATTENZIONE DI MATTIA. BUONA GIORNATA",
                   "ultima_loro_il": "2026-10-20", "ultima_nostra": "Salve, le avevo scritto", "ultima_nostra_il": "2026-10-15",
                   "scritto_dopo_di_lei": 0, "girato_a": ["info@nuova-azienda.invalid"], "detto_no": False, "autorisposta": False,
                   "analisi_ricevuta": False, "analisi_gia_letta": False, "destinatario": None, "coerenza": "COERENTE"}
_P_RIMBALZO = {"id": "x", "email": "lead@vecchia-azienda.invalid", "company": "Falegnameria F.lli Prova", "name": "", "email_alt": None,
               "classificazione": "da_classificare", "stage": "risposto", "fuori": False, "pipeline_stage": None, "no_followup": False,
               "analysis_sent": False, "analysis_pdf": "https://x/analisi.pdf"}


@prova("rimbalzo interno (20/10): il template di Dre composto dal codice, con la copia vera e l'analisi allegata")
def _():
    import bozze, seguiti, prima_risposta as R
    letti, p = _LETTI_RIMBALZO, _P_RIMBALZO
    cc = bozze.in_copia(letti, p)
    assert cc == ["info@nuova-azienda.invalid"], cc
    # chi ci ha dato un destinatario nuovo non ha nessuno in copia: la mail parte a lui
    assert bozze.in_copia(letti, {**p, "email_alt": ["nuovo@nuova-azienda.invalid"]}) == []
    # il nome solo se sta nel testo suo: «Mattia» si', «Giovanni» (inventato dal modello) no
    assert bozze.nome_nuovo(letti, "Metto in copia Mattia a info@nuova-azienda.invalid") == "Mattia"
    assert bozze.nome_nuovo({**letti, "ultima_loro": "mandi pure a info@nuova-azienda.invalid"}, "Metto in copia Giovanni") == ""
    t = seguiti.risposta("INT-08", p, letti, bozze.CALENDARIO, cc=cc, nome_nuovo="Mattia")
    assert t and "Metto in copia Mattia (info@nuova-azienda.invalid)" in t and "(la trova allegata)" in t and "Mattia, piacere:" in t, t
    assert "F.lli Prova appare oggi su Google" in t and bozze.CALENDARIO in t
    assert bozze.cancello(t) == [], bozze.cancello(t)                       # a capo, non punto-spazio-e-continua
    assert R.ALLEGA_ANALISI.search(t.lower()), "«F.lli» dentro la frase non deve nascondere l'allegato"
    senza_nome = seguiti.risposta("INT-08", p, letti, bozze.CALENDARIO, cc=cc, nome_nuovo="")
    assert "Metto in copia info@nuova-azienda.invalid" in senza_nome and "\nPiacere: sono Lorenzo" in senza_nome, senza_nome
    assert seguiti.risposta("INT-08", p, letti, bozze.CALENDARIO, cc=[]) is None, "senza nessuno in copia il codice non scrive"
    # il motore mette cc e allegati nella proposta
    b = bozze.testo_di_dre({"intento": "INT-08", "bozza": "Metto in copia Mattia a info@nuova-azienda.invalid", "nota": ""}, p, letti)
    assert b.get("dal_codice") and b.get("cc") == cc and "in copia info@nuova-azienda.invalid" in b["nota"], b
    src = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "bozze.py"), encoding="utf-8").read()
    assert 'azione.update({"cc": b["cc"], "allega": True, "allega_presentazione": True})' in src


@prova("seconda testa (20/10): «metto in copia» e' un fatto, e lo verifica il codice prima del modello")
def _():
    import lettura as L
    letti, cc = _LETTI_RIMBALZO, ["info@nuova-azienda.invalid"]
    bozza = "Salve,\n\ngrazie, metto in copia Mattia (info@nuova-azienda.invalid) così proseguiamo lì.\nLa trova allegata."
    assert L.copia_coerente(letti, bozza, cc) is None
    # la frase senza la copia: il caso vero del 20/10
    v, m = L.copia_coerente(letti, bozza, [])
    assert v == "INCOERENTE" and "FATTO INVENTATO" in m, (v, m)
    # in copia un indirizzo che la persona non ha scritto
    v, m = L.copia_coerente(letti, "Metto in copia Mattia (altro@altra.invalid)", ["altro@altra.invalid"])
    assert v == "INCOERENTE" and "non ha scritto" in m, (v, m)
    # la bozza nomina un indirizzo diverso da quello in copia
    v, m = L.copia_coerente(letti, "Metto in copia Mattia (altro@altra.invalid)", cc)
    assert v == "INCOERENTE" and "altro@altra.invalid" in m, (v, m)
    # qualcuno in copia senza dirlo
    v, m = L.copia_coerente(letti, "Salve, le allego l'analisi.", cc)
    assert v == "INCOERENTE" and "senza dirlo" in m, (v, m)
    # coerenza() si ferma qui, senza chiamare il modello
    assert L.coerenza(letti, bozza, None, cc=[])[0] == "INCOERENTE"
    assert "in copia a=" in open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "lettura.py"), encoding="utf-8").read()


@prova("prima risposta (20/10): INT-08 parte da solo solo con la copia vera, il template del codice e gli allegati")
def _():
    import prima_risposta as R
    letti, p = _LETTI_RIMBALZO, _P_RIMBALZO
    bozza = ("Salve,\n\ngrazie per il passaggio, molto gentile. Metto in copia Mattia (info@nuova-azienda.invalid) così proseguiamo direttamente lì.\n\n"
             "Mattia, piacere: sono Lorenzo di Studio Galilei.\nIn una riga: abbiamo preparato un'analisi esterna gratuita su come Falegnameria F.lli Prova "
             "appare oggi su Google (la trova allegata), ed è il nostro modo di presentarci.\n📅 Calendario: https://calendar.app.google/x")
    az = {"bozza": bozza, "intento": "INT-08", "cc": ["info@nuova-azienda.invalid"], "lettura": letti, "testo_dal_codice": True}
    pr = {"id": 1, "tipo": "risposta", "titolo": "Bozza per Prova, INT-08", "azione": az}
    assert R.perche_no(pr, p) == [], R.perche_no(pr, p)
    def con(**mod):
        return R.perche_no({**pr, "azione": {**az, **mod}}, p)
    assert any("nessuno in copia" in m for m in con(cc=[])), "senza copia non e' un rimbalzo servito"
    assert any("di mezzo un altro indirizzo" in m for m in con(cc=[])), "l'indirizzo non servito resta «di mezzo»"
    assert any("la copia non torna" in m for m in con(cc=["altro@altra.invalid"])), "una copia inventata deve fermare"
    assert any("composto dal codice" in m for m in con(testo_dal_codice=False)), "il testo del modello resta a Dre"
    assert any("fuori dalla prima risposta" in m for m in con(intento="INT-09")), "INT-09 non e' nella corsia (solo INT-08, decisione del 20/10)"
    # un INT-01 con un indirizzo di un altro dominio nel testo resta fermo come prima (2/10)
    assert any("di mezzo" in m for m in con(intento="INT-01", cc=[]))
    # il Revisore sa chi e' in copia
    assert "IN COPIA (cc, messa dal codice" in open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "prima_risposta.py"), encoding="utf-8").read()


@prova("postino (20/10): la copia parte davvero (cc di Smartlead) e passa dal cancello: mai inventata, mai un cliente, mai una casella di servizio")
def _():
    import manda
    letti, p = _LETTI_RIMBALZO, _P_RIMBALZO
    assert manda.in_copia({"cc": ["a@nuova-azienda.invalid", " b@nuova-azienda.invalid "]}) == {"cc": "a@nuova-azienda.invalid, b@nuova-azienda.invalid"}
    assert manda.in_copia({"cc": []}) == {} and manda.in_copia({}) == {}
    src = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "manda.py"), encoding="utf-8").read()
    assert '"to_email": a, **copia}' in src and "cc=az.get(\"cc\"), let=az.get(\"lettura\")" in src, "il cc deve entrare nel corpo di reply-email-thread"
    assert any("non ha scritto" in e for e in manda.controlla_cc(["x@altra.invalid"], p, letti))
    assert any("non e' un indirizzo" in e for e in manda.controlla_cc(["non-un-indirizzo"], p, letti))
    for brutto in ("noreply@nuova-azienda.invalid", "a@pec.nuova-azienda.invalid", "b@arubapec.invalid", "lorenzo@studiogalilei.com"):
        err = manda.controlla_cc([brutto], p, {**letti, "ultima_loro": letti["ultima_loro"] + " " + brutto})
        assert any("non una persona" in e for e in err), (brutto, err)
    assert any("gia' il destinatario" in e for e in manda.controlla_cc([p["email"]], p, {**letti, "girato_a": [p["email"]]}))
    vero_sb = manda.sb
    chiamate = []
    try:
        # sul dominio c'e' un cliente: la regola del 25/9 vale anche per chi sta in copia
        manda.sb = lambda m, u, *a, **k: chiamate.append(u) or [{"fuori": False, "stage": "cliente", "pipeline_stage": None, "no_followup": False, "classificazione": "positivo"}]
        err = manda.controlla_cc(["info@nuova-azienda.invalid"], p, letti)
        assert any("non si contatta" in e for e in err), err
        assert chiamate and "ilike" in chiamate[0] and "nuova-azienda.invalid" in chiamate[0], chiamate
        # nessuna scheda sul dominio, o schede contattabili: passa
        manda.sb = lambda m, u, *a, **k: []
        assert manda.controlla_cc(["info@nuova-azienda.invalid"], p, letti) == []
        manda.sb = lambda m, u, *a, **k: [{"fuori": False, "stage": "risposto", "pipeline_stage": None, "no_followup": False, "classificazione": "positivo"}]
        assert manda.controlla_cc(["info@nuova-azienda.invalid"], p, letti) == []
        # il database non risponde: non si manda alla cieca
        def rotto(*a, **k):
            raise RuntimeError("giu'")
        manda.sb = rotto
        assert any("non riesco a controllare" in e for e in manda.controlla_cc(["info@nuova-azienda.invalid"], p, letti))
        # il cancello intero: il cc passa prima del resto
        assert manda.controlla("Salve,\n\nmetto in copia x.", p, cc=["x@altra.invalid"], let=letti) == ["in copia x@altra.invalid, che la persona non ha scritto: mai un indirizzo inventato"]
    finally:
        manda.sb = vero_sb
    # chi approva in chat passa la copia al cancello e alla seconda testa
    src_a = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "approva.py"), encoding="utf-8").read()
    assert 'cc=az.get("cc"), let=az.get("lettura")' in src_a and 'seconda_testa(p, testo, az.get("gruppo") or az.get("template"), cc=az.get("cc"))' in src_a


def _lettura_finta(**campi):
    """Una lettura del modello finto: tutti i campi dello schema, con i valori di una risposta qualsiasi."""
    base = {"autore": "persona", "testo_suo": "", "caso": "C01", "caso_nuovo_nome": None, "caso_nuovo_descrizione": None,
            "sicurezza": "alta", "perche": "finto", "porta_aperta": False, "porta_aperta_frase": None, "motivo": "nessuno",
            "caldo": False, "caldo_motivi": [], "caldo_frase": None, "consiglio": None, "numeri": [], "orario_chiesto": None,
            "orario_iso": None, "data_rientro": None, "data_ricontatto": None, "indirizzi_nuovi": [], "elementi": [],
            "saluto_nome": None, "tu": False, "non_scrivere": False}
    base.update(campi)
    return base


def _modello_finto(lettura, apertura=False):
    chiamate = []

    def chiedi(ruolo, istruzioni, testo, schema):
        chiamate.append(ruolo)
        assert "LA CARTA DEI CASI" in istruzioni or ruolo in ("seconda_lettura", "caldo")
        return (lettura if ruolo == "lettore" else {"apertura": apertura, "frase": "x" if apertura else None}), 0.001
    return chiedi, chiamate


def _filo_finto(risposta):
    return [{"type": "SENT", "time": "2026-10-19T08:00:00Z", "email_seq_number": 1, "subject": "Analisi gratuita",
             "email_body": "<p>Buongiorno, abbiamo preparato un'analisi gratuita delle vostre campagne su Google. Gliela mando?</p>"},
            {"type": "REPLY", "time": "2026-10-19T09:00:00Z", "email_body": risposta}]


@prova("lettore: «noi siamo interessati grazie» e' un si' (i 4 si' persi dalle liste il 19/10)")
def _():
    import lettore as L
    chiedi, chiamate = _modello_finto(_lettura_finta(caso="C01", sicurezza="alta", testo_suo="noi siamo interessati grazie"))
    r = L.leggi_risposta("noi siamo interessati grazie", _filo_finto("noi siamo interessati grazie"), {}, chiedi=chiedi)
    assert r["classe"] == "positivo" and r["fonte"] == "lettore" and not r["non_scrivere"], r
    assert chiamate == ["lettore", "caldo"], "un si' non passa dalla seconda lettura, ma si rilegge cercando il caldo"
    # il caldo riletto: «se la condividiamo ne parliamo» e' caldo anche se il primo lettore non l'ha visto
    def caldo_riletto(ruolo, istruzioni, testo, schema):
        return (_lettura_finta(caso="C02") if ruolo == "lettore" else {"caldo": True, "frase": "ne parliamo"}), 0.0
    r = L.leggi_risposta("Si' la mail e' corretta, se la condividiamo ne parliamo", None, {}, chiedi=caldo_riletto)
    assert r["classe"] == "positivo" and r["caldo"] is True, r
    # chi e' irritato (C31) non riceve mail automatiche: decide Dre
    chiedi, _c = _modello_finto(_lettura_finta(caso="C31"))
    r = L.leggi_risposta("Basta spam, vi segnalo alla polizia postale", None, {}, chiedi=chiedi)
    assert r["classe"] == "da_classificare" and r["non_scrivere"] is True, r
    # un si' detto con poca sicurezza non fa scrivere Clara da sola: va a Dre, mai in un no
    chiedi, _c = _modello_finto(_lettura_finta(caso="C01", sicurezza="media"))
    assert L.leggi_risposta("può inviarmi il report", None, {}, chiedi=chiedi)["classe"] == "da_classificare"
    # dopo l'analisi chi rimanda e' in conversazione con Dre: niente ripresa automatica (la carta, «dopo»)
    assert L.classe_del_caso("C17", analisi=False) == "rinvio" and L.classe_del_caso("C17", analisi=True) == "da_classificare"
    assert L.classe_del_caso("C25", porta_aperta=True) == "rinvio" and L.classe_del_caso("C25") == "negativo"
    assert L.classe_del_caso("C44", analisi=False) == "da_classificare", "un collega a cui scrivere non e' un fuori ufficio da chiudere"


@prova("lettore: «Cancellami» e' un no e non si scrive piu', anche se il modello sbaglia")
def _():
    import lettore as L
    chiedi, chiamate = _modello_finto(_lettura_finta(caso="C30", non_scrivere=True))
    r = L.leggi_risposta("Cancellami", _filo_finto("Cancellami"), {}, chiedi=chiedi)
    assert r["classe"] == "negativo" and r["non_scrivere"] is True, r
    assert L.classe_db(r) == "soppresso"
    assert chiamate == ["lettore", "seconda_lettura"], "una chiusura passa dalla seconda lettura"
    # il modello legge un si': la rete dei casi gravi lo porta a Dre e nessuna mail parte
    chiedi, _c = _modello_finto(_lettura_finta(caso="C01", sicurezza="alta"))
    r = L.leggi_risposta("Cancellami", None, {}, chiedi=chiedi)
    assert r["classe"] == "da_classificare" and r["non_scrivere"] is True, r
    for frase in ("Cancellami", "toglietemi dalla lista", "non scriveteci più", "Non mi può più scrivere"):
        assert L.rete_su([frase]), frase
    assert not L.rete_su(["noi siamo interessati grazie"])


@prova("lettore: un'autorisposta e' automatica, mai un si' (caso Tenda Ok, 19/10)")
def _():
    import lettore as L
    auto = "Grazie per averci contattato, la sua richiesta e' stata presa in carico. Risponderemo al piu' presto."
    chiedi, _c = _modello_finto(_lettura_finta(autore="automatico", caso="C47"))
    r = L.leggi_risposta(auto, _filo_finto(auto), {}, chiedi=chiedi)
    assert r["classe"] == "automatico" and not r["caldo"], r
    assert L.classe_db(r) == "ooo", "nel database un automatico e' un fuori ufficio: la sequenza riprende"
    # il modello la legge come si' ma dice che l'ha scritta una macchina: a Dre, mai positivo
    chiedi, _c = _modello_finto(_lettura_finta(autore="automatico", caso="C01", caldo=True, caldo_motivi=["lascia_numero"]))
    r = L.leggi_risposta(auto, None, {}, chiedi=chiedi)
    assert r["classe"] == "da_classificare" and not r["caldo"], r
    # la seconda lettura trova un'apertura in una chiusura: a Dre
    chiedi, _c = _modello_finto(_lettura_finta(caso="C24"), apertura=True)
    assert L.leggi_risposta("No grazie, pero' mandatela", None, {}, chiedi=chiedi)["classe"] == "da_classificare"


@prova("lettore: se il modello non risponde o il tetto e' pieno, ricade sulle liste e lo dice")
def _():
    import lettore as L

    def rotto(*a):
        raise L.Guasto("Anthropic 529: overloaded")
    r = L.leggi_risposta("Non siamo interessati, grazie", None, {}, chiedi=rotto)
    assert r["fonte"] == "liste" and r["classe"] == "negativo" and "non ha risposto" in r["motivo"], r
    vecchia = os.environ.pop("ANTHROPIC_API_KEY", None)
    L_env = L._env
    L._env = lambda n: None
    try:
        r = L.leggi_risposta("si' mandatela pure", None, {})
        assert r["fonte"] == "liste" and "manca la chiave" in r["motivo"], r
        L._env = lambda n: "finta" if n == "ANTHROPIC_API_KEY" else None
        spesa = L.spesa_di_oggi
        L.spesa_di_oggi = lambda scopo="lettore": 5.0
        try:
            r = L.leggi_risposta("si' mandatela pure", None, {})
            assert r["fonte"] == "liste" and "tetto" in r["motivo"], r
        finally:
            L.spesa_di_oggi = spesa
    finally:
        L._env = L_env
        if vecchia:
            os.environ["ANTHROPIC_API_KEY"] = vecchia
    # i soldi: il prezzo di Sonnet e la cache letta a un decimo
    assert abs(L.costo("claude-sonnet-5", 1_000_000, 0, 0, 0) - 2.0) < 1e-9
    assert abs(L.costo("claude-sonnet-5", 0, 1_000_000, 0, 0) - 0.2) < 1e-9


@prova("lettore: la pulizia toglie la nostra mail citata e il nostro oggetto (pulizia.ts di Clara nuova)")
def _():
    import lettore as L
    nostra = "Buongiorno, abbiamo preparato un'analisi gratuita delle vostre campagne su Google e vorremmo mandargliela"
    t = "Va bene, me la mandi.\nIl giorno lun 19 ott 2026 alle 10:00 Lorenzo ha scritto:\n> " + nostra
    assert L.solo_suo(t, [nostra])["con_firma"] == "Va bene, me la mandi."
    t = "Va bene, me la mandi. " + nostra + " se le interessa"
    assert L.solo_suo(t, [nostra])["con_firma"].startswith("Va bene, me la mandi.") and "preparato" not in L.solo_suo(t, [nostra])["con_firma"]
    assert L.solo_suo("Analisi gratuita\nOk procedete", [], ["Re: Analisi gratuita"])["con_firma"] == "Ok procedete"
    # un'ora scritta dalla persona non e' l'intestazione di una citazione
    assert "14:30" in L.solo_suo("Confermo martedi' ore 14:30, il collega ha scritto: va bene", [])["con_firma"]


@prova("sync: il lettore decide la classe solo quando e' acceso; in ombra scrive accanto e la classe resta delle liste")
def _():
    import sync_v2 as S
    lettura = {"classe": "positivo", "caldo": False, "non_scrivere": False, "fonte": "lettore", "caso": "C01",
               "sicurezza": "alta", "motivo": "C01"}
    assert S.classe_col_lettore("negativo", lettura, "acceso") == "positivo"
    assert S.classe_col_lettore("negativo", lettura, "ombra") == "negativo"
    assert S.classe_col_lettore("negativo", lettura, "spento") == "negativo"
    assert S.classe_col_lettore("negativo", None, "acceso") == "negativo"
    # la ricaduta sulle liste non cambia niente; «non scrivetemi» diventa soppresso
    assert S.classe_col_lettore("positivo", dict(lettura, fonte="liste", classe="negativo"), "acceso") == "positivo"
    assert S.classe_col_lettore("positivo", dict(lettura, classe="negativo", non_scrivere=True), "acceso") == "soppresso"
    assert S.classe_col_lettore("positivo", dict(lettura, classe="automatico"), "acceso") == "ooo"
    # la rete delle liste resta per i casi gravi: se le liste dicono «Cancellami» e il lettore no, decide Dre
    assert S.classe_col_lettore("negativo", lettura, "acceso", testo="Cancellami") == "da_classificare"
    # una classe decisa da una persona (deciso, v78) non si scrive: il database la rifiuta e il giro cadrebbe
    src = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "sync_v2.py"), encoding="utf-8").read()
    assert '"classificazione" in deciso' in src and "select=enriched,deciso," in src


@prova("google fit: le zone non entrano nel verdetto ne' nelle bozze (Dre, 20/10)")
def _():
    import googlefit as G, inspect, bozze as B
    assert "zona = None" in inspect.getsource(G.valuta)
    vecchio = {"verdetto": "NO", "motivo": "provincia rossa: 80 ricerche/mese", "settore": "serramenti", "settore_uguale": True,
               "ticket_min": 2000, "ticket_max": 8000, "recensioni": {"recensioni": 40, "voto": 4.8},
               "zona": {"verdetto": "ROSSO", "domanda_mese": 80, "cpc": 1.2},
               "provenienza": [{"voce": "domanda e CPC dove vendono"}, {"voce": "settore"}]}
    n = G.senza_zone(vecchio)
    assert n["verdetto"] == "SI" and n["zona"] is None and "rossa" not in n["motivo"], n
    assert [r["voce"] for r in n["provenienza"]] == ["settore"]
    assert '"zona": fit.get("zona")' not in inspect.getsource(B)


@prova("google fit: chi fa gia' Google Ads sul serio e' NO, chi lo fa poco e' da guardare (Dre, 20/10)")
def _():
    import googlefit as G
    c = {"settore": "serramenti", "settore_uguale": True, "ticket_min": 2000, "ticket_max": 8000, "come_lo_cercano": "ricerca"}
    rec = {"recensioni": 40}
    assert G.verdetto(c, None, rec, {"fa_ads": False, "annunci": 0, "giorni_ads": 0})[0] == "SI"
    v, m = G.verdetto(c, None, rec, {"fa_ads": True, "annunci": 25, "giorni_ads": 200})
    assert v == "NO" and "continuita" in m
    v, m = G.verdetto(c, None, rec, {"fa_ads": True, "annunci": 3, "giorni_ads": 400})
    assert v == "PARZIALE" and "poco" in m
    v, m = G.verdetto(c, None, rec, {"errore": "x"})
    assert v == "PARZIALE" and "non misurato" in m                      # misura fallita: si dice
    assert G.verdetto(c, None, rec, None)[0] == "SI"                     # mai chiesto (esclusione o niente chiave): non pesa


@prova("meta fit: il ticket pesa piu' di tutto, chi fa gia' Meta Ads sul serio e' NO, il canale consigliato (Dre, 20/10)")
def _():
    import googlefit as G
    base = {"settore": "serramenti", "settore_uguale": True, "tipo": "B2C", "ticket_min": 2000, "ticket_max": 8000,
            "visivo": True, "pubblico_definibile": True, "come_lo_cercano": "ricerca", "categoria_sensibile": ""}
    rec = {"recensioni": 40}
    assert G.verdetto_meta(base, rec, {"fa_meta_ads": False})[0] == "SI"
    assert G.verdetto_meta(base, rec, {"fa_meta_ads": True, "annunci_attivi": 12, "giorni": 120})[0] == "NO"
    assert G.verdetto_meta(base, rec, {"fa_meta_ads": True, "annunci_attivi": 2, "giorni": 400})[0] == "PARZIALE"
    assert G.verdetto_meta(dict(base, ticket_max=200, vendita_possibile_online=False), rec)[0] == "NO"       # ticket basso, non online
    assert G.verdetto_meta(dict(base, ticket_max=200, vendita_possibile_online=True), rec)[0] == "PARZIALE"  # e-commerce
    assert G.verdetto_meta(dict(base, ticket_max=600), rec)[0] == "PARZIALE"                                  # ticket medio
    assert G.verdetto_meta(dict(base, tipo="B2B", pubblico_definibile=False), rec)[0] == "NO"
    assert G.verdetto_meta(dict(base, categoria_sensibile="armi"), rec)[0] == "NO"
    v, m = G.verdetto_meta(dict(base, categoria_sensibile="casa"), rec)
    assert v == "PARZIALE" and "limita" in m
    assert G.verdetto_meta(dict(base, esclusione="agenzia"), rec)[0] == "NO"
    v, m = G.verdetto_meta(base, rec, None)
    assert v == "PARZIALE" and "non misurato" in m                                                            # non misurato: si dice, non e' un si'
    assert G.verdetto_meta(base, rec, {"errore": "meta: risposta vuota"})[0] == "PARZIALE"
    assert G.canale("SI", "SI") == "entrambi" and G.canale("SI", "PARZIALE") == "Google" and G.canale("NO", "PARZIALE") == "Meta"
    assert G.canale("NO", "NO") == "nessuno"
    # gli annunci della Ad Library si attribuiscono per dominio o per nome della pagina, mai per somiglianza vaga
    ads = [{"is_active": True, "start_date": "2026-01-01T00:00:00Z", "page_name": "Serramenti Rossi Srl", "snapshot": {"link_url": "https://x.example/"}},
           {"is_active": True, "start_date": "2026-06-01T00:00:00Z", "page_name": "Altra Pagina", "snapshot": {"caption": "serramentirossi.example"}},
           {"is_active": False, "start_date": "2025-01-01T00:00:00Z", "page_name": "Rossi Pizzeria", "snapshot": {}}]
    oggi = datetime.datetime(2026, 10, 20, tzinfo=datetime.timezone.utc)
    m = G.conta_meta_ads(ads, "Serramenti Rossi", "serramentirossi.example", oggi)
    assert m["annunci_attivi"] == 2 and m["annunci_totali"] == 2 and m["giorni"] == 292, m
    assert G.segnali_meta("<script src='https://connect.facebook.net/it_IT/fbevents.js'></script><a href='https://instagram.com/x'>")["pixel_meta"]
    assert not G.segnali_meta("<a href='https://facebook.com/tr?id=1'>")["facebook"]

# ── 20/10 sera: i si' li dice il lettore, e un si' caldo passa a Dre senza fermare l'analisi ──

@prova("semaforo (20/10 sera): «sì senza analisi» lo decide il lettore (classificazione positivo), non il segnale vecchio")
def _():
    import datetime, clara_foglio as C
    roma = C.ROMA
    alle = lambda h, m=0: datetime.datetime(2026, 10, 20, h, m, tzinfo=roma)        # noqa: E731
    vero_cont, vero_rimb = C.contattabile, C.rimbalzi_fermi
    try:
        C.contattabile = lambda p: not p.get("fuori")
        C.rimbalzi_fermi = lambda ora, gia=(), **k: [{"prospect_id": "r1", "azienda": "Rimbalzo srl", "quando": alle(9), "bozza": True}]
        positivi = [
            {"id": "a", "company": "Si' Vero", "classificazione": "positivo", "analysis_sent": False, "fuori": False, "last_reply_at": alle(9, 30).isoformat()},
            {"id": "b", "company": "Gia' Servito", "classificazione": "positivo", "analysis_sent": False, "fuori": False, "last_reply_at": alle(9).isoformat()},
            {"id": "c", "company": "Con Analisi", "classificazione": "positivo", "analysis_sent": True, "fuori": False, "last_reply_at": alle(9).isoformat()},
            {"id": "d", "company": "In Pipeline", "classificazione": "positivo", "analysis_sent": False, "fuori": True, "last_reply_at": alle(9).isoformat()},
            {"id": "e", "company": "Da Guardare", "classificazione": "positivo", "analysis_sent": False, "fuori": False, "last_reply_at": alle(8, 15).isoformat()},
            {"id": "f", "company": "Non e' un si'", "classificazione": "da_classificare", "analysis_sent": False, "fuori": False, "last_reply_at": alle(9).isoformat()},
        ]
        dopo = {"b": alle(9, 20)}                     # a «b» abbiamo scritto dopo la sua mail: servito
        r = C.si_fermi(alle(11), positivi=positivi, dopo=dopo, bozze={"e"})
        assert [x["azienda"] for x in r] == ["Da Guardare", "Si' Vero", "Rimbalzo srl"], [x["azienda"] for x in r]
        assert r[1]["quando"] == alle(9, 30) and not r[1]["bozza"] and r[0]["bozza"], r
        g = C.semaforo(alle(11), {"si": r, "corse": {}, "operazioni": {}, "foglio_il": None, "conversazioni": None, "ultima_corsa": None})
        assert [x["pid"] for x in g] == ["e", "r1", "a"], g
        assert "scheda" in g[0]["sta_facendo"] and "riprova" in g[2]["sta_facendo"], g
        # una nostra mail PRIMA della sua (piu' di mezz'ora prima) non e' un servizio
        assert [x["azienda"] for x in C.si_fermi(alle(11), positivi=positivi[:1], dopo={"a": alle(8, 30)}, bozze=set())][:1] == ["Si' Vero"]
    finally:
        C.contattabile, C.rimbalzi_fermi = vero_cont, vero_rimb
    # la fonte vecchia non decide piu' da nessuna parte: ne' il semaforo, ne' il foglio, ne' il riquadro rosso di Oggi
    cartella = os.path.dirname(os.path.abspath(__file__))
    for nome in ("clara_foglio.py", "foglio.py"):
        src = open(os.path.join(cartella, nome), encoding="utf-8").read()
        assert "segnali_provvisori" not in src, f"{nome} legge ancora il segnale provvisorio per decidere"
    src = open(os.path.join(cartella, "schede.py"), encoding="utf-8").read()
    assert 'v.get("si")' not in src and "lettore_di" in open(os.path.join(cartella, "foglio.py"), encoding="utf-8").read()
    import stanza as St
    fresco = {"last_reply_at": "2026-10-20T13:31:16+00:00", "enriched": {"lettore": {"fonte": "lettore", "classe": "positivo", "caldo": True, "risposta_il": "2026-10-20T13:31:16"}}}
    assert St.lettore_di(fresco)["caldo"] is True
    assert St.lettore_di({**fresco, "last_reply_at": "2026-10-20T15:00:00+00:00"}) == {}, "una lettura di una mail vecchia non vale per la nuova"
    assert St.lettore_di({**fresco, "enriched": {"lettore": {**fresco["enriched"]["lettore"], "fonte": "liste"}}}) == {}, "le liste non sono il lettore"
    assert St.lettore_di({"last_reply_at": fresco["last_reply_at"], "lettore": fresco["enriched"]["lettore"]})["classe"] == "positivo", "anche con l'alias lettore:enriched->lettore"


@prova("bozze (20/10 sera): l'attacco del modello non racconta un passaggio; se risponde un'altra persona il saluto non riusa il nome nostro")
def _():
    import seguiti as S
    assert S._attacco("Grazie per il passaggio") is None and S._attacco("grazie per il passaggio, molto gentile") is None
    assert S._attacco("Perfetto, la metto in copia") is None and S._attacco("Grazie per avermela inoltrata") is None
    assert S._attacco("Perfetto") == "Perfetto," and S._attacco("La ringrazio della risposta") == "La ringrazio della risposta,"
    assert S._attacco("Buongiorno Francesco, grazie") is None and S._attacco("Salve, perfetto") is None, "un saluto nell'attacco fa un doppio saluto"
    letti = {"ultima_nostra": "Buongiorno Luca, le avevo scritto...", "ultima_nostra_a": "luca@esempio.invalid",
             "ultima_loro_da": "francesco@esempio.invalid", "ultima_loro": "mi ha passato la comunicazione il collega, me ne occupo io"}
    assert S.saluto({"name": "Luca"}, letti) == "Salve,", "ha risposto un'altra persona: il nome della nostra mail non vale"
    assert S.saluto({"name": "Luca"}, {**letti, "ultima_loro_da": "luca@esempio.invalid"}) == "Salve Luca,"
    assert S.saluto({"name": "Luca"}, {**letti, "ultima_loro_da": "LUCA@Esempio.invalid"}) == "Salve Luca,", "lo stesso indirizzo, maiuscole diverse"
    assert S.saluto({"name": "Luca"}, {**letti, "ultima_loro_da": None}) == "Salve Luca,", "senza mittente noto si fa come prima"


@prova("bozze (20/10 sera): un sì caldo per il lettore è INT-01 con la call, non INT-23; una bozza incoerente per l'attacco si ricompone col template puro")
def _():
    import bozze as Bz
    caldo = {"id": "p1", "last_reply_at": "2026-10-20T13:31:16+00:00",
             "enriched": {"lettore": {"fonte": "lettore", "classe": "positivo", "caldo": True, "caso": "C05", "risposta_il": "2026-10-20T13:31:16"}}}
    b = {"intento": "INT-23", "template": "INT-23", "nota": "", "fermati": "no", "bozza": "x"}
    b2 = Bz.intento_col_lettore(b, caldo)
    assert b2["intento"] == "INT-01" and b2["template"] == "INT-01" and "lettore" in b2["nota"], b2
    assert Bz.intento_col_lettore(b, {**caldo, "enriched": {}}) is b, "senza lettore non si tocca"
    assert Bz.intento_col_lettore(b, caldo, gruppo="FOLLOW UP 1") is b, "nei gruppi no"
    assert Bz.intento_col_lettore({**b, "intento": "INT-02"}, caldo)["intento"] == "INT-02", "INT-02 (fissa la call) non contraddice un caldo"
    tiepido = {**caldo, "enriched": {"lettore": {**caldo["enriched"]["lettore"], "caldo": False}}}
    assert Bz.intento_col_lettore(b, tiepido) is b, "un si' non caldo che vuole solo il materiale resta INT-23"
    # la ricomposizione: l'attacco del modello rende la bozza incoerente, il template puro no
    modello = {"intento": "INT-01", "template": "INT-01", "attacco": "Grazie per il passaggio", "bozza": "testo del modello", "fermati": "no", "nota": ""}
    composta = {**modello, "bozza": "Salve,\nGrazie per il passaggio, vi inoltro...", "dal_codice": True, "bozza_modello": "testo del modello"}
    chiamate = []
    def componi(bm, p, letti):
        chiamate.append(bm.get("attacco"))
        return {**bm, "bozza": "Salve,\nVa bene perfetto, vi inoltro...", "dal_codice": True}
    def giudica(letti, testo, gruppo=None, cc=None):
        return ("INCOERENTE", "grazie per il passaggio al contatto nuovo") if "passaggio" in testo else ("COERENTE", "")
    r = Bz.ricomponi_senza_attacco(composta, modello, {"id": "p1"}, {}, None, componi=componi, giudica=giudica)
    assert r and r[1] == "COERENTE" and r[0]["bozza"].startswith("Salve,\nVa bene perfetto") and "ricomposta" in r[0]["nota"], r
    assert chiamate == [""], "si ricompone senza l'attacco del modello"
    assert Bz.ricomponi_senza_attacco(composta, modello, {"id": "p1"}, {}, "FOLLOW UP 1", componi=componi, giudica=giudica) is None, "nei gruppi no"
    assert Bz.ricomponi_senza_attacco({**composta, "dal_codice": False}, modello, {"id": "p1"}, {}, None, componi=componi, giudica=giudica) is None, "solo sul template composto dal codice"
    assert Bz.ricomponi_senza_attacco(composta, {**modello, "attacco": ""}, {"id": "p1"}, {}, None, componi=componi, giudica=giudica) is None, "senza attacco non c'e' niente da togliere"
    ancora = lambda letti, testo, gruppo=None, cc=None: ("INCOERENTE", "altro")      # noqa: E731
    assert Bz.ricomponi_senza_attacco(composta, modello, {"id": "p1"}, {}, None, componi=componi, giudica=ancora) is None, "se resta incoerente va a Dre come prima"
    src = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "bozze.py"), encoding="utf-8").read()
    assert "intento_col_lettore(b, p, gruppo)" in src and "ricomponi_senza_attacco(b, b_modello" in src, "il motore deve usarle davvero"
    # il giorno lo sceglie il codice: un «fermati» del modello solo sullo slot non ferma la mail
    assert Bz.fermati_sullo_slot("si': slot sotto 48 ore; serve la sua conferma prima")
    assert Bz.fermati_sullo_slot("sì: lo slot proposto è lo stesso giorno dell'invio")
    assert not Bz.fermati_sullo_slot("no") and not Bz.fermati_sullo_slot("") and not Bz.fermati_sullo_slot(None)
    assert not Bz.fermati_sullo_slot("si': nella sua ultima mail sembra dire di no"), "un dubbio sulla persona resta"
    assert 'fermati_sullo_slot(b.get("fermati"))' in src and 'b.get("dal_codice") and b.get("giorno")' in src, "vale solo col giorno scelto dal codice"


@prova("conversazione (20/10 sera): un sì CALDO prima dell'analisi suona e passa a Dre: «Da chiamare» col cellulare, «Da rispondere» senza; un sì non caldo no")
def _():
    import segnale_provvisorio as S
    f = _ConversazioniFinte(analisi_ore_fa=None, stato={})
    f.caldo = True
    f.scrive("Se volete potete inviarmi tutto e poi ci sentiamo.\n\nMario Rossi\nCell. 333 0000001", minuti_fa=20)
    f.giro()
    assert len(f.notifiche) == 1, f.notifiche
    n = f.notifiche[0]
    assert n["titolo"].startswith("È entrato in conversazione") and "Vuole sentirti" in n["testo"] and n["url"].endswith("#/s/lead/p1"), n
    assert f.stato["p1"]["notificata"] is True and f.stato["p1"]["caldo"] is True and f.stato["p1"]["aperta_il"], f.stato
    d = f.snella_lead.get("p1")
    assert d and d["stato"] == "Da chiamare" and d["chiamata"] == "richiamare" and d["richiamare_il"] == f.ora.astimezone(zoneinfo.ZoneInfo("Europe/Rome")).date().isoformat(), d
    # lo stesso si' caldo senza un cellulare (solo il fisso in firma): suona lo stesso, ma e' «Da rispondere», gli scrive Dre
    for firma in ("", "\n\nMario Rossi\nTel. 02 00000001"):
        s = _ConversazioniFinte(analisi_ore_fa=None, stato={})
        s.caldo = True
        s.scrive("Se volete potete inviarmi tutto e poi ci sentiamo." + firma, minuti_fa=20)
        s.giro()
        d = s.snella_lead.get("p1")
        assert len(s.notifiche) == 1 and d and d["stato"] == "Da rispondere" and d["responsabile"] == "Dramane", (firma, s.notifiche, d)
        assert d["prossima_mossa"] == S.SENZA_CELLULARE and not d.get("chiamata"), d
    f.giro()
    f.giro()
    assert len(f.notifiche) == 1, "lo stesso caldo ha suonato piu' volte"
    # poi arriva l'analisi e lui riscrive: e' la stessa conversazione, non suona di nuovo
    f.analisi = (f.ora - datetime.timedelta(minutes=10)).strftime("%Y-%m-%dT%H:%M:%S+00:00")
    f.scrive("Ricevuto, grazie: ci sentiamo mercoledi'", minuti_fa=2)
    f.giro()
    assert len(f.notifiche) == 1, f.notifiche
    # un si' non caldo prima dell'analisi: niente (lo serve il sistema con l'analisi)
    g = _ConversazioniFinte(analisi_ore_fa=None, stato={})
    g.scrive("Si', mandatemi pure l'analisi", minuti_fa=20)
    g.giro()
    assert g.notifiche == [] and g.stato == {} and g.snella_lead == {}, (g.notifiche, g.stato, g.snella_lead)
    # Dre ha gia' toccato il lead dopo la sua mail: la notifica suona, la sua decisione non si tocca
    h = _ConversazioniFinte(analisi_ore_fa=None, stato={})
    h.caldo = True
    h.snella_lead["p1"] = {"prospect_id": "p1", "stato": "Perso", "aggiornato_il": h.ora.strftime("%Y-%m-%dT%H:%M:%S+00:00")}
    h.scrive("Chiamatemi pure al 333 0000000", minuti_fa=20)
    h.giro()
    assert len(h.notifiche) == 1 and h.snella_lead["p1"]["stato"] == "Perso", (h.notifiche, h.snella_lead)
    # la prova a secco non scrive niente
    k = _ConversazioniFinte(analisi_ore_fa=None, stato={})
    k.caldo = True
    k.scrive("Volentieri, poi ci sentiamo", minuti_fa=20)
    assert len(k.giro(prova=True)) == 1 and k.notifiche == [] and k.stato == {} and k.snella_lead == {}
    # una notifica non arrivata al caldo si riprova
    j = _ConversazioniFinte(analisi_ore_fa=None, stato={})
    j.caldo, j.dispositivi = True, 0
    j.scrive("Volentieri, poi ci sentiamo", minuti_fa=20)
    j.giro()
    assert j.notifiche == [] and j.stato["p1"]["notificata"] is False, j.stato
    j.dispositivi = 1
    j.giro()
    assert len(j.notifiche) == 1 and j.stato["p1"]["notificata"] is True, (j.notifiche, j.stato)



@prova("le strade (21/10): max 3, manda sempre con la bozza, chiama solo col cellulare, ricontatta con una data futura")
def _():
    import strade as S
    oggi = datetime.date(2026, 10, 22)
    MANDA = {"etichetta": "Chiedi il contatto del collega", "perche": "ci ha girato a un collega", "azione": "manda", "bozza": "Buongiorno,\n\nmi può girare il contatto del collega? Appena ce l'ho scrivo io a lui.", "intento": "INT-08"}
    RINVIO = {"etichetta": "Rimanda a gennaio", "perche": "non è il momento", "azione": "ricontatta", "data": "2027-01-12"}
    CHIUDI = {"etichetta": "Chiudi: non interessato", "perche": "un no cortese", "azione": "chiudi", "classe": "negativo"}
    CHIAMA = {"etichetta": "Chiamalo tu oggi", "perche": "ha lasciato il cellulare", "azione": "chiama"}
    NIENTE = {"etichetta": "Lascia che si faccia vivo lui", "perche": "ci scrive lui", "azione": "niente"}
    buone, scartate = S.valida([MANDA, RINVIO, CHIUDI, CHIAMA, NIENTE], cellulare=True, oggi=oggi)
    assert [s["azione"] for s in buone] == ["manda", "ricontatta", "chiudi"], buone
    assert any(m == "oltre la terza" for _, m in scartate)
    # manda senza bozza no; chiama senza cellulare no; ricontatta nel passato o senza data no; classe strana no; etichetta lunga no; doppie no
    buone, scartate = S.valida([{**MANDA, "bozza": ""}, CHIAMA, {**RINVIO, "data": "2026-10-22"}, {**RINVIO, "data": "ieri"}, {**CHIUDI, "classe": "soppresso"},
                                {**NIENTE, "etichetta": "Una etichetta davvero troppo lunga per una carta sul telefono"}, NIENTE, NIENTE, {"etichetta": "Boh", "perche": "x", "azione": "boh"}],
                               cellulare=False, oggi=oggi)
    assert [s["azione"] for s in buone] == ["niente"], buone
    motivi = " | ".join(m for _, m in scartate)
    for atteso in ("manda senza una bozza", "chiama senza un cellulare", "gia' passata", "senza una data vera", "classe che non esiste", "parole", "doppia", "azione sconosciuta"):
        assert atteso in motivi, (atteso, motivi)
    # la forma: solo le chiavi che l'app conosce, data e classe pulite dove non servono
    b, _ = S.valida([RINVIO, {**CHIUDI, "data": "2027-01-01"}], cellulare=False, oggi=oggi)
    assert set(b[0]) == {"etichetta", "perche", "azione", "bozza", "data", "classe", "intento"} and b[1]["data"] is None and b[0]["bozza"] is None
    # il tetto di spesa esiste ed e' quello detto a Dre (3 $), come il lettore
    assert S.TETTO_GIORNO == 3.0 and S.MAX_STRADE == 3 and S.MIN_STRADE == 2
    # chi non e' una persona non ha strade
    assert not S.e_persona({"perche": "sì: autorisposta di servizio", "azione": {}}, {"classificazione": "ooo"})
    assert not S.e_persona({"perche": "decidi tu", "azione": {"lettura": {"autorisposta": True}}}, {"classificazione": "rinvio"})
    assert S.e_persona({"perche": "Decidi tu: dice no ma tiene la porta aperta", "azione": {"lettura": {"autorisposta": False}}}, {"classificazione": "rinvio"})
    # una generazione sola: si rifa' solo se il lead ha riscritto dopo
    pr = {"azione": {"strade": [RINVIO, NIENTE], "strade_il": "2026-10-21T22:00:00+00:00"}}
    assert not S.filo_cambiato(pr, {"last_reply_at": "2026-10-20T10:00:00+00:00"})
    assert S.filo_cambiato(pr, {"last_reply_at": "2026-10-22T08:00:00+00:00"})
    assert S.filo_cambiato({"azione": {}}, {"last_reply_at": "2026-10-20T10:00:00+00:00"})


@prova("l'allenamento (21/10): la strada che Dre sceglie di solito va prima; tre uguali di fila sullo stesso caso e il sistema non chiede piu'; le scelte entrano nei prompt")
def _():
    import strade as S
    import bozze
    scelta = lambda caso, et, az, il, strade=None, porta=False: {"caso": caso, "etichetta": et, "azione": az, "il": il, "strade": strade or [et, "Chiudi: non interessato"], "porta_aperta": porta}   # noqa: E731
    scelte = [scelta("C27", "Rimanda a gennaio", "ricontatta", "2026-10-25T10:00:00+00:00", porta=True),
              scelta("C27", "Rimanda a gennaio", "ricontatta", "2026-10-24T10:00:00+00:00"),
              scelta("C26", "Lascia che si faccia vivo lui", "niente", "2026-10-23T10:00:00+00:00"),
              scelta("C27", "Rimanda a gennaio", "ricontatta", "2026-10-22T10:00:00+00:00"),
              scelta("C27", "Chiudi: non interessato", "chiudi", "2026-10-21T10:00:00+00:00")]
    strade = [{"etichetta": "Chiudi: non interessato", "azione": "chiudi"}, {"etichetta": "Rispondi all'obiezione", "azione": "manda"}, {"etichetta": "Rimanda a gennaio", "azione": "ricontatta"}]
    # la solita prima, il resto nell'ordine del modello
    assert [s["etichetta"] for s in S.ordina(strade, scelte, "C27")] == ["Rimanda a gennaio", "Chiudi: non interessato", "Rispondi all'obiezione"]
    assert [s["etichetta"] for s in S.ordina(strade, scelte, "C99")] == [s["etichetta"] for s in strade]
    assert [s["etichetta"] for s in S.ordina(strade, scelte, None)] == [s["etichetta"] for s in strade]
    # stessa azione, etichetta diversa: viene prima lo stesso (seconda fascia)
    assert S.ordina([strade[0], {"etichetta": "Riprendi a febbraio", "azione": "ricontatta"}], scelte, "C27")[0]["etichetta"] == "Riprendi a febbraio"
    # tre uguali DI FILA sullo stesso caso: abitudine; quattro con una diversa in mezzo no; senza caso mai
    assert S.abitudine(scelte, "C27") == {"azione": "ricontatta", "etichetta": "Rimanda a gennaio"}
    assert S.abitudine(scelte, "C26") is None
    assert S.abitudine([scelte[4]] + scelte[:2], "C27") is None
    assert S.abitudine(scelte, None) is None and S.abitudine(scelte, "") is None
    assert S.abitudine(scelte[:3] + [scelta("C27", "rimanda a gennaio.", "ricontatta", "2026-10-20T10:00:00+00:00")], "C27") is not None, "maiuscole e punto non contano"
    # gli esempi nel prompt, con le parole che Dre ha chiesto
    testo = S.esempi_per_prompt(scelte)
    assert "In un caso C27" in testo and "con spiraglio Dre ha scelto: «Rimanda a gennaio» (ricontatta)" in testo, testo
    assert "scartando: Chiudi: non interessato" in testo
    assert S.esempi_per_prompt([]) == ""
    # e arrivano anche alle bozze (bozze.main li aggiunge a LEZIONI)
    src = open(bozze.__file__, encoding="utf-8").read()
    assert "strade.esempi_per_prompt(" in src and "LEZIONI += " in src
    # la scelta ha la stessa forma dall'app e dal sistema (caso, intento, le strade, quale, quando)
    r = S.record_scelta([{"etichetta": "A"}, {"etichetta": "B"}], {"etichetta": "A", "azione": "niente"}, "C26", "INT-06", datetime.datetime(2026, 10, 22, 8, tzinfo=datetime.timezone.utc))
    assert r == {"etichetta": "A", "azione": "niente", "caso": "C26", "intento": "INT-06", "strade": ["A", "B"], "il": "2026-10-22T08:00:00+00:00", "porta_aperta": False}
    # l'automatica non insegna (si rafforzerebbe da sola): e' segnata
    assert S.record_scelta([], {"etichetta": "A", "azione": "niente"}, "C26", None, datetime.datetime(2026, 10, 22, tzinfo=datetime.timezone.utc), automatica=True)["automatica"] is True
    # l'app scrive le stesse cose: approvata da «Dre (app, strada: …)», nota «Dall'app: strada scelta: …», stati fra i 12
    radice = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    regole = open(os.path.join(radice, "src", "snella", "regole.ts"), encoding="utf-8").read()
    assert "export function stradeDi" in regole and "export function scrittureStrada" in regole and "export const MAX_STRADE = 3" in regole
    assert "strada: (etichetta: string) => `Dall'app: strada scelta: ${etichetta}`" in regole
    assert ", strada: ${scelta.etichetta})`" in regole and "scelta: scelta_record" in regole
    assert "stato: 'Da ricontattare'" in regole and "stato: 'Da chiamare', chiamata: 'richiamare'" in regole
    scheda = open(os.path.join(radice, "src", "snella", "SchedaLead.tsx"), encoding="utf-8").read()
    assert 'titolo="Decidi tu"' in scheda and "Nessuna di queste" in scheda and "stradeDi(dati.proposte)" in scheda
    # l'operazione e' registrata nello schema, ogni 15 minuti, in corsia leggera
    sql = open(os.path.join(radice, "supabase", "schema_v97.sql"), encoding="utf-8").read()
    assert "('strade'," in sql and "'python3 scripts/strade.py', 15," in sql
    import direttore
    assert direttore.corsia_di("strade") == "leggera"


@prova("foglio: la risposta del lead vale anche se la scheda e' indietro (21/10, CEFOSMET)")
def _():
    import foglio as F
    ora = datetime.datetime(2026, 10, 21, 11, tzinfo=datetime.timezone.utc)
    p = {"id": "p1", "classificazione": "positivo", "last_reply_at": "2026-10-21T08:49:00+00:00",
         "analysis_sent_at": "2026-10-19T13:22:00+00:00", "pipeline_stage": None, "stage": "risposto"}
    s_vecchia = {"stato": "Analisi inviata", "ultima_risposta": "2026-10-16T11:39:00+00:00"}
    assert F.fase_di(p, s_vecchia, None, [], None, None, ora=ora)[0] == F.CONV
    assert F._piu_recente(None, "2026-10-21T08:49:00+00:00") == "2026-10-21T08:49:00+00:00"
    assert F._piu_recente("2026-10-21T08:49:00+00:00", "2026-10-16T11:39:00+00:00") == "2026-10-21T08:49:00+00:00"


@prova("sync: una risposta nuova si vede dalla Master Inbox, non dalla rotazione (21/10, CEFOSMET)")
def _():
    import sync_v2 as S
    def pagina(offset, limit):
        tutte = [{"last_reply_time": "2026-10-21T08:49:00.000Z", "lead_email": "A@x.invalid", "email_lead_id": 1, "email_campaign_id": 9, "email_lead_map_id": 77},
                 {"last_reply_time": "2026-10-21T07:00:00.000Z", "lead_email": "b@x.invalid", "email_lead_id": 2, "email_campaign_id": 9, "email_lead_map_id": 78},
                 {"last_reply_time": "2026-10-20T20:00:00.000Z", "lead_email": "c@x.invalid", "email_lead_id": 3, "email_campaign_id": 9, "email_lead_map_id": 79}]
        return {"data": tutte[offset:offset + limit]}
    f = S.risposte_fresche("2026-10-21T04:00:00", pagina=pagina)
    assert set(f) == {"a@x.invalid", "b@x.invalid"} and f["a@x.invalid"]["lead_map"] == 77, f   # c e' prima della finestra
    known = {"a@x.invalid": {"last_reply_at": "2026-10-16T11:39:00+00:00"}, "b@x.invalid": {"last_reply_at": "2026-10-21T07:00:00+00:00"}}
    assert S.da_rileggere_perche_fresca("a@x.invalid", known, f)          # ha riscritto dopo quella che conosciamo
    assert not S.da_rileggere_perche_fresca("b@x.invalid", known, f)      # gia' vista
    assert not S.da_rileggere_perche_fresca("zz@x.invalid", known, f)
    def rotta(offset, limit):
        raise RuntimeError("giu'")
    assert S.risposte_fresche("2026-10-21T04:00:00", pagina=rotta) == {}  # servizio giu': il giro va come prima


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
