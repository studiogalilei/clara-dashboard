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

ordine=(schema.sql schema_v2.sql schema_v3.sql schema_v4.sql schema_v5.sql schema_v5b.sql schema_v6.sql schema_v7.sql schema_v8.sql schema_v9.sql schema_v10.sql)
mancanti=()
for f in supabase/*.sql; do
  b=$(basename "$f")
  [ "$b" = "schema_completo.sql" ] && continue
  trovato=no
  for o in "${ordine[@]}"; do [ "$o" = "$b" ] && trovato=si; done
  [ "$trovato" = no ] && mancanti+=("$b")
done
if [ ${#mancanti[@]} -gt 0 ]; then
  echo "✗ questi file non sono nell'ordine dentro $0: ${mancanti[*]}" >&2
  echo "  aggiungili alla lista, se no non finiscono nello schema completo" >&2
  exit 1
fi

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
