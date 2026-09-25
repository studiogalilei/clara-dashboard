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
from stanza import sb                                       # noqa: E402

AUTORISPOSTA = re.compile(r"out of (the )?office|fuori (ufficio|sede)|risposta automatica|automatic reply|auto-?reply|"
                          r"sar[òo] (assente|fuori)|assente (dal|fino|per)|rientr(o|er[òo]) (il|in|dal)|in ferie|ferie fino|"
                          r"non sono in ufficio|away from|chiusura estiva|chiusi per ferie|ufficio (e'|è) chiuso|"
                          r"avvenuta ricezione|provvederemo ad evader|conferm(a|iamo) (di|la|l')\s*(avvenuta )?ricezione|"
                          r"abbiamo ricevuto la (sua|vostra) (mail|email|richiesta|comunicazione)|questo (e'|è) un messaggio automatico|do not reply|non rispondere a questa|"
                          r"presa in carico|(richiesta|ticket|segnalazione) (e'|è) stat[ao] (inoltrat|ricevut|registrat|apert)|ticket (id|nr|n\.|numero)|id nr|numero (della|di) pratica|"
                          r"^gentile cliente|per poter gestire la (sua|vostra )?richiesta|(le|ti) sar[àa] notificat|riceverai una risposta|will get back to you", re.I | re.M)
DETTO_NO = re.compile(r"non (siamo|sono|siam) interessat|non (ci|mi) interessa|no,? grazie|non fa per noi|"
                      r"non (abbiamo|ho) (bisogno|necessit|interesse)|abbiamo gi[àa] (un|una|il|la|chi|qualcuno)|"
                      r"non (vogliamo|voglio|desider)|non (ci|mi) contatt|rimuov|cancell(are|atemi|ami)|declin|"
                      r"non (e'|è) di (nostro|mio) interesse|non (rientra|ci rientra) nei (nostri|miei)|non (ne )?abbiamo (la )?necessit|"
                      r"non (siamo|sono) alla ricerca|non (ci|mi) serve|non (e'|è) (il|un) (nostro|mio) (obiettivo|interesse)", re.I)
GIA_LETTA = re.compile(r"(ho|abbiamo|avevo|avevamo) (letto|visto|ricevuto|guardato|dato un.occhiata|analizzato)[^.\n]{0,40}analisi|"
                       r"grazie (per|dell)[^.\n]{0,20}analisi|l.analisi (che|ricevuta|inviata)|"
                       r"(per il|del) materiale (che|ricevuto|inviato)|materiale che (mi|ci) ha (trasmesso|inviato|mandato)|"
                       r"(letto|visto|guardato) (il|la) (documento|report|analisi|presentazione)", re.I)
SERVIZIO = re.compile(r"^(assistenza|supporto|support|helpdesk|help|ticket|noreply|no-reply|donotreply|customercare|customer\.?service|servizioclienti)@", re.I)
EMAIL = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+", re.I)
NOSTRI = ("studiogalilei", "galilei", "odyn", "smartlead")


def _segnaposto(b):
    b = (b or "").strip()
    return len(b) < 60 or b.lower().startswith("risposta ricevuta") or "smartlead" in b.lower()[:80]


def _smartlead(p):
    """Tutto il thread da Smartlead (la fonte vera), come righe kind/at/body."""
    try:
        import manda
        from sync_v2 import corpo_pulito
    except Exception:
        return []
    try:
        cid, lid, _ = manda.thread(p)
        if not cid:
            return []
        h = manda.sl("GET", f"/campaigns/{cid}/leads/{lid}/message-history") or {}
    except Exception as e:                                   # noqa: BLE001
        print(f"    (thread Smartlead non letto: {str(e)[:60]})")
        return []
    out = []
    for m in h.get("history") or []:
        corpo = corpo_pulito(m.get("email_body"))
        out.append({"kind": "email_in" if m.get("type") == "REPLY" else "email_out",
                    "at": (m.get("time") or "")[:19], "body": corpo[:3000], "da": "smartlead"})
    return out


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
                    if len(v["body"].strip()) >= 25:
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


def ha_gia(p, righe):
    """I fatti che si leggono dal filo senza chiedere a nessuno."""
    loro = [r for r in righe if r["kind"] == "email_in" and not _segnaposto(r.get("body"))]
    ultima_loro = loro[-1] if loro else None
    nostre = [r for r in righe if r["kind"] in ("email_out", "followup", "analisi")]
    dopo = [r for r in nostre if ultima_loro and (r.get("at") or "") > (ultima_loro.get("at") or "")]
    ultima_nostra = nostre[-1] if nostre else None
    testo = (ultima_loro or {}).get("body") or ""
    nostre_testo = " ".join((r.get("body") or "") for r in nostre).lower()
    alt = p.get("email_alt") or []
    alt = alt if isinstance(alt, list) else [alt]
    mie = {(p.get("email") or "").lower(), *[str(a).lower() for a in alt if a]}
    dom = (p.get("email") or "").split("@")[-1].lower()
    girato = sorted({e.lower() for e in EMAIL.findall(testo)
                     if e.lower() not in mie and not any(n in e.lower() for n in NOSTRI) and e.lower().split("@")[-1] != dom} |
                    {e.lower() for e in EMAIL.findall(testo) if e.lower().split("@")[-1] == dom and e.lower() not in mie})
    return {
        "ultima_loro": " ".join(testo.split())[:600], "ultima_loro_il": (ultima_loro or {}).get("at", "")[:10],
        "ultima_nostra": " ".join(((ultima_nostra or {}).get("body") or "").split())[:400], "ultima_nostra_il": (ultima_nostra or {}).get("at", "")[:10],
        "scritto_dopo_di_lei": len(dopo),
        "analisi_ricevuta": bool(p.get("analysis_sent")) or bool(GIA_LETTA.search(testo)) or ("analisi" in nostre_testo and bool(dopo)),
        "analisi_gia_letta": bool(GIA_LETTA.search(testo)),
        "detto_no": bool(DETTO_NO.search(testo)),
        "autorisposta": bool(AUTORISPOSTA.search(testo[:1200])),
        "casella_di_servizio": bool(SERVIZIO.match(p.get("email") or "")),
        "destinatario": (alt[0] if alt and alt[0] else None),
        "girato_a": girato[:3],
        "letto_il": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
    }


# I GRUPPI DELLA CODA: chi li mette in coda (followup.py, ripresa.py) non scrive
# piu' niente: dice solo «questo va ricontattato, per questo motivo». Scrive il motore.
GRUPPI = ("RIPRESA", "RINVIO SCADUTO", "RICONTATTO OOO", "FOLLOW UP 1", "MINI FOLLOW UP")


def regola_dura(gruppo, f, classificazione=None):
    """Torna ('salta', motivo) se la bozza non va scritta, ('fermati', motivo) se va scritta
    ma la deve guardare Dre, None se si procede. Sono i quattro errori del 25/9, in codice."""
    if not f["ultima_loro"]:
        return ("salta", "non ho l'ultima mail loro: senza lettura non si scrive")
    if gruppo == "RIPRESA":
        if f["scritto_dopo_di_lei"]:
            return ("salta", f"gli abbiamo già scritto {f['scritto_dopo_di_lei']} volte dopo la sua mail: «la mail non era partita» sarebbe una bugia")
        if f["analisi_ricevuta"]:
            return ("salta", "ha già ricevuto l'analisi: la ripresa promette un'analisi che ha già")
    if gruppo in ("RINVIO SCADUTO", "RICONTATTO OOO", "FOLLOW UP 1", "MINI FOLLOW UP") and f["analisi_gia_letta"] and gruppo != "MINI FOLLOW UP":
        return ("salta", "dice di aver già letto l'analisi: non gliela si rimanda come nuova")
    if f["detto_no"]:
        if gruppo in GRUPPI:
            return ("salta", "nella sua ultima mail dice di no: nessun ricontatto")
        if classificazione not in ("negativo",):
            return ("fermati", "nella sua ultima mail sembra dire di no, ma la classe non lo dice")
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
