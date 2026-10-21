#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""LA STANZA — le mani di Clara verso il database (7/9/2026).

Due cose sole: parlare con Supabase (sb) e mettere una proposta nella stanza
(proponi). Chi legge e capisce e' cervello.py; chi decide e' Dre. Questo
file e' solo la porta di servizio, e la usano sia la rilettura sia
l'ascoltatore, cosi' la scrittura di una proposta e' una e non due.
"""

import datetime
import json
import re
import sys
import os
import urllib.error
import urllib.parse
import urllib.request

RADICE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def quando(iso):
    """La data come la scrive il database, con QUALUNQUE numero di decimali.

    Postgres scrive i microsecondi senza zeri finali («...28.13447+00:00»), e
    Python sotto la 3.11 accetta solo tre o sei cifre: chi legge quella data
    finisce in ValueError. Il cloud gira su 3.12 e non se ne accorge, il Mac su
    3.9 sì, quindi il guasto si vede solo qui e sembra un mistero. Trovato il
    26/9 in salute.py, ritrovato il 28/9 nel direttore: sta qui perché lo usino
    tutti invece di riscoprirlo ogni volta.
    """
    t = re.sub(r"\.(\d{1,6})\d*", lambda m: "." + m.group(1).ljust(6, "0"), (iso or "").replace("Z", "+00:00"))
    return datetime.datetime.fromisoformat(t)


def env(nome):
    v = os.environ.get(nome)
    if v:
        return v
    for f in (".env.local", ".env"):
        p = os.path.join(RADICE, f)
        if not os.path.exists(p):
            continue
        for riga in open(p, encoding="utf-8"):
            if riga.strip().startswith(nome + "="):
                return riga.split("=", 1)[1].strip().strip("\"'")
    return None


URL = env("VITE_SUPABASE_URL")
CHIAVE = env("SUPABASE_SERVICE_KEY") or env("SUPABASE_SERVICE_ROLE_KEY")


def _chi_scrive():
    """Il nome di chi sta scrivendo, per il registro. Il modo ovvio (il nome del
    file lanciato) fallisce quando il codice parte con «python3 -c» o dentro un
    altro script: allora il nome diventa «-c» o vuoto, e nel registro resta una
    riga anonima. Trovato il 26/9: 401 righe su 713 senza nome, cioe' dopo un
    guaio non si risaliva a chi aveva cambiato cosa. Qui si guarda anche la pila
    delle chiamate, che dice sempre da quale file arriva la scrittura."""
    nome = os.path.basename(sys.argv[0] or "").replace(".py", "")
    if nome and nome not in ("-c", "-", "python", "python3", "<stdin>"):
        return nome
    try:                      # il primo file nostro che ha chiamato, dal basso
        import traceback
        qui = os.path.dirname(os.path.abspath(__file__))
        for f in reversed(traceback.extract_stack()[:-1]):
            d = os.path.dirname(os.path.abspath(f.filename))
            base = os.path.basename(f.filename).replace(".py", "")
            if d.startswith(qui) and base not in ("stanza", "<stdin>") and not base.startswith("<"):
                return base
    except Exception:
        pass
    return "a-mano"           # scritto da una persona in una finestra, non da un'operazione


CHI_SCRIVE = _chi_scrive()


def sb(metodo, percorso, corpo=None, intestazioni=None):
    if not URL or not CHIAVE:
        raise RuntimeError("manca VITE_SUPABASE_URL o la service key in .env.local")
    req = urllib.request.Request(
        URL.rstrip("/") + percorso, method=metodo,
        # 16/10: un sito con un carattere nullo (\u0000) faceva cadere ogni giro del Google Fit:
        # Postgres non accetta il nullo nel testo, quindi qui, in un punto solo, non entra mai
        data=json.dumps(corpo).replace("\\u0000", "").encode() if corpo is not None else None,
        headers={"apikey": CHIAVE, "Authorization": "Bearer " + CHIAVE,
                 "Content-Type": "application/json",
                 # IL REGISTRO (25/9): ogni scrittura porta il nome dello script; il database
                 # lo mette in `registro` accanto a cosa e' cambiato (trigger registra_*)
                 "X-Clara-Script": CHI_SCRIVE, **(intestazioni or {})})
    try:
        with urllib.request.urlopen(req, timeout=40) as r:
            grezzo = r.read()
            dati = json.loads(grezzo) if grezzo else None
            # 29/9: il database si ferma a mille righe qualunque «limit» si chieda.
            # Se una lettura torna esattamente mille righe e ne voleva di piu', lo si dice.
            m = re.search(r"[?&]limit=(\d+)", percorso)
            if metodo == "GET" and isinstance(dati, list) and len(dati) == 1000 and m and int(m.group(1)) > 1000:
                print(f"  (attenzione: la lettura si e' fermata al tetto di 1000 righe, usa sb_tutte: {percorso[:80]})", file=sys.stderr)
            return dati
    except urllib.error.HTTPError as e:
        corpo = e.read()[:300].decode(errors="replace")
        # 9/10: il 402 e' il database che non c'e' piu' (quota di traffico finita, piano
        # bloccato). Stanotte e' scattato alle 4:50 e per cinque ore sessanta giri del
        # direttore hanno fallito in silenzio, uno ogni cinque minuti, perche' questo
        # errore era uguale a tutti gli altri. Un database spento si dice con parole sue.
        if e.code == 402:
            raise RuntimeError(f"SUPABASE BLOCCATO (402): il progetto e' limitato, serve Dre su Billing. {corpo}")
        raise RuntimeError(f"{e.code} {corpo}")


def sb_tutte(percorso, passo=1000, chiave="id"):
    """TUTTE le righe, a pagine (29/9). Il database ne restituisce al massimo mille
    per richiesta, qualunque «limit» si chieda: calendario e Stripe cercavano fra
    mille aziende su 13.230, e nessuno se ne accorgeva perche' mille righe sembrano
    tutte. Chi vuole tutto usa questa, non un limit grande."""
    base = re.sub(r"([&?])limit=\d+&?", r"\1", percorso).rstrip("&?")
    # a pagine serve un ordine senza pari: la chiave della tabella (id, salvo dove si chiama altrimenti)
    if "order=" not in base:
        base += ("&" if "?" in base else "?") + f"order={chiave}"
    elif not re.search(rf"order=(?:[^&]*,)?{chiave}(?:\.|,|&|$)", base):
        base = re.sub(r"(order=[^&]*)", rf"\1,{chiave}.asc", base, count=1)
    sep = "&" if "?" in base else "?"
    righe, da = [], 0
    while True:
        pezzo = sb("GET", f"{base}{sep}limit={passo}&offset={da}") or []
        righe += pezzo
        if len(pezzo) < passo:
            return righe
        da += passo


def soldi_clienti(ids=None):
    """LA CASSAFORTE (Dre, 29/9: «i soldi li vediamo solo io e Giacomo»). Canone,
    fatturazione, prezzo suggerito e numeri del cliente stanno in soldi_clienti
    (schema_v67); gli script li leggono con la chiave di servizio. {prospect_id: riga}."""
    # 29/9 (schema_v68): prezzo, bilancio e valore stanno nel riservato di Dre
    out = {}
    for tabella in ("soldi_clienti", "riservato_clienti"):
        if ids is not None:
            lista = [i for i in ids if i]
            righe = []
            for i in range(0, len(lista), 100):
                righe += sb("GET", f"/rest/v1/{tabella}?select=*&prospect_id=in.({','.join(lista[i:i+100])})") or []
        else:
            righe = sb_tutte(f"/rest/v1/{tabella}?select=*")
        for r in righe:
            out.setdefault(r["prospect_id"], {}).update({k: v for k, v in r.items() if v is not None or k not in out.get(r["prospect_id"], {})})
    return out


def con_soldi(p, soldi):
    """La scheda con i suoi soldi rimessi al loro posto, in memoria: canone e, dentro
    enriched, prezzo, bilancio e valore. Cosi' la logica degli script non cambia."""
    s = (soldi or {}).get((p or {}).get("id"))
    if not p or not s:
        return p
    arr = dict(p.get("enriched") or {})
    for k in ("prezzo", "bilancio", "valore"):
        if s.get(k) is not None:
            arr[k] = s[k]
    return {**p, "canone": p.get("canone") if p.get("canone") is not None else s.get("canone"), "enriched": arr}


def soldi_progetti():
    """Il valore dei progetti, dalla cassaforte: {progetto_id: valore}."""
    return {int(r["progetto_id"]): r.get("valore") for r in sb_tutte("/rest/v1/soldi_progetti?select=progetto_id,valore")}


# I SERVIZI DI POSTA (17/10): da questi domini non si capisce l'azienda. Un lead con la casella
# @aruba.it aveva come «sito» aruba.it: il Google Fit e l'analisi hanno studiato Aruba.
SERVIZI_POSTA = {"gmail.com", "googlemail.com", "hotmail.com", "hotmail.it", "yahoo.com", "yahoo.it",
                 "libero.it", "outlook.com", "outlook.it", "icloud.com", "live.it", "live.com",
                 "pec.it", "tiscali.it", "virgilio.it", "alice.it", "me.com", "aol.com",
                 "aruba.it", "arubapec.it", "pec.aruba.it", "legalmail.it", "tin.it", "inwind.it", "email.it",
                 "fastwebnet.it", "interfree.it", "teletu.it", "libero.com", "protonmail.com", "proton.me"}


def dominio_vero(email):
    """Il dominio dell'azienda dalla mail, o «» se e' un servizio di posta (gmail, alice...)."""
    e = (email or "").strip().lower()
    dom = e.split("@")[-1] if "@" in e else ""
    return dom if dom and dom not in SERVIZI_POSTA else ""


def chiave_nome(nome):
    """Un nome d'azienda come si confronta: minuscolo, senza accenti, spazi e punteggiatura."""
    import unicodedata
    piatto = unicodedata.normalize("NFKD", str(nome or "")).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]", "", piatto.lower())


def sito_vero(p):
    """Il sito dell'azienda, o «» se manca o e' un servizio di posta (mai dedotto da gmail, aruba...)."""
    sito = ((p or {}).get("website") or "").strip()
    dom = re.sub(r"^www\.", "", re.sub(r"^https?://", "", sito.lower()).split("/")[0])
    if dom and dom not in SERVIZI_POSTA:
        return sito
    mail_dom = ((p or {}).get("email") or "").split("@")[-1].lower() if "@" in ((p or {}).get("email") or "") else ""
    if not sito and mail_dom and mail_dom not in SERVIZI_POSTA:
        return "https://" + mail_dom
    return ""


def contattabile(p):
    """MAI UNA BOZZA A CHI NON E' PIU' UN LEAD (25/9, caso Zafferano): in pipeline
    (fuori), cliente, perso, «niente follow-up», rimosso o nervoso. La stessa
    regola sta nel database (trigger proposta_ammessa): qui serve per dirlo
    prima, con parole, e per i test."""
    if not p:
        return False
    # 13/10: chi chiama passava spesso una scheda parziale (le bozze non leggevano no_followup):
    # la regola mancava il campo e diceva «contattabile». Ora i campi mancanti li va a prendere,
    # e chiede al database anche se e' cliente (tabella clienti, v78): la stessa cosa del trigger.
    CAMPI_REGOLA = ("fuori", "stage", "pipeline_stage", "no_followup", "classificazione")
    if p.get("id") and any(k not in p for k in CAMPI_REGOLA):
        try:
            fresco = (sb("GET", f"/rest/v1/prospects?select={','.join(CAMPI_REGOLA)}&id=eq.{p['id']}") or [{}])[0]
            p = {**fresco, **{k: v for k, v in p.items() if k in CAMPI_REGOLA}}
        except Exception:                                        # noqa: BLE001
            return False                         # nel dubbio non si scrive
    if p.get("fuori") or p.get("stage") in ("cliente", "perso") or p.get("pipeline_stage") in ("cliente", "perso"):
        return False
    if p.get("no_followup") or p.get("classificazione") in ("soppresso", "nervoso"):
        return False
    if p.get("id"):
        try:
            if sb("POST", "/rest/v1/rpc/e_cliente", {"p": p["id"]}) is True:
                return False
        except Exception:                                        # noqa: BLE001
            pass
    return True


def scritta_da_dre(az):
    """IL TESTO DI DRE NON SI TOCCA (22/10 notte, Dre: «vorrei poterle MODIFICARE»). Una bozza che Dre ha
    cambiato nell'app porta azione.modificata_da_dre: nessuno script la riscrive (orari rinfrescati, template,
    strade, abitudini), e il postino la passa dal cancello minimo, non dal giudice dello stile."""
    return bool((az or {}).get("modificata_da_dre"))


def lettore_di(p):
    """LA LETTURA DEL LETTORE AI SULLA SUA ULTIMA MAIL (20/10 sera). sync_v2 la salva in
    enriched.lettore con l'ora della risposta letta (risposta_il): vale solo se e' quella della
    sua ultima mail (last_reply_at), se no e' la lettura di un messaggio vecchio. Le liste di
    parole (fonte «liste») non sono il lettore. Torna il dizionario della lettura o {}.
    Accetta anche l'alias `lettore:enriched->lettore` delle select corte."""
    p = p or {}
    l = (p.get("enriched") or {}).get("lettore") if isinstance(p.get("enriched"), dict) else None
    l = l or p.get("lettore") or {}
    if not isinstance(l, dict) or l.get("fonte") != "lettore":
        return {}
    ultima = (p.get("last_reply_at") or "")[:19]
    if ultima and (l.get("risposta_il") or "")[:19] != ultima:
        return {}
    return l


def mail_notificata(voce):
    """La mail del lead per cui e' partita (o e' stata tentata) l'ultima notifica «entrato in
    conversazione»: `ultima_notificata` (dal 21/10), o `dal` per le voci di prima (anche quelle
    «silenziose» del 20/10: il passato vale come notificato). None se la voce non c'e'."""
    if not isinstance(voce, dict):
        return None
    t = voce.get("ultima_notificata") or voce.get("dal")
    return quando(t) if t else None


def tocca_a_dre(voce, mail, nostra, analisi):
    """LA PALLA TORNA A DRE (21/10). Dre: «chiunque risponda dopo l'analisi deve essere riportato,
    questo non puo' sbagliare». La notifica suona ogni volta che la palla torna a lui, non una
    volta per conversazione (il 19 e il 20/10 chi riscriveva dopo la sua risposta restava muto).
    `mail`: l'ultima mail di PERSONA del lead; `nostra`: la nostra ultima mail (Dre da Smartlead,
    un follow-up, l'analisi), None se nessuna; `analisi`: analysis_sent_at; `voce`: lo stato in
    snella_numeri «conversazioni» per quel lead (None se mai visto). Tutti datetime.
    - prima dell'analisi, o senza analisi: no;
    - se la nostra ultima mail e' dopo la sua: la palla e' sua, no;
    - mai notificato: si';
    - la stessa mail, o due sue di fila senza una nostra in mezzo: no (una sola);
    - lui riscrive dopo una nostra mail arrivata dopo la mail gia' notificata: si'."""
    if not analisi or not mail or mail <= analisi:
        return False
    if nostra and nostra >= mail:
        return False
    gia = mail_notificata(voce)
    if gia is None:
        return True
    if mail <= gia:
        return False
    return bool(nostra and nostra > gia)


def fit_di(p):
    """IL GOOGLE FIT, LETTO IN UN MODO SOLO (7/10). Prima c'erano due gerarchie: il
    triage e la prima risposta leggevano il fit nuovo prima del vecchio, bozze.py e
    analisi_auto solo il vecchio, e 14 lead avevano i due in disaccordo. Ora tutti
    passano di qui: il nuovo (google_fit_v2) vince, il vecchio vale solo se il nuovo
    manca. Torna (verdetto, motivo, decisione di Dre o None)."""
    e = (p or {}).get("enriched") or {}
    v2 = e.get("google_fit_v2") or {}
    v1 = e.get("google_fit") or {}
    fonte = v2 if v2.get("verdetto") else v1
    return fonte.get("verdetto"), fonte.get("motivo"), e.get("google_fit_decisione")


def fit_bocciato(p):
    """Il fit ha detto NO e Dre non ha ancora deciso «invia comunque» (6/10: la
    soppressione non la fa il sistema, decide Dre dal triage)."""
    verdetto, _, decisione = fit_di(p)
    return verdetto == "NO" and decisione != "invia"


_colonne = {}


def colonna_c_e(tabella, colonna):
    """Una colonna nuova esiste gia' nel database vero? (7/10) Il codice puo' arrivare in
    produzione prima che la migrazione sia incollata in Supabase: chi chiede una colonna
    che non c'e' riceve un errore e il giro si ferma. Si chiede una volta e si ricorda."""
    k = (tabella, colonna)
    if k not in _colonne:
        try:
            sb("GET", f"/rest/v1/{tabella}?select={colonna}&limit=1")
            _colonne[k] = True
        except Exception:                                     # noqa: BLE001
            _colonne[k] = False
    return _colonne[k]


def giorno_scelto(p):
    """Il giorno del follow-up scelto da Dre (7/10): la colonna prospects.follow_up_il
    (schema_v76). Prima stava in next_action_date, che il sistema usa gia' per la data
    detta dal lead (rinvio, ferie): due significati nello stesso campo."""
    v = (p or {}).get("follow_up_il")
    try:
        return datetime.date.fromisoformat(str(v)[:10]) if v else None
    except ValueError:
        return None


def _a_secco():
    """Siamo in una prova a secco? Si guarda la riga di comando e l'ambiente."""
    return ("--prova" in sys.argv or "--dry-run" in sys.argv
            or os.environ.get("PROVA") == "1" or os.environ.get("POLIZIA_PROVA") == "1"
            or os.environ.get("REVISORE_PROVA") == "1")


def proponi(tipo, titolo, prospect_id=None, perche=None, azione=None, owner=None, ref=None):
    """Una proposta nella stanza. Non scrive niente nella pipeline: solo la domanda.

    Non ne mette due uguali aperte sulla stessa persona: Dre le vedrebbe
    doppie e smetterebbe di leggerle. Con `ref` (schema_v45) la stessa
    domanda non nasce mai due volte, nemmeno dopo che e' stata chiusa: e' il
    modo giusto per le cose che ripassano ogni quarto d'ora (posta, azioni).

    LA PROVA A SECCO NON SCRIVE (28/9). Una prova di bozze.py lanciata con
    --prova ha creato otto proposte vere nella Posta di Dre, perche' chi aveva
    scritto quella parte (io) si era dimenticato il controllo. Il freno sta qui,
    non nei singoli script: se il comando ha --prova o PROVA=1, si stampa quello
    che si sarebbe chiesto e non si scrive niente. Cosi' vale per tutti, anche
    per il prossimo pezzo di codice che qualcuno aggiunge distrattamente.
    """
    if _a_secco():
        print(f"    (prova) chiederei: [{tipo}] {str(titolo)[:70]}")
        return None
    if ref:
        gia = sb("GET", f"/rest/v1/proposte?select=id&ref=eq.{urllib.parse.quote(ref, safe='')}&limit=1")
        if gia:
            return None
    elif prospect_id:
        gia = sb("GET", f"/rest/v1/proposte?select=id&stato=eq.aperta"
                        f"&tipo=eq.{tipo}&prospect_id=eq.{prospect_id}&limit=1")
        if gia:
            return None
    try:
        return sb("POST", "/rest/v1/proposte", {
            "tipo": tipo, "titolo": titolo[:200], "prospect_id": prospect_id,
            "perche": (perche or "")[:300] or None, "azione": azione or {}, "owner": owner,
            "ref": ref,
        }, {"Prefer": "return=representation"})
    except RuntimeError as e:
        # il database rifiuta le bozze a chi non e' piu' un lead (trigger proposta_ammessa, 25/9)
        if "proposta rifiutata" in str(e):
            print(f"  proposta rifiutata dal database (non è più un lead): {titolo[:60]}")
            return None
        if "bozza rifiutata" in str(e):                 # schema_v58: nessuna bozza senza lettura
            print(f"  bozza rifiutata dal database (senza lettura o incoerente): {titolo[:60]}")
            return None
        raise


# ── I GUASTI: una porta sola per entrare, una sola per uscire (notte del 22/10) ──
# Prima un errore preso dentro un giro restava un «print»: la corsa diceva «ok» e il semaforo verde
# (16/10: OpenAI senza crediti, l'analisi diceva «0 pronte su 1» per ore). Ora chi vede un guasto lo
# scrive qui, il semaforo della scheda Clara lo legge e guasti.py lo suona; lo toglie solo un fatto
# (guarito: la prova dopo e' andata bene), mai il tempo che passa. `vale` (minuti) solo per chi lo
# riscrive a ogni giro finche' e' vero (il segnale): se smette di riscriverlo, scade.
GUASTI = "guasti_segnale"          # la chiave in snella_numeri (il nome viene dal primo che la usava)

SERVIZIO_GIU = re.compile(
    r"insufficient_quota|credit balance is too low|no credits remaining|credits? (?:exhausted|finit)|"
    r"invalid_api_key|invalid x-api-key|authentication_error|invalid_grant|"
    r"token (?:has )?(?:been )?(?:expired|revoked)|SUPABASE BLOCCATO|quota exceeded|"
    r"\b40[12]\b[^\n]{0,80}(?:unauthori[sz]ed|invalid api|credit|billing|payment required)", re.I)
FORNITORI = (("openai", "OpenAI"), ("anthropic", "Anthropic"), ("smartlead", "Smartlead"), ("google", "Google"),
             ("gmail", "Google"), ("oauth", "Google"), ("searchapi", "SearchAPI"), ("supabase", "Supabase"))


def servizi_giu(uscita):
    """Pura. Le righe dell'uscita di un giro che dicono «un servizio esterno non ci fa entrare»
    (crediti finiti, chiave o token scaduti): [(fornitore o «», riga)]. Si legge TUTTA l'uscita."""
    out = []
    for riga in (uscita or "").splitlines():
        if SERVIZIO_GIU.search(riga):
            chi = next((n for k, n in FORNITORI if k in riga.lower()), "")
            out.append((chi, " ".join(riga.split())[:200]))
    return out


def _guasti_leggi():
    r = sb("GET", f"/rest/v1/snella_numeri?select=dati&chiave=eq.{GUASTI}") or []
    d = (r[0].get("dati") if r and isinstance(r[0], dict) else None) or {}
    return d if isinstance(d, dict) else {}


def _guasti_scrivi(dati):
    ora = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    sb("POST", "/rest/v1/snella_numeri?on_conflict=chiave", [{"chiave": GUASTI, "dati": dati, "aggiornato_il": ora}],
       {"Prefer": "resolution=merge-duplicates,return=minimal"})


def guasto(chiave, testo, sta_facendo=None, vale=None, fornitore=None):
    """Un guasto visto adesso: resta nel semaforo finche' qualcuno non chiama guarito(chiave)
    (o, con `vale`, finche' viene riscritto entro quei minuti). Con `fornitore` (OpenAI, Anthropic...)
    lo toglie solo la prova dal vivo di quel servizio (guasti.py, fumo.prova). Non alza mai: chi lo
    chiama sta gia' gestendo un errore. In prova a secco stampa e non scrive."""
    print(f"  GUASTO [{chiave}]: {' '.join(str(testo).split())[:200]}")
    if _a_secco():
        return
    try:
        dati = _guasti_leggi()
        ora = datetime.datetime.now(datetime.timezone.utc)
        prima = dati.get(chiave) if isinstance(dati.get(chiave), dict) else {}
        vivo = prima.get("il") and (not prima.get("vale") or ora - quando(prima["il"]) < datetime.timedelta(minutes=prima["vale"]))
        dati[chiave] = {"testo": str(testo)[:300], "il": ora.strftime("%Y-%m-%dT%H:%M:%SZ"),
                        "dal": (prima.get("dal") if vivo else None) or ora.strftime("%Y-%m-%dT%H:%M:%SZ"),
                        "sta_facendo": sta_facendo, "vale": vale, "fornitore": fornitore}
        _guasti_scrivi(dati)
    except Exception as e:                                       # noqa: BLE001
        print(f"  (guasto non scritto nel semaforo: {str(e)[:120]})", file=sys.stderr)


def guarito(chiave):
    """La prova dopo e' andata bene: il guasto `chiave` (o tutti quelli che cominciano con «chiave:»)
    esce dal semaforo. Non alza mai."""
    if _a_secco():
        return
    try:
        dati = _guasti_leggi()
        via = [k for k in dati if k == chiave or k.startswith(chiave + ":")]
        if via:
            for k in via:
                dati.pop(k, None)
            _guasti_scrivi(dati)
    except Exception as e:                                       # noqa: BLE001
        print(f"  (guarito non scritto: {str(e)[:120]})", file=sys.stderr)


def guarda_uscita(operazione, nome, uscita):
    """Dopo ogni giro (direttore e strada veloce): se l'uscita dice che un servizio esterno non ci fa
    entrare, e' un guasto anche se lo script e' finito «ok». Se si sa quale servizio, lo toglie solo
    la prova dal vivo di quel servizio (guasti.py ogni 10 minuti): un giro senza lead da lavorare non
    prova niente, e il «Risolto» sarebbe falso. Se non si sa, lo toglie il primo giro pulito."""
    giu = servizi_giu(uscita)
    chiave = f"servizio:{operazione}"
    if giu:
        chi = next((c for c, _ in giu if c), "")
        guasto(chiave, f"{nome}: {('crediti ' + chi + ' finiti o chiave scaduta') if chi else 'crediti finiti o chiave scaduta'} ({giu[0][1][:120]})",
               sta_facendo="Da solo non riparte: va ricaricato il conto o rinnovata la chiave (dillo ad Achille).",
               fornitore=chi or None)
    elif not _a_secco():
        try:
            v = _guasti_leggi().get(chiave)
            if isinstance(v, dict) and not v.get("fornitore"):
                guarito(chiave)
        except Exception:                                        # noqa: BLE001
            pass
    return giu


def senza_trattini(testo):
    """Il trattino lungo lo toglie il codice, non un secondo giro del modello (29/9).
    L'analisi di Naturalia e' stata bocciata cinque giri di fila, due ore, anche per
    il trattino lungo: un difetto che si corregge con una sostituzione. Un inciso
    fra due trattini diventa una parentesi, un trattino solo diventa due punti."""
    def frase(f):
        if f.count("—") == 2:
            f = re.sub(r"\s*—\s*(.*?)\s*—\s*", r" (\1) ", f, count=1)
        return re.sub(r"\s*—\s*", ": ", f)
    return "".join(frase(f) for f in re.split(r"(?<=[.!?\n])", testo or "")).replace("–", "-")


def di_clara(tipo, testo, prospect_id=None, owner=None, letto=False, diario=False):
    """Una riga nella chat, a nome di Clara. `diario` marca la domanda del diario."""
    import re
    testo = re.sub(r"\s*—\s*", ": ", testo).replace("–", "-").replace("·", ",")   # la stessa di regole.ts
    return sb("POST", "/rest/v1/clara_messaggi", {
        "tipo": tipo, "testo": testo, "prospect_id": prospect_id,
        "owner": owner, "letto": letto, "diario": diario,
    }, {"Prefer": "return=representation"})
