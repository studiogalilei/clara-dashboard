import { useEffect, useMemo, useRef, useState } from 'react'
import { supabase } from '../lib/supabase'
import { Card, Micro } from './ui'
import CercaAzienda, { CAMPI_AZIENDA, nomeAzienda } from './CercaAzienda'
import { nomeSalvato } from '../lib/profilo'
import { MODELLI, modelloDi, riempi, buchi, titoloDoc, type Dati } from '../lib/modelli'
import { caricaRisorse } from '../lib/preventivo'
import { nomeFile, type Documento, type Blocco } from '../lib/tono'

// L'EDITOR (Dre, 16/9): «un posto tipo Word col template già lì, collego
// l'azienda e i dati si riempiono, e se non c'è quello spazio resta
// fillabile e aggiungo altro; oppure un pulsante per farmi aiutare da Clara».
//
// Il foglio a schermo e' il PDF: stesso oggetto, stessi blocchi, stesso
// motore di stampa. Non c'e' un «anteprima»: quello che scrivi e' gia' la
// pagina. Si salva da solo, come Docs, e in alto si vede quando.
//
// Regole di casa rispettate: niente didascalie (i buchi si vedono da soli,
// in giallo), un solo blu per l'azione che conta, il documento largo quanto
// una pagina vera e non quanto lo schermo.

interface Props {
  id: number | null              // null = documento nuovo
  modello?: string
  prospectId?: string | null
  onEsci: () => void
}

interface Azienda { id: string; company: string | null; name: string | null; email: string }

const oggiIso = () => new Date().toISOString()

// ── l'area di testo che cresce con quello che scrivi ────────────────────
function Testo({ valore, su, classe, placeholder }: { valore: string; su: (v: string) => void; classe: string; placeholder?: string }) {
  const rif = useRef<HTMLTextAreaElement>(null)
  const misura = () => {
    const e = rif.current
    if (!e) return
    e.style.height = 'auto'
    e.style.height = `${e.scrollHeight}px`
  }
  useEffect(misura, [valore])
  return (
    <textarea
      ref={rif}
      rows={1}
      value={valore}
      placeholder={placeholder}
      onChange={(e) => { su(e.target.value); misura() }}
      className={`w-full resize-none overflow-hidden border-0 bg-transparent p-0 outline-none placeholder:text-spento ${classe}`}
    />
  )
}

// i buchi del modello restano visibili finche' non li riempi
const haBuco = (t: string) => /\[[^\]]{2,60}\]/.test(t)
// il buco si vede: sfondo ambra, e vince sul trasparente della base
const sfondoBuco = (t: string) => (haBuco(t) ? '!bg-amber-50' : '')

export default function Editor({ id, modello = 'bianco', prospectId = null, onEsci }: Props) {
  const [doc, setDoc] = useState<Documento | null>(null)
  const [rigaId, setRigaId] = useState<number | null>(id)
  const [azienda, setAzienda] = useState<Azienda | null>(null)
  const [cerco, setCerco] = useState(false)
  const [salvato, setSalvato] = useState<string | null>(null)
  const [salvo, setSalvo] = useState(false)
  const [guaio, setGuaio] = useState('')
  const [chiedo, setChiedo] = useState('')
  const [claraLavora, setClaraLavora] = useState(false)
  const [claraDice, setClaraDice] = useState<string | null>(null)
  const [menuBlocco, setMenuBlocco] = useState<number | null>(null)
  const [aggiungo, setAggiungo] = useState<number | null>(null)
  const primoGiro = useRef(true)

  // ── apertura: o si riprende un documento, o se ne inizia uno dal modello ──
  useEffect(() => {
    void (async () => {
      if (id) {
        const { data } = await supabase.from('documenti').select('*').eq('id', id).maybeSingle()
        const r = data as { doc: Documento; prospect_id: string | null } | null
        if (r) {
          setDoc(r.doc)
          if (r.prospect_id) {
            const { data: a } = await supabase.from('prospects').select(CAMPI_AZIENDA).eq('id', r.prospect_id).maybeSingle()
            if (a) setAzienda(a as unknown as Azienda)
          }
        }
        return
      }
      const m = modelloDi(modello) ?? MODELLI[MODELLI.length - 1]
      let dati: Dati = { io: nomeSalvato() }
      if (prospectId) {
        const { data: a } = await supabase.from('prospects').select(CAMPI_AZIENDA).eq('id', prospectId).maybeSingle()
        if (a) {
          const az = a as unknown as Azienda
          setAzienda(az)
          dati = { ...dati, azienda: nomeAzienda(az), email: az.email }
        }
      }
      setDoc(riempi(m.doc(), dati))
      // il gesto dopo e' sempre lo stesso: dire di chi e'. Si apre da sola
      if (!prospectId) setCerco(true)
    })()
  }, [id, modello, prospectId])

  // ── si salva da solo, come Docs ─────────────────────────────────────────
  useEffect(() => {
    if (!doc) return
    if (primoGiro.current) { primoGiro.current = false; return }
    const t = setTimeout(() => void salva(), 1200)
    return () => clearTimeout(t)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [doc, azienda])

  async function salva() {
    if (!doc) return
    setSalvo(true)
    const riga = {
      prospect_id: azienda?.id ?? null,
      modello,
      titolo: titoloDoc(doc),
      doc: doc as unknown as Record<string, unknown>,
      aggiornato_il: oggiIso(),
    }
    if (rigaId) {
      const { error } = await supabase.from('documenti').update(riga).eq('id', rigaId)
      if (error) { setGuaio(`Non si salva: ${error.message}`); setSalvo(false); return }
    } else {
      const { data, error } = await supabase.from('documenti').insert(riga).select('id').single()
      if (error || !data) { setGuaio(`Non si salva: ${error?.message ?? 'nessuna riga'}`); setSalvo(false); return }
      setRigaId((data as { id: number }).id)
    }
    setGuaio('')
    setSalvo(false)
    setSalvato(new Date().toLocaleTimeString('it-IT', { hour: '2-digit', minute: '2-digit' }))
  }

  // ── i blocchi ───────────────────────────────────────────────────────────
  const cambia = (i: number, b: Blocco) => setDoc((d) => (d ? { ...d, blocchi: d.blocchi.map((x, k) => (k === i ? b : x)) } : d))
  const togli = (i: number) => setDoc((d) => (d ? { ...d, blocchi: d.blocchi.filter((_, k) => k !== i) } : d))
  const sposta = (i: number, di: number) => setDoc((d) => {
    if (!d) return d
    const k = i + di
    if (k < 0 || k >= d.blocchi.length) return d
    const b = [...d.blocchi]
    const [x] = b.splice(i, 1)
    b.splice(k, 0, x)
    return { ...d, blocchi: b }
  })
  const infila = (i: number, b: Blocco) => setDoc((d) => {
    if (!d) return d
    const blocchi = [...d.blocchi]
    blocchi.splice(i + 1, 0, b)
    return { ...d, blocchi }
  })

  const NUOVI: Array<[string, () => Blocco]> = [
    ['Titolo', () => ({ tipo: 'h2', testo: 'Titolo' })],
    ['Testo', () => ({ tipo: 'p', testo: '' })],
    ['Elenco', () => ({ tipo: 'elenco', voci: ['', ''] })],
    ['Riquadro', () => ({ tipo: 'riquadro', titolo: 'IN BREVE', voci: [''] })],
    ['Tabella', () => ({ tipo: 'tabella', colonne: [{ testo: 'Voce', larghezza: 60 }, { testo: 'Quando', larghezza: 40 }], righe: [[{ testo: '' }, { testo: '' }]] })],
    ['Numeri', () => ({ tipo: 'numeri', voci: [{ valore: '0', etichetta: 'ETICHETTA' }] })],
    ['Pagina nuova', () => ({ tipo: 'pagina' })],
  ]

  function disegna(b: Blocco, i: number) {
    const set = (x: Blocco) => cambia(i, x)
    if (b.tipo === 'kicker') return <Testo valore={b.testo} su={(v) => set({ ...b, testo: v })} classe={`text-[11px] font-bold uppercase tracking-[0.12em] text-blu ${sfondoBuco(b.testo)}`} />
    if (b.tipo === 'h1') return <Testo valore={b.testo} su={(v) => set({ ...b, testo: v })} classe={`text-[27px] font-extrabold leading-tight text-navy ${sfondoBuco(b.testo)}`} />
    if (b.tipo === 'h2') return <Testo valore={b.testo} su={(v) => set({ ...b, testo: v })} classe={`text-[17px] font-extrabold text-navy ${sfondoBuco(b.testo)}`} />
    if (b.tipo === 'p') return <Testo valore={b.testo} su={(v) => set({ ...b, testo: v })} placeholder="Scrivi…" classe={`text-[14.5px] leading-relaxed ${b.piccolo ? 'text-tenue' : ''} ${sfondoBuco(b.testo)}`} />
    if (b.tipo === 'spazio') return <div className="h-4 rounded transition-colors group-hover:bg-velo/70" />
    if (b.tipo === 'pagina') return <div className="flex items-center gap-2 py-1 text-[11px] font-bold uppercase tracking-wide text-spento"><span className="h-px flex-1 bg-bordo" />pagina nuova<span className="h-px flex-1 bg-bordo" /></div>
    if (b.tipo === 'elenco') return (
      <ul className="space-y-1">
        {b.voci.map((v, k) => (
          <li key={k} className="flex gap-2">
            <span className="mt-[9px] h-1.5 w-1.5 shrink-0 rounded-[2px] bg-blu" />
            <Testo valore={v} placeholder="voce" classe={`text-[14.5px] leading-relaxed ${sfondoBuco(v)}`}
                   su={(x) => set({ ...b, voci: b.voci.map((y, j) => (j === k ? x : y)) })} />
            <button onClick={() => set({ ...b, voci: b.voci.filter((_, j) => j !== k) })}
                    className="mt-1 shrink-0 text-xs text-spento opacity-0 transition-opacity hover:text-red-700 group-hover:opacity-100">×</button>
          </li>
        ))}
        <li><button onClick={() => set({ ...b, voci: [...b.voci, ''] })} className="text-xs font-semibold text-blu hover:underline">+ voce</button></li>
      </ul>
    )
    if (b.tipo === 'riquadro') return (
      <div className="rounded-xl bg-velo px-4 py-3">
        <Testo valore={b.titolo} su={(v) => set({ ...b, titolo: v })} classe="text-[11px] font-bold uppercase tracking-[0.1em] text-blu" />
        <ul className="mt-1.5 space-y-1">
          {b.voci.map((v, k) => (
            <li key={k} className="flex gap-2">
              <span className="mt-[9px] h-1.5 w-1.5 shrink-0 rounded-[2px] bg-blu" />
              <Testo valore={v} placeholder="voce" classe={`text-[14.5px] leading-relaxed ${sfondoBuco(v)}`}
                     su={(x) => set({ ...b, voci: b.voci.map((y, j) => (j === k ? x : y)) })} />
            </li>
          ))}
          <li><button onClick={() => set({ ...b, voci: [...b.voci, ''] })} className="text-xs font-semibold text-blu hover:underline">+ voce</button></li>
        </ul>
      </div>
    )
    if (b.tipo === 'anagrafica') return (
      <div className="grid gap-4 sm:grid-cols-3">
        {b.colonne.map((c, k) => (
          <div key={k}>
            <Testo valore={c.titolo} classe="text-[11px] font-bold uppercase tracking-[0.1em] text-blu"
                   su={(v) => set({ ...b, colonne: b.colonne.map((x, j) => (j === k ? { ...x, titolo: v } : x)) })} />
            {c.righe.map((r, j) => (
              <Testo key={j} valore={r} classe={`text-[14px] ${sfondoBuco(r)}`}
                     su={(v) => set({ ...b, colonne: b.colonne.map((x, q) => (q === k ? { ...x, righe: x.righe.map((y, z) => (z === j ? v : y)) } : x)) })} />
            ))}
          </div>
        ))}
      </div>
    )
    if (b.tipo === 'tabella') return (
      <div className="overflow-x-auto">
        <table className="w-full border-collapse">
          <thead>
            <tr>{b.colonne.map((c, k) => (
              <th key={k} className="border-b border-navy/60 pb-1 pr-3 text-left">
                <Testo valore={c.testo} classe="text-[11px] font-bold uppercase tracking-[0.1em] text-blu"
                       su={(v) => set({ ...b, colonne: b.colonne.map((x, j) => (j === k ? { ...x, testo: v } : x)) })} />
              </th>
            ))}</tr>
          </thead>
          <tbody>
            {b.righe.map((r, k) => (
              <tr key={k} className="border-b border-velo align-top">
                {r.map((c, j) => (
                  <td key={j} className="py-2 pr-3">
                    <Testo valore={c.testo} placeholder="…" classe={`text-[14px] ${c.forte ? 'font-bold' : ''} ${sfondoBuco(c.testo)}`}
                           su={(v) => set({ ...b, righe: b.righe.map((y, z) => (z === k ? y.map((x, q) => (q === j ? { ...x, testo: v } : x)) : y)) })} />
                    {c.sotto !== undefined && (
                      <Testo valore={c.sotto} classe="text-[12px] text-tenue"
                             su={(v) => set({ ...b, righe: b.righe.map((y, z) => (z === k ? y.map((x, q) => (q === j ? { ...x, sotto: v } : x)) : y)) })} />
                    )}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
        <button onClick={() => set({ ...b, righe: [...b.righe, b.colonne.map(() => ({ testo: '' }))] })}
                className="mt-1.5 text-xs font-semibold text-blu hover:underline">+ riga</button>
      </div>
    )
    if (b.tipo === 'numeri') return (
      <div className="flex flex-wrap gap-6">
        {b.voci.map((v, k) => (
          <div key={k} className="min-w-[110px]">
            <Testo valore={v.valore} classe="text-[30px] font-extrabold leading-none text-navy"
                   su={(x) => set({ ...b, voci: b.voci.map((y, j) => (j === k ? { ...y, valore: x } : y)) })} />
            <Testo valore={v.etichetta} classe="mt-1 text-[11px] font-bold uppercase tracking-[0.1em] text-blu"
                   su={(x) => set({ ...b, voci: b.voci.map((y, j) => (j === k ? { ...y, etichetta: x } : y)) })} />
          </div>
        ))}
        <button onClick={() => set({ ...b, voci: [...b.voci, { valore: '0', etichetta: 'ETICHETTA' }] })}
                className="self-end text-xs font-semibold text-blu hover:underline">+ numero</button>
      </div>
    )
    if (b.tipo === 'due_colonne') return (
      <div className="grid gap-5 sm:grid-cols-2">
        {([['sinistra', b.sinistra], ['destra', b.destra]] as const).map(([lato, c]) => (
          <div key={lato}>
            <Testo valore={c.titolo} classe="text-[11px] font-bold uppercase tracking-[0.1em] text-blu"
                   su={(v) => set({ ...b, [lato]: { ...c, titolo: v } } as Blocco)} />
            <ul className="mt-1.5 space-y-1">
              {c.voci.map((v, k) => (
                <li key={k} className="flex gap-2">
                  <span className="mt-[9px] h-1.5 w-1.5 shrink-0 rounded-[2px] bg-blu" />
                  <Testo valore={v} classe={`text-[14px] leading-relaxed ${sfondoBuco(v)}`}
                         su={(x) => set({ ...b, [lato]: { ...c, voci: c.voci.map((y, j) => (j === k ? x : y)) } } as Blocco)} />
                </li>
              ))}
            </ul>
          </div>
        ))}
      </div>
    )
    if (b.tipo === 'tappe') return (
      <div className="grid gap-4 sm:grid-cols-3">
        {b.tappe.map((t, k) => (
          <div key={k}>
            <Testo valore={t.quando} classe="text-[11px] font-bold uppercase tracking-[0.1em] text-blu"
                   su={(v) => set({ ...b, tappe: b.tappe.map((x, j) => (j === k ? { ...x, quando: v } : x)) })} />
            <Testo valore={t.titolo} classe="text-[15px] font-bold text-navy"
                   su={(v) => set({ ...b, tappe: b.tappe.map((x, j) => (j === k ? { ...x, titolo: v } : x)) })} />
            <Testo valore={t.testo} classe={`text-[13.5px] leading-relaxed ${sfondoBuco(t.testo)}`}
                   su={(v) => set({ ...b, tappe: b.tappe.map((x, j) => (j === k ? { ...x, testo: v } : x)) })} />
          </div>
        ))}
      </div>
    )
    return null
  }

  // ── Clara scrive dentro il documento ────────────────────────────────────
  async function chiediAClara() {
    if (!doc || claraLavora) return
    setClaraLavora(true)
    setClaraDice(null)
    try {
      const { data, error } = await supabase.functions.invoke('documento', {
        body: { doc, prospect_id: azienda?.id ?? null, richiesta: chiedo.trim() },
      })
      if (error) throw new Error(error.message)
      const r = (data ?? {}) as { doc?: Documento; errore?: string; detto?: string }
      if (r.errore) { setClaraDice(r.errore); return }
      if (r.doc?.blocchi?.length) {
        setDoc(r.doc)
        setChiedo('')
        setClaraDice(r.detto ?? 'Fatto. Guarda e correggi quello che non ti torna.')
      } else setClaraDice('Non sono riuscita a scrivere niente di sensato, riprova a dirmelo diverso.')
    } catch (e) {
      setClaraDice(`Non ci sono riuscita: ${String(e).slice(0, 140)}`)
    } finally {
      setClaraLavora(false)
    }
  }

  async function scaricaPdf() {
    if (!doc) return
    const { generaPdf } = await import('../lib/documento')
    const bytes = await generaPdf(doc, await caricaRisorse())
    const blob = new Blob([bytes as BlobPart], { type: 'application/pdf' })
    const a = document.createElement('a')
    a.href = URL.createObjectURL(blob)
    a.download = nomeFile(titoloDoc(doc), azienda ? nomeAzienda(azienda as never) : '')
    a.click()
    setTimeout(() => URL.revokeObjectURL(a.href), 4000)
  }

  const quantiBuchi = useMemo(() => (doc ? buchi(doc) : 0), [doc])

  if (!doc) return <p className="px-1 py-8 text-sm text-spento">Apro il documento…</p>

  return (
    <div className="space-y-4">
      {/* testata: da dove torno, come si chiama, dov'e' finito */}
      <div className="flex flex-wrap items-center gap-3">
        <button onClick={onEsci} className="text-sm font-semibold text-blu hover:underline">‹ Preventivi</button>
        <span className="text-sm text-spento">
          {salvo ? 'salvo…' : salvato ? `salvato alle ${salvato}` : 'non ancora salvato'}
        </span>
        {quantiBuchi > 0 && (
          <span className="rounded-full bg-amber-50 px-2.5 py-0.5 text-[11px] font-bold text-amber-800">
            {quantiBuchi} da riempire
          </span>
        )}
        <div className="ml-auto flex items-center gap-2">
          <button onClick={() => void scaricaPdf()}
                  className="rounded-full border border-bordo px-3.5 py-1.5 text-xs font-bold text-navy hover:border-navy">
            Scarica il PDF
          </button>
        </div>
      </div>

      {guaio && <p className="rounded-xl border border-red-200 bg-red-50 px-4 py-2 text-sm font-semibold text-red-800">{guaio}</p>}

      <div className="lg:grid lg:grid-cols-[minmax(0,1fr)_300px] lg:items-start lg:gap-5">
        {/* il foglio: largo come una pagina vera, non come lo schermo */}
        <Card className="px-6 py-8 sm:px-10 sm:py-12">
          <div className="mx-auto max-w-[640px] space-y-3">
            {/* LA COPERTINA: e' la prima cosa che vede il cliente, quindi si
                scrive qui e non in un pannello a parte. Si vede com'e': blu
                pieno, come stampata */}
            {doc.copertina && (
              <div className="mb-6 rounded-xl bg-navy px-6 py-7 text-white">
                <Testo valore={doc.copertina.occhiello} classe="text-[11px] font-bold uppercase tracking-[0.14em] text-white/70"
                       su={(v) => setDoc((d) => (d?.copertina ? { ...d, copertina: { ...d.copertina, occhiello: v } } : d))} />
                <Testo valore={doc.copertina.titolo} classe="mt-1 text-[26px] font-extrabold leading-tight text-white"
                       su={(v) => setDoc((d) => (d?.copertina ? { ...d, copertina: { ...d.copertina, titolo: v } } : d))} />
                <Testo valore={doc.copertina.sottotitolo ?? ''} placeholder="una riga che dice cosa c'è dentro"
                       classe="mt-1 text-[13.5px] text-white/80"
                       su={(v) => setDoc((d) => (d?.copertina ? { ...d, copertina: { ...d.copertina, sottotitolo: v } } : d))} />
                <p className="mt-3 text-[11px] text-white/60">
                  {[doc.copertina.cliente, doc.copertina.riferimento, doc.copertina.data].filter(Boolean).join(', ')}
                </p>
              </div>
            )}
            {doc.blocchi.map((b, i) => (
              <div key={i} className="group relative">
                <div className="absolute -left-8 top-0 hidden gap-0.5 group-hover:flex lg:flex lg:opacity-0 lg:group-hover:opacity-100">
                  <button onClick={() => setMenuBlocco(menuBlocco === i ? null : i)} aria-label="Altro"
                          className="rounded px-1 text-spento hover:bg-velo hover:text-navy">⋯</button>
                </div>
                {menuBlocco === i && (
                  <div className="absolute -left-4 top-6 z-20 w-36 overflow-hidden rounded-lg border border-bordo bg-white text-left shadow-lg"
                       onMouseLeave={() => setMenuBlocco(null)}>
                    <button onClick={() => { sposta(i, -1); setMenuBlocco(null) }} className="block w-full px-3 py-1.5 text-xs hover:bg-velo">Sposta su</button>
                    <button onClick={() => { sposta(i, 1); setMenuBlocco(null) }} className="block w-full px-3 py-1.5 text-xs hover:bg-velo">Sposta giù</button>
                    <button onClick={() => { togli(i); setMenuBlocco(null) }} className="block w-full px-3 py-1.5 text-xs text-red-700 hover:bg-red-50">Togli</button>
                  </div>
                )}
                {disegna(b, i)}
                {/* il piu' fra un blocco e l'altro, come su Docs */}
                <div className="relative h-2">
                  <button onClick={() => setAggiungo(aggiungo === i ? null : i)}
                          className="absolute left-1/2 top-1/2 h-5 w-5 -translate-x-1/2 -translate-y-1/2 rounded-full border border-bordo bg-white text-xs font-bold leading-none text-tenue opacity-0 transition-opacity hover:border-blu hover:text-blu group-hover:opacity-100">
                    +
                  </button>
                  {aggiungo === i && (
                    <div className="absolute left-1/2 top-6 z-20 w-40 -translate-x-1/2 overflow-hidden rounded-lg border border-bordo bg-white shadow-lg"
                         onMouseLeave={() => setAggiungo(null)}>
                      {NUOVI.map(([nome, fai]) => (
                        <button key={nome} onClick={() => { infila(i, fai()); setAggiungo(null) }}
                                className="block w-full px-3 py-1.5 text-left text-xs hover:bg-velo">{nome}</button>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>
        </Card>

        {/* la colonna di lato: di chi e', e Clara */}
        <div className="mt-4 space-y-3 lg:mt-0">
          <Card className="p-4">
            <Micro>Azienda</Micro>
            {azienda && !cerco ? (
              <div className="mt-1.5 flex items-center gap-2">
                <p className="text-sm font-bold">{nomeAzienda(azienda as never)}</p>
                <button onClick={() => setCerco(true)} className="text-xs font-semibold text-blu hover:underline">cambia</button>
              </div>
            ) : (
              <div className="mt-1.5">
                <CercaAzienda
                  dentro
                  placeholder="di che azienda è?"
                  onScegli={(a) => {
                    const az = a as unknown as Azienda
                    setAzienda(az)
                    setCerco(false)
                    setDoc((d) => (d ? riempi(d, { azienda: nomeAzienda(az as never), email: az.email, io: nomeSalvato() }) : d))
                  }}
                />
              </div>
            )}
            {azienda && (
              <p className="mt-1.5 text-[11px] text-spento">
                Il documento resta nella sua cartella, e lo trovate tutti da lì.
              </p>
            )}
          </Card>

          <Card className="p-4">
            <Micro>Chiedi a Clara</Micro>
            <textarea
              value={chiedo}
              onChange={(e) => setChiedo(e.target.value)}
              onKeyDown={(e) => { if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) void chiediAClara() }}
              placeholder="Scrivi la proposta con quello che si sono detti in call…"
              className="mt-1.5 min-h-20 w-full rounded-lg border border-bordo px-2.5 py-2 text-[13px] outline-none focus:border-blu"
            />
            <button onClick={() => void chiediAClara()} disabled={claraLavora}
                    className="mt-2 w-full rounded-full bg-blu px-4 py-2 text-xs font-bold text-white hover:bg-blu-scuro disabled:opacity-40">
              {claraLavora ? 'Sta scrivendo…' : 'Scrivilo con me'}
            </button>
            {claraDice && <p className="mt-2 text-[12px] leading-relaxed text-tenue">{claraDice}</p>}
            {azienda && !claraDice && (
              <p className="mt-2 text-[11px] leading-relaxed text-spento">
                Legge le call, le mail e la scheda di {nomeAzienda(azienda as never)} prima di scrivere.
              </p>
            )}
          </Card>
        </div>
      </div>
    </div>
  )
}
