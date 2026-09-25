#!/usr/bin/env python3
"""
ODYN CRM — import iniziale (one-shot).
Legge TUTTE le fonti esistenti (CSV master, indice Smartlead, tracker,
inviate, stati Falcon, esclusioni follow-up, schede Obsidian, PDF analisi,
ricontatti programmati) e carica tutto su Supabase.

ATTENZIONE: pensato per il primo caricamento su DB vuoto. Se rilanciato,
sovrascrive i campi coi valori delle fonti (le modifiche fatte a mano
nell'app potrebbero essere perse).

Uso:  python3 scripts/import_all.py [--dry-run]
"""
import csv, json, os, re, sys, unicodedata
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
VAULT = os.path.expanduser("~/Documents/Obsidian/studiogalilei")
FALCON = os.path.join(VAULT, "Falcon Studio")
SISTEMA = os.path.join(VAULT, "Sistema Operativo Studio Galilei")

DRY = "--dry-run" in sys.argv

# ---------- env ----------
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
SB_URL = ENV.get("VITE_SUPABASE_URL", "").rstrip("/")
SB_KEY = ENV.get("SUPABASE_SERVICE_KEY", "")
if not DRY and (not SB_URL or not SB_KEY):
    sys.exit("ERRORE: compila VITE_SUPABASE_URL e SUPABASE_SERVICE_KEY in .env.local")

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
    with urllib.request.urlopen(req) as r:
        data = r.read()
        return json.loads(data) if data else None

# ---------- helpers ----------
def norm_email(e):
    return (e or "").strip().lower()

def norm_company(c):
    c = unicodedata.normalize("NFKD", c or "").encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]", "", c.lower())

def parse_ts(v):
    return v if v else None

FIELDS = [
    "email","name","role","phone","linkedin","company","website","sector","city",
    "socials","owner_name","campaign","campaign_id","lead_id","stage",
    "first_reply_at","last_reply_at","analysis_sent","analysis_sent_at","analysis_pdf",
    "next_action","next_action_date","no_followup","deal_value","lost_reason",
    "notes","enriched","source",
]

P = {}  # email -> record

def rec(email):
    email = norm_email(email)
    if not email or "@" not in email:
        return None
    if email not in P:
        P[email] = {k: None for k in FIELDS}
        P[email].update({
            "email": email, "stage": "nuovo", "analysis_sent": False,
            "no_followup": False, "socials": {}, "enriched": {}, "source": "",
        })
    return P[email]

def setv(r, k, v, src=None):
    if v in (None, "", []):
        return
    if r.get(k) in (None, "", False, 0) or k in ("stage",):
        r[k] = v
    if src and src not in (r["source"] or ""):
        r["source"] = ((r["source"] or "") + "," + src).strip(",")

STAGE_RANK = {"nuovo":0,"risposto":1,"in_follow_up":2,"analisi_inviata":3,"rinviato":4,"call_fissata":5,"perso":5,"cliente":6}
def upgrade_stage(r, stage):
    if STAGE_RANK.get(stage, 0) > STAGE_RANK.get(r["stage"], 0):
        r["stage"] = stage

interactions = []  # (email, at, kind, body)

# ---------- 1. CSV master ----------
for fn in ("leads_active.csv", "leads_education.csv"):
    p = os.path.join(FALCON, "data", "leads_master", fn)
    if not os.path.exists(p):
        print(f"  (salto {fn}: non trovato)")
        continue
    n = 0
    for row in csv.DictReader(open(p, encoding="utf-8-sig")):
        r = rec(row.get("Email"))
        if not r:
            continue
        name = f"{row.get('First Name','').strip()} {row.get('Last Name','').strip()}".strip()
        setv(r, "name", name or None, "csv")
        setv(r, "phone", (row.get("Phone Number") or "").strip() or None)
        setv(r, "linkedin", (row.get("Linkedin Profile") or "").strip() or None)
        setv(r, "role", (row.get("Title") or "").strip()[:200] or None)
        setv(r, "company", (row.get("Azienda") or row.get("Company Name") or "").strip() or None)
        setv(r, "website", (row.get("Website") or "").strip() or None)
        n += 1
    print(f"  CSV {fn}: {n} righe")

# ---------- 2. Indice Smartlead ----------
idx_path = "/tmp/sl_leads_index.json"
if os.path.exists(idx_path):
    leads = json.load(open(idx_path)).get("leads", [])
    for L in leads:
        r = rec(L.get("email"))
        if not r:
            continue
        setv(r, "name", L.get("name"), "smartlead")
        setv(r, "company", L.get("company"))
        setv(r, "website", L.get("website"))
        setv(r, "campaign", L.get("campaign"))
        setv(r, "campaign_id", L.get("campaign_id"))
        setv(r, "lead_id", L.get("lead_id"))
    print(f"  Indice Smartlead: {len(leads)} lead")
else:
    print("  (indice /tmp/sl_leads_index.json non trovato — rigeneralo con sl_index.py se vuoi tutti i lead)")

# ---------- 3. Tracker (risposte) ----------
trk_path = "/tmp/sl_tracker.json"
if not os.path.exists(trk_path):
    trk_path = os.path.join(FALCON, ".falcon-bridge", "sl_tracker.json")
if os.path.exists(trk_path):
    rows = json.load(open(trk_path)).get("rows", [])
    for t in rows:
        r = rec(t.get("email"))
        if not r:
            continue
        setv(r, "name", t.get("name"), "tracker")
        setv(r, "company", t.get("company"))
        setv(r, "campaign", t.get("campaign"))
        setv(r, "campaign_id", t.get("campaign_id"))
        setv(r, "lead_id", t.get("lead_id"))
        r["first_reply_at"] = parse_ts(t.get("reply_at")) or r["first_reply_at"]
        r["last_reply_at"] = parse_ts(t.get("last_reply")) or r["last_reply_at"]
        if t.get("analysis_sent"):
            r["analysis_sent"] = True
            r["analysis_sent_at"] = parse_ts(t.get("sent_at")) or r["analysis_sent_at"]
            upgrade_stage(r, "analisi_inviata")
        elif t.get("last_reply") or t.get("reply_at"):
            upgrade_stage(r, "risposto")
        if t.get("last_reply"):
            interactions.append((r["email"], t["last_reply"], "email_in", "Risposta ricevuta (Smartlead)"))
        if t.get("sent_at"):
            interactions.append((r["email"], t["sent_at"], "analisi", "Analisi inviata"))
    print(f"  Tracker: {len(rows)} rispondenti")
else:
    print("  (tracker non trovato)")

# ---------- 4. Inviate ----------
inv_path = os.path.join(FALCON, "data", "inviate_all.json")
if os.path.exists(inv_path):
    rows = json.load(open(inv_path)).get("rows", [])
    for t in rows:
        r = rec(t.get("email"))
        if not r:
            continue
        setv(r, "name", t.get("name"), "inviate")
        setv(r, "company", t.get("company"))
        setv(r, "campaign", t.get("campaign"))
        if t.get("reply_at"):
            r["first_reply_at"] = r["first_reply_at"] or parse_ts(t.get("reply_at"))
            r["last_reply_at"] = r["last_reply_at"] or parse_ts(t.get("reply_at"))
            upgrade_stage(r, "risposto")
        if t.get("analysis_sent"):
            r["analysis_sent"] = True
            r["analysis_sent_at"] = r["analysis_sent_at"] or parse_ts(t.get("sent_at"))
            upgrade_stage(r, "analisi_inviata")
    print(f"  Inviate: {len(rows)} righe")

# ---------- 5. Stati Falcon ----------
st_path = os.path.join(FALCON, ".falcon-bridge", "lead_states.json")
STAGE_MAP = {
    "in_attesa": "risposto", "analisi_inviata": "analisi_inviata",
    "appuntamento": "call_fissata", "call": "call_fissata",
    "cliente": "cliente", "perso": "perso", "no": "perso",
}
if os.path.exists(st_path):
    states = json.load(open(st_path))
    for email, s in states.items():
        r = rec(email)
        if not r:
            continue
        setv(r, "name", s.get("name"), "falcon")
        setv(r, "company", s.get("company"))
        setv(r, "website", s.get("website"))
        setv(r, "campaign", s.get("campaign"))
        mapped = STAGE_MAP.get((s.get("stage") or "").lower())
        if mapped:
            upgrade_stage(r, mapped)
    print(f"  Stati Falcon: {len(states)} lead")

# ---------- 6. Esclusioni follow-up ----------
ex_path = os.path.join(FALCON, ".falcon-bridge", "followup_exclude.json")
if os.path.exists(ex_path):
    ex = json.load(open(ex_path))
    for email, reason in ex.get("rinvio", {}).items():
        r = rec(email)
        if r:
            upgrade_stage(r, "rinviato")
            setv(r, "next_action", reason)
            setv(r, "lost_reason", None)
    for email, reason in ex.get("skip", {}).items():
        r = rec(email)
        if r:
            r["no_followup"] = True
            r["notes"] = ((r["notes"] or "") + f"\n[skip] {reason}").strip()
    print(f"  Esclusioni: {len(ex.get('rinvio',{}))} rinvii, {len(ex.get('skip',{}))} skip")

# ---------- 7. PDF analisi ----------
an_dir = os.path.join(SISTEMA, "Analisi")
pdf_by_company = {}
if os.path.isdir(an_dir):
    for fn in os.listdir(an_dir):
        m = re.match(r"Analisi_GoogleAds_(.+)\.pdf$", fn)
        if m:
            pdf_by_company[norm_company(m.group(1))] = fn
    matched = 0
    for r in P.values():
        key = norm_company(r.get("company") or "")
        if key and key in pdf_by_company:
            r["analysis_pdf"] = pdf_by_company[key]
            matched += 1
    print(f"  PDF analisi: {len(pdf_by_company)} file, {matched} abbinati")

# ---------- 8. Schede Obsidian (04) ----------
schede_dir = os.path.join(SISTEMA, "04 - Clienti e Potenziali Clienti")
n_schede = 0
if os.path.isdir(schede_dir):
    for root, _dirs, files in os.walk(schede_dir):
        for fn in files:
            if not fn.endswith(".md") or fn.startswith("ODYN"):
                continue
            txt = open(os.path.join(root, fn), encoding="utf-8", errors="ignore").read()
            m_email = re.search(r"\*\*Email:\*\*\s*([^\s\n]+@[^\s\n]+)", txt)
            if not m_email:
                continue
            r = rec(m_email.group(1))
            if not r:
                continue
            n_schede += 1
            m = re.search(r"\*\*Telefono:\*\*\s*([^\n]+)", txt)
            if m and m.group(1).strip() not in ("-", "—", ""):
                setv(r, "phone", m.group(1).strip(), "scheda")
            m = re.search(r"\*\*Sito:\*\*\s*(https?://[^\s\n]+)", txt)
            if m:
                setv(r, "website", m.group(1).strip())
            m = re.search(r"\*\*Stato:\*\*\s*([^\n]+)", txt)
            if m:
                mapped = STAGE_MAP.get(m.group(1).strip().lower())
                if mapped:
                    upgrade_stage(r, mapped)
    print(f"  Schede Obsidian: {n_schede} abbinate")

# ---------- 9. Ricontatti programmati ----------
ric_path = os.path.join(schede_dir, "ODYN — Ricontatti programmati.md")
MESI = {"gennaio":1,"febbraio":2,"marzo":3,"aprile":4,"maggio":5,"giugno":6,
        "luglio":7,"agosto":8,"settembre":9,"ottobre":10,"novembre":11,"dicembre":12}
if os.path.exists(ric_path):
    cur_date = None
    n_ric = 0
    for line in open(ric_path, encoding="utf-8"):
        h = re.match(r"##\s*.*?(?:(\d{1,2})\s+)?(gennaio|febbraio|marzo|aprile|maggio|giugno|luglio|agosto|settembre|ottobre|novembre|dicembre)\s+(\d{4})", line, re.I)
        if h:
            day = int(h.group(1)) if h.group(1) else (25 if "fine" in line.lower() else 5)
            cur_date = f"{h.group(3)}-{MESI[h.group(2).lower()]:02d}-{day:02d}"
            continue
        m = re.match(r"-\s*(.+?)\s*[—-]\s*([^\s@]+@[^\s—-]+)\s*[—-]\s*(.+)", line)
        if m and cur_date:
            r = rec(m.group(2))
            if r:
                if not r["next_action_date"]:
                    r["next_action_date"] = cur_date
                    setv(r, "next_action", m.group(3).strip()[:200])
                n_ric += 1
    print(f"  Ricontatti programmati: {n_ric} abbinati")

# ---------- riepilogo ----------
from collections import Counter
stages = Counter(r["stage"] for r in P.values())
print(f"\nTotale prospect: {len(P)}")
for s, n in stages.most_common():
    print(f"  {s}: {n}")
print(f"Interazioni da creare: {len(interactions)}")

if DRY:
    sys.exit("\n(dry-run: niente caricato)")

# ---------- upsert prospects ----------
rows = list(P.values())
print("\nCarico su Supabase…")
for i in range(0, len(rows), 500):
    batch = rows[i:i+500]
    sb("POST", "/rest/v1/prospects?on_conflict=email", batch,
       {"Prefer": "resolution=merge-duplicates,return=minimal"})
    print(f"  prospects {min(i+500, len(rows))}/{len(rows)}")

# ---------- id map ----------
print("Scarico gli id…")
id_by_email = {}
offset = 0
while True:
    page = sb("GET", f"/rest/v1/prospects?select=id,email&limit=1000&offset={offset}")
    if not page:
        break
    for row in page:
        id_by_email[row["email"]] = row["id"]
    if len(page) < 1000:
        break
    offset += 1000
print(f"  {len(id_by_email)} id")

# ---------- interactions ----------
ints = []
seen = set()
for email, at, kind, body in interactions:
    pid = id_by_email.get(email)
    if not pid:
        continue
    k = (pid, at, kind)
    if k in seen:
        continue
    seen.add(k)
    ints.append({"prospect_id": pid, "at": at, "kind": kind, "body": body})
for i in range(0, len(ints), 500):
    sb("POST", "/rest/v1/interactions?on_conflict=prospect_id,at,kind", ints[i:i+500],
       {"Prefer": "resolution=ignore-duplicates,return=minimal"})
    print(f"  interactions {min(i+500, len(ints))}/{len(ints)}")

print("\nFATTO. Apri l'app e controlla la tab Prospect.")
