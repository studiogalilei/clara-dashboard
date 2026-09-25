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
   (add_signature), all'indirizzo che la persona ci ha dato (email_alt) se c'e'.
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
import json
import os
import re
import sys
import urllib.parse
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from stanza import sb, di_clara, contattabile               # noqa: E402

BASE = "https://server.smartlead.ai/api/v1"
ROMA = datetime.timezone(datetime.timedelta(hours=2))


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


def in_html(testo):
    """La bozza e' testo semplice: paragrafi separati da riga vuota, a capo dentro.
    I link al bucket (analisi, presentazione) non ci vanno: quei file partono in allegato."""
    testo = re.sub(r"https?://\S*/storage/v1/object/\S+", "", testo)
    par = [p.strip() for p in re.split(r"\n\s*\n", testo.strip()) if p.strip()]
    def riga(s):
        s = html.escape(s)
        return re.sub(r"(https?://[^\s<]+)", r'<a href="\1">\1</a>', s).replace("\n", "<br>")
    return "".join(f"<p>{riga(p)}</p>" for p in par)


def thread(p):
    """La campagna dove ha risposto per ultimo, il lead e l'ultima sua risposta."""
    candidati = []
    try:
        d = sl("GET", f"/leads/?email={urllib.parse.quote(p['email'])}")
        if isinstance(d, dict):
            for c in d.get("lead_campaign_data") or []:
                if c.get("last_reply_at"):
                    candidati.append((c["last_reply_at"], int(c["campaign_id"]), int(d["id"])))
    except Exception as e:                                        # noqa: BLE001
        print(f"    lead non cercato ({str(e)[:60]})")
    candidati.sort(reverse=True)
    if not candidati and p.get("campaign_id") and p.get("lead_id"):
        candidati = [("", int(p["campaign_id"]), int(p["lead_id"]))]
    for _, cid, lid in candidati:
        try:
            h = sl("GET", f"/campaigns/{cid}/leads/{lid}/message-history") or {}
        except Exception as e:                                    # noqa: BLE001
            print(f"    storico illeggibile in {cid} ({str(e)[:60]})"); continue
        risposte = [m for m in (h.get("history") or []) if m.get("type") == "REPLY"]
        if risposte:
            return cid, lid, risposte[-1]
    return None, None, None


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


def controlla(bozza):
    if "{{" in bozza or "}}" in bozza or "[[" in bozza:
        return ["segnaposto lasciato nel testo"]
    try:
        import bozze
        return bozze.cancello(bozza)
    except Exception as e:                                        # noqa: BLE001
        return [f"cancello non eseguibile: {str(e)[:60]}"]


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
    bloccate = sb("GET", "/rest/v1/proposte?select=id,titolo,at&stato=eq.in_invio") or []
    for b in bloccate:
        print(f"  ferma in invio dal {b['at'][:16]}: {b['titolo'][:60]} (non riparte da sola)")
    mandate = 0
    for pr in approvate:
        az = pr.get("azione") or {}
        bozza = (az.get("bozza") or "").strip()
        p = (sb("GET", f"/rest/v1/prospects?select=id,email,email_alt,company,name,campaign_id,lead_id,analysis_pdf,analysis_sent&id=eq.{pr['prospect_id']}") or [None])[0] if pr.get("prospect_id") else None
        if not p or not bozza:
            torna_aperta(pr, pr["titolo"], "manca la scheda o la bozza", prova); continue
        azienda = p.get("company") or p.get("name") or p["email"]
        # MAI A UN CLIENTE O A CHI E' IN PIPELINE (25/9, caso Zafferano): si controlla
        # anche qui, all'ultimo passo, con la scheda riletta adesso
        stato_p = (sb("GET", f"/rest/v1/prospects?select=fuori,stage,pipeline_stage,no_followup,classificazione&id=eq.{p['id']}") or [{}])[0]
        if not contattabile(stato_p):
            print(f"  {azienda}: NON mando, non è più un lead (pipeline/cliente/perso/no follow-up)")
            sb("PATCH", f"/rest/v1/proposte?id=eq.{pr['id']}", {"stato": "no", "risposta": "non mandata: l'azienda è in pipeline, cliente, persa o senza follow-up (regola del 25/9)",
                                                                 "risposta_il": datetime.datetime.now(ROMA).isoformat()})
            di_clara("controllo", f"Non ho mandato la bozza a {azienda}: non è più un lead (pipeline/cliente). Chiusa.", prospect_id=p["id"], letto=True)
            continue
        if not az.get("approvata_da"):
            torna_aperta(pr, azienda, "non risulta chi l'ha approvata", prova); continue
        errori = controlla(bozza)
        if errori:
            torna_aperta(pr, azienda, "; ".join(errori)[:200], prova); continue
        cid, lid, ultima = thread(p)
        if not ultima:
            torna_aperta(pr, azienda, "non trovo il suo thread su Smartlead", prova); continue
        a = (p.get("email_alt") or [None])[0] or p["email"]
        corpo = {"email_stats_id": ultima.get("stats_id") or ultima.get("email_stats_id"),
                 "email_body": in_html(bozza),
                 "reply_message_id": ultima.get("message_id"),
                 "reply_email_time": ultima.get("time"),
                 "reply_email_body": ultima.get("email_body") or "",
                 "add_signature": True, "to_email": a}
        # GLI ALLEGATI IN PDF (Dre, 25/9): «alla prima risposta mandiamo l'analisi e
        # la presentazione in PDF allegato, nessun link da cliccare, semplicemente
        # quello». Nei follow-up: la presentazione se il template la prevede,
        # l'analisi se la spunta e' accesa.
        prima_risposta = not p.get("analysis_sent")
        if (prima_risposta or az.get("allega")) and not p.get("analysis_pdf"):
            # l'analisi non c'e' ancora (la sta facendo l'operazione «analisi»): si aspetta,
            # senza rimbalzare la bozza e senza domande a ogni giro
            print(f"  {azienda}: aspetto l'analisi, riprovo al giro dopo"); continue
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
        if prima_risposta or az.get("allega_presentazione"):
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
        print(f"  {azienda} → {a}  (campagna {cid}, risposta del {str(ultima.get('time'))[:16]})")
        if prova:
            print("    " + bozza[:160].replace("\n", " ") + "…"); continue
        # il lucchetto: prima di chiamare Smartlead
        sb("PATCH", f"/rest/v1/proposte?id=eq.{pr['id']}", {"stato": "in_invio"})
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
        elif az.get("allega") or (p.get("analysis_pdf") and p["analysis_pdf"] in bozza):
            agg.update({"analysis_sent": True, "analysis_sent_at": ora.isoformat()})
        sb("PATCH", f"/rest/v1/prospects?id=eq.{p['id']}", agg)
        sb("PATCH", f"/rest/v1/proposte?id=eq.{pr['id']}", {"stato": "fatta", "risposta_il": ora.isoformat(),
                                                             "risposta": f"Mandata da Clara alle {ora:%H:%M} da Smartlead, a {a}",
                                                             "azione": {**az, "invio": {"campagna": cid, "lead": lid, "alle": ora.isoformat(), "smartlead": (json.dumps(r, ensure_ascii=False) if not isinstance(r, str) else r)[:300]}}})
        di_clara("controllo", f"Mandata a {azienda} ({a}) alle {ora:%H:%M}, nel thread di Smartlead.", prospect_id=p["id"], letto=True)
        mandate += 1
    print(f"manda: {mandate} mandate, {len(approvate)} approvate, {len(bloccate)} ferme")


if __name__ == "__main__":
    main()
