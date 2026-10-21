#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""CLARA MANDA — le bozze approvate partono da Smartlead (24/9/2026).

PERCHE'
Dre, 24/9: «fai che Clara invia i messaggi: io clicco Approva e lei invia,
avendo a disposizione tutto il necessario per farlo bene; questi ultimi copy
mi hanno fatto capire che ha capito». Fino a oggi Clara preparava e Dre
copiava e mandava a mano. Resta vero che Clara NON manda niente da sola: parte
solo quello che una persona ha approvato con un clic, una bozza alla volta.

COSA FA, per ogni proposta in stato «approvata» (tipo risposta o umano, con la bozza):
1. IL CANCELLO: la bozza passa gli stessi controlli di quando e' stata scritta
   (bozze.cancello) e non ha segnaposto lasciati dentro. Se non passa, torna
   «aperta» con il motivo e Clara lo dice in Posta: meglio non mandare che
   mandare male.
2. IL THREAD GIUSTO: cerca il lead in Smartlead per email, prende la campagna
   dove ha risposto per ultimo (i thread vivono li'), legge lo storico e trova
   l'ultima sua risposta: e' a quella che si risponde, dalla stessa casella.
3. IL LUCCHETTO: la proposta passa a «in_invio» PRIMA di chiamare Smartlead.
   Se lo script muore a meta', al giro dopo non riparte da sola: resta li' e
   Clara lo dice.
4. L'INVIO: reply-email-thread di Smartlead, con la firma della casella
   (add_signature), all'indirizzo che la persona ci ha dato (email_alt) se c'e', e con
   in copia (cc) chi la bozza mette in copia (azione.cc, il rimbalzo interno del 20/10).
5. DOPO: proposta «fatta» con l'ora, la persona non aspetta piu' noi
   (awaiting_us), l'analisi segnata come mandata se il link era nel testo (o se
   Dre ha detto di allegarla), il gigante buono senza follow-up. La mail nel
   thread la registra il sync al giro dopo, con l'ora vera di Smartlead.

USO
  python3 scripts/manda.py            manda le approvate
  python3 scripts/manda.py --prova    mostra cosa manderebbe e non manda
"""

import datetime
import html
import itertools
import json
import os
import re
import sys
import urllib.parse
import time
import urllib.request
import zoneinfo

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from stanza import sb, di_clara, contattabile, quando, soldi_clienti, con_soldi  # noqa: E402

BASE = "https://server.smartlead.ai/api/v1"
ROMA = zoneinfo.ZoneInfo("Europe/Rome")          # 6/10: non +2 fisso, se no d'inverno «mandata alle» e' un'ora indietro


def chiave_smartlead():
    k = os.environ.get("SMARTLEAD_API_KEY", "")
    if k:
        return k
    try:
        for r in open(os.path.expanduser("~/.hermes/config.yaml"), encoding="utf-8"):
            m = re.match(r"\s*SMARTLEAD_API_KEY:\s*(\S+)", r)
            if m:
                return m.group(1).strip("\"'")
    except OSError:
        pass
    return ""


def sl(metodo, percorso, corpo=None):
    k = chiave_smartlead()
    sep = "&" if "?" in percorso else "?"
    req = urllib.request.Request(f"{BASE}{percorso}{sep}api_key={k}", method=metodo,
                                 data=json.dumps(corpo).encode() if corpo is not None else None,
                                 headers={"User-Agent": "clara/1.0", "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=90) as r:
        t = r.read().decode("utf-8", "replace")
    try:
        return json.loads(t)
    except ValueError:
        return {"grezzo": t}


def dopo_invio(az):
    """Cosa cambia sulla scheda quando la mail e' partita davvero (7/10: «follow-up a 15
    giorni» per chi ha l'analisi e dice piu' avanti). Solo questi campi, solo valori sani:
    la bozza non puo' scrivere altro sulla scheda per questa strada."""
    d = (az or {}).get("dopo_invio") or {}
    out = {}
    if d.get("classificazione") == "rinvio":
        out["classificazione"] = "rinvio"
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", str(d.get("next_action_date") or "")):
        out["next_action_date"] = d["next_action_date"]
    if isinstance(d.get("next_action"), str) and d["next_action"].strip():
        out["next_action"] = d["next_action"].strip()[:120]
    return out


def in_html(testo):
    """La bozza e' testo semplice: paragrafi separati da riga vuota, a capo dentro.
    I link al bucket (analisi, presentazione) non ci vanno: quei file partono in allegato."""
    testo = re.sub(r"https?://\S*/storage/v1/object/\S+", "", testo)
    par = [p.strip() for p in re.split(r"\n\s*\n", testo.strip()) if p.strip()]
    def riga(s):
        s = html.escape(s)
        return re.sub(r"(https?://[^\s<]+)", r'<a href="\1">\1</a>', s).replace("\n", "<br>")
    return "".join(f"<p>{riga(p)}</p>" for p in par)


def _sl_riprova(metodo, percorso, volte=4):
    """Smartlead frena quando le richieste sono tante (5/10: 73 fili su 277 letti monchi, in
    silenzio). Si riprova con attesa crescente prima di arrendersi."""
    for tentativo in range(volte):
        try:
            return sl(metodo, percorso)
        except Exception:                                          # noqa: BLE001
            if tentativo == volte - 1:
                raise
            time.sleep(2 * (tentativo + 1) ** 2)


def _quando(m):
    """L'ora di un messaggio, qualunque nome usi Smartlead. Serve per ordinare per DATA."""
    for k in ("time", "sent_time", "email_sent_time", "timestamp", "date", "created_at"):
        if m.get(k):
            return str(m[k])
    return ""


def _ultima_sua(h):
    """L'ultima risposta DEL LEAD, scelta per data e non per posizione nella lista.
    7/10: prima era risposte[-1], cioe' l'ultima nell'ordine in cui l'API le passa.
    Smartlead non garantisce quell'ordine: su un thread con piu' risposte si poteva
    rispondere citando un messaggio vecchio, ed e' uno dei modi in cui Clara sbagliava filo."""
    risposte = [m for m in (h.get("history") or []) if m.get("type") == "REPLY"]
    if not risposte:
        return None
    return max(risposte, key=_quando)


def _segna_thread(p, cid, lid, ultima):
    """IL FILO VERO SI SCRIVE (Dre, 7/10: «che abbia sempre il reale thread id»).
    Trovato una volta, si tiene: niente piu' deduzione dall'email a ogni invio.
    Sta in enriched.sl_thread, quindi non serve toccare lo schema."""
    try:
        fresco = (sb("GET", f"/rest/v1/prospects?select=enriched&id=eq.{p['id']}") or [{}])[0]
        arr = fresco.get("enriched") or {}
        arr["sl_thread"] = {"campaign_id": int(cid), "lead_id": int(lid),
                            "message_id": ultima.get("message_id"),
                            "stats_id": ultima.get("stats_id") or ultima.get("email_stats_id"),
                            "quando": _quando(ultima), "visto_il": datetime.datetime.now().isoformat()}
        sb("PATCH", f"/rest/v1/prospects?id=eq.{p['id']}", {"enriched": arr})
    except Exception as e:                                        # noqa: BLE001
        print(f"    filo non segnato ({str(e)[:60]})")


def thread(p):
    """La campagna dove ha risposto per ultimo, il lead e l'ultima sua risposta.
    7/10: l'ordine dei candidati e' cambiato. Prima si deduceva il filo dall'email a ogni
    invio e i dati del CRM erano l'ultima spiaggia: su un lead presente in piu' campagne
    si poteva prendere il filo di un'altra conversazione. Ora, in ordine:
      1. il filo gia' segnato in enriched.sl_thread (verificato dal vivo);
      2. campaign_id e lead_id del CRM;
      3. solo allora la ricerca per email.
    Il filo trovato si scrive, cosi' la volta dopo si parte dal punto 1."""
    visti = set()
    filo = (p.get("enriched") or {}).get("sl_thread") or {}

    def noti():
        """I fili che conosciamo senza chiedere niente a nessuno."""
        for cid, lid in ((filo.get("campaign_id"), filo.get("lead_id")),
                         (p.get("campaign_id"), p.get("lead_id"))):
            if cid and lid:
                yield int(cid), int(lid)

    def cercati():
        """Gli altri fili del lead, chiesti a Smartlead per email (15/10: sempre, non solo se i noti
        non portano a nulla: il filo vivo puo' essere in un'altra campagna)."""
        try:
            d = _sl_riprova("GET", f"/leads/?email={urllib.parse.quote(p['email'])}")
        except Exception as e:                                    # noqa: BLE001
            print(f"    lead non cercato ({str(e)[:60]})"); return
        if not isinstance(d, dict):
            return
        dati = [c for c in (d.get("lead_campaign_data") or []) if c.get("last_reply_at")]
        dati.sort(key=lambda c: str(c.get("last_reply_at")), reverse=True)
        for c in dati:
            if c.get("campaign_id") and d.get("id"):
                yield int(c["campaign_id"]), int(d["id"])

    # 15/10 (EnergetiKa): si fermava al PRIMO filo con una risposta. Il lead era in due campagne:
    # il «siamo a posto» di maggio veniva prima del filo vivo di ottobre, e la mail e' partita nel
    # filo vecchio. Ora si leggono tutti i fili del lead e vince la risposta piu' recente, come dice
    # il nome della funzione («dove ha risposto per ultimo»).
    migliore = None
    for cid, lid in itertools.chain(noti(), cercati()):
        if (cid, lid) in visti:
            continue
        visti.add((cid, lid))
        try:
            h = _sl_riprova("GET", f"/campaigns/{cid}/leads/{lid}/message-history") or {}
        except Exception as e:                                    # noqa: BLE001
            print(f"    storico illeggibile in {cid} ({str(e)[:60]})"); continue
        ultima = _ultima_sua(h)
        if ultima and (migliore is None or _quando(ultima) > _quando(migliore[2])):
            migliore = (cid, lid, ultima)
    if migliore:
        cid, lid, ultima = migliore
        if (filo.get("campaign_id"), filo.get("lead_id")) != (cid, lid) \
           or filo.get("message_id") != ultima.get("message_id"):
            _segna_thread(p, cid, lid, ultima)
        return cid, lid, ultima
    return None, None, None


def prendi(pr):
    """IL LUCCHETTO VERO (6/10). La bozza passa a «in invio» solo se e' ancora «approvata», e si
    guarda se la scrittura e' riuscita. Prima il passaggio non controllava niente: l'1/10 alle 9:11
    lampo e il direttore hanno fatto girare il postino insieme, tutti e due hanno letto
    «approvata», tutti e due hanno scritto «in invio», tutti e due hanno spedito. Christian Pircher
    e Maura (Studio M) hanno ricevuto la stessa mail due volte, a due secondi di distanza."""
    # 15/10: l'ora del lucchetto (risposta_il, che a invio fatto diventa l'ora della risposta). Il
    # recupero dei lucchetti appesi la misurava da «at», la nascita della bozza: una bozza di ieri
    # appena presa da un altro postino sembrava appesa, e con la cronologia di Smartlead in
    # ritardo di 5-20 minuti sarebbe ripartita. Con due corsie del direttore in parallelo conta.
    r = sb("PATCH", f"/rest/v1/proposte?id=eq.{pr['id']}&stato=eq.approvata",
           {"stato": "in_invio", "risposta_il": datetime.datetime.now(ROMA).isoformat()},
           {"Prefer": "return=representation"}) or []
    return bool(r)


def eta_lucchetto(b, adesso=None):
    """Minuti da quando la bozza e' stata presa (risposta_il); senza, dalla nascita (at)."""
    adesso = adesso or datetime.datetime.now(ROMA)
    quando_preso = b.get("risposta_il") or b.get("at")
    if not quando_preso:
        return 999
    return (adesso - datetime.datetime.fromisoformat(quando_preso)).total_seconds() / 60


LUCCHETTO_APPESO_MIN = 30      # la cronologia di Smartlead arriva anche 20 minuti dopo l'invio


def link_fresco(url):
    """Un link firmato nuovo (un giorno) per il PDF nel bucket: quello nella scheda
    puo' essere vecchio. Se non e' un file del bucket, resta com'e'."""
    m = re.search(r"/storage/v1/object/(?:sign|public)/vault/([^?]+)", url or "")
    if not m:
        return url
    try:
        from stanza import env
        SB, K = env("VITE_SUPABASE_URL"), env("SUPABASE_SERVICE_KEY")
        req = urllib.request.Request(f"{SB}/storage/v1/object/sign/vault/{m.group(1)}", data=json.dumps({"expiresIn": 86400}).encode(),
                                     method="POST", headers={"apikey": K, "Authorization": f"Bearer {K}", "Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=60) as r:
            f = json.load(r).get("signedURL") or ""
        return f"{SB}/storage/v1{f}" if f.startswith("/") else (f or url)
    except Exception:                                             # noqa: BLE001
        return url


def chi_ha_risposto(ultima, email_lead):
    """A chi rispondere quando ha scritto una persona della stessa azienda da un altro indirizzo.
    15/10 (Techno Pool): il lead era la casella generica, il responsabile ha risposto dalla sua; il
    postino rispondeva alla generica. Come «Rispondi» di Gmail: si risponde a chi ha scritto, ma
    solo se e' lo stesso dominio del lead (un dominio diverso puo' essere un'agenzia o un inoltro:
    li' decide email_alt) e non e' un indirizzo automatico."""
    if not ultima or ultima.get("type") != "REPLY":
        return None
    m = re.search(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+", ultima.get("from") or "")
    if not m or not email_lead or "@" not in email_lead:
        return None
    mittente = m.group(0).lower()
    if mittente == email_lead.lower() or mittente.split("@")[1] != email_lead.lower().split("@")[1]:
        return None
    if re.match(r"(no-?reply|mailer-daemon|postmaster|notifiche|notification)", mittente.split("@")[0]):
        return None
    # 16/10: un fuori ufficio di un collega non e' «una persona che ha risposto». Il postino aveva
    # scritto «Buongiorno Giuseppe» alla collega che aveva mandato solo l'automatico di assenza.
    import lettura
    corpo = re.sub(r"<[^>]+>", " ", ultima.get("email_body") or "")
    if lettura.AUTORISPOSTA.search(" ".join(corpo.split())[:1200]):
        return None
    return mittente


def con_presentazione(prima_risposta, az):
    """La presentazione va allegata? Alla prima risposta si', salvo un «no» esplicito (14/10);
    nei follow-up solo se la bozza la chiede."""
    scelta = (az or {}).get("allega_presentazione")
    return bool(scelta) or (prima_risposta and scelta is not False)


EMAIL = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")
# caselle che non sono una persona: in copia non ci vanno mai
DI_SERVIZIO = re.compile(r"^(?:no-?reply|noreply|donotreply|mailer-daemon|postmaster|notif\w*|dmarc\w*|abuse|privacy|unsubscribe|"
                         r"assistenza|supporto|support|helpdesk|ticket|customercare|customer\.?service|servizioclienti)@", re.I)


def controlla_cc(cc, p=None, let=None):
    """IL CANCELLO SULLA COPIA (20/10). Un indirizzo in copia deve essere:
    1. scritto dalla persona nella SUA mail (lettura.girato_a o il testo suo): mai inventato;
    2. una persona: non una casella di servizio, non una pec, non uno di noi;
    3. di un'azienda che si contatta: la regola del 25/9 (mai a un cliente, a chi e' in pipeline,
       perso o senza follow-up) vale anche per chi sta in copia, scheda per scheda sul dominio.
    Torna i motivi; vuota vuol dire che passa."""
    errori = []
    suo = ((let or {}).get("ultima_loro") or "").lower()
    noti = {str(g).lower() for g in ((let or {}).get("girato_a") or [])}
    for c in cc or []:
        c = str(c).strip().lower()
        if not EMAIL.fullmatch(c):
            errori.append(f"in copia «{c[:40]}» non e' un indirizzo"); continue
        if c not in suo and c not in noti:
            errori.append(f"in copia {c}, che la persona non ha scritto: mai un indirizzo inventato"); continue
        dominio = c.split("@")[1]
        if DI_SERVIZIO.match(c) or "pec" in dominio or dominio.endswith(("legalmail.it", "postecert.it")) \
                or any(n in c for n in ("studiogalilei", "galilei", "odyn", "smartlead")):
            errori.append(f"in copia {c}: casella di servizio, pec o nostra, non una persona"); continue
        if p and (p.get("email") or "").lower() == c:
            errori.append(f"in copia {c}, che e' gia' il destinatario"); continue
        try:
            q = urllib.parse.quote(c, safe="@"), urllib.parse.quote("*@" + dominio, safe="@*")
            schede = sb("GET", f"/rest/v1/prospects?select=id,fuori,stage,pipeline_stage,no_followup,classificazione"
                               f"&or=(email.eq.{q[0]},email.ilike.{q[1]})&limit=20") or []
        except Exception as e:                                    # noqa: BLE001
            errori.append(f"in copia {c}: non riesco a controllare se e' un cliente ({str(e)[:40]})"); continue
        if any(not contattabile(s) for s in schede):
            errori.append(f"in copia {c}: su quel dominio c'e' chi non si contatta (cliente, pipeline, perso o senza follow-up, regola del 25/9)")
    return errori


def in_copia(az):
    """Il campo cc di reply-email-thread: una stringa, indirizzi separati da virgola
    (documentazione Smartlead, api.smartlead.ai/api-reference/inbox/reply, letta il 20/10)."""
    cc = [str(c).strip() for c in ((az or {}).get("cc") or []) if str(c).strip()]
    return {"cc": ", ".join(cc)} if cc else {}


def controlla(bozza, p=None, gruppo=None, detto_no=False, cc=None, let=None, intento=None):
    if "{{" in bozza or "}}" in bozza or "[[" in bozza:
        return ["segnaposto lasciato nel testo"]
    if cc:
        errori_cc = controlla_cc(cc, p, let)
        if errori_cc:
            return errori_cc
    # IL PREZZO SUGGERITO E' INTERNO (Dre, 26/9): se il numero della scheda compare nel testo, non parte.
    # 12/10: vale fino alla conoscitiva compresa («mai un prezzo prima della conoscitiva»). Dopo,
    # il canone e' il listino e puo' stare in una mail di preventivo: bloccarlo fermerebbe il lavoro vero.
    pz = ((p or {}).get("enriched") or {}).get("prezzo") or {}
    if (p or {}).get("pipeline_stage") in ("tecnica", "avvio", "prova", "cliente"):
        pz = {}
    for n in [pz.get("punto")] + list(pz.get("fascia") or []):
        if n and re.search(rf"\b{int(n):,}\b|\b{int(n)}\b|\b{int(n):,}\b".replace(",", r"[.,]"), bozza):
            return [f"il prezzo suggerito ({int(n)} €) e' interno: non entra in una mail"]
    try:
        import bozze
        # i gruppi del segugio hanno il prossimo tocco gia' programmato: il finale leggero e' voluto (Dre 30/9)
        # 20/10 sera: l'intento dice al cancello cosa pretendere (INT-23: l'analisi si', la call no)
        return bozze.cancello(bozza, seguito_programmato=bool(gruppo), detto_no=detto_no, intento=intento)
    except Exception as e:                                        # noqa: BLE001
        return [f"cancello non eseguibile: {str(e)[:60]}"]


def superata(pr, p, ultima_at):
    """LA BOZZA E' SUPERATA DAI FATTI? (20/10, caso 3). L'ultima risposta del lead su Smartlead
    (ultima_at, la fonte vera) e' arrivata DOPO la nascita della bozza: la bozza risponde a un
    filo che non c'e' piu'. Per un follow-up vale anche una sua mail dopo l'analisi: e' una
    conversazione, non un silenzio. Torna il motivo, o None."""
    quando_lei = str(ultima_at or "").replace("Z", "")[:19]
    nata = str(pr.get("at") or "")[:19]
    if quando_lei and nata and quando_lei > nata:
        return f"ha riscritto il {quando_lei[8:10]}/{quando_lei[5:7]}, dopo che la bozza era nata ({nata[8:10]}/{nata[5:7]})"
    az = pr.get("azione") or {}
    if "FOLLOW UP 1" in ((az.get("template") or "") + (az.get("gruppo") or "")).upper():
        inviata = str((p or {}).get("analysis_sent_at") or "")[:19]
        if quando_lei and inviata and quando_lei > inviata:
            return f"ha scritto il {quando_lei[8:10]}/{quando_lei[5:7]}, dopo l'analisi: è una conversazione, non un silenzio"
    return None


def torna_aperta(pr, azienda, motivo, prova):
    print(f"    NON mandata: {motivo}")
    if prova:
        return
    sb("PATCH", f"/rest/v1/proposte?id=eq.{pr['id']}", {"stato": "aperta", "risposta": f"Non mandata: {motivo}"[:300]})
    di_clara("domanda", f"Non sono riuscita a mandare la risposta a {azienda}: {motivo}. Correggi la bozza e ripremi «Approva e manda», oppure mandala tu da Smartlead e segnala mandata.", prospect_id=pr.get("prospect_id"))


def pulizia():
    """LE BOZZE DI CHI NON E' PIU' UN LEAD si chiudono da sole (25/9, caso Zafferano):
    se un'azienda e' passata in pipeline, cliente, persa o senza follow-up dopo
    che la bozza era stata scritta, la bozza non deve restare in Posta."""
    ap = sb("GET", "/rest/v1/proposte?select=id,titolo,prospect_id&stato=in.(aperta,approvata)&tipo=in.(risposta,umano)&prospect_id=not.is.null&limit=1000") or []
    ids = list({x["prospect_id"] for x in ap})
    stato = {}
    for i in range(0, len(ids), 100):
        for p in sb("GET", f"/rest/v1/prospects?select=id,fuori,stage,pipeline_stage,no_followup,classificazione&id=in.({','.join(ids[i:i+100])})") or []:
            stato[p["id"]] = p
    n = 0
    for x in ap:
        if x["prospect_id"] in stato and not contattabile(stato[x["prospect_id"]]):
            sb("PATCH", f"/rest/v1/proposte?id=eq.{x['id']}", {"stato": "no", "risposta": "chiusa da sola: l'azienda non è più un lead (pipeline, cliente, persa o senza follow-up)",
                                                                 "risposta_il": datetime.datetime.now(ROMA).isoformat()})
            print(f"  chiusa: {x['titolo'][:60]} (non è più un lead)"); n += 1
    return n


def main():
    prova = "--prova" in sys.argv
    if not prova:
        pulizia()
    approvate = sb("GET", "/rest/v1/proposte?select=id,tipo,titolo,prospect_id,azione,at&stato=eq.approvata&tipo=in.(risposta,umano)&order=at") or []
    MAX_PER_GIRO = 12          # in fila, non a raffica (25/9): dodici ogni cinque minuti
    if len(approvate) > MAX_PER_GIRO:
        print(f"  {len(approvate)} approvate: ne mando {MAX_PER_GIRO} questo giro, le altre al prossimo")
        approvate = approvate[:MAX_PER_GIRO]
    # 2/10: una bozza «in invio» da piu' di 10 minuti e' un lucchetto appeso (rete caduta
    # fra il lucchetto e Smartlead). Si guarda il thread vero: se la mail NON e' partita,
    # torna «approvata» e riparte; se e' partita, si chiude. Niente resta appeso in silenzio.
    bloccate = sb("GET", "/rest/v1/proposte?select=id,titolo,at,risposta_il,prospect_id,azione&stato=eq.in_invio") or []
    for b in bloccate:
        eta = eta_lucchetto(b)
        if eta < LUCCHETTO_APPESO_MIN or prova:
            print(f"  in invio dal {b['at'][:16]}: {b['titolo'][:60]} (la lascio, e' appena partita)"); continue
        pr = (sb("GET", f"/rest/v1/prospects?select=email,campaign_id,lead_id&id=eq.{b['prospect_id']}") or [None])[0] if b.get("prospect_id") else None
        partita = False
        if pr:
            try:
                cid, lid, _ = thread(pr)
                h = sl("GET", f"/campaigns/{cid}/leads/{lid}/message-history") or {}
                corpo = ((b.get("azione") or {}).get("bozza") or "")[:60].strip()
                partita = any(m.get("type") != "REPLY" and corpo and corpo[:40] in (m.get("email_body") or "") for m in (h.get("history") or []))
            except Exception:                                 # noqa: BLE001
                partita = None
        if partita:
            sb("PATCH", f"/rest/v1/proposte?id=eq.{b['id']}", {"stato": "fatta", "risposta": "era rimasta in invio: su Smartlead risulta mandata, chiusa"})
            print(f"  recuperata (gia' partita): {b['titolo'][:50]}")
        elif partita is False:
            sb("PATCH", f"/rest/v1/proposte?id=eq.{b['id']}", {"stato": "approvata"})
            print(f"  recuperata (NON partita, la rimando): {b['titolo'][:50]}")
        else:
            print(f"  in invio dal {b['at'][:16]}: {b['titolo'][:50]} (non ho potuto verificare, la lascio)")
    approvate = sb("GET", "/rest/v1/proposte?select=id,tipo,titolo,prospect_id,azione,at&stato=eq.approvata&tipo=in.(risposta,umano)&order=at") or [] if bloccate else approvate
    mandate = 0
    for pr in approvate:
        az = pr.get("azione") or {}
        bozza = (az.get("bozza") or "").strip()
        p = (sb("GET", f"/rest/v1/prospects?select=id,email,email_alt,company,name,campaign_id,lead_id,analysis_pdf,analysis_sent,"
                       f"trattenuta:enriched->analisi->>trattenuta&id=eq.{pr['prospect_id']}") or [None])[0] if pr.get("prospect_id") else None
        # 29/9: il prezzo suggerito sta in cassaforte. Prima qui non arrivava proprio (la
        # scheda si leggeva senza enriched): il controllo «il prezzo non entra in una mail» era cieco
        p = con_soldi(p, soldi_clienti([p["id"]])) if p else p
        if not p or not bozza:
            torna_aperta(pr, pr["titolo"], "manca la scheda o la bozza", prova); continue
        azienda = p.get("company") or p.get("name") or p["email"]
        # MAI A UN CLIENTE O A CHI E' IN PIPELINE (25/9, caso Zafferano): si controlla
        # anche qui, all'ultimo passo, con la scheda riletta adesso
        stato_p = (sb("GET", f"/rest/v1/prospects?select=fuori,stage,pipeline_stage,no_followup,classificazione&id=eq.{p['id']}") or [{}])[0]
        gruppo_fu = any(k in ((az.get("template") or "") + (az.get("gruppo") or "")).upper()
                        for k in ("FOLLOW", "MINI", "RICONTATTO", "RIPRESA"))
        if gruppo_fu and stato_p.get("classificazione") in ("negativo", "persona_sbagliata"):
            # 7/10, dal controllo dal vivo: la classe puo' cambiare DOPO che la bozza e' nata
            # (Cisanova, EnergetiKa). Un no resta un no anche con la bozza approvata.
            sb("PATCH", f"/rest/v1/proposte?id=eq.{pr['id']}", {"stato": "no", "risposta": f"non mandata: nel frattempo e' {stato_p.get('classificazione')} (controllo del 7/10)",
                                                                 "risposta_il": datetime.datetime.now(ROMA).isoformat()})
            print(f"  {azienda}: NON mando il follow-up, ora e' {stato_p.get('classificazione')}")
            continue
        if not contattabile(stato_p):
            print(f"  {azienda}: NON mando, non è più un lead (pipeline/cliente/perso/no follow-up)")
            sb("PATCH", f"/rest/v1/proposte?id=eq.{pr['id']}", {"stato": "no", "risposta": "non mandata: l'azienda è in pipeline, cliente, persa o senza follow-up (regola del 25/9)",
                                                                 "risposta_il": datetime.datetime.now(ROMA).isoformat()})
            di_clara("controllo", f"Non ho mandato la bozza a {azienda}: non è più un lead (pipeline/cliente). Chiusa.", prospect_id=p["id"], letto=True)
            continue
        if not az.get("approvata_da"):
            torna_aperta(pr, azienda, "non risulta chi l'ha approvata", prova); continue
        errori = controlla(bozza, p, gruppo=az.get("gruppo") or az.get("template"), detto_no=bool((az.get("lettura") or {}).get("detto_no")),
                           cc=az.get("cc"), let=az.get("lettura"), intento=az.get("intento"))
        if errori:
            torna_aperta(pr, azienda, "; ".join(errori)[:200], prova); continue
        cid, lid, ultima = thread(p)
        if not ultima:
            torna_aperta(pr, azienda, "non trovo il suo thread su Smartlead", prova); continue
        # 20/10 (caso 3): l'ultimo cancello guarda il filo VERO. Se il lead ha scritto dopo la
        # nascita della bozza, un follow-up si chiude col motivo (e' una conversazione: scrive Dre);
        # una risposta approvata da sola torna in Posta a Dre.
        vecchia = superata(pr, p, _quando(ultima))
        if vecchia and (gruppo_fu or az.get("automatica")):
            if gruppo_fu:
                print(f"  {azienda}: NON mando il follow-up, {vecchia}")
                if not prova:
                    sb("PATCH", f"/rest/v1/proposte?id=eq.{pr['id']}", {"stato": "no", "risposta": f"non mandata: {vecchia}"[:300],
                                                                         "risposta_il": datetime.datetime.now(ROMA).isoformat()})
                    di_clara("controllo", f"Follow-up a {azienda} non mandato, chiuso: {vecchia}.", prospect_id=p["id"], letto=True)
            else:
                torna_aperta(pr, azienda, vecchia + ": rileggi il filo", prova)
            continue
        a = (p.get("email_alt") or [None])[0] or chi_ha_risposto(ultima, p["email"]) or p["email"]
        copia = in_copia(az)
        corpo = {"email_stats_id": ultima.get("stats_id") or ultima.get("email_stats_id"),
                 "email_body": in_html(bozza),
                 "reply_message_id": ultima.get("message_id"),
                 "reply_email_time": ultima.get("time"),
                 "reply_email_body": ultima.get("email_body") or "",
                 "add_signature": True, "to_email": a, **copia}
        a_chi = a + (f", in copia {copia['cc']}" if copia else "")
        # GLI ALLEGATI IN PDF (Dre, 25/9): «alla prima risposta mandiamo l'analisi e
        # la presentazione in PDF allegato, nessun link da cliccare, semplicemente
        # quello». Nei follow-up: la presentazione se il template la prevede,
        # l'analisi se la spunta e' accesa.
        prima_risposta = not p.get("analysis_sent")
        if (prima_risposta or az.get("allega")) and not p.get("analysis_pdf"):
            # l'analisi non c'e' ancora (la sta facendo l'operazione «analisi»): si aspetta,
            # senza rimbalzare la bozza e senza domande a ogni giro
            # 28/9: l'attesa non e' infinita. Istituto Flegreo era approvato dal 25
            # e a ogni giro, ogni cinque minuti, si scriveva «aspetto l'analisi»:
            # ma l'analisi non poteva arrivare, perche' il loro sito rispondeva 500
            # e senza sito letto non si fa. Nessuno lo diceva. Dopo un giorno di
            # attesa la mail torna in Posta con il motivo: la decide una persona.
            ferma_da = (datetime.datetime.now(datetime.timezone.utc) - quando(az.get("approvata_il") or pr["at"])).total_seconds() / 3600
            if ferma_da > 24:
                torna_aperta(pr, pr["titolo"],
                             f"aspetta l'analisi da {int(ferma_da)} ore e non arriva: guarda se il sito loro risponde, "
                             f"oppure togli l'allegato e mandala cosi'", prova)
                continue
            # 21/10 sera: il perche' dell'attesa sta nella riga (la scheda Clara lo dice in rosso dopo un'ora)
            motivo = f" (l'analisi e' bocciata: {str(p.get('trattenuta'))[:100]})" if p.get("trattenuta") else ""
            print(f"  {azienda}: aspetto l'analisi da {int(ferma_da)}h{motivo}, riprovo al giro dopo"); continue
        if p.get("analysis_pdf") and (prima_risposta or az.get("allega")):
            url = link_fresco(p["analysis_pdf"])
            try:
                with urllib.request.urlopen(urllib.request.Request(url, method="HEAD"), timeout=30) as r:
                    peso = int(r.headers.get("Content-Length") or 0)
            except Exception:                                     # noqa: BLE001
                peso = 0
            if peso:
                corpo["attachments"] = [{"file_name": f"Analisi Google Ads - {azienda}.pdf"[:120], "file_url": url,
                                         "file_type": "application/pdf", "file_size": peso}]
            else:
                torna_aperta(pr, azienda, "il PDF dell'analisi non si apre: non la mando senza", prova); continue
        # LA PRESENTAZIONE (FOLLOW UP 1: «le allego anche una breve presentazione»)
        # 14/10: un «niente presentazione» esplicito vale anche alla prima risposta (a chi ha
        # appena detto no ma «me la mandi», la presentazione dei servizi suona come vendita)
        if con_presentazione(prima_risposta, az):
            from stanza import env as _env
            url_p = link_fresco(f"{_env('VITE_SUPABASE_URL')}/storage/v1/object/sign/vault/modelli/sg-presentazione.pdf")
            try:
                with urllib.request.urlopen(urllib.request.Request(url_p, method="HEAD"), timeout=30) as r:
                    peso_p = int(r.headers.get("Content-Length") or 0)
            except Exception:                                 # noqa: BLE001
                peso_p = 0
            if peso_p:
                corpo.setdefault("attachments", []).append({"file_name": "Presentazione Studio Galilei.pdf", "file_url": url_p,
                                                             "file_type": "application/pdf", "file_size": peso_p})
            else:
                torna_aperta(pr, azienda, "la presentazione dello Studio non si apre dal bucket: non la mando senza", prova); continue
        print(f"  {azienda} → {a_chi}  (campagna {cid}, risposta del {str(ultima.get('time'))[:16]})")
        if prova:
            print("    " + bozza[:160].replace("\n", " ") + "…"); continue
        # il lucchetto: prima di chiamare Smartlead, e solo se nessun altro postino l'ha presa
        if not prendi(pr):
            print(f"    {azienda}: l'ha gia' presa un altro giro del postino, non la rimando"); continue
        try:
            r = sl("POST", f"/campaigns/{cid}/reply-email-thread", corpo)
        except Exception as e:                                    # noqa: BLE001
            torna_aperta(pr, azienda, f"Smartlead ha risposto male: {str(e)[:120]}", prova); continue
        if isinstance(r, dict) and (r.get("ok") is False or r.get("error")):
            torna_aperta(pr, azienda, f"Smartlead: {json.dumps(r, ensure_ascii=False)[:150]}", prova); continue
        ora = datetime.datetime.now(ROMA)
        agg = {"awaiting_us": False}
        if az.get("intento") == "INT-GB":
            agg.update({"analysis_sent": True, "analysis_sent_at": ora.isoformat(), "no_followup": True})
        # 1/10: gli allegati partivano (prima_risposta) ma il segno «analisi mandata» no,
        # e senza quel segno il segugio non programma i follow-up. Stessa condizione dell'allegato.
        elif prima_risposta or az.get("allega") or (p.get("analysis_pdf") and p["analysis_pdf"] in bozza):
            # 7/10: solo il PRIMO invio segna la data. La ripresa del 25/9 la riscriveva e il
            # timer dei follow-up ripartiva: Rastan risultava «analisi del 25/9», e chi aveva
            # avuto la ripresa si beccava FOLLOW UP 1 e MINI insieme (Renewal Italy)
            agg.update({"analysis_sent": True} if p.get("analysis_sent") else {"analysis_sent": True, "analysis_sent_at": ora.isoformat()})
        agg.update(dopo_invio(az))
        sb("PATCH", f"/rest/v1/prospects?id=eq.{p['id']}", agg)
        sb("PATCH", f"/rest/v1/proposte?id=eq.{pr['id']}", {"stato": "fatta", "risposta_il": ora.isoformat(),
                                                             "risposta": f"Mandata da Clara alle {ora:%H:%M} da Smartlead, a {a_chi}",
                                                             "azione": {**az, "invio": {"campagna": cid, "lead": lid, "alle": ora.isoformat(), "smartlead": (json.dumps(r, ensure_ascii=False) if not isinstance(r, str) else r)[:300]}}})
        di_clara("controllo", f"Mandata a {azienda} ({a_chi}) alle {ora:%H:%M}, nel thread di Smartlead.", prospect_id=p["id"], letto=True)
        mandate += 1
    print(f"manda: {mandate} mandate, {len(approvate)} approvate, {len(bloccate)} ferme")


if __name__ == "__main__":
    main()
