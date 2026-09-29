#!/bin/bash
# A OGNI INIZIO SESSIONE NEL CRM (28/9/2026).
#
# Il vault ce l'aveva da agosto, qui no: aprendo VS Code su odyn-crm si
# ripartiva senza sapere dove eravamo. Dre, 28/9: «voglio questo thread là con
# questa memoria». La memoria sta su disco, ma qualcuno deve metterla davanti
# agli occhi, e non puo' essere una cosa che mi ricordo.
#
# Mette in fila tre cose: lo stato del lavoro, il punto piu' recente su dove
# siamo, e i promemoria operativi.

VAULT="/Users/dramane/Documents/Obsidian/studiogalilei"
CERVELLO="$VAULT/00 - Cervello Condiviso"

echo "════ STATO — leggere prima di rispondere ════"
cat "$VAULT/STATO.md" 2>/dev/null || echo "(STATO.md non trovato in $VAULT)"

# l'ultimo «dove siamo»: si prende il piu' recente, cosi' non va aggiornato a mano
PUNTO=$(ls -t "$CERVELLO"/Dove\ siamo*.md 2>/dev/null | head -1)
if [ -n "$PUNTO" ]; then
  echo
  echo "════ DOVE SIAMO — $(basename "$PUNTO") ════"
  cat "$PUNTO"
fi

echo
echo "════ Promemoria ════"
echo "· Le regole complete stanno nel vault: $VAULT/CLAUDE.md"
echo "· Il blocco Parked CHIUDE ogni messaggio (in fondo) finché c'è una cosa aperta."
echo "· L'invio automatico è SPENTO (28/9): Clara prepara, Dre copia e manda."
echo "· Prima di consegnare: npm run controlla · test_invarianti.py · vite build"
echo "· Una prova a secco NON scrive: proponi() si ferma con --prova o PROVA=1."
echo "· Per cercare nel passato:  ricorda.py \"cosa cerchi\"  (negli script del vault)"
