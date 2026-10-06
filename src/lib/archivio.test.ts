import { describe, expect, it } from 'vitest'
import { riprendiDallArchivio } from './percorso'

// L'archivio (Dre, 6/10): si riprende solo chi e' uscito per silenzio, e chi ha detto no resta fuori
const base = { stage: 'perso', pipeline_stage: null, fuori: false, analysis_sent: true, prova_inizio: null, tappa: null }

describe("riprendere dall'archivio", () => {
  it('rimette fra i lead chi era uscito per silenzio, senza «niente follow-up»', () => {
    const m = riprendiDallArchivio({ ...base, classificazione: 'positivo', lost_reason: "Nessuna risposta dopo l'analisi (10 giorni), uscito il 1/10" } as never)
    expect('patch' in m && m.patch).toMatchObject({ stage: 'analisi_inviata', no_followup: false, lost_reason: null, tappa: 'analisi' })
  })
  it('non riprende chi ha detto no', () => {
    const m = riprendiDallArchivio({ ...base, classificazione: 'negativo', lost_reason: "Nessuna risposta dopo l'analisi" } as never)
    expect('no' in m).toBe(true)
  })
  it('non tocca i persi con un motivo vero', () => {
    const m = riprendiDallArchivio({ ...base, classificazione: 'positivo', lost_reason: 'ha scelto un altro fornitore' } as never)
    expect('no' in m).toBe(true)
  })
})
