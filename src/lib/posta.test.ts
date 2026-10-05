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
