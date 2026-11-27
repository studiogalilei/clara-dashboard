#!/usr/bin/env python3
"""Le regole del LinkedIn Desk che si difendono da sole (27/11/2026). Girano nel cancello `controlla` a ogni push.

1. Gli automatici escono solo lunedi', mercoledi' e venerdi' (Dre, 27/11: «sono 3 post a settimana»).
2. Lo script della routine non pubblica mai su LinkedIn e non manda mail: suggerisce e scrive bozze. Dal 27/11 (Dre:
   «colleghiamo i post automatici») pubblica solo la funzione linkedin-pubblica, e solo i post «programmato» arrivati
   alla loro ora, mai piu' vecchi di 6 ore.
3. Il repository e' pubblico: nessun testo di post e nessuna chiave nei file.
"""
import os
import pathlib
import re
import sys

QUI = pathlib.Path(__file__).resolve().parent
RADICE = QUI.parent
sys.path.insert(0, str(QUI))
os.environ.setdefault("VITE_SUPABASE_URL", "https://prova.supabase.co")
os.environ.setdefault("SUPABASE_SERVICE_KEY", "prova")

import linkedin_desk  # noqa: E402

errori = []

if linkedin_desk.GIORNI_AUTOMATICI != {0, 2, 4}:
    errori.append("gli automatici devono essere lunedi', mercoledi', venerdi'")

script = (QUI / "linkedin_desk.py").read_text()
for vietato in ("api.linkedin.com", "ugcPosts", "/rest/posts", "smtp", "gmail.googleapis"):
    if vietato in script:
        errori.append(f"linkedin_desk.py non deve contenere «{vietato}»: la routine non pubblica e non manda")

chiave = re.compile(r"sk-[A-Za-z0-9_-]{20,}|eyJ[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{20,}|sbp_[a-f0-9]{20,}|ghp_[A-Za-z0-9]{30,}")
for f in list(RADICE.glob("src/**/*.ts*")) + list(QUI.glob("*.py")) + list(RADICE.glob("supabase/**/*.ts")):
    if chiave.search(f.read_text(errors="ignore")):
        errori.append(f"chiave nel file {f.relative_to(RADICE)}")

pubblica = (RADICE / "supabase/functions/linkedin-pubblica/index.ts").read_text()
if '.eq("stato", "programmato")' not in pubblica or "6 * 3600000" not in pubblica:
    errori.append("linkedin-pubblica deve pubblicare solo i post programmato, arrivati alla loro ora e non piu' vecchi di 6 ore")

if errori:
    print("INVARIANTI ROTTI:\n  " + "\n  ".join(errori))
    sys.exit(1)
print("invarianti del LinkedIn Desk: tutti in piedi")
