#!/bin/bash
# Blocca un git commit se si tocca uno schema numerato e schema_completo.sql
# non e' stato rifatto. Il file completo e' quello che si incolla in un
# progetto Supabase vergine: era rimasto alla v4 mentre il codice era alla v6,
# e un ambiente nuovo sarebbe nato senza pipeline, task e progetti senza che
# nessuno se ne accorgesse (4/9/2026).
comando=$(jq -r '.tool_input.command // ""' 2>/dev/null)
case "$comando" in
  *"git commit"*) ;;
  *) exit 0 ;;
esac

cd "$(dirname "$0")/../.." || exit 0
toccati=$(git diff --cached --name-only 2>/dev/null | grep '^supabase/.*\.sql$' | grep -v schema_completo)
[ -z "$toccati" ] && exit 0

prima=$(cat supabase/schema_completo.sql 2>/dev/null)
./scripts/schema-completo.sh >/dev/null 2>&1
if [ "$prima" != "$(cat supabase/schema_completo.sql)" ]; then
  {
    echo "COMMIT BLOCCATO: hai toccato uno schema ($toccati) e schema_completo.sql era vecchio."
    echo "L'ho appena rifatto io. Aggiungilo allo stage (git add supabase/schema_completo.sql) e ricommitta."
  } >&2
  exit 2
fi
exit 0
