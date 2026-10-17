// IL PONTE (17/10/2026): entrare nell'app del telefono con un codice di 6 cifre.
// Sull'iPhone l'app aggiunta alla Home ha una memoria sua, separata da Safari: chi e' gia'
// dentro altrove chiede il codice («Collega il telefono»), e nell'app lo scrive sulla porta.
// Il lavoro vero lo fa supabase/functions/ponte (la chiave di servizio non sta nel browser).
import { supabase } from './supabase'

async function chiama(corpo: Record<string, unknown>): Promise<Record<string, unknown>> {
  const { data, error } = await supabase.functions.invoke('ponte', { body: corpo })
  if (error) {
    // la funzione risponde {errore} anche quando dice di no: si legge quello, non «non-2xx»
    const ctx = (error as { context?: Response }).context
    const testo = ctx && typeof ctx.json === 'function' ? await ctx.json().then((j: { errore?: string }) => j.errore).catch(() => null) : null
    throw new Error(testo || 'Non riesco a raggiungere il Workspace: controlla la connessione')
  }
  return (data ?? {}) as Record<string, unknown>
}

/** Il codice per far entrare un altro dispositivo: 6 cifre, vale pochi minuti, una volta. */
export async function creaCodice(): Promise<{ codice: string; minuti: number }> {
  const r = await chiama({ azione: 'crea' })
  if (typeof r.codice !== 'string') throw new Error(String(r.errore ?? 'Non riesco a fare il codice'))
  return { codice: r.codice, minuti: Number(r.minuti ?? 10) }
}

/** Entra con il codice: torna null se sei dentro, se no la frase che dice perche' no. */
export async function entraConCodice(codice: string): Promise<string | null> {
  try {
    const r = await chiama({ azione: 'usa', codice })
    if (typeof r.token_hash !== 'string') return String(r.errore ?? 'Codice non valido')
    const { error } = await supabase.auth.verifyOtp({ token_hash: r.token_hash, type: 'magiclink' })
    return error ? 'La porta non si apre: ' + error.message : null
  } catch (e) {
    return e instanceof Error ? e.message : String(e)
  }
}
