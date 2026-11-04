// IL DESK (4/11/2026): i dati. Tutto passa dalle funzioni del database fatte per il Desk
// (schema_v104: clara_coda, clara_relazione, clara_cerca, clara_call) e dalle scritture su
// clara_decisioni, che il database lascia fare solo ai ceo. Nessuna mail parte da qui: il Desk
// approva, il postino (scripts/clara_manda.py) manda entro cinque minuti, o subito se il
// direttore risponde alla chiamata.
import { supabase } from '../lib/supabase'
import { aggiungiNota } from '../snella/dati'
import { MOTIVO_WHATSAPP, NOTA_WHATSAPP } from './regole'
export { aggiungiNota }

export type Mossa = 'send_analysis' | 'reply' | 'offer_slots' | 'book_meeting' | 'callback' | 'wait' | 'close' | 'escalate'
export type Stato = 'proposta' | 'approvata' | 'in_invio' | 'inviata' | 'scartata' | 'superata' | 'fatta'

export interface Prova { messaggio: number; frase: string }
export interface Consiglio { numero?: string; perche?: string; esito?: string; esito_il?: string }
export interface Giudizio { pericoloso?: boolean; errore_pericoloso?: string; mossa?: string; mossa_migliore?: string; testo?: string; nota?: string; errore?: string }

export interface Decisione {
  id: string; prospect_id: string; risposta_il: string; mossa: Mossa; owner: string | null; entro_il: string | null
  testo: string | null; testo_clara: string | null; perche: string | null; prove: Prova[] | null
  richiamo: { numero?: string; quando?: string; perche?: string } | null
  consiglio?: Consiglio | null
  segnali: string[] | null; giudice: Giudizio | null; stato: Stato; lead_testo: string | null
  approvata_il: string | null; inviata_il: string | null; verificata_il: string | null; errore: string | null
  esito: string | null; esito_il: string | null; creato_il: string; versione: string; dollari: number | null
  dre_giudizio: 'ok' | 'no' | null
  azienda: string | null; persona: string | null; ruolo: string | null; email: string; citta: string | null; settore: string | null
  telefono: string | null; sito: string | null; analisi_pdf: boolean; analisi_mandata: boolean; fase: string | null
  classe: string | null; ultima_risposta: string | null; prossima_call: string | null
  approvata_da?: string | null; in_mano_a?: string | null; in_mano_motivo?: string | null; in_mano_il?: string | null
  fit?: string | null
}

export interface Messaggio { at: string; tipo: 'email_in' | 'email_out'; testo: string | null; casella: string | null }
export interface Relazione {
  lead: {
    id: string; azienda: string | null; persona: string | null; ruolo: string | null; email: string; citta: string | null
    settore: string | null; telefono: string | null; sito: string | null; analisi_pdf: string | null; analisi_mandata: boolean
    analisi_il: string | null; fase: string | null; classe: string | null; ultima_risposta: string | null; fuori: boolean
    no_followup: boolean; fonte: string | null; fit: string | null; fit_motivo: string | null; cosa_fa: string | null; campagna: string | null
    in_mano_a?: string | null; in_mano_motivo?: string | null; in_mano_il?: string | null; altre_email?: string[] | null
    fit_meta?: string | null; fit_meta_motivo?: string | null; fit_linkedin?: string | null; fit_linkedin_motivo?: string | null
    canale?: string | null; ticket?: string | null
  } | null
  filo: Messaggio[]
  decisioni: Array<{ id: string; risposta_il: string; mossa: Mossa; owner: string | null; testo: string | null; perche: string | null; stato: Stato; inviata_il: string | null; esito: string | null; dre_giudizio: string | null; dre_nota: string | null; creato_il: string }>
  agenda: Array<{ at: string; tipo: string | null; titolo: string | null; link: string | null }>
  note: Array<{ id?: number; at: string; tipo: string; testo: string; autore?: string | null }>
  scheda: { stato: string | null; prossima_mossa: string | null; prossima_il: string | null; responsabile: string | null } | null
}
export interface Trovato { id: string; azienda: string | null; persona: string | null; email: string; citta: string | null; telefono?: string | null; fase: string | null; classe: string | null; ultima_risposta: string | null; analisi_mandata: boolean }
export interface NotaChiamata { at: string; testo: string }
export interface Chiamata {
  id: string; chiamata_id: string | null; prospect_id: string | null; azienda: string | null; persona: string | null; telefono: string | null
  quando?: string | null; perche?: string | null; risposta_il?: string | null; lead_testo?: string | null; richiamare_il: string | null
  note: NotaChiamata[]; origine: 'clara' | 'dre' | 'consiglio'; creato_il?: string; fase?: string | null; analisi_mandata?: boolean | null; ultima_risposta?: string | null
  whatsapp_il?: string | null                 // 4/11: «l'ho passato su WhatsApp»: resta in lista come contatto di Dre
  consiglio?: Consiglio | null                // quando e' un «Ti consiglio di chiamare» di Clara
}
export interface Call {
  prossime: Array<{ id?: number; at: string; tipo: string | null; titolo: string | null; link: string | null; prospect_id: string | null; azienda: string | null; persona: string | null; telefono: string | null; preparazione: string | null }>
  richiami: Chiamata[]
  mie?: Chiamata[]
  consigli?: Chiamata[]
}
export interface Operazione { chiave: string; nome: string; ultima_corsa: string | null; ultimo_esito: string | null; ultimo_dettaglio: string | null; attiva: boolean }

/** La spesa dei modelli (uso_modelli, letta solo dai ceo): oggi e gli ultimi 7 giorni, in dollari, per Clara
 *  (il cervello: scopo clara_sdr) e il giudice (esame_clara). token_in e' gia' pesato per la cache. */
const PREZZI: Record<string, { in: number; out: number }> = {
  'claude-fable-5-1': { in: 10, out: 50 }, 'claude-opus-5-5': { in: 4, out: 20 }, 'claude-sonnet-5-5': { in: 2, out: 10 },
  'claude-sonnet-5': { in: 2, out: 10 }, 'claude-haiku-5-5': { in: 0.1, out: 0.5 },
}
export interface Spesa { oggi: number; sette: number; oggiCervello: number; oggiGiudice: number; chiamateOggi: number; giorniConSpesa: number }
export async function leggiSpesa(): Promise<Spesa> {
  const da = new Date(Date.now() - 7 * 864e5).toISOString()
  const { data, error } = await supabase.from('uso_modelli').select('il,scopo,modello,token_in,token_out')
    .in('scopo', ['clara_sdr', 'esame_clara']).gte('il', da).limit(5000).abortSignal(entro())
  if (error) guasto(error)
  const inizioOggi = new Date(); inizioOggi.setHours(0, 0, 0, 0)
  const out: Spesa = { oggi: 0, sette: 0, oggiCervello: 0, oggiGiudice: 0, chiamateOggi: 0, giorniConSpesa: 0 }
  const giorni = new Set<string>()
  for (const r of data ?? []) {
    const p = PREZZI[r.modello as string] ?? PREZZI['claude-opus-5-5']
    const d = ((r.token_in as number) * p.in + (r.token_out as number) * p.out) / 1e6
    out.sette += d; giorni.add(String(r.il).slice(0, 10))
    if (new Date(r.il as string) >= inizioOggi) {
      out.oggi += d; out.chiamateOggi += 1
      if (r.scopo === 'clara_sdr') out.oggiCervello += d; else out.oggiGiudice += d
    }
  }
  out.giorniConSpesa = giorni.size
  return out
}

const ATTESA_MS = 20_000
function entro(ms = ATTESA_MS): AbortSignal {
  const c = new AbortController()
  setTimeout(() => c.abort(), ms)
  return c.signal
}
function guasto(e: { message?: string } | null): never {
  if (/abort/i.test(e?.message ?? '')) throw new Error('La connessione non risponde. Controlla la rete e riprova.')
  if (!navigator.onLine || /failed to fetch|load failed|networkerror/i.test(e?.message ?? '')) throw new Error('Sei senza connessione: riprovo da solo appena torna.')
  throw new Error(e?.message || 'Il database non ha risposto')
}

export async function leggiCoda(giorni = 30): Promise<Decisione[]> {
  const { data, error } = await supabase.rpc('clara_coda', { giorni }).abortSignal(entro())
  if (error) guasto(error)
  return (data ?? []) as Decisione[]
}

export async function leggiRelazione(id: string): Promise<Relazione> {
  const { data, error } = await supabase.rpc('clara_relazione', { chi: id }).abortSignal(entro())
  if (error) guasto(error)
  return data as Relazione
}

export async function cerca(q: string): Promise<Trovato[]> {
  const { data, error } = await supabase.rpc('clara_cerca', { q }).abortSignal(entro())
  if (error) guasto(error)
  return (data ?? []) as Trovato[]
}

export async function leggiCall(): Promise<Call> {
  const { data, error } = await supabase.rpc('clara_call').abortSignal(entro())
  if (error) guasto(error)
  return (data ?? { prossime: [], richiami: [], consigli: [], mie: [] }) as Call
}

/** Una call del calendario collegata a un'azienda da Dre (4/11), o segnata come interna (lead=false). */
export async function collegaCall(evento: number, prospectId: string | null, lead = true): Promise<void> {
  const { data, error } = await supabase.rpc('clara_collega_call', { evento, chi: prospectId, lead }).abortSignal(entro())
  if (error) guasto(error)
  const r = data as { ok?: boolean; perche?: string } | null
  if (r && r.ok === false) throw new Error(r.perche || 'Non collegata')
}

export async function leggiOperazioni(): Promise<Operazione[]> {
  const { data, error } = await supabase.from('operazioni').select('chiave,nome,ultima_corsa,ultimo_esito,ultimo_dettaglio,attiva')
    .in('chiave', ['clara_prova', 'clara_manda', 'sync_smartlead', 'analisi']).abortSignal(entro())
  if (error) guasto(error)
  return (data ?? []) as Operazione[]
}

const ADESSO = () => new Date().toISOString()
const DRE = 'Dre (Desk)'

/** Il postino parte subito, se il direttore risponde; se no al giro dei cinque minuti. */
export async function spingiPostino(): Promise<void> {
  try { await supabase.rpc('chiama_direttore', { forza: 'clara_manda' }).abortSignal(entro(8000)) } catch { /* al giro dopo */ }
}

/** Invia: la decisione passa ad «approvata» col testo com'e' adesso. Se Dre l'ha toccato, resta scritto
 *  (testo_finale) e Clara lo impara come correzione; se e' uguale, e' un «ok» su quella mossa. */
export async function approva(d: Decisione, testo: string): Promise<void> {
  const toccato = testo.trim() !== (d.testo_clara ?? '').trim()
  const { data, error } = await supabase.from('clara_decisioni')
    .update({ stato: 'approvata', testo_finale: toccato ? testo.trim() : null, approvata_il: ADESSO(), approvata_da: DRE, errore: null,
      dre_giudizio: 'ok', dre_nota: toccato ? 'testo modificato da Dre prima dell’invio' : null, dre_il: ADESSO() })
    .eq('id', d.id).in('stato', ['proposta', 'approvata']).select('id').abortSignal(entro())
  if (error) guasto(error)
  if (!data?.length) throw new Error('Questa decisione non è più da approvare (è già partita o è superata). Ricarico.')
  void spingiPostino()
}

/** No: non si manda, e Clara sa perche'. */
export async function scarta(id: string, motivo: string): Promise<void> {
  const { error } = await supabase.from('clara_decisioni')
    .update({ stato: 'scartata', dre_giudizio: 'no', dre_nota: motivo.trim() || null, dre_il: ADESSO() })
    .eq('id', id).in('stato', ['proposta', 'approvata']).abortSignal(entro())
  if (error) guasto(error)
}

/** Dre ha mandato l'invito a mano (Google non lo creava): la conferma parte lo stesso (4/11). */
export async function invitoFatto(id: string): Promise<void> {
  const { error } = await supabase.from('clara_decisioni')
    .update({ invio: { invito: 'manuale' }, stato: 'approvata', approvata_il: ADESSO(), approvata_da: DRE, errore: null, dre_giudizio: 'ok', dre_il: ADESSO() })
    .eq('id', id).in('stato', ['proposta', 'approvata']).abortSignal(entro())
  if (error) guasto(error)
}

/** L'esito di una cosa fatta da Dre (una call, un richiamo, una decisione sua). */
export async function segnaEsito(id: string, esito: string, nota?: string): Promise<void> {
  const agg: Record<string, unknown> = { esito, esito_il: ADESSO(), stato: 'fatta' }
  if (nota?.trim()) agg.dre_nota = nota.trim()
  const { error } = await supabase.from('clara_decisioni').update(agg).eq('id', id).abortSignal(entro())
  if (error) guasto(error)
}

/** Il giudizio di Dre su una decisione che non manda niente (aspetta, chiude): per imparare. */
export async function giudica(id: string, ok: boolean, nota?: string): Promise<void> {
  const { error } = await supabase.from('clara_decisioni')
    .update({ dre_giudizio: ok ? 'ok' : 'no', dre_nota: nota?.trim() || null, dre_il: ADESSO() }).eq('id', id).abortSignal(entro())
  if (error) guasto(error)
}

/** «Me ne occupo io»: la relazione passa a Dre, Clara si ferma su quel lead (le sue mosse aperte si chiudono)
 *  e il motivo resta scritto come nota. Con lascia=true gliela ridà. */
export async function prendiInMano(prospectId: string, motivo: string, lascia = false): Promise<void> {
  const { data, error } = await supabase.rpc('clara_prendi', { chi: prospectId, motivo: motivo.trim() || null, lascia }).abortSignal(entro())
  if (error) guasto(error)
  if (data && data.ok === false) throw new Error(data.perche || 'Non riesco')
}

/** Una chiamata aggiunta da Dre: azienda (o un lead scelto dalla ricerca), numero, giorno, prima nota. */
export async function aggiungiChiamata(c: { prospect_id?: string | null; azienda: string; persona?: string | null; numero?: string | null; richiamare_il?: string | null; nota?: string }): Promise<Chiamata> {
  const note = c.nota?.trim() ? [{ at: ADESSO(), testo: c.nota.trim() }] : []
  const { data, error } = await supabase.from('chiamate').insert({ prospect_id: c.prospect_id ?? null, azienda: c.azienda.trim(), persona: c.persona?.trim() || null,
    numero: c.numero?.trim() || null, richiamare_il: c.richiamare_il || null, note, creato_da: DRE }).select('id,prospect_id,azienda,persona,numero,richiamare_il,note,creato_il').abortSignal(entro()).single()
  if (error) guasto(error)
  return { id: data.id, chiamata_id: data.id, prospect_id: data.prospect_id, azienda: data.azienda, persona: data.persona, telefono: data.numero,
    richiamare_il: data.richiamare_il, note: (data.note ?? []) as NotaChiamata[], origine: 'dre', creato_il: data.creato_il }
}

/** La riga «chiamate» di un Da chiamare di Clara: nasce alla prima programmazione o nota. Torna l'id. */
async function rigaDi(c: Chiamata): Promise<string> {
  if (c.chiamata_id) return c.chiamata_id
  const { data, error } = await supabase.from('chiamate').upsert({ decisione_id: c.id, prospect_id: c.prospect_id, azienda: c.azienda, persona: c.persona, numero: c.telefono, creato_da: DRE }, { onConflict: 'decisione_id' })
    .select('id').abortSignal(entro()).single()
  if (error) guasto(error)
  return data.id
}

/** Il numero aggiunto da Dre a una chiamata senza numero (4/11): sulla chiamata e, se il lead e' in scheda, anche nella scheda. */
export async function numeroChiamata(c: Chiamata, numero: string): Promise<string> {
  const id = await rigaDi(c)
  const n = numero.trim()
  const { error } = await supabase.from('chiamate').update({ numero: n }).eq('id', id).abortSignal(entro())
  if (error) guasto(error)
  if (c.prospect_id) {
    const { error: e2 } = await supabase.from('prospects').update({ phone: n }).eq('id', c.prospect_id).abortSignal(entro())
    if (e2) guasto(e2)
  }
  return id
}

/** Una nota di Dre corretta (4/11). Clara la rilegge (clara_letta_il torna vuoto). */
export async function modificaNota(id: number, testo: string): Promise<void> {
  const { error } = await supabase.from('snella_note').update({ testo: testo.trim(), clara_letta_il: null }).eq('id', id).abortSignal(entro())
  if (error) guasto(error)
}

/** Una nota di una chiamata corretta: sulla chiamata e, se il lead e' in scheda, anche nella copia per Clara. */
export async function modificaNotaChiamata(c: Chiamata, indice: number, testo: string): Promise<NotaChiamata[]> {
  const id = await rigaDi(c)
  const vecchia = (c.note ?? [])[indice]
  const note = (c.note ?? []).map((n, i) => i === indice ? { ...n, testo: testo.trim() } : n)
  const { error } = await supabase.from('chiamate').update({ note }).eq('id', id).abortSignal(entro())
  if (error) guasto(error)
  if (c.prospect_id && vecchia) {
    try { await supabase.from('snella_note').update({ testo: `Chiamata: ${testo.trim()}`, clara_letta_il: null }).eq('prospect_id', c.prospect_id).eq('testo', `Chiamata: ${vecchia.testo}`).abortSignal(entro()) } catch { /* la copia per Clara resta vecchia */ }
  }
  return note
}

/** «WhatsApp» (4/11 sera, Dre): «se clicco vuol dire che l'ho passato e ce l'ho su WhatsApp». La chiamata resta
 *  nella lista come contatto suo; la relazione passa a Dre (Clara si ferma, niente consigli ne' solleciti); un
 *  consiglio di Clara si chiude con esito «whatsapp». Torna l'id della riga e l'ora. */
export async function suWhatsapp(c: Chiamata): Promise<{ id: string; whatsapp_il: string }> {
  const id = await rigaDi(c)
  const whatsapp_il = ADESSO()
  const { error } = await supabase.from('chiamate').update({ whatsapp_il }).eq('id', id).abortSignal(entro())
  if (error) guasto(error)
  if (c.origine === 'consiglio') { try { await segnaConsiglio(c, 'whatsapp') } catch { /* il consiglio resta aperto, la chiamata e' comunque sua */ } }
  if (c.prospect_id) {
    try { await aggiungiNota(c.prospect_id, NOTA_WHATSAPP) } catch { /* la nota resta sulla chiamata */ }
    await prendiInMano(c.prospect_id, MOTIVO_WHATSAPP)
  }
  return { id, whatsapp_il }
}

/** Quando richiamare (una data; null toglie la programmazione). */
export async function programmaChiamata(c: Chiamata, giorno: string | null): Promise<string> {
  const id = await rigaDi(c)
  const { error } = await supabase.from('chiamate').update({ richiamare_il: giorno }).eq('id', id).abortSignal(entro())
  if (error) guasto(error)
  return id
}

/** Una nota veloce sulla chiamata (si accoda). Se il lead e' in scheda, la nota va anche a Clara. */
export async function notaChiamata(c: Chiamata, testo: string): Promise<{ id: string; nota: NotaChiamata }> {
  const id = await rigaDi(c)
  const nota = { at: ADESSO(), testo: testo.trim() }
  const { error } = await supabase.from('chiamate').update({ note: [...(c.note ?? []), nota] }).eq('id', id).abortSignal(entro())
  if (error) guasto(error)
  if (c.prospect_id) { try { await aggiungiNota(c.prospect_id, `Chiamata: ${nota.testo}`) } catch { /* la nota resta sulla chiamata */ } }
  return { id, nota }
}

/** L'esito di una chiamata (fissata, non risponde, non interessato): la chiamata esce dalla lista. Per quelle di
 *  Clara si segna anche sulla decisione. «richiamare» non chiude: si programma un giorno. */
export async function esitoChiamata(c: Chiamata, esito: string, nota?: string): Promise<void> {
  const id = await rigaDi(c)
  const { error } = await supabase.from('chiamate').update({ esito, esito_il: ADESSO(), ...(nota?.trim() ? { note: [...(c.note ?? []), { at: ADESSO(), testo: nota.trim() }] } : {}) }).eq('id', id).abortSignal(entro())
  if (error) guasto(error)
  if (c.origine === 'clara') await segnaEsito(c.id, esito, nota)
  else if (c.origine === 'consiglio') { await segnaConsiglio(c, esito); if (c.prospect_id) { try { await aggiungiNota(c.prospect_id, `Chiamata di Dre: ${esito}${nota?.trim() ? `, ${nota.trim()}` : ''}`) } catch { /* niente */ } } }
  else if (c.prospect_id) { try { await aggiungiNota(c.prospect_id, `Chiamata di Dre: ${esito}${nota?.trim() ? `, ${nota.trim()}` : ''}`) } catch { /* niente */ } }
}

/** «Più avanti» su una cosa tua: resta tua, ma sparisce da Da fare fino al giorno scelto (la Coda la mostra in Prossime). */
export async function rimanda(id: string, giorno: string): Promise<void> {
  const { error } = await supabase.from('clara_decisioni').update({ entro_il: giorno, dre_nota: `rimandata da Dre al ${giorno}`, dre_il: ADESSO() }).eq('id', id).abortSignal(entro())
  if (error) guasto(error)
}

/** L'esito di un consiglio di chiamata (chiamato, non ora): resta dentro al consiglio, la decisione non cambia stato. */
export async function segnaConsiglio(d: { id: string; consiglio?: Consiglio | null }, esito: string): Promise<void> {
  const { error } = await supabase.from('clara_decisioni').update({ consiglio: { ...(d.consiglio ?? {}), esito, esito_il: ADESSO() } }).eq('id', d.id).abortSignal(entro())
  if (error) guasto(error)
}

/** Il testo cambiato senza mandare (si salva come testo_finale, la decisione resta proposta). */
export async function salvaTesto(id: string, testo: string): Promise<void> {
  const { error } = await supabase.from('clara_decisioni').update({ testo_finale: testo.trim() || null }).eq('id', id).abortSignal(entro())
  if (error) guasto(error)
}
