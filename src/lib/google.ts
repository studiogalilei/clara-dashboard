import type { Session } from '@supabase/supabase-js'
import { supabase } from './supabase'

// ENTRA CON GOOGLE (Dre, 11/9): «gli accessi come Google». Si entra con la
// mail @studiogalilei.com (il progetto Cloud e' interno: fuori dal dominio
// Google non fa passare nessuno). Al primo accesso chiediamo anche i permessi
// su Drive, Chat e Calendar: il refresh token che torna lo mettiamo in
// google_token (schema_v20), cosi' Clara puo' agire a nome di chi l'ha dato.

// I permessi si chiedono una volta sola, al primo accesso: quello che non
// chiediamo oggi vuol dire far ricollegare tutti domani. Gmail serve al
// «sistema vivo» (Dre, 15/9): Clara legge la casella, capisce cosa e'
// successo e aggiorna gli stati da sola, e una bozza approvata parte
// davvero invece di passare per copia e incolla. Calendar per intero (non
// solo gli eventi) perche' le nostre scadenze vanno in un calendario a
// parte, «SG Scadenze», che si accende e si spegne con un clic: crearlo
// vuole il permesso pieno.
export const SCOPI = [
  'openid', 'email', 'profile',
  'https://www.googleapis.com/auth/drive',
  'https://www.googleapis.com/auth/calendar',
  'https://www.googleapis.com/auth/gmail.readonly',
  'https://www.googleapis.com/auth/gmail.send',
  'https://www.googleapis.com/auth/chat.spaces',
  'https://www.googleapis.com/auth/chat.messages',
  'https://www.googleapis.com/auth/chat.memberships',
].join(' ')

export async function entraConGoogle(): Promise<string | null> {
  const { error } = await supabase.auth.signInWithOAuth({
    provider: 'google',
    options: {
      redirectTo: window.location.origin + import.meta.env.BASE_URL,
      scopes: SCOPI,
      queryParams: { access_type: 'offline', prompt: 'consent', hd: 'studiogalilei.com' },
    },
  })
  return error ? error.message : null
}

// dopo il login: se Google ha dato il refresh token, lo teniamo (una riga per persona)
export async function salvaTokenGoogle(s: Session | null): Promise<string | null> {
  let rt = s?.provider_refresh_token ?? null
  if (!rt) { try { rt = localStorage.getItem('google-refresh') } catch { /* niente */ } }
  if (!rt || !s?.user) return 'nessun token da salvare'
  const { error } = await supabase.from('google_token').upsert(
    { user_id: s.user.id, email: s.user.email ?? null, refresh_token: rt, scopes: SCOPI, aggiornato_il: new Date().toISOString() },
    { onConflict: 'user_id' })
  if (error) { console.warn('google_token non salvato:', error.message); return error.message }
  try { localStorage.removeItem('google-refresh') } catch { /* niente */ }
  return null
}

// c'e' il token di chi e' dentro? (funzione security definer, schema_v20)
export async function collegato(): Promise<boolean> {
  const { data } = await supabase.rpc('ho_il_token_google')
  return Boolean(data)
}
