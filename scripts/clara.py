#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Clara, la segretaria: il giro del mattino.

Legge Supabase e scrive i suoi messaggi nella tabella clara_messaggi:
  - il BRIEF del giorno (uno solo: se c'e' gia', non lo riscrive)
  - i PROMEMORIA concreti (call di oggi, prove in scadenza, fermi da un mese)

Il carattere e il mandato stanno in ODYN Cockpit/prompts/CLARA.md.
Regola d'oro: Clara prepara e avvisa, non invia mai niente.

    clara.py            # il giro del mattino
    clara.py --prova    # scrive un brief di prova anche se ce n'e' gia' uno
"""
import json
import re
import os
import sys
import urllib.request
from datetime import date, datetime, timedelta, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SEGRETI = os.path.expanduser(
    "~/Documents/Obsidian/studiogalilei/Falcon Studio/.falcon-bridge/secrets.env")
HERMES = os.path.expanduser("~/.hermes/config.yaml")


def env():
    # in cloud il file non c'e': le chiavi arrivano dall'ambiente (righe sotto)
    out = {}
    p = os.path.join(ROOT, ".env.local")
    if not os.path.exists(p):
        return out
    with open(p) as f:
        for r in f:
            r = r.strip()
            if r and not r.startswith("#") and "=" in r:
                k, v = r.split("=", 1)
                out[k.strip()] = v.strip()
    return out


ENV = env()
URL = (os.environ.get("VITE_SUPABASE_URL") or ENV.get("VITE_SUPABASE_URL", "")).rstrip("/")
KEY = os.environ.get("SUPABASE_SERVICE_KEY") or ENV.get("SUPABASE_SERVICE_KEY", "")
if not URL or not KEY:
    sys.exit("manca VITE_SUPABASE_URL o SUPABASE_SERVICE_KEY in .env.local")


def api(percorso, dati=None, metodo="GET"):
    """Una chiamata che fallisce non deve buttare giu' tutto il giro del
    mattino: prima un errore qui moriva dentro launchd senza che si vedesse."""
    req = urllib.request.Request(
        f"{URL}/rest/v1/{percorso}",
        data=json.dumps(dati).encode() if dati is not None else None,
        headers={
            "apikey": KEY, "Authorization": f"Bearer {KEY}",
            "Content-Type": "application/json", "Prefer": "return=representation",
        },
        method=metodo)
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            corpo = r.read()
            return json.loads(corpo) if corpo else []
    except Exception as e:                                  # noqa: BLE001
        print(f"  ! {metodo} {percorso.split('?')[0]}: {e}")
        return []


def iso_utc(dt):
    """ISO in UTC con la Z. isoformat() mette «+00:00» e il «+» dentro un URL
    viene letto come spazio: il filtro arrivava malformato."""
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def ora_italiana(iso):
    """L'ora come la legge Dre. Supabase risponde in UTC: il brief diceva
    «13:00» per una call delle 15:00."""
    if not iso:
        return "??:??"
    try:
        t = datetime.fromisoformat(iso.replace("Z", "+00:00"))
    except ValueError:
        return "??:??"
    if t.tzinfo is None:
        t = t.replace(tzinfo=timezone.utc)
    return t.astimezone().strftime("%H:%M")


def pulisci(testo):
    """Il trattino lungo e' bandito (Dre, 31/8).

    Copia esatta di pulisci() in src/lib/regole.ts: se cambia una, cambia
    l'altra, se no Clara scrive in due modi a seconda di chi la chiama.
    """
    return re.sub(r"\s*—\s*", ": ", testo).replace("–", "-")


def scrivi(tipo, testo, prospect_id=None):
    testo = pulisci(testo)
    api("clara_messaggi", {"tipo": tipo, "testo": testo, "prospect_id": prospect_id}, "POST")
    print(f"  {tipo}: {testo[:70]}")


GIORNI_FOLLOWUP = 6   # Dre (9/9)


def dovuto(p, oggi):
    """Se questo follow-up e' dovuto oggi.

    Copia esatta del ramo 'followup' di codaDiOggi() in src/lib/regole.ts:
    una data sua vince sul conto dei giorni, perche' e' la ragione per cui
    sta in lista. Se cambia una, cambia l'altra: se no il saluto in testata
    e il Radar sotto contano due code diverse.
    """
    if p.get("followup_due"):
        return p["followup_due"][:10] <= oggi
    return (gg_fa(p.get("analysis_sent_at")) or 0) >= GIORNI_FOLLOWUP


def gg_fa(iso):
    if not iso:
        return None
    try:
        t = datetime.fromisoformat(iso.replace("Z", "+00:00"))
        return (datetime.now(timezone.utc) - t).days
    except ValueError:
        return None


def leggi_file_env(percorso):
    out = {}
    if os.path.exists(percorso):
        for r in open(percorso):
            r = r.strip()
            if r and not r.startswith("#") and "=" in r:
                k, v = r.split("=", 1)
                out[k.strip()] = v.strip()
    return out


def chiave_smartlead():
    k = os.environ.get("SMARTLEAD_API_KEY")
    if k:
        return k.strip().strip("'\"")
    if not os.path.exists(HERMES):
        return None
    for r in open(HERMES):
        if r.strip().startswith("SMARTLEAD_API_KEY"):
            return r.split(":", 1)[1].strip().strip("'\"")
    return None


def http_json(url, dati=None):
    req = urllib.request.Request(
        url,
        data=json.dumps(dati).encode() if dati is not None else None,
        headers={"Content-Type": "application/json",
                 "User-Agent": "clara/1.0"},
        method="POST" if dati is not None else "GET")
    with urllib.request.urlopen(req, timeout=40) as r:
        return json.loads(r.read())


def sorveglia_domini(lunedi):
    """Porkbun: scadenze e rinnovi. Anomalia se un dominio sta per scadere
    senza auto-rinnovo; il lunedi' un riepilogo che dice che va tutto bene."""
    env = leggi_file_env(SEGRETI)
    k, sec = env.get("PORKBUN_API_KEY"), env.get("PORKBUN_SECRET_KEY")
    if not k or not sec:
        return
    try:
        r = http_json("https://api.porkbun.com/api/json/v3/domain/listAll",
                      {"apikey": k, "secretapikey": sec})
    except Exception as e:
        scrivi("anomalia", f"Non riesco a controllare i domini su Porkbun ({e}).")
        return
    domini = r.get("domains") or []
    fra30 = (date.today() + timedelta(days=30)).isoformat()
    fra15 = (date.today() + timedelta(days=15)).isoformat()
    problemi = 0
    for d in domini:
        scade = str(d.get("expireDate", ""))[:10]
        auto = str(d.get("autoRenew", "0")) in ("1", "true", "True")
        nome = d.get("domain", "?")
        if scade and scade <= fra30 and not auto:
            scrivi("anomalia",
                   f"Il dominio {nome} scade il {scade} SENZA auto-rinnovo: "
                   f"si perde la posta se non si rinnova.")
            problemi += 1
        elif scade and scade <= fra15 and auto:
            scrivi("promemoria",
                   f"Il dominio {nome} si rinnova da solo intorno al {scade}: "
                   f"arriva l'addebito Porkbun.")
    if lunedi and problemi == 0 and domini:
        prossima = min((str(d.get("expireDate", ""))[:10] for d in domini
                        if d.get("expireDate")), default="?")
        scrivi("controllo",
               f"Domini: {len(domini)} attivi su Porkbun, rinnovi in ordine. "
               f"Prossima scadenza: {prossima}.")


def sorveglia_caselle(lunedi):
    """Smartlead: warmup e reputazione con le soglie di Ali (playbook):
    sotto 80% si stacca 5-7 giorni, warmup MAI spento."""
    api_key = chiave_smartlead()
    if not api_key:
        return
    try:
        conti = http_json("https://server.smartlead.ai/api/v1/email-accounts/"
                          f"?api_key={api_key}&offset=0&limit=100")
    except Exception as e:
        scrivi("anomalia", f"Non riesco a leggere le caselle su Smartlead ({e}).")
        return
    if isinstance(conti, dict):
        conti = conti.get("email_accounts") or conti.get("data") or []
    male, spenti, tot = [], [], 0
    for c in conti or []:
        email = c.get("from_email") or c.get("email") or "?"
        w = c.get("warmup_details") or {}
        stato_w = str(c.get("warmup_status") or w.get("status") or "").lower()
        rep = str(w.get("warmup_reputation") or "").replace("%", "")
        tot += 1
        if stato_w and stato_w not in ("active", "enabled", "on", "warming"):
            spenti.append(email)
        try:
            if rep and float(rep) < 80:
                male.append((email, rep))
        except ValueError:
            pass
    if spenti:
        scrivi("anomalia",
               f"Warmup SPENTO su {len(spenti)} casell{'a' if len(spenti) == 1 else 'e'} "
               f"({', '.join(spenti[:3])}{'…' if len(spenti) > 3 else ''}): "
               f"la regola è che non si spegne mai.")
    for email, rep in male[:3]:
        scrivi("anomalia",
               f"La casella {email} ha reputazione {rep}%: sotto la soglia. "
               f"Da staccare 5-7 giorni (playbook di Ali).")
    if lunedi and not spenti and not male and tot:
        scrivi("controllo",
               f"Caselle: {tot} controllate su Smartlead, warmup acceso e "
               f"reputazione sopra soglia per tutte.")


def sorveglia_call_fissate():
    """Il buco fra Smartlead e Calendar: se dal thread risulta una call
    fissata (stage call_fissata dal sync) ma in agenda non c'e' niente di
    futuro per quel prospect, dopo un po' di ore Clara lo chiede a Dre.
    Formato voluto da Dre (31/8), non si cambia."""
    adesso = datetime.now(timezone.utc)
    fissate = api('prospects?stage=eq.call_fissata&fuori=eq.false'
                  '&select=id,company,name,email,last_reply_at,next_action_date')
    if not fissate:
        return
    ids = ",".join(f'"{p["id"]}"' for p in fissate)
    # coperto = la call sta in agenda, anche se e' gia' avvenuta: guardando
    # solo il futuro, a call fatta Clara la richiedeva ogni settimana
    mese_fa = iso_utc(adesso - timedelta(days=30))
    in_agenda = api(f'agenda?prospect_id=in.({ids})&at=gte.{mese_fa}'
                    '&select=prospect_id')
    coperti = {a["prospect_id"] for a in in_agenda}
    settimana_fa = iso_utc(adesso - timedelta(days=7))
    gia_chieste = api(f'clara_messaggi?tipo=eq.domanda&at=gte.{settimana_fa}'
                      '&select=prospect_id,testo')
    for p in fissate:
        if p["id"] in coperti:
            continue
        if p.get("next_action_date") and p["next_action_date"] >= date.today().isoformat():
            continue
        # senza last_reply_at non c'e' niente di recente da aspettare: si
        # chiede subito. Prima ore restava 0 e Clara non chiedeva MAI.
        ore = 10_000
        if p.get("last_reply_at"):
            try:
                t = datetime.fromisoformat(p["last_reply_at"].replace("Z", "+00:00"))
                if t.tzinfo is None:
                    t = t.replace(tzinfo=timezone.utc)
                ore = (adesso - t).total_seconds() / 3600
            except ValueError:
                pass
        if ore < 3:      # la grazia: magari la sta fissando adesso
            continue
        if any(g.get("prospect_id") == p["id"] and "in Calendar non vedo" in (g.get("testo") or "")
               for g in gia_chieste):
            continue
        nome = p.get("company") or p.get("name") or p.get("email")
        scrivi("domanda",
               f"Ciao Dre, ho visto che su Smartlead hai fissato una call con "
               f"{nome}, però in Calendar non vedo nulla. Vuoi che la preparo io?",
               p["id"])


PUNTO_OGGI = []   # le righe del brief, che vanno anche in calendario (23/9: la chat e' spenta)


def punto_in_calendario(righe, prova):
    """«Clara: il punto di oggi», un evento a giornata intera in SG Scadenze, uno al giorno."""
    try:
        sys.path.insert(0, HERE)
        import calendario_sg as cal
        cid = cal.calendario(prova)
        if not cid:
            return
        cal.scrivi(cid, f"punto-{date.today().isoformat()}", "Clara: il punto di oggi", date.today().isoformat(), "\n".join(righe), prova)
        print("  il punto di oggi e' in calendario")
    except Exception as e:                                        # noqa: BLE001
        print(f"  punto non scritto in calendario: {str(e)[:120]}")


def main():
    prova = "--prova" in sys.argv
    oggi = date.today().isoformat()
    # la giornata italiana, tradotta in UTC per il database
    inizio = datetime.now().astimezone().replace(hour=0, minute=0, second=0, microsecond=0)

    # il brief e' uno al giorno
    di_oggi = api(f"clara_messaggi?tipo=eq.brief&at=gte.{iso_utc(inizio)}&select=id")
    if di_oggi and not prova:
        print("brief di oggi gia' scritto")
        return

    vivi = ("classificazione.is.null,"
            'classificazione.not.in.("negativo","fuori_target","soppresso")')

    agenda = api(f"agenda?at=gte.{iso_utc(inizio)}"
                 f"&at=lt.{iso_utc(inizio + timedelta(days=1))}&order=at")
    da_risp = api(f"prospects?awaiting_us=eq.true&fuori=eq.false&or=({vivi})&select=id")
    in_pipe = api('prospects?fuori=eq.true&pipeline_stage=in.("conoscitiva","tecnica","avvio")')
    inviate = api(f"prospects?stage=in.(\"analisi_inviata\",\"in_follow_up\")"
                  f"&awaiting_us=eq.false&fuori=eq.false"
                  f"&no_followup=eq.false&or=({vivi})"
                  f"&select=id,company,name,analysis_sent_at,followup_due")
    ricontatti = api(f"prospects?next_action_date=not.is.null&next_action_date=lte.{oggi}"
                     f"&or=({vivi})&select=id")
    rientri = api(f"prospects?ooo_until=not.is.null&ooo_until=lte.{oggi}"
                  f"&no_followup=eq.false&fuori=eq.false&or=({vivi})&select=id")
    clienti = api('prospects?pipeline_stage=eq.cliente')

    dovuti = [p for p in inviate if dovuto(p, oggi)]
    fermi = [p for p in inviate if (gg_fa(p.get("analysis_sent_at")) or 0) >= 30]

    # ── il saluto in testata: il suo spazio nella UI ─────────────
    giorni_it = ["Lunedì", "Martedì", "Mercoledì", "Giovedì",
                 "Venerdì", "Sabato", "Domenica"]
    nome_giorno = giorni_it[date.today().weekday()]
    # la coda: le stesse quattro ragioni della Dashboard, nello stesso
    # ordine, contate una volta sola per persona
    visti = set()
    per_ragione = {}
    for nome_gruppo, righe in (("rispondere", da_risp), ("follow-up", dovuti),
                               ("ricontatti", ricontatti), ("rientri", rientri)):
        quanti = 0
        for p in righe:
            if p["id"] in visti:
                continue
            visti.add(p["id"])
            quanti += 1
        per_ragione[nome_gruppo] = quanti
    conta_coda = len(visti)
    if agenda and conta_coda > 3:
        saluto = (f"Buongiorno Dre. {nome_giorno} pieno: "
                  f"{len(agenda)} call e {conta_coda} in coda. Si parte dalla prima.")
    elif agenda:
        saluto = (f"Buongiorno Dre. {nome_giorno} con "
                  f"{'una call' if len(agenda) == 1 else str(len(agenda)) + ' call'}"
                  f" e coda corta: giornata buona.")
    elif conta_coda > 0:
        saluto = (f"Buongiorno Dre. Niente call oggi: "
                  f"{conta_coda} in coda e poi sei libero.")
    else:
        saluto = f"Buongiorno Dre. {nome_giorno} pulito: tutto in ordine."
    scrivi("saluto", saluto)
    PUNTO_OGGI.append(saluto)

    # ── il brief ─────────────────────────────────────────────────
    righe = ["Buongiorno Dre. Il punto di oggi:"]
    if agenda:
        for a in agenda[:3]:
            righe.append(f"• {ora_italiana(a['at'])}: {a['titolo']}")
    else:
        righe.append("• Nessuna call in calendario.")
    if conta_coda:
        etichette = {
            "rispondere": ("da rispondere", "da rispondere"),
            "follow-up": ("follow-up dovuto", "follow-up dovuti"),
            "ricontatti": ("con la data arrivata", "con la data arrivata"),
            "rientri": ("rientrato dalle ferie", "rientrati dalle ferie"),
        }
        pezzi = [f"{n} {etichette[g][0 if n == 1 else 1]}"
                 for g, n in per_ragione.items() if n]
        righe.append("• In coda: " + ", ".join(pezzi) + ".")
    else:
        righe.append("• Coda pulita: nessun lead aspetta te.")
    righe.append("Ho controllato tutto io. Il resto è nella sezione Task.")
    scrivi("brief", "\n".join(righe))
    punto_in_calendario(righe, prova)

    # ── i promemoria concreti ────────────────────────────────────
    for c in clienti:
        if c.get("contratto") == "prova" and c.get("fuori_at"):
            giorno = gg_fa(c["fuori_at"])
            if giorno is not None and giorno >= 50:
                scrivi("promemoria",
                       f"{c.get('company') or c.get('name')}: giorno {giorno} di 60 "
                       f"del periodo di prova. Prepariamo il rinnovo?", c["id"])

    if fermi and date.today().weekday() == 0:   # il lunedi', non tutti i giorni
        scrivi("promemoria",
               f"{len(fermi)} prospect tacciono da più di un mese dopo l'analisi. "
               f"Li trovi in Task: decidiamo chi lasciar andare?")

    # ── la sorveglianza autonoma: domini, caselle, soldi ─────────
    lunedi = date.today().weekday() == 0
    sorveglia_domini(lunedi)
    sorveglia_caselle(lunedi)
    sorveglia_call_fissate()

    print("giro finito")


if __name__ == "__main__":
    main()
