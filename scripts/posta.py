#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""LA POSTA (15/9/2026): Clara legge le caselle e tiene aggiornata la pipeline.

PERCHE'
Dre (15/9): «voglio un sistema vivo, Clara vede cio' che succede nelle nostre
mailbox e aggiorna tutto di conseguenza: se invio una mail la vede, capisce e
aggiorna gli stati; se non e' sicura me lo chiede». Fino a oggi Clara vedeva
solo Smartlead (le campagne), il calendario, il Drive e Stripe: una mail
scritta a mano da Gmail non esisteva per il CRM. Risultato: la scheda diceva
«da rispondere» a chi avevi gia' risposto un'ora prima.

COSA FA, per ogni persona che e' entrata con Google
1. legge le mail degli ultimi giorni (gmail.readonly, il permesso che si da'
   al primo accesso);
2. scarta il traffico che non e' una conversazione con un'azienda: newsletter,
   notifiche, mail interne fra noi;
3. capisce di che azienda e': prima l'indirizzo esatto, poi il dominio, poi
   il nome dell'azienda dentro l'oggetto (senza indovinare sui domini
   generici tipo gmail.com);
4. scrive l'interazione nella scheda (`email_in` o `email_out`), una volta
   sola: il riferimento al messaggio Gmail resta in `ref`;
5. aggiorna quel poco che e' sicuro: chi ci ha scritto aspetta una risposta,
   chi ha ricevuto la nostra non la aspetta piu', chi era «nuovo» e risponde
   diventa «risposto»;
6. quando NON e' sicura non scrive: mette una domanda nella Posta di Clara
   (l'azienda non e' nel CRM, oppure la mail cambierebbe uno stato delicato).

Non tocca mai clienti e persi: quelli li muove una persona.

USO
  python3 scripts/posta.py                  gli ultimi 2 giorni, tutte le caselle
  python3 scripts/posta.py --prova          dice cosa farebbe, non scrive
  python3 scripts/posta.py --giorni 7       piu' indietro
  python3 scripts/posta.py --chi dramane@studiogalilei.com
"""

import base64
import datetime
import os
import re
import sys
import urllib.parse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from stanza import sb, proponi                             # noqa: E402
from google_api import g                                   # noqa: E402

NOSTRO_DOMINIO = "studiogalilei.com"
GMAIL = "https://gmail.googleapis.com/gmail/v1/users/me"

# i domini di chiunque: da questi non si deduce l'azienda
GENERICI = {"gmail.com", "googlemail.com", "hotmail.com", "hotmail.it", "yahoo.com", "yahoo.it",
            "libero.it", "outlook.com", "outlook.it", "icloud.com", "live.it", "live.com",
            "pec.it", "tiscali.it", "virgilio.it", "alice.it", "me.com", "aol.com"}

# quello che non e' una conversazione con un'azienda
AUTOMATICI = re.compile(
    r"(no-?reply|do-?not-?reply|nonrispondere|notification|notifiche|notify|mailer-daemon|postmaster|"
    r"bounce|newsletter|mailing|unsubscribe|@smartlead|@stripe\.|@google\.com|@docs\.google|@calendar-notification|"
    r"@github\.com|@linkedin\.com|@facebookmail|@youtube|@apple\.com|@paypal|@amazon|@microsoft|@slack|"
    r"@notion\.so|@figma\.com|@vercel\.com|@supabase)", re.I)

PAROLE_VUOTE = {"studiogalilei", "studio", "galilei", "call", "chiamata", "meeting", "srl", "srls", "spa",
                "snc", "sas", "italia", "italy", "group", "google", "ads", "marketing", "sito", "analisi",
                "info", "team", "web", "digital", "agency", "agenzia", "consulting", "societa", "società",
                "azienda", "impresa", "ditta", "company", "servizi", "services", "progetto", "preventivo",
                "contratto", "proposta", "offerta", "conferma", "grazie", "salve", "buongiorno", "riscontro"}


def parole(t):
    return {w for w in re.split(r"[^a-zà-ù0-9]+", (t or "").lower()) if len(w) >= 4 and w not in PAROLE_VUOTE}


def dominio(mail):
    return (mail or "").split("@")[-1].lower().strip(">").strip()


def indirizzi(testo):
    return [m.lower() for m in re.findall(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+", testo or "")]


def carica_rubrica():
    # PostgREST ne da' mille per volta: la rubrica vera e' di tredicimila, e
    # una mail che arriva dalla tredicimillesima azienda deve essere
    # riconosciuta come le altre
    righe, pagina = [], 0
    while True:
        blocco = sb("GET", "/rest/v1/prospects?select=id,name,company,email,email_alt,stage,pipeline_stage,fuori,"
                           f"awaiting_us,last_reply_at,classificazione&limit=1000&offset={pagina * 1000}") or []
        righe += blocco
        if len(blocco) < 1000 or pagina > 40:
            break
        pagina += 1
    per_email, per_dominio, aziende, indice = {}, {}, [], {}
    for p in righe:
        indice[p["id"]] = p
        for m in [p.get("email") or ""] + list(p.get("email_alt") or []):
            m = m.lower().strip()
            if not m:
                continue
            per_email[m] = p["id"]
            d = dominio(m)
            if d and d not in GENERICI and d != NOSTRO_DOMINIO:
                per_dominio.setdefault(d, p["id"])
        ps = parole(p.get("company") or "")
        if ps:
            aziende.append((p["id"], ps))
    conta = {}
    for _, ps in aziende:
        for w in ps:
            conta[w] = conta.get(w, 0) + 1
    return {"email": per_email, "dominio": per_dominio, "aziende": aziende, "conta": conta, "indice": indice}


def trova(rubrica, mail_controparte, oggetto):
    """Prima l'indirizzo, poi il dominio, poi il nome dell'azienda nell'oggetto."""
    for m in mail_controparte:
        if m in rubrica["email"]:
            return rubrica["email"][m], "indirizzo"
    for m in mail_controparte:
        d = dominio(m)
        if d and d not in GENERICI and d in rubrica["dominio"]:
            return rubrica["dominio"][d], "dominio"
    ogg = parole(oggetto)
    if ogg:
        for pid, ps in rubrica["aziende"]:
            comuni = ps & ogg
            # una parola sola basta se e' lunga e di UNA azienda soltanto
            if any(len(w) >= 6 and rubrica["conta"][w] == 1 for w in comuni):
                return pid, "oggetto"
    return None, None


# ---------- Gmail ----------

def caselle(chi=None):
    """Chi ha dato il permesso su Gmail entrando nel Workspace."""
    righe = sb("GET", "/rest/v1/google_token?select=email,user_id,scopes") or []
    fuori = []
    for r in righe:
        if chi and r["email"] != chi:
            continue
        if "gmail.readonly" not in (r.get("scopes") or ""):
            continue
        fuori.append(r)
    return fuori


def testo_di(payload):
    """Il testo semplice del messaggio, senza allegati e senza HTML."""
    if not payload:
        return ""
    mime = payload.get("mimeType", "")
    corpo = payload.get("body", {}) or {}
    if mime == "text/plain" and corpo.get("data"):
        try:
            return base64.urlsafe_b64decode(corpo["data"] + "==").decode("utf-8", "ignore")
        except Exception:
            return ""
    for parte in payload.get("parts", []) or []:
        t = testo_di(parte)
        if t.strip():
            return t
    return ""


def ripulisci(t):
    """Via le citazioni e le firme: resta quello che ha scritto davvero."""
    righe = []
    for r in (t or "").splitlines():
        if r.strip().startswith(">"):
            continue
        if re.match(r"^\s*(Il .* ha scritto:|On .* wrote:|-{2,}\s*Messaggio originale|From:)", r):
            break
        righe.append(r.rstrip())
    fuori = "\n".join(righe).strip()
    fuori = re.sub(r"\n{3,}", "\n\n", fuori)
    return fuori[:1200]


def quando(headers):
    for h in headers:
        if h["name"].lower() == "date":
            try:
                import email.utils
                d = email.utils.parsedate_to_datetime(h["value"])
                if d.tzinfo is None:
                    d = d.replace(tzinfo=datetime.timezone.utc)
                return d.astimezone(datetime.timezone.utc).isoformat()
            except Exception:
                return None
    return None


def leggi_casella(email_persona, giorni, prova):
    q = urllib.parse.quote(f"newer_than:{giorni}d -in:spam -in:chats -in:drafts "
                           f"-category:promotions -category:social -category:forums")
    lista = g("GET", f"{GMAIL}/messages?q={q}&maxResults=80", email=email_persona) or {}
    return lista.get("messages", []) or []


def macina(persona, rubrica, giorni, prova, limite_domande):
    email_persona = persona["email"]
    fatte = {"scritte": 0, "saltate": 0, "domande": 0, "aggiornate": 0}
    try:
        messaggi = leggi_casella(email_persona, giorni, prova)
    except RuntimeError as e:
        print(f"  {email_persona}: {e}")
        return fatte
    print(f"  {email_persona}: {len(messaggi)} messaggi negli ultimi {giorni} giorni")

    for m in messaggi:
        try:
            d = g("GET", f"{GMAIL}/messages/{m['id']}?format=full", email=email_persona)
        except RuntimeError as e:
            print(f"    {m['id']}: {e}")
            continue
        headers = d.get("payload", {}).get("headers", []) or []
        h = {x["name"].lower(): x["value"] for x in headers}
        mittente = " ".join(indirizzi(h.get("from", "")))
        destinatari = indirizzi(h.get("to", "")) + indirizzi(h.get("cc", ""))
        oggetto = h.get("subject", "")
        at = quando(headers)
        if not at or not mittente:
            continue

        tutti = [mittente] + destinatari
        if any(AUTOMATICI.search(x) for x in tutti + [h.get("from", "")]):
            fatte["saltate"] += 1
            continue
        nostra = mittente.endswith(NOSTRO_DOMINIO)
        controparte = [x for x in (destinatari if nostra else [mittente]) if not x.endswith(NOSTRO_DOMINIO)]
        if not controparte:
            fatte["saltate"] += 1          # posta interna fra noi: non e' pipeline
            continue

        pid, come = trova(rubrica, controparte, oggetto)
        if not pid:
            d0 = dominio(controparte[0])
            if d0 and d0 not in GENERICI and fatte["domande"] < limite_domande and not nostra:
                fatte["domande"] += 1
                print(f"    [?] {controparte[0]}: «{oggetto[:60]}» non e' nel CRM")
                if not prova:
                    proponi("nuovo", f"{controparte[0]} ci ha scritto e non e' nel CRM",
                            perche=f"Oggetto: {oggetto[:150]}",
                            azione={"nuovo": {"email": controparte[0], "company": d0.split(".")[0].title(),
                                              "stage": "risposto", "awaiting_us": True}},
                            owner=persona.get("user_id"))
            continue

        p = rubrica["indice"][pid]
        kind = "email_out" if nostra else "email_in"
        corpo = ripulisci(testo_di(d.get("payload"))) or (d.get("snippet") or "")[:300]
        riga = {"prospect_id": pid, "at": at, "kind": kind,
                "body": f"{oggetto}\n\n{corpo}".strip()[:1500], "ref": f"gmail:{m['id']}"}
        nome = p.get("company") or p.get("name") or p.get("email")
        print(f"    {'->' if nostra else '<-'} {nome} ({come}): {oggetto[:50]}")
        if prova:
            fatte["scritte"] += 1
            continue

        gia = sb("GET", f"/rest/v1/interactions?select=id&ref=eq.gmail:{m['id']}&limit=1")
        if gia:
            fatte["saltate"] += 1
            continue
        try:
            sb("POST", "/rest/v1/interactions", riga)
            fatte["scritte"] += 1
        except RuntimeError as e:
            if "409" in str(e) or "duplicate" in str(e).lower():
                fatte["saltate"] += 1
                continue
            print(f"    non scritta: {e}")
            continue

        # quello che si puo' dire con certezza, e niente di piu'
        chiuso = p.get("pipeline_stage") in ("cliente", "perso") or p.get("stage") in ("cliente", "perso")
        patch = {}
        if kind == "email_in" and not chiuso:
            if (p.get("last_reply_at") or "") < at:
                patch["last_reply_at"] = at
            patch["awaiting_us"] = True
            if p.get("stage") == "nuovo":
                patch["stage"] = "risposto"
                patch["first_reply_at"] = at
        elif kind == "email_out" and not chiuso and p.get("awaiting_us"):
            patch["awaiting_us"] = False
        if patch:
            sb("PATCH", f"/rest/v1/prospects?id=eq.{pid}", patch)
            fatte["aggiornate"] += 1
            p.update(patch)
    return fatte


def main():
    prova = "--prova" in sys.argv
    giorni = 2
    if "--giorni" in sys.argv:
        giorni = int(sys.argv[sys.argv.index("--giorni") + 1])
    chi = None
    if "--chi" in sys.argv:
        chi = sys.argv[sys.argv.index("--chi") + 1]

    persone = caselle(chi)
    if not persone:
        print("Nessuna casella collegata: serve che entrino con Google (permesso Gmail).")
        return
    rubrica = carica_rubrica()
    print(f"Rubrica: {len(rubrica['indice'])} aziende, {len(rubrica['email'])} indirizzi")
    totale = {"scritte": 0, "saltate": 0, "domande": 0, "aggiornate": 0}
    for persona in persone:
        f = macina(persona, rubrica, giorni, prova, limite_domande=5)
        for k in totale:
            totale[k] += f[k]
    print(f"{'(prova) ' if prova else ''}scritte {totale['scritte']}, "
          f"aggiornate {totale['aggiornate']}, saltate {totale['saltate']}, domande {totale['domande']}")


if __name__ == "__main__":
    main()
