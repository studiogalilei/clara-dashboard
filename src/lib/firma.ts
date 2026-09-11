import { supabase } from './supabase'

// LA FIRMA DI OGNUNO (Dre, 11/9): «la possibilita' di avere la propria firma
// li', comoda». Sta nel profilo come PNG (data URL), la disegni una volta.
// Il timbro dell'azienda e' un file solo nel bucket vault: timbro/timbro.png.

export async function leggiFirma(): Promise<string | null> {
  const { data: { user } } = await supabase.auth.getUser()
  if (!user) return null
  const { data } = await supabase.from('profili').select('firma').eq('id', user.id).maybeSingle()
  return (data as { firma: string | null } | null)?.firma ?? null
}

export async function scriviFirma(dataUrl: string | null): Promise<string | null> {
  const { data: { user } } = await supabase.auth.getUser()
  if (!user) return 'Non sei dentro'
  const { error } = await supabase.from('profili').update({ firma: dataUrl }).eq('id', user.id)
  return error ? error.message : null
}

export const TIMBRO_PATH = 'timbro/timbro.png'

export async function leggiTimbro(): Promise<string | null> {
  const { data } = await supabase.storage.from('vault').list('timbro', { limit: 5 })
  if (!data?.some((f) => f.name === 'timbro.png')) return null
  return supabase.storage.from('vault').getPublicUrl(TIMBRO_PATH).data.publicUrl + '?v=' + Date.now()
}

export async function scriviTimbro(f: File): Promise<string | null> {
  const { error } = await supabase.storage.from('vault').upload(TIMBRO_PATH, f, { upsert: true, contentType: 'image/png' })
  return error ? error.message : null
}

// da un'immagine (URL o data URL) ai byte PNG, per pdf-lib
export async function bytePng(src: string): Promise<Uint8Array> {
  const r = await fetch(src)
  return new Uint8Array(await r.arrayBuffer())
}
