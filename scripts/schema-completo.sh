#!/bin/bash
# Rimette insieme supabase/schema_completo.sql dai file numerati.
#
# Il file completo e' quello che si incolla in un progetto Supabase vergine.
# Era fermo alla v4 mentre il codice era gia' alla v6: un ambiente nuovo
# sarebbe nato senza pipeline, senza task e senza progetti, e nessuno se ne
# sarebbe accorto finche' qualcosa non falliva. Adesso si rigenera, non si
# aggiorna a mano (revisione 4/9).
set -euo pipefail
cd "$(dirname "$0")/.."

# 6/10: la lista scritta a mano era ferma alla v15 da settimane, e lo schema
# completo con lei: proprio il marcio che questo script prometteva di evitare.
# Ora l'ordine si calcola dai file (numero di versione, poi la lettera: v5
# prima di v5b), cosi' un file nuovo non puo' restare fuori in silenzio.
ordine=()
while IFS= read -r f; do ordine+=("$f"); done < <(python3 - <<'PY'
import os, re
fs = []
for f in os.listdir('supabase'):
    if not f.endswith('.sql') or f == 'schema_completo.sql':
        continue
    m = re.match(r'schema(?:_v(\d+)([a-z]?))?\.sql$', f)
    if not m:
        raise SystemExit(f"✗ nome fuori schema: supabase/{f} (atteso schema_vN[.lettera].sql)")
    fs.append(((int(m.group(1) or 0), m.group(2) or ''), f))
for _, f in sorted(fs):
    print(f)
PY
)

out=supabase/schema_completo.sql
{
  echo "-- ════════════════════════════════════════════════════════════════════"
  echo "-- ODYN CRM: schema completo, per un progetto Supabase vergine."
  echo "-- Tutte le versioni una dopo l'altra. Non cancella niente."
  echo "--"
  echo "-- GENERATO da scripts/schema-completo.sh: non si modifica a mano."
  echo "-- Si aggiunge un file numerato in supabase/ e si rilancia lo script."
  echo "-- ════════════════════════════════════════════════════════════════════"
  echo
  for f in "${ordine[@]}"; do
    echo
    echo "-- ─── $f ────────────────────────────────────────────"
    echo
    cat "supabase/$f"
  done
} > "$out"
echo "✓ $out rifatto: ${#ordine[@]} file, $(wc -l < "$out" | tr -d ' ') righe"
