import { Fragment, useEffect, useState } from 'react'
import { supabase } from '../lib/supabase'
import { sonoCeo } from '../lib/accessi'
import { Card, Spinner, Micro, Cella, Faccia, sgid, fmtDateShort, type FacciaP } from './ui'
import { giorno } from '../lib/regole'
import { leggi as leggiPref, scrivi as scriviPref } from '../lib/preferenze'

// PROGETTI = IL FOGLIO DI GIACOMO (Dre, 8/9): «un excel con selettore, serve
// per seguire i progetti in corso». Una riga per progetto, si scrive dentro
// le celle come in un foglio, e il selettore ha esattamente le sue tre voci:
// Trial, Retainer, onboarding. Il cliente si scrive libero (non tutti sono
// prospect del CRM); se e' un prospect, il nome porta alla sua scheda.
// Il dettaglio con i documenti resta nella scheda del cliente.
// 9/9, Dre: «ogni progetto connesso a quell'unico id». Il cliente non si
// scrive piu' a mano: si sceglie fra quelli del CRM (con l'SG-ID accanto) e
// se non c'e' si crea da qui, e nasce gia' con il suo ID.

export interface Progetto {
  id: number
  prospect_id: string | null
  cliente: string | null
  nome: string
  natura: string | null
  chi_segue: string | null
  data_inizio: string | null
  scadenza: string | null
  valore: number | null
  tipo: 'trial' | 'retainer' | 'onboarding' | null
  stato: 'da_iniziare' | 'in_corso' | 'consegnato'
  note: string | null
  // GLI ACCESSI (Alex, 15/9): stavano dentro le note, quindi si scoprivano
  // solo aprendo la riga. Le credenziali non stanno qui e non ci staranno
  // mai: qui c'e' solo dove sono e a che punto siamo.
  accessi_stato?: Accessi | null
  accessi_dove?: string | null
  accessi_chiesti_il?: string | null
  // COSA ABBIAMO IMPARATO (Dre, 15/9, schema_v39): una riga alla consegna.
  // E' l'unico momento in cui uno ce l'ha ancora in testa, ed e' la materia
  // prima per contare i problemi che tornano, settore per settore.
  imparato?: string | null
}

export type Accessi = 'mancano' | 'chiesti' | 'arrivati'

// ambra quando li abbiamo chiesti e aspettiamo, rosso quando non li ha
// chiesti nessuno: il rosso e' la riga su cui Alex e' fermo
export const ACCESSI: Array<[Accessi, string, string]> = [
  ['mancano', 'Mancano', 'bg-red-50 text-red-800'],
  ['chiesti', 'Chiesti', 'bg-amber-100 text-amber-900'],
  ['arrivati', 'Arrivati', 'bg-green-100 text-green-900'],
]

// I progetti che vivono di accessi sono quelli di Alex: sito, landing,
// modifiche a un sito. Sulle campagne la colonna resta vuota invece di
// chiedere una cosa che li' non esiste.
const PAROLE_SITO = /(sito|landing|web|vetrina|shop|e-?commerce|dominio|hosting)/i
export const vuoleAccessi = (p: Progetto) => PAROLE_SITO.test(`${p.natura ?? ''} ${p.nome ?? ''}`)

// il lavoro vivo sta sopra, il consegnato scende; a parita' comanda la
// scadenza, e chi non ce l'ha va in coda (revisione 4/9)
export function ordineProgetti(a: Progetto, b: Progetto): number {
  const finito = (p: Progetto) => (p.stato === 'consegnato' ? 1 : 0)
  if (finito(a) !== finito(b)) return finito(a) - finito(b)
  if (!a.scadenza) return b.scadenza ? 1 : 0
  if (!b.scadenza) return -1
  return a.scadenza.localeCompare(b.scadenza)
}

export const STATI: Array<[Progetto['stato'], string, string]> = [
  ['da_iniziare', 'Da iniziare', 'bg-velo text-tenue'],
  ['in_corso', 'In corso', 'bg-blu/10 text-blu'],
  ['consegnato', 'Consegnato', 'bg-green-50 text-green-800'],
]

// le tre voci del suo foglio, con i suoi colori (verde, giallo, azzurro)
export const TIPI: Array<[NonNullable<Progetto['tipo']>, string, string]> = [
  ['trial', 'Trial', 'bg-amber-100 text-amber-900'],
  ['retainer', 'Retainer', 'bg-green-100 text-green-900'],
  ['onboarding', 'onboarding', 'bg-sky-100 text-sky-900'],
]

// L'ORDINE DEL FOGLIO (Dre, 11/9): «prima i clienti, poi a scendere», o lo
// scegli tu. Di default comanda lo stato: Retainer, Trial, onboarding, senza.
type Ordine = 'stato' | 'cliente' | 'inizio' | 'prezzo' | 'chi_segue'
const ORDINI: Array<[Ordine, string]> = [['stato', 'Stato'], ['cliente', 'Cliente'], ['inizio', 'Inizio'], ['prezzo', 'Prezzo'], ['chi_segue', 'Chi segue']]
const PESO_TIPO: Record<string, number> = { retainer: 0, trial: 1, onboarding: 2 }

interface Props { onOpen: (id: string) => void }

type Campo = 'cliente' | 'nome' | 'natura' | 'chi_segue' | 'data_inizio' | 'scadenza' | 'valore' | 'note' | 'accessi_dove'

export default function Progetti({ onOpen }: Props) {
  const [righe, setRighe] = useState<Progetto[] | null>(null)
  const [nomi, setNomi] = useState<Record<string, string>>({})
  const [ordine, setOrdine] = useState<Ordine>(() => (leggiPref('progetti-ordine') as Ordine) || 'stato')
  const [sg, setSg] = useState<Record<string, number | null>>({})
  const [facce, setFacce] = useState<Record<string, FacciaP>>({})   // per la foto con le cifre dell'ID
  const [scelgo, setScelgo] = useState<number | null>(null)     // la riga con il selettore cliente aperto
  const [menuRiga, setMenuRiga] = useState<number | null>(null)  // il menu ⋯ della riga
  const [chiusi, setChiusi] = useState(false)
  const [problema, setProblema] = useState<string | null>(null)
  const [tolgo, setTolgo] = useState<Progetto | null>(null)   // la riga che sta per sparire
  const [vedoSoldi, setVedoSoldi] = useState(false)
  const [apriAccessi, setApriAccessi] = useState<number | null>(null)   // la riga con il riquadro accessi aperto
  const [imparo, setImparo] = useState<{ id: number; testo: string } | null>(null)  // la riga appena consegnata
  // finche' le colonne non sono sul database la colonna non si mostra:
  // meglio niente che una colonna che da' errore a ogni clic
  const [accessiPronti, setAccessiPronti] = useState(false)

  useEffect(() => {
    void sonoCeo().then(setVedoSoldi)
    void supabase.from('progetti').select('accessi_stato').limit(1)
      .then(({ error }) => setAccessiPronti(!error))
    supabase.from('progetti').select('*')
      .order('data_inizio', { ascending: true, nullsFirst: false }).order('id', { ascending: true }).limit(300)
      .then(({ data, error }) => {
        if (error) setProblema('Il foglio non si legge: ' + error.message)
        setRighe((data as Progetto[]) ?? [])
      })
    supabase.from('prospects').select('id,company,name,email,sg_id,fuori,stage,pipeline_stage').neq('stage', 'nuovo')
      .order('last_reply_at', { ascending: false, nullsFirst: false }).limit(1000)
      .then(({ data }) => {
        const m: Record<string, string> = {}
        const ids: Record<string, number | null> = {}
        const ff: Record<string, FacciaP> = {}
        for (const p of (data as Array<{ id: string; company: string | null; name: string | null; email: string; sg_id: number | null; fuori: boolean; stage: FacciaP['stage']; pipeline_stage: FacciaP['pipeline_stage'] }>) ?? []) {
          m[p.id] = p.company || p.name || p.email
          ids[p.id] = p.sg_id
          ff[p.id] = p
        }
        setNomi(m); setSg(ids); setFacce(ff)
      })
  }, [])

  async function scrivi(p: Progetto, patch: Partial<Progetto>) {
    const { data, error } = await supabase.from('progetti').update(patch).eq('id', p.id).select().single()
    if (error || !data) {
      setProblema(`«${p.nome || p.cliente || 'la riga'}» non è stato salvato: ${error?.message ?? 'nessuna riga aggiornata'}`)
      return
    }
    setProblema(null)
    setRighe((r) => r!.map((x) => (x.id === p.id ? (data as Progetto) : x)))
  }

  function campo(p: Progetto, k: Campo, v: string) {
    const patch: Partial<Progetto> = {}
    if (k === 'valore') patch.valore = v.trim() ? Number(v.replace(',', '.')) : null
    else if (k === 'nome') patch.nome = v.trim()          // nome non ammette il vuoto nel database
    else patch[k] = v.trim() ? v : null
    void scrivi(p, patch)
  }

  // «chiesti» senza il giorno non dice niente: se manca si mette oggi, cosi'
  // si vede da quanto stiamo aspettando senza aprire niente
  function segnaAccessi(p: Progetto, v: Accessi) {
    const patch: Partial<Progetto> = { accessi_stato: v }
    if (v === 'chiesti' && !p.accessi_chiesti_il) patch.accessi_chiesti_il = giorno()
    void scrivi(p, patch)
  }

  async function aggiungi() {
    const { data, error } = await supabase.from('progetti')
      .insert({ nome: '', stato: 'in_corso' }).select().single()
    if (error || !data) { setProblema('La riga nuova non si è creata: ' + (error?.message ?? '')); return }
    setRighe((r) => [...(r ?? []), data as Progetto])
  }

  // il cliente che nel CRM non c'e': nasce adesso, come cliente, con il suo SG-ID
  async function creaCliente(p: Progetto, nome: string) {
    const n = nome.trim()
    if (!n) return
    const oggi = new Date().toISOString()
    const email = `da-completare+${n.toLowerCase().replace(/[^a-z0-9]+/g, '')}@studiogalilei.com`
    const { data, error } = await supabase.from('prospects').insert({
      email, company: n, name: n, stage: 'cliente', fuori: true, fuori_at: oggi, pipeline_stage: 'cliente',
      first_reply_at: oggi, source: 'foglio_progetti', classificazione: 'positivo', awaiting_us: false, no_followup: true,
      notes: 'Creato dal foglio progetti. Email da completare.',
    }).select('id,sg_id').single()
    if (error || !data) { setProblema(`«${n}» non si è creato: ${error?.message ?? ''}`); return }
    const c = data as { id: string; sg_id: number | null }
    setNomi((m) => ({ ...m, [c.id]: n })); setSg((m) => ({ ...m, [c.id]: c.sg_id }))
    await scrivi(p, { prospect_id: c.id, cliente: n })
    setScelgo(null)
  }

  // la conferma sta dentro la pagina, come le altre: il popup del browser
  // non segue il tema e sul telefono e' brutto (QA Dre, 15/9)
  async function togli(p: Progetto) {
    const { error } = await supabase.from('progetti').delete().eq('id', p.id)
    if (error) { setProblema('Non si è tolta: ' + error.message); return }
    setRighe((r) => r!.filter((x) => x.id !== p.id))
    setTolgo(null)
  }

  if (righe === null) return <Spinner />


  const oggi = giorno()
  const colonne = 9 + (vedoSoldi ? 1 : 0) + (accessiPronti ? 1 : 0)
  const nomeDi = (p: Progetto) => (p.prospect_id ? (nomi[p.prospect_id] ?? p.cliente ?? '') : (p.cliente ?? '')).toLowerCase()
  const confronta = (a: Progetto, b: Progetto): number => {
    const perCliente = nomeDi(a).localeCompare(nomeDi(b)) || (a.nome ?? '').localeCompare(b.nome ?? '')
    if (ordine === 'cliente') return perCliente
    if (ordine === 'inizio') return (b.data_inizio ?? '').localeCompare(a.data_inizio ?? '') || perCliente   // i piu' recenti sopra, senza data in coda
    if (ordine === 'prezzo') return (Number(b.valore) || 0) - (Number(a.valore) || 0) || perCliente
    if (ordine === 'chi_segue') return (a.chi_segue ?? 'zzz').localeCompare(b.chi_segue ?? 'zzz') || perCliente
    return (PESO_TIPO[a.tipo ?? ''] ?? 3) - (PESO_TIPO[b.tipo ?? ''] ?? 3) || perCliente
  }
  const vivi = righe.filter((p) => p.stato !== 'consegnato').sort(confronta)
  const fatti = righe.filter((p) => p.stato === 'consegnato').sort(confronta)
  const fermi = vivi.filter((p) => vuoleAccessi(p) && p.accessi_stato !== 'arrivati').length
  const retainer = vivi.filter((p) => p.tipo === 'retainer').reduce((t, p) => t + (Number(p.valore) || 0), 0)
  const totale = vivi.reduce((t, p) => t + (Number(p.valore) || 0), 0)

  const riga = (p: Progetto) => {
    const tardi = p.scadenza && p.scadenza < oggi && p.stato !== 'consegnato'
    const nomeCliente = p.prospect_id ? (nomi[p.prospect_id] ?? p.cliente ?? '') : (p.cliente ?? '')
    return (
      <Fragment key={p.id}>
      <tr className="h-12 border-b border-velo last:border-0 hover:bg-velo/30">
        <td className="sticky left-0 z-10 bg-white">
          {p.prospect_id && scelgo !== p.id ? (
            <div className="group flex items-center">
              <button onClick={() => onOpen(p.prospect_id!)} title={sgid(sg[p.prospect_id]) ?? undefined}
                      className="flex min-w-0 flex-1 items-center gap-2.5 px-3 py-2 text-left text-sm font-semibold hover:text-navy">
                {facce[p.prospect_id] && <Faccia p={facce[p.prospect_id]} size={28} />}
                <span className="truncate">{nomeCliente}</span>
              </button>
              <button onClick={() => setScelgo(p.id)} aria-label="Cambia cliente" title="Cambia cliente"
                      className="mr-1 hidden rounded px-1 text-xs text-spento hover:bg-velo hover:text-navy group-hover:block">⇄</button>
            </div>
          ) : (
            <SceltaCliente
              nomi={nomi} sg={sg} facce={facce}
              onScegli={(id) => { void scrivi(p, { prospect_id: id, cliente: nomi[id] ?? null }); setScelgo(null) }}
              onCrea={(nome) => creaCliente(p, nome)}
              onAnnulla={p.prospect_id ? () => setScelgo(null) : undefined}
            />
          )}
        </td>
        <td className=""><Cella valore={p.nome} su={(v) => campo(p, 'nome', v)} placeholder="cosa gli facciamo" /></td>
        <td className=""><Cella tipo="date" valore={p.data_inizio ?? ''} su={(v) => campo(p, 'data_inizio', v)} className="tabular-nums" /></td>
        {vedoSoldi && <td className=""><Cella tipo="number" valore={p.valore == null ? '' : String(p.valore)} su={(v) => campo(p, 'valore', v)} className="text-right tabular-nums" placeholder="€" /></td>}
        <td className="px-1">
          <select
            value={p.tipo ?? ''}
            onChange={(e) => scrivi(p, { tipo: (e.target.value || null) as Progetto['tipo'] })}
            className={`w-full rounded-md border-0 px-2 py-1 text-xs font-semibold outline-none ${TIPI.find(([t]) => t === p.tipo)?.[2] ?? 'bg-transparent text-spento'}`}
          >
            <option value="">—</option>
            {TIPI.map(([t, etichetta]) => <option key={t} value={t}>{etichetta}</option>)}
          </select>
        </td>
        <td className=""><Cella valore={p.chi_segue ?? ''} su={(v) => campo(p, 'chi_segue', v)} placeholder="chi" /></td>
        {accessiPronti && (
          <td className="px-2">
            {vuoleAccessi(p) && (
              <button
                onClick={() => setApriAccessi(apriAccessi === p.id ? null : p.id)}
                className="flex w-full flex-col items-start gap-0.5 py-1 text-left"
              >
                {p.accessi_stato ? (
                  <span className={`rounded-full px-2 py-0.5 text-[11px] font-bold ${ACCESSI.find(([v]) => v === p.accessi_stato)?.[2] ?? ''}`}>
                    {p.accessi_stato === 'chiesti' && p.accessi_chiesti_il
                      ? `Chiesti il ${fmtDateShort(p.accessi_chiesti_il)}`
                      : ACCESSI.find(([v]) => v === p.accessi_stato)?.[1]}
                  </span>
                ) : (
                  <span className="text-sm text-spento">—</span>
                )}
                {p.accessi_dove && <span className="w-full truncate text-[11px] text-spento">{p.accessi_dove}</span>}
              </button>
            )}
          </td>
        )}
        <td className=""><Cella tipo="date" valore={p.scadenza ?? ''} su={(v) => campo(p, 'scadenza', v)} className={`tabular-nums ${tardi ? 'text-red-700 font-semibold' : ''}`} /></td>
        <td className=""><Cella valore={p.natura ?? ''} su={(v) => campo(p, 'natura', v)} placeholder="sito vetrina, ads…" /></td>
        <td className="">
          <Cella valore={p.note ?? ''} su={(v) => campo(p, 'note', v)} placeholder="note" />
          {p.stato === 'consegnato' && (
            <button onClick={() => setImparo({ id: p.id, testo: p.imparato ?? '' })}
                    title={p.imparato ?? 'Cosa abbiamo imparato?'}
                    className={`mt-0.5 block max-w-[260px] truncate px-2 text-left text-[11px] font-semibold ${p.imparato ? 'text-green-800' : 'text-spento hover:text-navy'}`}>
              {p.imparato ? `Imparato: ${p.imparato}` : 'Cosa abbiamo imparato?'}
            </button>
          )}
        </td>
        <td className="relative px-1 text-center">
          <button onClick={() => setMenuRiga(menuRiga === p.id ? null : p.id)} aria-label="Altro" className="rounded px-1.5 text-spento hover:bg-velo hover:text-navy">⋯</button>
          {menuRiga === p.id && (
            <div className="absolute right-1 top-9 z-20 w-44 overflow-hidden rounded-lg border border-bordo bg-white text-left shadow-lg" onMouseLeave={() => setMenuRiga(null)}>
              {p.stato !== 'consegnato' ? (
                <button onClick={() => { void scrivi(p, { stato: 'consegnato' }); setMenuRiga(null); setImparo({ id: p.id, testo: p.imparato ?? '' }); setChiusi(true) }} className="block w-full px-3 py-2 text-sm hover:bg-velo">Segna consegnato</button>
              ) : (
                <button onClick={() => { void scrivi(p, { stato: 'in_corso' }); setMenuRiga(null) }} className="block w-full px-3 py-2 text-sm hover:bg-velo">Riporta in corso</button>
              )}
              <button onClick={() => { setMenuRiga(null); setTolgo(p) }} className="block w-full px-3 py-2 text-sm text-red-700 hover:bg-red-50">Togli la riga</button>
            </div>
          )}
        </td>
      </tr>
      {imparo?.id === p.id && (
        <tr className="border-b border-velo bg-velo/40">
          <td colSpan={colonne} className="px-3 py-3">
            <div className="sticky left-3 flex max-w-3xl flex-wrap items-center gap-2">
              <span className="text-xs font-bold text-navy">Cosa abbiamo imparato?</span>
              <input
                autoFocus
                value={imparo.testo}
                onChange={(e) => setImparo({ id: p.id, testo: e.target.value })}
                onKeyDown={(e) => { if (e.key === 'Enter') { void scrivi(p, { imparato: imparo.testo.trim() || null }); setImparo(null) } }}
                placeholder="il problema vero era…, la prossima volta…"
                className="min-w-[280px] flex-1 rounded-lg border border-bordo bg-white px-3 py-1.5 text-sm outline-none focus:border-blu"
              />
              <button onClick={() => { void scrivi(p, { imparato: imparo.testo.trim() || null }); setImparo(null) }}
                      disabled={!imparo.testo.trim()}
                      className="rounded-full bg-blu px-3.5 py-1.5 text-xs font-bold text-white hover:bg-blu-scuro disabled:opacity-30">
                Salva
              </button>
              <button onClick={() => setImparo(null)} className="text-xs font-semibold text-tenue hover:text-navy">Salto</button>
            </div>
          </td>
        </tr>
      )}
      {accessiPronti && apriAccessi === p.id && (
        <tr className="border-b border-velo bg-velo/40">
          <td colSpan={colonne} className="px-3 py-3">
            {/* resta incollata a sinistra: il foglio scorre di lato e i
                controlli non devono finire fuori dallo schermo */}
            <div className="sticky left-3 flex max-w-3xl flex-wrap items-center gap-2">
              {ACCESSI.map(([v, etichetta, colore]) => (
                <button
                  key={v}
                  onClick={() => segnaAccessi(p, v)}
                  className={`rounded-full px-3 py-1 text-[11px] font-bold ${
                    p.accessi_stato === v ? colore : 'bg-white text-tenue hover:bg-white/60'
                  }`}
                >
                  {etichetta}
                </button>
              ))}
              {/* qui ci va il posto, non la password: la cartella del cliente
                  nei Documenti, «dal cliente», chi le ha in mano. Le
                  credenziali in chiaro nel foglio le leggerebbe tutta l'agenzia */}
              <input
                key={p.accessi_dove ?? ''}
                defaultValue={p.accessi_dove ?? ''}
                onBlur={(e) => { if (e.target.value !== (p.accessi_dove ?? '')) campo(p, 'accessi_dove', e.target.value) }}
                onKeyDown={(e) => { if (e.key === 'Enter') (e.target as HTMLInputElement).blur() }}
                placeholder="Dove stanno"
                className="w-56 min-w-0 flex-1 rounded-lg border border-bordo bg-white px-3 py-1.5 text-sm outline-none focus:border-blu"
              />
              {p.accessi_stato === 'chiesti' && (
                <input
                  type="date"
                  value={p.accessi_chiesti_il ?? ''}
                  onChange={(e) => void scrivi(p, { accessi_chiesti_il: e.target.value || null })}
                  className="rounded-lg border border-bordo bg-white px-3 py-1.5 text-sm tabular-nums outline-none focus:border-blu"
                />
              )}
              <button onClick={() => setApriAccessi(null)} className="text-[11px] font-semibold text-spento hover:text-navy">
                Chiudi
              </button>
            </div>
          </td>
        </tr>
      )}
      </Fragment>
    )
  }

  const testata = (
    <thead>
      <tr className="bg-velo/60 text-left text-[11px] font-bold uppercase tracking-wide text-tenue">
        <th className="sticky left-0 z-10 min-w-[220px] bg-velo/60 px-3 py-2.5 backdrop-blur">Cliente</th>
        <th className="min-w-[150px] px-3 py-2.5">Progetto</th>
        <th className="min-w-[130px] px-3 py-2.5">Inizio</th>
        {vedoSoldi && <th className="min-w-[90px] px-3 py-2.5 text-right">Prezzo</th>}
        <th className="min-w-[130px] px-3 py-2.5">Stato</th>
        <th className="min-w-[100px] px-3 py-2.5">Chi segue</th>
        {accessiPronti && <th className="min-w-[150px] px-3 py-2.5">Accessi</th>}
        <th className="min-w-[130px] px-3 py-2.5">Scadenza</th>
        <th className="min-w-[120px] px-3 py-2.5">Natura</th>
        <th className="min-w-[180px] px-3 py-2.5">Note</th>
        <th className="w-8"></th>
      </tr>
    </thead>
  )

  return (
    <div className="space-y-3 pb-24 sm:pb-8">
      {problema && (
        <div className="flex items-start gap-2 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800">
          <span className="flex-1">{problema}</span>
          <button onClick={() => setProblema(null)} className="shrink-0 text-xs font-bold text-red-600 hover:text-red-900">Chiudi</button>
        </div>
      )}

      {tolgo && (
        <div className="salta-su flex flex-wrap items-center gap-3 rounded-xl border border-blu/40 bg-white px-4 py-3">
          <span className="flex-1 text-sm font-semibold">Tolgo «{tolgo.nome || tolgo.cliente || 'questa riga'}» dal foglio?</span>
          <button onClick={() => void togli(tolgo)} className="rounded-full bg-red-700 px-4 py-1.5 text-sm font-bold text-white hover:bg-red-800">Sì, togli</button>
          <button onClick={() => setTolgo(null)} className="rounded-full border border-bordo px-4 py-1.5 text-sm font-semibold text-tenue hover:border-spento">No, lascia</button>
        </div>
      )}

      <div className="flex flex-wrap items-baseline gap-x-4 gap-y-1 rounded-xl border border-bordo bg-white px-4 py-3">
        {/* uno zero grande in cima non decide niente e sembra un errore:
            il retainer si mostra quando c'e' (QA browser, 15/9) */}
        {vedoSoldi && retainer > 0 && <>
          <span className="text-xl font-extrabold tabular-nums">{retainer.toLocaleString('it-IT')} €</span>
          <Micro>di retainer al mese</Micro>
        </>}
        <span className="text-sm font-semibold text-tenue">{vedoSoldi ? `${totale.toLocaleString('it-IT')} € in tutto, ` : ''}{vivi.length} progett{vivi.length === 1 ? 'o' : 'i'} in corso</span>
        {accessiPronti && fermi > 0 && (
          <span className="text-xs font-bold text-amber-800">
            {fermi} aspett{fermi === 1 ? 'a' : 'ano'} gli accessi
          </span>
        )}
        {vivi.some((p) => p.scadenza && p.scadenza < oggi) && (
          <span className="text-xs font-bold text-red-700">
            {vivi.filter((p) => p.scadenza && p.scadenza < oggi).length} oltre la scadenza
          </span>
        )}
        <label className="ml-auto flex items-center gap-1.5 text-xs text-tenue">
          Ordina per
          <select value={ordine} onChange={(e) => { const o = e.target.value as Ordine; setOrdine(o); scriviPref('progetti-ordine', o) }}
                  className="rounded-md border border-bordo bg-white px-2 py-1 text-xs font-semibold text-inchiostro outline-none focus:border-blu">
            {ORDINI.map(([o, e]) => <option key={o} value={o}>{e}</option>)}
          </select>
        </label>
        <button onClick={aggiungi} className="rounded-full bg-blu px-4 py-1.5 text-sm font-semibold text-white hover:bg-blu-scuro">
          + Riga
        </button>
      </div>

      <Card>
        <div className="overflow-x-auto">
          <table className="w-full border-collapse">
            {testata}
            <tbody>
              {vivi.length === 0 ? (
                <tr><td colSpan={colonne} className="px-4 py-6 text-center text-sm text-spento">Foglio vuoto.</td></tr>
              ) : vivi.map(riga)}
            </tbody>
          </table>
        </div>
      </Card>

      {fatti.length > 0 && (
        <Card>
          <button onClick={() => setChiusi(!chiusi)} className="flex w-full items-center gap-2 px-4 py-3 text-left hover:bg-velo/40">
            <svg viewBox="0 0 24 24" className={`h-4 w-4 text-tenue transition-transform ${chiusi ? 'rotate-90' : ''}`}>
              <path fill="currentColor" d="M9 6l6 6-6 6z" />
            </svg>
            <span className="text-sm font-bold">Consegnati ({fatti.length})</span>
          </button>
          {chiusi && (
            <div className="overflow-x-auto border-t border-velo">
              <table className="w-full border-collapse">{testata}<tbody>{fatti.map(riga)}</tbody></table>
            </div>
          )}
        </Card>
      )}
    </div>
  )
}

// il selettore del cliente: si scrive, si sceglie fra quelli del CRM (con
// l'SG-ID), o si crea. Niente nomi liberi: ogni progetto appeso al suo ID.
function SceltaCliente({ nomi, sg, facce, onScegli, onCrea, onAnnulla }: {
  nomi: Record<string, string>; sg: Record<string, number | null>; facce: Record<string, FacciaP>
  onScegli: (id: string) => void; onCrea: (nome: string) => void; onAnnulla?: () => void
}) {
  const [testo, setTesto] = useState('')
  const [aperto, setAperto] = useState(false)
  const q = testo.trim().toLowerCase()
  const trovati = q.length < 2 ? [] : Object.entries(nomi)
    .filter(([id, n]) => n.toLowerCase().includes(q) || (sg[id] != null && String(sg[id]) === q.replace(/^sg-?0*/, '')))
    .slice(0, 8)
  return (
    <div className="relative">
      <input
        autoFocus={Boolean(onAnnulla)}
        value={testo}
        onChange={(e) => { setTesto(e.target.value); setAperto(true) }}
        onFocus={() => setAperto(true)}
        onBlur={() => setTimeout(() => setAperto(false), 150)}
        onKeyDown={(e) => { if (e.key === 'Escape' && onAnnulla) onAnnulla(); if (e.key === 'Enter' && trovati[0]) onScegli(trovati[0][0]) }}
        placeholder="cerca il cliente o l'SG-ID"
        className="w-full min-w-0 bg-transparent px-2 py-1.5 text-sm font-semibold outline-none focus:bg-blu/5 focus:ring-1 focus:ring-blu"
      />
      {aperto && q.length >= 2 && (
        <div className="absolute left-0 top-full z-20 mt-0.5 w-72 overflow-hidden rounded-lg border border-bordo bg-white shadow-lg">
          {trovati.map(([id, n]) => (
            <button key={id} onMouseDown={() => onScegli(id)} className="flex w-full items-center gap-2 px-3 py-1.5 text-left text-sm hover:bg-velo">
              {facce[id] && <Faccia p={facce[id]} size={22} />}
              <span className="truncate">{n}</span>
              {sg[id] != null && <span className="ml-auto text-[11px] text-spento">{sgid(sg[id])}</span>}
            </button>
          ))}
          <button onMouseDown={() => onCrea(testo)} className="flex w-full items-center gap-2 border-t border-velo px-3 py-1.5 text-left text-sm font-semibold text-navy hover:bg-velo">
            + Crea «{testo.trim()}» come cliente nuovo
          </button>
        </div>
      )}
    </div>
  )
}
