import { createClient, type SupabaseClient } from '@supabase/supabase-js'
import { demoClient } from './demo'

const url = import.meta.env.VITE_SUPABASE_URL as string | undefined
const anon = import.meta.env.VITE_SUPABASE_ANON_KEY as string | undefined

// ?demo nell'indirizzo = il Desk con dati finti, senza login: per vedere la forma e per i collaudi.
export const demo = typeof window !== 'undefined' && window.location.search.includes('demo')

export const supabase: SupabaseClient = demo
  ? (demoClient as unknown as SupabaseClient)
  : createClient(url ?? 'https://placeholder.supabase.co', anon ?? 'placeholder')
