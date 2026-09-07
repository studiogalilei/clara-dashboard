#!/bin/bash
# Mette l'ascoltatore di Clara fuori da ~/Documents e lo accende con launchd.
#
# PERCHE' FUORI: macOS non lascia leggere ~/Documents ai processi avviati da
# launchd (blocco TCC). Il 7/9 l'agente moriva subito con «Operation not
# permitted». Lo stesso blocco che gia' fermava il ponte di Falcon. Quindi il
# codice che gira si copia in ~/.clara, e questo script e' l'UNICO modo per
# aggiornarlo: si rilancia dopo ogni modifica agli script di Clara.
set -euo pipefail
QUI="$(cd "$(dirname "$0")/.." && pwd)"
CASA="$HOME/.clara"
mkdir -p "$CASA/scripts"
cp "$QUI/scripts/clara_ascolta.py" "$QUI/scripts/cervello.py" "$QUI/scripts/stanza.py" "$CASA/scripts/"
cp "$QUI/.env.local" "$CASA/.env.local"
chmod 600 "$CASA/.env.local"

PLIST="$HOME/Library/LaunchAgents/com.studiogalilei.clara-ascolta.plist"
cat > "$PLIST" <<PL
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key><string>com.studiogalilei.clara-ascolta</string>
  <key>ProgramArguments</key>
  <array>
    <string>/usr/bin/python3</string><string>-u</string>
    <string>$CASA/scripts/clara_ascolta.py</string>
  </array>
  <key>WorkingDirectory</key><string>$CASA</string>
  <key>EnvironmentVariables</key>
  <dict><key>PATH</key><string>$HOME/.local/bin:/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin</string></dict>
  <key>RunAtLoad</key><true/>
  <key>KeepAlive</key><true/>
  <key>StandardOutPath</key><string>/tmp/clara-ascolta.log</string>
  <key>StandardErrorPath</key><string>/tmp/clara-ascolta.err</string>
</dict>
</plist>
PL
launchctl bootout "gui/$(id -u)/com.studiogalilei.clara-ascolta" 2>/dev/null || true
: > /tmp/clara-ascolta.err
launchctl bootstrap "gui/$(id -u)" "$PLIST"
sleep 4
if pgrep -f "$CASA/scripts/clara_ascolta.py" >/dev/null; then
  echo "✓ Clara ascolta (pid $(pgrep -f "$CASA/scripts/clara_ascolta.py" | head -1)), codice in $CASA"
  tail -1 /tmp/clara-ascolta.log
else
  echo "✗ non e' partita:"; tail -3 /tmp/clara-ascolta.err; exit 1
fi
