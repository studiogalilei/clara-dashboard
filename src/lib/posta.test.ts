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
