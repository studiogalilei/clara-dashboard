import { describe, expect, it } from 'vitest'
import { agendaPulita, destinatari, filtra, gruppoDi, priorita, statoBreve, telefonoDa } from './regole'
import type { Decisione } from './dati'

const base = (x: Partial<Decisione>): Decisione => ({
  id: 'd1', prospect_id: 'p1', risposta_il: '2026-11-03T10:00:00Z', mossa: 'reply', owner: 'Clara', entro_il: null,
  testo: 'ciao', testo_clara: 'ciao', perche: null, prove: [], richiamo: null, segnali: [], giudice: null, stato: 'proposta',
  lead_testo: null, approvata_il: null, inviata_il: null, verificata_il: null, errore: null, esito: null, esito_il: null,
  creato_il: '2026-11-03T10:01:00Z', versione: 'v', dollari: 0.04, dre_giudizio: null, azienda: 'Rossi Srl', persona: 'Mario Rossi',
  ruolo: null, email: 'm@rossi.it', citta: 'Pesaro', settore: null, telefono: null, sito: null, analisi_pdf: false, analisi_mandata: false,
  fase: null, classe: null, ultima_risposta: null, prossima_call: null, ...x,
})
const adesso = new Date('2026-11-03T12:00:00Z')

describe('il desk: la coda', () => {
  it('una call da confermare viene prima di un «aspetta», e la freschezza conta', () => {
    expect(priorita(base({ mossa: 'book_meeting' }), adesso)).toBeGreaterThan(priorita(base({ mossa: 'wait' }), adesso))
    const vecchia = base({ mossa: 'reply', risposta_il: '2026-10-20T10:00:00Z' })
    expect(priorita(base({ mossa: 'reply' }), adesso)).toBeGreaterThan(priorita(vecchia, adesso))
  })
  it('i gruppi seguono lo stato prima della mossa', () => {
    expect(gruppoDi(base({ mossa: 'close' }))).toBe('chiuse')
    expect(gruppoDi(base({ mossa: 'wait' }))).toBe('attesa')
    expect(gruppoDi(base({ mossa: 'close', stato: 'inviata' }))).toBe('fatte')
    expect(gruppoDi(base({ mossa: 'send_analysis', stato: 'approvata' }))).toBe('corso')
    expect(gruppoDi(base({ mossa: 'send_analysis', stato: 'superata' }))).toBe('chiuse')
  })
  it('«Da inviare» mostra solo le mosse che scrivono, «Decidi tu» solo le escalation, e la ricerca filtra', () => {
    const ds = [base({ id: 'a', mossa: 'send_analysis' }), base({ id: 'b', mossa: 'escalate', azienda: 'Bianchi' }), base({ id: 'c', mossa: 'callback' })]
    expect(filtra(ds, 'inviare').map((d) => d.id)).toEqual(['a'])
    expect(filtra(ds, 'tue').map((d) => d.id)).toEqual(['b'])
    expect(filtra(ds, 'call').map((d) => d.id)).toEqual(['c'])
    expect(filtra(ds, 'tutte', 'bianchi').map((d) => d.id)).toEqual(['b'])
  })
  it('lo stato in una parola dice quando e\' ferma e perche\'', () => {
    expect(statoBreve(base({ errore: 'aspetta l’analisi' })).tono).toBe('no')
    expect(statoBreve(base({ stato: 'inviata', verificata_il: '2026-11-03T11:00:00Z' })).testo).toBe('Inviata e verificata')
  })
  it('la riga «A: … Cc: …» di Clara si separa dal corpo', () => {
    const d = destinatari('A: marketing@x.it — Cc: capo@x.it\nOggetto: Analisi\n\nBuongiorno,\ntesto')
    expect(d).toEqual({ a: 'marketing@x.it', cc: 'capo@x.it', oggetto: 'Analisi', corpo: 'Buongiorno,\ntesto' })
    expect(destinatari('Buongiorno').corpo).toBe('Buongiorno')
  })

  it('il numero si tira fuori dal testo e l\'agenda perde i doppioni e gli impegni interni', () => {
    expect(telefonoDa('335 838 3593 (Matteo Lari, Direzione Commerciale)')).toBe('335 838 3593')
    expect(telefonoDa('+39 347 699 3922')).toBe('+39 347 699 3922')
    expect(telefonoDa('nessun numero')).toBeNull()
    const a = agendaPulita([
      { at: '2026-11-04T10:00:00Z', titolo: 'Eco', tipo: 'tecnica', prospect_id: 'p' },
      { at: '2026-11-04T10:00:00Z', titolo: 'Eco', tipo: 'tecnica', prospect_id: 'p' },
      { at: '2026-11-06T16:30:00Z', titolo: 'Allineamento', tipo: 'altro', prospect_id: null },
    ])
    expect(a).toHaveLength(1)
  })
})
