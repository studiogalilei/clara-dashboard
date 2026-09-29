import { useEffect, useMemo, useState } from 'react'
import { supabase } from '../lib/supabase'
import { leggi as leggiPref, scrivi as scriviPref } from '../lib/preferenze'
import { giorno, oggi } from '../lib/regole'
import { useVivo } from '../lib/vivo'
import { Card } from './ui'

// I FOLLOW-UP IN ARRIVO, GIORNO PER GIORNO (Dre, 29/9): «una sezione apribile dove
// vedo in ordine, giorno dopo giorno, i follow-up in arrivo, e un sistema in
// leverage per gestirli tutti». Le date non si calcolano qui: le scrive
// scripts/followup.py nella tabella seguiti_calendario, con la stessa regola che
// mette in coda. Qui si legge, si raggruppa per giorno e si decide sulle eccezioni.
// Le bozze gia' pronte in Posta stanno in «Oggi», con quello che l'ombra ha deciso.

const GRUPPI = ['FOLLOW UP 1', 'MINI FOLLOW UP', 'RIPRESA', 'RINVIO SCADUTO', 'RICONTATTO OOO']
const NOME: Record<string, string> = {
  'FOLLOW UP 1': 'Follow up', 'MINI FOLLOW UP': 'Mini follow up', RIPRESA: 'Ripresa',
  'RINVIO SCADUTO': 'Rinvio', 'RICONTATTO OOO': 'Dopo le ferie',
}

interface Riga {
  prospect_id: string
  gruppo: string
  il: string
  perche: string | null
  nome: string
  proposta?: { id: number; esito?: string; motivo?: string; dalCodice: boolean; azione: Record<string, unknown> }
}

function etichettaGiorno(g: string, adesso: string): string {
  if (g <= adesso) return 'Oggi'
  const domani = giorno(new Date(Date.now() + 86400e3))
  if (g === domani) return 'Domani'
  const d = new Date(g + 'T12:00:00')
  return d.toLocaleDateString('it-IT', { weekday: 'long', day: 'numeric', month: 'short' })
}

export default function SeguitiInArrivo({ onOpen }: { onOpen: (id: string) => void }) {
  const [aperta, setAperta] = useState(() => leggiPref('seguiti-aperti') === 'si')
  const [righe, setRighe] = useState<Riga[] | null>(null)
  const [giro, setGiro] = useState(0)
  const [chiedo, setChiedo] = useState<string | null>(null)   // «Niente follow-up?» chiesto una volta
  const [lavoro, setLavoro] = useState<string | null>(null)
  useVivo(['proposte', 'seguiti_calendario'], () => setGiro((n) => n + 1))

  useEffect(() => {
    let vivo = true
    ;(async () => {
      const [cal, pr] = await Promise.all([
        supabase.from('seguiti_calendario').select('prospect_id,gruppo,il,perche').order('il', { ascending: true }).limit(400),
        supabase.from('proposte').select('id,prospect_id,azione').eq('stato', 'aperta').in('tipo', ['risposta', 'umano'])
          .not('prospect_id', 'is', null).limit(300),
      ])
      const perId = new Map<string, Riga>()
      const adesso = oggi()
      for (const x of (pr.data ?? []) as Array<{ id: number; prospect_id: string; azione: Record<string, unknown> | null }>) {
        const az = x.azione ?? {}
        const gruppo = ((az.lettura as { gruppo?: string } | undefined)?.gruppo) ?? ''
        if (!GRUPPI.includes(gruppo)) continue
        const ombra = az.ombra as { esito?: string; motivo?: string } | undefined
        perId.set(x.prospect_id, {
          prospect_id: x.prospect_id, gruppo, il: adesso, perche: 'bozza pronta in Posta', nome: '',
          proposta: { id: x.id, esito: ombra?.esito, motivo: ombra?.motivo, dalCodice: Boolean(az.testo_dal_codice), azione: az },
        })
      }
      for (const c of (cal.data ?? []) as Array<{ prospect_id: string; gruppo: string; il: string; perche: string | null }>) {
        if (!perId.has(c.prospect_id)) perId.set(c.prospect_id, { ...c, nome: '' })
      }
      const ids = [...perId.keys()]
      for (let i = 0; i < ids.length; i += 150) {
        const { data } = await supabase.from('prospects').select('id,company,name,email').in('id', ids.slice(i, i + 150))
        for (const p of (data ?? []) as Array<{ id: string; company: string | null; name: string | null; email: string }>) {
          const r = perId.get(p.id)
          if (r) r.nome = p.company || p.name || p.email
        }
      }
      // chi non si vede (regola di accesso) non si mostra: niente righe senza nome
      if (vivo) setRighe([...perId.values()].filter((r) => r.nome).sort((a, b) => a.il.localeCompare(b.il)))
    })()
    return () => { vivo = false }
  }, [giro])

  const perGiorno = useMemo(() => {
    const adesso = oggi()
    const m = new Map<string, Riga[]>()
    for (const r of righe ?? []) {
      const k = etichettaGiorno(r.il, adesso)
      m.set(k, [...(m.get(k) ?? []), r])
    }
    return [...m.entries()]
  }, [righe])

  if (righe === null || righe.length === 0) return null
  const adesso = oggi()
  const oggiN = righe.filter((r) => r.il <= adesso).length
  const settimana = righe.filter((r) => r.il <= giorno(new Date(Date.now() + 7 * 86400e3))).length
  const partono = righe.filter((r) => r.proposta?.esito === 'partirebbe').length

  async function nienteFollowup(r: Riga) {
    if (chiedo !== r.prospect_id) { setChiedo(r.prospect_id); return }
    setLavoro(r.prospect_id)
    await supabase.from('prospects').update({ no_followup: true, coda: null }).eq('id', r.prospect_id)
    if (r.proposta) await supabase.from('proposte').update({ stato: 'no', risposta: 'Niente follow-up (dal calendario dei follow-up)' }).eq('id', r.proposta.id)
    await supabase.from('seguiti_calendario').delete().eq('prospect_id', r.prospect_id)
    setRighe((l) => (l ?? []).filter((x) => x.prospect_id !== r.prospect_id))
    setChiedo(null); setLavoro(null)
  }

  // VIA LIBERA: l'ha fermato una traccia che Dre sa essere innocua (una nota di
  // servizio, una call vecchia). Si toglie il giudizio dell'ombra e si segna il via:
  // al prossimo giro il cancello non guarda piu' i contatti fuori da Smartlead.
  async function viaLibera(r: Riga) {
    if (!r.proposta) return
    setLavoro(r.prospect_id)
    const { ombra: _via, ...resto } = r.proposta.azione
    void _via
    await supabase.from('proposte').update({ azione: { ...resto, via_libera: true } }).eq('id', r.proposta.id)
    setGiro((n) => n + 1); setLavoro(null)
  }

  return (
    <Card className="mb-4">
      <button
        onClick={() => { setAperta(!aperta); scriviPref('seguiti-aperti', aperta ? 'no' : 'si') }}
        className="flex w-full items-center gap-2 px-4 py-3 text-left hover:bg-velo/40"
      >
        <svg viewBox="0 0 24 24" className={`h-4 w-4 text-tenue transition-transform duration-150 ${aperta ? 'rotate-90' : ''}`}>
          <path fill="currentColor" d="M9 6l6 6-6 6z" />
        </svg>
        <span className="text-sm font-semibold text-navy">Follow-up in arrivo</span>
        <span className="ml-auto text-xs text-tenue">
          <b className="text-inchiostro">{oggiN}</b> oggi, <b className="text-inchiostro">{settimana}</b> in 7 giorni
          {partono > 0 && <>, <b className="text-inchiostro">{partono}</b> partirebbero da soli</>}
        </span>
      </button>
      {aperta && (
        <div className="border-t border-velo px-2 pb-2">
          {perGiorno.map(([etichetta, lista]) => (
            <div key={etichetta} className="mt-2">
              <p className="px-2 py-1 text-[11px] font-bold uppercase tracking-[0.06em] text-navy">
                {etichetta} <span className="font-semibold text-tenue">{lista.length}</span>
              </p>
              {lista.map((r) => {
                const esito = r.proposta?.esito
                return (
                  <div key={r.prospect_id} className="flex flex-wrap items-center gap-x-3 gap-y-1 rounded-lg px-2 py-2 hover:bg-velo/40">
                    <button onClick={() => onOpen(r.prospect_id)} className="min-w-0 max-w-[16rem] truncate text-left text-sm font-semibold text-inchiostro hover:text-navy">
                      {r.nome}
                    </button>
                    <span className="rounded-full bg-velo px-2 py-0.5 text-[11px] font-semibold text-navy">{NOME[r.gruppo] ?? r.gruppo}</span>
                    <span className="order-last w-full min-w-0 truncate text-xs text-tenue sm:order-none sm:w-auto sm:flex-1">
                      {esito === 'partirebbe' ? 'pronta, partirebbe da sola'
                        : esito === 'resta a Dre' ? `resta a te: ${r.proposta?.motivo ?? ''}`
                        : r.proposta ? (r.proposta.dalCodice ? 'pronta, col tuo testo' : 'pronta in Posta')
                        : r.perche}
                    </span>
                    {esito === 'resta a Dre' && (r.proposta?.motivo ?? '').includes('fuori da Smartlead') && (
                      <button onClick={() => void viaLibera(r)} disabled={lavoro === r.prospect_id}
                              data-tip="La traccia che l'ha fermato è innocua: al prossimo giro il cancello non guarda più i contatti fuori da Smartlead"
                              className="rounded-full border border-blu px-2.5 py-0.5 text-[11px] font-bold text-blu hover:bg-blu/5 disabled:opacity-40">
                        Via libera
                      </button>
                    )}
                    <button onClick={() => void nienteFollowup(r)} disabled={lavoro === r.prospect_id}
                            className={`rounded-full px-2.5 py-0.5 text-[11px] font-semibold disabled:opacity-40 ${chiedo === r.prospect_id ? 'bg-red-50 text-red-700' : 'text-tenue hover:text-inchiostro'}`}>
                      {chiedo === r.prospect_id ? 'Sicuro? Niente più follow-up' : 'Niente follow-up'}
                    </button>
                  </div>
                )
              })}
            </div>
          ))}
        </div>
      )}
    </Card>
  )
}
