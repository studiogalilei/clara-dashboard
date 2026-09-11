import { supabase } from './supabase'
import { WIDGET, type Chiave } from './widget'

// I WIDGET A RICHIESTA (Dre, 11/9): «le persone vedono i widget con i loro
// nomi, mi mandano la richiesta, io accetto e basta». Le voci di base le
// hanno tutti; il resto si chiede da Impostazioni, la richiesta arriva in
// chat a chi ha il ruolo ceo (Dre e Giacomo) e con un si' il widget compare
// nel menu. Tabella widget_accessi (schema_v22): la regola sta nel database.

export type StatoAccesso = 'richiesto' | 'approvato' | 'negato'
export interface Accesso { user_id: string; widget: string; stato: StatoAccesso; chiesto_il: string; deciso_il: string | null }

export async function sonoCeo(): Promise<boolean> {
  const { data } = await supabase.rpc('sono_ceo')
  return Boolean(data)
}

// CHI SONO, in una chiamata (schema_v23): l'utente effettivo, il ruolo vero,
// i widget concessi, e se un ceo sta guardando il Workspace nei panni di
// qualcun altro («vedi come»). Tutto il resto del database ragiona uguale.
export interface ChiSono { uid: string | null; nome: string | null; ruolo: 'ceo' | 'coordinamento'; concessi: Chiave[]; vista: { id: string; nome: string | null } | null }
export async function chiSono(): Promise<ChiSono> {
  const { data } = await supabase.rpc('chi_sono')
  const d = (data ?? {}) as Partial<ChiSono>
  return { uid: d.uid ?? null, nome: d.nome ?? null, ruolo: d.ruolo === 'ceo' ? 'ceo' : 'coordinamento', concessi: (d.concessi ?? []) as Chiave[], vista: d.vista ?? null }
}

// un ceo si mette nei panni di una persona (null = torna a se')
export async function vediCome(come_id: string | null): Promise<string | null> {
  const { data: { user } } = await supabase.auth.getUser()
  if (!user) return 'Non sei dentro'
  if (!come_id) {
    const { error } = await supabase.from('vista_come').delete().eq('ceo_id', user.id)
    return error ? error.message : null
  }
  const { error } = await supabase.from('vista_come').upsert({ ceo_id: user.id, come_id, da: new Date().toISOString() }, { onConflict: 'ceo_id' })
  return error ? error.message : null
}

// i miei: chiave → stato
export async function mieiAccessi(): Promise<Partial<Record<Chiave, StatoAccesso>>> {
  const { data: { user } } = await supabase.auth.getUser()
  if (!user) return {}
  const { data } = await supabase.from('widget_accessi').select('widget,stato').eq('user_id', user.id)
  const m: Partial<Record<Chiave, StatoAccesso>> = {}
  for (const r of (data as Array<{ widget: Chiave; stato: StatoAccesso }>) ?? []) m[r.widget] = r.stato
  return m
}

// tutti (solo i ceo li vedono, per la policy)
export async function tuttiAccessi(): Promise<Accesso[]> {
  const { data } = await supabase.from('widget_accessi').select('*').limit(2000)
  return (data as Accesso[]) ?? []
}

// chiedo io, per me: la riga e la domanda in chat a chi decide
export async function chiedi(widget: Chiave, nomeUtente: string): Promise<string | null> {
  const { data: { user } } = await supabase.auth.getUser()
  if (!user) return 'Non sei dentro'
  const w = WIDGET.find((x) => x.chiave === widget)
  const { error } = await supabase.from('widget_accessi')
    .upsert({ user_id: user.id, widget, stato: 'richiesto', chiesto_il: new Date().toISOString(), deciso_il: null, deciso_da: null }, { onConflict: 'user_id,widget' })
  if (error) return error.message
  await supabase.from('proposte').insert({
    tipo: 'accesso',
    titolo: `${nomeUtente} chiede il widget ${w?.nome ?? widget}`,
    perche: w ? `${w.nome}: ${w.cosa}. Con un si' gli compare nel menu.` : null,
    azione: { accesso: { user_id: user.id, widget, nome: nomeUtente } },
  })
  return null
}

// decide un ceo (anche senza richiesta: dare o togliere dalla mappa)
export async function decidi(user_id: string, widget: string, si: boolean): Promise<string | null> {
  const { data: { user } } = await supabase.auth.getUser()
  const { error } = await supabase.from('widget_accessi')
    .upsert({ user_id, widget, stato: si ? 'approvato' : 'negato', deciso_il: new Date().toISOString(), deciso_da: user?.id ?? null }, { onConflict: 'user_id,widget' })
  return error ? error.message : null
}
