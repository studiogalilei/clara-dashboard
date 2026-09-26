import { describe, it, expect } from 'vitest'
import { codiceAzienda, codiceDi, leggiCodice, paiUnCodice } from './codice'

describe('i codici', () => {
  it('l\'azienda ha sempre tre cifre almeno', () => {
    expect(codiceAzienda(201)).toBe('SG-201')
    expect(codiceAzienda(7)).toBe('SG-007')
    expect(codiceAzienda(null)).toBeNull()
  })

  it('le cose dell\'azienda ereditano il suo numero', () => {
    expect(codiceDi(201, 'AN', 2)).toBe('SG-201-AN-02')
    expect(codiceDi(201, 'DOC', 13)).toBe('SG-201-DOC-13')
    expect(codiceDi(null, 'AN', 1)).toBeNull()
  })

  it('si rileggono tutti i codici che usiamo, anche scritti male', () => {
    expect(leggiCodice('SG-201')).toMatchObject({ azienda: 201, tipo: null })
    expect(leggiCodice(' sg-201 ')).toMatchObject({ azienda: 201 })
    expect(leggiCodice('201')).toMatchObject({ azienda: 201 })
    expect(leggiCodice('SG-201-AN-02')).toMatchObject({ azienda: 201, tipo: 'AN', n: 2 })
    expect(leggiCodice('sg-201-doc-13')).toMatchObject({ azienda: 201, tipo: 'DOC', n: 13 })
    // il numero storico dei preventivi resta valido: e' su PDF gia' mandati
    expect(leggiCodice('SG-MK-2026-003')).toMatchObject({ tipo: 'PR', linea: 'MK', anno: 2026, n: 3 })
  })

  it('non scambia per codice quello che non lo e\'', () => {
    expect(leggiCodice('Tecnolegno')).toBeNull()
    expect(leggiCodice('SG')).toBeNull()
    expect(leggiCodice('SG-XX-2026-001')).toBeNull()
    expect(paiUnCodice('tecno')).toBe(false)
    expect(paiUnCodice('SG-201')).toBe(true)
  })
})
