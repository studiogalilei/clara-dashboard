// OGGI, la home della versione snella. Dre la apre alle 10, alle 15 e alle 17:30.
// In 10 secondi: com'e' andata la giornata (una riga, rossa se qualcosa e' in ritardo), chi
// chiamare adesso, le call dei prossimi giorni, cosa aspetta una sua decisione nella Posta.
import { useMemo, useState } from 'react'
import {
  aggiungiNota, leggiDecisioni, leggiDomande, leggiNumeri, leggiPerChiamare, leggiSistema, salvaDecisione, togliNota,
  type Call, type Decisione, type Domanda, type NumeriOggi, type Operazione, type RigaConScheda,
} from './dati'
import {
  chiamateInRitardo, dataCorta, daQuanto, durata, giornoRoma, listaDaChiamare, nomeGiorno, ora, perAzienda, perGiorno,
  piuGiorni, quando, titoloDomanda, type DaChiamare,
} from './regole'
import { Bottone, Carico, Errore, Icona, Pillola, Sezione, Vuoto } from './pezzi'
import { linkCompleto, useAvviso, useDati, type Avviso } from './uso'

interface DatiOggi {
  oggi: { dati: NumeriOggi; il: string } | null
  call: Call[]
  righe: RigaConScheda[]
  decisioni: Map<string, Decisione>
  domande: Domanda[]
  sistema: Operazione[]
}

async function caricaOggi(): Promise<DatiOggi> {
  const [numeri, decisioni, domande, sistema] = await Promise.all([leggiNumeri(), leggiDecisioni(), leggiDomande(), leggiSistema()])
  const richiamare = [...decisioni.values()].filter((d) => d.chiamata === 'richiamare').map((d) => d.prospect_id)
  const righe = await leggiPerChiamare(richiamare)
  return { oggi: numeri.oggi ?? null, call: numeri.call?.dati.call ?? [], righe, decisioni, domande, sistema }
}

const BOZZA_FERMA_MIN = 60

export default function Oggi({ apri }: { apri: (id: string) => void }) {
  const { dati, setDati, errore, caricando, rifai } = useDati(caricaOggi)
  const { mostra, vista: avviso } = useAvviso()
  const adesso = new Date()

  const lista = useMemo(() => dati ? listaDaChiamare(dati.righe, dati.decisioni, adesso) : [],
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [dati])
  const domande = useMemo(() => perAzienda((dati?.domande ?? []).filter((d) => d.tipo === 'umano')), [dati])
  const bozze = useMemo(() => perAzienda((dati?.domande ?? []).filter((d) => d.tipo === 'risposta'
    && adesso.getTime() - new Date(d.at).getTime() > BOZZA_FERMA_MIN * 60_000)),
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [dati])
  const call = useMemo(() => {
    const oggi = giornoRoma(adesso)
    const fine = piuGiorni(oggi, 8)
    return (dati?.call ?? []).filter((c) => {
      const g = giornoRoma(new Date(c.at))
      return g >= oggi && g < fine && new Date(c.at).getTime() > adesso.getTime() - 90 * 60_000
    })
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [dati])

  function cambiaDecisione(id: string, d: Decisione | null) {
    setDati((x) => {
      if (!x) return x
      const m = new Map(x.decisioni)
      if (d) m.set(id, d); else m.delete(id)
      return { ...x, decisioni: m }
    })
  }

  if (caricando) return <Carico righe={4} etichetta="Carico la giornata" />
  if (errore && !dati) return <Errore testo={errore} riprova={() => void rifai()} />
  if (!dati) return null

  const niente = !lista.length && !call.length && !domande.length && !bozze.length

  return (
    <div>
      <RigaStato oggi={dati.oggi} lista={lista} sistema={dati.sistema} apri={apri} />
      {errore && <p role="alert" className="mt-3 text-[14px] text-red-800">Non sono riuscito ad aggiornare: {errore}</p>}

      {niente ? (
        <p className="mt-8 text-center text-[17px] font-semibold text-inchiostro">Niente per te adesso.</p>
      ) : (
        <div className="mt-6">
          <Sezione titolo="Da chiamare" conta={lista.length} id="sez-chiamare">
            {lista.length ? (
              <ul className="space-y-3">
                {lista.map((x) => (
                  <li key={x.riga.prospect_id}>
                    <CartaChiamata x={x} apri={apri} mostra={mostra} onCambio={cambiaDecisione} />
                  </li>
                ))}
              </ul>
            ) : <Vuoto>Nessuno da chiamare adesso.</Vuoto>}
          </Sezione>

          <Sezione titolo="Call prenotate" conta={call.length} id="sez-call">
            {call.length ? <ListaCall call={call} apri={apri} /> : <Vuoto>Nessuna call da oggi ai prossimi 7 giorni.</Vuoto>}
          </Sezione>

          <Sezione titolo="Da decidere" conta={domande.length + bozze.length} id="sez-decidere">
            {domande.length || bozze.length ? (
              <DaDecidere domande={domande} bozze={bozze} />
            ) : <Vuoto>Nella Posta non ti aspetta niente.</Vuoto>}
          </Sezione>
        </div>
      )}
      {avviso}
    </div>
  )
}

// ── la riga di stato ───────────────────────────────────────────────────

function RigaStato({ oggi, lista, sistema, apri }: { oggi: DatiOggi['oggi']; lista: DaChiamare[]; sistema: Operazione[]; apri: (id: string) => void }) {
  const adesso = new Date()
  const n = oggi?.dati
  const tardi = chiamateInRitardo(lista, adesso)
  const ritardi = [...(n?.ritardi ?? []), ...tardi.map((x) => `${x.riga.azienda}: aspetta una telefonata ${daQuanto(x.riga.ultima_risposta, adesso)}`)]
  const rosso = ritardi.length > 0
  // il sistema fermo si dice: le schede (questo giro) e il sync delle risposte
  const fermi: string[] = []
  const vecchio = (iso: string | null | undefined, min: number) => !iso || adesso.getTime() - new Date(iso).getTime() > min * 60_000
  if (oggi && vecchio(oggi.il, 40)) fermi.push(`i dati di questa pagina sono fermi a ${quando(oggi.il, adesso)}`)
  const sync = sistema.find((o) => o.chiave === 'sync_smartlead')
  if (sync && (sync.ultimo_esito === 'errore' || vecchio(sync.ultima_corsa, 40))) {
    fermi.push(sync.ultimo_esito === 'errore' ? 'l\'ultimo controllo delle risposte è andato male' : `le risposte non si controllano ${daQuanto(sync.ultima_corsa, adesso)}`)
  }

  return (
    <div role="status" className={`rounded-2xl border px-4 py-3.5 ${rosso ? 'border-red-300 bg-red-50' : 'border-bordo bg-white'}`}>
      {!n ? (
        <p className="text-[15px] text-tenue">I numeri di oggi non sono ancora pronti: arrivano entro dieci minuti.</p>
      ) : (
        <>
          <p className="text-[16px] leading-snug text-inchiostro">
            <b>{n.risposte} {n.risposte === 1 ? 'risposta' : 'risposte'} oggi</b>
            <span className="text-tenue"> · </span>
            {n.si === 0 ? <span>nessun sì</span> : (
              <span>
                <b>{n.si} sì</b>: {n.serviti.length} {n.serviti.length === 1 ? 'servito' : 'serviti'}
                {n.media_minuti != null && <> in {durata(n.media_minuti)} di media</>}
                {n.in_attesa.length > 0 && <>, <b className={rosso ? 'text-red-800' : ''}>{n.in_attesa.length} {n.in_attesa.length === 1 ? 'aspetta' : 'aspettano'}</b></>}
              </span>
            )}
          </p>
          {n.aspetta_da_piu && (
            <p className="mt-1 text-[15px] text-tenue">
              Aspetta da più tempo una risposta:{' '}
              <button onClick={() => apri(n.aspetta_da_piu!.prospect_id)} className="font-semibold text-inchiostro underline decoration-bordo underline-offset-4 hover:decoration-inchiostro">
                {n.aspetta_da_piu.azienda}
              </button>{' '}
              {daQuanto(n.aspetta_da_piu.da, adesso)}
              {n.aspettano > 1 && <> ({n.aspettano} in tutto)</>}
            </p>
          )}
          {rosso && (
            <div className="mt-2 text-[15px] text-red-800">
              <p className="font-bold">In ritardo: {ritardi.length}</p>
              <ul className="mt-0.5 space-y-0.5">
                {ritardi.slice(0, 3).map((r) => <li key={r}>{r}</li>)}
                {ritardi.length > 3 && <li>e altri {ritardi.length - 3}</li>}
              </ul>
            </div>
          )}
        </>
      )}
      {fermi.length > 0 && <p className="mt-2 text-[14px] font-semibold text-amber-900">Attenzione: {fermi.join('; ')}.</p>}
      {oggi && !fermi.length && <p className="mt-1.5 text-[13px] text-tenue">Aggiornato alle {ora(oggi.il)}</p>}
    </div>
  )
}

// ── una persona da chiamare ────────────────────────────────────────────

function CartaChiamata({ x, apri, mostra, onCambio }: {
  x: DaChiamare<RigaConScheda>; apri: (id: string) => void; mostra: (a: Avviso) => void
  onCambio: (id: string, d: Decisione | null) => void
}) {
  const r = x.riga
  const s = r.scheda
  const id = r.prospect_id
  const [lavoro, setLavoro] = useState(false)
  const [quale, setQuale] = useState<'nota' | 'richiamare' | null>(null)
  const [nota, setNota] = useState('')
  const [giorno, setGiorno] = useState(piuGiorni(giornoRoma(), 1))
  const [sbaglio, setSbaglio] = useState<string | null>(null)
  const [primo, ...altri] = s?.telefoni ?? []
  const nonRisponde = x.decisione?.chiamata === 'non_risponde' ? x.decisione : null

  async function segna(cosa: 'chiamato' | 'non_risponde' | 'richiamare') {
    setLavoro(true); setSbaglio(null)
    const prima = x.decisione
    try {
      const adesso = new Date().toISOString()
      const cambia: Partial<Decisione> = cosa === 'chiamato' ? { chiamata: 'chiamato', chiamata_il: adesso, richiamare_il: null }
        : cosa === 'non_risponde' ? { chiamata: 'non_risponde', chiamata_il: adesso, richiamare_il: null, tentativi: (prima?.tentativi ?? 0) + 1 }
          : { chiamata: 'richiamare', chiamata_il: adesso, richiamare_il: giorno }
      const testo = cosa === 'chiamato' ? 'Chiamato' : cosa === 'non_risponde' ? 'Chiamato: non risponde' : `Da richiamare il ${dataCorta(giorno)}`
      const nuova = await salvaDecisione(id, cambia)
      const n = await aggiungiNota(id, testo, 'chiamata')
      onCambio(id, nuova)
      setQuale(null)
      mostra({
        testo: `${r.azienda}: ${testo.toLowerCase()}`,
        annulla: async () => {
          try {
            const indietro = await salvaDecisione(id, {
              chiamata: prima?.chiamata ?? null, chiamata_il: prima?.chiamata_il ?? null,
              richiamare_il: prima?.richiamare_il ?? null, tentativi: prima?.tentativi ?? 0,
            })
            await togliNota(n.id)
            onCambio(id, indietro)
          } catch (e) {
            mostra({ testo: `Non sono riuscito ad annullare: ${e instanceof Error ? e.message : e}` })
          }
        },
      })
    } catch (e) {
      setSbaglio(`Non salvato: ${e instanceof Error ? e.message : e}`)
    } finally {
      setLavoro(false)
    }
  }

  async function salvaNota() {
    if (!nota.trim()) return
    setLavoro(true); setSbaglio(null)
    try {
      await aggiungiNota(id, nota)
      setNota(''); setQuale(null)
      mostra({ testo: `Nota salvata su ${r.azienda}` })
    } catch (e) {
      setSbaglio(`Nota non salvata: ${e instanceof Error ? e.message : e}`)
    } finally {
      setLavoro(false)
    }
  }

  const oggi = giornoRoma()
  const scelte = [
    { g: piuGiorni(oggi, 1), n: 'Domani' },
    { g: piuGiorni(oggi, 2), n: 'Dopodomani' },
    { g: piuGiorni(oggi, 7), n: 'Tra una settimana' },
  ]

  return (
    <article className={`rounded-2xl border bg-white p-4 ${x.motivo === 'richiamare' ? 'border-blu-scuro/40' : 'border-bordo'}`}
             aria-labelledby={`az-${id}`}>
      <button onClick={() => apri(id)} className="block w-full text-left">
        <h3 id={`az-${id}`} className="text-[17px] font-bold leading-snug text-inchiostro hover:underline">{r.azienda}</h3>
        <span className="mt-0.5 block text-[14px] text-tenue">
          {[[s?.nome || r.persona, s?.ruolo].filter(Boolean).join(', '), r.ultima_risposta && `ha scritto ${quando(r.ultima_risposta)}`].filter(Boolean).join(' · ')}
        </span>
      </button>
      <div className="mt-2"><Pillola testo={x.motivo === 'richiamare' ? 'Da richiamare oggi' : (r.perche_chiamare ?? 'Da chiamare')} forte /></div>
      {r.frase && <p className="mt-2 text-[15px] leading-snug text-inchiostro">«{r.frase}»</p>}
      {s?.consiglio && <p className="mt-1 text-[14px] text-tenue">{s.consiglio}</p>}
      {nonRisponde && (
        <p className="mt-1.5 text-[14px] font-semibold text-amber-900">
          Non ha risposto {nonRisponde.tentativi > 1 ? `${nonRisponde.tentativi} volte` : ''} · ultima prova {quando(nonRisponde.chiamata_il)}
        </p>
      )}

      <div className="mt-3">
        {primo ? (
          <a href={`tel:${primo.tel}`} aria-label={`Chiama ${primo.numero}, ${primo.etichetta}`}
             className="flex min-h-14 items-center gap-3 rounded-xl bg-blu-scuro px-4 py-2 text-white hover:bg-navy sm:max-w-md">
            <Icona nome="telefono" className="h-5 w-5 shrink-0" />
            <span className="min-w-0">
              <span className="block whitespace-nowrap text-[17px] font-bold tracking-wide">{primo.numero}</span>
              <span className="block truncate text-[13px] text-white/85">{primo.etichetta}</span>
            </span>
          </a>
        ) : (
          <p className="text-[15px] text-tenue">Nessun numero trovato: né nella firma né nella scheda. Aprila per scrivergli.</p>
        )}
        {altri.length > 0 && (
          <ul className="mt-1.5 space-y-0.5">
            {altri.map((t) => (
              <li key={t.tel} className="text-[14px]">
                <a href={`tel:${t.tel}`} className="inline-flex min-h-9 items-center font-semibold text-blu-scuro hover:underline">{t.numero}</a>
                <span className="text-tenue"> · {t.etichetta}</span>
              </li>
            ))}
          </ul>
        )}
      </div>

      <div className="mt-3 flex flex-wrap gap-2">
        <Bottone onClick={() => void segna('chiamato')} disabled={lavoro}>Chiamato</Bottone>
        <Bottone onClick={() => void segna('non_risponde')} disabled={lavoro}>Non risponde</Bottone>
        <Bottone onClick={() => setQuale(quale === 'richiamare' ? null : 'richiamare')} disabled={lavoro}>Richiamare il…</Bottone>
        <Bottone tipo="piatto" onClick={() => setQuale(quale === 'nota' ? null : 'nota')} disabled={lavoro}>Nota</Bottone>
      </div>

      {quale === 'richiamare' && (
        <fieldset className="mt-3 rounded-xl bg-velo p-3">
          <legend className="sr-only">Quando richiamare</legend>
          <div className="flex flex-wrap gap-2">
            {scelte.map((c) => (
              <button key={c.g} onClick={() => setGiorno(c.g)} aria-pressed={giorno === c.g}
                      className={`min-h-10 rounded-full border px-3 text-[14px] font-semibold ${giorno === c.g ? 'border-blu-scuro bg-white text-blu-scuro' : 'border-bordo bg-white text-inchiostro'}`}>
                {c.n}
              </button>
            ))}
            <label className="flex min-h-10 items-center gap-2 rounded-full border border-bordo bg-white px-3 text-[14px]">
              <span className="text-tenue">Il</span>
              <input type="date" value={giorno} min={piuGiorni(oggi, 1)} onChange={(e) => setGiorno(e.target.value)}
                     className="bg-transparent font-semibold text-inchiostro outline-none" aria-label="Giorno in cui richiamare" />
            </label>
          </div>
          <div className="mt-2.5 flex gap-2">
            <Bottone tipo="primo" onClick={() => void segna('richiamare')} disabled={lavoro || !giorno}>Richiama il {dataCorta(giorno)}</Bottone>
            <Bottone tipo="piatto" onClick={() => setQuale(null)}>Annulla</Bottone>
          </div>
        </fieldset>
      )}

      {quale === 'nota' && (
        <form className="mt-3" onSubmit={(e) => { e.preventDefault(); void salvaNota() }}>
          <label htmlFor={`nota-${id}`} className="sr-only">Nota su {r.azienda}</label>
          <textarea id={`nota-${id}`} value={nota} onChange={(e) => setNota(e.target.value)} rows={3} autoFocus
                    placeholder="Cosa ti ha detto, cosa fare dopo"
                    className="w-full rounded-xl border border-bordo px-3 py-2 text-[15px] outline-none focus:border-blu-scuro" />
          <div className="mt-2 flex gap-2">
            <Bottone tipo="primo" type="submit" disabled={lavoro || !nota.trim()}>Salva la nota</Bottone>
            <Bottone tipo="piatto" onClick={() => { setQuale(null); setNota('') }}>Annulla</Bottone>
          </div>
        </form>
      )}
      {sbaglio && <p role="alert" className="mt-2 text-[14px] font-semibold text-red-800">{sbaglio}</p>}
    </article>
  )
}

// ── le call ────────────────────────────────────────────────────────────

const TIPO_CALL: Record<string, string> = { conoscitiva: 'Conoscitiva', tecnica: 'Call tecnica', avvio: 'Avvio', altro: 'Call' }

function ListaCall({ call, apri }: { call: Call[]; apri: (id: string) => void }) {
  return (
    <div className="space-y-4">
      {perGiorno(call).map(({ giorno, call: cc }) => (
        <div key={giorno}>
          <h3 className="mb-1.5 text-[14px] font-semibold text-tenue">{nomeGiorno(giorno)}</h3>
          <ul className="divide-y divide-velo overflow-hidden rounded-2xl border border-bordo bg-white">
            {cc.map((c) => {
              const nome = c.azienda || c.titolo
              const dentro = (
                <>
                  <span className="w-14 shrink-0 text-[16px] font-bold text-inchiostro">{ora(c.at)}</span>
                  <span className="min-w-0 flex-1">
                    <span className="block truncate text-[15px] font-semibold text-inchiostro">{nome}</span>
                    <span className="block truncate text-[13px] text-tenue">
                      {TIPO_CALL[c.tipo] ?? 'Call'}{c.di_chi && ` · nel calendario di ${c.di_chi}`}
                    </span>
                  </span>
                </>
              )
              return (
                <li key={`${c.at}-${nome}`} className="flex items-center gap-2 pr-2">
                  {c.prospect_id ? (
                    <button onClick={() => apri(c.prospect_id!)} className="flex min-h-14 min-w-0 flex-1 items-center gap-3 px-4 py-2 text-left hover:bg-velo">
                      {dentro}
                    </button>
                  ) : <div className="flex min-h-14 min-w-0 flex-1 items-center gap-3 px-4 py-2">{dentro}</div>}
                  {c.meet && (
                    <a href={c.meet} target="_blank" rel="noreferrer" aria-label={`Apri il Meet della call con ${nome}`}
                       className="flex h-11 w-11 shrink-0 items-center justify-center rounded-full text-blu-scuro hover:bg-velo">
                      <Icona nome="video" />
                    </a>
                  )}
                </li>
              )
            })}
          </ul>
        </div>
      ))}
    </div>
  )
}

// ── da decidere ────────────────────────────────────────────────────────

function DaDecidere({ domande, bozze }: { domande: Array<{ ultima: Domanda; quante: number }>; bozze: Array<{ ultima: Domanda; quante: number }> }) {
  const [tutte, setTutte] = useState(false)
  const quante = tutte ? 50 : 5
  const riga = (x: { ultima: Domanda; quante: number }) => (
    <li key={x.ultima.id}>
      <a href={linkCompleto('posta')} className="flex min-h-12 items-center gap-3 px-4 py-2 hover:bg-velo">
        <span className="min-w-0 flex-1">
          <span className="block truncate text-[15px] font-semibold text-inchiostro">{titoloDomanda(x.ultima.titolo)}</span>
          <span className="block truncate text-[13px] text-tenue">
            {x.ultima.perche ? x.ultima.perche : 'Da guardare'}{x.quante > 1 && ` · ${x.quante} in sospeso`}
          </span>
        </span>
        <span className="shrink-0 text-[13px] text-tenue">{daQuanto(x.ultima.at)}</span>
      </a>
    </li>
  )
  return (
    <div className="space-y-4">
      {domande.length > 0 && (
        <div>
          <h3 className="mb-1.5 text-[14px] font-semibold text-tenue">Domande per te · {domande.length} aziende</h3>
          <ul className="divide-y divide-velo overflow-hidden rounded-2xl border border-bordo bg-white">{domande.slice(0, quante).map(riga)}</ul>
        </div>
      )}
      {bozze.length > 0 && (
        <div>
          <h3 className="mb-1.5 text-[14px] font-semibold text-tenue">Bozze ferme da più di un'ora · {bozze.length}</h3>
          <ul className="divide-y divide-velo overflow-hidden rounded-2xl border border-bordo bg-white">{bozze.slice(0, quante).map(riga)}</ul>
        </div>
      )}
      <div className="flex flex-wrap items-center gap-2">
        <a href={linkCompleto('posta')} className="inline-flex min-h-11 items-center gap-1.5 rounded-full bg-blu-scuro px-4 text-[14px] font-semibold text-white hover:bg-navy">
          Decidi nella Posta <Icona nome="esterno" className="h-4 w-4" />
        </a>
        {(domande.length > 5 || bozze.length > 5) && (
          <Bottone tipo="piatto" onClick={() => setTutte(!tutte)}>{tutte ? 'Mostra meno' : 'Mostra tutte'}</Bottone>
        )}
      </div>
    </div>
  )
}
