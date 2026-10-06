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


@prova("prezzo: fascia dalla domanda, il bilancio corregge, mai sotto il floor, e non entra in una mail")
def _():
    import prezzo as Z, manda as M
    P = {"base": 1400, "soglia": 5000, "quota": 0.10, "floor": 1200, "fascia": 0.15, "quota_cattura": 0.03, "conversione": 0.02, "tetto_quota": 1 / 3,
         "scaglioni": [[1000000, 0.02], [3000000, 0.015], [10000000, 0.01], [None, 0.005]], "quota_agenzia": 0.25,
         "margine": [[0, 0.5], [0.03, 0.7], [0.08, 1.0], [0.15, 1.2], [None, 1.4]], "cluster": {"A": 1.1, "B": 0.9}}
    assert Z.scaglioni(8_000_000, P["scaglioni"]) == 100000                    # a scaglioni, come l'IRPEF
    vol = {"tam": 91020, "cpc_medio": 3.54}
    b = Z.calcola({"enriched": {}}, P, vol, {}, {"fa_ads": True})
    assert b["formula"] == "domanda" and b["fascia"][0] < b["punto"] < b["fascia"][1] and b["affidabilita"] == "media"
    c = Z.calcola({"enriched": {"bilancio": {"fatturato": 2000000, "utile": -1, "anno": 2025}}}, P, vol, {}, {})
    assert c["formula"] == "bilancio" and c["punto"] >= P["floor"] and any("rischio" in f for f in c["flag"])
    assert Z.calcola({"enriched": {}}, P, None, {}, {}) is None                 # senza niente, niente numero
    assert M.controlla("il canone sarebbe 2.000 € al mese", {"enriched": {"prezzo": {"punto": 2000, "fascia": [1700, 2300]}}})


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
         "analysis_sent": False, "analysis_pdf": "https://x/analisi.pdf"}
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
    assert R.finestra(datetime.datetime(2026, 9, 29, 10, 0, tzinfo=roma))       # martedi' 10:00
    assert not R.finestra(datetime.datetime(2026, 9, 29, 8, 59, tzinfo=roma))
    assert not R.finestra(datetime.datetime(2026, 9, 29, 17, 0, tzinfo=roma))
    assert not R.finestra(datetime.datetime(2026, 10, 3, 11, 0, tzinfo=roma))   # sabato
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
    assert R.MAX_PER_GIRO <= 5 and R.MAX_AL_GIORNO <= 15
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
    assert "Le propongo giovedì 1 ottobre alle 14:30" in t and "nel caso quel giorno" in t and "https://cal/NUOVO" in t and "VECCHIO" not in t
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
    assert PR.INTENTI_OK == ("INT-01", "INT-02", "INT-03", "INT-23"), "la lista degli intenti automatici e' cambiata senza Dre"
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
    assert PR.finestra(lun.replace(hour=10)) and not PR.finestra(lun.replace(hour=20)), "la finestra dei si' non e' piu' 9-17"
    assert not PR.finestra(sab.replace(hour=10)), "i si' partono di sabato"
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


@prova("INT-23, vuole il materiale ma non la call: si manda l'analisi e non si propone nessun orario (caso Oikos, 6/10)")
def _():
    import bozze as Bz
    import seguiti as S
    vero = Bz.template_verbatim()
    t = S.risposta("INT-23", {}, {}, "https://cal/NUOVO", giorno="giovedì 8 ottobre alle 15:30", testo_file=vero, garanzia=True)
    assert t, "INT-23 deve avere il suo testo dal template di Dre"
    assert "Le propongo" not in t and "giovedì 8 ottobre" not in t, "INT-23 propone comunque un orario: il playbook dice di non farlo"
    assert "calendar" not in t and "cal/NUOVO" not in t and "Calendario" not in t, "INT-23 non spinge il calendario"
    assert "confrontarmi" not in t and "a disposizione" in t, "si dice che restiamo a disposizione, come dice il playbook"
    assert "vi inoltro qui l'analisi" in t and "presentazione" in t, "l'analisi e la presentazione restano"
    # senza giorno dal calendario INT-23 si scrive lo stesso (non serve un orario)
    assert S.risposta("INT-23", {}, {}, "x", giorno=None, testo_file=vero, garanzia=False)
    # INT-01 resta com'era: propone l'orario
    assert "Le propongo giovedì 8 ottobre alle 15:30" in S.risposta("INT-01", {}, {}, "x", giorno="giovedì 8 ottobre alle 15:30", testo_file=vero)


@prova("i template di Dre: se il bucket non risponde si usa l'ultima copia buona, non il vuoto (6/10)")
def _():
    import tempfile, urllib.request as U
    import bozze as Bz
    loc = os.path.join(tempfile.gettempdir(), "odyn-risposte-template.md")
    c_era = os.path.exists(loc)
    prima = open(loc, encoding="utf-8").read() if c_era else None
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
        else:
            os.remove(loc)


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
        assert m == "PATCH" and "stato=eq.approvata" in path and corpo == {"stato": "in_invio"}
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
