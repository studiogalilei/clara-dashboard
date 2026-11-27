import { describe, expect, it } from 'vitest'
import { demoClient } from '../lib/demo'

// Il calendario in demo: programmare un post il giorno di un automatico lo sostituisce (come linkedin_programma).
describe('linkedin_programma in demo', () => {
  it('il post nuovo prende il posto dell’automatico di quel giorno', async () => {
    const d = new Date(); d.setDate(d.getDate() + 2); d.setHours(10, 0, 0, 0)
    const { data } = await demoClient.from('linkedin_post').insert({ dettato: 'prova', stato: 'bozza', origine: 'mio' }) as unknown as { data: Array<{ id: string }> }
    await demoClient.rpc('linkedin_programma', { post: data[0].id, quando: d.toISOString() })
    const { data: righe } = await demoClient.from('linkedin_post').neq('stato', 'scartato') as unknown as { data: Array<{ uscita_il: string; origine: string }> }
    const quelGiorno = righe.filter((r) => r.uscita_il.slice(0, 10) === d.toISOString().slice(0, 10))
    expect(quelGiorno.map((r) => r.origine)).toEqual(['mio'])
  })
})
