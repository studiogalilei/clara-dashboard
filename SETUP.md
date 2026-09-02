# ODYN CRM — setup (5 minuti, una volta sola)

## 1. Crea il progetto su Supabase
1. Vai su https://supabase.com/dashboard → **New project**
2. Nome: `odyn-crm` — scegli una password per il database (salvala) — Region: `eu-central-1` (Francoforte)
3. Aspetta ~2 minuti che il progetto sia pronto.

## 2. Copia le chiavi in `.env.local`
1. Nel progetto: **Project Settings → API**
2. Apri il file `.env.local` in questa cartella e incolla:
   - `VITE_SUPABASE_URL=` → il **Project URL**
   - `VITE_SUPABASE_ANON_KEY=` → la chiave **anon / publishable**
   - `SUPABASE_SERVICE_KEY=` → la chiave **service_role / secret** (⚠️ segreta, non condividerla)

## 3. Crea le tabelle
1. Nel progetto: **SQL Editor → New query**
2. Incolla tutto il contenuto di `supabase/schema.sql` → **Run**
   (deve dire "Success. No rows returned")

## 4. Crea il tuo utente (il login dell'app)
1. **Authentication → Users → Add user → Create new user**
2. Email: la tua — Password: una a tua scelta — ✅ Auto Confirm User

## 5. Importa i dati (lo fa Claude)
Da qui in poi dillo a Claude in chat: "importa i dati nel CRM".
Claude lancia `scripts/import_all.py` che carica tutto l'esistente
(CSV master, Smartlead, stati Falcon, esclusioni, ricontatti, PDF analisi).

## 6. Prova l'app in locale
```
cd ~/Documents/odyn-crm && npm run dev
```
Apri http://localhost:5173 ed entra con l'utente del punto 4.

## 7. Metti online (Vercel) — per averla sul telefono
```
npm i -g vercel && vercel login
vercel --prod
```
Poi su vercel.com → progetto → **Settings → Environment Variables** aggiungi
`VITE_SUPABASE_URL` e `VITE_SUPABASE_ANON_KEY` (NON la service key!) e rideploya.
Dal telefono: apri l'URL → Condividi → **Aggiungi a schermata Home** = app installata.

## Sync giornaliero
`scripts/sync_smartlead.py` aggiorna il CRM dall'output del segugio (sl_tracker).
È pensato per essere agganciato al check mattutino delle 8:13.
