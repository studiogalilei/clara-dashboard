import type { Prospect } from './types'
import { eCliente, eInArrivo, eProspect, passato, quandoRisentirlo, GIORNI_SILENZIO } from './regole'

// LO STATO VIVO (Dre, 14/9): sotto ogni carta della Pipeline una riga che
// dice la verita' di oggi. O rassicura («follow-up tra 4 giorni») o dice
// chiaro che c'e' un problema («ha scritto il 12 set: da rispondere»).
// Non e' un campo: nasce dai dati che Clara aggiorna ogni ora, quindi e'
// sempre fresco e nessuno deve ricordarsi di scriverlo.

export type Tono = 'ok' | 'attesa' | 'azione' | 'spento'
export interface Stato { testo: string; tono: Tono }

interface Extra {
  bozza?: boolean          // c'e' una bozza di Clara aperta nella Posta
  domanda?: boolean        // Clara ha una domanda aperta su questa azienda
  call?: string | null     // la data della call della fase (dall'agenda)
  fase?: string            // la colonna in cui sta
}

const giorniDa = (iso: string) => Math.floor((Date.now() - new Date(iso).getTime()) / 86400e3)
const giorniA = (iso: string) => Math.ceil((new Date(iso.length === 10 ? iso + 'T12:00:00' : iso).getTime() - Date.now()) / 86400e3)
const data = (iso: string) => new Date(iso.length === 10 ? iso + 'T12:00:00' : iso).toLocaleDateString('it-IT', { day: 'numeric', month: 'short' })
const ora = (iso: string) => new Date(iso).toLocaleTimeString('it-IT', { hour: '2-digit', minute: '2-digit' })
const tra = (n: number) => n === 0 ? 'oggi' : n === 1 ? 'domani' : `tra ${n} giorni`
const FASE_NOME: Record<string, string> = { conoscitiva: 'conoscitiva', tecnica: 'tecnica', avvio: 'di avvio' }

export function statoVivo(p: Prospect, x: Extra = {}): Stato {
  const passatoA = (p as unknown as { passato_a?: string | null }).passato_a
  if (passato(p)) return { testo: `Passato a ${passatoA}`, tono: 'spento' }

  if (eCliente(p)) {
    const canone = (p as unknown as { canone?: number | null }).canone
    if (!canone) return { testo: 'Cliente: canone da mettere', tono: 'azione' }
    const contratto = (p as unknown as { contratto?: string | null }).contratto
    return { testo: `${Number(canone).toLocaleString('it-IT')} €/mese${contratto === 'prova' ? ', in prova' : contratto === 'stable' ? ', stabile' : ''}`, tono: 'ok' }
  }

  if (p.fuori && p.pipeline_stage === 'prova') {
    if (!p.prova_fine) return { testo: 'Date della prova da mettere', tono: 'azione' }
    const n = giorniA(p.prova_fine)
    if (n < 0) return { testo: `Prova finita il ${data(p.prova_fine)}: da decidere il rinnovo`, tono: 'azione' }
    if (n <= 14) return { testo: `La prova finisce ${tra(n)}: preparare il rinnovo`, tono: 'attesa' }
    return { testo: `In prova fino al ${data(p.prova_fine)}`, tono: 'ok' }
  }

  if (x.bozza) return { testo: 'Bozza pronta nella Posta di Clara', tono: 'azione' }
  if (x.domanda) return { testo: 'Clara ha una domanda nella Posta', tono: 'azione' }

  if (p.awaiting_us && p.last_reply_at) {
    const n = giorniDa(p.last_reply_at)
    return { testo: `Ha scritto il ${data(p.last_reply_at)}: da rispondere${n >= 2 ? `, ${n} giorni fa` : ''}`, tono: 'azione' }
  }

  if (x.call) {
    const n = giorniA(x.call)
    if (n >= 0) return { testo: `Call ${tra(n)}, ${data(x.call)} alle ${ora(x.call)}`, tono: 'ok' }
    return { testo: `Call fatta il ${data(x.call)}: da segnare com'è andata`, tono: 'azione' }
  }

  if (p.fuori && p.pipeline_stage && p.pipeline_stage in FASE_NOME) {
    if (p.next_action_date) {
      const n = giorniA(p.next_action_date)
      if (n >= 0) return { testo: `${p.next_action || 'Prossimo passo'} ${tra(n)}`, tono: 'ok' }
      return { testo: `${p.next_action || 'Prossimo passo'}: era il ${data(p.next_action_date)}`, tono: 'azione' }
    }
    return { testo: `Call ${FASE_NOME[p.pipeline_stage]} da fissare`, tono: 'azione' }
  }

  if (eInArrivo(p)) {
    return { testo: `Ha risposto${p.last_reply_at ? ` il ${data(p.last_reply_at)}` : ''}: analisi da mandare`, tono: 'azione' }
  }

  if (eProspect(p)) {
    if (p.classificazione === 'rinvio') {
      const q = quandoRisentirlo(p)
      if (!q) return { testo: 'Rinviato senza una data', tono: 'azione' }
      const n = giorniA(q)
      return n >= 0 ? { testo: `Risentirlo ${tra(n)}, dal ${data(q)}`, tono: 'ok' } : { testo: `Da risentire: era il ${data(q)}`, tono: 'azione' }
    }
    if (p.classificazione === 'ooo') {
      if (p.ooo_until && giorniA(p.ooo_until) >= 0) return { testo: `Fuori ufficio fino al ${data(p.ooo_until)}`, tono: 'ok' }
      return { testo: 'Rientrato dalle ferie: da risentire', tono: 'azione' }
    }
    const mandata = p.analysis_sent_at ? `Analisi mandata il ${data(p.analysis_sent_at)}` : 'Analisi mandata'
    if (p.no_followup) return { testo: `${mandata}, niente follow-up`, tono: 'spento' }
    if (p.followup_due) {
      const n = giorniA(p.followup_due)
      if (n > 0) return { testo: `${mandata}, follow-up ${tra(n)}`, tono: 'ok' }
      if (n === 0) return { testo: 'Follow-up oggi', tono: 'azione' }
      return { testo: `Follow-up in ritardo di ${-n} giorni`, tono: 'azione' }
    }
    if (p.analysis_sent_at) {
      const n = giorniDa(p.analysis_sent_at)
      return n >= GIORNI_SILENZIO ? { testo: `${mandata}, silenzio da ${n} giorni`, tono: 'attesa' } : { testo: mandata, tono: 'ok' }
    }
    return { testo: mandata, tono: 'ok' }
  }

  if (p.last_reply_at) {
    const n = giorniDa(p.last_reply_at)
    if (n >= 30) return { testo: `Fermo da ${n} giorni`, tono: 'azione' }
    if (n >= GIORNI_SILENZIO) return { testo: `Fermo da ${n} giorni`, tono: 'attesa' }
    return { testo: `Ultimo contatto il ${data(p.last_reply_at)}`, tono: 'ok' }
  }
  return { testo: 'Nessun contatto ancora', tono: 'spento' }
}

export const COLORE_STATO: Record<Tono, { pallino: string; testo: string }> = {
  ok: { pallino: 'bg-green-600', testo: 'text-tenue' },
  attesa: { pallino: 'bg-amber-500', testo: 'text-amber-800' },
  azione: { pallino: 'bg-red-600', testo: 'font-semibold text-red-800' },
  spento: { pallino: 'bg-gray-300', testo: 'text-spento' },
}
