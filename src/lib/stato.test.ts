// LO STATO VIVO, messo alla prova.
//
// Perche' proprio questo: e' la riga che Dre legge sotto ogni carta per
// decidere se stare tranquillo o preoccuparsi. Il 14 settembre diceva «da
// rispondere» in rosso a 78 aziende che avevano gia' detto no, «analisi da
// mandare» a 45 che avevano chiesto di essere risentite piu' avanti, e alle
// 9 del mattino chiamava «domani» una call dello stesso pomeriggio.
//
// Regola: se un caso qui sotto smette di passare, non si aggiusta il test.
// Si guarda cosa sta dicendo la carta a chi vende.

import { describe, it, expect } from 'vitest'
import { statoVivo } from './stato'
import type { Prospect } from './types'

const oggi = new Date()
const giorno = (n: number) => {
  const d = new Date(oggi)
  d.setDate(d.getDate() + n)
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
}
const alle = (n: number, ora: string) => `${giorno(n)}T${ora}:00`

const p = (x: Partial<Prospect> = {}): Prospect => ({
  id: 'x', sg_id: 1, email: 'a@b.it', name: null, role: null, phone: null, linkedin: null,
  company: 'Prova', website: null, sector: null, city: null, descrizione: null, socials: {},
  owner_name: null, campaign: null, stage: 'risposto', first_reply_at: null, last_reply_at: null,
  analysis_sent: false, analysis_sent_at: null, analysis_pdf: null, next_action: null,
  next_action_date: null, no_followup: false, deal_value: null, lost_reason: null, notes: null,
  enriched: {}, updated_at: giorno(0), awaiting_us: false, classificazione: null, followup_due: null,
  ooo_until: null, prova_inizio: null, prova_fine: null, fuori: false, fuori_at: null,
  pipeline_stage: null, fuori_binario: null, market: null, contratto: null, canone: null, ...x,
} as Prospect)

describe('chi e\' chiuso non chiede niente', () => {
  it('un perso e\' spento, col motivo, anche se aspettava una risposta', () => {
    const s = statoVivo(p({ stage: 'perso', awaiting_us: true, last_reply_at: giorno(-40), lost_reason: 'Prezzo' }))
    expect(s.tono).toBe('spento')
    expect(s.testo).toBe('Perso: prezzo')
  })
  it('un negativo con awaiting_us non dice «da rispondere» in rosso', () => {
    const s = statoVivo(p({ classificazione: 'negativo', awaiting_us: true, last_reply_at: giorno(-3) }))
    expect(s.tono).toBe('spento')
    expect(s.testo).toBe('Ha detto no')
  })
})

describe('le date sono giorni di calendario, non ore', () => {
  it('una call di oggi pomeriggio e\' oggi anche se la guardi la mattina', () => {
    const s = statoVivo(p({ fuori: true, pipeline_stage: 'conoscitiva' }), { calls: { conoscitiva: alle(0, '23:30') } })
    expect(s.testo).toContain('Call conoscitiva oggi')
  })
  it('domani e\' domani', () => {
    const s = statoVivo(p({ fuori: true, pipeline_stage: 'conoscitiva' }), { calls: { conoscitiva: alle(1, '09:00') } })
    expect(s.testo).toContain('domani')
  })
  it('l\'articolo giusto davanti all\'8', () => {
    const d = new Date(oggi); d.setDate(8); d.setMonth(d.getMonth() - 1)
    const iso = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-08`
    const s = statoVivo(p({ fuori: true, pipeline_stage: 'tecnica', next_action: 'Sollecito', next_action_date: iso }))
    expect(s.testo).toContain("era l'8")
  })
})

describe('la prossima call vince', () => {
  it('con la tecnica fra due giorni non si chiede di segnare la conoscitiva', () => {
    const s = statoVivo(p({ fuori: true, pipeline_stage: 'conoscitiva' }), {
      fase: 'conoscitiva',
      call: alle(-12, '15:00'),
      calls: { conoscitiva: alle(-12, '15:00'), tecnica: alle(2, '13:30') },
    })
    expect(s.tono).toBe('ok')
    expect(s.testo).toContain('Call tecnica tra 2 giorni')
  })
  it('senza call future si chiede com\'e\' andata', () => {
    const s = statoVivo(p({ fuori: true, pipeline_stage: 'conoscitiva' }), {
      fase: 'conoscitiva', call: alle(-3, '15:00'), calls: { conoscitiva: alle(-3, '15:00') },
    })
    expect(s.tono).toBe('azione')
    expect(s.testo).toContain('da segnare')
  })
})

describe('rinvii e fuori ufficio, anche senza analisi', () => {
  it('un rinvio senza data non e\' «analisi da mandare»', () => {
    const s = statoVivo(p({ classificazione: 'rinvio', analysis_sent: false, last_reply_at: giorno(-70) }))
    expect(s.testo).toBe('Rinviato senza una data')
  })
  it('un rinvio con la data passata chiede di risentirlo', () => {
    const s = statoVivo(p({ classificazione: 'rinvio', analysis_sent: false, next_action_date: giorno(-3) }))
    expect(s.tono).toBe('azione')
    expect(s.testo).toContain('Da risentire')
  })
  it('un fuori ufficio ancora in corso e\' tranquillo', () => {
    const s = statoVivo(p({ classificazione: 'ooo', ooo_until: giorno(5) }))
    expect(s.tono).toBe('ok')
  })
})

describe('il rosso lo prende solo chi ha una cosa da fare adesso', () => {
  it('ha scritto ieri: rosso', () => {
    expect(statoVivo(p({ awaiting_us: true, last_reply_at: giorno(-1) })).tono).toBe('azione')
  })
  it('ha scritto due mesi fa: e\' arretrato, giallo', () => {
    expect(statoVivo(p({ awaiting_us: true, last_reply_at: giorno(-60) })).tono).toBe('attesa')
  })
})

describe('la nota lunga resta nella scheda', () => {
  it('in carta ci va «Prossimo passo», non tre righe di appunti', () => {
    const lunga = 'RISPOSTA INVIATA 5/8: call proposta mer 2/9 15:30, se non conferma sollecito'
    const s = statoVivo(p({ fuori: true, pipeline_stage: 'tecnica', next_action: lunga, next_action_date: giorno(3) }))
    expect(s.testo).toBe('Prossimo passo tra 3 giorni')
  })
  it('una nota corta si legge volentieri', () => {
    const s = statoVivo(p({ fuori: true, pipeline_stage: 'tecnica', next_action: 'Mandare la proposta', next_action_date: giorno(1) }))
    expect(s.testo).toBe('Mandare la proposta domani')
  })
})
