import { supabase } from './supabase'

// IL RISERVATO (Dre, 29/9: «la preparazione precall la vedo io e basta», «anche il
// prezzo, solo io»). Preparazioni delle call, prezzo suggerito e formula dei prezzi
// stanno in tabelle che il database fa leggere solo a chi ha profili.vede_riservato
// (schema_v68). A tutti gli altri risponde vuoto; qui si decide anche cosa disegnare.

let riservato: Promise<boolean> | null = null
export function vedoRiservato(): Promise<boolean> {
  if (!riservato) {
    riservato = (async () => {
      try { const { data } = await supabase.rpc('vedo_riservato'); return Boolean(data) } catch { return false }
    })()
  }
  return riservato
}

export interface Preparazione { testo: string; preparata_il: string }

/** La preparazione di quella call, se c'e' e se chi guarda puo' vederla. */
export async function preparazioneDi(agendaId: number | string | null | undefined): Promise<Preparazione | null> {
  if (agendaId == null) return null
  const { data } = await supabase.from('preparazioni').select('testo,preparata_il').eq('agenda_id', agendaId).maybeSingle()
  return (data as Preparazione | null) ?? null
}

/** L'ultima preparazione fatta per quell'azienda. */
export async function ultimaPreparazione(prospectId: string): Promise<Preparazione | null> {
  const { data } = await supabase.from('preparazioni').select('testo,preparata_il').eq('prospect_id', prospectId)
    .order('preparata_il', { ascending: false }).limit(1)
  return ((data as Preparazione[] | null) ?? [])[0] ?? null
}
