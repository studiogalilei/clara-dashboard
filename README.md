# SG Workspace

Il posto di lavoro di Studio Galilei, con Clara dentro. App: https://studiogalilei.github.io/clara/

**La documentazione tecnica, verificata, è in [docs/WORKSPACE.md](docs/WORKSPACE.md):**
cos'è, com'è fatto (frontend, database, funzioni cloud, direttore, Clara),
come funziona il tempo reale, dove stanno i segreti, come si pubblica.

Per iniziare:

```
npm install
npm run dev            # http://localhost:5173  (con ?demo: dati finti, senza login)
npm run controlla      # tsc + oxlint + vitest, prima di ogni push
npm run build
```

Altri documenti che contano:

- `docs/LA-STANZA-DI-CLARA.md`: le regole di Clara (propone, non decide)
- `docs/clara-sg-outbound.md`: il playbook delle risposte outbound, usato da `scripts/bozze.py`
- `docs/squadra/`: la scheda di ogni persona, in markdown e PDF
- `supabase/schema_v*.sql`: le migrazioni, una per cambiamento, con il perché in testa

I file `LEGGIMI-PRIMA.md`, `SETUP.md`, `CANTIERE-CRUSCOTTO.md` e `docs/ARCHITETTURA-CLARA.md`
sono storia di agosto e settembre 2026: raccontano come si è arrivati qui, non com'è oggi.
