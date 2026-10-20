// LA SCHEDA di un lead nella versione snella (pulita il 20/10, Dre: «fa abbastanza schifo,
// impostala clean con le info anche del sito»). In quest'ordine: chi e' (azienda, persona, stato in
// una riga); come si contatta (telefono, mail, sito, citta', settore, campagna); il prossimo messaggio
// di Clara, col testo esatto e «Ferma»; la conversazione con l'analisi; stato e prossima azione; note.
import { useEffect, useState } from 'react'
import {
  GRUPPI, INFO_STATI, RESPONSABILI, aggiungiNota, fermaMessaggi, ioSono, leggiScheda, linkAnalisi, salvaDecisione, togliNota,
  type Call, type Decisione, type Lead, type Messaggio, type Nota, type Scheda, type Telefono,
} from './dati'
import {
  giornoRoma, infoStato, nomeGiorno, nomeStato, ora, prossimoMessaggio, quando, sitoBreve, sitoCliccabile, statoDi,
} from './regole'
import { Bottone, Carico, Errore, Icona, PillolaStato, type NomeIcona } from './pezzi'
import { linkCompleto, useAvviso, useDati } from './uso'

export default function SchedaLead({ id, indietro }: { id: string; indietro: () => void }) {
  const { dati, setDati, errore, caricando, rifai } = useDati(() => leggiScheda(id), [id])
  const { mostra, vista: avviso } = useAvviso()

  useEffect(() => { window.scrollTo(0, 0) }, [id])

  if (caricando) return <><Torna indietro={indietro} /><Carico righe={5} etichetta="Carico la scheda" /></>
  if (errore && !dati) return <><Torna indietro={indietro} /><Errore testo={errore} riprova={() => void rifai()} /></>
  if (!dati) return null
  const sc = dati.scheda
  const b = dati.base
  if (!sc && !b) {
    return <><Torna indietro={indietro} /><Errore testo="Questo lead non c'è più nel Workspace." /></>
  }
  const lead = dati.lead
  const d = dati.decisione
  const s = sc?.scheda
  // la scheda piena (chi ha risposto negli ultimi 60 giorni, scripts/schede.py) o la riga di «Tutti»
  const stato = sc ? statoDi(sc, d) : (d?.stato || b!.stato_sistema)
  const sistema = sc ? (nomeStato(sc.stato) ?? 'Da rispondere') : b!.stato_sistema
  const suggerita = sc
    ? (nomeStato(sc.stato) === sc.stato ? s!.prossima : { mossa: null, il: null })
    : (b!.mossa_tua ? { mossa: null, il: null } : { mossa: b!.mossa, il: b!.mossa_il })
  const azienda = s?.azienda || sc?.azienda || b?.azienda || b?.email || 'Senza nome'
  const persona = [s?.nome || sc?.persona || b?.persona, s?.ruolo].filter(Boolean).join(', ')
  const ultima = sc ? sc.ultima_risposta : b!.ultima_risposta
  const unico = b?.telefono || lead?.phone || ''
  const telefoni: Telefono[] = s?.telefoni.length ? s.telefoni
    : unico ? [{ numero: unico, tel: unico.replace(/[^\d+]/g, ''), etichetta: '' }] : []
  // l'analisi della scheda; se la scheda non la sa, quella della riga del lead
  const analisi: Scheda['scheda']['analisi'] = s?.analisi.mandata ? s.analisi : {
    mandata: Boolean(lead?.analysis_sent_at), il: lead?.analysis_sent_at ?? null, link: lead?.analysis_pdf ?? '', percorso: '', punto: s?.analisi.punto ?? '',
  }
  const chiuso = ['Opportunità', 'Chiusi'].includes(infoStato(stato)?.gruppo ?? '')
  const filo = sc?.filo ?? []
  const prossimo = prossimoMessaggio(lead ?? VUOTO, dati.proposte, dati.calendario,
    filo.filter((m) => m.chi === 'noi' && m.at).map((m) => m.at!))

  return (
    <article aria-labelledby="titolo-scheda">
      <Torna indietro={indietro} />
      <header>
        <h1 id="titolo-scheda" className="text-[26px] font-bold leading-tight tracking-[-0.01em] text-inchiostro">{azienda}</h1>
        <div className="mt-2 flex flex-wrap items-center gap-x-2 gap-y-1.5 text-[15px] text-tenue">
          <PillolaStato stato={stato} />
          {persona && <span className="text-inchiostro">{persona}</span>}
        </div>
        <p className="mt-1 text-[14px] text-tenue">{ultima ? `Ha scritto ${quando(ultima)}` : 'Non ha mai risposto'}</p>
        {s?.attivita && <p className="mt-3 max-w-[65ch] text-[15px] leading-relaxed text-tenue">{s.attivita}</p>}
        <ProssimaCall call={dati.call} />
      </header>

      <Contatti telefoni={telefoni} email={s?.email || b?.email || lead?.email || ''} lead={lead}
                campagna={s?.campagna || b?.campagna || lead?.campaign || ''} />

      <Blocco titolo="Il prossimo messaggio di Clara">
        <ProssimoMessaggio id={id} prossimo={prossimo} fermato={Boolean(lead?.no_followup)} chiuso={chiuso} onFermato={(partite) => {
          setDati((x) => x ? {
            ...x, calendario: null, lead: x.lead ? { ...x.lead, no_followup: true, coda: null } : x.lead,
            proposte: x.proposte.map((p) => prossimo?.da_chiudere.includes(p.id) && (p.stato === 'aperta' || p.stato === 'approvata')
              ? { ...p, stato: 'no', risposta: 'NO: fermato da Dre' } : p),
          } : x)
          mostra({ testo: partite ? 'Fermato. Una mail era già partita.' : 'Fermato' })
        }} />
      </Blocco>

      <Blocco titolo="La conversazione">
        <Analisi a={analisi} />
        {sc ? <div className="mt-4"><Filo filo={filo} lui={(s?.nome || sc.persona || '').trim().split(/\s+/)[0] || ''} /></div>
          : <p className="mt-3 text-[15px] text-tenue">Le mail arrivano qui entro dieci minuti da quando salvi uno stato o una nota.</p>}
      </Blocco>

      <Blocco titolo="Stato e prossima azione">
        <Decidi id={id} sistema={sistema} suggerita={suggerita} decisione={d} onSalvato={(nuova) => {
          setDati((x) => x ? { ...x, decisione: nuova } : x)
          mostra({ testo: 'Salvato' })
        }} />
      </Blocco>

      <Blocco titolo="Note">
        <Note id={id} note={dati.note} mostra={mostra}
              onNota={(n) => setDati((x) => x ? { ...x, note: [n, ...x.note] } : x)}
              onTolta={(nid) => setDati((x) => x ? { ...x, note: x.note.filter((n) => n.id !== nid) } : x)} />
      </Blocco>

      <p className="mt-10 border-t border-velo pt-3 text-[14px]">
        <a href={linkCompleto(`azienda/${id}`)} className="inline-flex min-h-11 items-center gap-1.5 font-semibold text-blu-scuro hover:underline">
          Apri nel Workspace completo <Icona nome="esterno" className="h-4 w-4" />
        </a>
      </p>
      {avviso}
    </article>
  )
}

const VUOTO: Lead = {
  website: null, city: null, sector: null, campaign: null, phone: null, email: null, analysis_pdf: null, analysis_sent_at: null,
  last_reply_at: null, no_followup: null, fuori: null, stage: null, classificazione: null, coda: null, awaiting_us: null,
}

/** «esperienze_turistiche» → «Esperienze turistiche» */
function settore(s: string | null | undefined): string {
  const t = (s ?? '').replace(/_/g, ' ').trim()
  return t ? t.charAt(0).toUpperCase() + t.slice(1) : ''
}

/** Come si contatta e chi e': una riga per cosa, come la rubrica del telefono. Quello che manca non c'e'. */
function Contatti({ telefoni, email, lead, campagna }: { telefoni: Telefono[]; email: string; lead: Lead | null; campagna: string }) {
  const sito = sitoCliccabile(lead?.website)
  const righe: Array<{ icona: NomeIcona; testo: string; sotto?: string; href?: string; fuori?: boolean; etichetta?: string }> = [
    ...telefoni.map((t) => ({ icona: 'telefono' as const, testo: t.numero, sotto: t.etichetta, href: `tel:${t.tel}`, etichetta: `Chiama ${t.numero}` })),
    ...(email ? [{ icona: 'mail' as const, testo: email, href: `mailto:${email}`, etichetta: `Scrivi a ${email}` }] : []),
    ...(sito ? [{ icona: 'sito' as const, testo: sitoBreve(sito), href: sito, fuori: true, etichetta: `Apri il sito ${sitoBreve(sito)}` }] : []),
    ...(lead?.city ? [{ icona: 'luogo' as const, testo: lead.city }] : []),
    ...(settore(lead?.sector) ? [{ icona: 'settore' as const, testo: settore(lead?.sector) }] : []),
    ...(campagna ? [{ icona: 'campagna' as const, testo: campagna, sotto: 'campagna' }] : []),
  ]
  if (!righe.length) return null
  return (
    <section aria-label="Contatti" className="mt-6 rounded-2xl border border-bordo bg-white px-2 py-1">
      <ul className="grid sm:grid-cols-2 sm:gap-x-2">
        {righe.map((r) => {
          const dentro = (
            <>
              <Icona nome={r.icona} className={`h-5 w-5 shrink-0 ${r.href ? 'text-blu-scuro' : 'text-tenue'}`} />
              <span className="min-w-0">
                <span className={`block truncate text-[15px] ${r.href ? 'font-semibold text-blu-scuro' : 'text-inchiostro'} ${r.icona === 'telefono' ? 'tabular-nums tracking-wide' : ''}`}>{r.testo}</span>
                {r.sotto && <span className="block truncate text-[13px] text-tenue">{r.sotto}</span>}
              </span>
              {r.fuori && <Icona nome="esterno" className="ml-auto h-4 w-4 shrink-0 text-tenue" />}
            </>
          )
          const stile = 'flex min-h-12 items-center gap-3 rounded-xl px-3 py-2'
          return (
            <li key={`${r.icona}-${r.testo}`} className="min-w-0">
              {r.href ? (
                <a href={r.href} aria-label={r.etichetta} {...(r.fuori ? { target: '_blank', rel: 'noreferrer' } : {})}
                   className={`${stile} transition-colors duration-150 hover:bg-velo focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blu-scuro`}>
                  {dentro}
                </a>
              ) : <div className={stile}>{dentro}</div>}
            </li>
          )
        })}
      </ul>
    </section>
  )
}

const RIGHE_MESSAGGIO = 8

/** Il prossimo messaggio che Clara gli mandera': quando, il testo esatto (se e' gia' scritto) e
 *  «Ferma», che chiede conferma prima di fermare questo e i messaggi automatici dopo. */
function ProssimoMessaggio({ id, prossimo, fermato, chiuso, onFermato }: {
  id: string; prossimo: ReturnType<typeof prossimoMessaggio>; fermato: boolean; chiuso: boolean; onFermato: (partite: number) => void
}) {
  const [chiedo, setChiedo] = useState(false)
  const [lavoro, setLavoro] = useState(false)
  const [sbaglio, setSbaglio] = useState<string | null>(null)
  const [intero, setIntero] = useState(false)

  if (!prossimo) {
    return (
      <p className="text-[15px] text-tenue">
        {chiuso ? 'Nessun messaggio automatico.'
          : fermato ? 'Fermato: Clara non gli scrive finché non risponde lui.' : 'Nessun messaggio in programma.'}
      </p>
    )
  }

  async function ferma() {
    setLavoro(true); setSbaglio(null)
    try {
      const { partite } = await fermaMessaggi(id, prossimo!.da_chiudere)
      setChiedo(false)
      onFermato(partite)
    } catch (e) {
      setSbaglio(`Non fermato: ${e instanceof Error ? e.message : e}`)
    } finally {
      setLavoro(false)
    }
  }

  const righe = prossimo.testo?.split('\n') ?? []
  const lungo = righe.length > RIGHE_MESSAGGIO + 2
  const testo = lungo && !intero ? righe.slice(0, RIGHE_MESSAGGIO).join('\n').trimEnd() + '…' : prossimo.testo
  return (
    <div className="overflow-hidden rounded-2xl border border-noi-bordo bg-white">
      <p className="border-b border-noi-bordo px-4 py-3 text-[16px] font-bold text-inchiostro">
        {prossimo.quando}
        <span className="font-normal text-tenue"> · {prossimo.tipo}</span>
      </p>
      <div className="px-4 py-3">
        {testo ? (
          <>
            <p className="whitespace-pre-wrap break-words text-[15px] leading-relaxed text-inchiostro">{testo}</p>
            {lungo && (
              <button onClick={() => setIntero(!intero)} aria-expanded={intero}
                      className="mt-1 inline-flex min-h-11 items-center text-[14px] font-semibold text-blu-scuro hover:underline">
                {intero ? 'Mostra meno' : 'Mostra tutto'}
              </button>
            )}
          </>
        ) : <p className="text-[15px] text-tenue">Clara lo scrive quel giorno, dopo aver riletto la conversazione.</p>}
      </div>
      {!chiedo && (
        <div className="border-t border-velo px-2 py-1">
          <button onClick={() => setChiedo(true)}
                  className="inline-flex min-h-11 items-center gap-1.5 rounded-full px-3 text-[14px] font-semibold text-no-testo transition-colors duration-150 hover:bg-no-fondo focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-no-testo">
            <Icona nome="divieto" className="h-4 w-4" /> Ferma
          </button>
        </div>
      )}
      {chiedo && (
        <div role="alertdialog" aria-labelledby={`ferma-${id}`} className="border-t border-no-bordo bg-no-fondo px-4 py-3">
          <p id={`ferma-${id}`} className="text-[15px] font-semibold text-no-testo">Fermarlo? Clara non gli scrive più finché non risponde lui.</p>
          <div className="mt-2 flex flex-wrap gap-2">
            <button onClick={() => void ferma()} disabled={lavoro} autoFocus
                    className="inline-flex min-h-11 items-center rounded-full border border-no-testo bg-no-testo px-4 text-[14px] font-semibold text-white transition-opacity duration-150 hover:opacity-90 disabled:opacity-50">
              {lavoro ? 'Fermo…' : 'Sì, ferma'}
            </button>
            <Bottone onClick={() => setChiedo(false)} disabled={lavoro}>Annulla</Bottone>
          </div>
        </div>
      )}
      {sbaglio && <p role="alert" className="px-4 pb-3 text-[14px] font-semibold text-no-testo">{sbaglio}</p>}
    </div>
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
    <section className="mt-8">
      <h2 className="mb-3 text-[13px] font-bold uppercase tracking-[0.06em] text-tenue">{titolo}</h2>
      {children}
    </section>
  )
}

/** Stato, responsabile, prossima azione e data: quello che decide Dre (19/10, i 12 stati). Vuoto vuol
 *  dire «come dice il sistema»: la voce vuota porta il nome di quello che vale adesso. */
function Decidi({ id, sistema, suggerita, decisione, onSalvato }: {
  id: string; sistema: string; suggerita: { mossa: string | null; il: string | null }; decisione: Decisione | null; onSalvato: (d: Decisione) => void
}) {
  const [stato, setStato] = useState(decisione?.stato ?? '')
  const [chi, setChi] = useState<string>(decisione?.responsabile ?? '')
  const [mossa, setMossa] = useState(decisione?.prossima_mossa ?? '')
  const [il, setIl] = useState(decisione?.prossima_il ?? '')
  const [lavoro, setLavoro] = useState(false)
  const [sbaglio, setSbaglio] = useState<string | null>(null)
  const cambiato = stato !== (decisione?.stato ?? '') || chi !== (decisione?.responsabile ?? '')
    || mossa !== (decisione?.prossima_mossa ?? '') || il !== (decisione?.prossima_il ?? '')
  const info = infoStato(stato || sistema)
  const proposta = stato && stato !== sistema ? (info?.azione ?? null) : (suggerita.mossa || info?.azione || null)

  async function salva() {
    setLavoro(true); setSbaglio(null)
    try {
      onSalvato(await salvaDecisione(id, {
        stato: (stato || null) as Decisione['stato'], responsabile: (chi || null) as Decisione['responsabile'],
        prossima_mossa: mossa.trim() || null, prossima_il: il || null,
      }))
    } catch (e) {
      setSbaglio(`Non salvato: ${e instanceof Error ? e.message : e}`)
    } finally {
      setLavoro(false)
    }
  }

  const campo = 'h-11 w-full rounded-xl border border-bordo bg-white px-3 text-[16px] text-inchiostro outline-none transition-colors duration-150 focus:border-blu-scuro'
  const etichetta = 'mb-1 block text-[13px] font-semibold text-tenue'
  return (
    <form onSubmit={(e) => { e.preventDefault(); void salva() }} className="rounded-2xl border border-bordo bg-white p-4">
      <div className="grid gap-3 sm:grid-cols-2">
        <div>
          <label htmlFor="stato" className={etichetta}>Stato</label>
          <select id="stato" value={stato} onChange={(e) => setStato(e.target.value)} className={campo}>
            <option value="">{sistema}</option>
            {GRUPPI.map((g) => (
              <optgroup key={g} label={g}>
                {INFO_STATI.filter((s) => s.gruppo === g).map((s) => <option key={s.nome} value={s.nome}>{s.nome}</option>)}
              </optgroup>
            ))}
          </select>
        </div>
        <div>
          <label htmlFor="responsabile" className={etichetta}>Chi</label>
          <select id="responsabile" value={chi} onChange={(e) => setChi(e.target.value)} className={campo}>
            <option value="">{info?.responsabile ?? 'Claude'}</option>
            {RESPONSABILI.map((r) => <option key={r} value={r}>{r}</option>)}
          </select>
        </div>
        <div>
          <label htmlFor="mossa" className={etichetta}>Prossima azione</label>
          <input id="mossa" value={mossa} onChange={(e) => setMossa(e.target.value)} maxLength={200}
                 placeholder={proposta ?? 'Cosa fare'}
                 className={`${campo} placeholder:text-spento`} />
        </div>
        <div>
          <label htmlFor="quando" className={etichetta}>Quando</label>
          <input id="quando" type="date" value={il || ''} onChange={(e) => setIl(e.target.value)} className={campo} />
        </div>
      </div>
      <div className="mt-4 flex items-center gap-3">
        <Bottone tipo="primo" type="submit" disabled={lavoro || !cambiato}>{lavoro ? 'Salvo…' : 'Salva'}</Bottone>
        {sbaglio && <p role="alert" className="text-[14px] font-semibold text-no-testo">{sbaglio}</p>}
      </div>
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
                  className="w-full rounded-xl border border-bordo px-3 py-2 text-[16px] text-inchiostro outline-none placeholder:text-spento focus:border-blu-scuro" />
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
  if (!a.mandata) return <p className="text-[15px] text-tenue">Analisi non ancora mandata.</p>
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
    <div className="rounded-2xl border border-bordo bg-white px-4 py-3">
      <div className="flex flex-wrap items-center justify-between gap-x-3 gap-y-1">
        <p className="text-[15px] text-inchiostro"><b className="font-semibold">Analisi mandata</b>{a.il ? <span className="text-tenue"> {quando(a.il)}</span> : ''}</p>
        {apribile ? (
          <Bottone onClick={() => void apri()} disabled={apro} className="-mr-2">{apro ? 'Apro…' : 'Apri il PDF'} <Icona nome="esterno" className="h-4 w-4" /></Bottone>
        ) : <span className="text-[14px] text-tenue">PDF non agganciato</span>}
      </div>
      {a.punto && <p className="mt-1 max-w-[65ch] text-[14px] leading-snug text-tenue">{a.punto}</p>}
      {sbaglio && <p role="alert" className="mt-1 text-[14px] font-semibold text-no-testo">Il PDF non si apre: provalo dal Workspace completo.</p>}
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
                className="mt-1 inline-flex min-h-11 items-center text-[14px] font-semibold text-blu-scuro hover:underline">
          {intera ? 'Mostra meno' : 'Mostra tutta la mail'}
        </button>
      )}
      {m.citato && (
        <div className="mt-2">
          <button onClick={() => setCitato(!citato)} aria-expanded={citato}
                  className="inline-flex min-h-11 items-center text-[14px] font-semibold text-blu-scuro hover:underline">
            {citato ? 'Nascondi il testo citato' : 'Mostra il testo citato'}
          </button>
          {citato && <p className="mt-1 whitespace-pre-wrap break-words border-l-2 border-bordo pl-3 text-[14px] leading-relaxed text-tenue">{m.citato}</p>}
        </div>
      )}
    </li>
  )
}
