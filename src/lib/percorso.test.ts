import { describe, it, expect } from 'vitest'
import { tappaDi, prossima, precedente, mossa, inBacheca } from './percorso'
import type { Prospect } from './types'

const p = (x: Partial<Prospect> & { tappa?: string }) =>
  ({ stage: 'risposto', pipeline_stage: null, fuori: false, analysis_sent: false, prova_inizio: null, classificazione: 'positivo', ...x }) as Prospect & { tappa?: string }

describe('la tappa unica (schema_v72)', () => {
  it('una sola tappa per le combinazioni di oggi', () => {
    expect(tappaDi(p({}))).toBe('risposta')
    expect(tappaDi(p({ analysis_sent: true }))).toBe('analisi')
    expect(tappaDi(p({ stage: 'in_follow_up', analysis_sent: true }))).toBe('follow_up')
    expect(tappaDi(p({ stage: 'call_fissata' }))).toBe('conoscitiva')
    // le 47 «in pipeline senza fase» stanno in Conoscitiva, come nella bacheca di sempre
    expect(tappaDi(p({ fuori: true }))).toBe('conoscitiva')
    expect(tappaDi(p({ fuori: true, pipeline_stage: 'tecnica' }))).toBe('tecnica')
    expect(tappaDi(p({ fuori: true, pipeline_stage: 'perso' }))).toBe('perso')
    expect(tappaDi(p({ stage: 'cliente' }))).toBe('cliente')
    expect(tappaDi(p({ stage: 'nuovo' }))).toBe('nuovo')
    expect(tappaDi(p({ tappa: 'avvio' }))).toBe('avvio')
  })

  it('in bacheca solo chi e\' vivo e in cammino', () => {
    expect(inBacheca(p({}))).toBe(true)
    expect(inBacheca(p({ classificazione: 'negativo' }))).toBe(false)
    expect(inBacheca(p({ stage: 'nuovo' }))).toBe(false)
    expect(inBacheca(p({ stage: 'cliente' }))).toBe(false)
  })
})

describe('le regole per muoversi', () => {
  it('prima della call si entra dalla Conoscitiva', () => {
    expect(prossima('analisi')).toBe('conoscitiva')
    const m = mossa(p({ analysis_sent: true }), 'conoscitiva')
    expect('patch' in m && m.patch.fuori && m.patch.pipeline_stage).toBe('conoscitiva')
    expect('no' in mossa(p({}), 'tecnica')).toBe(true)
  })

  it('una tappa alla volta, e il riassunto non blocca piu\' ma resta scritto', () => {
    const c = p({ fuori: true, pipeline_stage: 'conoscitiva' })
    expect(prossima('conoscitiva')).toBe('tecnica')
    expect('no' in mossa(c, 'avvio')).toBe(true)
    const senza = mossa(c, 'tecnica')
    expect('nota' in senza && senza.nota).toBe('Passa a Tecnica (senza riassunto della Conoscitiva)')
    const con = mossa(c, 'tecnica', { riassunto: true })
    expect('nota' in con && con.nota).toBe('Passa a Tecnica')
  })

  it('perso vuole il motivo, e si riapre dentro la trattativa', () => {
    expect('no' in mossa(p({}), 'perso')).toBe(true)
    const m = mossa(p({}), 'perso', { motivo: 'budget' })
    expect('patch' in m && m.patch.stage).toBe('perso')
    const r = mossa(p({ fuori: true, pipeline_stage: 'perso' }), 'tecnica')
    expect('patch' in r && r.patch.pipeline_stage).toBe('tecnica')
  })

  it('indietro: dalla Conoscitiva si torna fra i lead', () => {
    expect(precedente('conoscitiva')).toBe('lead')
    expect(precedente('tecnica')).toBe('conoscitiva')
    expect(precedente('analisi')).toBeNull()
    const m = mossa(p({ fuori: true, pipeline_stage: 'conoscitiva' }), 'lead')
    expect('patch' in m && m.patch.fuori).toBe(false)
  })

  it('in prova le date si mettono da sole, da cliente si porta via il contratto', () => {
    const m = mossa(p({ fuori: true, pipeline_stage: 'avvio' }), 'prova')
    expect('patch' in m && m.patch.contratto).toBe('prova')
    const t = mossa(p({ fuori: true, pipeline_stage: 'cliente' }), 'prova')
    expect('patch' in t && t.patch.contratto).toBeNull()
  })
})
