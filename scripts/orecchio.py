#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""L'ORECCHIO: Clara legge la casella di Dre (rifatto il 20/10/2026).

PERCHE'
Il 19/10 un lead ha annullato per mail la conoscitiva («ho avuto un imprevisto e devo
annullare l'appuntamento»), fuori dal calendario. Il calendario diceva ancora «call
fissata», il promemoria del giorno prima era pronto a partire, e il lead non tornava fra
quelli da chiamare. La mail stava nella casella di Dre, e nessuno la leggeva.

COSA FA DA SOLO (una cosa sola, decisione del 20/10)
Una mail nella casella di Dre che ANNULLA o SPOSTA la call di un lead che ha una call
in calendario (risposta all'invito, «devo annullare», «possiamo spostare», «non riesco»):
  1. il lead torna a Dre: «Da chiamare» (snella_lead, come dal foglio) se ha lasciato un
     cellulare (firma o scheda, mai il centralino del sito: regola di Dre del 20/10 sera,
     segnale_provvisorio.cellulare_di); se no «Da rispondere» con Dre responsabile e la
     prossima azione che dice perche' (gli scrive lui per rifissarla);
  2. una nota sul lead: «Achille: ha annullato la call per mail»;
  3. il promemoria di quella call si ferma (proposta ref=promemoria:<evento>, stato «no»).
Lo fa solo se due teste concordano: il lettore AI dice annulla o sposta, sicuro, E nel
testo ci sono le parole di un annullamento o di uno spostamento (o e' un «Rifiutato:»
all'invito). Se discordano, non fa niente e lo scrive. Non manda mai una mail, non tocca
il calendario.

TUTTO IL RESTO lo scrive solo nel registro (tabella registro, tabella='gmail_dre'): ogni
mail guardata una volta, con l'esito. Cosi' non si rilegge e si vede cosa ha visto.

PRIMA (17/9-24/9) l'orecchio era un campanello push di Gmail (Pub/Sub) per svegliare il
direttore: serviva un progetto Google Cloud che non c'e' (GOOGLE_CLOUD_PROJECT), 8 corse su 8
in errore, spento il 24/9. Leggere ogni 15 minuti basta, e non chiede niente a nessuno: il
token di Dre ha gia' gmail.readonly.

USO
  python3 scripts/orecchio.py                     il giro (le mail degli ultimi 2 giorni non ancora viste)
  python3 scripts/orecchio.py --prova             cosa farebbe, non scrive niente
  python3 scripts/orecchio.py --prova --giorni 8  a secco su piu' giorni (anche gia' viste)
"""

import base64
import datetime
import json
import os
import re
import sys
import urllib.parse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from stanza import sb, quando                              # noqa: E402

PROVA = "--prova" in sys.argv or os.environ.get("PROVA") == "1"
GIORNI = int(sys.argv[sys.argv.index("--giorni") + 1]) if "--giorni" in sys.argv else 2
DRE = "dramane@studiogalilei.com"
GMAIL = "https://gmail.googleapis.com/gmail/v1/users/me"
NOSTRI = ("studiogalilei.com", "studiogalilei.it")
NOTA_ANNULLA = "Achille: ha annullato la call per mail"
NOTA_SPOSTA = "Achille: ha chiesto per mail di spostare la call"
# la rete di parole: senza una di queste il lettore AI da solo non basta per muovere un lead
PAROLE = re.compile(r"annull|disdir|disdic|disdett|spost|rimand|rinvi|riprogramm|cambiare (data|giorno|orario)|"
                    r"non (riesco|riusciamo|riuscir|potr[oò]|posso|possiamo|ce la faccio)|imprevist|contrattempo|"
                    r"cancel|reschedul|postpone|can.?t make it|unable to (attend|make)|another (day|time)", re.I)
RIFIUTATO = re.compile(r"^\s*(rifiutato|declined|invito rifiutato)\s*:", re.I)
ALTRO_ORARIO = re.compile(r"^\s*(nuovo orario proposto|new time proposed)\b", re.I)
ACCETTATO = re.compile(r"^\s*(accettato|accepted|provvisoriamente accettato|tentatively accepted)\s*:", re.I)
CLIENTI = ("cliente", "prova", "avvio")
GIORNI_AVANTI = 30                    # una call oltre un mese non e' «la call» di cui parla la mail


# ── le decisioni (pure: le prove le chiamano senza rete) ─────────────────────────

def mittente(da):
    m = re.search(r"[\w.+'-]+@[\w-]+(?:\.[\w-]+)+", da or "")
    return m.group(0).lower() if m else ""


def e_nostro(email):
    return email.split("@")[-1] in NOSTRI or email.endswith("google.com") or "noreply" in email or "no-reply" in email


def call_del_lead(email, pid, eventi, at):
    """La prossima call (conoscitiva, tecnica, avvio) del lead dopo la mail: per invitato o per lead."""
    from calendario import esterni, tipo_evento
    buone = []
    for ev in eventi:
        inizio = ev.get("inizio")
        if not inizio or not (at < inizio <= at + datetime.timedelta(days=GIORNI_AVANTI)):
            continue
        if tipo_evento(ev) == "altro":
            continue
        if email in esterni(ev.get("invitati") or []) or (pid and ev.get("pid") == pid):
            buone.append(ev)
    return min(buone, key=lambda e: e["inizio"]) if buone else None


def decidi(oggetto, testo, letto):
    """(cosa, motivo): cosa e' «annulla», «sposta» o None. letto = il lettore AI
    ({cosa, sicuro, perche}) o None se non ha risposto. Agisce solo se le due teste concordano."""
    if ACCETTATO.search(oggetto or ""):
        return None, "ha accettato l'invito"
    if RIFIUTATO.search(oggetto or ""):
        return "annulla", "ha rifiutato l'invito"
    if ALTRO_ORARIO.search(oggetto or ""):
        return "sposta", "ha proposto un altro orario dall'invito"
    parole = bool(PAROLE.search(testo or ""))
    ai = (letto or {}).get("cosa") if (letto or {}).get("sicuro") else None
    if ai in ("annulla", "sposta") and parole:
        return ai, (letto.get("perche") or "")[:160]
    if ai in ("annulla", "sposta"):
        return None, f"dubbio: il lettore dice «{ai}» ma il testo non ne ha le parole, non tocco niente"
    if parole and letto is None:
        return None, "dubbio: il testo ha le parole di un annullamento ma il lettore non ha risposto, non tocco niente"
    if parole:
        return None, f"il lettore dice «{(letto or {}).get('cosa') or 'altro'}» (le parole c'erano): non tocco niente"
    return None, "non parla di annullare o spostare la call"


CHIUSI = ("Perso", "Non interessato", "Non contattare", "Cliente acquisito")


def gia_deciso(p, scelta, note, at):
    """Il motivo per non toccare il lead, o None. Quello che ha deciso Dre vince: se dopo la mail
    ha gia' scritto una nota o cambiato lo stato, o il lead e' chiuso, l'orecchio non lo muove.
    Collaudo del 20/10: il lead che il 19/10 ha annullato per mail, Dre l'aveva gia' chiamato e
    segnato perso un'ora dopo; riportarlo a «Da chiamare» sarebbe stato un errore."""
    if p.get("stage") in ("perso", "cliente") or p.get("pipeline_stage") in ("perso",) + CLIENTI:
        return f"il lead e' gia' «{p.get('pipeline_stage') or p.get('stage')}»"
    if (scelta or {}).get("stato") in CHIUSI:
        return f"Dre l'ha gia' messo in «{scelta['stato']}»"
    if (scelta or {}).get("aggiornato_il") and quando(scelta["aggiornato_il"]) > at:
        return "Dre ha gia' cambiato il lead dopo la mail"
    if any(n.get("at") and quando(n["at"]) > at for n in note or []):
        return "c'e' gia' una nota sul lead dopo la mail"
    return None


def scritture(pid, evento, cosa, oggi, call_at=None, cellulare=None, ora=None):
    """Le tre scritture di un annullamento: (tabella, riga). Niente mail, niente calendario.
    `cellulare`: il suo, se c'e' (segnale_provvisorio.cellulare_di): senza, non e' «Da chiamare»."""
    import segnale_provvisorio as SP
    ora = ora or datetime.datetime.now(datetime.timezone.utc)
    riga = SP.passa_a_dre(pid, cellulare, ora)
    if not cellulare:
        riga["prossima_mossa"] = ("Ha annullato la call per mail" if cosa == "annulla" else "Ha chiesto per mail di spostare la call") \
            + " e non ha lasciato un cellulare: scrivigli per rifissarla"
    return [
        ("snella_lead", riga),
        ("snella_note", {"prospect_id": pid, "testo": NOTA_ANNULLA if cosa == "annulla" else NOTA_SPOSTA,
                         "tipo": "nota", "autore_nome": "Achille"}),
        # call_at: cosi' il foglio sa QUALE call e' saltata e non la mostra piu' come «Chiamata conoscitiva»
        ("promemoria", {"ref": f"promemoria:{evento}", "prospect_id": pid, "call_at": call_at}),
    ]


# ── il lettore AI ────────────────────────────────────────────────────────────────

SCHEMA = {"type": "json_schema", "json_schema": {"name": "call", "strict": True, "schema": {
    "type": "object", "additionalProperties": False, "required": ["cosa", "sicuro", "perche"],
    "properties": {"cosa": {"type": "string", "enum": ["annulla", "sposta", "conferma", "altro"]},
                   "sicuro": {"type": "boolean"}, "perche": {"type": "string"}}}}}


def leggi_con_ai(oggetto, testo, quando_call):
    """Il senso lo decide l'AI (regola del 12/10). None se non risponde: allora non si agisce."""
    prompt = (f"Questa mail arriva da un lead che ha una call fissata con noi per {quando_call}.\n"
              "Domanda: la mail annulla la call, chiede di spostarla, la conferma, o parla d'altro?\n"
              "«annulla»: disdice, non verra', ha un imprevisto e la cancella. «sposta»: chiede un altro giorno o\n"
              "orario, rimanda. «conferma»: ci sara'. «altro»: tutto il resto (domande, materiale, ringraziamenti).\n"
              "sicuro=true solo se la mail lo dice chiaramente, con parole sue (non la nostra mail citata sotto).\n"
              "perche: una frase.\n\n"
              f"OGGETTO: {oggetto[:200]}\nTESTO:\n{testo[:2500]}")
    try:
        import cervello
        r = cervello._chiedi_openai(prompt, "gpt-5", formato=SCHEMA, fornitore="openai", tetto=2500, sforzo="low")
        d = json.loads(r)
        return d if isinstance(d, dict) and d.get("cosa") else None
    except Exception as e:                                     # noqa: BLE001
        print(f"  (lettore AI non disponibile: {str(e)[:100]})")
        return None


# ── la posta ─────────────────────────────────────────────────────────────────────

def _testo(payload):
    """Il testo semplice della mail (o l'html ripulito), senza la parte citata."""
    piani, html = [], []
    def giro(p):
        dati = (p.get("body") or {}).get("data")
        if dati:
            t = base64.urlsafe_b64decode(dati + "=" * (-len(dati) % 4)).decode("utf-8", errors="replace")
            (piani if p.get("mimeType") == "text/plain" else html if p.get("mimeType") == "text/html" else []).append(t)
        for q in p.get("parts") or []:
            giro(q)
    giro(payload or {})
    t = "\n".join(piani) or re.sub(r"<[^>]+>", " ", "\n".join(html))
    try:
        from lettura import solo_suo
        return solo_suo(t, con_firma=False) or t[:3000]
    except Exception:                                          # noqa: BLE001
        return t[:3000]


def mail_recenti(giorni):
    from google_api import g
    q = urllib.parse.urlencode({"q": f"newer_than:{giorni}d -from:me -in:chats", "maxResults": 200})
    out = []
    for m in (g("GET", f"{GMAIL}/messages?{q}", email=DRE) or {}).get("messages") or []:
        x = g("GET", f"{GMAIL}/messages/{m['id']}?format=full", email=DRE) or {}
        h = {k["name"].lower(): k["value"] for k in (x.get("payload") or {}).get("headers") or []}
        out.append({"id": m["id"], "da": h.get("from", ""), "oggetto": h.get("subject", ""),
                    "at": datetime.datetime.fromtimestamp(int(x.get("internalDate", "0")) / 1000, datetime.timezone.utc),
                    "payload": x.get("payload")})
    return out


def gia_viste(ids):
    if not ids:
        return set()
    righe = sb("GET", f"/rest/v1/registro?select=riga&tabella=eq.gmail_dre&riga=in.({','.join(ids)})") or []
    return {r["riga"] for r in righe}


def scrivi_registro(mid, esito):
    if PROVA:
        return
    sb("POST", "/rest/v1/registro", {"tabella": "gmail_dre", "riga": mid, "campo": "orecchio", "dopo": esito[:500], "chi": "orecchio"},
       {"Prefer": "return=minimal"})


def applica(pid, ev, cosa, oggi, cellulare=None):
    inizio = ev.get("inizio")
    for tabella, riga in scritture(pid, ev["evento"], cosa, oggi, inizio.isoformat() if inizio else None, cellulare):
        if tabella == "snella_lead":
            sb("POST", "/rest/v1/snella_lead?on_conflict=prospect_id", [riga], {"Prefer": "resolution=merge-duplicates,return=minimal"})
        elif tabella == "snella_note":
            sb("POST", "/rest/v1/snella_note", riga, {"Prefer": "return=minimal"})
        else:
            ref = urllib.parse.quote(riga["ref"], safe="")
            gia = sb("GET", f"/rest/v1/proposte?select=id,stato&ref=eq.{ref}&limit=1") or []
            motivo = NOTA_ANNULLA if cosa == "annulla" else NOTA_SPOSTA
            if gia and gia[0]["stato"] in ("aperta", "approvata"):
                sb("PATCH", f"/rest/v1/proposte?id=eq.{gia[0]['id']}", {"stato": "no", "risposta": motivo, "azione": {"call_at": riga.get("call_at")},
                   "risposta_il": datetime.datetime.now(datetime.timezone.utc).isoformat()}, {"Prefer": "return=minimal"})
            elif not gia:
                sb("POST", "/rest/v1/proposte", {"tipo": "umano", "stato": "no", "ref": riga["ref"], "prospect_id": pid, "azione": {"call_at": riga.get("call_at")},
                   "titolo": "Promemoria fermato: la call e' stata annullata per mail", "risposta": motivo,
                   "risposta_il": datetime.datetime.now(datetime.timezone.utc).isoformat()}, {"Prefer": "return=minimal"})
    if cosa == "annulla" and inizio:
        segna_annullata(pid, inizio)


def segna_annullata(pid, inizio):
    """LA CALL ANNULLATA STA IN UN POSTO SOLO (notte del 22/10): la riga dell'agenda diventa
    «annullata», come quando l'evento sparisce dal calendario (calendario.py). Prima l'annullamento
    per mail lo sapeva solo il foglio (dai promemoria fermati): la scheda diceva ancora «Call
    fissata», la preparazione preparava la call e le categorie la tenevano. Torna quante righe."""
    da = (inizio - datetime.timedelta(minutes=1)).astimezone(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")
    a = (inizio + datetime.timedelta(minutes=1)).astimezone(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")
    righe = sb("GET", f"/rest/v1/agenda?select=id&prospect_id=eq.{pid}&tipo=neq.annullata&at=gte.{da}&at=lte.{a}") or []
    for r in righe:
        sb("PATCH", f"/rest/v1/agenda?id=eq.{r['id']}", {"tipo": "annullata"}, {"Prefer": "return=minimal"})
    return len(righe)


def main():
    import segnale_provvisorio as SP
    import calendario as C
    adesso = datetime.datetime.now(datetime.timezone.utc)
    mails = mail_recenti(GIORNI)
    viste = set() if PROVA else gia_viste([m["id"] for m in mails])
    nuove = [m for m in mails if m["id"] not in viste]
    print(f"orecchio{' (prova: non scrive niente)' if PROVA else ''}: {len(mails)} mail negli ultimi {GIORNI} giorni, {len(nuove)} da guardare")
    # le nostre e quelle dei servizi si segnano subito: per loro non serve leggere calendario e lead
    for m in [m for m in nuove if not mittente(m["da"]) or e_nostro(mittente(m["da"]))]:
        scrivi_registro(m["id"], "non e' di un lead (nostra o di un servizio)")
    nuove = [m for m in nuove if mittente(m["da"]) and not e_nostro(mittente(m["da"]))]
    if not nuove:
        return
    eventi = SP._eventi_calendario(min(m["at"] for m in nuove))
    prospects = C.carica_prospects()
    for ev in eventi:
        if ev.get("inizio") and C.tipo_evento(ev) != "altro":
            ev["pid"] = SP._riconosci(ev)
    oggi = adesso.astimezone(SP.ROMA).date()
    mossi = 0
    for m in sorted(nuove, key=lambda m: m["at"]):
        email = mittente(m["da"])
        pid, _ = C.riconosci({"invitati": [email], "titolo": "", "descrizione": ""}, prospects)
        ev = call_del_lead(email, pid, eventi, m["at"])
        if not ev:
            scrivi_registro(m["id"], f"{email}: nessuna call in calendario dopo la mail, non tocco niente")
            continue
        pid = pid or ev.get("pid")
        p = (sb("GET", f"/rest/v1/prospects?select=id,company,stage,pipeline_stage,phone,enriched&id=eq.{pid}") or [None])[0] if pid else None
        if not p:
            scrivi_registro(m["id"], f"{email}: la call c'e' ma non e' abbinata a un lead, non tocco niente")
            print(f"  {email}: call del {ev['inizio'].astimezone(SP.ROMA):%d/%m %H:%M} senza lead abbinato")
            continue
        if p.get("stage") == "cliente" or p.get("pipeline_stage") in CLIENTI:
            scrivi_registro(m["id"], f"{email}: e' un cliente, le sue call le segue Dre")
            continue
        testo = _testo(m["payload"])
        quando_call = ev["inizio"].astimezone(SP.ROMA).strftime("%d/%m alle %H:%M")
        letto = None if (ACCETTATO.search(m["oggetto"]) or RIFIUTATO.search(m["oggetto"])) else leggi_con_ai(m["oggetto"], testo, quando_call)
        cosa, motivo = decidi(m["oggetto"], testo, letto)
        riga = f"{p.get('company') or email}, call del {quando_call}: {cosa or 'niente'} ({motivo})"
        print(f"  {m['at'].astimezone(SP.ROMA):%d/%m %H:%M} {riga}")
        if cosa:
            scelta = (sb("GET", f"/rest/v1/snella_lead?select=stato,aggiornato_il&prospect_id=eq.{pid}") or [None])[0]
            note = sb("GET", f"/rest/v1/snella_note?select=at&prospect_id=eq.{pid}&order=at.desc&limit=5") or []
            fermo = gia_deciso(p, scelta, note, m["at"])
            if fermo:
                riga += f", ma non lo muovo: {fermo}"
                print(f"      non lo muovo: {fermo}")
            else:
                cellulare = SP.cellulare_di(p)
                riga += ", torna «Da chiamare»" if cellulare else ", senza cellulare: «Da rispondere», gli scrive Dre"
                print(f"      {'ha un cellulare: Da chiamare' if cellulare else 'nessun cellulare: Da rispondere, gli scrive Dre'}")
                if not PROVA:
                    applica(pid, ev, cosa, oggi, cellulare)
                    mossi += 1
        scrivi_registro(m["id"], riga)
    print(f"orecchio: {mossi} lead tornati a Dre" + (" (prova)" if PROVA else ""))


if __name__ == "__main__":
    main()
