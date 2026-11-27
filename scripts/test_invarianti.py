#!/usr/bin/env python3
"""Le regole del LinkedIn Desk che si difendono da sole (27/11/2026). Girano nel cancello `controlla` a ogni push.

1. La settimana (Dre, 27/11 notte): lunedi' e mercoledi' post con disegno, martedi' e giovedi' una storia dal lavoro
   (non esce mai da solo), venerdi' e fine settimana liberi.
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

if linkedin_desk.SETTIMANA != {0: "post", 1: "storia", 2: "post", 3: "storia"}:
    errori.append("la settimana deve essere: lun e mer post col disegno, mar e gio storia dal lavoro, ven libero")
if "copy_video" in (QUI / "linkedin_desk.py").read_text().split("def riempi")[1].split("def settimana")[0]:
    errori.append("i giorni automatici non chiedono piu' copioni video: Dre non fa piu' i video")
if 'v.get("framework") == "Copy video"' not in (QUI / "linkedin_desk.py").read_text():
    errori.append("i copioni video devono restare bozza: non escono mai da soli")

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

if 'rivedere = any(v.get("da_rivedere")' not in script:
    errori.append("le storie inventate (da_rivedere) devono restare bozza: escono solo con l'approvazione della persona")

if errori:
    print("INVARIANTI ROTTI:\n  " + "\n  ".join(errori))
    sys.exit(1)
print("invarianti del LinkedIn Desk: tutti in piedi")
