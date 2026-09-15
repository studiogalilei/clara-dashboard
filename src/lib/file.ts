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
export async function apriFile(path: string): Promise<boolean> {
  const w = window.open('', '_blank', 'noopener')
  const url = await urlFile(path)
  if (!url) { w?.close(); return false }
  if (w) w.location.href = url
  else window.open(url, '_blank', 'noopener')
  return true
}

export function dimenticaFile(path: string) {
  firmate.delete(path)
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
