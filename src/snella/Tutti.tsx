// TUTTI (19/10/2026): il foglio con tutti i prospect e il loro stato.
// Dre, 19/10: «io non ho un luogo dove vedere tutti quanti». Lead tiene chi ha risposto negli
// ultimi 60 giorni (il lavoro di adesso); qui ci sono tutti: di base chi ha risposto almeno una
// volta, con un interruttore anche chi non ha mai risposto («Nessuna risposta»). Gli stati sono i 12
// di Dre (19/10, stati.json), con responsabile, prossima azione e data. L'ultima novita' in cima
// (la sua ultima risposta o la nostra ultima mail, la piu' recente).
// Sul computer una tabella vera, come un foglio; sul telefono una lista compatta. Un tocco apre la
// scheda. Il telefono non scarica 13.500 righe: il database filtra, conta e manda 80 righe alla
// volta (supabase/schema_v92.sql, snella_tutti_pagina); le altre arrivano scorrendo.
import { useCallback, useEffect, useLayoutEffect, useRef, useState } from 'react'
import { STATI, leggiNoteFollowUp, leggiTutti, type FiltriTutti, type PaginaTutti, type RigaTutti } from './dati'
import { dataCorta, giornoRoma, mossaDiRiga, nomeStato, numero, quando, tonoStato, type NotaFollowUp } from './regole'
import { Bottone, Carico, Errore, Icona, PillolaStato, Vuoto } from './pezzi'
import { TONO } from './toni'

const PASSO = 80
const BLOCCO = 200                     // il database non manda piu' di 200 righe per volta

type Conti = Pick<PaginaTutti, 'totale' | 'stati' | 'campagne'>

// tornando dalla scheda la lista riappare subito com'era (righe, filtri, punto in cui eri) e
// intanto si rilegge: lo stato appena cambiato nella scheda si vede senza ricaricare a mano
let memoria: { chiave: string; righe: RigaTutti[]; conti: Conti; y: number } | null = null

function ricorda(k: string, v?: string): string | null {
  try {
    if (v === undefined) return sessionStorage.getItem(k)
    sessionStorage.setItem(k, v)
  } catch { /* in privato non si ricorda: pazienza */ }
  return null
}

function filtriIniziali(): FiltriTutti {
  try {
    const f = JSON.parse(ricorda('snella-tutti') ?? 'null') as Partial<FiltriTutti> | null
    if (f) return { q: f.q ?? '', stato: nomeStato(f.stato), campagna: f.campagna ?? null, mai: Boolean(f.mai) }
  } catch { /* filtri rovinati: si riparte puliti */ }
  return { q: '', stato: null, campagna: null, mai: false }
}

const chiaveDi = (f: FiltriTutti) => JSON.stringify([f.q.trim(), f.stato, f.campagna, f.mai])

/** Le righe senza doppioni (una risposta nuova fra due pagine sposta l'ordine). */
function unisci(a: RigaTutti[], b: RigaTutti[]): RigaTutti[] {
  const visti = new Set(a.map((r) => r.prospect_id))
  return [...a, ...b.filter((r) => !visti.has(r.prospect_id))]
}

export default function Tutti({ apri }: { apri: (id: string) => void }) {
  const [filtri, setFiltri] = useState<FiltriTutti>(filtriIniziali)
  const [scritto, setScritto] = useState(filtri.q)          // la ricerca mentre la scrivi
  const chiave = chiaveDi(filtri)
  const dalla = memoria && memoria.chiave === chiave ? memoria : null
  const [righe, setRighe] = useState<RigaTutti[]>(dalla?.righe ?? [])
  const [conti, setConti] = useState<Conti>(dalla?.conti ?? {})
  const [caricando, setCaricando] = useState(!dalla)
  const [altre, setAltre] = useState(false)
  const [errore, setErrore] = useState<string | null>(null)
  // 22/10: cosa ha in programma il sistema per chi ha l'analisi (scripts/followup.py); senza, la lista resta com'era
  const [note, setNote] = useState<NoteFU>({})
  useEffect(() => { void leggiNoteFollowUp().then(setNote).catch(() => setNote({})) }, [])
  const giro = useRef(0)
  const stato = useRef({ righe, conti, chiave })
  stato.current = { righe, conti, chiave }

  // la ricerca parte quando smetti di scrivere
  useEffect(() => {
    if (scritto === filtri.q) return
    const t = window.setTimeout(() => setFiltri((f) => ({ ...f, q: scritto })), 300)
    return () => window.clearTimeout(t)
  }, [scritto, filtri.q])

  useEffect(() => { ricorda('snella-tutti', JSON.stringify(filtri)) }, [filtri])

  /** Rilegge dal database le righe gia' mostrate (o la prima pagina) e i conteggi. */
  const rileggi = useCallback(async (f: FiltriTutti, quante: number) => {
    const mio = ++giro.current
    try {
      const n = Math.max(PASSO, Math.min(quante, 1000))
      const pezzi = await Promise.all(Array.from({ length: Math.ceil(n / BLOCCO) }, (_, i) =>
        leggiTutti(f, i * BLOCCO, Math.min(BLOCCO, n - i * BLOCCO), i === 0)))
      if (mio !== giro.current) return
      setRighe(pezzi.reduce<RigaTutti[]>((acc, p) => unisci(acc, p.righe), []))
      setConti({ totale: pezzi[0].totale, stati: pezzi[0].stati, campagne: pezzi[0].campagne })
      setErrore(null)
    } catch (e) {
      if (mio === giro.current) setErrore(e instanceof Error ? e.message : String(e))
    } finally {
      if (mio === giro.current) setCaricando(false)
    }
  }, [])

  // filtri nuovi: da capo. Ritorno dalla scheda con gli stessi filtri: si rilegge quello che c'era.
  const primo = useRef(true)
  useEffect(() => {
    if (primo.current && dalla) { primo.current = false; void rileggi(filtri, dalla.righe.length); return }
    primo.current = false
    setCaricando(true); setRighe([])
    void rileggi(filtri, PASSO)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [chiave])

  // torni sull'app, la rete torna, ogni 2 minuti mentre la guardi: si rilegge quello che vedi
  useEffect(() => {
    const ora = () => { if (document.visibilityState === 'visible') void rileggi(filtri, stato.current.righe.length) }
    document.addEventListener('visibilitychange', ora)
    window.addEventListener('online', ora)
    const t = window.setInterval(ora, 120_000)
    return () => { document.removeEventListener('visibilitychange', ora); window.removeEventListener('online', ora); window.clearInterval(t) }
  }, [filtri, rileggi])

  // il punto in cui eri, tornando dalla scheda
  useLayoutEffect(() => {
    if (dalla?.y) window.scrollTo(0, dalla.y)
    return () => { memoria = { ...stato.current, y: window.scrollY } }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const totale = conti.totale ?? null
  const finite = totale != null && righe.length >= totale

  const ancora = useCallback(async () => {
    if (altre || finite) return
    setAltre(true)
    const mio = giro.current
    try {
      const p = await leggiTutti(filtri, stato.current.righe.length, PASSO, false)
      if (mio === giro.current) setRighe((r) => unisci(r, p.righe))
    } catch (e) {
      if (mio === giro.current) setErrore(e instanceof Error ? e.message : String(e))
    } finally {
      setAltre(false)
    }
  }, [altre, finite, filtri])

  // le righe dopo arrivano da sole quando arrivi in fondo (il bottone resta, per chi non scorre)
  const fondo = useRef<HTMLDivElement>(null)
  useEffect(() => {
    const el = fondo.current
    if (!el || finite || caricando) return
    const o = new IntersectionObserver((e) => { if (e[0]?.isIntersecting) void ancora() }, { rootMargin: '600px' })
    o.observe(el)
    return () => o.disconnect()
  }, [ancora, finite, caricando])

  const largo = useLargo()

  function cambia(f: Partial<FiltriTutti>) { setFiltri((x) => ({ ...x, ...f })) }

  const quanti = conti.stati ? Object.values(conti.stati).reduce((a, b) => a + b, 0) : null
  const altriStati = Object.keys(conti.stati ?? {}).filter((k) => !(STATI as readonly string[]).includes(k)).sort()
  const filtriStato: Array<string | null> = [null, ...STATI, ...altriStati]
  const filtrato = Boolean(filtri.q.trim() || filtri.stato || filtri.campagna !== null)

  return (
    <div>
      <div className="flex flex-col gap-3 xl:flex-row xl:items-center">
        <div className="relative xl:w-[360px]">
          <label htmlFor="cerca-tutti" className="sr-only">Cerca per azienda, persona o mail</label>
          <Icona nome="cerca" className="pointer-events-none absolute left-3.5 top-1/2 h-5 w-5 -translate-y-1/2 text-tenue" />
          <input id="cerca-tutti" type="search" value={scritto} placeholder="Cerca azienda, persona o mail" autoComplete="off"
                 onChange={(e) => setScritto(e.target.value)}
                 className="h-12 w-full rounded-full border border-bordo bg-white pl-11 pr-4 text-[16px] text-inchiostro outline-none placeholder:text-spento focus:border-blu-scuro" />
        </div>
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
          <label htmlFor="campagna-tutti" className="sr-only">Campagna</label>
          <select id="campagna-tutti" value={filtri.campagna ?? '*'} onChange={(e) => cambia({ campagna: e.target.value === '*' ? null : e.target.value })}
                  className="h-11 min-w-0 max-w-full rounded-full border border-bordo bg-white px-4 text-[15px] text-inchiostro outline-none focus:border-blu-scuro sm:max-w-[320px]">
            <option value="*">Tutte le campagne</option>
            {(conti.campagne ?? []).map((c) => <option key={c.nome} value={c.nome}>{c.nome || 'Senza campagna'} ({numero(c.n)})</option>)}
            {filtri.campagna !== null && !(conti.campagne ?? []).some((c) => c.nome === filtri.campagna) && (
              <option value={filtri.campagna}>{filtri.campagna || 'Senza campagna'} (0)</option>
            )}
          </select>
          <label className="inline-flex min-h-11 cursor-pointer select-none items-center gap-2.5 text-[15px] text-inchiostro">
            <input type="checkbox" checked={filtri.mai} onChange={(e) => cambia({ mai: e.target.checked })}
                   className="h-5 w-5 shrink-0 accent-blu-scuro" />
            Mostra anche chi non ha mai risposto
          </label>
        </div>
      </div>

      <div role="group" aria-label="Filtra per stato" className="-mx-4 mt-3 flex gap-2 overflow-x-auto px-4 pb-1 lg:mx-0 lg:flex-wrap lg:px-0">
        {filtriStato.map((s) => {
          const n = s === null ? quanti : conti.stati?.[s] ?? (conti.stati ? 0 : null)
          const su = filtri.stato === s
          if (s !== null && s !== filtri.stato && n === 0) return null
          return (
            <button key={s ?? '*'} onClick={() => cambia({ stato: s })} aria-pressed={su}
                    className={`inline-flex min-h-11 shrink-0 items-center gap-1.5 whitespace-nowrap rounded-full border px-3.5 text-[14px] font-semibold transition-colors ${su ? 'border-blu-scuro bg-blu-scuro text-white' : 'border-bordo bg-white text-inchiostro hover:border-tenue'}`}>
              {s !== null && tonoStato(s) !== 'neutro' && <span aria-hidden="true" className={`h-2 w-2 rounded-full ${TONO[tonoStato(s)].segno} ${su ? 'ring-2 ring-white' : ''}`} />}
              {s ?? 'Tutti gli stati'}{n != null && <span className={su ? 'text-white/85' : 'text-tenue'}>{numero(n)}</span>}
            </button>
          )
        })}
      </div>

      <div className="mt-4">
        {caricando && !righe.length ? <Carico righe={8} etichetta="Carico i prospect" />
          : errore && !righe.length ? <Errore testo={errore} riprova={() => void rileggi(filtri, PASSO)} />
            : !righe.length ? (
              <Vuoto>
                {filtri.q.trim() ? `Nessuno trovato per «${filtri.q.trim()}»` : 'Nessuno qui'}
                {filtri.stato ? ` in ${filtri.stato}` : ''}{filtri.campagna !== null ? ' in questa campagna' : ''}
                {!filtri.mai ? ' fra chi ha risposto almeno una volta.' : '.'}
                {!filtri.mai && <> <button onClick={() => cambia({ mai: true })} className="font-semibold text-blu-scuro underline">Cerca anche fra chi non ha mai risposto</button>.</>}
                {filtri.mai && filtrato && <> <button onClick={() => { setScritto(''); setFiltri({ q: '', stato: null, campagna: null, mai: true }) }} className="font-semibold text-blu-scuro underline">Togli i filtri</button>.</>}
              </Vuoto>
            ) : (
              <>
                <p aria-live="polite" className="mb-2 text-[14px] text-tenue">
                  {totale != null && <b className="font-semibold text-inchiostro">{numero(totale)} {totale === 1 ? 'prospect' : 'prospect'}</b>}
                  {totale != null && righe.length < totale && <>, ne vedi {numero(righe.length)}</>}
                  {totale != null ? '. ' : ''}L'ultima novità in cima.
                  <span className="hidden lg:inline"> In grigio responsabile e prossima azione di default dello stato, in nero quelli scritti da te</span>
                </p>
                {largo ? <Tabella righe={righe} apri={apri} note={note} /> : <Lista righe={righe} apri={apri} note={note} />}
                <div ref={fondo} className="mt-3 text-center">
                  {errore && <p role="alert" className="mb-2 text-[14px] font-semibold text-no-testo">Non riesco a leggere le altre righe: {errore}</p>}
                  {!finite && (
                    <Bottone onClick={() => void ancora()} disabled={altre}>
                      {altre ? 'Carico…' : `Mostra altri ${numero(Math.min(PASSO, (totale ?? righe.length + PASSO) - righe.length))}`}
                    </Bottone>
                  )}
                </div>
              </>
            )}
      </div>
    </div>
  )
}

/** Il computer (da 1024 punti, come il menu a sinistra): la tabella; sotto, la lista. Una sola
 *  delle due nel documento: sul telefono le righe non si disegnano due volte. */
function useLargo(): boolean {
  const mq = '(min-width: 1024px)'
  const [largo, setLargo] = useState(() => typeof window !== 'undefined' && window.matchMedia(mq).matches)
  useEffect(() => {
    const m = window.matchMedia(mq)
    const cambia = () => setLargo(m.matches)
    m.addEventListener('change', cambia)
    return () => m.removeEventListener('change', cambia)
  }, [])
  return largo
}

/** La data della prossima azione: «Richiamare il 21 ott» se Dre ha detto di richiamare, se no la data. */
function quandoMossa(r: RigaTutti): string {
  if (r.richiamare_il) return `Richiamare il ${giorno(r.richiamare_il)}`
  return r.mossa_il ? giorno(r.mossa_il) : ''
}

type NoteFU = Record<string, NotaFollowUp>

/** La riga con la prossima azione giusta: per chi e' in «Analisi inviata» quella del sistema (22/10). */
function conNota(r: RigaTutti, note: NoteFU): RigaTutti {
  const m = mossaDiRiga(r, note[r.prospect_id])
  return m.mossa === r.mossa && m.il === r.mossa_il ? r : { ...r, mossa: m.mossa, mossa_il: m.il }
}

/** «21 ott»; con l'anno se non e' quest'anno («30 dic 25»): nel foglio ci sono date vecchie. */
function giorno(d: string): string {
  const anno = d.slice(0, 4)
  return anno === giornoRoma().slice(0, 4) ? dataCorta(d) : `${dataCorta(d)} ${anno.slice(2)}`
}

/** L'ultima novita' (quella che ordina la lista): la sua ultima risposta o la nostra ultima mail,
 *  la piu' recente, con chi l'ha scritta. Senza, «mai». */
function Novita({ r }: { r: RigaTutti }) {
  if (!r.novita) return <span className="text-spento">mai risposto</span>
  const noi = Boolean(r.ultima_nostra && (!r.ultima_risposta || r.ultima_nostra > r.ultima_risposta))
  return (
    <span title={[r.ultima_risposta && `Sua ultima risposta: ${quando(r.ultima_risposta)}`, r.ultima_nostra && `Nostra ultima mail: ${quando(r.ultima_nostra)}`].filter(Boolean).join(', ')}>
      <b className={`font-semibold ${noi ? 'text-noi-testo' : 'text-loro-testo'}`}>{noi ? 'Noi' : 'Loro'}</b>{' '}
      <span className="text-inchiostro">{quando(r.novita).replace(' alle ', ' ')}</span>
    </span>
  )
}

/** Il computer: una tabella vera, l'intestazione resta su mentre scorri. Da 1280 punti tutte le
 *  colonne; fra 1024 e 1280 (col menu a sinistra restano 730 punti) persona, campagna e telefono
 *  si leggono passandoci sopra col mouse e nella scheda: nove colonne li' non si leggerebbero. */
function Tabella({ righe: grezze, apri, note }: { righe: RigaTutti[]; apri: (id: string) => void; note: NoteFU }) {
  const righe = grezze.map((r) => conNota(r, note))
  const th = 'sticky top-0 z-10 border-b border-bordo bg-white px-2.5 py-2.5 text-left text-[13px] font-semibold text-tenue'
  const td = 'border-b border-velo px-2.5 py-2 align-middle'
  const largo = 'hidden xl:table-cell'
  return (
    <table className="w-full table-fixed border-separate border-spacing-0 text-[14px]">
      <thead>
        <tr>
          <th scope="col" className={`${th}`}>Azienda</th>
          <th scope="col" className={`${th} ${largo} w-[7%]`}>Persona</th>
          <th scope="col" className={`${th} w-[9.5rem]`}>Stato</th>
          <th scope="col" className={`${th} w-[8rem]`} title="La sua ultima risposta o la nostra ultima mail, la più recente">Ultima novità</th>
          <th scope="col" className={`${th} ${largo} w-[7%]`}>Campagna</th>
          <th scope="col" className={`${th} w-[6.75rem]`}>Responsabile</th>
          <th scope="col" className={`${th} w-[22%] xl:w-[14%]`}>Prossima azione</th>
          <th scope="col" className={`${th} w-[5.75rem]`}>Data</th>
          <th scope="col" className={`${th} ${largo} w-[8rem]`}>Telefono</th>
        </tr>
      </thead>
      <tbody>
        {righe.map((r) => (
          <tr key={r.prospect_id} onClick={() => apri(r.prospect_id)} className="cursor-pointer hover:bg-velo">
            <td className={td}>
              <button onClick={(e) => { e.stopPropagation(); apri(r.prospect_id) }}
                      title={[r.azienda || r.email, r.persona, r.campagna, r.telefono].filter(Boolean).join(', ')}
                      className="block w-full truncate text-left font-bold text-inchiostro hover:underline">
                {r.azienda || r.email}
              </button>
            </td>
            <td className={`${td} ${largo} truncate text-inchiostro`} title={r.persona || ''}>{r.persona || ''}</td>
            <td className={td}><PillolaStato stato={r.stato} /></td>
            <td className={`${td} truncate whitespace-nowrap`}><Novita r={r} /></td>
            <td className={`${td} ${largo} truncate text-tenue`} title={r.campagna || ''}>{r.campagna || ''}</td>
            <td className={`${td} truncate ${r.responsabile_tuo ? 'text-inchiostro' : 'text-tenue'}`}>{r.responsabile || ''}</td>
            <td className={`${td} truncate ${r.mossa_tua ? 'text-inchiostro' : 'text-tenue'}`} title={r.mossa || ''}>{r.mossa || ''}</td>
            <td className={`${td} truncate whitespace-nowrap ${r.richiamare_il || r.mossa_tua ? 'font-semibold text-inchiostro' : 'text-tenue'}`} title={quandoMossa(r)}>
              {r.richiamare_il && <Icona nome="telefono" className="mr-1 inline h-3.5 w-3.5 align-[-2px]" />}
              {r.richiamare_il && <span className="sr-only">Richiamare il </span>}
              {r.richiamare_il ? giorno(r.richiamare_il) : r.mossa_il ? giorno(r.mossa_il) : ''}
            </td>
            <td className={`${td} ${largo} truncate whitespace-nowrap tabular-nums text-inchiostro`}>{r.telefono || ''}</td>
          </tr>
        ))}
      </tbody>
    </table>
  )
}

/** Il telefono: una lista compatta, un tocco apre la scheda. */
function Lista({ righe: grezze, apri, note }: { righe: RigaTutti[]; apri: (id: string) => void; note: NoteFU }) {
  const righe = grezze.map((r) => conNota(r, note))
  return (
    <ul className="divide-y divide-velo overflow-hidden rounded-2xl border border-bordo bg-white">
      {righe.map((r) => {
        const q = quandoMossa(r)
        return (
          <li key={r.prospect_id}>
            <button onClick={() => apri(r.prospect_id)} className="block w-full px-4 py-2.5 text-left hover:bg-velo">
              <span className="flex items-baseline justify-between gap-3">
                <span className="truncate text-[16px] font-bold text-inchiostro">{r.azienda || r.email}</span>
                <span className="shrink-0 text-[13px]"><Novita r={r} /></span>
              </span>
              <span className="mt-1 flex min-w-0 items-center gap-2 text-[14px]">
                <PillolaStato stato={r.stato} />
                {q && <span className={`shrink-0 ${r.richiamare_il || r.mossa_tua ? 'font-semibold text-inchiostro' : 'text-tenue'}`}>{q}</span>}
                {r.responsabile && <span className={`min-w-0 truncate ${r.responsabile_tuo ? 'text-inchiostro' : 'text-tenue'}`}>{q ? ', ' : ''}{r.responsabile}</span>}
              </span>
              {r.mossa && <span className={`mt-0.5 block truncate text-[14px] ${r.mossa_tua ? 'text-inchiostro' : 'text-tenue'}`}>{r.mossa}</span>}
            </button>
          </li>
        )
      })}
    </ul>
  )
}
