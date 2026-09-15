import { supabase } from './supabase'
import { urlFile, dimenticaFile } from './file'

// LA FIRMA DI OGNUNO (Dre, 11/9): «la possibilita' di avere la propria firma
// li', comoda». Sta nel profilo come PNG (data URL), la disegni una volta.
// Il timbro dell'azienda e' un file solo nel bucket vault: azienda/timbro.png.

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

export const TIMBRO_PATH = 'azienda/timbro.png'

export async function leggiTimbro(): Promise<string | null> {
  const { data } = await supabase.storage.from('vault').list('azienda', { limit: 20 })
  if (!data?.some((f) => f.name === 'timbro.png')) return null
  dimenticaFile(TIMBRO_PATH)
  return urlFile(TIMBRO_PATH)
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
