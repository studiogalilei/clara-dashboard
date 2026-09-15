import type { Prospect } from './types'
import {
  eCliente, eInArrivo, eProspect, ePerso, vivo, passato, quandoRisentirlo,
  giorno, oggi, GIORNI_SILENZIO,
} from './regole'

// LO STATO VIVO (Dre, 14/9): sotto ogni carta della Pipeline una riga che
// dice la verita' di oggi. O rassicura («follow-up tra 4 giorni») o dice
// chiaro che c'e' un problema («ha scritto il 12 set: da rispondere»).
// Non e' un campo: nasce dai dati che Clara aggiorna ogni ora, quindi e'
// sempre fresco e nessuno deve ricordarsi di scriverlo.
// Revisione 15/9: il rosso lo prende solo chi ha una cosa da fare adesso.
// Chi e' chiuso (perso, scartato, passato) e' grigio e non chiede niente;
// quello che e' vecchio di piu' di due settimane e' giallo, non rosso.

export type Tono = 'ok' | 'attesa' | 'azione' | 'spento'
export interface Stato { testo: string; tono: Tono }

interface Extra {
  bozza?: boolean                       // c'e' una bozza di Clara aperta nella Posta
  domanda?: boolean                     // Clara ha una domanda aperta su questa azienda
  call?: string | null                  // la data della call della fase (dall'agenda)
  calls?: Record<string, string>         // tutte le sue call in agenda, per tipo
  fase?: string                          // la colonna in cui sta
}

// ── le date, in giorni di calendario ──────────────────────────────
// Prima era una differenza in ore arrotondata in su: alle 9 del mattino una
// call dello stesso pomeriggio diceva «domani» (QA Dre, 14/9). Per un
// venditore la data della call e' l'unica cosa che conta sulla carta.
const GG = 86400e3
const quando = (iso: string) => new Date(iso.length === 10 ? `${iso}T12:00:00` : iso)
const mezzogiorno = (g: string) => new Date(`${g}T12:00:00`).getTime()
const giorniA = (iso: string) => Math.round((mezzogiorno(giorno(quando(iso))) - mezzogiorno(oggi())) / GG)
const giorniDa = (iso: string) => -giorniA(iso)

const data = (iso: string) => quando(iso).toLocaleDateString('it-IT', { day: 'numeric', month: 'short' })
// in italiano l'articolo cambia davanti a 1, 8 e 11: «era l'8 set», non «il 8»
const il = (iso: string) => ([1, 8, 11].includes(quando(iso).getDate()) ? `l'${data(iso)}` : `il ${data(iso)}`)
const ora = (iso: string) => new Date(iso).toLocaleTimeString('it-IT', { hour: '2-digit', minute: '2-digit' })
const tra = (n: number) => (n === 0 ? 'oggi' : n === 1 ? 'domani' : `tra ${n} giorni`)
const FASE_NOME: Record<string, string> = { conoscitiva: 'conoscitiva', tecnica: 'tecnica', avvio: 'di avvio' }

// «da rispondere» da tre settimane non e' un'emergenza, e' un arretrato:
// giallo. Se no la bacheca diventa tutta rossa e il colore non dice piu' niente.
const invecchia = (n: number): Tono => (n > 14 ? 'attesa' : 'azione')

// la nota del prossimo passo in carta solo se e' corta: quelle lunghe
// («RISPOSTA INVIATA 5/8: call proposta mer 2/9 15:30. Se non conferma…»)
// stanno nella scheda, non su una carta da 240px (QA Dre, 14/9)
function passoBreve(t: string | null): string {
  const s = (t ?? '').trim().split(/[.;\n]/)[0].trim()
  return s.length > 0 && s.length <= 38 ? s : 'Prossimo passo'
}

export function statoVivo(p: Prospect, x: Extra = {}): Stato {
  const passatoA = (p as unknown as { passato_a?: string | null }).passato_a
  if (passato(p)) return { testo: `Passato a ${passatoA}`, tono: 'spento' }

  // ── prima i chiusi: non chiedono niente a nessuno ───────────────
  if (ePerso(p)) {
    const perche = (p.lost_reason ?? '').trim()
    return { testo: perche ? `Perso: ${perche.toLowerCase()}` : 'Perso', tono: 'spento' }
  }
  if (!vivo(p)) {
    const c = p.classificazione
    return {
      testo: c === 'fuori_target' ? 'Fuori target' : c === 'soppresso' ? 'Non vuole essere contattato' : 'Ha detto no',
      tono: 'spento',
    }
  }

  if (eCliente(p)) {
    const canone = p.canone
    if (!canone) return { testo: 'Cliente: canone da mettere', tono: 'attesa' }
    return {
      testo: `${Number(canone).toLocaleString('it-IT')} €/mese${p.contratto === 'prova' ? ', in prova' : p.contratto === 'stable' ? ', stabile' : ''}`,
      tono: 'ok',
    }
  }

  if (p.fuori && p.pipeline_stage === 'prova') {
    if (!p.prova_fine) return { testo: 'Date della prova da mettere', tono: 'azione' }
    const n = giorniA(p.prova_fine)
    if (n < 0) return { testo: `Prova finita ${il(p.prova_fine)}: da decidere il rinnovo`, tono: 'azione' }
    if (n <= 14) return { testo: `La prova finisce ${tra(n)}: preparare il rinnovo`, tono: 'attesa' }
    return { testo: `In prova fino al ${data(p.prova_fine)}`, tono: 'ok' }
  }

  if (x.bozza) return { testo: 'Bozza pronta nella Posta di Clara', tono: 'azione' }
  if (x.domanda) return { testo: 'Clara ha una domanda nella Posta', tono: 'azione' }

  if (p.awaiting_us && p.last_reply_at) {
    const n = giorniDa(p.last_reply_at)
    return {
      testo: `Ha scritto ${il(p.last_reply_at)}: da rispondere${n >= 2 ? `, ${n} giorni fa` : ''}`,
      tono: invecchia(n),
    }
  }

  // ── la prossima call vince su tutto il resto ────────────────────
  // Se domani c'e' la tecnica, la carta non deve dire «segna com'e' andata
  // la conoscitiva»: dice che domani c'e' una call (QA Dre, 14/9).
  const inAgenda = Object.entries(x.calls ?? (x.call && x.fase ? { [x.fase]: x.call } : {}))
  const prossima = inAgenda
    .map(([tipo, at]) => ({ tipo, at, n: giorniA(at) }))
    .filter((c) => c.n >= 0)
    .sort((a, b) => a.at.localeCompare(b.at))[0]
  if (prossima) {
    const nome = FASE_NOME[prossima.tipo] ? ` ${FASE_NOME[prossima.tipo]}` : ''
    return { testo: `Call${nome} ${tra(prossima.n)}, ${data(prossima.at)} alle ${ora(prossima.at)}`, tono: 'ok' }
  }

  // ── rinviati e fuori ufficio: la loro data batte tutto il resto ──
  // Stava dentro il ramo «prospect» e non si vedeva mai per i 110 che non
  // hanno ancora l'analisi (QA Dre, 14/9).
  if (p.classificazione === 'rinvio') {
    const q = quandoRisentirlo(p)
    if (!q) return { testo: 'Rinviato senza una data', tono: 'attesa' }
    const n = giorniA(q)
    return n >= 0
      ? { testo: `Risentirlo ${tra(n)}, dal ${data(q)}`, tono: 'ok' }
      : { testo: `Da risentire: era ${il(q)}`, tono: invecchia(-n) }
  }
  if (p.classificazione === 'ooo') {
    if (p.ooo_until && giorniA(p.ooo_until) >= 0) return { testo: `Fuori ufficio fino al ${data(p.ooo_until)}`, tono: 'ok' }
    const q = quandoRisentirlo(p)
    return { testo: 'Rientrato dalle ferie: da risentire', tono: q ? invecchia(-giorniA(q)) : 'azione' }
  }

  if (p.fuori && p.pipeline_stage && p.pipeline_stage in FASE_NOME) {
    if (p.next_action_date) {
      const n = giorniA(p.next_action_date)
      if (n >= 0) return { testo: `${passoBreve(p.next_action)} ${tra(n)}`, tono: 'ok' }
      return { testo: `${passoBreve(p.next_action)}: era ${il(p.next_action_date)}`, tono: invecchia(-n) }
    }
    // la call della fase e' passata e nessuno ha scritto com'e' andata
    if (x.call) return { testo: `Call fatta ${il(x.call)}: da segnare com'è andata`, tono: 'azione' }
    return { testo: `Call ${FASE_NOME[p.pipeline_stage]} da fissare`, tono: 'azione' }
  }

  if (eInArrivo(p)) {
    return { testo: `Ha risposto${p.last_reply_at ? ` ${il(p.last_reply_at)}` : ''}: analisi da mandare`, tono: 'azione' }
  }

  if (eProspect(p)) {
    const mandata = p.analysis_sent_at ? `Analisi mandata ${il(p.analysis_sent_at)}` : 'Analisi mandata'
    if (p.no_followup) return { testo: `${mandata}, niente follow-up`, tono: 'spento' }
    if (p.followup_due) {
      const n = giorniA(p.followup_due)
      if (n > 0) return { testo: `${mandata}, follow-up ${tra(n)}`, tono: 'ok' }
      if (n === 0) return { testo: 'Follow-up oggi', tono: 'azione' }
      return { testo: `Follow-up in ritardo di ${-n} giorni`, tono: invecchia(-n) }
    }
    if (p.analysis_sent_at) {
      const n = giorniDa(p.analysis_sent_at)
      return n >= GIORNI_SILENZIO ? { testo: `${mandata}, silenzio da ${n} giorni`, tono: 'attesa' } : { testo: mandata, tono: 'ok' }
    }
    return { testo: mandata, tono: 'ok' }
  }

  if (p.last_reply_at) {
    const n = giorniDa(p.last_reply_at)
    if (n >= GIORNI_SILENZIO) return { testo: `Fermo da ${n} giorni`, tono: 'attesa' }
    return { testo: `Ultimo contatto ${il(p.last_reply_at)}`, tono: 'ok' }
  }
  return { testo: 'Nessun contatto ancora', tono: 'spento' }
}

export const COLORE_STATO: Record<Tono, { pallino: string; testo: string }> = {
  ok: { pallino: 'bg-green-600', testo: 'text-tenue' },
  attesa: { pallino: 'bg-amber-500', testo: 'text-amber-800' },
  azione: { pallino: 'bg-red-600', testo: 'font-semibold text-red-800' },
  spento: { pallino: 'bg-gray-300', testo: 'text-spento' },
}
