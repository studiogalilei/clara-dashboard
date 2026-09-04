#!/bin/bash
# Blocca un git commit se fra i file in stage c'e' qualcosa che somiglia a una
# chiave vera. Nasce il 4/9/2026: in questo progetto vivono tre file con dentro
# chiavi vive, e basta un nome di file sbagliato perche' una finisca in git
# per sempre. La regola non deve dipendere dalla memoria di nessuno.
comando=$(jq -r '.tool_input.command // ""' 2>/dev/null)
case "$comando" in
  *"git commit"*) ;;
  *) exit 0 ;;
esac

trovate=$(git diff --cached -U0 2>/dev/null | grep -E '^\+' \
  | grep -nE 'sb_secret_[A-Za-z0-9_-]{10,}|eyJ[A-Za-z0-9_-]{40,}|sk-[A-Za-z0-9_-]{20,}|(SERVICE_KEY|SECRET_KEY|API_KEY)=[A-Za-z0-9_.\-]{12,}' \
  | head -5)

if [ -n "$trovate" ]; then
  {
    echo "COMMIT BLOCCATO: fra i file in stage c'e' qualcosa che somiglia a una chiave segreta."
    echo "$trovate"
    echo "Togli il file dallo stage (git restore --staged <file>) e mettilo fra i file ignorati."
  } >&2
  exit 2
fi
exit 0
