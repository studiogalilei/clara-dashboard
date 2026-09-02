#!/usr/bin/env python3
"""
ODYN Studio — semina del registro SOPPRESSIONI (one-shot, 3 lug 2026).

Porta dentro i casi reali già accumulati:
  - le richieste di rimozione/GDPR di questa settimana (unsubscribe già fatti su Smartlead)
  - gli skip "duri" da followup_exclude.json (competitor/agenzie, no espliciti)
I rinvii ("risentiamoci a ottobre") NON sono soppressioni: restano fuori.

Uso: python3 scripts/migra_soppressioni.py [--dry-run]
"""
import json, os, sys, urllib.request, urllib.parse

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
    req = urllib.request.Request(SB_URL + path,
        data=json.dumps(body).encode() if body is not None else None, method=method)
    for k, v in {"apikey": SB_KEY, "Authorization": f"Bearer {SB_KEY}",
                 "Content-Type": "application/json", **(headers or {})}.items():
        req.add_header(k, v)
    with urllib.request.urlopen(req) as r:
        data = r.read()
        return json.loads(data) if data else None

# ============ i casi, con tipo e motivo ============
CASI = [
    # GDPR / richieste di rimozione esplicite (blocco legale, per sempre)
    ("gdpr", "mattia@filippinibusinessconsulting.com", "richiesta rimozione furiosa 3/7: 'rimuovete ogni dato, non contattatemi mai piu''", "mail 3/7"),
    ("gdpr", "dan@buenaonda-holidays.com", "caso GDPR art.14 (dati da Apollo), chiuso 2/7 'siamo ok cosi'' — mai piu' contattare", "thread giu-lug"),
    ("rimozione", "luana.arginelli@monitortheplanet.com", "'CANCELLAMI DALLE LISTE' 1/7 — unsubscribe fatto", "mail 1/7"),
    ("rimozione", "info@centromedicoitaliano.com", "'cancellare il nostro indirizzo dalla mailing list' 2/7 — unsubscribe fatto", "mail 2/7"),
    ("deceduto", "pierfelice.turrin@imecosrl.net", "il geom. Turrin e' venuto a mancare; l'azienda ha chiesto la rimozione — unsubscribe fatto", "mail 1/7"),
    ("rimozione", "v.ferretti@fbsrl.biz", "'prego cancellare il mio contatto dalla vostra banca dati' 2/7 — unsubscribe fatto", "mail 2/7"),
    # non-target: competitor / agenzie (decisione Dre)
    ("non_target", "alessandro.vidotto@404scs.com", "404scs = agenzia marketing (competitor), lasciar cadere (Dre 2/7)", "followup_exclude"),
    ("non_target", "room@motel409.com", "MOTEL 409 = agenzia", "followup_exclude"),
    ("non_target", "s.biella@doublemalt.it", "BB Lions: ha un'agenzia di comunicazione propria", "followup_exclude"),
    # no espliciti (soft ma registrati: non ricontattare in liste future)
    ("no_esplicito", "padova@habimmobiliare.it", "HAB Immobiliare: non interessati (2/7)", "followup_exclude"),
    ("no_esplicito", "info@impresaitaliasnc.191.it", "Impresa Italia Pulizie: non interessati (2/7)", "followup_exclude"),
    ("no_esplicito", "fabio@evoluzionebenefit.it", "gia' affidato ad altra azienda (3/7)", "followup_exclude"),
    ("no_esplicito", "mariangela.bonatto@imagine.srl", "IMAGINE Media Center: non interessati (2/7)", "followup_exclude"),
    ("no_esplicito", "i.morganti@itinerariparalleli.org", "Itinerari Paralleli: non interessati (2/7)", "followup_exclude"),
]

def main():
    dry = "--dry-run" in sys.argv
    rows = []
    for kind, email, reason, source in CASI:
        email = email.lower()
        # aggancia il PID se il prospect esiste
        pid = None
        try:
            found = sb("GET", f"/rest/v1/prospects?email=eq.{urllib.parse.quote(email)}&select=pid")
            if found:
                pid = found[0].get("pid")
        except Exception:
            pass
        rows.append({"kind": kind, "email": email, "domain": None,
                     "pid": pid, "reason": reason, "source": source})
        print(f"{'[dry] ' if dry else ''}{kind:14s} {email:45s} pid={pid}")
    if dry:
        print(f"\n(dry-run: {len(rows)} soppressioni NON scritte)")
        return
    sb("POST", "/rest/v1/suppressions", rows, {"Prefer": "resolution=ignore-duplicates,return=minimal"})
    print(f"\n✅ {len(rows)} soppressioni nel registro. Il sistema ora SA chi non toccare.")

if __name__ == "__main__":
    main()
