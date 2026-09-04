#!/bin/bash
# Passa dal cancello ogni documento .md che scrivo: trattino lungo, parole
# vernice, preamboli. La regola esisteva dal 24/8 ma dipendeva dal fatto che
# mi ricordassi di lanciarla a mano. Adesso non piu'.
file=$(jq -r '.tool_response.filePath // .tool_input.file_path // ""' 2>/dev/null)
case "$file" in
  *.md) ;;
  *) exit 0 ;;
esac
case "$file" in
  */node_modules/*|*/.git/*) exit 0 ;;
esac

lint="/Users/dramane/Documents/Obsidian/studiogalilei/Sistema Operativo Studio Galilei/ODYN Cockpit/scripts/regole.py"
[ -f "$lint" ] || exit 0
esito=$(python3 "$lint" "$file" 2>&1)
if echo "$esito" | grep -q '✗'; then
  { echo "Il cancello delle regole di casa ha bocciato $file:"; echo "$esito"; } >&2
  exit 2
fi
exit 0
