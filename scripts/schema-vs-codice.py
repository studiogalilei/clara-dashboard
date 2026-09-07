#!/usr/bin/env python3
"""Il codice e il database vero dicono la stessa cosa?

Nasce il 7/9/2026. Tutta la Dashboard e' stata collaudata in demo, dove il
finto Supabase risponde sempre di si': e' esattamente li' che si nascondono
i bug peggiori, quelli che si vedono solo il giorno che apri l'app vera.
Il 4 settembre uno di questi ha fatto morire la home, e l'ho preso per caso.

Questo confronta ogni tabella e ogni colonna che il codice nomina con quelle
che esistono davvero, e si lamenta se qualcosa non c'e'. Non serve un test
che finge: serve chiedere al database.

Uso:  python3 scripts/schema-vs-codice.py
"""
import json
import os
import re
import subprocess
import sys
import urllib.request

RADICE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def leggi_env(nome):
    for f in ('.env.local', '.env'):
        p = os.path.join(RADICE, f)
        if not os.path.exists(p):
            continue
        for riga in open(p, encoding='utf-8'):
            if riga.strip().startswith(nome + '='):
                return riga.split('=', 1)[1].strip().strip('"\'')
    return None


def schema_vero():
    url = leggi_env('VITE_SUPABASE_URL')
    chiave = leggi_env('SUPABASE_SERVICE_KEY') or leggi_env('SUPABASE_SERVICE_ROLE_KEY')
    if not url or not chiave:
        print('✗ manca VITE_SUPABASE_URL o la service key in .env.local')
        sys.exit(2)
    req = urllib.request.Request(
        url.rstrip('/') + '/rest/v1/',
        headers={'apikey': chiave, 'Authorization': 'Bearer ' + chiave})
    with urllib.request.urlopen(req, timeout=20) as r:
        d = json.load(r)
    return {t: set(v.get('properties', {})) for t, v in d.get('definitions', {}).items()}


def sorgenti():
    out = subprocess.run(['git', 'ls-files', 'src', 'scripts'], cwd=RADICE,
                         capture_output=True, text=True).stdout.split()
    return [f for f in out if f.endswith(('.ts', '.tsx', '.py'))]


# from('tabella'), ma non storage.from('secchio'): quello e' un secchio di
# file, non una tabella, e non ha colonne da controllare
TABELLA = re.compile(r"""(?<!storage\.)from\(\s*['"]([a-z_][a-z0-9_]*)['"]\s*\)""")
SELECT = re.compile(r"""\.select\(\s*['"]([^'"*()]+)['"]""")
COLONNA = re.compile(r"""\.(?:eq|neq|gt|gte|lt|lte|is|in|not|order)\(\s*['"]([a-z_][a-z0-9_]*)['"]""")


def controlla():
    vero = schema_vero()
    problemi = []
    for f in sorgenti():
        testo = open(os.path.join(RADICE, f), encoding='utf-8').read()
        for m in TABELLA.finditer(testo):
            tab = m.group(1)
            if tab not in vero:
                problemi.append(f'{f}: la tabella «{tab}» non esiste nel database')
                continue
            # le colonne nominate da qui al prossimo from(): senza il taglio
            # la lettura sbordava sulla query dopo e accusava colonne
            # innocenti (29 falsi allarmi al primo giro, 7/9)
            dopo = TABELLA.search(testo, m.end())
            fine = min(dopo.start() if dopo else len(testo), m.end() + 600)
            pezzo = testo[m.end():fine]
            nomi = set()
            for s in SELECT.findall(pezzo):
                nomi |= {c.strip() for c in s.split(',') if c.strip()}
            nomi |= set(COLONNA.findall(pezzo))
            for c in sorted(nomi - vero[tab]):
                problemi.append(f'{f}: {tab}.{c} non esiste (la tabella ha {len(vero[tab])} colonne)')
    return vero, problemi


if __name__ == '__main__':
    vero, problemi = controlla()
    print(f'Database vero: {len(vero)} fra tabelle e viste.')
    if not problemi:
        print('✓ ogni tabella e ogni colonna che il codice nomina esiste davvero.')
        sys.exit(0)
    print(f'\n✗ {len(problemi)} disaccordi fra codice e database:\n')
    for p in problemi:
        print('  ' + p)
    sys.exit(1)
