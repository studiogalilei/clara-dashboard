// LA SCHEDA di un lead nella versione snella: chi e', come chiamarlo, cosa fa, le note di Dre,
// stato e prossima mossa (solo Workspace: non va su Smartlead), l'analisi e tutto il filo.
import { useEffect, useState } from 'react'
import {
  STATI, aggiungiNota, ioSono, leggiScheda, linkAnalisi, salvaDecisione, togliNota,
  type Call, type Decisione, type Messaggio, type Nota, type Scheda,
} from './dati'
import { dataCorta, giornoRoma, nomeGiorno, ora, quando, statoDi } from './regole'
import { Bottone, Carico, Errore, Icona, PillolaStato, Vuoto } from './pezzi'
import { linkCompleto, useAvviso, useDati } from './uso'

export default function SchedaLead({ id, indietro }: { id: string; indietro: () => void }) {
  const { dati, setDati, errore, caricando, rifai } = useDati(() => leggiScheda(id), [id])
  const { mostra, vista: avviso } = useAvviso()

  useEffect(() => { window.scrollTo(0, 0) }, [id])

  if (caricando) return <><Torna indietro={indietro} /><Carico righe={5} etichetta="Carico la scheda" /></>
  if (errore && !dati) return <><Torna indietro={indietro} /><Errore testo={errore} riprova={() => void rifai()} /></>
  if (!dati) return null
  if (!dati.scheda) {
    return (
      <>
        <Torna indietro={indietro} />
        <Vuoto>
          Questa scheda non è ancora pronta: si prepara entro dieci minuti per chi ha risposto negli ultimi 60 giorni.{' '}
          <a className="font-semibold text-blu-scuro underline" href={linkCompleto(`azienda/${id}`)}>Aprila nel Workspace completo</a>.
        </Vuoto>
      </>
    )
  }
  const sc = dati.scheda
  const s = sc.scheda
  const d = dati.decisione
  const stato = statoDi(sc, d)

  return (
    <article aria-labelledby="titolo-scheda">
      <Torna indietro={indietro} />
      <header>
        <h1 id="titolo-scheda" className="text-[24px] font-bold leading-tight text-inchiostro">{s.azienda || sc.azienda}</h1>
        <p className="mt-1 text-[15px] text-tenue">
          {[s.nome || sc.persona, s.ruolo].filter(Boolean).join(', ') || 'Persona non indicata'}
        </p>
        <div className="mt-2 flex flex-wrap items-center gap-2">
          <PillolaStato stato={stato} />
          {sc.ultima_risposta && <span className="text-[14px] text-tenue">ultima risposta {quando(sc.ultima_risposta)}</span>}
        </div>
        <ProssimaCall call={dati.call} />
      </header>

      <Blocco titolo="Telefoni">
        {s.telefoni.length ? (
          <ul className="space-y-2 sm:max-w-md">
            {s.telefoni.map((t, i) => (
              <li key={t.tel}>
                <a href={`tel:${t.tel}`} aria-label={`Chiama ${t.numero}, ${t.etichetta}`}
                   className={`flex min-h-14 items-center gap-3 rounded-xl px-4 py-2 ${i === 0 ? 'bg-blu-scuro text-white hover:bg-navy' : 'border border-bordo text-inchiostro hover:border-tenue'}`}>
                  <Icona nome="telefono" className="h-5 w-5 shrink-0" />
                  <span className="min-w-0">
                    <span className="block whitespace-nowrap text-[17px] font-bold tracking-wide">{t.numero}</span>
                    <span className={`block truncate text-[13px] ${i === 0 ? 'text-white/85' : 'text-tenue'}`}>{t.etichetta}</span>
                  </span>
                </a>
              </li>
            ))}
          </ul>
        ) : <p className="text-[15px] text-tenue">Nessun numero: né nella firma, né nella scheda, né sul sito.</p>}
        {s.email && <p className="mt-2 break-all text-[14px] text-tenue">Mail: {s.email}</p>}
      </Blocco>

      {s.attivita && (
        <Blocco titolo="Cosa fa">
          <p className="text-[15px] leading-relaxed text-inchiostro">{s.attivita}</p>
        </Blocco>
      )}

      <Blocco titolo="Stato e prossima mossa">
        <Decidi id={id} scheda={sc} decisione={d} onSalvato={(nuova) => {
          setDati((x) => x ? { ...x, decisione: nuova } : x)
          mostra({ testo: 'Salvato' })
        }} />
      </Blocco>

      <Blocco titolo="Note">
        <Note id={id} note={dati.note} mostra={mostra}
              onNota={(n) => setDati((x) => x ? { ...x, note: [n, ...x.note] } : x)}
              onTolta={(nid) => setDati((x) => x ? { ...x, note: x.note.filter((n) => n.id !== nid) } : x)} />
      </Blocco>

      <Blocco titolo="Analisi">
        <Analisi a={s.analisi} />
      </Blocco>

      <Blocco titolo={`La conversazione · ${sc.filo.length} mail`}>
        <Filo filo={sc.filo} lui={(s.nome || sc.persona || '').trim().split(/\s+/)[0] || ''} />
      </Blocco>

      <p className="mt-8 border-t border-velo pt-4 text-[14px] text-tenue">
        {s.campagna && <>Campagna: {s.campagna}<br /></>}
        Scheda aggiornata {quando(sc.aggiornata_il)}.{' '}
        <a href={linkCompleto(`azienda/${id}`)} className="inline-flex min-h-9 items-center font-semibold text-blu-scuro hover:underline">
          Apri nel Workspace completo
        </a>
      </p>
      {avviso}
    </article>
  )
}

/** La prossima call con lui (17/10: la scheda di chi aveva la call lunedi' non la diceva). */
function ProssimaCall({ call }: { call: Call[] }) {
  const adesso = Date.now()
  const c = [...call].sort((a, b) => a.at.localeCompare(b.at)).find((x) => new Date(x.at).getTime() > adesso - 90 * 60_000)
  if (!c) return null
  const giorno = nomeGiorno(giornoRoma(new Date(c.at)))
  return (
    <div className="mt-3 flex flex-wrap items-center gap-x-3 gap-y-2 rounded-2xl border border-ok-bordo bg-ok-fondo px-4 py-3">
      <p className="flex items-center gap-2 text-[15px] text-inchiostro">
        <Icona nome="ok" className="h-5 w-5 shrink-0 text-ok-testo" />
        <b className="text-ok-testo">Call {giorno === 'Oggi' || giorno === 'Domani' ? giorno.toLowerCase() : giorno.charAt(0).toLowerCase() + giorno.slice(1)} alle {ora(c.at)}</b>
        {c.di_chi && <span className="text-tenue"> · nel calendario di {c.di_chi}</span>}
      </p>
      {c.meet && (
        <a href={c.meet} target="_blank" rel="noreferrer"
           className="inline-flex min-h-11 items-center gap-1.5 rounded-full bg-blu-scuro px-4 text-[14px] font-semibold text-white hover:bg-navy">
          <Icona nome="video" className="h-4 w-4" /> Apri il Meet
        </a>
      )}
    </div>
  )
}

function Torna({ indietro }: { indietro: () => void }) {
  return (
    <button onClick={indietro} className="-ml-2 mb-3 inline-flex min-h-11 items-center gap-1 rounded-full pl-1 pr-3 text-[15px] font-semibold text-blu-scuro hover:bg-velo">
      <Icona nome="indietro" /> Indietro
    </button>
  )
}

function Blocco({ titolo, children }: { titolo: string; children: React.ReactNode }) {
  return (
    <section className="mt-6">
      <h2 className="mb-2 text-[13px] font-bold uppercase tracking-[0.06em] text-tenue">{titolo}</h2>
      {children}
    </section>
  )
}

function Decidi({ id, scheda, decisione, onSalvato }: { id: string; scheda: Scheda; decisione: Decisione | null; onSalvato: (d: Decisione) => void }) {
  const suggerita = scheda.scheda.prossima
  const [stato, setStato] = useState(decisione?.stato ?? '')
  const [mossa, setMossa] = useState(decisione?.prossima_mossa ?? '')
  const [il, setIl] = useState(decisione?.prossima_il ?? '')
  const [lavoro, setLavoro] = useState(false)
  const [sbaglio, setSbaglio] = useState<string | null>(null)
  const cambiato = stato !== (decisione?.stato ?? '') || mossa !== (decisione?.prossima_mossa ?? '') || il !== (decisione?.prossima_il ?? '')

  async function salva() {
    setLavoro(true); setSbaglio(null)
    try {
      onSalvato(await salvaDecisione(id, { stato: (stato || null) as Decisione['stato'], prossima_mossa: mossa.trim() || null, prossima_il: il || null }))
    } catch (e) {
      setSbaglio(`Non salvato: ${e instanceof Error ? e.message : e}`)
    } finally {
      setLavoro(false)
    }
  }

  return (
    <form onSubmit={(e) => { e.preventDefault(); void salva() }} className="space-y-3 rounded-2xl border border-bordo bg-white p-4">
      <div>
        <label htmlFor="stato" className="mb-1 block text-[14px] font-semibold text-inchiostro">Stato</label>
        <select id="stato" value={stato} onChange={(e) => setStato(e.target.value)}
                className="h-11 w-full rounded-xl border border-bordo bg-white px-3 text-[15px] text-inchiostro outline-none focus:border-blu-scuro">
          <option value="">Come dicono le mail: {scheda.stato ?? 'In conversazione'}</option>
          {STATI.map((s) => <option key={s} value={s}>{s}</option>)}
        </select>
      </div>
      <div>
        <label htmlFor="mossa" className="mb-1 block text-[14px] font-semibold text-inchiostro">Prossima mossa</label>
        <input id="mossa" value={mossa} onChange={(e) => setMossa(e.target.value)} maxLength={200}
               placeholder={suggerita.mossa ? `Suggerita: ${suggerita.mossa}${suggerita.il ? ` (${dataCorta(suggerita.il)})` : ''}` : 'Cosa fare'}
               className="h-11 w-full rounded-xl border border-bordo px-3 text-[15px] text-inchiostro outline-none placeholder:text-spento focus:border-blu-scuro" />
      </div>
      <div>
        <label htmlFor="quando" className="mb-1 block text-[14px] font-semibold text-inchiostro">Quando</label>
        <input id="quando" type="date" value={il} onChange={(e) => setIl(e.target.value)}
               className="h-11 rounded-xl border border-bordo px-3 text-[15px] text-inchiostro outline-none focus:border-blu-scuro" />
      </div>
      {!decisione?.prossima_mossa && suggerita.mossa && (
        <p className="text-[14px] text-tenue">Per ora vale quella suggerita: {suggerita.mossa}{suggerita.il ? `, ${dataCorta(suggerita.il)}` : ''}.</p>
      )}
      <div className="flex items-center gap-3">
        <Bottone tipo="primo" type="submit" disabled={lavoro || !cambiato}>{lavoro ? 'Salvo…' : 'Salva'}</Bottone>
        <span className="text-[13px] text-tenue">Resta nel Workspace: Smartlead non cambia.</span>
      </div>
      {sbaglio && <p role="alert" className="text-[14px] font-semibold text-no-testo">{sbaglio}</p>}
    </form>
  )
}

function Note({ id, note, onNota, onTolta, mostra }: {
  id: string; note: Nota[]; onNota: (n: Nota) => void; onTolta: (id: number) => void; mostra: (a: { testo: string }) => void
}) {
  const [testo, setTesto] = useState('')
  const [lavoro, setLavoro] = useState(false)
  const [sbaglio, setSbaglio] = useState<string | null>(null)
  const [io, setIo] = useState<string | null>(null)
  useEffect(() => { void ioSono().then(setIo) }, [])

  // 17/10: una nota scritta sul lead sbagliato o con un errore non si poteva togliere.
  // Chi l'ha scritta la cancella (il database non lascia cancellare quelle degli altri).
  async function togli(n: Nota) {
    if (!window.confirm('Cancellare questa nota?')) return
    setSbaglio(null)
    try {
      await togliNota(n.id)
      onTolta(n.id)
      mostra({ testo: 'Nota cancellata' })
    } catch (e) {
      setSbaglio(`Nota non cancellata: ${e instanceof Error ? e.message : e}`)
    }
  }

  async function aggiungi() {
    if (!testo.trim()) return
    setLavoro(true); setSbaglio(null)
    try {
      onNota(await aggiungiNota(id, testo))
      setTesto('')
    } catch (e) {
      setSbaglio(`Nota non salvata: ${e instanceof Error ? e.message : e}`)
    } finally {
      setLavoro(false)
    }
  }

  return (
    <div>
      <form onSubmit={(e) => { e.preventDefault(); void aggiungi() }}>
        <label htmlFor="nuova-nota" className="sr-only">Nuova nota</label>
        <textarea id="nuova-nota" value={testo} onChange={(e) => setTesto(e.target.value)} rows={3} maxLength={4000}
                  placeholder="Scrivi una nota: cosa vi siete detti, cosa fare"
                  className="w-full rounded-xl border border-bordo px-3 py-2 text-[15px] text-inchiostro outline-none placeholder:text-spento focus:border-blu-scuro" />
        <div className="mt-2 flex items-center gap-2">
          <Bottone tipo="primo" type="submit" disabled={lavoro || !testo.trim()}>{lavoro ? 'Salvo…' : 'Aggiungi la nota'}</Bottone>
        </div>
        {sbaglio && <p role="alert" className="mt-2 text-[14px] font-semibold text-no-testo">{sbaglio}</p>}
      </form>
      {note.length ? (
        <ol className="mt-4 space-y-3">
          {note.map((n) => (
            <li key={n.id} className="border-l-2 border-bordo pl-3">
              <p className="flex items-center justify-between gap-2 text-[13px] text-tenue">
                <span>{quando(n.at)}{n.autore_nome && ` · ${n.autore_nome}`}{n.tipo === 'chiamata' && ' · telefonata'}</span>
                {io && n.autore === io && (
                  <button onClick={() => void togli(n)} aria-label="Cancella questa nota"
                          className="-my-2 inline-flex min-h-11 items-center rounded-full px-3 text-[13px] font-semibold text-tenue hover:bg-velo hover:text-no-testo">
                    Cancella
                  </button>
                )}
              </p>
              <p className="whitespace-pre-wrap text-[15px] text-inchiostro">{n.testo}</p>
            </li>
          ))}
        </ol>
      ) : <p className="mt-3 text-[14px] text-tenue">Ancora nessuna nota.</p>}
    </div>
  )
}

function Analisi({ a }: { a: Scheda['scheda']['analisi'] }) {
  const [apro, setApro] = useState(false)
  const [sbaglio, setSbaglio] = useState(false)
  if (!a.mandata) return <p className="text-[15px] text-inchiostro">Non ancora mandata.</p>
  const apribile = Boolean(a.percorso || a.link)

  async function apri() {
    // la finestra si apre subito (Safari blocca quelle aperte dopo un'attesa), poi si punta al PDF
    const w = window.open('', '_blank')
    if (w) { try { w.opener = null } catch { /* niente */ } }
    setApro(true); setSbaglio(false)
    const url = await linkAnalisi(a)
    setApro(false)
    if (!url) { w?.close(); setSbaglio(true); return }
    if (w) w.location.replace(url); else window.open(url, '_blank')
  }

  return (
    <div className="space-y-2">
      <p className="text-[15px] text-inchiostro">Mandata{a.il ? ` ${quando(a.il)}` : ''}.</p>
      {a.punto && <p className="text-[15px] leading-snug text-tenue">Il punto chiave: {a.punto}</p>}
      {apribile ? (
        <Bottone onClick={() => void apri()} disabled={apro}>{apro ? 'Apro…' : 'Apri il PDF'} <Icona nome="esterno" className="h-4 w-4" /></Bottone>
      ) : <p className="text-[14px] text-tenue">Il PDF non è agganciato a questa scheda.</p>}
      {sbaglio && <p role="alert" className="text-[14px] font-semibold text-no-testo">Il PDF non si apre: provalo dal Workspace completo.</p>}
    </div>
  )
}

function Filo({ filo, lui }: { filo: Messaggio[]; lui: string }) {
  const [tutto, setTutto] = useState(false)
  if (!filo.length) return <p className="text-[15px] text-tenue">Nessuna mail.</p>
  const nascosti = tutto ? 0 : Math.max(0, filo.length - 4)
  return (
    <div>
      {nascosti > 0 && (
        <div className="mb-3">
          <Bottone onClick={() => setTutto(true)}>{nascosti === 1 ? 'Mostra la mail prima' : `Mostra le ${nascosti} mail prima`}</Bottone>
        </div>
      )}
      <ol className="space-y-3">
        {filo.slice(nascosti).map((m, i) => <Mail key={`${m.at}-${i}`} m={m} lui={lui} />)}
      </ol>
    </div>
  )
}

const RIGHE = 6
const CARATTERI = 600

function Mail({ m, lui: nome }: { m: Messaggio; lui: string }) {
  const [citato, setCitato] = useState(false)
  const lui = m.chi === 'lui'
  // le mail lunghe (le nostre con firma e informativa, le sue con l'invito del calendario) si
  // leggono dalle prime righe, il resto a richiesta. Le sue brevi restano intere.
  const righe = m.testo.split('\n')
  const lunga = righe.length > RIGHE + 2 || m.testo.length > CARATTERI + 200
  const [intera, setIntera] = useState(false)
  const testo = lunga && !intera ? righe.slice(0, RIGHE).join('\n').slice(0, CARATTERI).trimEnd() + '…' : m.testo
  // 17/10, Dre: «"noi" e "loro" in piccolissimo: devo rileggere ogni messaggio per capire qual e'
  // il mio». Ogni mail ha la sua barra a sinistra e la parola grande: Noi in blu, sul fondo
  // azzurro e spostata a destra; Loro nel colore caldo, sul bianco e a sinistra.
  return (
    <li className={`rounded-xl border border-l-[5px] p-4 ${lui
      ? 'mr-6 border-bordo border-l-loro-segno bg-white sm:mr-16'
      : 'ml-6 border-noi-bordo border-l-noi-segno bg-noi-fondo sm:ml-16'}`}>
      <p className="mb-2 flex flex-wrap items-baseline gap-x-2">
        <span className={`text-[15px] font-bold ${lui ? 'text-loro-testo' : 'text-noi-testo'}`}>
          {lui ? `Loro${nome ? ` · ${nome}` : ''}` : 'Noi'}
        </span>
        <span className="text-[14px] text-inchiostro/75">{quando(m.at)}</span>
      </p>
      {m.testo ? <p className="whitespace-pre-wrap break-words text-[15px] leading-relaxed text-inchiostro">{testo}</p>
        : <p className="text-[14px] italic text-tenue">Solo testo citato.</p>}
      {lunga && (
        <button onClick={() => setIntera(!intera)} aria-expanded={intera}
                className="mt-1 inline-flex min-h-9 items-center text-[14px] font-semibold text-blu-scuro hover:underline">
          {intera ? 'Mostra meno' : 'Mostra tutta la mail'}
        </button>
      )}
      {m.citato && (
        <div className="mt-2">
          <button onClick={() => setCitato(!citato)} aria-expanded={citato}
                  className="inline-flex min-h-9 items-center text-[14px] font-semibold text-blu-scuro hover:underline">
            {citato ? 'Nascondi il testo citato' : 'Mostra il testo citato'}
          </button>
          {citato && <p className="mt-1 whitespace-pre-wrap break-words border-l-2 border-bordo pl-3 text-[14px] leading-relaxed text-tenue">{m.citato}</p>}
        </div>
      )}
    </li>
  )
}
