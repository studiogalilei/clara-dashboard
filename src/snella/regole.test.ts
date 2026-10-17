// La versione snella: le regole di chi chiamare, con dati finti.
import { describe, expect, it } from 'vitest'
import type { Decisione, Domanda, RigaLead } from './dati'
import {
  cerca, chiamateInRitardo, contaStati, eSeguito, giornoRoma, listaDaChiamare, nomeGiorno, perAzienda, piuGiorni, primaRiga, quando,
  scrittoDopo, spiegaDomanda, tasso, titoloDomanda,
} from './regole'

const ORA = new Date('2026-10-19T08:00:00Z')          // lunedi' 19/10, le 10 a Roma

function riga(id: string, cambia: Partial<RigaLead> = {}): RigaLead {
  return { prospect_id: id, azienda: `Azienda ${id}`, persona: `Persona ${id}`, email: `${id}@esempio.it`, stato: 'Vuole sentirti',
           ultima_risposta: '2026-10-18T09:00:00Z', frase: 'Ci sentiamo?', da_chiamare: true, perche_chiamare: 'Vuole sentirti', ...cambia }
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
  it('chi Dre ha messo in No grazie o in Conoscitiva non si chiama; oltre 21 giorni neanche', () => {
    const d = new Map([['a', dec('a', { stato: 'No grazie' })], ['b', dec('b', { stato: 'Conoscitiva' })]])
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
    const m = contaStati([riga('a'), riga('b')], new Map([['a', dec('a', { stato: 'Follow-up' })]]))
    expect(m.get('Follow-up')).toBe(1)
    expect(m.get('Vuole sentirti')).toBe(1)
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
