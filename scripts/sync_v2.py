#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ODYN CRM — SYNC V2, il segugio affidabile (7 lug 2026).

PERCHE' ESISTE: il vecchio giro (sl_tracker su endpoint /statistics) perdeva
risposte in silenzio — statistics e' paginato+rate-limitato e sotto-restituisce
senza errore. Le vittime le ha trovate Dre a mano. Mai piu'.

COME FUNZIONA (fonte diretta, riconciliata):
  1. Per ogni campagna (non archiviata, no "Best Campaign"):
     scarica l'EXPORT CSV completo /campaigns/{id}/leads-export — UNA chiamata,
     tutti i lead con reply_count VERO, categoria Smartlead e unsubscribe.
     (l'endpoint /leads paginato NON espone reply_count: scoperto il 7/7 sera,
      era la maglia larga residua della rete)
     RICONCILIA: righe CSV vs lead attesi -> se non tornano, anomalia segnalata.
  2. Per ogni lead con reply_count>0 (o gia' noto a DB come risposto):
     legge il thread completo /message-history e calcola:
       - awaiting_us: l'ultimo messaggio e' del lead -> tocca a noi
       - classificazione euristica (positivo/tiepido/negativo/ooo/rinvio/da_classificare)
       - date: last_reply_at, ooo_until, followup_due
  3. Upsert su Supabase (prospects + interactions) SENZA toccare:
     stage bloccati (cliente, call_fissata, perso, rinviato), fuori=true,
     classificazione corretta a mano (enriched.classificazione == 'manual'),
     e nessun campo compilato a mano.
  4. Scrive la corsa in sync_runs: numeri, riconciliazione, anomalie.
     Se qualcosa non torna -> ok=false e lo dice FORTE in output.

Uso:  python3 scripts/sync_v2.py            # sync completo
      python3 scripts/sync_v2.py --dry-run  # mostra cosa farebbe, non scrive
"""
import csv as csvmod
import io
import json, os, re, sys, time, html as ihtml
import urllib.request, urllib.parse, urllib.error
from datetime import date, datetime, timedelta

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DRY = "--dry-run" in sys.argv
# INCREMENTALE (7/9/2026): Dre vuole i messaggi nuovi «in realtime o quasi».
# L'export CSV di ogni campagna costa una chiamata e dice reply_count, categoria,
# stato: se per un lead non e' cambiato niente da quando l'abbiamo letto
# (enriched.sl_firma), il thread non si riscarica. Cosi' il giro passa da ~10
# minuti a meno di uno e puo' girare ogni 15. Il giro completo (--completo)
# resta una volta al giorno, per non fidarsi mai di una firma sola.
COMPLETO = "--completo" in sys.argv

# ---------- config ----------
def load_env():
    env = {}
    p = os.path.join(ROOT, ".env.local")
    if os.path.exists(p):
        for line in open(p):
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                env[k.strip()] = v.strip()
    return env

ENV = load_env()
SB_URL = (os.environ.get("VITE_SUPABASE_URL") or ENV.get("VITE_SUPABASE_URL", "")).rstrip("/")
SB_KEY = os.environ.get("SUPABASE_SERVICE_KEY") or ENV.get("SUPABASE_SERVICE_KEY", "")
if not SB_URL or not SB_KEY:
    sys.exit("ERRORE: compila .env.local (VITE_SUPABASE_URL + SUPABASE_SERVICE_KEY)")

def sl_key():
    # in cloud arriva dall'ambiente (o da .env.local); sul Mac di Dre sta in Hermes
    k = os.environ.get("SMARTLEAD_API_KEY") or ENV.get("SMARTLEAD_API_KEY")
    if k:
        return k.strip().strip('"\'')
    p = os.path.expanduser("~/.hermes/config.yaml")
    if os.path.exists(p):
        for line in open(p):
            m = re.match(r"\s*SMARTLEAD_API_KEY:\s*(\S+)", line)
            if m:
                return m.group(1).strip().strip('"\'')
    sys.exit("ERRORE: SMARTLEAD_API_KEY non trovata (ambiente, .env.local o ~/.hermes/config.yaml)")

SL_KEY = sl_key()
SL_BASE = "https://server.smartlead.ai/api/v1"

# ---------- http ----------
def sl_get(path, tries=7):
    """GET Smartlead con retry robusto (401 transitori da rate-limit)."""
    sep = "&" if "?" in path else "?"
    url = f"{SL_BASE}{path}{sep}api_key={SL_KEY}"
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "odyn-sync/2.0"})
            with urllib.request.urlopen(req, timeout=60) as r:
                return json.loads(r.read())
        except Exception as e:
            if i == tries - 1:
                raise RuntimeError(f"Smartlead GET fallita dopo {tries} tentativi: {path} ({e})")
            time.sleep(1.5 * (i + 1))

def sl_export(cid, tries=5):
    """Export CSV completo della campagna: la fonte AUTOREVOLE per reply_count."""
    url = f"{SL_BASE}/campaigns/{cid}/leads-export?api_key={SL_KEY}"
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "odyn-sync/2.0"})
            with urllib.request.urlopen(req, timeout=180) as r:
                raw = r.read().decode(errors="replace")
            return list(csvmod.DictReader(io.StringIO(raw)))
        except Exception as e:
            if i == tries - 1:
                raise RuntimeError(f"leads-export fallito per campagna {cid}: {e}")
            time.sleep(2 * (i + 1))

# categoria Smartlead -> suggerimento di classificazione (il testo del thread vince)
CAT_HINT = {
    "Interested": "positivo", "Meeting Request": "positivo", "Information Request": "positivo",
    "Not Interested": "negativo", "Do Not Contact": "negativo",
    "Out Of Office": "ooo", "Wrong Person": "da_classificare",
}

def sb(method, path, body=None, headers=None):
    req = urllib.request.Request(
        SB_URL + path,
        data=json.dumps(body).encode() if body is not None else None,
        method=method,
    )
    req.add_header("apikey", SB_KEY)
    req.add_header("Authorization", f"Bearer {SB_KEY}")
    req.add_header("Content-Type", "application/json")
    for k, v in (headers or {}).items():
        req.add_header(k, v)
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            data = r.read()
            return json.loads(data) if data else None
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"Supabase {method} {path}: {e.code} {e.read().decode()[:300]}")

# ---------- classificazione euristica (proposta, mai verita' assoluta) ----------
NEG = re.compile(r"non (siamo|sono) interessat|non mi interessa|no,?\s*grazie|non interessa|basta spam|"
                 r"cancellat|rimuov|non voglio|ci occupiamo (gia|già)|abbiamo gia|unsubscribe|non desidero|"
                 r"togliet|non fa per noi|non abbiamo (intenzione|interesse|budget)|siamo (a posto|copert)|"
                 r"^\s*(stop|no|remove)\b|non contattarmi|non scriv|gia'? seguiti|già seguiti", re.I)
OOO = re.compile(r"out of (the )?office|fuori ufficio|assenza|assente|in ferie|maternit|paternit|congedo|"
                 r"rientr|automatic reply|risposta automatica|messaggio automatico|autorepl|vacation|"
                 r"i'?ll be (back|out)|accesso limitato", re.I)
CAMBIO = re.compile(r"non (e'|è) piu' (attiv|in uso)|non è più (attiv|in uso)|verra' dismess|verrà dismess|"
                    r"nuovo indirizzo|casella.*(chius|dismess|disattiv)|non collabora piu|non collabora più|"
                    r"non ricopro piu|non ricopro più|non fa più parte|non faccio più parte", re.I)
POS = re.compile(r"interessat[oa]|mi interessa|volentieri|va bene|invii pure|invia pure|inviate pure|"
                 r"mi mandi|puo' mandare|può mandare|sentiamo|chiamat|telefonat|fissiamo|"
                 r"disponibil|ci dica|quanto cost|come funziona|aspetto|attendo|ricevo|con piacere|"
                 r"mi piacerebbe|me la invii|mandi pure|\bcall\b|videochiamata|ok\b", re.I)
RINVIO = re.compile(r"(risentiamo|sentiamoci|riparliamone|ricontatt\w+|riprend\w+)\s*(ci|mi|pure)?\s*"
                    r"(a|dopo|verso|in|tra)\s*(\w+)|piu' avanti|più avanti|fine (mese|anno)|prossim[oa] (mese|settimana|anno)|"
                    r"a (settembre|ottobre|novembre|dicembre|gennaio)", re.I)

def strip_html(s):
    s = re.sub(r"<style.*?</style>|<script.*?</script>", " ", s or "", flags=re.S | re.I)
    s = re.sub(r"<br\s*/?>|</p>|</div>", "\n", s, flags=re.I)
    s = re.sub(r"<[^>]+>", " ", s)
    return re.sub(r"[ \t]+", " ", ihtml.unescape(s)).strip()

def corpo_pulito(body):
    """Toglie il quoted delle mail precedenti."""
    t = strip_html(body)
    t = re.split(r"\bIl \d{4}-\d{2}-\d{2}|\bOn .{4,40} wrote:|Il giorno .{4,60} ha scritto|"
                 r"^Da:\s|^From:\s|-----Original|Messaggio originale", t, flags=re.M)[0]
    return t.strip()

def classifica(testo):
    t = testo.lower()
    if OOO.search(t) and not POS.search(t):
        return "ooo"
    if CAMBIO.search(t) and not POS.search(t):
        return "da_classificare"   # cambio indirizzo/persona: serve occhio umano
    if NEG.search(t):
        return "negativo"
    if RINVIO.search(t) and not re.search(r"invii|mandi|aspetto|attendo", t):
        return "rinvio"
    if POS.search(t):
        return "positivo"
    return "da_classificare"

def data_ooo(testo):
    """Prova a leggere 'fino al X luglio' / 'until July X' -> date ISO, se no None."""
    t = testo.lower()
    mesi = {"gennaio":1,"febbraio":2,"marzo":3,"aprile":4,"maggio":5,"giugno":6,"luglio":7,
            "agosto":8,"settembre":9,"ottobre":10,"novembre":11,"dicembre":12,
            "january":1,"february":2,"march":3,"april":4,"may":5,"june":6,"july":7,
            "august":8,"september":9,"october":10,"november":11,"december":12}
    m = re.search(r"(?:fino al|until|al rientro il|rientro|rientrer\w+\s+\w*\s*il?)\s*(\d{1,2})[°]?\s+(\w+)", t)
    if m and m.group(2) in mesi:
        try:
            d = date(date.today().year, mesi[m.group(2)], int(m.group(1)))
            if d < date.today() - timedelta(days=60):
                d = d.replace(year=d.year + 1)
            return d.isoformat()
        except ValueError:
            return None
    m = re.search(r"(\d{1,2})[/\-](\d{1,2})[/\-](\d{2,4})", t)
    if m:
        try:
            y = int(m.group(3)); y = y + 2000 if y < 100 else y
            return date(y, int(m.group(2)), int(m.group(1))).isoformat()
        except ValueError:
            return None
    return None

# ---------- stato attuale dal DB ----------
LOCKED_STAGES = {"cliente", "call_fissata", "perso", "rinviato"}

def db_prospects():
    """Tutti i prospects (email -> record ridotto), paginati."""
    out = {}
    offset = 0
    while True:
        rows = sb("GET", f"/rest/v1/prospects?select=id,email,stage,fuori,classificazione,enriched,"
                         f"analysis_sent,analysis_sent_at,no_followup,last_reply_at,followup_due"
                         f"&limit=1000&offset={offset}") or []
        for r in rows:
            out[r["email"].lower()] = r
        if len(rows) < 1000:
            break
        offset += 1000
    return out

# ---------- il giro ----------
def main():
    started = datetime.now().isoformat()
    print(f"SYNC V2 {'(DRY RUN)' if DRY else ''} — {started}")
    known = db_prospects()
    print(f"  DB: {len(known)} prospects noti")

    camps = sl_get("/campaigns") or []
    camps = [c for c in camps
             if c.get("status") != "ARCHIVED"
             and "best campaign" not in (c.get("name") or "").lower()]
    print(f"  campagne da controllare: {len(camps)}")

    tot_scanned = 0
    tot_replies = 0
    updated = 0
    anomalies = []
    da_rispondere = []

    for c in camps:
        cid = c["id"]
        # UNA chiamata: export CSV con reply_count autorevole per ogni lead
        rows = sl_export(cid)
        # RICONCILIAZIONE: il numero di righe deve essere sensato vs il totale noto
        declared_total = None
        try:
            page = sl_get(f"/campaigns/{cid}/leads?offset=0&limit=1")
            declared_total = int((page or {}).get("total_leads") or 0)
        except RuntimeError:
            pass
        if declared_total and abs(len(rows) - declared_total) > 0:
            anomalies.append(f"campagna {cid} '{c['name'][:30]}': export {len(rows)} righe vs dichiarati {declared_total}")
        tot_scanned += len(rows)

        with_reply = []
        invariati = 0
        for r in rows:
            em = (r.get("email") or "").strip().lower()
            if not em:
                continue
            rc = int(r.get("reply_count") or 0)
            known_replied = em in known and known[em].get("last_reply_at")
            firma = f"{rc}|{r.get('category') or ''}|{r.get('is_unsubscribed') or ''}|{r.get('status') or ''}"
            if rc > 0 or known_replied:
                if not COMPLETO and em in known and ((known[em].get("enriched") or {}).get("sl_firma") == firma):
                    invariati += 1
                    continue
                r["_firma"] = firma
                lead = {
                    "id": r.get("id"),
                    "first_name": r.get("first_name"), "last_name": r.get("last_name"),
                    "company_name": r.get("company_name"), "website": r.get("website"),
                    "category": r.get("category"),
                    "is_unsubscribed": (r.get("is_unsubscribed") or "").lower() == "true",
                }
                with_reply.append((em, lead, r))
        print(f"  [{cid}] {c['name'][:38]:38s} lead={len(rows)} con_reply={len(with_reply)}" + (f" invariati={invariati}" if invariati else ""))

        for em, lead, wrap in with_reply:
            lid = lead.get("id")
            try:
                h = sl_get(f"/campaigns/{cid}/leads/{lid}/message-history") or {}
            except RuntimeError as e:
                anomalies.append(f"thread illeggibile {em}: {e}")
                continue
            msgs = h.get("history") or []
            replies = [m for m in msgs if m.get("type") == "REPLY"]
            if not replies:
                continue
            tot_replies += 1
            last = msgs[-1]
            last_reply = replies[-1]
            awaiting = last.get("type") == "REPLY"
            testo = corpo_pulito(last_reply.get("email_body"))
            cls = classifica(testo)
            # se il testo non decide, la categoria Smartlead suggerisce
            if cls == "da_classificare" and lead.get("category") in CAT_HINT:
                cls = CAT_HINT[lead["category"]]
            ooo_until = data_ooo(testo) if cls == "ooo" else None

            rec = known.get(em)
            # se Dre ha classificato a mano ooo/rinvio/negativo/fuori_target/soppresso,
            # l'autoreply non rimette il lead in coda risposta
            manual_cls = (rec or {}).get("enriched", {}) or {}
            if manual_cls.get("classificazione") == "manual" and                (rec or {}).get("classificazione") in ("ooo", "rinvio", "negativo", "fuori_target", "soppresso"):
                awaiting = False
            body_first_reply = (replies[0].get("time") or "")[:19]
            body_last_reply = (last_reply.get("time") or "")[:19]

            patch = {
                "enriched": {**((rec or {}).get("enriched") or {}), "sl_firma": wrap.get("_firma")},
                "awaiting_us": awaiting,
                "last_reply_at": body_last_reply or None,
                "first_reply_at": body_first_reply or None,
            }
            if lead.get("is_unsubscribed"):
                patch["no_followup"] = True   # unsubscribed su Smartlead: non si tocca piu'
            # classificazione: solo se non corretta a mano
            manual = (rec or {}).get("enriched", {}).get("classificazione") == "manual"
            if not manual:
                patch["classificazione"] = cls
                if ooo_until:
                    patch["ooo_until"] = ooo_until
            # stage: mai toccare i bloccati o i fuori
            cur = rec or {}
            if not cur.get("fuori") and cur.get("stage") not in LOCKED_STAGES:
                if awaiting:
                    patch["stage"] = "risposto"
                elif cur.get("analysis_sent"):
                    patch["stage"] = "in_follow_up"
            # followup_due: 5gg dopo analisi (se inviata e lead in silenzio).
            # MA solo se non e' gia' impostata PIU' AVANTI (es. FU2 a 15gg, rinvii):
            # il sync propone, non sovrascrive il calendario deciso.
            if cur.get("analysis_sent") and cur.get("analysis_sent_at") and not awaiting:
                try:
                    d0 = datetime.fromisoformat(cur["analysis_sent_at"][:19])
                    proposta = (d0 + timedelta(days=6)).date().isoformat()   # Dre (9/9): follow-up a 6 giorni
                    esistente = cur.get("followup_due")
                    if not esistente or esistente < proposta:
                        patch["followup_due"] = proposta
                except ValueError:
                    pass

            if DRY:
                print(f"    ~ {em}: awaiting={awaiting} cls={cls}" + (f" ooo->{ooo_until}" if ooo_until else ""))
            else:
                if rec:
                    sb("PATCH", f"/rest/v1/prospects?id=eq.{rec['id']}", patch)
                else:
                    nuovo = {
                        "email": em,
                        "name": (lead.get("first_name") or "") + (" " + lead.get("last_name") if lead.get("last_name") else ""),
                        "company": lead.get("company_name"),
                        "website": lead.get("website"),
                        "campaign_id": cid, "lead_id": lid,
                        "campaign": c.get("name"), "stage": "risposto",
                        "source": "sync_v2", **patch,
                    }
                    created = sb("POST", "/rest/v1/prospects", nuovo,
                                 headers={"Prefer": "return=representation"})
                    rec = created[0] if isinstance(created, list) else created
                    known[em] = rec
                    anomalies.append(f"NUOVO nel CRM (mancava!): {em}")
                # timeline: le reply come interactions (dedup su unique constraint)
                for m in replies[-3:]:
                    body = corpo_pulito(m.get("email_body"))[:800]
                    try:
                        sb("POST", "/rest/v1/interactions",
                           {"prospect_id": rec["id"], "at": (m.get("time") or "")[:19],
                            "kind": "email_in", "body": body},
                           headers={"Prefer": "resolution=ignore-duplicates"})
                    except RuntimeError:
                        pass
                updated += 1
            if awaiting and cls not in ("negativo",):
                da_rispondere.append(f"{em} [{cls}] {lead.get('company_name') or ''}")
            time.sleep(0.12)

    ok = not anomalies
    print(f"\n{'='*60}")
    print(f"  lead scansionati: {tot_scanned} | thread con reply: {tot_replies} | aggiornati: {updated}")
    if da_rispondere:
        print(f"\n  DA RISPONDERE ADESSO ({len(da_rispondere)}):")
        for x in sorted(set(da_rispondere)):
            print(f"    - {x}")
    if anomalies:
        print(f"\n  !!! ANOMALIE ({len(anomalies)}) — CONTROLLARE, i conti non tornano:")
        for a in anomalies:
            print(f"    ! {a}")
    else:
        print("\n  riconciliazione OK: i conti tornano, nessun buco.")

    if not DRY:
        sb("POST", "/rest/v1/sync_runs", {
            "started_at": started, "finished_at": datetime.now().isoformat(),
            "campaigns_checked": len(camps), "leads_scanned": tot_scanned,
            "replies_found": tot_replies, "updated": updated,
            "reconciliation_ok": ok, "ok": ok,
            "anomalies": "\n".join(anomalies) if anomalies else None,
        })
    print(f"\nSYNC {'OK' if ok else 'CON ANOMALIE'} — registrato su sync_runs" if not DRY else "\n(dry run: nessuna scrittura)")
    sys.exit(0 if ok else 2)

if __name__ == "__main__":
    main()
