#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""LE STRADE — quando il sistema e' indeciso, 2 o 3 strade e Dre sceglie (21/10/2026 notte).

Dre, 21/10: «quando il sistema e' indeciso, mi da' 2 o 3 strade e io scelgo, e lui procede.
Cosi' lo alleno anche».

COSA FA
Per ogni proposta aperta «Da guardare tu» (la bozza che il sistema non se l'e' sentita di mandare)
e per ogni lead in conversazione dopo l'analisi senza una nostra risposta da piu' di 24 ore, il
modello legge il filo vero (lettura.leggi), la scheda, il fit e il playbook, e propone 2 o 3 STRADE:
ognuna con un'etichetta (3-6 parole, un gesto), una riga di perche', e l'azione che il sistema
esegue se Dre la tocca: `manda` (con la bozza, nello stile di Dre, passata dal cancello e dalla
seconda testa), `ricontatta` (con la data), `chiudi` (negativo o fuori_target), `chiama` (solo se
c'e' un cellulare suo), `niente`. Le strade stanno in proposte.azione.strade; la scheda nell'app le
mostra come carte («Decidi tu») e un tocco di Dre le esegue (src/snella/regole.ts, dati.ts).

UNA GENERAZIONE PER PROPOSTA: le strade non si rifanno a ogni giro. Si rifanno solo se il lead ha
riscritto dopo `strade_il`: allora la domanda vecchia si chiude e ne nasce una nuova (cosi' il postino
non la boccia come «superata dai fatti»). Se intanto gli abbiamo gia' risposto (anche a mano), la
domanda si chiude da sola: non c'e' piu' niente da decidere.

L'ALLENAMENTO. Ogni scelta di Dre resta sulla proposta (azione.scelta: caso del lettore, intento,
le strade proposte, quale ha scelto, quando) e si rispecchia in snella_numeri «scelte_di_dre».
Le ultime 30 entrano nel prompt (qui e in bozze.py) come esempi: la strada che Dre sceglie di
solito su quel caso viene proposta per prima, con la stessa etichetta. Con TRE scelte uguali di
fila sullo stesso caso il sistema non chiede piu': prende quella strada da solo e lo scrive.
(Nessuna tabella nuova: le tabelle si creano incollando SQL in Supabase, e stanotte non c'e'
nessuno a farlo. La proposta e' gia' il posto dove vive la decisione.)

IL TETTO DI SPESA: 3 $ al giorno (snella_numeri «strade», come il lettore), da uso_modelli
scopo «strade». Oltre, non si generano strade nuove; nella scheda restano i pulsanti di oggi.

USO
  python3 scripts/strade.py --prova          mostra le strade, non scrive
  python3 scripts/strade.py                  scrive le strade nelle proposte
  python3 scripts/strade.py --id 3453        solo quella proposta
  python3 scripts/strade.py --quanti 3
  python3 scripts/strade.py --tetto 5        alza il tetto di spesa per questo giro (una tantum)
"""
import datetime
import json
import os
import re
import sys
import time
import unicodedata
import urllib.parse
import urllib.request
import zoneinfo

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from stanza import sb, sb_tutte, proponi, quando, senza_trattini, contattabile, lettore_di, fit_di, _a_secco  # noqa: E402

PROVA = "--prova" in sys.argv
QUANTI = int(sys.argv[sys.argv.index("--quanti") + 1]) if "--quanti" in sys.argv else 6
SOLO_ID = int(sys.argv[sys.argv.index("--id") + 1]) if "--id" in sys.argv else None
ROMA = zoneinfo.ZoneInfo("Europe/Rome")
TETTO_GIORNO = float(sys.argv[sys.argv.index("--tetto") + 1]) if "--tetto" in sys.argv else 3.0   # dollari al giorno, come il lettore (snella_numeri «strade»); --tetto 5 per una sera di recupero
MAX_STRADE = 3
MIN_STRADE = 2
QUANTE_SCELTE = 30                  # le ultime scelte di Dre che entrano nel prompt
TRE = 3                             # tre scelte uguali di fila sullo stesso caso: il sistema non chiede piu'
ORE_CONVERSAZIONE = 24              # in conversazione senza una nostra risposta da piu' di un giorno
AZIONI = ("manda", "ricontatta", "chiudi", "chiama", "niente")
CLASSI_CHIUSURA = ("negativo", "fuori_target")
TITOLO = "Decidi tu"
# a chi non si propone niente: non e' una persona (autorisposte, caselle di servizio, rimbalzi)
NON_PERSONA = re.compile(r"autorispost|autorespon|auto-?reply|autoresponder|bounce|\bNDR\b|\bDSN\b|mancata consegna|"
                         r"casella di servizio|antispam|helpdesk|ticket|indirizzo non valido|deliverability", re.I)
FERMI = ("negativo", "soppresso", "nervoso", "fuori_target", "ooo")
INTOCCABILI = ("cliente", "perso", "call_fissata", "rinviato")


# ── 1. le regole pure (le prova test_invarianti.py) ────────────────────────────

def normalizza(etichetta):
    """Un'etichetta come si confronta: minuscola, senza accenti ne' punteggiatura."""
    piatto = unicodedata.normalize("NFKD", str(etichetta or "")).encode("ascii", "ignore").decode()
    return " ".join(re.sub(r"[^a-z0-9 ]", " ", piatto.lower()).split())


def chiave(strada):
    return (strada.get("azione"), normalizza(strada.get("etichetta")))


def valida(strade, cellulare, oggi):
    """Le strade che reggono, al massimo 3, e quelle scartate col motivo. Le regole che non si
    discutono: `manda` ha sempre una bozza; `chiama` solo con un cellulare; `ricontatta` ha una
    data vera, futura; `chiudi` una classe fra negativo e fuori_target; etichetta da 2 a 7 parole
    (il modello ne chiede 3-6, qui si lascia un filo di gioco); due strade uguali sono una."""
    buone, scartate, viste = [], [], set()
    for s in strade or []:
        s = dict(s or {})
        az = s.get("azione")
        et = " ".join(str(s.get("etichetta") or "").split()).strip(" .")
        s["etichetta"] = et
        s["perche"] = " ".join(str(s.get("perche") or "").split())
        n_parole = len(et.split())
        if az not in AZIONI:
            scartate.append((s, f"azione sconosciuta: {az}")); continue
        if not (2 <= n_parole <= 7):
            scartate.append((s, f"etichetta di {n_parole} parole (ne servono da 3 a 6)")); continue
        if not s["perche"]:
            scartate.append((s, "senza il perche'")); continue
        if az == "manda":
            if not str(s.get("bozza") or "").strip() or len(str(s.get("bozza")).strip()) < 40:
                scartate.append((s, "manda senza una bozza")); continue
            s["bozza"] = str(s["bozza"]).strip()
        else:
            s["bozza"] = None
        if az == "chiama" and not cellulare:
            scartate.append((s, "chiama senza un cellulare suo")); continue
        if az == "ricontatta":
            d = str(s.get("data") or "")[:10]
            try:
                g = datetime.date.fromisoformat(d)
            except ValueError:
                scartate.append((s, f"ricontatta senza una data vera ({s.get('data')})")); continue
            if g <= oggi:
                scartate.append((s, f"ricontatta a una data gia' passata ({d})")); continue
            s["data"] = d
        else:
            s["data"] = None
        if az == "chiudi":
            if s.get("classe") not in CLASSI_CHIUSURA:
                scartate.append((s, f"chiudi con una classe che non esiste ({s.get('classe')})")); continue
        else:
            s["classe"] = None
        k = chiave(s)
        if k in viste:
            scartate.append((s, "doppia")); continue
        viste.add(k)
        buone.append({k2: s.get(k2) for k2 in ("etichetta", "perche", "azione", "bozza", "data", "classe", "intento")})
    return buone[:MAX_STRADE], scartate + [(s, "oltre la terza") for s in buone[MAX_STRADE:]]


def scelte_sul_caso(scelte, caso):
    """Le scelte di Dre su quel caso del lettore, dalla piu' recente."""
    if not caso:
        return []
    return [s for s in scelte or [] if (s.get("caso") or "") == caso]


def abitudine(scelte, caso):
    """TRE SCELTE UGUALI DI FILA sullo stesso caso = il sistema non chiede piu' (Dre, 21/10).
    Torna {azione, etichetta} o None. Senza caso non c'e' abitudine: mai in automatico alla cieca."""
    ultime = scelte_sul_caso(scelte, caso)[:TRE]
    if len(ultime) < TRE:
        return None
    chiavi = {chiave(s) for s in ultime}
    if len(chiavi) != 1:
        return None
    return {"azione": ultime[0].get("azione"), "etichetta": ultime[0].get("etichetta")}


def ordina(strade, scelte, caso):
    """La strada che Dre sceglie di solito su questo caso va prima: la stessa etichetta se c'e',
    se no la stessa azione. Il resto nell'ordine del modello."""
    sul_caso = scelte_sul_caso(scelte, caso)
    if not sul_caso or not strade:
        return list(strade)
    conta = {}
    for s in sul_caso:
        conta[chiave(s)] = conta.get(chiave(s), 0) + 1
    solita = max(conta.items(), key=lambda kv: kv[1])[0]
    def peso(s):
        k = chiave(s)
        if k == solita:
            return 0
        if k[0] == solita[0]:
            return 1
        return 2
    return sorted(strade, key=peso)             # stabile: a parita' resta l'ordine del modello


def nome_caso(caso):
    try:
        import lettore
        return (lettore.CASI.get(caso) or {}).get("nome") or ""
    except Exception:                                            # noqa: BLE001
        return ""


def esempi_per_prompt(scelte, quante=QUANTE_SCELTE):
    """Le scelte di Dre come esempi nel prompt (qui e in bozze.py). «» se non ce ne sono."""
    righe = []
    for s in (scelte or [])[:quante]:
        caso = s.get("caso") or "senza caso"
        nome = nome_caso(s.get("caso"))
        spiraglio = " con spiraglio" if s.get("porta_aperta") else ""
        altre = [e for e in (s.get("strade") or []) if normalizza(e) != normalizza(s.get("etichetta"))]
        righe.append(f"- In un caso {caso}{f' ({nome})' if nome else ''}{spiraglio} Dre ha scelto: «{s.get('etichetta')}» ({s.get('azione')})"
                     + (f", scartando: {' / '.join(altre)}" if altre else "")
                     + (" [scelta automatica: tre volte uguale]" if s.get("automatica") else ""))
    if not righe:
        return ""
    return ("\n\nLE SCELTE DI DRE (le ultime, dalla piu' recente). Quando il caso e' lo stesso o somiglia, la strada "
            "che sceglie di solito va PRIMA, con la stessa etichetta parola per parola; se tre volte di fila ha scelto "
            "la stessa cosa, e' quella e basta.\n" + "\n".join(righe))


def record_scelta(strade, scelta, caso, intento, ora, porta_aperta=False, automatica=False):
    """La forma di una scelta (la stessa che scrive l'app in azione.scelta, src/snella/regole.ts)."""
    return {"etichetta": scelta.get("etichetta"), "azione": scelta.get("azione"), "caso": caso, "intento": intento,
            "strade": [s.get("etichetta") for s in strade], "il": ora.isoformat(), "porta_aperta": bool(porta_aperta),
            **({"automatica": True} if automatica else {})}


def e_persona(pr, p):
    """La proposta riguarda una persona vera? Niente strade per autorisposte, caselle di servizio,
    rimbalzi: li' non c'e' nessuno con cui decidere."""
    az = (pr or {}).get("azione") or {}
    let = az.get("lettura") or {}
    if let.get("autorisposta") or let.get("casella_di_servizio"):
        return False
    if NON_PERSONA.search((pr or {}).get("perche") or ""):
        return False
    if (p or {}).get("classificazione") == "ooo":
        return False
    return True


def filo_cambiato(pr, p):
    """Le strade ci sono gia': si rifanno solo se il lead ha riscritto dopo."""
    az = (pr or {}).get("azione") or {}
    il = az.get("strade_il") or ""
    if not az.get("strade") or not il:
        return True
    ultima = (p or {}).get("last_reply_at") or ""
    return bool(ultima) and quando(ultima) > quando(il)


# ── 2. le scelte di Dre (lettura e specchio) ───────────────────────────────────

def scelte_di_dre(quante=QUANTE_SCELTE):
    """Le ultime scelte, dalla piu' recente: stanno sulle proposte (azione.scelta)."""
    try:
        righe = sb("GET", "/rest/v1/proposte?select=id,prospect_id,at,scelta:azione->scelta,scelta_automatica:azione->scelta_automatica"
                          "&or=(azione->scelta.not.is.null,azione->scelta_automatica.not.is.null)"
                          f"&order=at.desc&limit={quante * 3}") or []
    except Exception as e:                                       # noqa: BLE001
        print(f"  (le scelte di Dre non si leggono: {str(e)[:80]})")
        return []
    out = []
    for r in righe:
        s = r.get("scelta") or r.get("scelta_automatica")
        if isinstance(s, dict) and s.get("etichetta") and s.get("azione"):
            out.append({**s, "proposta": r["id"], "prospect_id": r.get("prospect_id"), "automatica": bool(r.get("scelta_automatica")) and not r.get("scelta")})
    out.sort(key=lambda s: s.get("il") or "", reverse=True)
    # le scelte di Dre insegnano; quelle automatiche no (si rafforzerebbero da sole)
    return [s for s in out if not s.get("automatica")][:quante]


def specchio_scelte(scelte):
    """snella_numeri «scelte_di_dre»: la lista leggibile, per chi vuole vedere cosa ha imparato."""
    if _a_secco():
        return
    sb("POST", "/rest/v1/snella_numeri?on_conflict=chiave",
       [{"chiave": "scelte_di_dre", "dati": {"scelte": scelte, "quante": len(scelte)},
         "aggiornato_il": datetime.datetime.now(datetime.timezone.utc).isoformat()}],
       {"Prefer": "resolution=merge-duplicates,return=minimal"})


# ── 3. il modello ──────────────────────────────────────────────────────────────

_T = {"type": "string"}
SCHEMA_STRADE = {
    "type": "object", "additionalProperties": False, "required": ["lettura", "strade"],
    "properties": {
        "lettura": {"type": "string", "description": "una riga: cosa vuole davvero questa persona"},
        "strade": {"type": "array", "description": "da 2 a 3 strade", "items": {
            "type": "object", "additionalProperties": False,
            "required": ["etichetta", "perche", "azione", "intento", "bozza", "data", "classe"],
            "properties": {
                "etichetta": _T, "perche": _T,
                "azione": {"type": "string", "enum": list(AZIONI)},
                "intento": {"type": "string", "description": "per manda, il codice INT del playbook che la bozza segue; altrimenti vuoto"},
                "bozza": {"type": "string", "description": "il testo completo della mail, solo per manda; altrimenti vuoto"},
                "data": {"type": "string", "description": "AAAA-MM-GG, solo per ricontatta; altrimenti vuoto"},
                "classe": {"type": "string", "enum": ["negativo", "fuori_target", ""], "description": "solo per chiudi"},
            }}},
    },
}

ISTRUZIONE = """IL GIOCO DELLE STRADE (Dre, 21/10: «quando il sistema e' indeciso, mi da' 2 o 3 strade e io
scelgo, e lui procede. Cosi' lo alleno anche»).

Il sistema non sapeva cosa fare con questa persona: la risposta che aveva preparato e' ferma. Il tuo
lavoro: proporre a Dre 2 o 3 STRADE diverse davvero (non tre varianti della stessa mail), ognuna un
gesto che si capisce in un secondo sul telefono. Dre ne tocca una e il sistema la esegue.

LE AZIONI (una per strada):
- manda: scriviamo noi, adesso. Porta la bozza completa.
- ricontatta: oggi niente, lo riprendiamo a una data. Porta la data (AAAA-MM-GG), coerente con quello che
  ha detto lui («a gennaio» = un giorno feriale di gennaio; «dopo le ferie» = la settimana dopo; se non dice
  niente, fra 30 e 45 giorni). E' la strada giusta per chi dice «piu' avanti», «non ora», «vi terremo presenti».
- chiudi: finita qui. Porta la classe: «negativo» (non gli interessa) o «fuori_target» (non e' un cliente per
  noi: agenzia, portale, settore o taglia sbagliati).
- chiama: lo chiama Dre. SOLO se sotto c'e' scritto CELLULARE: si'. Se no, non proporla mai.
- niente: nessun gesto adesso: ha detto che si fa vivo lui, o ha gia' tutto quello che serve.

LE REGOLE:
1. etichetta: da 3 a 6 parole, un gesto all'imperativo o un verdetto. Esempi buoni: «Chiedi il contatto del
   collega», «Rimanda a gennaio», «Chiudi: non interessato», «Manda il materiale senza call», «Rispondi
   all'obiezione», «Lascia che si faccia vivo lui», «Chiudi: fuori target». Mai generica («Rispondi», «Procedi»).
   Per ricontatta l'etichetta dice il momento come lo direbbe una persona («Rimanda a gennaio», «Riprendi dopo
   le feste», «Risentilo a fine novembre»), non un numero di giorni. UN gesto solo per etichetta: mai «o»
   («Chiudi: fuori target o no» non vale), i due punti solo in «Chiudi: …», niente parole di casa nostra
   («gigante buono», «dono», «archivia», «classifica»).
2. perche: UNA riga in italiano semplice, detta a Dre («gli dai ragione e…», «lo riprendi quando…»): cosa succede
   se la sceglie e perche' ha senso. Niente codici interni (INT-xx, Cxx), niente gergo, niente «il sistema».
3. Le strade devono essere alternative vere, con esiti diversi. Se c'e' una sola strada sensata, affiancala
   a «ricontatta» o a «niente»: non inventare una terza strada stupida. Mai piu' di tre.
4. La bozza (solo per manda), nello stile di Dre: «lei», corta (5-9 righe), genuina, zero vendita, zero
   fuffa, nessuna firma, mai il trattino lungo, mai note interne fra parentesi quadre, mai un indirizzo
   email al posto del nome. Risponde a quello che ha scritto davvero lui, nell'ordine, senza ripetere cose
   gia' scritte. Un prossimo punto di contatto chiaro (il calendario {{CALENDARIO}}, oppure «le scrivo io
   il …»), tranne quando la persona ha chiesto il materiale senza call o di farsi viva lei: allora si
   chiude con «resto a disposizione». Mai un prezzo. Mai numeri sulla zona. Mai una data a chi ha detto
   no. Al messaggero (chi ci gira a un collega) non si propone la call: si chiede il contatto o di
   inoltrare, e si chiude con «appena ho il contatto scrivo io a lui/lei», mai con «a disposizione».
   A chi ha detto no NON si regala l'analisi (Dre, 5/10: costa e non torna niente): una strada manda a
   un no esiste solo se c'e' una cosa precisa a cui rispondere (un'obiezione, una domanda, un contatto da
   chiedere). Se ha detto un no cortese e non c'e' niente da aggiungere, NON forzare una strada manda.
5. intento: per manda, il codice INT del playbook che la bozza segue (INT-23 se manda il materiale senza
   call); vuoto per le altre azioni.
6. lettura: una riga su cosa vuole davvero questa persona, in parole normali.
7. Se qui sotto ci sono LE SCELTE DI DRE su casi uguali o simili, la strada che sceglie di solito va PRIMA,
   con la stessa etichetta parola per parola: cosi' impara una lingua sola."""


def _sistema():
    import cervello
    return (cervello.ruolo("preparatore") + cervello.manuale("testa", "outbound", "template")
            + cervello.istruzione("contesto") + cervello.istruzione("chat") + cervello.istruzione("bozze")
            + "\n\n" + ISTRUZIONE)


def chiedi_modello(sistema, testo, registra="strade"):
    """UNA chiamata: istruzioni in cache (sono le stesse per ogni proposta), uscita a schema fisso.
    Torna (dict, costo). Scrive la chiamata in uso_modelli (scopo «strade»), anche in prova."""
    import lettore
    chiave_api = lettore._env("ANTHROPIC_API_KEY")
    if not chiave_api:
        raise lettore.Guasto("manca la chiave Anthropic")
    modello = lettore.modello_scelto()
    corpo = {"model": modello, "max_tokens": 6000,
             "system": [{"type": "text", "text": sistema, "cache_control": {"type": "ephemeral"}}],
             "messages": [{"role": "user", "content": testo}],
             "output_config": {"effort": "medium", "format": {"type": "json_schema", "schema": SCHEMA_STRADE}}}
    req = urllib.request.Request("https://api.anthropic.com/v1/messages", data=json.dumps(corpo).encode("utf-8"), method="POST")
    req.add_header("x-api-key", chiave_api)
    req.add_header("anthropic-version", "2023-06-01")
    req.add_header("content-type", "application/json")
    d = None
    for tentativo in range(3):
        try:
            with urllib.request.urlopen(req, timeout=240) as r:
                d = json.loads(r.read())
            break
        except urllib.error.HTTPError as e:
            msg = e.read().decode("utf-8", "replace")[:200]
            if e.code in (429, 500, 502, 503, 529) and tentativo < 2:
                time.sleep(3 * (tentativo + 1)); continue
            raise lettore.Guasto(f"Anthropic {e.code}: {msg}")
        except (urllib.error.URLError, TimeoutError, OSError) as e:
            if tentativo < 2:
                time.sleep(3 * (tentativo + 1)); continue
            raise lettore.Guasto(f"Anthropic non risponde: {e}")
    u = d.get("usage") or {}
    nuovi, letti, scritti = int(u.get("input_tokens") or 0), int(u.get("cache_read_input_tokens") or 0), int(u.get("cache_creation_input_tokens") or 0)
    fuori = int(u.get("output_tokens") or 0)
    spesa = lettore.costo(modello, nuovi, letti, scritti, fuori)
    lettore._registra(registra, modello, nuovi, letti, scritti, fuori)
    return lettore.uscita_del_messaggio(d, SCHEMA_STRADE), spesa


def spesa_di_oggi():
    import lettore
    return lettore.spesa_di_oggi("strade")


# ── 4. il materiale per una proposta ───────────────────────────────────────────

def fatti_di(p, letti, righe):
    """La scheda, come la vede il modello: chi e', il fit, il filo (il filo vero, non il CRM)."""
    verdetto, motivo, decisione = fit_di(p)
    f = {"nome": p.get("name") or "", "azienda": p.get("company") or "", "settore": p.get("sector"), "citta": p.get("city"),
         "classificazione": p.get("classificazione"), "stage": p.get("stage"),
         "analisi_inviata_il": (p.get("analysis_sent_at") or "")[:10] or "mai",
         "analisi_pronta_in_allegato": bool(p.get("analysis_pdf")),
         "google_fit": {"verdetto": verdetto, "motivo": (motivo or "")[:200], "decisione_di_dre": decisione} if verdetto else None,
         "ultima_sua_mail": (p.get("last_reply_at") or "")[:10]}
    seq = [f"{str(x.get('at'))[:10]} {'NOI' if x.get('kind') in ('email_out', 'followup', 'analisi') else 'LORO' if x.get('kind') == 'email_in' else str(x.get('kind')).upper()}: "
           + " ".join((x.get("body") or "").split())[:400] for x in (righe or [])[-12:]]
    f["sequenza"] = seq
    f["quante_ne_abbiamo_mandate"] = sum(1 for x in righe or [] if x.get("kind") in ("email_out", "followup", "analisi"))
    f["quante_ne_ha_scritte"] = sum(1 for x in righe or [] if x.get("kind") == "email_in")
    if letti:
        f["fatti_verificati_dal_codice"] = {k: letti.get(k) for k in ("scritto_dopo_di_lei", "analisi_ricevuta", "analisi_gia_letta", "detto_no", "autorisposta", "girato_a")}
        if letti.get("ultima_nostra"):
            f["ultima_mail_nostra"] = f"{letti['ultima_nostra_il']}: {letti['ultima_nostra'][:500]}"
    return f


def caso_di(p, pr):
    """Il caso del lettore (Cxx) e la sua lettura: dalla scheda (enriched.lettore, se e' della sua
    ultima mail), se no dal triage salvato nella proposta."""
    l = lettore_di(p)
    if not l:
        l = ((pr or {}).get("azione") or {}).get("lettore_triage") or {}
    return (l.get("caso") or ""), l


def testo_per(p, pr, letti, righe, scelte, cellulare, ora):
    import bozze
    caso, lett = caso_di(p, pr)
    az = (pr or {}).get("azione") or {}
    cosa_aveva = ""
    if pr:
        cosa_aveva = (f"\n\nCOSA AVEVA PREPARATO IL SISTEMA E PERCHE' SI E' FERMATO:\ntitolo: {pr.get('titolo')}\nperche': {pr.get('perche') or ''}\n"
                      + (f"la bozza ferma:\n{str(az.get('bozza'))[:900]}" if az.get("bozza") else "nessuna bozza"))
    lettore_txt = (f"caso {caso} «{nome_caso(caso)}», classe {lett.get('classe')}, porta aperta {'si' if lett.get('porta_aperta') else 'no'}, "
                   f"caldo {'si' if lett.get('caldo') else 'no'}, motivo: {lett.get('motivo') or ''}") if lett else "non l'ha letta"
    ab = abitudine(scelte, caso)
    ab_txt = (f"\n\nABITUDINE DI DRE su questo caso ({caso}): tre volte di fila ha scelto «{ab['etichetta']}» ({ab['azione']}). "
              "Proponi SOLO quella strada, fatta bene (con la bozza se e' manda): il sistema la prende da solo.") if ab else ""
    return (esempi_per_prompt(scelte) + ab_txt
            + f"\n\nOGGI: {ora.astimezone(ROMA):%A %d %B %Y}. CELLULARE: {'si' if cellulare else 'no'}. "
            f"SLOT PROPONIBILE (se serve una data per la call): {bozze.proposta_giorno_ora()}. {{{{CALENDARIO}}}} = {bozze.CALENDARIO}"
            f"\n\nLA SCHEDA:\n{json.dumps(fatti_di(p, letti, righe), ensure_ascii=False)}"
            f"\n\nIL LETTORE AI HA LETTO LA SUA ULTIMA MAIL COSI': {lettore_txt}"
            + cosa_aveva
            + f"\n\nL'ULTIMO MESSAGGIO CHE HA SCRITTO ({letti.get('ultima_loro_il')}):\n{(letti.get('ultima_loro') or '')[:2500]}")


def genera(p, pr, letti, righe, scelte, cellulare, ora, sistema=None):
    """Le strade per una proposta (o per un lead in conversazione, pr=None). Torna
    {strade, lettura, caso, intento, abitudine, scartate, costo} o None con il motivo stampato."""
    import bozze
    import lettura
    sistema = sistema or _sistema()
    caso, lett = caso_di(p, pr)
    ab = abitudine(scelte, caso)
    oggi = ora.astimezone(ROMA).date()
    testo = testo_per(p, pr, letti, righe, scelte, cellulare, ora)
    costo = 0.0
    scartate_tutte = []
    buone = []
    letture = ""
    for giro in range(2):
        if giro:
            testo += "\n\nLE STRADE PRECEDENTI NON REGGEVANO: " + "; ".join(f"«{s.get('etichetta')}»: {m}" for s, m in scartate_tutte[-6:]) + ". Rifalle correggendo solo quello."
        risposta, c = chiedi_modello(sistema, testo)
        costo += c
        letture = (risposta.get("lettura") or "").strip()
        buone, scartate = valida(risposta.get("strade"), cellulare, oggi)
        scartate_tutte += scartate
        tenute = []
        for s in buone:
            if s["azione"] != "manda":
                tenute.append(s); continue
            b = senza_trattini(s["bozza"].replace("{{CALENDARIO}}", bozze.CALENDARIO).replace("{{ CALENDARIO }}", bozze.CALENDARIO))
            errori = bozze.cancello(b, senza_analisi=bozze.analisi_impossibile(p), detto_no=bool(letti.get("detto_no")), intento=(s.get("intento") or None))
            if errori:
                scartate_tutte.append((s, "cancello: " + "; ".join(errori)[:160])); continue
            verdetto, motivo = lettura.coerenza(letti, b, None)
            if verdetto != "COERENTE":
                scartate_tutte.append((s, f"seconda testa: {motivo[:160]}")); continue
            tenute.append({**s, "bozza": b})
        buone = tenute
        if ab:
            stessa = [s for s in buone if s["azione"] == ab["azione"]]
            if stessa:
                buone = stessa[:1]
                break
            # la strada abituale non ha retto (cancello o seconda testa): si torna a chiedere a Dre
            ab = None
            testo += "\n\nL'ABITUDINE NON SI APPLICA stavolta: proponi 2 o 3 strade come al solito."
            continue
        if len(buone) >= MIN_STRADE:
            break
    if not buone or (len(buone) < MIN_STRADE and not ab):
        print(f"      niente strade che reggono (ne restano {len(buone)}): " + "; ".join(f"{s.get('etichetta')}: {m[:80]}" for s, m in scartate_tutte[-4:]))
        return None
    return {"strade": ordina(buone, scelte, caso), "lettura": letture, "caso": caso, "intento": ((pr or {}).get("azione") or {}).get("intento"),
            "abitudine": ab, "scartate": [(s.get("etichetta"), m) for s, m in scartate_tutte], "costo": costo,
            "porta_aperta": bool(lett.get("porta_aperta")) if lett else False}


# ── 5. le scritture ────────────────────────────────────────────────────────────

def _azione_con_strade(az, esito, ora):
    return {**(az or {}), "strade": esito["strade"], "strade_il": ora.isoformat(), "strade_caso": esito["caso"],
            "strade_lettura": esito["lettura"][:300], "strade_scartate": [f"{e}: {m[:120]}" for e, m in esito["scartate"]][:6]}


def _scheda(p, patch):
    """Una scrittura sulla scheda del lead; se il database la protegge (lock umano) lo si dice e si va avanti."""
    try:
        sb("PATCH", f"/rest/v1/prospects?id=eq.{p['id']}", patch, {"Prefer": "return=minimal"})
    except RuntimeError as e:
        print(f"      la scheda non si tocca: {str(e)[:120]}")


def applica_abitudine(pr, p, esito, ora):
    """Tre scelte uguali sullo stesso caso: il sistema prende quella strada da solo e lo scrive.
    `manda`: la proposta prende la bozza e passa approvata (il postino la manda, con analisi e
    presentazione come alla prima risposta). Le altre azioni sono le stesse scritture dell'app."""
    s = esito["strade"][0]
    ab = esito["abitudine"]
    perche = f"Presa da sola: tre volte di fila su questo caso ({esito['caso']}) Dre ha scelto «{ab['etichetta']}»."
    s = {**s, "perche": (s.get("perche") or "") + " " + perche}
    scelta = record_scelta(esito["strade"], s, esito["caso"], esito.get("intento"), ora, esito.get("porta_aperta"), automatica=True)
    az = {**_azione_con_strade(pr.get("azione"), {**esito, "strade": [s]}, ora), "scelta_automatica": scelta}
    nota = f"Dal sistema: strada presa da sola: {s['etichetta']} (tre scelte uguali di Dre sul caso {esito['caso']})"
    if s["azione"] == "manda":
        for k in ("dopo_invio", "testo_dal_codice", "bozza_modello", "giorno_proposto", "ritocco", "bozza_originale"):
            az.pop(k, None)
        az.update({"bozza": s["bozza"], "intento": s.get("intento") or az.get("intento"), "approvata_da": f"il sistema (abitudine di Dre: tre volte «{ab['etichetta']}» sul caso {esito['caso']})",
                   "approvata_il": ora.isoformat()})
        if p.get("analysis_pdf") and not p.get("analysis_sent_at"):
            az["allega"] = True
        sb("PATCH", f"/rest/v1/proposte?id=eq.{pr['id']}&stato=eq.aperta", {"stato": "approvata", "azione": az, "perche": perche[:300]})
    elif s["azione"] == "ricontatta":
        _scheda(p, {"next_action_date": s["data"], "classificazione": "rinvio", "coda": None})
        sb("POST", "/rest/v1/snella_lead?on_conflict=prospect_id", [{"prospect_id": p["id"], "stato": "Da ricontattare", "prossima_il": s["data"], "prossima_mossa": s["etichetta"]}],
           {"Prefer": "resolution=merge-duplicates,return=minimal"})
        sb("PATCH", f"/rest/v1/proposte?id=eq.{pr['id']}&stato=eq.aperta", {"stato": "no", "risposta": f"rinvio preso dal sistema (abitudine di Dre): {s['data']}", "risposta_il": ora.isoformat(), "azione": az})
    elif s["azione"] == "chiudi":
        _scheda(p, {"classificazione": s["classe"], "no_followup": True, "coda": None})
        sb("POST", "/rest/v1/snella_lead?on_conflict=prospect_id", [{"prospect_id": p["id"], "stato": "Non interessato"}], {"Prefer": "resolution=merge-duplicates,return=minimal"})
        sb("PATCH", f"/rest/v1/proposte?id=eq.{pr['id']}&stato=eq.aperta", {"stato": "no", "risposta": "chiusa dal sistema (abitudine di Dre)", "risposta_il": ora.isoformat(), "azione": az})
    elif s["azione"] == "chiama":
        oggi = ora.astimezone(ROMA).date().isoformat()
        sb("POST", "/rest/v1/snella_lead?on_conflict=prospect_id", [{"prospect_id": p["id"], "stato": "Da chiamare", "chiamata": "richiamare", "chiamata_il": ora.isoformat(), "richiamare_il": oggi}],
           {"Prefer": "resolution=merge-duplicates,return=minimal"})
        sb("PATCH", f"/rest/v1/proposte?id=eq.{pr['id']}&stato=eq.aperta", {"stato": "no", "risposta": "lo chiama Dre (abitudine)", "risposta_il": ora.isoformat(), "azione": az})
    else:
        sb("PATCH", f"/rest/v1/proposte?id=eq.{pr['id']}&stato=eq.aperta", {"stato": "no", "risposta": "nessun gesto (abitudine di Dre)", "risposta_il": ora.isoformat(), "azione": az})
    sb("POST", "/rest/v1/snella_note", {"prospect_id": p["id"], "testo": nota, "tipo": "nota", "autore_nome": "Clara"}, {"Prefer": "return=minimal"})


def salva(pr, p, esito, ora, nuova_domanda=None):
    """Le strade sulla proposta. Se la proposta va rifatta (il lead ha riscritto), la vecchia si chiude
    e ne nasce una nuova con la data di adesso. Torna l'id della proposta con le strade."""
    if esito.get("abitudine") and len(esito["strade"]) == 1 and pr and not nuova_domanda:
        applica_abitudine(pr, p, esito, ora)
        return pr["id"]
    if pr and not nuova_domanda:
        sb("PATCH", f"/rest/v1/proposte?id=eq.{pr['id']}&stato=eq.aperta", {"azione": _azione_con_strade(pr.get("azione"), esito, ora)})
        return pr["id"]
    titolo, perche, azione = nuova_domanda
    if pr:
        # prima si chiude la vecchia: proponi non ne mette due aperte sulla stessa persona
        sb("PATCH", f"/rest/v1/proposte?id=eq.{pr['id']}&stato=eq.aperta",
           {"stato": "no", "risposta": "superata: ha riscritto dopo, le strade sono sulla domanda nuova", "risposta_il": ora.isoformat()})
    pid = proponi("umano", titolo, prospect_id=p["id"], perche=perche, azione=_azione_con_strade(azione, esito, ora))
    if isinstance(pid, list):
        pid = pid[0].get("id") if pid else None
    return pid


def chiudi_superata(pr, motivo, ora):
    print(f"      si chiude: {motivo}")
    if PROVA:
        return
    sb("PATCH", f"/rest/v1/proposte?id=eq.{pr['id']}&stato=eq.aperta", {"stato": "no", "risposta": f"superata: {motivo}"[:300], "risposta_il": ora.isoformat()})


# ── 6. i candidati ─────────────────────────────────────────────────────────────

CAMPI = ("id,name,company,email,email_alt,phone,classificazione,stage,analysis_sent,analysis_sent_at,analysis_pdf,"
         "last_reply_at,sector,city,enriched,campaign_id,lead_id,coda,next_action_date,campaign,fuori,no_followup,awaiting_us,pipeline_stage")


def proposte_da_guardare():
    q = "/rest/v1/proposte?select=id,at,titolo,perche,prospect_id,tipo,azione&stato=eq.aperta&prospect_id=not.is.null"
    if SOLO_ID:
        return sb("GET", f"{q}&id=eq.{SOLO_ID}") or []
    return sb("GET", f"{q}&or=(titolo.ilike.Da%20guardare%20tu*,titolo.ilike.{urllib.parse.quote(TITOLO)}*)&order=at.desc&limit=200") or []


def conversazioni_ferme(ora, con_proposta):
    """Chi ha risposto di persona dopo l'analisi, aspetta una nostra risposta da piu' di 24 ore,
    e non ha nessuna domanda aperta: la stessa funzione, con la domanda che nasce qui."""
    import bozze
    soglia = (ora - datetime.timedelta(hours=ORE_CONVERSAZIONE)).isoformat()
    ps = sb("GET", f"/rest/v1/prospects?select={CAMPI}&awaiting_us=eq.true&fuori=eq.false&no_followup=eq.false"
                   f"&analysis_sent_at=not.is.null&last_reply_at=lt.{urllib.parse.quote(soglia)}"
                   f"&classificazione=not.in.({','.join(FERMI)})&order=last_reply_at.desc&limit=200") or []
    ps = [p for p in ps if p["id"] not in con_proposta and p.get("stage") not in INTOCCABILI
          and "usa" not in (p.get("campaign") or "").lower() and (p.get("last_reply_at") or "") > (p.get("analysis_sent_at") or "")]
    risposte = bozze.risposte_dopo_analisi(ps)
    return [p for p in ps if bozze.in_conversazione(p, risposte.get(p["id"]))]


# ── 7. il giro ─────────────────────────────────────────────────────────────────

def conto(speso, generate, aperte_con_strade, scelte, note=None):
    if _a_secco():
        return
    r = sb("GET", "/rest/v1/snella_numeri?select=dati&chiave=eq.strade") or []
    st = dict((r[0].get("dati") if r else None) or {})
    st.update({"tetto_giorno": TETTO_GIORNO, "speso_oggi": round(speso, 4) if speso is not None else None,
               "generate_nel_giro": generate, "aperte_con_strade": aperte_con_strade, "scelte_di_dre": len(scelte),
               "ultimo_giro": datetime.datetime.now(datetime.timezone.utc).isoformat()})
    if note:
        st["avviso"] = note
    else:
        st.pop("avviso", None)
    sb("POST", "/rest/v1/snella_numeri?on_conflict=chiave",
       [{"chiave": "strade", "dati": st, "aggiornato_il": datetime.datetime.now(datetime.timezone.utc).isoformat()}],
       {"Prefer": "resolution=merge-duplicates,return=minimal"})


def stampa(nome, esito):
    print(f"\n  {nome}: {esito['lettura'][:160]}" + (f"  [caso {esito['caso']}]" if esito["caso"] else "") + (f"  (abitudine: {esito['abitudine']['etichetta']})" if esito.get("abitudine") else ""))
    for i, s in enumerate(esito["strade"], 1):
        extra = f" -> {s['data']}" if s["azione"] == "ricontatta" else f" -> {s['classe']}" if s["azione"] == "chiudi" else ""
        print(f"    {i}. [{s['azione']}{extra}] {s['etichetta']}\n       {s['perche']}")
        if s.get("bozza") and PROVA:
            print("       " + s["bozza"].replace("\n", "\n       "))
    if esito["scartate"]:
        print("    scartate: " + "; ".join(f"«{e}» ({m[:70]})" for e, m in esito["scartate"][:4]))
    print(f"    costo {esito['costo']:.3f} $")


def main():
    import lettura
    from segnale_provvisorio import cellulare_di
    ora = datetime.datetime.now(datetime.timezone.utc)
    print("LE STRADE" + (" (prova: non scrive niente)" if PROVA else ""))
    scelte = scelte_di_dre()
    if scelte:
        print(f"  (Dre ha fatto {len(scelte)} scelte da cui imparare)")
    speso = spesa_di_oggi()
    aperte = proposte_da_guardare()
    con_strade = sum(1 for pr in aperte if (pr.get("azione") or {}).get("strade"))
    if speso is not None and speso >= TETTO_GIORNO:
        print(f"  tetto di spesa del giorno raggiunto: {speso:.2f} $ su {TETTO_GIORNO:.2f} $: niente strade nuove fino a domani")
        conto(speso, 0, con_strade, scelte, f"Tetto di spesa raggiunto ({speso:.2f} $): le strade riprendono domani.")
        specchio_scelte(scelte)
        return
    ids = [pr["prospect_id"] for pr in aperte]
    persone = {}
    for i in range(0, len(ids), 80):
        for p in sb("GET", f"/rest/v1/prospects?select={CAMPI}&id=in.({','.join(ids[i:i + 80])})") or []:
            persone[p["id"]] = p
    # 1. le proposte «Da guardare tu» e «Decidi tu» che aspettano Dre
    lavori = []
    for pr in aperte:
        p = persone.get(pr["prospect_id"])
        if not p:
            continue
        nome = (p.get("company") or p.get("name") or p.get("email") or "")[:34]
        if not filo_cambiato(pr, p):
            continue
        if not e_persona(pr, p):
            print(f"  {nome:34} niente strade: non c'e' una persona (autorisposta o casella di servizio)")
            continue
        if not contattabile(p):
            print(f"  {nome:34} niente strade: non e' piu' un lead (pipeline, cliente, perso, bloccato)")
            continue
        lavori.append((pr, p, nome))
    # 2. le conversazioni ferme senza una domanda
    occupati = {x["prospect_id"] for x in (sb("GET", "/rest/v1/proposte?select=prospect_id&stato=in.(aperta,approvata,in_invio)&prospect_id=not.is.null&limit=1000") or [])}
    if not SOLO_ID:
        for p in conversazioni_ferme(ora, occupati):
            lavori.append((None, p, (p.get("company") or p.get("name") or p.get("email") or "")[:34]))
    if not lavori:
        print("  niente da decidere adesso")
        conto(speso, 0, con_strade, scelte)
        specchio_scelte(scelte)
        return
    print(f"  {len(lavori)} da guardare, ne faccio {min(QUANTI, len(lavori))} questo giro (le piu' fresche prima)")
    sistema = _sistema()
    fatte, chiuse = 0, 0
    for pr, p, nome in lavori[:QUANTI]:
        if speso is not None and speso >= TETTO_GIORNO:
            print(f"  tetto di spesa raggiunto ({speso:.2f} $): il resto domani"); break
        try:
            righe, letti = lettura.leggi(p)
        except Exception as e:                                   # noqa: BLE001
            print(f"  {nome:34} lettura non riuscita: {str(e)[:80]}"); continue
        if not letti.get("ultima_loro"):
            print(f"  {nome:34} niente strade: l'ultima mail loro non si legge"); continue
        if letti.get("autorisposta"):
            if pr:
                print(f"  {nome:34}", end=""); chiudi_superata(pr, "l'ultima mail loro e' un'autorisposta, non c'e' nessuno con cui decidere", ora); chiuse += 1
            continue
        if letti.get("scritto_dopo_di_lei"):
            if pr:
                print(f"  {nome:34}", end=""); chiudi_superata(pr, f"le abbiamo gia' risposto il {letti.get('ultima_nostra_il')}: non c'e' piu' niente da decidere", ora); chiuse += 1
            continue
        try:
            cellulare = cellulare_di(p, righe)
        except Exception:                                        # noqa: BLE001
            cellulare = None
        try:
            esito = genera(p, pr, letti, righe, scelte, bool(cellulare), ora, sistema)
        except Exception as e:                                   # noqa: BLE001
            print(f"  {nome:34} il modello non ha risposto: {str(e)[:100]}"); continue
        if not esito:
            continue
        speso = (speso or 0.0) + esito["costo"]
        stampa(nome, esito)
        if PROVA:
            fatte += 1; continue
        # dove scrivere: sulla proposta (prima generazione), su una domanda nuova (il lead ha riscritto,
        # o non c'era una domanda), o da soli (abitudine)
        rifare = bool(pr and (pr.get("azione") or {}).get("strade"))
        nuova = None
        if rifare or not pr:
            let = {**letti, "coerenza": "n/a", "coerenza_motivo": "", "gruppo": None}
            perche = (f"In conversazione dopo l'analisi, senza una nostra risposta dal {letti.get('ultima_loro_il')}: {esito['lettura']}" if not pr
                      else f"Ha riscritto il {letti.get('ultima_loro_il')}: {esito['lettura']}")[:280]
            nuova = (f"{TITOLO}: {nome}", perche, {"lettura": let, "intento": esito.get("intento"), "lettore_triage": caso_di(p, pr)[1] or None})
        pid = salva(pr, p, esito, ora, nuova)
        if pid:
            fatte += 1
            if esito.get("abitudine") and len(esito["strade"]) == 1:
                print(f"    presa da sola (abitudine): {esito['strade'][0]['etichetta']}")
            else:
                print(f"    scritte sulla proposta {pid}")
        else:
            print("    non scritte: il database ha rifiutato la domanda o ce n'era gia' una")
    aperte_dopo = proposte_da_guardare() if not PROVA else aperte
    con_strade = sum(1 for pr in aperte_dopo if (pr.get("azione") or {}).get("strade"))
    conto(speso, fatte, con_strade, scelte)
    specchio_scelte(scelte)
    print(f"\n  strade generate {fatte}, domande chiuse perche' superate {chiuse}, spesa di oggi {speso or 0:.2f} $ su {TETTO_GIORNO:.0f} $")


if __name__ == "__main__":
    main()
