import type { Session } from '@supabase/supabase-js'
import { supabase } from './supabase'

// ENTRA CON GOOGLE (Dre, 11/9): «gli accessi come Google». Si entra con la
// mail @studiogalilei.com (il progetto Cloud e' interno: fuori dal dominio
// Google non fa passare nessuno). Al primo accesso chiediamo anche i permessi
// su Drive, Chat e Calendar: il refresh token che torna lo mettiamo in
// google_token (schema_v20), cosi' Clara puo' agire a nome di chi l'ha dato.

export const SCOPI = [
  'openid', 'email', 'profile',
  'https://www.googleapis.com/auth/drive',
  'https://www.googleapis.com/auth/calendar.readonly',
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
export async function salvaTokenGoogle(s: Session | null): Promise<void> {
  const rt = s?.provider_refresh_token
  if (!rt || !s?.user) return
  try {
    await supabase.from('google_token').upsert(
      { user_id: s.user.id, email: s.user.email ?? null, refresh_token: rt, scopes: SCOPI, aggiornato_il: new Date().toISOString() },
      { onConflict: 'user_id' })
  } catch { /* se non si salva, Clara non agisce a nome suo: lo si rivede al prossimo login */ }
}
