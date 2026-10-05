import { supabase } from './supabase'

// GLI EVENTI ATTORNO A ADESSO (5/10). Radar e Calendario chiedevano «da N giorni fa,
// in ordine, al massimo M»: se gli eventi passati erano tanti, il tetto tagliava proprio
// quelli futuri, e la prossima call poteva sparire. Passato e futuro si chiedono a parte,
// ognuno col suo tetto, e si rimettono in ordine.
export async function agendaAttorno(giorniPrima: number, quantiPrima: number, quantiDopo: number, filtro?: { conOwner?: boolean }) {
  const adesso = new Date().toISOString()
  const da = new Date(Date.now() - giorniPrima * 86400e3).toISOString()
  let passato = supabase.from('agenda').select('*').gte('at', da).lt('at', adesso)
  let futuro = supabase.from('agenda').select('*').gte('at', adesso)
  if (filtro?.conOwner) {
    passato = passato.not('owner', 'is', null)
    futuro = futuro.not('owner', 'is', null)
  }
  const [p, f] = await Promise.all([
    passato.order('at', { ascending: false }).limit(quantiPrima),
    futuro.order('at', { ascending: true }).limit(quantiDopo),
  ])
  return {
    data: [...((p.data ?? []) as unknown[]).reverse(), ...((f.data ?? []) as unknown[])],
    error: p.error ?? f.error,
  }
}
