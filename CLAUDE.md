# LinkedIn Desk di Studio Galilei: istruzioni per chi lavora qui

> **Mi chiamo Achille.** Le regole complete, la memoria e lo storico stanno nel vault, in
> `~/Documents/Obsidian/studiogalilei/` (e nel repo privato `studiogalilei/cervello`).

Dal 27/11/2026 questo repository e' solo il **LinkedIn Desk**: l'outbound, Clara, la versione snella e il
Workspace sono stati tolti (Dre: «eliminiamo tutto cio' che riguarda l'outbound, il desk diventa per LinkedIn»).
Una copia dei dati dell'outbound sta sul Mac di Dre in `~/Documents/archivio-outbound-27-11/`; il codice vecchio
e' nella storia di git.

| dove | cosa c'e' |
|---|---|
| `src/desk/` | le due zone: Post (compositore e calendario) e Persone (le aziende del giorno) |
| `src/ui/`, `src/lib/` | pezzi dell'interfaccia, il client Supabase, la demo (`?demo`) |
| `scripts/linkedin_desk.py` | il lato della routine «LinkedIn Desk: scrivi i post» (Claude Code in cloud) |
| `supabase/` | lo schema, un file per versione (v121-v125 sono il LinkedIn Desk) e le funzioni |

**Il repository e' PUBBLICO.** Mai testi dei post, nomi di aziende o persone, chiavi nei file o nei commit.

**Prima di consegnare:** `npm run controlla`, `python3 scripts/test_invarianti.py`, `npm run build`, poi la prova a
schermo in demo (`npx vite preview`, `http://localhost:4173/?demo#/d/post`) a 390 px.

**Mai:** pubblicare su LinkedIn o mandare richieste e messaggi in automatico (le richieste le manda la persona), usare
programmi che girano su LinkedIn da soli, inventare storie vissute nei post automatici.
