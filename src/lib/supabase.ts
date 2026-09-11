import { createClient, type SupabaseClient } from '@supabase/supabase-js'
import { demoClient } from './demo'

const url = import.meta.env.VITE_SUPABASE_URL as string | undefined
const anon = import.meta.env.VITE_SUPABASE_ANON_KEY as string | undefined

// ?demo nella URL = Dashboard piena di dati finti, senza login.
export const demo = typeof window !== 'undefined' && window.location.search.includes('demo')

export const configured = demo || Boolean(url && anon)

export const supabase: SupabaseClient = demo
  ? (demoClient as unknown as SupabaseClient)
  : createClient(url ?? 'https://placeholder.supabase.co', anon ?? 'placeholder')

// IL TOKEN DI GOOGLE si vede una volta sola, nell'attimo del login: il
// listener deve esserci PRIMA che React parta, se no lo perde (11/9).
if (!demo) {
  supabase.auth.onAuthStateChange((_e, s) => {
    if (s?.provider_refresh_token) {
      try { localStorage.setItem('google-refresh', s.provider_refresh_token) } catch { /* niente */ }
      void import('./google').then((m) => m.salvaTokenGoogle(s))
    }
  })
}
