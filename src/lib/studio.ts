import { supabase } from './supabase'
import { STUDIO_VUOTO, type DatiStudio } from './condizioni'

// I DATI DELLO STUDIO (15/9): ragione sociale, P.IVA, sede, IBAN, aliquota.
// Vanno nei documenti che il cliente firma. Si scrivono una volta sola in
// Impostazioni; stanno in `istruzioni` alla chiave «studio», che e' dei ceo.

export type { DatiStudio } from './condizioni'
export { STUDIO_VUOTO, mancaStudio } from './condizioni'

let letti: DatiStudio | null = null

export async function datiStudio(): Promise<DatiStudio> {
  if (letti) return letti
  const { data } = await supabase.from('istruzioni').select('testo').eq('chiave', 'studio').maybeSingle()
  let d: DatiStudio
  try {
    d = { ...STUDIO_VUOTO, ...JSON.parse((data as { testo: string } | null)?.testo || '{}') }
  } catch {
    d = { ...STUDIO_VUOTO }
  }
  letti = d
  return d
}

export async function scriviStudio(d: DatiStudio): Promise<string | null> {
  const { error } = await supabase.from('istruzioni')
    .upsert({ chiave: 'studio', titolo: 'Dati dello Studio', testo: JSON.stringify(d), aggiornata: new Date().toISOString() }, { onConflict: 'chiave' })
  if (error) return error.message
  letti = { ...STUDIO_VUOTO, ...d }
  return null
}
