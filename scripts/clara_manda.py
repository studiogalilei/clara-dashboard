"""IL POSTINO DEL DESK (4/11/2026, notte).

Manda SOLO le decisioni che Dre ha approvato nel Desk (clara_decisioni.stato = approvata), nel thread
vero di Smartlead, dalla casella della campagna, con l'analisi e la presentazione quando la mossa le
prevede. Riusa i pezzi del postino di sempre (manda.py: il filo, l'HTML, i link freschi, a chi
rispondere) e il suo lucchetto: una decisione passa a «in_invio» solo se e' ancora «approvata», e solo
chi riesce a scriverlo manda. Poi la ricevuta: al giro dopo rilegge il filo e segna «verificata» quando
la mail risulta davvero partita.

Non decide niente: il testo e' quello lasciato da Dre (testo_finale) o quello di Clara.

  python3 scripts/clara_manda.py            il giro (ogni 5 minuti dal direttore, o su richiesta dal Desk)
  python3 scripts/clara_manda.py --prova    mostra cosa manderebbe, non manda
"""
import datetime
import json
import os
import sys
import urllib.request
import zoneinfo

QUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, QUI)
import manda  # noqa: E402
from stanza import sb, contattabile, env  # noqa: E402

PROVA = os.environ.get("PROVA") == "1" or "--prova" in sys.argv
ROMA = zoneinfo.ZoneInfo("Europe/Rome")
MAX_PER_GIRO = 12
ATTESA_ANALISI_ORE = 24
LUCCHETTO_APPESO_MIN = 30
CON_ANALISI = {"send_analysis"}
CON_TESTO = {"send_analysis", "reply", "offer_slots", "book_meeting", "escalate"}   # escalate parte solo se Dre la approva nel Desk


def adesso():
    return datetime.datetime.now(datetime.timezone.utc)


def _quando(iso):
    return datetime.datetime.fromisoformat(str(iso).replace("Z", "+00:00"))


def _peso(url):
    try:
        with urllib.request.urlopen(urllib.request.Request(url, method="HEAD"), timeout=30) as r:
            return int(r.headers.get("Content-Length") or 0)
    except Exception:                                            # noqa: BLE001
        return 0


def allegati(p, d):
    """[(nome, url, peso)] da allegare, o una stringa col motivo per cui non si puo' mandare."""
    fuori = []
    azienda = p.get("company") or p.get("name") or p["email"]
    prima_volta = not p.get("analysis_sent")
    if d["mossa"] in CON_ANALISI:
        if not p.get("analysis_pdf"):
            return "aspetta l'analisi"
        url = manda.link_fresco(p["analysis_pdf"])
        peso = _peso(url)
        if not peso:
            return "il PDF dell'analisi non si apre"
        fuori.append({"file_name": f"Analisi Google Ads - {azienda}.pdf"[:120], "file_url": url, "file_type": "application/pdf", "file_size": peso})
    if d["mossa"] in CON_ANALISI and prima_volta:
        url_p = manda.link_fresco(f"{env('VITE_SUPABASE_URL')}/storage/v1/object/sign/vault/modelli/sg-presentazione.pdf")
        peso_p = _peso(url_p)
        if not peso_p:
            return "la presentazione non si apre dal bucket"
        fuori.append({"file_name": "Presentazione Studio Galilei.pdf", "file_url": url_p, "file_type": "application/pdf", "file_size": peso_p})
    return fuori


def ferma(d, motivo, stato="proposta"):
    """La decisione torna a Dre (proposta) con il motivo scritto, oppure resta approvata in attesa."""
    print(f"  {motivo}")
    if PROVA:
        return
    sb("PATCH", f"/rest/v1/clara_decisioni?id=eq.{d['id']}", {"stato": stato, "errore": motivo[:300]}, {"Prefer": "return=minimal"})


def intestazione(testo):
    """La testa «A: …» / «Cc: …» / «Oggetto: …» che Clara scrive quando il destinatario cambia (una o due righe),
    separata dal corpo. {"a", "cc": [...], "oggetto", "corpo"}; a=None se non c'e'."""
    import re
    righe = (testo or "").strip().split("\n")
    a, cc, oggetto, i = None, [], None, 0
    if righe and righe[0].lower().startswith("a:") and "@" in righe[0]:
        trovati = re.findall(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+", righe[0])
        a, cc, i = (trovati[0] if trovati else None), trovati[1:], 1
        if a and i < len(righe) and righe[i].lower().startswith("cc:"):
            cc += re.findall(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+", righe[i])
            i += 1
    if a and i < len(righe) and righe[i].lower().startswith("oggetto:"):
        oggetto = righe[i].split(":", 1)[1].strip()
        i += 1
    if not a:
        return {"a": None, "cc": [], "oggetto": None, "corpo": (testo or "").strip()}
    return {"a": a, "cc": cc, "oggetto": oggetto, "corpo": "\n".join(righe[i:]).strip()}


def prendi(d):
    r = sb("PATCH", f"/rest/v1/clara_decisioni?id=eq.{d['id']}&stato=eq.approvata",
           {"stato": "in_invio", "errore": None}, {"Prefer": "return=representation"}) or []
    return bool(r)


DURATA_CALL_MIN = 45


def invito(p, d, a):
    """LA CALL PRENOTATA FINISCE NEL CALENDARIO (4/11). Un book_meeting crea l'evento nel calendario di Dramane
    con il Meet e il lead invitato: l'invito glielo manda Google, la conferma la scrive Clara. Se l'evento non si
    crea la mail resta ferma (non si promette un invito che non parte). Torna il link del Meet, o un errore (str).
    Idempotente: il link gia' creato sta in invio.invito e non si rifa'."""
    gia = (d.get("invio") or {}).get("invito")
    if gia:
        return gia
    quando = (d.get("appuntamento") or "").strip()
    if not quando:
        return "prenotazione senza l'orario confermato: tocca No e scrivi a Clara l'orario giusto, la rifà"
    try:
        inizio = datetime.datetime.fromisoformat(quando)
    except ValueError:
        return f"orario della prenotazione illeggibile ({quando[:30]}): tocca No e scrivi a Clara l'orario giusto"
    inizio = inizio.replace(tzinfo=ROMA) if inizio.tzinfo is None else inizio.astimezone(ROMA)
    if inizio < adesso():
        return f"la prenotazione è nel passato ({inizio.strftime('%d/%m %H:%M')}): tocca No e scrivi a Clara l'orario giusto"
    fine = inizio + datetime.timedelta(minutes=DURATA_CALL_MIN)
    azienda = p.get("company") or p.get("name") or a
    corpo = {"summary": f"Conoscitiva {azienda}"[:200],
             "description": f"Call conoscitiva con {azienda}, fissata da Clara.",
             "start": {"dateTime": inizio.isoformat(), "timeZone": "Europe/Rome"},
             "end": {"dateTime": fine.isoformat(), "timeZone": "Europe/Rome"},
             "attendees": [{"email": a}],
             "conferenceData": {"createRequest": {"requestId": f"clara-{d['id']}", "conferenceSolutionKey": {"type": "hangoutsMeet"}}}}
    if PROVA:
        print(f"    [prova] invito {inizio.strftime('%d/%m %H:%M')} a {a}")
        return "prova"
    try:
        import calendario_sg
        from google_api import g
        ev = g("POST", f"{calendario_sg.CAL}/calendars/primary/events?conferenceDataVersion=1&sendUpdates=all",
               corpo, email=calendario_sg.PADRONE)
    except Exception as e:                                       # noqa: BLE001
        return f"Google non crea l'evento ({str(e)[:120]}): manda tu l'invito dal calendario e tocca «Invito fatto, manda la conferma»"
    link = (ev or {}).get("hangoutLink") or (ev or {}).get("htmlLink") or "creato"
    sb("PATCH", f"/rest/v1/clara_decisioni?id=eq.{d['id']}", {"invio": {**(d.get("invio") or {}), "invito": link, "evento": (ev or {}).get("id")}})
    return link


def manda_una(d):
    p = (sb("GET", f"/rest/v1/prospects?select=id,email,email_alt,company,name,campaign_id,lead_id,analysis_pdf,analysis_sent,"
                   f"fuori,stage,pipeline_stage,no_followup,classificazione,enriched&id=eq.{d['prospect_id']}") or [None])[0]
    if not p:
        return ferma(d, "scheda del lead non trovata")
    azienda = p.get("company") or p.get("name") or p["email"]
    testo = (d.get("testo_finale") or d.get("testo") or "").strip()
    if d["mossa"] not in CON_TESTO or not testo:
        return ferma(d, f"{azienda}: la mossa «{d['mossa']}» non manda una mail")
    if not contattabile(p):
        return ferma(d, f"{azienda}: non più un lead (cliente, perso, in pipeline o niente follow-up): non mando", "scartata")
    cid, lid, ultima = manda.thread(p)
    if not ultima:
        return ferma(d, f"{azienda}: non trovo il suo filo su Smartlead, da qui non può partire: se vuoi rispondere tu, «Me ne occupo io»")
    # il lead ha scritto dopo la decisione? allora la decisione e' vecchia: torna a Dre, e Clara ne fa una nuova
    if _quando(ultima.get("time")) > _quando(d["risposta_il"]) + datetime.timedelta(minutes=3):
        return ferma(d, f"{azienda}: ha scritto di nuovo dopo questa decisione: rileggi", "superata")
    # abbiamo gia' risposto noi dopo quella mail (dal sistema vecchio o a mano)? non si manda due volte
    h = {}
    try:
        h = manda.sl("GET", f"/campaigns/{cid}/leads/{lid}/message-history") or {}
        nostre_dopo = [m for m in (h.get("history") or []) if m.get("type") != "REPLY"
                       and _quando(m.get("time")) > _quando(d["risposta_il"]) + datetime.timedelta(minutes=3)]
    except Exception:                                            # noqa: BLE001
        nostre_dopo = []
    if nostre_dopo:
        return ferma(d, f"{azienda}: gli abbiamo già scritto dopo quella mail ({str(nostre_dopo[-1].get('time'))[:16]}): non mando due volte", "superata")
    att = allegati(p, d)
    if isinstance(att, str):
        if att == "aspetta l'analisi":
            ore = (adesso() - _quando(d.get("approvata_il") or d["creato_il"])).total_seconds() / 3600
            if ore > ATTESA_ANALISI_ORE:
                return ferma(d, f"{azienda}: aspetta l'analisi da {int(ore)} ore e non arriva: tocca No e scrivi a Clara «manda senza l'analisi», la riscrive")
            print(f"  {azienda}: aspetto l'analisi ({int(ore * 60)} min), riprovo al giro dopo")
            return None
        return ferma(d, f"{azienda}: {att}: tocca No e scrivi a Clara «manda senza l'analisi», la riscrive")
    a = (p.get("email_alt") or [None])[0] or manda.chi_ha_risposto(ultima, p["email"]) or p["email"]
    corpo = {"email_stats_id": ultima.get("stats_id") or ultima.get("email_stats_id"),
             "email_body": manda.in_html(testo),
             "reply_message_id": ultima.get("message_id"),
             "reply_email_time": ultima.get("time"),
             "reply_email_body": ultima.get("email_body") or "",
             "add_signature": True, "to_email": a}
    # «A: …» (e «Cc: …», sulla stessa riga o sotto) in testa al testo di Clara: il destinatario l'ha indicato
    # il lead (es. il marketing, la sede locale). Si accetta un indirizzo dello stesso dominio o uno che il
    # lead ha scritto lui nel filo; altrimenti la mail resta ferma, non va a chi ha detto di non essere la persona
    testa = intestazione(testo)
    if testa["a"]:
        dominio = p["email"].split("@")[-1].lower()
        nel_filo = (" ".join((m.get("email_body") or "") for m in (h.get("history") or []) if m.get("type") == "REPLY")
                    or (ultima.get("email_body") or "")).lower()
        tutti = [testa["a"]] + testa["cc"]
        # 4/11: se l'ha approvata Dre (ha visto il destinatario) non si ferma piu'
        if d.get("approvata_da") == "Dre" or all(i.split("@")[-1].lower() == dominio or i.lower() in nel_filo for i in tutti):
            corpo["to_email"] = testa["a"]
            if testa["cc"]:
                corpo["cc"] = ",".join(testa["cc"])
            corpo["email_body"] = manda.in_html(testa["corpo"])
            a = corpo["to_email"]
        else:
            return ferma(d, f"{azienda}: Clara vuole scrivere a un indirizzo che il lead non ha dato ({testa['a']}): guarda tu")
    if att:
        corpo["attachments"] = att
    if d["mossa"] == "book_meeting":
        inv = invito(p, d, a)
        if inv.startswith(("prenotazione", "orario", "la prenotazione", "Google")):   # i motivi: ognuno dice il gesto da fare nel Desk
            return ferma(d, f"{azienda}: {inv}")
    print(f"  {azienda} → {a}" + (f" (cc {corpo['cc']})" if corpo.get("cc") else "") + f"  campagna {cid}, {len(att)} allegati")
    if PROVA:
        print("    " + testo[:160].replace("\n", " ") + "…")
        return None
    if not prendi(d):
        print("    l'ha già presa un altro giro")
        return None
    try:
        r = manda.sl("POST", f"/campaigns/{cid}/reply-email-thread", corpo)
    except Exception as e:                                       # noqa: BLE001
        sb("PATCH", f"/rest/v1/clara_decisioni?id=eq.{d['id']}", {"stato": "approvata", "errore": f"Smartlead ha risposto male: {str(e)[:150]}"})
        return None
    if isinstance(r, dict) and (r.get("ok") is False or r.get("error")):
        sb("PATCH", f"/rest/v1/clara_decisioni?id=eq.{d['id']}", {"stato": "approvata", "errore": f"Smartlead: {json.dumps(r, ensure_ascii=False)[:200]}"})
        return None
    ora = datetime.datetime.now(ROMA)
    agg = {"awaiting_us": False}
    if d["mossa"] in CON_ANALISI:
        agg.update({"analysis_sent": True} if p.get("analysis_sent") else {"analysis_sent": True, "analysis_sent_at": ora.isoformat()})
    sb("PATCH", f"/rest/v1/prospects?id=eq.{p['id']}", agg)
    sb("PATCH", f"/rest/v1/clara_decisioni?id=eq.{d['id']}",
       {"stato": "inviata", "inviata_il": ora.isoformat(), "errore": None,
        "invio": {"campagna": cid, "lead": lid, "a": a, "cc": corpo.get("cc"), "allegati": [x["file_name"] for x in att],
                  "smartlead": (json.dumps(r, ensure_ascii=False) if not isinstance(r, str) else r)[:300]}})
    return True


def ricevute():
    """Le inviate senza ricevuta: si rilegge il filo vero e, se la mail c'e', si segna verificata."""
    righe = sb("GET", "/rest/v1/clara_decisioni?select=id,prospect_id,testo,testo_finale,inviata_il,invio&stato=eq.inviata&verificata_il=is.null"
                      "&order=inviata_il.desc&limit=20") or []
    ok = 0
    for d in righe:
        inv = d.get("invio") or {}
        if not (inv.get("campagna") and inv.get("lead")):
            continue
        try:
            h = manda.sl("GET", f"/campaigns/{inv['campagna']}/leads/{inv['lead']}/message-history") or {}
        except Exception:                                        # noqa: BLE001
            continue
        testo = (d.get("testo_finale") or d.get("testo") or "").strip()
        # 4/11: la testa (A:/Cc:/Oggetto:) si toglie come quando parte, e il confronto e' quello unico di manda
        partita = manda.partita_nel_filo(intestazione(testo)["corpo"], h.get("history"))
        eta = (adesso() - _quando(d["inviata_il"])).total_seconds() / 60
        if partita:
            if not PROVA:
                sb("PATCH", f"/rest/v1/clara_decisioni?id=eq.{d['id']}", {"verificata_il": adesso().isoformat()})
            ok += 1
        elif eta > 60:
            print(f"  ricevuta mancante da {int(eta)} minuti per {d['id'][:8]}: Smartlead non la mostra ancora nel filo")
    return ok


def appese():
    """Un «in_invio» da piu' di 30 minuti e' un lucchetto appeso: torna approvata (se non e' partita) o inviata."""
    righe = sb("GET", "/rest/v1/clara_decisioni?select=id,prospect_id,testo,testo_finale,approvata_il,creato_il&stato=eq.in_invio") or []
    for d in righe:
        da = _quando(d.get("approvata_il") or d["creato_il"])
        if (adesso() - da).total_seconds() / 60 < LUCCHETTO_APPESO_MIN or PROVA:
            continue
        sb("PATCH", f"/rest/v1/clara_decisioni?id=eq.{d['id']}", {"stato": "approvata", "errore": "era rimasta in invio: riprovo"})
        print(f"  lucchetto appeso sciolto: {d['id'][:8]}")


def main():
    appese()
    approvate = sb("GET", "/rest/v1/clara_decisioni?select=*&stato=eq.approvata&order=approvata_il.asc.nullsfirst") or []
    if len(approvate) > MAX_PER_GIRO:
        print(f"  {len(approvate)} approvate: ne mando {MAX_PER_GIRO} questo giro")
        approvate = approvate[:MAX_PER_GIRO]
    mandate = 0
    for d in approvate:
        try:
            if manda_una(d):
                mandate += 1
        except Exception as e:                                   # noqa: BLE001
            print(f"  {d['id'][:8]}: non mandata ({str(e)[:150]})")
            if not PROVA:
                sb("PATCH", f"/rest/v1/clara_decisioni?id=eq.{d['id']}&stato=eq.in_invio", {"stato": "approvata", "errore": str(e)[:200]})
    verificate = ricevute()
    print(f"clara_manda: {mandate} mandate, {len(approvate)} approvate, {verificate} ricevute confermate")


if __name__ == "__main__":
    main()
