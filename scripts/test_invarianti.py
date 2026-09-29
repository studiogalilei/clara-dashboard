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
    # senza l'ultima mail loro non si scrive niente
    assert L.regola_dura(None, {**base, "ultima_loro": ""})[0] == "salta"
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
    promette = "Salve, grazie. Le inoltro qui l'analisi che abbiamo fatto sulla vostra azienda."
    assert B.cancello(promette, senza_analisi=True), "una bozza promette ancora un'analisi impossibile"
    assert not B.cancello(promette, senza_analisi=False), "il cancello blocca anche quando l'analisi c'e'"
    onesta = ("Salve, grazie per il riscontro. Le dico subito una cosa: su Google la domanda "
              "nel vostro settore e nella vostra zona e' troppo bassa perche' valga la spesa.")
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
    import prima_risposta as R
    # 29/9: Dre vuole che la prima risposta parta da sola. E' il punto piu'
    # delicato del sistema: approva al posto di una persona. Ogni porta del
    # cancello deve restare chiusa quando deve.
    let = {"coerenza": "COERENTE", "scritto_dopo_di_lei": 0, "ultima_loro": "si' grazie, mandatemi l'analisi"}
    pr = {"id": 1, "tipo": "risposta", "titolo": "Bozza per Rossi, INT-01",
          "azione": {"bozza": "Salve,\n\necco l'analisi.", "intento": "INT-01", "lettura": let}}
    p = {"id": "x", "email": "a@b.it", "classificazione": "positivo", "stage": "risposto",
         "analysis_sent": False, "analysis_pdf": "https://x/analisi.pdf"}
    assert R.perche_no(pr, p) == [], R.perche_no(pr, p)
    def con(pr_mod=None, let_mod=None, p_mod=None, az_mod=None):
        az = {**pr["azione"], "lettura": {**let, **(let_mod or {})}, **(az_mod or {})}
        return R.perche_no({**pr, **(pr_mod or {}), "azione": az}, {**p, **(p_mod or {})})
    for caso, motivo in (
        (con(pr_mod={"tipo": "umano"}), "una bozza «da guardare tu»"),
        (con(pr_mod={"titolo": "Da guardare tu: Rossi"}), "un titolo «da guardare tu»"),
        (con(let_mod={"gruppo": "FOLLOW UP 1"}), "un follow-up"),
        (con(let_mod={"gruppo": "GIGANTE BUONO"}), "un gigante buono"),
        (con(az_mod={"intento": "INT-13"}), "una domanda sul prezzo"),
        (con(az_mod={"intento": "INT-GB"}), "un intento del gigante buono"),
        (con(let_mod={"coerenza": "INCOERENTE"}), "una bozza incoerente"),
        (con(let_mod={"scritto_dopo_di_lei": 1}), "chi ha gia' avuto una nostra mail dopo la sua"),
        (con(let_mod={"detto_no": True}), "chi ha detto no"),
        (con(let_mod={"autorisposta": True}), "un'autorisposta"),
        (con(let_mod={"girato_a": ["c@b.it"]}), "un inoltro a un collega"),
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
    ):
        assert caso, f"la prima risposta automatica farebbe partire {motivo}"
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
    assert "prima-risposta-automatica" in R.FIRMA
    import pathlib
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
