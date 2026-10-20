// La versione snella: le regole di chi chiamare, con dati finti.
import { describe, expect, it } from 'vitest'
import type { Decisione, Domanda, RigaLead } from './dati'
import {
  FASI, cerca, chiamateInRitardo, contaStati, eSeguito, faseDi, giornoRoma, listaDaChiamare, nomeGiorno, perAzienda, piuGiorni, primaRiga, quando,
  infoStato, nomeStato, prossimoMessaggio, scrittoDopo, sitoBreve, sitoCliccabile, spiegaDomanda, statoDi, tasso, titoloDomanda, tonoStato,
  type LeadPerProssimo, type PropostaLead,
} from './regole'
import { GRUPPI, INFO_STATI, STATI } from './dati'
import statiJson from './stati.json'

const ORA = new Date('2026-10-19T08:00:00Z')          // lunedi' 19/10, le 10 a Roma

function riga(id: string, cambia: Partial<RigaLead> = {}): RigaLead {
  return { prospect_id: id, azienda: `Azienda ${id}`, persona: `Persona ${id}`, email: `${id}@esempio.it`, stato: 'Da chiamare',
           ultima_risposta: '2026-10-18T09:00:00Z', frase: 'Ci sentiamo?', da_chiamare: true, perche_chiamare: 'Ha chiesto una chiamata', ...cambia }
}
function dec(id: string, cambia: Partial<Decisione> = {}): Decisione {
  return { prospect_id: id, stato: null, prossima_mossa: null, prossima_il: null, chiamata: null, chiamata_il: null,
           richiamare_il: null, tentativi: 0, ...cambia }
}

describe('chi chiamare', () => {
  it('chi vuole sentirti c\'e\', chi no non c\'e\'', () => {
    const l = listaDaChiamare([riga('a'), riga('b', { da_chiamare: false })], new Map(), ORA)
    expect(l.map((x) => x.riga.prospect_id)).toEqual(['a'])
  })
  it('chiamato dopo la sua risposta esce; una risposta nuova dopo la chiamata lo riporta', () => {
    const d = new Map([['a', dec('a', { chiamata: 'chiamato', chiamata_il: '2026-10-18T10:00:00Z' })]])
    expect(listaDaChiamare([riga('a')], d, ORA)).toHaveLength(0)
    expect(listaDaChiamare([riga('a', { ultima_risposta: '2026-10-18T11:00:00Z' })], d, ORA)).toHaveLength(1)
  })
  it('richiamare: sparisce fino al giorno scelto, poi torna in cima', () => {
    const domani = dec('a', { chiamata: 'richiamare', chiamata_il: '2026-10-18T10:00:00Z', richiamare_il: '2026-10-20' })
    expect(listaDaChiamare([riga('a'), riga('b')], new Map([['a', domani]]), ORA).map((x) => x.riga.prospect_id)).toEqual(['b'])
    const oggi = { ...domani, richiamare_il: '2026-10-19' }
    const l = listaDaChiamare([riga('b'), riga('a', { da_chiamare: false })], new Map([['a', oggi]]), ORA)
    expect(l.map((x) => [x.riga.prospect_id, x.motivo])).toEqual([['a', 'richiamare'], ['b', 'chiamare']])
  })
  it('non risponde: resta, ma in fondo', () => {
    const d = new Map([['a', dec('a', { chiamata: 'non_risponde', chiamata_il: '2026-10-18T10:00:00Z', tentativi: 1 })]])
    const l = listaDaChiamare([riga('a', { ultima_risposta: '2026-10-17T09:00:00Z' }), riga('b')], d, ORA)
    expect(l.map((x) => [x.riga.prospect_id, x.nonRisponde])).toEqual([['b', false], ['a', true]])
  })
  it('chi Dre ha messo in Non interessato o in Call fissata non si chiama; oltre 21 giorni neanche', () => {
    const d = new Map([['a', dec('a', { stato: 'Non interessato' })], ['b', dec('b', { stato: 'Call fissata' })]])
    const vecchio = riga('c', { ultima_risposta: '2026-09-20T09:00:00Z' })
    expect(listaDaChiamare([riga('a'), riga('b'), vecchio], d, ORA)).toHaveLength(0)
  })
  it('in ritardo: chi aspetta da piu\' di un giorno senza un tentativo', () => {
    const l = listaDaChiamare([riga('a', { ultima_risposta: '2026-10-17T07:00:00Z' }), riga('b')], new Map(), ORA)
    expect(chiamateInRitardo(l, ORA).map((x) => x.riga.prospect_id)).toEqual(['a'])
  })
})

describe('lista e ricerca', () => {
  it('lo stato deciso da Dre vince su quello calcolato', () => {
    const m = contaStati([riga('a'), riga('b')], new Map([['a', dec('a', { stato: 'Analisi inviata' })]]))
    expect(m.get('Analisi inviata')).toBe(1)
    expect(m.get('Da chiamare')).toBe(1)
  })
  it('cerca per azienda o persona, senza accenti', () => {
    const r = [riga('a', { azienda: 'Caffè Rossi' }), riga('b', { persona: 'Mario Verdi' })]
    expect(cerca(r, 'caffe').map((x) => x.prospect_id)).toEqual(['a'])
    expect(cerca(r, 'mario ver').map((x) => x.prospect_id)).toEqual(['b'])
    expect(cerca(r, '  ')).toHaveLength(2)
  })
})

describe('date e numeri', () => {
  it('il giorno e\' quello di Roma, anche a mezzanotte UTC', () => {
    expect(giornoRoma(new Date('2026-10-18T22:30:00Z'))).toBe('2026-10-19')
    expect(piuGiorni('2026-10-31', 1)).toBe('2026-11-01')
  })
  it('quando, detto come una persona', () => {
    expect(quando('2026-10-19T07:31:00Z', ORA)).toBe('oggi alle 09:31')
    expect(quando('2026-10-18T16:02:00Z', ORA)).toBe('ieri alle 18:02')
    expect(nomeGiorno('2026-10-20', ORA)).toBe('Domani')
  })
  it('il tasso non si inventa', () => {
    expect(tasso(120, 1606)).toBe('7,5%')
    expect(tasso(null, 1606)).toBeNull()
    expect(tasso(3, 0)).toBeNull()
  })
  it('le domande della Posta: una riga per azienda, titolo senza codici', () => {
    const d: Domanda[] = [
      { id: 1, tipo: 'umano', titolo: 'Da guardare tu: Azienda A, INT-09', perche: null, at: '2026-10-19T07:00:00Z', prospect_id: 'a' },
      { id: 2, tipo: 'umano', titolo: 'Da guardare tu: Azienda A, INT-07', perche: null, at: '2026-10-19T07:10:00Z', prospect_id: 'a' },
      { id: 3, tipo: 'risposta', titolo: 'Bozza per Azienda B, INT-01', perche: null, at: '2026-10-18T07:00:00Z', prospect_id: 'b' },
    ]
    const g = perAzienda(d)
    expect(g.map((x) => [x.ultima.id, x.quante])).toEqual([[2, 2], [3, 1]])
    expect(titoloDomanda(g[0].ultima.titolo)).toBe('Azienda A')
    expect(titoloDomanda(g[1].ultima.titolo)).toBe('Azienda B')
  })
  it('la Posta detta senza parole interne: niente INT, FOLLOW UP doppio, seconda testa, CANCELLO', () => {
    expect(titoloDomanda('Follow up 1: Azienda C, FOLLOW UP 1')).toBe('Azienda C')
    expect(titoloDomanda('Da guardare tu: Azienda D, INT-08 ')).toBe('Azienda D')
    expect(eSeguito({ titolo: 'Azienda C, FOLLOW UP 1', intento: 'FOLLOW UP 1' })).toBe(true)
    expect(eSeguito({ titolo: 'Bozza per Azienda E, INT-01', intento: 'INT-01' })).toBe(false)
    expect(spiegaDomanda("si': la seconda testa dice INCOERENTE: non risponde alla domanda")).toBe('Il controllo ha fermato la bozza: non risponde alla domanda')
    expect(spiegaDomanda("sì: è un'autorisposta, CANCELLO: regola 3h")).toBe("È un'autorisposta")
    expect(spiegaDomanda('il template di Dre parola per parola (INT-01); va bene')).toBe('Il template di Dre parola per parola; va bene')
    expect(spiegaDomanda(null)).toBe('')
  })
  it('cosa gli abbiamo scritto dopo la sua risposta', () => {
    const filo = [
      { at: '2026-10-12T14:37:00Z', chi: 'lui' as const, testo: 'Possiamo sentirci mercoledì?' },
      { at: '2026-10-15T15:05:00Z', chi: 'noi' as const, testo: 'Buongiorno Andrea,\nmi scusi: mercoledì è passato.\nA presto' },
    ]
    const d = scrittoDopo(filo, '2026-10-12T14:37:00Z')
    expect(d?.at).toBe('2026-10-15T15:05:00Z')
    expect(primaRiga(d!.testo)).toBe('mi scusi: mercoledì è passato.')
    expect(scrittoDopo(filo, '2026-10-16T00:00:00Z')).toBeNull()
  })
})

describe('i 12 stati (Dre, 19/10)', () => {
  it('dodici, in quattro gruppi, in quest\'ordine, nient\'altro', () => {
    expect(STATI).toEqual(['Da chiamare', 'Da rispondere', 'Analisi inviata', 'Call fissata', 'Proposta inviata', 'Cliente acquisito',
      'Da ricontattare', 'Assente', 'Nessuna risposta', 'Non interessato', 'Perso', 'Non contattare'])
    expect(GRUPPI).toEqual(['Da gestire oggi', 'Opportunità', 'In attesa', 'Chiusi'])
  })
  it('ogni stato ha un responsabile e una prossima azione di default', () => {
    for (const s of INFO_STATI) {
      expect(['Dramane', 'Claude']).toContain(s.responsabile)
      expect(s.azione.trim().length).toBeGreaterThan(0)
      expect(GRUPPI).toContain(s.gruppo)
    }
    expect(infoStato('Da chiamare')?.responsabile).toBe('Dramane')
    expect(infoStato('Da rispondere')?.responsabile).toBe('Claude')
  })
  it('i nomi vecchi passano ai nuovi, mai si mostrano', () => {
    expect(nomeStato('No grazie')).toBe('Non interessato')
    expect(nomeStato('Non scrivere più')).toBe('Non contattare')
    expect(nomeStato('Fuori ufficio')).toBe('Assente')
    expect(nomeStato('Conoscitiva')).toBe('Call fissata')
    expect(nomeStato('Analisi mandata')).toBe('Analisi inviata')
    expect(nomeStato('Vuole sentirti')).toBe('Da chiamare')
    expect(nomeStato('Follow-up')).toBe('Analisi inviata')
    expect(nomeStato('Da riprendere')).toBe('Da ricontattare')
    expect(nomeStato('In conversazione')).toBe('Da rispondere')
    for (const v of Object.values(statiJson.dai_vecchi)) expect(STATI).toContain(v)
    expect(statoDi({ stato: 'Vuole sentirti' })).toBe('Da chiamare')
    expect(statoDi({ stato: 'Nel Workspace' })).toBe('Da rispondere')
  })
})

describe('il colore degli stati', () => {
  it('verde il si\', rosso il no, ambra da rispondere, blu quello che seguiamo noi, viola le opportunita\'', () => {
    expect(tonoStato('Da chiamare')).toBe('ok')
    expect(tonoStato('Cliente acquisito')).toBe('ok')
    expect(tonoStato('Da rispondere')).toBe('attesa')
    expect(tonoStato('Analisi inviata')).toBe('noi')
    expect(tonoStato('Call fissata')).toBe('opp')
    expect(tonoStato('Proposta inviata')).toBe('opp')
    expect(tonoStato('Da ricontattare')).toBe('giallo')
    expect(tonoStato('Non interessato')).toBe('no')
    expect(tonoStato('Perso')).toBe('no')
    expect(tonoStato('Non contattare')).toBe('stop')
  })
  it('grigi: assente, nessuna risposta, e uno stato che non conosce', () => {
    expect(tonoStato('Assente')).toBe('neutro')
    expect(tonoStato('Nessuna risposta')).toBe('neutro')
    expect(tonoStato('Uno stato nuovo')).toBe('neutro')
  })
})

describe('le 8 fasi del foglio della pipeline (19/10)', () => {
  it('sono otto, nell\'ordine del design, e ogni stato ha la sua fase o il suo conteggio', () => {
    expect(FASI.map((f) => f.nome)).toEqual(['Analisi in preparazione', 'Analisi inviata', 'Conversazione',
      'Chiamata conoscitiva', 'Chiamata tecnica', 'Chiamata di avvio', 'Periodo di prova', 'Cliente'])
    for (const s of STATI) expect(faseDi(s)).not.toBeNull()
  })
  it('quella del foglio vince su quella di partenza dello stato', () => {
    expect(faseDi('Da rispondere')).toEqual({ nome: 'Analisi in preparazione', dentro: true })
    expect(faseDi('Da rispondere', 'Conversazione')).toEqual({ nome: 'Conversazione', dentro: true })
    expect(faseDi('Call fissata', 'Chiamata tecnica')).toEqual({ nome: 'Chiamata tecnica', dentro: true })
    expect(faseDi('Assente')).toEqual({ nome: 'Fuori ufficio', dentro: false })
    expect(faseDi('Analisi inviata', 'Persi')).toEqual({ nome: 'Persi', dentro: false })
    expect(faseDi('Vuole sentirti')).toEqual({ nome: 'Analisi in preparazione', dentro: true })   // un nome vecchio si traduce
    expect(faseDi(null)).toBeNull()
  })
})

describe('la scheda pulita (20/10): il prossimo messaggio di Clara e il sito', () => {
  const ADESSO = new Date('2026-10-20T08:00:00Z')        // martedi' 20/10, le 10 a Roma
  const lead: LeadPerProssimo = {
    analysis_sent_at: '2026-10-19T09:00:00Z', last_reply_at: '2026-10-18T09:00:00Z', no_followup: false, fuori: false,
    stage: 'risposto', classificazione: 'positivo', coda: null, awaiting_us: false,
  }
  const proposta = (cambia: Partial<PropostaLead> = {}): PropostaLead => ({
    id: 1, tipo: 'risposta', stato: 'approvata', at: '2026-10-20T07:00:00Z', bozza: 'Salve,\n\ntorno sull\'analisi.', template: 'FOLLOW UP 1', risposta: null, ...cambia,
  })

  it('una proposta approvata: parte a minuti, col testo esatto, e si sa cosa chiudere', () => {
    const p = prossimoMessaggio(lead, [proposta()], null, [], ADESSO)
    expect(p).toMatchObject({ testo: 'Salve,\n\ntorno sull\'analisi.', tipo: 'Primo follow-up', da_chiudere: [1] })
    expect(p?.quando).toMatch(/parte a minuti/i)
  })
  it('l\'approvata vince sull\'aperta; chiuse e altri tipi non contano', () => {
    const p = prossimoMessaggio(lead, [proposta({ id: 2, stato: 'aperta', template: null, bozza: 'Altro' }), proposta({ id: 3 }),
      proposta({ id: 4, stato: 'fatta' }), proposta({ id: 5, stato: 'aperta', bozza: null, tipo: 'umano' }),
      proposta({ id: 6, stato: 'aperta', tipo: 'avanza' })], null, [], ADESSO)
    expect(p?.da_chiudere).toEqual([2, 3, 5])
    expect(p?.testo).toBe('Salve,\n\ntorno sull\'analisi.')
  })
  it('una proposta aperta: scritta, non ancora partita', () => {
    expect(prossimoMessaggio(lead, [proposta({ stato: 'aperta', template: null })], null, [], ADESSO))
      .toMatchObject({ tipo: 'Risposta', quando: 'Scritto, non ancora partito' })
  })
  it('senza proposte e senza analisi: niente', () => {
    expect(prossimoMessaggio({ ...lead, analysis_sent_at: null }, [], null, [], ADESSO)).toBeNull()
  })
  it('il calendario dei follow-up (followup.py) dice il giorno; il testo lo scrive Clara quel giorno', () => {
    const p = prossimoMessaggio(lead, [], { gruppo: 'MINI FOLLOW UP', il: '2026-10-22' }, [], ADESSO)
    expect(p).toMatchObject({ giorno: '2026-10-22', testo: null, tipo: 'Mini follow-up', da_chiudere: [] })
    expect(p?.quando).toMatch(/22/)
  })
  it('senza calendario: come followup.py, analisi + 5 giorni se non ha piu\' scritto', () => {
    expect(prossimoMessaggio(lead, [], null, [], ADESSO)).toMatchObject({ giorno: '2026-10-24', tipo: 'Primo follow-up' })
    // in ritardo: oggi, non nel passato
    expect(prossimoMessaggio({ ...lead, analysis_sent_at: '2026-10-01T09:00:00Z', last_reply_at: '2026-09-30T09:00:00Z' }, [], null, [], ADESSO)?.giorno).toBe('2026-10-20')
  })
  it('niente follow-up se ha scritto dopo l\'analisi, se e\' fermato, fuori, perso, o l\'ha gia\' avuto', () => {
    expect(prossimoMessaggio({ ...lead, last_reply_at: '2026-10-19T10:00:00Z' }, [], null, [], ADESSO)).toBeNull()
    expect(prossimoMessaggio({ ...lead, no_followup: true }, [], null, [], ADESSO)).toBeNull()
    expect(prossimoMessaggio({ ...lead, fuori: true }, [], null, [], ADESSO)).toBeNull()
    expect(prossimoMessaggio({ ...lead, stage: 'perso' }, [], null, [], ADESSO)).toBeNull()
    expect(prossimoMessaggio({ ...lead, classificazione: 'negativo' }, [], null, [], ADESSO)).toBeNull()
    expect(prossimoMessaggio(lead, [proposta({ stato: 'fatta' })], null, [], ADESSO)).toBeNull()
    // una nostra mail partita dopo il giorno dell'analisi e' gia' un follow-up
    expect(prossimoMessaggio(lead, [], null, ['2026-10-21T09:00:00Z'], ADESSO)).toBeNull()
    // un follow-up rifiutato «a mano» da Dre conta come avuto; chiuso dagli script no
    expect(prossimoMessaggio(lead, [proposta({ stato: 'no', risposta: 'NO: non serve' })], null, [], ADESSO)).toBeNull()
    expect(prossimoMessaggio(lead, [proposta({ stato: 'no', risposta: 'chiusa da sola' })], null, [], ADESSO)).not.toBeNull()
  })
  it('fermato da Dre: il calendario non conta piu\'', () => {
    expect(prossimoMessaggio({ ...lead, no_followup: true }, [], { gruppo: 'FOLLOW UP 1', il: '2026-10-22' }, [], ADESSO)).toBeNull()
  })

  it('il sito si apre sempre, con o senza https', () => {
    expect(sitoCliccabile('esempio.it')).toBe('https://esempio.it')
    expect(sitoCliccabile(' www.esempio.it/ ')).toBe('https://www.esempio.it/')
    expect(sitoCliccabile('http://esempio.it')).toBe('http://esempio.it')
    expect(sitoCliccabile('HTTPS://Esempio.it')).toBe('HTTPS://Esempio.it')
    expect(sitoCliccabile('')).toBeNull()
    expect(sitoCliccabile(null)).toBeNull()
    expect(sitoCliccabile('non un sito')).toBeNull()
    expect(sitoBreve('https://www.esempio.it/')).toBe('esempio.it')
    expect(sitoBreve('https://esempio.it/chi-siamo')).toBe('esempio.it/chi-siamo')
  })
})
