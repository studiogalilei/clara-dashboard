// Le regole di casa, messe alla prova.
//
// Perche' proprio queste e non il resto: regole.ts e' l'unico file dove un
// errore si vede in QUATTRO schermate insieme. Il 4 settembre «cliente» era
// scritto in quattro modi e il ricorrente mensile usciva con tre cifre
// diverse; «prospect» ne aveva tre e la home ne contava piu' della bacheca.
// Quei bug non li prende il compilatore, perche' sintatticamente erano
// perfetti: li prende solo qualcuno che chiede «e per un cliente vecchio
// stile cosa dici?».
//
// Regola: se un caso qui sotto smette di passare, non si aggiusta il test.
// Si guarda quale schermata stava mentendo.

import { describe, it, expect } from 'vitest'
import {
  vivo, eCliente, ePerso, chiuso, passato, eProspect, eInArrivo, inPipeline,
  giorno, pulisci, MORTI,
} from './regole'

// il minimo che serve alle regole per rispondere
type Tipo = Parameters<typeof eProspect>[0]
const p = (x: Partial<Tipo> = {}): Tipo => ({
  fuori: false, stage: 'risposto', pipeline_stage: null, classificazione: null, ...x,
} as Tipo)

describe('chi e\' vivo', () => {
  it('un morto dichiarato non si conta e non si ricontatta', () => {
    for (const m of MORTI) expect(vivo(p({ classificazione: m as Tipo['classificazione'] }))).toBe(false)
  })
  it('chi non ha ancora una classificazione e\' vivo', () => {
    expect(vivo(p({ classificazione: null }))).toBe(true)
  })
})

describe('cliente: le due strade', () => {
  it('quello arrivato dalla pipeline', () => {
    expect(eCliente(p({ fuori: true, pipeline_stage: 'cliente' }))).toBe(true)
  })
  it('quello vecchio stile, che in pipeline non c\'e\' mai entrato', () => {
    expect(eCliente(p({ fuori: false, stage: 'cliente' }))).toBe(true)
  })
  it('un prospect in pipeline non e\' un cliente', () => {
    expect(eCliente(p({ fuori: true, pipeline_stage: 'tecnica' }))).toBe(false)
  })
  it('«cliente» scritto nella colonna sbagliata non conta', () => {
    // era il bug del filtro Cliente in Tutti: chiedeva stage, che la
    // pipeline non scrive mai
    expect(eCliente(p({ fuori: true, stage: 'cliente', pipeline_stage: 'tecnica' }))).toBe(false)
  })
})

describe('perso, e la storia finita', () => {
  it('perso dalle due strade', () => {
    expect(ePerso(p({ fuori: true, pipeline_stage: 'perso' }))).toBe(true)
    expect(ePerso(p({ fuori: false, stage: 'perso' }))).toBe(true)
  })
  it('chiuso vale per cliente, perso e morto dichiarato', () => {
    expect(chiuso(p({ fuori: true, pipeline_stage: 'cliente' }))).toBe(true)
    expect(chiuso(p({ stage: 'perso' }))).toBe(true)
    expect(chiuso(p({ classificazione: 'negativo' }))).toBe(true)
    expect(chiuso(p())).toBe(false)
  })
})

describe('prospect: la stessa risposta in tutte le schermate', () => {
  // IN ARRIVO = tocca a te (Dre, 25/9: «la prassi e' che sia vuota»): chi ha scritto per
  // ultimo aspetta la tua risposta; tutto il resto di chi ha risposto sta in Lead
  it('chi ha scritto per ultimo aspetta te: e\' in arrivo, non in Lead', () => {
    expect(eInArrivo(p({ stage: 'risposto', awaiting_us: true }))).toBe(true)
    expect(eProspect(p({ stage: 'risposto', awaiting_us: true }))).toBe(false)
    expect(eInArrivo(p({ stage: 'risposto', awaiting_us: true, classificazione: 'negativo' }))).toBe(false)
  })
  it('chi ha risposto e non aspetta niente da te sta in Lead, con o senza analisi', () => {
    expect(eProspect(p({ stage: 'risposto', awaiting_us: false, analysis_sent: true }))).toBe(true)
    expect(eProspect(p({ stage: 'risposto', awaiting_us: false, analysis_sent: false }))).toBe(true)
    expect(eInArrivo(p({ stage: 'risposto', awaiting_us: false, analysis_sent: false }))).toBe(false)
  })
  it('chi e\' entrato in pipeline non e\' piu\' un prospect', () => {
    expect(eProspect(p({ fuori: true, pipeline_stage: 'conoscitiva' }))).toBe(false)
  })
  it('la terza porta: passato a qualcun altro esce dal conto', () => {
    // e' quella che mancava alla home: contava piu' prospect della bacheca
    expect(eProspect(p({ passato_a: 'il web' } as Partial<Tipo>))).toBe(false)
    expect(passato(p({ passato_a: 'Lore' } as Partial<Tipo>))).toBe(true)
    expect(passato(p())).toBe(false)
  })
  it('un morto dichiarato non e\' un prospect', () => {
    expect(eProspect(p({ classificazione: 'fuori_target' }))).toBe(false)
  })
  it('cliente e perso non sono prospect, da nessuna delle due strade', () => {
    expect(eProspect(p({ stage: 'cliente' }))).toBe(false)
    expect(eProspect(p({ stage: 'perso' }))).toBe(false)
  })
})

describe('in pipeline', () => {
  it('fra la prima call e la firma', () => {
    expect(inPipeline(p({ fuori: true, pipeline_stage: 'tecnica' }))).toBe(true)
  })
  it('chi ha firmato o e\' perso e\' fuori dalla pipeline', () => {
    expect(inPipeline(p({ fuori: true, pipeline_stage: 'cliente' }))).toBe(false)
    expect(inPipeline(p({ fuori: true, pipeline_stage: 'perso' }))).toBe(false)
  })
})

describe('il giorno, in ora italiana', () => {
  it('all\'una di notte e\' ancora oggi, non ieri', () => {
    // toISOString() da' il giorno UTC: fra mezzanotte e le 2 sbagliava data
    const notte = new Date(2026, 8, 7, 1, 30)   // 7 settembre, 01:30 locali
    expect(giorno(notte.toISOString())).toBe('2026-09-07')
  })
  it('una data vuota non inventa un giorno', () => {
    expect(giorno(null)).toBe('')
  })
})

describe('il trattino lungo e\' bandito', () => {
  it('diventa due punti, con o senza spazi', () => {
    expect(pulisci('a — b')).toBe('a: b')
    expect(pulisci('a—b')).toBe('a: b')
    expect(pulisci('a —b')).toBe('a: b')
  })
  it('la lineetta media diventa un trattino normale', () => {
    expect(pulisci('lun–ven')).toBe('lun-ven')
  })
  it('un testo pulito resta com\'e\'', () => {
    expect(pulisci('Ciao Dre, tutto a posto.')).toBe('Ciao Dre, tutto a posto.')
  })
})
