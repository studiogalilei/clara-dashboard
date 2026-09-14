import { useEffect, useMemo, useState } from 'react'
import { supabase } from '../lib/supabase'
import { Card, Spinner, Micro, sgid, fmtDateShort, Faccia, type FacciaP } from './ui'
import { creaTask } from '../lib/regole'
import { LINEA_NOME, controllaTono, testoDi } from '../lib/tono'
import {
  STATI, alMese, unaTantum, lineaDi, prossimoNumero, titoloDi, documentoDi, generaEArchivia, scaduto,
  type Preventivo, type Voce, type VoceListino, type Fatturazione,
} from '../lib/preventivo'

// I PREVENTIVI (Dre, 14/9): si crea in modo smooth, esce un PDF secondo il
// brand, si segna inviato, accettato o rifiutato, e si vede cosa gira e per
// chi. Collegato all'azienda (scheda, cartella Documenti), ai progetti
// (accettato = nasce il progetto) e a Stripe (pagato lo scrive Clara).
// Lo vedono Dre e Giacomo: la regola e' nel database (ruolo ceo).

interface Props { onOpen: (id: string) => void }
type Nome = FacciaP & { id: string; email: string; fatturazione: Fatturazione | null }
type Filtro = 'giro' | 'tutti' | 'accettati' | 'pagati' | 'rifiutati' | 'bozze'

interface Incasso {
  id: string; genere: 'addebito' | 'fattura' | 'abbonamento'; importo: number; valuta: string; stato: string | null
  quando: string | null; ricorrenza: string | null; cliente_nome: string | null; cliente_email: string | null
  descrizione: string | null; prospect_id: string | null; preventivo_id: number | null
}
const GENERE: Record<Incasso['genere'], string> = { addebito: 'Pagamento', fattura: 'Fattura', abbonamento: 'Abbonamento' }
function tonoStato(s: string | null) {
  if (s === 'succeeded' || s === 'paid' || s === 'active' || s === 'trialing') return 'bg-green-100 text-green-900'
  if (s === 'failed' || s === 'canceled' || s === 'incomplete_expired' || s === 'unpaid') return 'bg-red-50 text-red-700'
  return 'bg-velo text-tenue'
}
function statoIt(s: string | null) {
  return ({ succeeded: 'riuscito', paid: 'pagata', open: 'aperta', active: 'attivo', trialing: 'in prova', canceled: 'cancellato',
    failed: 'fallito', incomplete: 'incompleto', incomplete_expired: 'scaduto', past_due: 'in ritardo', unpaid: 'non pagato' } as Record<string, string>)[s ?? ''] ?? (s ?? '')
}

const oggi = () => new Date().toISOString().slice(0, 10)
const fraGiorni = (n: number) => new Date(Date.now() + n * 86400e3).toISOString().slice(0, 10)
const euro = (n: number | null | undefined) => n == null ? '' : `${Number(n).toLocaleString('it-IT')} €`

// quello che si scrive nel pannello, prima di diventare una riga
interface Bozza {
  id: number | null
  prospect_id: string
  voci: Voce[]
  valido_fino: string
  note: string
  fatturazione: Fatturazione
}
const vuota = (): Bozza => ({ id: null, prospect_id: '', voci: [], valido_fino: fraGiorni(30), note: '', fatturazione: {} })

export default function Preventivi({ onOpen }: Props) {
  const [righe, setRighe] = useState<Preventivo[] | null>(null)
  const [nomi, setNomi] = useState<Record<string, Nome>>({})
  const [aziende, setAziende] = useState<Nome[]>([])
  const [listino, setListino] = useState<VoceListino[]>([])
  const [incassi, setIncassi] = useState<Incasso[] | null>(null)
  const [filtro, setFiltro] = useState<Filtro>('giro')
  const [cerca, setCerca] = useState('')
  const [bozza, setBozza] = useState<Bozza | null>(null)
  const [lavoro, setLavoro] = useState<string | null>(null)       // «Genero il PDF…»
  const [problema, setProblema] = useState<string | null>(null)
  const [toast, setToast] = useState<string | null>(null)
  const [cercaAzienda, setCercaAzienda] = useState('')
  const [chiedo, setChiedo] = useState<{ id: number; cosa: 'rifiuto' | 'link' } | null>(null)
  const [testoChiesto, setTestoChiesto] = useState('')

  useEffect(() => {
    void supabase.from('preventivi').select('*').order('creato_il', { ascending: false }).limit(2000)
      .then(({ data, error }) => { if (error) setProblema(error.message); setRighe((data as Preventivo[]) ?? []) })
    void supabase.from('prospects').select('id,company,name,email,sg_id,fuori,stage,pipeline_stage,fatturazione').order('company').limit(3000)
      .then(({ data }) => {
        const l = (data as Nome[]) ?? []
        setAziende(l)
        const m: Record<string, Nome> = {}
        for (const x of l) m[x.id] = x
        setNomi(m)
      })
    void supabase.from('listino').select('*').eq('attivo', true).order('ordine').then(({ data }) => setListino((data as VoceListino[]) ?? []))
    void supabase.from('incassi').select('*').order('quando', { ascending: false }).limit(500)
      .then(({ data, error }) => { if (!error && data && data.length) setIncassi(data as Incasso[]) })
  }, [])

  // arrivo dalla scheda di un'azienda: il pannello si apre gia' su di lei.
  // Il widget non era montato quando la scheda ha chiesto: l'azienda aspetta in sessionStorage
  useEffect(() => {
    if (Object.keys(nomi).length === 0) return
    let id: string | null = null
    try { id = sessionStorage.getItem('preventivo:nuovo'); sessionStorage.removeItem('preventivo:nuovo') } catch { /* niente */ }
    if (id) apriNuovo(id)
  }, [nomi])   // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    if (!toast) return
    const t = setTimeout(() => setToast(null), 2800)
    return () => clearTimeout(t)
  }, [toast])

  const nomeDi = (id: string) => { const n = nomi[id]; return n ? (n.company || n.name || n.email) : '…' }

  async function scrivi(id: number, patch: Partial<Preventivo>): Promise<Preventivo | null> {
    const { data, error } = await supabase.from('preventivi').update({ ...patch, aggiornato_il: new Date().toISOString() }).eq('id', id).select().single()
    if (error) { setProblema(`Non ho potuto salvare: ${error.message}`); return null }
    setRighe((v) => v!.map((q) => (q.id === id ? (data as Preventivo) : q)))
    return data as Preventivo
  }

  // ── il pannello: nuovo o modifica ─────────────────────────────────────
  function apriNuovo(prospect_id = '') {
    const n = nomi[prospect_id]
    setBozza({ ...vuota(), prospect_id, fatturazione: n?.fatturazione ?? (n ? { ragione: n.company ?? '' } : {}) })
    setCercaAzienda('')
  }
  function apriModifica(q: Preventivo) {
    const n = nomi[q.prospect_id]
    setBozza({ id: q.id, prospect_id: q.prospect_id, voci: q.voci ?? [], valido_fino: q.valido_fino ?? fraGiorni(30), note: q.note ?? '', fatturazione: n?.fatturazione ?? { ragione: n?.company ?? '' } })
  }
  function scegliAzienda(id: string) {
    const n = nomi[id]
    setBozza((b) => b && ({ ...b, prospect_id: id, fatturazione: n?.fatturazione ?? { ragione: n?.company ?? '' } }))
    setCercaAzienda('')
  }
  function aggiungiVoce(v: VoceListino) {
    setBozza((b) => b && ({ ...b, voci: [...b.voci, { nome: v.nome, descrizione: v.descrizione ?? undefined, quantita: 1, prezzo: Number(v.prezzo), ricorrenza: v.ricorrenza }] }))
  }
  function cambiaVoce(i: number, patch: Partial<Voce>) {
    setBozza((b) => b && ({ ...b, voci: b.voci.map((v, k) => (k === i ? { ...v, ...patch } : v)) }))
  }

  // salva la bozza (riga + dati di fatturazione sull'azienda) e, se chiesto, genera il PDF
  async function salva(conPdf: boolean) {
    if (!bozza) return
    if (!bozza.prospect_id) { setProblema('Scegli l\'azienda prima.'); return }
    if (bozza.voci.length === 0) { setProblema('Un preventivo senza voci non è un preventivo.'); return }
    if (bozza.voci.some((v) => !v.nome.trim())) { setProblema('Ogni voce ha un nome.'); return }
    setLavoro(conPdf ? 'Salvo e genero il PDF…' : 'Salvo…')
    try {
      const linea = lineaDi(bozza.voci, listino)
      const base = {
        prospect_id: bozza.prospect_id, linea, voci: bozza.voci, titolo: titoloDi(bozza.voci),
        importo: unaTantum(bozza.voci), mensile: alMese(bozza.voci) || null, valido_fino: bozza.valido_fino || null,
        note: bozza.note || null, aggiornato_il: new Date().toISOString(),
      }
      let riga: Preventivo
      if (bozza.id) {
        const { data, error } = await supabase.from('preventivi').update(base).eq('id', bozza.id).select().single()
        if (error) throw new Error(error.message)
        riga = data as Preventivo
      } else {
        const numero = await prossimoNumero(linea)
        const { data: sess } = await supabase.auth.getSession()
        const { data, error } = await supabase.from('preventivi').insert({ ...base, numero, stato: 'bozza', owner: sess.session?.user?.id ?? null }).select().single()
        if (error) throw new Error(error.message)
        riga = data as Preventivo
      }
      // i dati di fatturazione restano sull'azienda: servono anche a Giacomo
      const f = bozza.fatturazione
      if (f.ragione || f.indirizzo || f.piva || f.pec || f.sdi) {
        await supabase.from('prospects').update({ fatturazione: f }).eq('id', bozza.prospect_id)
        setNomi((m) => ({ ...m, [bozza.prospect_id]: { ...m[bozza.prospect_id], fatturazione: f } }))
      }
      if (conPdf) {
        const doc = documentoDi(riga, nomeDi(riga.prospect_id), f)
        const tono = controllaTono(testoDi(doc))
        if (tono.length) throw new Error(`Il testo non passa il controllo del tono: ${tono.join(', ')}`)
        const { path } = await generaEArchivia(riga, nomeDi(riga.prospect_id), f)
        const { data } = await supabase.from('preventivi').update({ pdf_path: path }).eq('id', riga.id).select().single()
        if (data) riga = data as Preventivo
      }
      setRighe((v) => { const l = (v ?? []).filter((q) => q.id !== riga.id); return [riga, ...l] })
      setBozza(null)
      setToast(conPdf ? `${riga.numero}: PDF pronto, nella cartella di ${nomeDi(riga.prospect_id)} ✓` : `${riga.numero} salvato come bozza ✓`)
      if (conPdf) apri(riga)
    } catch (e) {
      setProblema((e as Error).message)
    } finally {
      setLavoro(null)
    }
  }

  function apri(q: Preventivo) {
    if (!q.pdf_path) return
    const { data } = supabase.storage.from('vault').getPublicUrl(q.pdf_path)
    window.open(data.publicUrl, '_blank', 'noopener')
  }

  // ── gli esiti: inviato, accettato (nasce il progetto), rifiutato, pagato ──
  async function segnaInviato(q: Preventivo) {
    if (!q.pdf_path && !confirm('Non c\'è ancora il PDF. Lo segno inviato lo stesso?')) return
    const r = await scrivi(q.id, { stato: 'inviato', inviato_il: q.inviato_il ?? oggi() })
    if (r) setToast(`${q.numero} segnato inviato. Quando risponde, segna l'esito qui.`)
  }
  async function segnaAccettato(q: Preventivo) {
    const r = await scrivi(q.id, { stato: 'accettato', accettato_il: oggi() })
    if (!r) return
    let messaggio = `${q.numero} accettato ✓`
    // nasce il progetto, cosi' in Clienti si vede subito cosa gli abbiamo venduto
    if (!q.progetto_id) {
      const tipo = q.voci?.some((v) => /pilota|prova/i.test(v.nome)) ? 'trial' : q.mensile ? 'retainer' : null
      const { data: g } = await supabase.from('progetti').insert({
        prospect_id: q.prospect_id, nome: q.titolo ?? 'Progetto', valore: (q.importo ?? 0) + (q.mensile ?? 0) * 2, stato: 'da_iniziare', tipo,
        note: `Dal preventivo ${q.numero}`,
      }).select('id').single()
      if (g) { await scrivi(q.id, { progetto_id: g.id }); messaggio += ', progetto creato' }
    }
    // e la call di avvio va fissata: una task in cima alla lista
    const { task } = await creaTask({ titolo: `Fissare la call di avvio con ${nomeDi(q.prospect_id)}`, prospect_id: q.prospect_id, scadenza: fraGiorni(3) })
    if (task) messaggio += ', task per la call di avvio'
    setToast(messaggio)
  }
  async function segnaRifiutato(q: Preventivo, motivo: string) {
    const r = await scrivi(q.id, { stato: 'rifiutato', rifiutato_il: oggi(), motivo: motivo || null })
    if (r) setToast(`${q.numero} segnato rifiutato`)
  }
  async function segnaPagato(q: Preventivo) {
    const r = await scrivi(q.id, { pagato_il: oggi(), note: [q.note, 'segnato a mano'].filter(Boolean).join(', ') })
    if (r) setToast(`${q.numero} pagato ✓`)
  }
  async function riapri(q: Preventivo) {
    const r = await scrivi(q.id, { stato: 'inviato', accettato_il: null, rifiutato_il: null, motivo: null })
    if (r) setToast(`${q.numero} di nuovo in attesa`)
  }
  async function copiaLink(q: Preventivo) {
    if (!q.link_pagamento) { setChiedo({ id: q.id, cosa: 'link' }); setTestoChiesto(''); return }
    try { await navigator.clipboard.writeText(q.link_pagamento); setToast('Link di pagamento copiato ✓') } catch { setProblema('Non riesco a copiare') }
  }
  async function elimina(q: Preventivo) {
    if (!confirm(`Elimino la bozza ${q.numero}?`)) return
    const { error } = await supabase.from('preventivi').delete().eq('id', q.id)
    if (error) { setProblema(error.message); return }
    setRighe((v) => v!.filter((x) => x.id !== q.id))
  }

  // ── la lista ───────────────────────────────────────────────────────────
  const t = cerca.trim().toLowerCase()
  const visibili = useMemo(() => (righe ?? []).filter((q) => {
    if (filtro === 'giro' && !(q.stato === 'inviato')) return false
    if (filtro === 'accettati' && !(q.stato === 'accettato' && !q.pagato_il)) return false
    if (filtro === 'pagati' && !q.pagato_il) return false
    if (filtro === 'rifiutati' && q.stato !== 'rifiutato') return false
    if (filtro === 'bozze' && q.stato !== 'bozza') return false
    if (!t) return true
    const n = nomi[q.prospect_id]
    return (q.numero ?? '').toLowerCase().includes(t) || (q.titolo ?? '').toLowerCase().includes(t)
      || nomeDi(q.prospect_id).toLowerCase().includes(t) || (sgid(n?.sg_id, n) ?? '').toLowerCase().includes(t)
  }), [righe, filtro, t, nomi])   // eslint-disable-line react-hooks/exhaustive-deps

  if (righe === null) return <Spinner />

  const somma = (l: Preventivo[]) => l.reduce((s, q) => s + (Number(q.importo) || 0), 0)
  const inGiro = righe.filter((q) => q.stato === 'inviato')
  const scaduti = inGiro.filter(scaduto)
  const daIncassare = righe.filter((q) => q.stato === 'accettato' && !q.pagato_il)
  const incassati = righe.filter((q) => q.pagato_il)
  const anno = new Date().getFullYear()
  const incassatiStripe = (incassi ?? []).filter((i) => i.genere === 'addebito' && i.stato === 'succeeded' && (i.quando ?? '').startsWith(String(anno)))
  const abbonamenti = (incassi ?? []).filter((i) => i.genere === 'abbonamento' && (i.stato === 'active' || i.stato === 'trialing'))
  const mensile = abbonamenti.reduce((s, i) => s + (i.ricorrenza === 'year' ? i.importo / 12 : i.importo), 0)

  const tessera = (n: string, v: number, quanti: number, tono = '', su?: Filtro) => (
    <button onClick={() => su && setFiltro(su)} disabled={!su}
            className={`min-w-[150px] flex-1 rounded-xl border bg-white px-4 py-3 text-left ${su && filtro === su ? 'border-navy' : 'border-bordo'} ${su ? 'hover:border-navy' : ''}`}>
      <Micro>{n}</Micro>
      <p className={`text-xl font-extrabold tabular-nums ${tono}`}>{v.toLocaleString('it-IT')} €</p>
      <p className="text-[11px] text-spento">{quanti} preventiv{quanti === 1 ? 'o' : 'i'}</p>
    </button>
  )

  const candidate = cercaAzienda.trim()
    ? aziende.filter((a) => (a.company || a.name || a.email || '').toLowerCase().includes(cercaAzienda.trim().toLowerCase())).slice(0, 8)
    : []

  return (
    <div className="space-y-4 pb-24 sm:pb-8">
      {problema && (
        <div className="flex items-start gap-2 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800">
          <span className="flex-1">{problema}</span>
          <button onClick={() => setProblema(null)} className="shrink-0 text-xs font-bold text-red-600 hover:text-red-900">chiudi</button>
        </div>
      )}

      {/* le tessere: un colpo d'occhio, e cliccando filtrano */}
      <div className="flex flex-wrap gap-2">
        {tessera('In giro, in attesa', somma(inGiro), inGiro.length, scaduti.length ? 'text-amber-800' : '', 'giro')}
        {tessera('Accettati, da incassare', somma(daIncassare), daIncassare.length, daIncassare.length ? 'text-amber-800' : '', 'accettati')}
        {tessera('Incassati', somma(incassati), incassati.length, 'text-green-800', 'pagati')}
        {incassi && (
          <div className="min-w-[150px] flex-1 rounded-xl border border-bordo bg-white px-4 py-3">
            <Micro>Abbonamenti su Stripe</Micro>
            <p className="text-xl font-extrabold tabular-nums">{Math.round(mensile).toLocaleString('it-IT')} € <span className="text-sm font-semibold text-tenue">al mese</span></p>
            <p className="text-[11px] text-spento">{abbonamenti.length} attiv{abbonamenti.length === 1 ? 'o' : 'i'}, {incassatiStripe.length} pagament{incassatiStripe.length === 1 ? 'o' : 'i'} nel {anno}</p>
          </div>
        )}
      </div>

      {/* la barra: filtri, ricerca, nuovo */}
      <div className="flex flex-wrap items-center gap-2">
        <div className="flex flex-wrap gap-1.5">
          {([['giro', 'In giro'], ['accettati', 'Da incassare'], ['pagati', 'Pagati'], ['rifiutati', 'Rifiutati'], ['bozze', 'Bozze'], ['tutti', 'Tutti']] as Array<[Filtro, string]>).map(([k, n]) => (
            <button key={k} onClick={() => setFiltro(k)}
                    className={`rounded-full px-3 py-1.5 text-sm font-semibold ${filtro === k ? 'bg-navy text-white' : 'bg-white text-tenue ring-1 ring-bordo hover:text-inchiostro'}`}>{n}</button>
          ))}
        </div>
        <div className="ml-auto flex items-center gap-2">
          <input type="search" value={cerca} onChange={(e) => setCerca(e.target.value)} placeholder="Cerca azienda o numero…"
                 className="w-56 rounded-full border border-bordo bg-white px-4 py-2 text-sm outline-none focus:border-blu" />
          <button onClick={() => apriNuovo()} className="rounded-full bg-blu px-4 py-2 text-sm font-bold text-white shadow-[0_4px_12px_rgba(6,23,115,0.25)] hover:bg-blu-scuro">+ Nuovo preventivo</button>
        </div>
      </div>

      {/* IL PANNELLO: azienda, voci, validita', PDF. Tutto in una schermata */}
      {bozza && (
        <Card className="salta-su space-y-5 border-blu/40 p-5">
          <div className="flex items-baseline justify-between gap-3">
            <h2 className="text-base font-extrabold">{bozza.id ? 'Modifica il preventivo' : 'Nuovo preventivo'}</h2>
            <button onClick={() => setBozza(null)} className="text-xs font-semibold text-spento hover:text-inchiostro">annulla</button>
          </div>

          {/* 1. l'azienda */}
          <div className="grid gap-4 md:grid-cols-2">
            <div>
              <Micro>Azienda</Micro>
              {bozza.prospect_id ? (
                <div className="mt-1 flex items-center gap-2.5 rounded-xl border border-bordo bg-white px-3 py-2">
                  {nomi[bozza.prospect_id] && <Faccia p={nomi[bozza.prospect_id]} size={28} />}
                  <span className="min-w-0 flex-1 truncate text-sm font-semibold">{nomeDi(bozza.prospect_id)}</span>
                  {!bozza.id && <button onClick={() => setBozza({ ...bozza, prospect_id: '' })} className="text-xs font-semibold text-blu hover:underline">cambia</button>}
                </div>
              ) : (
                <div className="relative mt-1">
                  <input autoFocus value={cercaAzienda} onChange={(e) => setCercaAzienda(e.target.value)} placeholder="Scrivi il nome dell'azienda…"
                         className="w-full rounded-xl border border-bordo bg-white px-3 py-2 text-sm outline-none focus:border-blu" />
                  {candidate.length > 0 && (
                    <div className="absolute z-20 mt-1 w-full overflow-hidden rounded-xl border border-bordo bg-white shadow-[0_8px_24px_rgba(16,24,40,0.12)]">
                      {candidate.map((a) => (
                        <button key={a.id} onClick={() => scegliAzienda(a.id)} className="flex w-full items-center gap-2.5 px-3 py-2 text-left text-sm hover:bg-velo">
                          <Faccia p={a} size={24} />
                          <span className="min-w-0 flex-1 truncate">{a.company || a.name || a.email}</span>
                          {sgid(a.sg_id, a) && <span className="text-[11px] font-semibold text-spento">{sgid(a.sg_id, a)}</span>}
                        </button>
                      ))}
                    </div>
                  )}
                </div>
              )}
            </div>
            <div className="grid grid-cols-2 gap-2">
              {([['ragione', 'Ragione sociale'], ['piva', 'Partita IVA'], ['indirizzo', 'Indirizzo'], ['pec', 'PEC'], ['sdi', 'Codice SDI']] as Array<[keyof Fatturazione, string]>).map(([k, n]) => (
                <label key={k} className={k === 'indirizzo' ? 'col-span-2' : ''}>
                  <span className="text-[10px] font-bold uppercase tracking-wide text-spento">{n}</span>
                  <input value={bozza.fatturazione[k] ?? ''} onChange={(e) => setBozza({ ...bozza, fatturazione: { ...bozza.fatturazione, [k]: e.target.value } })}
                         className="mt-0.5 w-full rounded-lg border border-bordo bg-white px-2.5 py-1.5 text-sm outline-none focus:border-blu" />
                </label>
              ))}
            </div>
          </div>

          {/* 2. le voci: dal listino con un clic, o scritte a mano */}
          <div>
            <div className="flex flex-wrap items-center gap-1.5">
              <Micro>Voci</Micro>
              {listino.map((v) => (
                <button key={v.id} onClick={() => aggiungiVoce(v)} title={v.descrizione ?? undefined}
                        className="rounded-full border border-bordo bg-white px-3 py-1 text-xs font-semibold text-tenue hover:border-navy hover:text-navy">
                  + {v.nome}{v.prezzo ? <span className="text-spento"> {euro(v.prezzo)}{v.ricorrenza === 'mese' ? '/mese' : ''}</span> : null}
                </button>
              ))}
              <button onClick={() => setBozza({ ...bozza, voci: [...bozza.voci, { nome: '', quantita: 1, prezzo: 0, ricorrenza: 'una_tantum' }] })}
                      className="rounded-full border border-dashed border-bordo px-3 py-1 text-xs font-semibold text-tenue hover:border-navy hover:text-navy">+ voce a mano</button>
            </div>
            {bozza.voci.length > 0 && (
              <div className="mt-2 overflow-hidden rounded-xl border border-bordo bg-white">
                {bozza.voci.map((v, i) => (
                  <div key={i} className="grid grid-cols-[1fr_64px_110px_120px_28px] items-center gap-2 border-b border-velo px-3 py-2 last:border-0">
                    <div className="min-w-0">
                      <input value={v.nome} onChange={(e) => cambiaVoce(i, { nome: e.target.value })} placeholder="Cosa"
                             className="w-full rounded bg-transparent text-sm font-semibold outline-none focus:bg-velo" />
                      <input value={v.descrizione ?? ''} onChange={(e) => cambiaVoce(i, { descrizione: e.target.value })} placeholder="Una riga che spiega (va nel PDF)"
                             className="w-full rounded bg-transparent text-xs text-tenue outline-none focus:bg-velo" />
                    </div>
                    <input type="number" min={1} value={v.quantita} onChange={(e) => cambiaVoce(i, { quantita: Math.max(1, Number(e.target.value) || 1) })}
                           className="w-full rounded-lg border border-bordo px-2 py-1 text-right text-sm tabular-nums outline-none focus:border-blu" />
                    <div className="flex items-center gap-1">
                      <input type="number" min={0} step={1} value={v.prezzo} onChange={(e) => cambiaVoce(i, { prezzo: Number(e.target.value) || 0 })}
                             className="w-full rounded-lg border border-bordo px-2 py-1 text-right text-sm tabular-nums outline-none focus:border-blu" />
                      <span className="text-xs text-spento">€</span>
                    </div>
                    <select value={v.ricorrenza} onChange={(e) => cambiaVoce(i, { ricorrenza: e.target.value as Voce['ricorrenza'] })}
                            className="rounded-lg border border-bordo bg-white px-2 py-1 text-xs outline-none focus:border-blu">
                      <option value="una_tantum">una tantum</option>
                      <option value="mese">al mese</option>
                    </select>
                    <button onClick={() => setBozza({ ...bozza, voci: bozza.voci.filter((_, k) => k !== i) })} aria-label="Togli" className="text-spento hover:text-red-700">×</button>
                  </div>
                ))}
                <div className="flex flex-wrap items-baseline justify-end gap-x-5 gap-y-1 bg-velo/60 px-3 py-2 text-sm">
                  {unaTantum(bozza.voci) > 0 && <span><span className="text-tenue">alla firma</span> <b className="tabular-nums">{euro(unaTantum(bozza.voci))}</b></span>}
                  {alMese(bozza.voci) > 0 && <span><span className="text-tenue">poi</span> <b className="tabular-nums">{euro(alMese(bozza.voci))}</b> <span className="text-tenue">al mese</span></span>}
                  <span className="text-xs text-spento">IVA esclusa, linea {LINEA_NOME[lineaDi(bozza.voci, listino)]}</span>
                </div>
              </div>
            )}
          </div>

          {/* 3. validita' e note, poi il PDF */}
          <div className="flex flex-wrap items-end gap-3">
            <label>
              <span className="text-[10px] font-bold uppercase tracking-wide text-spento">Valido fino al</span>
              <input type="date" value={bozza.valido_fino} onChange={(e) => setBozza({ ...bozza, valido_fino: e.target.value })}
                     className="mt-0.5 block rounded-lg border border-bordo bg-white px-2.5 py-1.5 text-sm outline-none focus:border-blu" />
            </label>
            <label className="min-w-[240px] flex-1">
              <span className="text-[10px] font-bold uppercase tracking-wide text-spento">Note interne (non vanno nel PDF)</span>
              <input value={bozza.note} onChange={(e) => setBozza({ ...bozza, note: e.target.value })}
                     className="mt-0.5 block w-full rounded-lg border border-bordo bg-white px-2.5 py-1.5 text-sm outline-none focus:border-blu" />
            </label>
            <div className="ml-auto flex items-center gap-2">
              <button onClick={() => salva(false)} disabled={!!lavoro} className="rounded-full border border-bordo bg-white px-4 py-2 text-sm font-semibold text-tenue hover:border-navy hover:text-navy disabled:opacity-40">Salva bozza</button>
              <button onClick={() => salva(true)} disabled={!!lavoro} className="rounded-full bg-blu px-5 py-2 text-sm font-bold text-white hover:bg-blu-scuro disabled:opacity-40">{lavoro ?? 'Genera il PDF'}</button>
            </div>
          </div>
        </Card>
      )}

      {/* una domanda veloce: il motivo del no, o il link di pagamento */}
      {chiedo && (
        <Card className="salta-su flex flex-wrap items-center gap-2 border-blu/40 p-3">
          <span className="text-sm font-semibold">{chiedo.cosa === 'rifiuto' ? 'Perché ha detto no?' : 'Incolla il link di pagamento Stripe'}</span>
          <input autoFocus value={testoChiesto} onChange={(e) => setTestoChiesto(e.target.value)} placeholder={chiedo.cosa === 'rifiuto' ? 'In due parole, o lascia vuoto' : 'https://buy.stripe.com/…'}
                 onKeyDown={(e) => { if (e.key === 'Escape') setChiedo(null) }}
                 className="min-w-[260px] flex-1 rounded-lg border border-bordo bg-white px-3 py-1.5 text-sm outline-none focus:border-blu" />
          <button onClick={async () => {
            const q = righe.find((x) => x.id === chiedo.id)!
            if (chiedo.cosa === 'rifiuto') await segnaRifiutato(q, testoChiesto.trim())
            else { const r = await scrivi(q.id, { link_pagamento: testoChiesto.trim() || null }); if (r) setToast('Link salvato ✓') }
            setChiedo(null)
          }} className="rounded-full bg-blu px-4 py-1.5 text-sm font-bold text-white">Ok</button>
          <button onClick={() => setChiedo(null)} className="text-xs text-spento hover:text-inchiostro">annulla</button>
        </Card>
      )}

      {/* LA LISTA: una riga per preventivo, con l'esito a portata di mano */}
      {visibili.length === 0 ? (
        <Card><p className="px-4 py-8 text-center text-sm text-spento">
          {righe.length === 0 ? 'Nessun preventivo ancora. Il primo si fa con «Nuovo preventivo».' : t ? `Niente per «${cerca.trim()}»` : filtro === 'giro' ? 'Niente in giro: nessuno sta aspettando una risposta.' : 'Niente qui.'}
        </p></Card>
      ) : (
        <div className="space-y-2">
          {visibili.map((q) => {
            const n = nomi[q.prospect_id]
            const tono = STATI.find(([s]) => s === q.stato)?.[2] ?? ''
            const vecchio = scaduto(q)
            return (
              <Card key={q.id} className="p-3.5">
                <div className="flex flex-wrap items-center gap-x-3 gap-y-2">
                  <button onClick={() => onOpen(q.prospect_id)} className="flex min-w-0 items-center gap-2.5 text-left hover:text-navy">
                    {n && <Faccia p={n} size={32} />}
                    <span className="min-w-0">
                      <span className="block truncate text-[15px] font-bold">{nomeDi(q.prospect_id)}</span>
                      <span className="block truncate text-xs text-tenue">{q.titolo || 'preventivo'}</span>
                    </span>
                  </button>
                  <span className="text-[11px] font-semibold text-spento">{q.numero}</span>
                  <span className="ml-auto text-right">
                    {q.importo ? <span className="block text-[15px] font-extrabold tabular-nums">{euro(q.importo)}</span> : null}
                    {q.mensile ? <span className="block text-xs font-semibold tabular-nums text-tenue">{euro(q.mensile)} al mese</span> : null}
                  </span>
                  <span className={`rounded-md px-2 py-0.5 text-xs font-semibold ${q.pagato_il ? 'bg-green-100 text-green-900' : vecchio ? 'bg-amber-100 text-amber-900' : tono}`}>
                    {q.pagato_il ? `pagato il ${fmtDateShort(q.pagato_il)}` : vecchio ? `scaduto il ${fmtDateShort(q.valido_fino)}` : q.stato === 'inviato' ? `inviato il ${fmtDateShort(q.inviato_il)}` : q.stato === 'accettato' ? `accettato il ${fmtDateShort(q.accettato_il)}, da incassare` : q.stato === 'rifiutato' ? `rifiutato${q.motivo ? `: ${q.motivo}` : ''}` : 'bozza'}
                  </span>
                </div>
                <div className="mt-2.5 flex flex-wrap items-center gap-1.5">
                  {q.pdf_path
                    ? <button onClick={() => apri(q)} className="rounded-full border border-bordo bg-white px-3 py-1 text-xs font-bold text-navy hover:border-navy">Apri il PDF</button>
                    : <button onClick={() => apriModifica(q)} className="rounded-full border border-bordo bg-white px-3 py-1 text-xs font-bold text-navy hover:border-navy">Genera il PDF</button>}
                  {(q.stato === 'bozza' || q.stato === 'inviato') && <button onClick={() => apriModifica(q)} className="rounded-full border border-bordo bg-white px-3 py-1 text-xs font-semibold text-tenue hover:border-spento">modifica</button>}
                  {q.stato === 'bozza' && <button onClick={() => segnaInviato(q)} className="rounded-full bg-navy px-3 py-1 text-xs font-bold text-white hover:bg-blu">L'ho mandato</button>}
                  {q.stato === 'inviato' && <>
                    <button onClick={() => segnaAccettato(q)} className="rounded-full bg-green-700 px-3 py-1 text-xs font-bold text-white hover:bg-green-800">Ha accettato</button>
                    <button onClick={() => { setChiedo({ id: q.id, cosa: 'rifiuto' }); setTestoChiesto('') }} className="rounded-full border border-bordo bg-white px-3 py-1 text-xs font-semibold text-red-700 hover:border-red-300">Ha detto no</button>
                  </>}
                  {q.stato === 'accettato' && !q.pagato_il && <button onClick={() => segnaPagato(q)} className="rounded-full bg-green-700 px-3 py-1 text-xs font-bold text-white hover:bg-green-800">È stato pagato</button>}
                  {(q.stato === 'accettato' || q.stato === 'rifiutato') && !q.pagato_il && <button onClick={() => riapri(q)} className="rounded-full border border-bordo bg-white px-3 py-1 text-xs font-semibold text-tenue hover:border-spento">rimetti in attesa</button>}
                  <button onClick={() => copiaLink(q)} className="rounded-full border border-bordo bg-white px-3 py-1 text-xs font-semibold text-tenue hover:border-spento">{q.link_pagamento ? 'copia il link di pagamento' : 'metti il link di pagamento'}</button>
                  <button onClick={() => onOpen(q.prospect_id)} className="rounded-full border border-bordo bg-white px-3 py-1 text-xs font-semibold text-blu hover:border-blu">scheda</button>
                  {q.stato === 'bozza' && <button onClick={() => elimina(q)} className="ml-auto text-xs text-spento hover:text-red-700">elimina</button>}
                  {q.note && <span className="ml-auto text-xs text-spento">{q.note}</span>}
                </div>
              </Card>
            )
          })}
        </div>
      )}

      {/* GLI INCASSI DA STRIPE: Clara li legge ogni ora (stripe_sync.py) */}
      {incassi && filtro === 'tutti' && (
        <>
          <div className="pt-2">
            <h2 className="text-base font-extrabold text-navy">Incassi su Stripe</h2>
          </div>
          <Card>
            <div className="overflow-x-auto">
              <table className="w-full border-collapse">
                <thead>
                  <tr className="bg-velo/60 text-left text-[11px] font-bold uppercase tracking-wide text-tenue">
                    <th className="min-w-[110px] px-2 py-2">Quando</th>
                    <th className="min-w-[110px] px-2 py-2">Cosa</th>
                    <th className="min-w-[220px] px-2 py-2">Cliente</th>
                    <th className="min-w-[200px] px-2 py-2">Descrizione</th>
                    <th className="min-w-[100px] px-2 py-2 text-right">Importo</th>
                    <th className="min-w-[100px] px-2 py-2">Stato</th>
                    <th className="min-w-[160px] px-2 py-2">Azienda</th>
                  </tr>
                </thead>
                <tbody>
                  {incassi.map((i) => (
                    <tr key={i.id} className="border-b border-velo last:border-0 hover:bg-velo/30">
                      <td className="px-2 py-2 text-sm tabular-nums">{fmtDateShort(i.quando ? i.quando.slice(0, 10) : null)}</td>
                      <td className="px-2 py-2 text-sm">{GENERE[i.genere]}{i.ricorrenza ? <span className="text-spento"> / {i.ricorrenza === 'year' ? 'anno' : 'mese'}</span> : null}</td>
                      <td className="px-2 py-2">
                        <p className="text-sm font-semibold">{i.cliente_nome || <span className="text-spento">senza nome</span>}</p>
                        {i.cliente_email && <p className="text-[11px] text-spento">{i.cliente_email}</p>}
                      </td>
                      <td className="px-2 py-2 text-sm text-tenue">{i.descrizione || <span className="text-spento">senza descrizione</span>}</td>
                      <td className="px-2 py-2 text-right text-sm font-semibold tabular-nums">{i.importo.toLocaleString('it-IT', { minimumFractionDigits: 0, maximumFractionDigits: 2 })} {i.valuta.toUpperCase()}</td>
                      <td className="px-2 py-2"><span className={`rounded-md px-2 py-0.5 text-xs font-semibold ${tonoStato(i.stato)}`}>{statoIt(i.stato)}</span></td>
                      <td className="px-2 py-2 text-xs">
                        {i.prospect_id
                          ? <button onClick={() => onOpen(i.prospect_id!)} className="font-semibold hover:text-navy">{nomeDi(i.prospect_id)}{i.preventivo_id ? <span className="text-spento"> (preventivo pagato)</span> : null}</button>
                          : <span className="text-spento">non collegato</span>}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Card>
        </>
      )}

      {toast && (
        <div className="salta-su fixed bottom-20 left-1/2 z-40 -translate-x-1/2 rounded-full border border-green-200 bg-green-50 px-5 py-2.5 text-sm font-bold text-green-800 shadow-[0_8px_24px_rgba(16,24,40,0.2)] sm:bottom-6">
          {toast}
        </div>
      )}
    </div>
  )
}
