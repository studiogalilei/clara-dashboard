import { supabase } from './supabase'

// L'INDIRIZZO DI UN FILE (15/9): il bucket dei Documenti e' privato, quindi
// ogni file si apre con una URL firmata che scade. Si chiede al volo e si
// tiene in memoria finche' vale: se no ogni anteprima e' una chiamata in piu'.
const firmate = new Map<string, { url: string; scade: number }>()

export async function urlFile(path: string, minuti = 60): Promise<string | null> {
  const ora = Date.now()
  const c = firmate.get(path)
  if (c && c.scade > ora + 30_000) return c.url
  const { data, error } = await supabase.storage.from('vault').createSignedUrl(path, minuti * 60)
  if (error || !data?.signedUrl) return null
  firmate.set(path, { url: data.signedUrl, scade: ora + minuti * 60_000 })
  return data.signedUrl
}

// apre il file in una scheda nuova (il clic deve partire prima della firma,
// se no Safari blocca la finestra: si apre subito e si punta dopo)
// BUG (Alex 17/9, Lorenzo 19/9: «Apri restituisce una pagina about:blank»):
// con 'noopener' il browser NON restituisce la finestra, quindi la scheda
// vuota restava vuota e la seconda apertura, dopo l'attesa, la bloccava il
// popup blocker. Si apre senza noopener (la finestra e' nostra), si stacca
// l'opener a mano, poi si punta al file.
export async function apriFile(path: string): Promise<boolean> {
  const w = window.open('', '_blank')
  if (w) { try { w.opener = null } catch { /* niente */ } }
  const url = await urlFile(path)
  if (!url) { w?.close(); return false }
  if (w) w.location.replace(url)
  else window.open(url, '_blank')
  return true
}

export function dimenticaFile(path: string) {
  firmate.delete(path)
}

// CARICARE UN FILE (6/10): la stessa sequenza viveva copiata in tre posti
// (Vault, Chat, Scheda), ognuno col suo modo di sbagliare. Qui una volta sola:
// sale nello storage, nasce la riga nei Documenti, e se la riga non nasce il
// file si toglie (niente orfani nel bucket). Il titolo e' il nome del file
// senza estensione, come fa Google.
export interface FileCaricato { id: number; nome: string; path: string; mime: string | null; dimensione: number | null; at: string }

export async function caricaFile(prospectId: string, f: File, nota?: string): Promise<{ file: FileCaricato | null; errore: string | null }> {
  const pulito = f.name.replace(/[^a-zA-Z0-9._-]+/g, '-')
  const path = `clienti/${prospectId}/${Date.now()}-${pulito}`
  const { error } = await supabase.storage.from('vault').upload(path, f)
  if (error) return { file: null, errore: `Non sono riuscito a caricare «${f.name}»: ${error.message}` }
  const { data, error: e2 } = await supabase.from('vault_file')
    .insert({ nome: f.name.replace(/\.[^.]+$/, ''), path, mime: f.type || null, dimensione: f.size, prospect_id: prospectId, sezione: 'clienti', nota: nota ?? null })
    .select('id,nome,path,mime,dimensione,at').single()
  if (e2 || !data) {
    await supabase.storage.from('vault').remove([path])
    return { file: null, errore: `Il file è salito ma non è finito nei Documenti: ${e2?.message ?? ''}` }
  }
  return { file: data as FileCaricato, errore: null }
}

// tanti file insieme (la griglia dei Documenti): una chiamata sola
export async function urlFileTanti(paths: string[], minuti = 60): Promise<Record<string, string>> {
  const ora = Date.now()
  const fuori = paths.filter((p) => {
    const c = firmate.get(p)
    return !c || c.scade <= ora + 30_000
  })
  if (fuori.length) {
    for (let i = 0; i < fuori.length; i += 100) {
      const pezzo = fuori.slice(i, i + 100)
      const { data } = await supabase.storage.from('vault').createSignedUrls(pezzo, minuti * 60)
      for (const r of data ?? []) {
        if (r.signedUrl && r.path) firmate.set(r.path, { url: r.signedUrl, scade: ora + minuti * 60_000 })
      }
    }
  }
  const out: Record<string, string> = {}
  for (const p of paths) {
    const c = firmate.get(p)
    if (c) out[p] = c.url
  }
  return out
}
