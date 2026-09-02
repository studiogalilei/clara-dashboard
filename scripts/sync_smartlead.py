#!/usr/bin/env python3
"""
ODYN CRM — sync giornaliero da Smartlead.
Legge l'output del segugio (sl_tracker.json) e aggiorna il CRM:
  - nuove risposte -> stage 'risposto' (se non gia' piu' avanti)
  - analisi inviata -> stage 'analisi_inviata' + data
  - risposta DOPO l'analisi -> torna 'risposto' (da gestire)
  - aggiunge gli eventi in timeline (dedup automatico)
NON tocca mai: cliente, call_fissata, perso, rinviato, campi compilati a mano.

Uso:  python3 scripts/sync_smartlead.py [/percorso/sl_tracker.json]
      (default: /tmp/sl_tracker.json, fallback copia Falcon)
"""
import json, os, sys, urllib.request, urllib.parse

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
FALCON_TRK = os.path.expanduser(
    "~/Documents/Obsidian/studiogalilei/Sistema Operativo Studio Galilei/ODYN Cockpit/data/sl_tracker.json")

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
if not SB_URL or not SB_KEY:
    sys.exit("ERRORE: compila .env.local")

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

trk_path = sys.argv[1] if len(sys.argv) > 1 else "/tmp/sl_tracker.json"
if not os.path.exists(trk_path):
    trk_path = FALCON_TRK
if not os.path.exists(trk_path):
    sys.exit("ERRORE: sl_tracker.json non trovato (lancia prima sl_tracker.py)")

rows = json.load(open(trk_path)).get("rows", [])
LOCKED = {"cliente", "call_fissata", "perso", "rinviato"}
n_new, n_upd, n_int = 0, 0, 0

for t in rows:
    email = (t.get("email") or "").strip().lower()
    if not email:
        continue
    q = urllib.parse.quote(email)
    found = sb("GET", f"/rest/v1/prospects?email=eq.{q}&select=id,stage,last_reply_at,analysis_sent")
    if not found:
        body = {
            "email": email, "name": t.get("name"), "company": t.get("company"),
            "campaign": t.get("campaign"), "campaign_id": t.get("campaign_id"),
            "lead_id": t.get("lead_id"), "stage": "risposto",
            "first_reply_at": t.get("reply_at"), "last_reply_at": t.get("last_reply"),
            "analysis_sent": bool(t.get("analysis_sent")),
            "analysis_sent_at": t.get("sent_at"), "source": "sync",
        }
        created = sb("POST", "/rest/v1/prospects", body, {"Prefer": "return=representation"})
        pid = created[0]["id"]
        n_new += 1
    else:
        cur = found[0]
        pid = cur["id"]
        patch = {}
        if t.get("last_reply") and t["last_reply"] != cur.get("last_reply_at"):
            patch["last_reply_at"] = t["last_reply"]
        if t.get("analysis_sent") and not cur.get("analysis_sent"):
            patch["analysis_sent"] = True
            patch["analysis_sent_at"] = t.get("sent_at")
        if cur["stage"] not in LOCKED:
            if t.get("reply_after_sent"):
                patch["stage"] = "risposto"
            elif t.get("analysis_sent") and cur["stage"] in ("nuovo", "risposto"):
                patch["stage"] = "analisi_inviata"
            elif t.get("last_reply") and cur["stage"] == "nuovo":
                patch["stage"] = "risposto"
        if patch:
            sb("PATCH", f"/rest/v1/prospects?id=eq.{pid}", patch, {"Prefer": "return=minimal"})
            n_upd += 1
    ints = []
    if t.get("last_reply"):
        ints.append({"prospect_id": pid, "at": t["last_reply"], "kind": "email_in",
                     "body": "Risposta ricevuta (Smartlead)"})
    if t.get("sent_at"):
        ints.append({"prospect_id": pid, "at": t["sent_at"], "kind": "analisi",
                     "body": "Analisi inviata"})
    if ints:
        sb("POST", "/rest/v1/interactions?on_conflict=prospect_id,at,kind", ints,
           {"Prefer": "resolution=ignore-duplicates,return=minimal"})
        n_int += len(ints)

print(f"Sync ok: {n_new} nuovi, {n_upd} aggiornati, {n_int} eventi timeline (dedup automatico).")
