#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""LA LETTURA — nessuna bozza senza lettura (25/9/2026).

Il 25/9 dieci «riprese» sono partite scritte da un template alla cieca: quattro
erano sbagliate (due avevano gia' letto l'analisi, uno aveva detto no, una era
un'autorisposta). Me ne sono accorto leggendo l'ultima mail loro accanto al
testo nostro. Dre: «qualsiasi cosa hai fatto per accorgertene e' quello che
bisogna fare sempre; questo metodo fa schifo, elimina subito, nuova architettura».

Da qui in poi ogni bozza nasce da questo modulo:
  1. filo(p)        il thread VERO: le mail nel CRM, e se il corpo e' un segnaposto
                    («Risposta ricevuta (Smartlead)») si va a prenderlo da Smartlead
                    e si riempie l'archivio. Chi ha scritto per ultimo, cosa, quando.
  2. ha_gia(...)    i fatti che il codice sa leggere da solo: abbiamo gia' scritto
                    dopo la sua mail? ha gia' ricevuto l'analisi? ha detto no? e' una
                    autorisposta? ci ha girato a qualcun altro?
  3. regola_dura()  se un fatto rende il gruppo (ripresa, follow-up...) una bugia,
                    la bozza non si scrive: si salta o ci si ferma, con il motivo.
  4. coerenza()     una SECONDA TESTA (modello diverso) legge «loro / noi / bozza» e
                    dice COERENTE o INCOERENTE. Solo COERENTE entra nel database come
                    «risposta» (trigger proposta_ammessa, schema_v58): il resto va a Dre
                    come «da guardare tu», con il motivo.
La lettura viaggia dentro la proposta (azione.lettura) e si vede nella scheda:
chi approva vede la mail loro accanto al testo nostro, sempre.
"""
import datetime
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from stanza import sb, _a_secco                             # noqa: E402

AUTORISPOSTA = re.compile(r"out of (the )?office|fuori (ufficio|sede)|risposta automatica|automatic reply|auto-?reply|"
                          r"sar[òo] (assente|fuori)|assente (dal|fino|per)|rientr(o|er[òo]) (il|in|dal)|in ferie|ferie fino|"
                          r"non sono in ufficio|away from|chiusura estiva|chiusi per ferie|ufficio (e'|è) chiuso|"
                          r"avvenuta ricezione|provvederemo ad evader|conferm(a|iamo) (di|la|l')\s*(avvenuta )?ricezione|"
                          r"abbiamo ricevuto la (sua|vostra) (mail|email|richiesta|comunicazione)|questo (e'|è) un messaggio automatico|do not reply|non rispondere a questa|"
                          r"presa in carico|(richiesta|ticket|segnalazione) (e'|è) stat[ao] (inoltrat|ricevut|registrat|apert)|ticket (id|nr|n\.|numero)|id nr|numero (della|di) pratica|"
                          r"^gentile cliente|per poter gestire la (sua|vostra )?richiesta|(le|ti) sar[àa] notificat|riceverai una risposta|will get back to you", re.I | re.M)
# 12/10: lo spazio vale anche doppio o a capo («non siamo  interessati» passava per un si')
DETTO_NO = re.compile((r"non (siamo|sono|siam) interessat|non (ci|mi) interessa|\bno,? grazie|non fa per noi|"
                      r"non (abbiamo|ho) (bisogno|necessit|interesse)|abbiamo gi[àa] (un|una|il|la|chi|qualcuno)|"
                      r"non (vogliamo|voglio|desider)|non (ci|mi) contatt|"
                      r"rimuov(etemi|eteci|ermi|erci|a(mi|ci))|rimuov(ete|ere|a) (il|la|le|i|lo) (mio|mia|miei|mie|nostr)|"
                      r"cancell(atemi|ateci|ami|aci|armi|arci)|cancell(ate|are|i) (il|la|le|i|lo) (mio|mia|miei|mie|nostr)|"
                      r"(rimuov|cancell)\w* (dalla|dalle|dai|dal|dagli) (vostr|lista|list|mailing|database|elenc|contatt)|declin|"
                      r"non (e'|è) di (nostro|mio) interesse|non (rientra|ci rientra) nei (nostri|miei)|non (ne )?abbiamo (la )?necessit|"
                      r"(siamo|sono) gi[àa] (seguit|copert|a posto)|"
                      r"non (siamo|sono) alla ricerca|non (ci|mi) serve|non (e'|è) (il|un) (nostro|mio) (obiettivo|interesse)").replace(" ", r"\s+"), re.I)
GIA_LETTA = re.compile(r"(ho|abbiamo|avevo|avevamo) (letto|visto|ricevuto|guardato|dato un.occhiata|analizzato)[^.\n]{0,40}analisi|"
                       r"grazie (per|dell)[^.\n]{0,20}analisi|l.analisi (che|ricevuta|inviata)|"
                       r"(per il|del) materiale (che|ricevuto|inviato)|materiale che (mi|ci) ha (trasmesso|inviato|mandato)|"
                       r"(letto|visto|guardato) (il|la) (documento|report|analisi|presentazione)", re.I)
SERVIZIO = re.compile(r"^(assistenza|supporto|support|helpdesk|help|ticket|noreply|no-reply|donotreply|customercare|customer\.?service|servizioclienti)@", re.I)
EMAIL = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+", re.I)
from senso import NOSTRI, PEC, rimando_prima                # noqa: E402  una regola, un posto (12/10)


def _segnaposto(b):
    """La notifica di Smartlead al posto della risposta vera. 12/10: via la regola «meno di 60
    caratteri», che buttava i si' corti («mandali pure grazie»): quelli sono risposte vere.
    Una regola, un posto: la usa anche la rilettura."""
    t = " ".join((b or "").split()).lower()
    return not t or t.startswith("risposta ricevuta") or "smartlead" in t[:80]


def _smartlead(p):
    """Tutto il thread da Smartlead (la fonte vera), come righe kind/at/body."""
    try:
        import manda
        from sync_v2 import corpo_pulito
    except Exception:
        return []
    try:
        cid, lid, _ = manda.thread(p)          # riprova da sola se Smartlead frena (5/10)
        if not cid:
            return []
        h = manda._sl_riprova("GET", f"/campaigns/{cid}/leads/{lid}/message-history") or {}
    except Exception as e:                                   # noqa: BLE001
        print(f"    THREAD SMARTLEAD NON LETTO ({p.get('email')}): {str(e)[:80]}")
        return []
    out = []
    for m in h.get("history") or []:
        corpo = corpo_pulito(m.get("email_body"))
        out.append({"kind": "email_in" if m.get("type") == "REPLY" else "email_out",
                    "at": (m.get("time") or "")[:19], "body": corpo[:3000], "da": "smartlead"})
    return out


# QUELLO CHE HA SCRITTO LUI, SENZA LA NOSTRA MAIL SOTTO (Dre, 28/9). Una lead
# immobiliare ha risposto «si grazie sono curiosa» e il sistema l'ha saltata dicendo
# che aveva «chiesto di non essere contattata»: la parola «cancellarlo» stava
# dentro la NOSTRA firma sul GDPR, citata sotto la sua risposta. Misurato su 300
# risposte: 6 bloccate per sbaglio, fra cui un si' pieno. Da qui in poi le regole
# che cercano un rifiuto guardano solo le righe che ha scritto la persona.
CITAZIONE = re.compile(
    r"\n\s*(?:>\s*)?(?:il giorno\s+\w|on\s+\w.{0,60}\bwrote:|-{2,}\s*original message|"
    r"da:\s|from:\s|inviato:\s|sent:\s|a:\s.{0,60}\noggetto:|_{5,}|"
    # 12/10: l'intestazione senza i due punti («Da "Nome" <indirizzo> ... Oggetto») e quella
    # polacca (Od: / Wysłane: / Temat:): la nostra mail citata sotto restava nel testo suo
    r"(?:da|from)\s+[^\n<@]{0,60}<?[\w.+-]+@[\w-]+(?:\.[\w-]+)+>?[\s\S]{0,300}?\b(?:oggetto|subject)\b|od:\s|wys[łl]ane:\s|temat:\s)", re.I)

# L'INTESTAZIONE DELLA CITAZIONE, ANCHE SENZA A CAPO (29/9). «Il 16/07/2026 16:37,
# Lorenzo ha scritto:» o «On Jul 15, 2026 at 4:37 PM Lorenzo <...> wrote:»: la regola
# sopra vuole un a capo davanti e «il giorno», e 95 risposte su 688 si portavano
# dietro la nostra mail intera. Il lettore e le regole leggevano il nostro testo come
# suo: una nostra frase con «analisi» sotto un «non siamo interessati». Si riconosce
# da «ha scritto:»/«wrote:» con una data e un'ora poco prima; si taglia dall'«Il»/«On»
# che apre. Senza data non si taglia: «va bene alle 16:30, il collega ha scritto:» e' suo.
_SCRITTO = re.compile(r"\b(?:ha scritto|wrote|napisa[łl]\w*)\s*:", re.I)
_ORA = re.compile(r"\b\d{1,2}[:.]\d{2}\b")
_DATA = re.compile(r"\b(?:19|20)\d{2}\b|\b\d{1,2}[/.-]\d{1,2}[/.-]\d{2,4}\b")
_APERTURA = re.compile(r"(?<!\w)(?:il giorno|il|on|am|el|le|w dniu|dnia)\s", re.I)


def _intestazione(t):
    """Dove comincia l'intestazione della mail citata, o None."""
    for m in _SCRITTO.finditer(t):
        da = max(0, m.start() - 200)
        ore = list(_ORA.finditer(t, da, m.start()))
        if not ore or not _DATA.search(t, da, m.start()):
            continue           # «il mio collega ha scritto:» non e' una citazione
        aperture = list(_APERTURA.finditer(t, da, ore[0].start()))
        return aperture[-1].start() if aperture else ore[0].start()
    return None


# La firma aziendale, che comincia dopo i saluti. Un lead immobiliare (28/9)
# ha scritto «sarei felice di ricevere la vostra analisi» ed e' stato bloccato
# dalla parola «privacy» dentro la SUA firma («Informativa privacy disponibile
# sul nostro sito»). Misurato su 300 risposte: 45 portano un disclaimer legale.
SALUTI = re.compile(
    r"\n\s*(?:cordiali saluti|distinti saluti|un cordiale saluto|cari saluti|"
    r"in attesa di|best regards|kind regards|--\s*$|__+\s*$|"
    # 12/10: «Cordialità», «porgo i migliori saluti», «Buon lavoro» chiudono il messaggio come gli altri
    r"cordialit[àa]|(?:porg|invi)\w*\s[^\n]{0,20}saluti|buon lavoro|"
    r"rest\w+ a (?:sua |vostra )?(?:completa )?disposizione)", re.I | re.M)
DISCLAIMER = re.compile(
    r"informativa privacy|"
    r"(?:le |l')informazioni (?:incluse|contenute|trasmesse|presenti)|"
    r"questo (?:messaggio|documento|e-?mail) (?:e'|è) (?:riservat|confidenzial|destinat)|"
    r"il (?:presente|contenuto del) messaggio (?:e'|è)|"
    r"this (?:communication|message|e-?mail|document) is (?:confidential|intended|reserved)|"
    r"reg\.? ?ue ?2016/679|regolamento \(?ue\)? ?2016/679|\bgdpr\b|privacy:\s|"
    r"destinatario indicato|ai sensi dell|\*{6,}|"
    r"se (?:avete|hai) ricevuto (?:questo|questa) (?:messaggio|documento|mail|comunicazione) per errore|"
    # 12/10: due si' veri fermati come no dal «cancellare il messaggio» dell'informativa:
    # «Il presente messaggio e gli eventuali allegati sono destinati...», «Questa mail
    # contiene informazioni riservate...», «Qualora fosse stato ricevuto per errore...»
    r"(?:il )?presente (?:messaggio|e-?mail|comunicazione)[^.\n]{0,60}(?:destinat|riservat|confidenzial)|"
    r"quest[ao] (?:mail|e-?mail|messaggio|comunicazione) (?:contiene|(?:e'|è) (?:riservat|confidenzial|destinat))|"
    r"(?:se|qualora) (?:ha|avete|hai|abbia|aveste|fosse stat[oa]) ricevut\w* [^.\n]{0,40}per errore", re.I)


# L'OGGETTO IN TESTA (12/10). posta.py scrive il corpo come «oggetto, riga vuota, testo», e
# 15 risposte su 321 cominciavano col NOSTRO oggetto («Re: Analisi per ...»): il lettore lo
# leggeva come suo. Una prima riga «Re:/R:/I:/Fwd: ...» seguita da una riga vuota e' un oggetto,
# non un messaggio; e un oggetto che chi chiama sa nostro si toglie anche senza il «Re:».
OGGETTO_IN_TESTA = re.compile(r"^\s*(?:re|r|i|fw|fwd|rif|aw|odp)\s*:[^\n]{0,200}\n[ \t]*\n", re.I)


def _parti(testo, con_firma=False, nostri_oggetti=()):
    """(quello che ha scritto lui, quello che si e' tolto). Una funzione sola per i due lati,
    cosi' il resto che va al lettore (secondo blocco del prompt) e' esattamente il taglio."""
    t = testo or ""
    tolto = []
    m = OGGETTO_IN_TESTA.match(t)
    if m:
        tolto.append(t[:m.end()].strip()); t = t[m.end():]
    for o in nostri_oggetti or ():
        o = re.sub(r"^\s*(?:re|r|i|fw|fwd|rif)\s*:\s*", "", o or "", flags=re.I).strip()
        if len(o) >= 6:
            mo = re.match(r"\s*(?:(?:re|r|i|fw|fwd|rif)\s*:\s*)*" + re.escape(o) + r"[ \t]*\n?", t, re.I)
            if mo:
                tolto.append(t[:mo.end()].strip()); t = t[mo.end():]
    m = CITAZIONE.search(t)
    if m:
        tolto.append(t[m.start():]); t = t[:m.start()]
    h = _intestazione(t)
    if h is not None:
        tolto.append(t[h:]); t = t[:h]
    # via le righe citate con «>», che in ogni client sono testo di qualcun altro
    righe = t.split("\n")
    tolto += [r for r in righe if r.lstrip().startswith(">")]
    t = "\n".join(r for r in righe if not r.lstrip().startswith(">")).strip()
    if con_firma:
        return t, tolto
    # il disclaimer legale: si taglia da dove comincia
    d = DISCLAIMER.search(t)
    if d:
        tolto.append(t[d.start():]); t = t[:d.start()]
    # la firma: si taglia dopo i saluti, ma solo se resta abbastanza messaggio
    f = SALUTI.search(t)
    if f and len(t[:f.start()].strip()) >= 25:
        tolto.append(t[f.start():]); t = t[:f.start()]
    return t.strip(), tolto


def solo_suo(testo, con_firma=False, nostri_oggetti=()):
    """Quello che ha scritto la persona: senza il nostro oggetto in testa, senza la nostra mail
    citata sotto e, se non si chiede il contrario, senza la sua firma e il disclaimer legale.

    Serve alle regole che cercano un rifiuto: «privacy», «cancellar», «rimuov»
    stanno quasi sempre nella firma o nel disclaimer, non in quello che dice.
    Per leggere il messaggio intero (per esempio per scrivere la risposta) si
    passa con_firma=True: li' la firma serve, perche' contiene il nome e il ruolo.
    """
    return _parti(testo, con_firma, nostri_oggetti)[0]


PREFISSO_RISPOSTA = re.compile(r"^\s*(?:re|r|i|fw|fwd|rif|aw|odp)\s*:", re.I)


def _senza_prefisso(o):
    return re.sub(r"^\s*(?:(?:re|r|i|fw|fwd|rif|aw|odp)\s*:\s*)*", "", o or "", flags=re.I).strip().lower()


def corpo_e_oggetto(riga, nostri_oggetti=()):
    """(corpo, oggetto) di una mail del CRM. Le mail arrivate da Gmail (ref «gmail:») posta.py le
    scrive «oggetto, riga vuota, testo» (12/10).

    12/10 sera, dagli scettici: prima la prima riga si staccava SEMPRE. Ma posta.py faceva lo strip,
    e con l'oggetto vuoto il primo paragrafo della persona («Sì, mandatemela pure») diventava
    «l'oggetto» e spariva dal testo suo. Ora la prima riga e' un oggetto da togliere solo se:
      - e' vuota (posta.py, dal 12/10 sera, lascia la riga vuota quando l'oggetto manca);
      - e' una risposta o un inoltro («Re:», «R:», «I:», «Fwd:»...): l'oggetto e' il NOSTRO;
      - e' uguale a un nostro oggetto che chi chiama conosce.
    Altrimenti resta nel testo: o e' l'oggetto nuovo scritto da LUI («Richiesta variazione
    riunione»), che e' parola sua, o e' una riga vecchia col primo paragrafo suo."""
    b = (riga or {}).get("body") or ""
    if str((riga or {}).get("ref") or "").startswith("gmail:") and "\n\n" in b:
        oggetto, corpo = b.split("\n\n", 1)
        o = oggetto.strip()
        if not o:
            return corpo, ""
        nostri = {_senza_prefisso(x) for x in nostri_oggetti or () if x and _senza_prefisso(x)}
        if len(o) <= 200 and "\n" not in o and (PREFISSO_RISPOSTA.match(o) or _senza_prefisso(o) in nostri):
            return corpo, o
    return b, ""


def resto(testo, nostri_oggetti=()):
    """Quello che solo_suo ha tolto (oggetto, citazione, firma, informativa), in ordine.
    Va al lettore come secondo blocco: serve a capire, non conta (12/10)."""
    return "\n".join(x.strip() for x in _parti(testo, False, nostri_oggetti)[1] if x and x.strip())


def filo(p):
    """Il thread vero, in ordine di tempo. Riempie i segnaposto nel CRM strada facendo."""
    righe = sb("GET", f"/rest/v1/interactions?select=id,kind,at,body,ref&prospect_id=eq.{p['id']}"
                      "&kind=in.(email_in,email_out,followup,analisi,call,nota)&order=at.asc&limit=60") or []
    mail_in = [r for r in righe if r["kind"] == "email_in"]
    # Smartlead si legge SEMPRE quando c'e' l'email: e' la fonte vera, e le mail
    # nostre mandate da li' (campagna, risposte, riprese) spesso nel CRM non ci sono
    if p.get("email"):
        vere = _smartlead(p)
        if vere:
            # i segnaposto del CRM si riempiono con il corpo vero (stessa data al minuto, o l'ultima risposta)
            risposte = [v for v in vere if v["kind"] == "email_in"]
            for r in mail_in:
                if _segnaposto(r.get("body")) and risposte:
                    at = (r.get("at") or "")[:16]
                    v = next((x for x in risposte if x["at"][:16] == at), None) or risposte[-1]
                    if not _segnaposto(v["body"]):          # 12/10: un si' corto e' una risposta vera
                        r["body"] = v["body"]
                        try:
                            sb("PATCH", f"/rest/v1/interactions?id=eq.{r['id']}", {"body": v["body"][:3000]})
                        except Exception:
                            pass
            # le mail che il CRM non ha (nostre o loro) entrano nel filo in lettura, non nel CRM
            noti = {(r["kind"] if r["kind"] == "email_in" else "email_out", (r.get("at") or "")[:16]) for r in righe}
            for v in vere:
                if (v["kind"], v["at"][:16]) not in noti:
                    righe.append(v)
            righe.sort(key=lambda r: r.get("at") or "")
    return righe


# IL SECONDO LETTORE (30/9, verdetto del metro su 150 mail etichettate da Dre).
# Il modello (cervello.classifica_risposta) legge meglio delle regex dove conta:
# sì presi per no 1/44 (ed era un dubbio) contro 3/44, «non scrivetemi» mancati
# 0/3 contro 2/3. Fino al 12/10 leggevano in DUE con la regola «un freno scatta se lo
# dice UNO dei due»: e' la regola che il 12/10 ha fermato due si' veri per una parola
# dell'informativa. Resta solo finche' l'interruttore senso_v2 e' spento (sette giorni
# in ombra, poi la pulizia): da li' decide senso.giudica, qui sotto.
# 12/10 sera: il vecchio non paga piu' una sua lettura (secondo_lettore, cancellato): usa le
# probabilita' della lettura del senso, la stessa, salvata (vecchio_lettore qui sotto).

def vecchio_lettore(p, riga):
    """Le soglie di prima sulla lettura del senso di questa mail (gratis se gia' letta). None = nessuna opinione."""
    try:
        return cervello_decisioni((senso(p, riga) or {}).get("risposte"))
    except Exception:                                        # noqa: BLE001
        return None


def _per_il_vecchio(r):
    """Le soglie di prima conoscevano una domanda sola per il grave: dal 12/10 l'ostilita'
    ha la sua, e per la regola vecchia vale come «non contattare»."""
    if not r:
        return r
    return {**r, "non_contattare": max(r.get("non_contattare", 0), r.get("ostile", 0))}


def frena(regex_dice, lettore, etichette):
    """Il freno: basta che UNO dei due lo dica, dubbio compreso. (Vale solo con senso_v2 spento.)"""
    return bool(regex_dice) or bool(lettore and lettore.get("etichetta") in etichette)


def si_acceso(regex_dice, lettore):
    """Il via: la regex di sempre, oppure il modello SICURO. Mai un via da un dubbio."""
    if lettore and lettore.get("etichetta") in ("no", "non_scrivere"):
        return False
    return bool(regex_dice) or bool(lettore and lettore.get("etichetta") == "si" and not lettore.get("dubbio"))


# ── IL SENSO (12/10/2026) ─────────────────────────────────────────────────────────
# Dre: «questo deve essere interpretato». Il senso di quello che ha scritto una persona lo
# decide l'AI, sul testo suo; la lista di parole resta solo come rete per i gravi
# (senso.GRAVI); se discordano si rilegge e il dubbio va a Dre in tre righe, mai un blocco
# muto. Una lettura per messaggio: si salva nella tabella `letture` (schema_v81) e tutti
# gli altri (bozze, prima risposta, postino, analisi, seguiti) la rileggono gratis.
# L'interruttore e' la riga `senso_v2` in `operazioni`: spento, il nuovo gira in ombra
# accanto al vecchio e non decide niente; acceso, decide lui. Si torna indietro con una riga.

_MEMO = {}                       # (prospect, impronta, versione) -> riga: nello stesso giro non si rilegge
_STATO = {"tabella": None, "soglie": "?", "acceso": None}
SCELTE_DRE = [["si", "Sì, vuole"], ["no", "No"], ["non_scrivere", "Non scrivetemi più"],
              ["fuori_ufficio", "Fuori ufficio"], ["rinvio", "Più avanti"], ["altro", "Altro"]]


def senso_acceso():
    """L'interruttore senso_v2 (tabella operazioni). Se non si legge, e' spento: si resta sul vecchio."""
    if _STATO["acceso"] is None:
        try:
            r = sb("GET", "/rest/v1/operazioni?select=attiva&chiave=eq.senso_v2&limit=1") or []
            _STATO["acceso"] = bool(r and r[0].get("attiva"))
        except Exception:                                    # noqa: BLE001
            _STATO["acceso"] = False
    return _STATO["acceso"]


def soglie_lettore():
    """Le soglie dal Manuale (regole, sezione F), una volta per giro. None = senza regole."""
    if _STATO["soglie"] == "?":
        import senso as S
        try:
            righe = sb("GET", "/rest/v1/regole?select=chiave,valore&limit=500") or []
            _STATO["soglie"] = S.soglie(righe)
        except Exception:                                    # noqa: BLE001
            _STATO["soglie"] = None
    return _STATO["soglie"]


def _impronta(suo):
    import hashlib
    return hashlib.sha256(" ".join((suo or "").lower().split()).encode("utf-8")).hexdigest()[:32]


def _riga_salvata(pid, impronta, versione):
    """La lettura salvata di questo messaggio. 12/10 sera: la scelta di Dre riguarda il TESTO, non
    il lettore. Prima si cercava solo la versione corrente, e ritoccare una domanda faceva sparire
    tutte le scelte di Dre (la stessa mail riletta a pagamento, la stessa domanda rifatta). Ora:
    prima una scelta di Dre su questo testo, a qualunque versione; poi la lettura della versione
    corrente. Una domanda sola al database."""
    if _STATO["tabella"] is False or not pid:
        return None
    try:
        r = sb("GET", f"/rest/v1/letture?select=*&prospect_id=eq.{pid}&impronta=eq.{impronta}&order=letta_il.desc&limit=20") or []
        _STATO["tabella"] = True
    except Exception as e:                                   # noqa: BLE001
        if "PGRST205" in str(e) or "404" in str(e):
            _STATO["tabella"] = False                        # schema_v81 non ancora applicato: si legge in memoria
        return None
    dre = [x for x in r if x.get("decisione_dre")]
    if dre:
        return max(dre, key=lambda x: x.get("deciso_il") or "")
    return next((x for x in r if x.get("versione") == versione), None)


def _salva(riga):
    """Upsert della lettura. Se non riesce si usa quella in memoria: il giro dopo la riscrive."""
    if _STATO["tabella"] is False or _a_secco():
        return riga
    try:
        corpo = {k: v for k, v in riga.items() if k not in ("id", "decisione_dre", "deciso_il", "proposta_id")}
        r = sb("POST", "/rest/v1/letture?on_conflict=prospect_id,impronta,versione", corpo,
               {"Prefer": "resolution=merge-duplicates,return=representation"}) or []
        return {**riga, **(r[0] if r else {})}
    except Exception as e:                                   # noqa: BLE001
        print(f"    (lettura non salvata: {str(e)[:80]})")
        return riga


def _da_riga(riga, nostri_oggetti=(), oggetto="", interaction_id=None):
    """LA PORTA SOLA (12/10 sera). Una riga del CRM (o del filo Smartlead) diventa (corpo, oggetto,
    nostri oggetti, interaction_id) in un posto solo. Prima ogni chiamante preparava il testo a modo
    suo (il corpo grezzo, o corpo_e_oggetto): per le mail di Gmail lo stesso messaggio dava due
    testi suoi, due impronte, due letture pagate, e la scelta di Dre su una non valeva sull'altra."""
    corpo, ogg = corpo_e_oggetto(riga, nostri_oggetti)
    if interaction_id is None and riga.get("da") != "smartlead":
        interaction_id = riga.get("id")
    if ogg:
        oggetto = oggetto or ogg
        nostri_oggetti = (*(nostri_oggetti or ()), ogg)
    return corpo, oggetto, tuple(nostri_oggetti or ()), interaction_id


def senso(p, corpo, *, interaction_id=None, nostra="", nostri_oggetti=(), oggetto="", leggi=True,
          chiedi=None, segnali=(), attuale=None):
    """La lettura di UNA risposta: taglia, cerca nella tabella, chiama il modello una volta,
    decide con senso.giudica, salva, e se serve chiede a Dre. Torna la riga di `letture`
    (con `decisione`). Non solleva: senza rete la decisione e' «senza_ai» (freno, niente di
    permanente). `segnali` sono i segnali gravi che non stanno nel testo (Smartlead
    is_unsubscribed, categoria «Do Not Contact»): entrano nella rete.

    `corpo` e' la riga del CRM (dict con body, ref, id): e' la porta sola, e tutti passano da
    qui. Un testo (str) lo passa solo il sync, che legge da Smartlead prima che la riga esista.

    12/10 sera, dagli scettici:
      - LA DECISIONE NON SI CONGELA. Nella tabella contano le probabilita' (risposte, seconda): la
        decisione si ricalcola a ogni uso con le soglie del Manuale di adesso (un calcolo puro,
        gratis). Prima una soglia cambiata nel Manuale non arrivava alle letture gia' salvate.
      - LA RETE GUARDA ANCHE FIRMA E INFORMATIVA (senza la nostra mail citata). Il taglio della
        firma portava via anche le richieste vere: «P.S. cancellatemi» dopo i saluti, «Buon lavoro
        e non contattateci piu'», un'opposizione GDPR scritta in linguaggio legale. Il falso
        allarme dell'informativa costa una seconda lettura, che lo scarta.
      - MAI «SICURO» SENZA UNA LETTURA. Se il testo suo resta vuoto ma la mail no, l'AI legge
        la mail intera (le domande le dicono gia' che firme e informative non contano).
      - SENZA REGOLE NON SI PAGA. Una lettura che non si sa usare non si compra.
      - IL DUBBIO ARRIVA A DRE ANCHE DOPO. Un dubbio salvato in ombra, o una domanda non riuscita,
        si chiede al primo passaggio con l'interruttore acceso."""
    import cervello
    import senso as S
    if isinstance(corpo, dict):
        corpo, oggetto, nostri_oggetti, interaction_id = _da_riga(corpo, nostri_oggetti, oggetto, interaction_id)
    corpo = (corpo or "")[:3000]                             # come l'archivio del CRM: stessa impronta da ogni strada
    suo = solo_suo(corpo, nostri_oggetti=nostri_oggetti)
    intero = solo_suo(corpo, con_firma=True, nostri_oggetti=nostri_oggetti)
    letto = suo if suo.strip() else intero                   # quello che l'AI legge come suo
    imp, ver = _impronta(suo if suo.strip() else "\x00" + intero), cervello.VERSIONE
    chiave = (p.get("id"), imp, ver)
    if chiave in _MEMO:
        return _MEMO[chiave]
    s = soglie_lettore()
    salvata = _riga_salvata(p.get("id"), imp, ver)
    dre = (salvata or {}).get("decisione_dre")
    # i segnali di Smartlead (disiscritto, «Do Not Contact») li vede solo il sync: restano nella lettura
    # anche quando la rilegge chi non li ha, e la rete si ricalcola sul testo (la lista puo' cambiare)
    vivi = [x for x in segnali if x] + [x for x in (salvata or {}).get("rete") or [] if str(x).startswith("Smartlead:")]
    rete = S.rete(intero) + list(dict.fromkeys(vivi))
    mie = [p.get("email"), *(p.get("email_alt") or [] if isinstance(p.get("email_alt"), list) else [p.get("email_alt")])]
    r, sec, problemi, pagate = None, None, [], 0
    if salvata and salvata.get("risposte"):
        r, sec = salvata["risposte"], salvata.get("seconda")
    elif letto.strip() and leggi and not dre and s is not None and _riprovo(salvata):
        r = cervello.classifica_risposta(letto, resto(corpo, nostri_oggetti) if suo.strip() else "", nostra, oggetto)
        pagate += 1
    if not letto.strip():
        dec = S._d(etichetta="illeggibile", sicuro=True, dubbio=False, freno=True, fonte="nessuna", stato="letta",
                   rete=rete, grave=bool(rete), motivo="niente da leggere: la mail e' vuota o e' solo la nostra citata")
    elif dre:
        dec = S.giudica(r, rete, s, dre=dre)
    else:
        rv, problemi = S.verifica(r, letto, s, mie) if r else (r, [])
        dec = S.giudica(rv, rete, s, problemi=problemi)
        if dec.get("serve_seconda"):
            c = dec["contesa"]
            buona = bool(sec) and sec.get("campo") == c.get("campo") and (
                isinstance(sec.get("p"), (int, float)) or (salvata or {}).get("proposta_id") or not _riprovo(salvata))
            if not buona and leggi:
                # la frase della lista puo' stare nella firma o in un P.S.: la seconda legge la mail intera
                sec = cervello.rileggi(intero if c.get("da") == "lista" else letto, c, rv) or {"campo": c.get("campo"), "p": None}
                pagate += 1
            if sec and sec.get("campo") == c.get("campo"):
                dec = S.giudica(rv, rete, s, seconda=sec, problemi=problemi)
    fallita = dec["stato"] == "senza_ai" or (bool(sec) and sec.get("p") is None)
    tentativi = int((salvata or {}).get("tentativi") or 0) + (1 if pagate and fallita else 0)
    riga = {"prospect_id": p.get("id"), "interaction_id": interaction_id or (salvata or {}).get("interaction_id"),
            "impronta": imp, "versione": (salvata or {}).get("versione") if dre else ver,
            "testo_suo": letto[:4000], "risposte": r, "seconda": sec, "rete": rete, "decisione": dec,
            "stato": dec["stato"], "fonte": dec["fonte"], "tentativi": tentativi,
            "modello": (salvata or {}).get("modello") if not pagate else (cervello._modello_lettura() if r else None)}
    if pagate:
        riga["letta_il"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
    if salvata:
        riga = {**salvata, **riga, "id": salvata.get("id")}
    cambiata = not salvata or pagate or not all(json_uguale(salvata.get(k), riga.get(k))
                                                for k in ("stato", "fonte", "rete", "interaction_id", "tentativi"))
    if p.get("id") and cambiata and not dre:
        riga = _salva(riga)
    elif dre and interaction_id and not (salvata or {}).get("interaction_id") and salvata.get("id") and not _a_secco():
        try:                                                 # il sync la legge prima che esista la riga nel CRM
            sb("PATCH", f"/rest/v1/letture?id=eq.{salvata['id']}", {"interaction_id": interaction_id}, {"Prefer": "return=minimal"})
        except Exception:                                    # noqa: BLE001
            pass
    if chiedi is None:
        chiedi = senso_acceso()
    if chiedi and dec["stato"] == "dubbio_a_dre" and not riga.get("proposta_id") and S.va_a_dre(dec, attuale):
        riga = chiedi_a_dre(p, riga) or riga
    if chiedi and leggi and dec["stato"] in ("senza_ai", "senza_regole"):
        if tentativi >= 3 or dec["stato"] == "senza_regole":
            avviso_lettore_giu(dec["stato"])
    _MEMO[chiave] = riga
    return riga


def _riprovo(salvata):
    """Si ripaga una lettura fallita (AI giu', seconda senza risposta)? Le prime tre volte a ogni giro,
    poi una volta l'ora: un modello che risponde male non si paga ogni cinque minuti per sempre."""
    if not salvata or int(salvata.get("tentativi") or 0) < 3:
        return True
    ultima = _quando(salvata.get("letta_il"))
    return not ultima or datetime.datetime.now(datetime.timezone.utc) - ultima > datetime.timedelta(hours=1)


def json_uguale(a, b):
    """Confronto di due valori come li tiene il database (liste e dict compresi)."""
    import json
    return json.dumps(a, sort_keys=True, default=str) == json.dumps(b, sort_keys=True, default=str)


def lettura_salvata(p, riga):
    """La lettura gia' fatta di questa mail, senza pagarne una nuova e senza scrivere. None = da leggere."""
    import cervello
    corpo, _o, nostri, _i = _da_riga(riga)
    corpo = (corpo or "")[:3000]
    suo = solo_suo(corpo, nostri_oggetti=nostri)
    imp = _impronta(suo if suo.strip() else "\x00" + solo_suo(corpo, con_firma=True, nostri_oggetti=nostri))
    return _riga_salvata(p.get("id"), imp, cervello.VERSIONE)


def chiedi_a_dre(p, riga):
    """Il dubbio in tre righe, una volta per messaggio. Sotto, i bottoni del Metro: la scelta di Dre
    scrive la lettura (RPC decidi_lettura) e diventa un'etichetta.
    12/10 sera: il ref e' del MESSAGGIO (prospect + impronta), non della riga: una versione nuova del
    lettore non rifa' la stessa domanda. Se la domanda c'e' gia', la riga si lega a quella."""
    import senso as S
    from stanza import proponi
    dec = riga.get("decisione") or {}
    nome = (p.get("company") or p.get("name") or p.get("email") or "Un'azienda")[:60]
    ref = f"senso:{p.get('id')}:{(riga.get('impronta') or '')[:16]}"
    try:
        pid = proponi("senso", f"{nome}: non sono sicura di cosa ha risposto", prospect_id=p.get("id"),
                      perche=S.tre_righe(dec, riga.get("testo_suo")),
                      azione={"senso": {"lettura_id": riga.get("id"), "grave": bool(dec.get("grave")), "frase": dec.get("frase"),
                                        "tre_righe": S.tre_righe(dec, riga.get("testo_suo")),
                                        "rete": dec.get("rete"), "etichetta": dec.get("etichetta"), "fonte": dec.get("fonte")},
                              "scelte": SCELTE_DRE},
                      ref=ref)
        nuova = (pid or [{}])[0].get("id") if isinstance(pid, list) else None
        if not nuova and not _a_secco():
            nuova = ((sb("GET", f"/rest/v1/proposte?select=id&ref=eq.{ref}&limit=1") or [{}])[0]).get("id")
        if nuova and riga.get("id") and not _a_secco():
            sb("PATCH", f"/rest/v1/letture?id=eq.{riga['id']}", {"proposta_id": nuova}, {"Prefer": "return=minimal"})
        return {**riga, "proposta_id": nuova} if nuova else riga
    except Exception as e:                                   # noqa: BLE001
        print(f"    (domanda a Dre non scritta: {str(e)[:80]})")
        return riga


def avviso_lettore_giu(stato="senza_ai"):
    """L'AI giu' (o le regole illeggibili): UN avviso al giorno, non uno per messaggio."""
    from stanza import proponi
    oggi = datetime.date.today().isoformat()
    try:
        n = len(sb("GET", "/rest/v1/letture?select=id&stato=in.(senza_ai,senza_regole)&limit=500") or []) if _STATO["tabella"] else 0
    except Exception:                                        # noqa: BLE001
        n = 0
    cosa = "Le soglie del lettore nel Manuale non si leggono" if stato == "senza_regole" else \
        f"Il lettore non risponde da stamattina alle {datetime.datetime.now().strftime('%H:%M')}"
    proponi("senso", f"{cosa}: le risposte aspettano", ref=f"senso:giu:{oggi}",
            perche=f"{cosa}: {n or 'alcune'} risposte aspettano, nessuna parte da sola e non chiudo niente. Le trovi in Posta.")


def _campi_dalla_lettura(riga, s):
    """I campi di senso che le bozze, la prima risposta e il postino usano, dalla lettura."""
    import senso as S
    dec = (riga or {}).get("decisione") or {}
    r = (riga or {}).get("risposte") or {}
    gia = bool(s) and r.get("ha_gia_analisi", 0) >= s["lettore_ha_gia_analisi"][0]
    e = dec.get("etichetta")
    return {
        # chi chiede di non essere contattato ha detto no anche lui (come il freno di prima)
        "detto_no": e in ("no", "non_scrivere"),
        "detto_no_sicuro": e in ("no", "non_scrivere") and S.permanente_ok(dec),
        "non_scrivere": bool(dec.get("grave")),
        "autorisposta": e == "auto",
        "analisi_gia_letta": gia,
        "girato_a": list(dec.get("girato_a") or [])[:3],
        "si_sicuro": e == "si" and bool(dec.get("sicuro")) and not dec.get("dubbio") and not dec.get("grave"),
        "lettura_id": (riga or {}).get("id"), "lettura_stato": dec.get("stato"), "fonte": dec.get("fonte"),
        "dubbio": bool(dec.get("dubbio")) or dec.get("stato") == "dubbio_a_dre", "frase": dec.get("frase") or "",
        "permanente_ok": S.permanente_ok(dec), "versione": (riga or {}).get("versione"),
        "domanda": dec.get("domanda") or "", "etichetta": e, "motivo_lettura": dec.get("motivo") or "",
        "chiesto_a_dre": bool((riga or {}).get("proposta_id")),
    }


def ombra(riga):
    """Quello che il senso nuovo direbbe, accanto ai valori vecchi: non decide niente (passo 6)."""
    dec = (riga or {}).get("decisione") or {}
    return {"etichetta": dec.get("etichetta"), "sicuro": dec.get("sicuro"), "dubbio": dec.get("dubbio"),
            "grave": dec.get("grave"), "fonte": dec.get("fonte"), "stato": dec.get("stato"),
            "lettura_id": (riga or {}).get("id"), "frase": dec.get("frase"), "motivo": dec.get("motivo")}


def ha_gia(p, righe):
    """I fatti che si leggono dal filo senza chiedere a nessuno."""
    loro = [r for r in righe if r["kind"] == "email_in" and not _segnaposto(r.get("body"))]
    ultima_loro = loro[-1] if loro else None
    nostre = [r for r in righe if r["kind"] in ("email_out", "followup", "analisi")]
    dopo = [r for r in nostre if ultima_loro and (r.get("at") or "") > (ultima_loro.get("at") or "")]
    ultima_nostra = nostre[-1] if nostre else None
    # la nostra mail a cui ha risposto (l'ultima prima della sua): il terzo blocco del lettore
    prima_di_lei = [r for r in nostre if ultima_loro and (r.get("at") or "") <= (ultima_loro.get("at") or "")]
    testo = (ultima_loro or {}).get("body") or ""
    nostre_testo = " ".join((r.get("body") or "") for r in nostre).lower()
    alt = p.get("email_alt") or []
    alt = alt if isinstance(alt, list) else [alt]
    mie = {(p.get("email") or "").lower(), *[str(a).lower() for a in alt if a]}
    dom = (p.get("email") or "").split("@")[-1].lower()
    acceso = senso_acceso()
    lett = None
    if testo.strip():
        lett = senso(p, ultima_loro, nostra=(prima_di_lei[-1].get("body") or "") if prima_di_lei else "",
                     attuale=p.get("classificazione"), chiedi=acceso)
    base = {
        "ultima_loro": " ".join(testo.split())[:600], "ultima_loro_il": (ultima_loro or {}).get("at", "")[:10],
        # 12/10 sera: l'ora e l'id, non solo il giorno: il postino riconosce una mail dello stesso giorno
        "ultima_loro_at": (ultima_loro or {}).get("at") or "", "ultima_loro_id": (ultima_loro or {}).get("id"),
        "ultima_nostra": " ".join(((ultima_nostra or {}).get("body") or "").split())[:400], "ultima_nostra_il": (ultima_nostra or {}).get("at", "")[:10],
        "scritto_dopo_di_lei": len(dopo),
        "casella_di_servizio": bool(SERVIZIO.match(p.get("email") or "")),
        "destinatario": (alt[0] if alt and alt[0] else None),
        "letto_il": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
    }
    if acceso:
        # senso_v2 acceso: tutti i campi di senso vengono dalla lettura, nessuna lista
        f = _campi_dalla_lettura(lett, soglie_lettore()) if lett else {
            "detto_no": False, "detto_no_sicuro": False, "non_scrivere": False, "autorisposta": False,
            "analisi_gia_letta": False, "girato_a": [], "si_sicuro": False, "lettura_id": None,
            "lettura_stato": None, "fonte": None, "dubbio": False, "frase": "", "permanente_ok": False}
        return {**base, **f, "analisi_ricevuta": bool(p.get("analysis_sent")) or f["analisi_gia_letta"]}
    # senso_v2 spento: il vecchio decide (regex + lettore con «basta che uno dei due»), il nuovo in ombra.
    # La lettura e' UNA: il vecchio lettore usa le probabilita' della stessa chiamata, non ne paga un'altra.
    lettore = cervello_decisioni((lett or {}).get("risposte"))
    # una pec citata senza un verbo di rimando («scrivete a», «inviate a») e' quasi
    # sempre la firma legale, non un passaggio di persona (1/10: la pec in firma di una
    # lead bloccava un «sarei interessata a ricevere il documento»)
    # un indirizzo in firma non e' un «ci ha girato a», lo e' solo con un verbo di
    # rimando davanti. Vale per le pec (qualunque provider col «pec» nel dominio:
    # legalmail, interfreepec, arubapec... due casi del 5/10) e per l'indirizzo
    # personale del mittente stesso (il suo cognome nel local-part, 5/10).
    # (12/10 sera: PEC e il verbo di rimando stanno in senso.py, una regola un posto; questo ramo
    # vecchio se ne va con la pulizia del passo 9)
    _tok = {t for t in re.split(r"[^a-z]+", f"{p.get('name') or ''} {(p.get('email') or '').split('@')[0]}".lower()) if len(t) >= 4}
    def _rimando_vero(e, t):
        locale, _, dominio = e.partition("@")
        firma = ("pec" in dominio or any(e.endswith(x) or x in e for x in PEC)
                 or any(tk in locale for tk in _tok))
        return not firma or rimando_prima(t, e)
    # 5/10: «potete inviare una mail a ...@gmail» stava nel disclaimer privacy della
    # firma, e il verbo convinceva la regex. Gli indirizzi si cercano solo nel
    # testo suo vero (solo_suo), come gia' per NON_TOCCARE (28/9): la miglioria si
    # applica ovunque.
    suo = solo_suo(testo)
    girato = sorted({e.lower() for e in EMAIL.findall(suo) if _rimando_vero(e.lower(), suo)
                     if e.lower() not in mie and not any(n in e.lower() for n in NOSTRI) and e.lower().split("@")[-1] != dom} |
                    {e.lower() for e in EMAIL.findall(suo) if e.lower().split("@")[-1] == dom and e.lower() not in mie})
    return {
        **base,
        "analisi_ricevuta": bool(p.get("analysis_sent")) or bool(GIA_LETTA.search(testo)) or ("analisi" in nostre_testo and bool(dopo)),
        "analisi_gia_letta": bool(GIA_LETTA.search(testo)),
        # 28/9: solo le sue righe. La nostra mail citata sotto contiene le nostre
        # frasi, e una di quelle poteva far sembrare che avesse detto di no.
        "detto_no": frena(DETTO_NO.search(solo_suo(testo)), lettore, ("no", "non_scrivere")),
        # il no CONCORDE: regex E modello sicuro insieme. Serve per aggiornare la classe
        # da soli (5/10): un no cosi' certo non si scarica su Dre.
        "detto_no_sicuro": bool(DETTO_NO.search(solo_suo(testo))) and bool(
            lettore and lettore.get("etichetta") in ("no", "non_scrivere") and not lettore.get("dubbio")),
        "autorisposta": frena(AUTORISPOSTA.search(testo[:1200]), lettore, ("fuori_ufficio",)),
        "non_scrivere": frena(False, lettore, ("non_scrivere",)),
        "girato_a": girato[:3],
        "ombra": ombra(lett) if lett else None,
    }


def _quando(s):
    """Un orario del database o di Smartlead come datetime con fuso (senza fuso = UTC). None se manca."""
    if not s:
        return None
    try:
        d = datetime.datetime.fromisoformat(str(s).strip().replace("Z", "+00:00").replace(" ", "T"))
    except ValueError:
        return None
    return d if d.tzinfo else d.replace(tzinfo=datetime.timezone.utc)


def _decidi_salvata(riga, p):
    """La decisione di una lettura gia' salvata, ricalcolata adesso con le soglie di adesso (gratis)."""
    import senso as S
    s = soglie_lettore()
    if riga.get("decisione_dre"):
        return S.giudica(riga.get("risposte"), riga.get("rete") or [], s, dre=riga["decisione_dre"])
    r = riga.get("risposte")
    if not r:
        return riga.get("decisione") or S.giudica(None, riga.get("rete") or [], s)
    mie = [p.get("email"), *(p.get("email_alt") or [] if isinstance(p.get("email_alt"), list) else [p.get("email_alt")])]
    rv, problemi = S.verifica(r, riga.get("testo_suo") or "", s, mie)
    dec = S.giudica(rv, riga.get("rete") or [], s, problemi=problemi)
    sec = riga.get("seconda")
    if dec.get("serve_seconda") and sec and sec.get("campo") == (dec.get("contesa") or {}).get("campo"):
        dec = S.giudica(rv, riga.get("rete") or [], s, seconda=sec, problemi=problemi)
    return dec


def per_il_postino(az, p, viva=None, nata_il=None, segna=None):
    """Cosa sa il postino (manda.py) del senso, al momento di mandare: (detto_no, blocco).
    Con senso_v2 spento resta il valore scritto nella bozza (com'era). Acceso, la lettura si
    RILEGGE (gratis se gia' fatta): se Dre ha sciolto un dubbio vale la sua scelta, un grave
    non sciolto ferma, e una sua mail piu' nuova della bozza ferma e lo dice (12/10).

    12/10 sera, dagli scettici: prima la mail «piu' nuova» si riconosceva dal GIORNO. Un «ci ho
    ripensato, cancellatemi» scritto lo stesso giorno della bozza non si vedeva, e la bozza partiva.
    Ora si guarda SEMPRE l'ultima sua mail, sia quella nel CRM sia quella viva su Smartlead (`viva`,
    letta dal postino un attimo prima di mandare: il sync puo' non averla ancora portata nel CRM),
    e si confronta il TESTO (l'impronta della lettura su cui e' nata la bozza) e l'ORA, non il giorno.
      viva     {at, body} l'ultima sua risposta su Smartlead, gia' pulita (sync_v2.corpo_pulito)
      nata_il  quando e' nata la bozza (proposte.at): serve alle bozze che non portano l'ora
      segna    un dict che, se la bozza si ferma perche' ha riscritto, riceve l'impronta della mail
               nuova: il postino la scrive nella bozza, e se Dre la riapprova DOPO, l'ha vista."""
    import senso as S
    let = (az or {}).get("lettura") or {}
    if not senso_acceso():
        return bool(let.get("detto_no")), None
    cand = []
    try:
        for x in sb("GET", f"/rest/v1/interactions?select=id,at,body,ref&prospect_id=eq.{p['id']}&kind=eq.email_in&order=at.desc&limit=3") or []:
            if not _segnaposto(x.get("body")):
                cand.append(x)
                break
    except Exception:                                        # noqa: BLE001
        pass
    if viva and not _segnaposto(viva.get("body")):
        cand.append({"at": viva.get("at"), "body": viva.get("body"), "da": "smartlead"})
    lid = let.get("lettura_id") or (let.get("ombra") or {}).get("lettura_id")
    riga_b = None
    if lid:
        try:
            riga_b = (sb("GET", f"/rest/v1/letture?select=*&id=eq.{lid}") or [None])[0]
        except Exception:                                    # noqa: BLE001
            riga_b = None
    if not cand and not riga_b:
        return bool(let.get("detto_no")), None
    lett, nuova, quando_mail = None, False, None
    if cand:
        ultima = max(cand, key=lambda x: _quando(x.get("at")) or datetime.datetime.min.replace(tzinfo=datetime.timezone.utc))
        quando_mail = _quando(ultima.get("at"))
        lett = senso(p, ultima, attuale=p.get("classificazione"))
        if not riga_b or not lett.get("impronta") or lett.get("impronta") != riga_b.get("impronta"):
            # una mail diversa da quella della bozza: e' piu' nuova della bozza? (l'ora, non il giorno)
            soglia = _quando(let.get("ultima_loro_at")) or _quando(nata_il)
            if soglia and quando_mail:
                nuova = quando_mail > soglia
            else:                                            # senza un'ora: nel dubbio e' nuova, se e' dello stesso giorno o dopo
                nuova = (ultima.get("at") or "")[:10] >= (let.get("ultima_loro_il") or "~")[:10]
    if nuova:
        dec = lett.get("decisione") or {}
        frase = (dec.get("frase") or " ".join((lett.get("testo_suo") or "").split()))[:100]
        if dec.get("grave") and not S.permanente_ok(dec):
            return True, f"ha riscritto dopo la bozza e forse chiede di non essere contattato («{frase}»): rispondi alla domanda in Posta"
        if dec.get("grave"):
            return True, f"ha riscritto dopo la bozza e chiede di non essere contattato («{frase}»)"
        if dec.get("etichetta") == "si" and S.permanente_ok(dec):
            return False, None
        vista = let.get("riletta") or {}
        appr = _quando((az or {}).get("approvata_il"))
        if vista.get("impronta") and vista.get("impronta") == lett.get("impronta") and appr and _quando(vista.get("il")) and appr > _quando(vista.get("il")):
            return dec.get("etichetta") in ("no", "non_scrivere"), None      # l'ha vista Dre e l'ha riapprovata
        if segna is not None:
            segna["impronta"] = lett.get("impronta")
        return True, f"ha riscritto dopo che la bozza era nata («{frase}»): la bozza risponde alla mail di prima, rileggila tu"
    if riga_b and (not lett or lett.get("impronta") != riga_b.get("impronta")):
        dec = _decidi_salvata(riga_b, p)                     # la lettura della mail su cui e' nata la bozza
    else:
        dec = lett.get("decisione") or {}
    if dec.get("grave") and not S.permanente_ok(dec):
        return True, "c'e' un dubbio sul «non scrivetemi» non ancora sciolto: rispondi alla domanda in Posta"
    if dec.get("grave"):
        return True, "ha chiesto di non essere contattato"
    if dec.get("stato") in ("senza_ai", "senza_regole"):
        return True, "l'AI non ha letto la sua ultima mail: non mando alla cieca"
    return dec.get("etichetta") in ("no", "non_scrivere"), None


def cervello_decisioni(r):
    """Le soglie di prima (cervello.decisioni) sulla lettura di adesso. None = nessuna opinione."""
    if not r:
        return None
    try:
        import cervello
        return cervello.decisioni(_per_il_vecchio(r))
    except Exception:                                        # noqa: BLE001
        return None


# I GRUPPI DELLA CODA: chi li mette in coda (followup.py, ripresa.py) non scrive
# piu' niente: dice solo «questo va ricontattato, per questo motivo». Scrive il motore.
GRUPPI = ("RIPRESA", "RINVIO SCADUTO", "RICONTATTO OOO", "FOLLOW UP 1", "MINI FOLLOW UP")


def regola_dura(gruppo, f, classificazione=None):
    """Torna ('salta', motivo) se la bozza non va scritta, ('fermati', motivo) se va scritta
    ma la deve guardare Dre, None se si procede. Sono i quattro errori del 25/9, in codice."""
    if not f["ultima_loro"]:
        # 4/10: un lead ha risposto con la sola firma, niente testo leggibile (anche su
        # Smartlead). Non si scrive alla cieca, ma non si resta appesi in silenzio ogni giro:
        # va messo UNA volta davanti a Dre, che apre il thread e decide.
        return ("fermati", "ha risposto senza testo leggibile (solo firma): guarda tu il thread e dimmi")
    # 12/10, senso_v2 acceso: una lettura in dubbio, senza AI o senza regole ferma e lo dice,
    # e MAI «salta»: «salta» chiude l'attesa e la coda (CHIUDONO), un effetto che vuole l'AI sicura
    stato = f.get("lettura_stato")
    if stato in ("dubbio_a_dre", "senza_ai", "senza_regole"):
        # 12/10 sera: «te l'ho chiesto in Posta» solo se la domanda c'e' davvero (il caso c del piano,
        # un dubbio su chi ha gia' una bozza, la domanda non la fa: la porta la bozza stessa)
        perche = {"dubbio_a_dre": "la lettura e' in dubbio, te l'ho chiesto in Posta" if f.get("chiesto_a_dre")
                  else "la lettura e' in dubbio: guarda tu la sua mail e decidi",
                  "senza_ai": "l'AI non ha letto la sua ultima mail", "senza_regole": "le soglie del lettore nel Manuale non si leggono"}[stato]
        return ("fermati", perche + (f": «{f['frase'][:120]}»" if f.get("frase") else ""))
    nuovo = stato is not None
    if gruppo == "RIPRESA":
        if f["scritto_dopo_di_lei"]:
            return ("salta", f"gli abbiamo già scritto {f['scritto_dopo_di_lei']} volte dopo la sua mail: «la mail non era partita» sarebbe una bugia")
        if f["analisi_ricevuta"]:
            return ("salta", "ha già ricevuto l'analisi: la ripresa promette un'analisi che ha già")
    if gruppo in ("RINVIO SCADUTO", "RICONTATTO OOO", "FOLLOW UP 1", "MINI FOLLOW UP") and f["analisi_gia_letta"] and gruppo != "MINI FOLLOW UP":
        return ("salta", "dice di aver già letto l'analisi: non gliela si rimanda come nuova")
    if nuovo and f.get("non_scrivere"):
        if f.get("permanente_ok"):
            return ("salta", f"ha chiesto di non essere contattato: nessun ricontatto («{(f.get('frase') or '')[:120]}»)")
        return ("fermati", "potrebbe chiedere di non essere contattato: te l'ho chiesto in Posta")
    if f["detto_no"]:
        if gruppo in GRUPPI and (not nuovo or f.get("detto_no_sicuro")):
            return ("salta", "nella sua ultima mail dice di no: nessun ricontatto")
        if gruppo in GRUPPI:
            return ("fermati", f"nella sua ultima mail sembra dire di no (in dubbio): «{(f.get('frase') or '')[:120]}»")
        if classificazione not in ("negativo",):
            dubbio = f" (la lettura e' in dubbio: «{(f.get('frase') or '')[:120]}»)" if nuovo and not f.get("detto_no_sicuro") else ""
            return ("fermati", "nella sua ultima mail sembra dire di no, ma la classe non lo dice" + dubbio)
    if f["autorisposta"] and f.get("casella_di_servizio"):
        return ("salta", "casella di servizio che risponde con un automatismo (ticket): non c'è nessuno a cui scrivere")
    if f["autorisposta"] and gruppo != "RICONTATTO OOO" and classificazione != "ooo":
        return ("fermati", "l'ultima mail loro è un'autorisposta, non una persona")
    if f["autorisposta"] and gruppo == "RIPRESA":
        return ("salta", "l'ultima mail loro è un'autorisposta: non è una ripresa, semmai un dopo le ferie")
    return None


def coerenza(f, bozza, gruppo=None):
    """LA SECONDA TESTA. Un modello diverso legge loro / noi / bozza e dice COERENTE o
    INCOERENTE con il motivo. Non scrive, giudica. Nel dubbio, INCOERENTE."""
    try:
        import cervello
        prompt = f"""Sei la SECONDA TESTA di Studio Galilei. Un altro sistema ha scritto una mail a un'azienda.
Il tuo lavoro e' UNO: dire se la bozza e' coerente con quello che l'azienda ci ha scritto per ultimo
e con quello che noi le abbiamo gia' scritto. Non correggi, non riscrivi: giudichi.
{"REGOLA DEL GIGANTE BUONO (decisa da Dre, 1-2/10): a chi ha detto no si lascia comunque l'analisi gia' pronta, un saluto cordiale, la porta aperta e il LINK del calendario in fondo, SENZA proporre una data ne' chiedere una call. Questo NON e' ignorare il no: e' la regola voluta. Boccia solo se la bozza propone una data, insiste, o ignora quello che hanno detto." if (gruppo or '').upper().startswith('GIGANTE') or gruppo == 'INT-GB' else ''}

L'ULTIMA MAIL LORO ({f['ultima_loro_il'] or 'data ignota'}):
{f['ultima_loro'] or '(nessuna)'}

L'ULTIMA MAIL NOSTRA ({f['ultima_nostra_il'] or 'mai'}), {'mandata DOPO la loro' if f['scritto_dopo_di_lei'] else 'mandata PRIMA della loro'}:
{f['ultima_nostra'] or '(nessuna)'}

FATTI CHE IL CODICE HA VERIFICATO: analisi gia' ricevuta={f['analisi_ricevuta']}, dice di averla letta={f['analisi_gia_letta']},
ha detto no={f['detto_no']}, autorisposta={f['autorisposta']}, ci ha girato a={f['girato_a'] or 'nessuno'}, gruppo={gruppo or 'risposta normale'},
la mail parte a={f.get('destinatario') or 'lo stesso indirizzo del thread'}.

LA BOZZA CHE STIAMO PER MANDARE:
{bozza}

E' INCOERENTE se: risponde a qualcosa che non hanno detto; dice «la mail non era partita» quando noi avevamo
gia' scritto dopo la loro; promette o allega l'analisi come nuova a chi dice di averla gia' letta; parla a
un'autorisposta come a una persona (salvo il gruppo RICONTATTO OOO, che e' fatto apposta); ignora un no;
sbaglia nome o azienda; usa un indirizzo email come se fosse il nome di una persona; dice «metto in copia»
o «grazie per il passaggio» quando la mail parte direttamente al contatto nuovo; ripete parola per parola una
cosa che avevamo gia' scritto; risponde a una domanda precisa senza rispondere; nei gruppi (ripresa, rinvio,
dopo le ferie, follow-up) aggiunge uno slot o righe che il template di Dre non ha. E' COERENTE se un lettore attento, che vede tutto il filo, la troverebbe naturale.

Rispondi SOLO con una riga: «COERENTE» oppure «INCOERENTE: motivo in venti parole»."""
        modello = "gpt-5" if cervello.FORNITORE == "openai" else None
        r = " ".join((cervello._chiedi(prompt, modello) or "").split()).strip()
        if r.upper().startswith("COERENTE"):
            return "COERENTE", ""
        return "INCOERENTE", (r.split(":", 1)[1].strip() if ":" in r else r)[:200]
    except Exception as e:                                   # noqa: BLE001
        return "INCOERENTE", f"la seconda testa non ha risposto ({str(e)[:60]})"


def leggi(p):
    """Tutto insieme: il filo e i fatti. E' quello che ogni bozza porta con se'."""
    righe = filo(p)
    return righe, ha_gia(p, righe)


if __name__ == "__main__":
    import json
    email = sys.argv[1] if len(sys.argv) > 1 else ""
    p = (sb("GET", f"/rest/v1/prospects?select=id,email,email_alt,company,name,analysis_sent,campaign_id,lead_id&email=eq.{email}") or [None])[0]
    if not p:
        sys.exit("uso: lettura.py <email>")
    righe, f = leggi(p)
    for r in righe:
        print(f"{(r.get('at') or '')[:16]} {r['kind']:9} {' '.join((r.get('body') or '').split())[:120]}")
    print(json.dumps(f, ensure_ascii=False, indent=1))
