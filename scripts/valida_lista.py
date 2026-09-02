#!/usr/bin/env python3
"""
ODYN Studio — VALIDAZIONE DELLA LISTA (il cancello, "la porta di entrata").

Gli scraper producono liste grezze; NIENTE entra nel sistema senza passare da qui.
Per ogni riga della lista grezza, nell'ordine:
  1. check duplicati contro l'anagrafe (email, poi dominio) -> si aggancia al PID esistente
  2. check soppressioni (email E dominio) -> ESPULSO, con motivo
  3. i nuovi ricevono il Prospect ID (automatico dal database) + fonte + data
  4. la lista riceve il suo codice L-NNN e i membri (PID, non righe copiate)
  5. report di validazione

Uso:
  python3 scripts/valida_lista.py lista.csv --nome "Hotel lago di Garda" --scopo outbound --fonte "maps-scraper" [--dry-run]

CSV: colonne riconosciute (case-insensitive, in qualsiasi ordine):
  email (obbligatoria) · company/azienda · website/sito · name/nome · phone/telefono · linkedin
"""
import argparse, csv, json, os, re, sys, urllib.request, urllib.parse

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

def load_env():
    env = {}
    for line in open(os.path.join(ROOT, ".env.local")):
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            env[k.strip()] = v.strip()
    return env

ENV = load_env()
SB_URL = ENV["VITE_SUPABASE_URL"].rstrip("/")
SB_KEY = ENV["SUPABASE_SERVICE_KEY"]

def sb(method, path, body=None, headers=None):
    req = urllib.request.Request(
        SB_URL + path,
        data=json.dumps(body).encode() if body is not None else None,
        method=method,
    )
    for k, v in {"apikey": SB_KEY, "Authorization": f"Bearer {SB_KEY}",
                 "Content-Type": "application/json", **(headers or {})}.items():
        req.add_header(k, v)
    with urllib.request.urlopen(req) as r:
        data = r.read()
        return json.loads(data) if data else None

def norm_email(e):
    e = (e or "").strip().lower()
    return e if "@" in e else None

def norm_domain(url_or_domain):
    d = (url_or_domain or "").strip().lower()
    d = re.sub(r"^https?://", "", d).split("/")[0]
    d = re.sub(r"^www\.", "", d)
    return d or None

def col(row, *names):
    for n in names:
        for k, v in row.items():
            if k and k.strip().lower() == n:
                return (v or "").strip()
    return ""

def fetch_all(path_tmpl):
    """pagina su PostgREST con offset"""
    out, offset = [], 0
    while True:
        page = sb("GET", path_tmpl.format(offset=offset))
        if not page:
            break
        out.extend(page)
        if len(page) < 1000:
            break
        offset += 1000
    return out

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("csvfile")
    ap.add_argument("--nome", required=True, help="nome della lista")
    ap.add_argument("--scopo", default="outbound")
    ap.add_argument("--fonte", required=True, help="da dove viene la lista grezza (scraper/fonte)")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    righe = list(csv.DictReader(open(a.csvfile, encoding="utf-8-sig")))
    if not righe:
        sys.exit("lista vuota")
    print(f"lista grezza: {len(righe)} righe — carico anagrafe e soppressioni...")

    # anagrafe: email -> (uuid, pid); dominio -> (uuid, pid)
    anag = fetch_all("/rest/v1/prospects?select=id,pid,email,website&limit=1000&offset={offset}")
    by_email = {p["email"].lower(): p for p in anag if p.get("email")}
    by_domain = {}
    for p in anag:
        d = norm_domain(p.get("website") or "")
        if d and d not in by_domain:
            by_domain[d] = p

    # soppressioni
    soppr = fetch_all("/rest/v1/suppressions?select=email,domain,kind,reason&limit=1000&offset={offset}")
    s_email = {s["email"].lower(): s for s in soppr if s.get("email")}
    s_domain = {s["domain"].lower(): s for s in soppr if s.get("domain")}

    nuovi, esistenti, soppressi, invalidi = [], [], [], []
    visti = set()
    for r in righe:
        email = norm_email(col(r, "email"))
        if not email:
            invalidi.append(r); continue
        if email in visti:
            continue
        visti.add(email)
        dom_sito = norm_domain(col(r, "website", "sito"))
        dom_mail = email.split("@")[1]
        # 2. soppressioni (email, dominio sito, dominio mail)
        blocco = s_email.get(email) or s_domain.get(dom_sito or "") or s_domain.get(dom_mail)
        if blocco:
            soppressi.append((email, blocco["kind"], blocco["reason"]))
            continue
        # 1. duplicati
        match = by_email.get(email) or (by_domain.get(dom_sito) if dom_sito else None)
        if match:
            esistenti.append(match)
        else:
            nuovi.append({
                "email": email,
                "company": col(r, "company", "azienda") or None,
                "website": col(r, "website", "sito") or None,
                "name": col(r, "name", "nome") or None,
                "phone": col(r, "phone", "telefono") or None,
                "linkedin": col(r, "linkedin") or None,
                "stage": "nuovo",
                "source": f"lista:{a.fonte}",
            })

    print(f"\n=== REPORT VALIDAZIONE ===")
    print(f"nuovi (ricevono PID):   {len(nuovi)}")
    print(f"gia' in anagrafe:       {len(esistenti)} (si agganciano al loro PID, storia continua)")
    print(f"SOPPRESSI (espulsi):    {len(soppressi)}")
    for em, kind, reason in soppressi[:15]:
        print(f"   ⛔ {em} [{kind}] {reason[:60]}")
    if len(soppressi) > 15:
        print(f"   ... e altri {len(soppressi)-15}")
    print(f"invalidi (senza email): {len(invalidi)}")

    if a.dry_run:
        print("\n(dry-run: niente scritto)")
        return

    # 3. inserisci i nuovi (il PID arriva dal default del database)
    inseriti = []
    for i in range(0, len(nuovi), 500):
        batch = nuovi[i:i+500]
        res = sb("POST", "/rest/v1/prospects", batch, {"Prefer": "return=representation"})
        inseriti.extend(res or [])
    print(f"\ninseriti {len(inseriti)} nuovi prospect")

    # 4. crea la lista e i membri
    lista = sb("POST", "/rest/v1/lists",
               {"name": a.nome, "purpose": a.scopo, "source": a.fonte},
               {"Prefer": "return=representation"})[0]
    lcode = f"L-{lista['lid']:03d}"
    membri = [{"list_id": lista["id"], "prospect_id": p["id"]}
              for p in inseriti + esistenti]
    # dedup (un prospect può matchare sia per email che dominio)
    visti_m = set(); membri_dedup = []
    for m in membri:
        if m["prospect_id"] not in visti_m:
            visti_m.add(m["prospect_id"]); membri_dedup.append(m)
    for i in range(0, len(membri_dedup), 500):
        sb("POST", "/rest/v1/list_members?on_conflict=list_id,prospect_id",
           membri_dedup[i:i+500], {"Prefer": "resolution=ignore-duplicates,return=minimal"})

    print(f"\n✅ LISTA VALIDATA: {lcode} — \"{a.nome}\" ({len(membri_dedup)} membri)")
    print(f"   pronta per alimentare Smartlead/LinkedIn/azioni. Solo liste validate escono nel mondo.")

if __name__ == "__main__":
    main()
