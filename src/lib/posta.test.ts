import { describe, expect, it } from 'vitest'
import { percheCosi } from './posta'

describe('il perché così sopra la bozza', () => {
  it('toglie i codici e il «sì:» davanti', () => {
    expect(percheCosi("si': la seconda testa dice INCOERENTE")).toBe('La seconda testa dice INCOERENTE')
    expect(percheCosi('il template di Dre parola per parola (INT-01); adattato l’incipit')).toBe('Il template di Dre parola per parola; adattato l’incipit')
    expect(percheCosi('uso RIMBALZO INTERNO, INT-08')).toBe('Uso RIMBALZO INTERNO')
  })
  it('vuoto resta vuoto, lungo si taglia su una parola intera', () => {
    expect(percheCosi(null)).toBe('')
    const t = percheCosi('a'.repeat(10) + ' parola '.repeat(60))
    expect(t.endsWith('…')).toBe(true)
    expect(t.length).toBeLessThanOrEqual(222)
  })
})

import { soloSuo } from './posta'

describe('solo quello che ha scritto lei (come lettura.solo_suo)', () => {
  it('una risposta che cita solo noi resta vuota (caso WATER WAY)', () => {
    expect(soloSuo("Il 2026-08-03 13:22 Lorenzo Fornasier ha scritto: Buongiorno Daniele, se le fa piacere riceverla, gliela mando subito")).toBe('')
  })
  it('taglia la nostra mail citata anche senza a capo (caso Venice Design Week)', () => {
    expect(soloSuo('mi incuriosisce vediamo e poi fissiamo un appuntamento telefonico dopo il 25 agosto saluti lisa Il giorno lun 10 ago 2026 alle ore 13:42 Lorenzo Fornasier < l@x.com > ha scritto: Buongiorno Lisa'))
      .toBe('mi incuriosisce vediamo e poi fissiamo un appuntamento telefonico dopo il 25 agosto saluti lisa')
  })
  it('«il collega ha scritto:» senza data e ora e\' suo', () => {
    expect(soloSuo('va bene alle 16:30, il collega ha scritto: ok')).toBe('va bene alle 16:30, il collega ha scritto: ok')
  })
  it('via la firma dopo i saluti e il disclaimer', () => {
    expect(soloSuo('Sì grazie, sarei felice di ricevere la vostra analisi.\nCordiali saluti\nCristian Porta\nInformativa privacy disponibile')).toBe('Sì grazie, sarei felice di ricevere la vostra analisi.')
  })
})

import { fraseDiClara } from './posta'

describe('la frase di Clara in cima a Oggi', () => {
  it('dice chi aspetta, con i nomi, e i follow-up pronti', () => {
    expect(fraseDiClara({ risposte: ['CER Italia'], seguiti: 3 })).toBe('CER Italia aspetta una risposta e ho preparato 3 follow-up.')
    expect(fraseDiClara({ risposte: ['A', 'B', 'C', 'D'], seguiti: 1, siSenza: 4 }))
      .toBe('A, B e altre 2 aspettano una risposta, ho preparato un follow-up e 4 sì aspettano ancora l’analisi.')
    expect(fraseDiClara({ risposte: [], seguiti: 2 })).toBe('Ho preparato 2 follow-up.')
  })
  it('a posta vuota la giornata è chiusa', () => {
    expect(fraseDiClara({ risposte: [], seguiti: 0, siSenza: 0 })).toBe('Niente aspetta te: la giornata è chiusa.')
  })
})

import { dataDiRipresa } from './posta'

describe('il non ora diventa una data', () => {
  const oggi = new Date(2026, 9, 6)          // martedì 6 ottobre 2026
  const giorno = (d: Date) => d.toLocaleDateString('sv-SE')
  it('il mese nominato si legge dal giorno della sua mail', () => {
    expect(giorno(dataDiRipresa('ci sentiamo a gennaio', new Date(2026, 9, 1), oggi).il)).toBe('2027-01-11')
    expect(giorno(dataDiRipresa('ne riparliamo a novembre', new Date(2026, 8, 20), oggi).il)).toBe('2026-11-09')
  })
  it('«dopo l’estate» scritto a luglio è già passato: si riprende subito', () => {
    const r = dataDiRipresa('ne riparliamo dopo l’estate', new Date(2026, 6, 10), oggi)
    expect(giorno(r.il)).toBe('2026-10-08')
    expect(r.perche).toContain('già passato')
  })
  it('senza data, tre mesi dalla sua mail, mai nel weekend', () => {
    const r = dataDiRipresa('non riesco a darle una risposta in questo momento', new Date(2026, 7, 7), oggi)
    expect(giorno(r.il)).toBe('2026-11-09')
    expect([0, 6]).not.toContain(r.il.getDay())
  })
})

import { nonDaRiprendere } from './posta'

describe('chi non è un non ora da riprendere', () => {
  it('cambi di indirizzo, «la ricontatto io», motivi personali', () => {
    expect(nonDaRiprendere('Hello Everyone, My Email address has recently changed')).toBeTruthy()
    expect(nonDaRiprendere('Ho provveduto in data 23/06 ad inoltrare alla sede di Brescia')).toBeTruthy()
    expect(nonDaRiprendere('sarà mia premura ricontattarLa qualora di interesse')).toBe('ha detto che si fa vivo lui')
    expect(nonDaRiprendere('in questo momento non posso per problemi in famiglia')).toBe('un motivo personale: non si insiste')
  })
  it('un non ora vero resta', () => {
    expect(nonDaRiprendere('Siamo ancora in early stage per questa iniziativa. Grazie')).toBeNull()
    expect(nonDaRiprendere('Non riesco a darle una risposta in questo momento, non escludo che si possa riparlarne più avanti')).toBeNull()
  })
})

import { rimandata } from './posta'

describe('rimandata a domani', () => {
  const oggi = new Date(2026, 9, 6)
  it('fino al suo giorno non sta nella fila, dal suo giorno torna', () => {
    expect(rimandata({ rimandata_al: '2026-10-07' }, oggi)).toBe(true)
    expect(rimandata({ rimandata_al: '2026-10-06' }, oggi)).toBe(false)
    expect(rimandata({}, oggi)).toBe(false)
  })
})

import { quandoProposto } from './posta'

describe('la fila dei follow-up, il piu urgente prima', () => {
  const oggi = new Date(2026, 9, 6)
  it('giovedì 8 viene prima di martedì 13, e chi non ha un giorno va in fondo', () => {
    expect(quandoProposto('giovedì 8 ottobre alle 15', oggi)).toBeLessThan(quandoProposto('martedì 13 ottobre alle 14:30', oggi))
    expect(quandoProposto('giovedì 8 ottobre alle 15', oggi)).toBeLessThan(quandoProposto('giovedì 8 ottobre alle 16:30', oggi))
    expect(quandoProposto('', oggi)).toBe(Number.POSITIVE_INFINITY)
  })
})
