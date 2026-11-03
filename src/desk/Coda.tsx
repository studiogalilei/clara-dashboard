// LA CODA: ogni relazione aperta con la mossa che Clara ha scelto e il testo pronto. Dre legge,
// tocca Invia (o aggiusta il testo e poi Invia), o dice No con una riga di perche'. Le call e le
// cose sue (Decidi tu) si chiudono con un esito. Sul computer: elenco a sinistra, scheda a destra;
// sul telefono: elenco, poi la scheda.
import { useEffect, useMemo, useState } from 'react'
import { approva, giudica, leggiCoda, salvaTesto, scarta, segnaEsito, type Decisione } from './dati'
import { conta, destinatari, ESITI_CHIAMATA, ESITI_TUA, filtra, FILTRI, iniziali, MOSSE, ordina, priorita, statoBreve, telefonoDa, type Filtro } from './regole'
import { Bottone, Carico, Errore, Icona, Pillola, Vuoto } from '../snella/pezzi'
import { useAvviso, useDati } from '../snella/uso'
import { quando } from '../snella/regole'
import { TONO } from '../snella/toni'
import type { Dove } from './Desk'

export default function Coda({ dove, vai, indietro }: { dove: Dove; vai: (d: Dove) => void; indietro: () => void }) {
  const { dati, setDati, errore, caricando, rifai } = useDati(() => leggiCoda(30))
  const [filtro, setFiltro] = useState<Filtro>('tutte')
  const [q, setQ] = useState('')
  const { mostra, vista } = useAvviso()
  const adesso = new Date()
  // eslint-disable-next-line react-hooks/exhaustive-deps
  const righe = useMemo(() => dati ? ordina(filtra(dati, filtro, q), new Date()) : [], [dati, filtro, q])
  const conti = useMemo(() => dati ? conta(dati) : null, [dati])
  const scelta = dati?.find((d) => d.id === dove.id) ?? null
  // sul computer, senza una scelta, si apre la prima della coda
  const prima = righe[0] ?? null

  const aggiorna = (d: Decisione) => setDati((prev) => prev ? prev.map((x) => x.id === d.id ? d : x) : prev)

  if (caricando) return <Carico righe={4} etichetta="Carico la coda" />
  if (errore && !dati) return <Errore testo={errore} riprova={() => void rifai()} />

  const Elenco = (
    <section className="rounded-2xl border border-bordo bg-white">
      <header className="border-b border-bordo p-4 lg:p-5">
        <div className="flex items-start justify-between gap-3">
          <div>
            <h1 className="text-[22px] font-bold leading-tight text-navy lg:text-[26px]">La coda</h1>
            <p className="mt-1 text-[13.5px] text-tenue">Clara ha letto ogni risposta e preparato la mossa. Tu: Invia, aggiusta, o No.</p>
          </div>
          {conti && <span className="shrink-0 rounded-full bg-navy/[0.08] px-3 py-1 text-[13px] font-bold text-navy">{conti.tutte} da fare</span>}
        </div>
        <div className="mt-3 flex gap-1.5 overflow-x-auto pb-1 [-ms-overflow-style:none] [scrollbar-width:none] [&::-webkit-scrollbar]:hidden">
          {FILTRI.map((f) => (
            <button key={f.f} onClick={() => setFiltro(f.f)} aria-pressed={filtro === f.f}
                    className={`min-h-9 shrink-0 rounded-full border px-3 text-[13px] font-semibold ${filtro === f.f ? 'border-navy bg-navy text-white' : 'border-bordo bg-white text-tenue hover:border-tenue'}`}>
              {f.nome}{conti && conti[f.f] ? <span className="ml-1 opacity-70">{conti[f.f]}</span> : null}
            </button>
          ))}
        </div>
        <label className="mt-3 flex min-h-10 items-center gap-2 rounded-xl border border-bordo bg-white px-3 text-tenue focus-within:border-navy">
          <Icona nome="cerca" className="h-4 w-4 shrink-0" />
          <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Cerca azienda o persona" aria-label="Cerca"
                 className="min-w-0 flex-1 bg-transparent text-[14px] text-inchiostro outline-none placeholder:text-spento" />
        </label>
      </header>
      {righe.length === 0 ? <Vuoto>Niente qui. {filtro === 'tutte' ? 'La coda è vuota: Clara non ha mosse da farti vedere.' : 'Prova un altro filtro.'}</Vuoto> : (
        <ul>
          {righe.map((d) => {
            const su = (scelta ?? prima)?.id === d.id
            const s = statoBreve(d)
            return (
              <li key={d.id} className="border-b border-velo last:border-0">
                <button onClick={() => vai({ voce: 'coda', id: d.id })} aria-current={su ? 'true' : undefined}
                        className={`grid w-full grid-cols-[44px_minmax(0,1fr)_auto] items-center gap-3 px-4 py-3 text-left hover:bg-fondo/70 ${su ? 'bg-navy/[0.05] shadow-[inset_3px_0_0_var(--color-navy)]' : ''}`}>
                  <span className={`grid h-9 w-11 place-items-center rounded-lg text-[13px] font-extrabold ${priorita(d, adesso) >= 90 ? 'bg-navy/[0.1] text-navy' : 'bg-velo text-tenue'}`}>{priorita(d, adesso)}</span>
                  <span className="min-w-0">
                    <span className="block truncate text-[14.5px] font-bold text-inchiostro">{d.azienda || d.email}</span>
                    <span className="block truncate text-[12.5px] text-tenue">{[[d.persona, d.citta].filter(Boolean).join(', '), d.lead_testo ? `“${d.lead_testo.replace(/\s+/g, ' ').slice(0, 70)}”` : ''].filter(Boolean).join(' · ')}</span>
                  </span>
                  <span className="flex flex-col items-end gap-1">
                    <Pillola testo={s.testo.length > 26 ? s.testo.slice(0, 24) + '…' : s.testo} tono={s.tono} />
                    <span className="text-[11.5px] text-tenue">{quando(d.risposta_il)}</span>
                  </span>
                </button>
              </li>
            )
          })}
        </ul>
      )}
    </section>
  )

  const dett = scelta ?? prima
  return (
    <>
      {/* sul telefono: elenco o scheda; sul computer: tutte e due */}
      <div className="lg:grid lg:grid-cols-[minmax(0,1.25fr)_minmax(380px,1fr)] lg:items-start lg:gap-4">
        <div className={scelta ? 'hidden lg:block' : ''}>{Elenco}</div>
        <div className={scelta ? '' : 'hidden lg:block'}>
          {dett ? <Scheda key={dett.id} d={dett} indietro={indietro} aggiorna={aggiorna} mostra={mostra} vaiRelazione={() => vai({ voce: 'relazioni', id: dett.prospect_id })} />
            : <div className="rounded-2xl border border-bordo bg-white p-8 text-center text-tenue">Scegli una riga.</div>}
        </div>
      </div>
      {vista}
    </>
  )
}

function Scheda({ d, indietro, aggiorna, mostra, vaiRelazione }: {
  d: Decisione; indietro: () => void; aggiorna: (d: Decisione) => void; mostra: (a: { testo: string }) => void; vaiRelazione: () => void
}) {
  const m = MOSSE[d.mossa]
  const parti = destinatari(d.testo)
  const [testo, setTesto] = useState(parti.corpo)
  const [modifico, setModifico] = useState(false)
  const [chiedoNo, setChiedoNo] = useState(false)
  const [motivo, setMotivo] = useState('')
  const [lavoro, setLavoro] = useState(false)
  const s = statoBreve(d)
  const aperta = d.stato === 'proposta'
  const inPartenza = d.stato === 'approvata' || d.stato === 'in_invio'
  useEffect(() => { setTesto(destinatari(d.testo).corpo); setModifico(false); setChiedoNo(false) }, [d.id, d.testo])

  const testoIntero = () => {
    const testa = [parti.a ? `A: ${parti.a}${parti.cc ? ` — Cc: ${parti.cc}` : ''}` : null, parti.oggetto ? `Oggetto: ${parti.oggetto}` : null].filter(Boolean)
    return [...testa, testa.length ? '' : null, testo].filter((x) => x !== null).join('\n')
  }
  const fai = async (cosa: () => Promise<void>, dopo: Partial<Decisione>, detto: string) => {
    setLavoro(true)
    try { await cosa(); aggiorna({ ...d, ...dopo }); mostra({ testo: detto }) } catch (e) { mostra({ testo: e instanceof Error ? e.message : String(e) }) } finally { setLavoro(false) }
  }
  const invia = () => fai(() => approva(d, testoIntero()), { stato: 'approvata', approvata_il: new Date().toISOString(), testo: testoIntero(), dre_giudizio: 'ok', errore: null }, 'In partenza: parte entro pochi minuti dal thread di Smartlead.')
  const no = () => fai(() => scarta(d.id, motivo), { stato: 'scartata', dre_giudizio: 'no' }, 'Scartata. Clara se lo segna.')
  const esito = (e: string) => fai(() => segnaEsito(d.id, e), { stato: 'fatta', esito: e, esito_il: new Date().toISOString() }, 'Segnato.')
  const okCosi = () => fai(() => giudica(d.id, true), { dre_giudizio: 'ok' }, 'Bene: Clara impara che va bene così.')
  const nonCosi = () => fai(() => giudica(d.id, false, motivo), { dre_giudizio: 'no' }, 'Segnato: Clara impara.')

  return (
    <section className="rounded-2xl border border-bordo bg-white lg:sticky lg:top-6 lg:max-h-[calc(100dvh-3rem)] lg:overflow-y-auto">
      <header className="border-b border-bordo p-4 lg:p-5">
        <div className="mb-3 flex items-center justify-between">
          <button onClick={indietro} className="-ml-2 inline-flex min-h-10 items-center gap-1 rounded-full px-2 text-[14px] font-semibold text-navy lg:hidden"><Icona nome="indietro" className="h-4 w-4" /> Coda</button>
          <button onClick={vaiRelazione} className="ml-auto inline-flex min-h-9 items-center gap-1.5 rounded-full border border-bordo px-3 text-[12.5px] font-semibold text-tenue hover:border-tenue hover:text-inchiostro"><Icona nome="lead" className="h-3.5 w-3.5" /> Tutto il filo</button>
        </div>
        <div className="flex items-center gap-3">
          <span className="grid h-11 w-11 shrink-0 place-items-center rounded-xl bg-navy/[0.08] text-[15px] font-extrabold text-navy">{iniziali(d.azienda)}</span>
          <div className="min-w-0">
            <h2 className="truncate text-[18px] font-bold leading-tight text-inchiostro">{d.azienda || d.email}</h2>
            <p className="truncate text-[13px] text-tenue">{[d.persona, d.ruolo, d.citta, d.settore].filter(Boolean).join(' · ').replace(/ · /g, ', ')}</p>
          </div>
        </div>
        <div className="mt-3 flex flex-wrap gap-1.5">
          <Pillola testo={m.nome} tono={m.tono} piena={d.mossa === 'callback' || d.mossa === 'book_meeting'} />
          {!aperta && <Pillola testo={s.testo} tono={s.tono} />}
          {d.analisi_mandata && <Pillola testo="Analisi mandata" tono="noi" />}
          {d.fase && !['risposto', 'in_follow_up'].includes(d.fase) && <Pillola testo={d.fase.replace(/_/g, ' ')} tono="neutro" />}
          {d.prossima_call && <Pillola testo={`Call ${quando(d.prossima_call)}`} tono="opp" icona="video" />}
        </div>
      </header>

      <div className="space-y-4 p-4 lg:p-5">
        {d.lead_testo && (
          <Blocco titolo={`Ha scritto ${quando(d.risposta_il)}`}>
            <blockquote className="whitespace-pre-wrap rounded-r-xl border-l-2 border-loro-segno bg-loro-fondo/60 px-3.5 py-3 text-[14px] leading-relaxed text-inchiostro">{d.lead_testo.trim().slice(0, 1200)}</blockquote>
          </Blocco>
        )}
        <Blocco titolo="Clara">
          <p className="text-[14px] leading-relaxed text-inchiostro">{d.perche}</p>
          {d.richiamo?.numero && <p className="mt-2 text-[14px]"><span className="text-tenue">Numero:</span> <a href={`tel:${(telefonoDa(d.richiamo.numero) ?? d.richiamo.numero).replace(/[^\d+]/g, '')}`} className="font-bold text-navy underline-offset-2 hover:underline">{telefonoDa(d.richiamo.numero) ?? d.richiamo.numero}</a>{d.richiamo.quando ? <span className="text-tenue"> · {d.richiamo.quando}</span> : null}</p>}
          {!d.richiamo?.numero && d.telefono && d.mossa === 'callback' && <p className="mt-2 text-[14px]"><span className="text-tenue">Numero in scheda:</span> <a href={`tel:${d.telefono.replace(/\s/g, '')}`} className="font-bold text-navy underline-offset-2 hover:underline">{d.telefono}</a></p>}
          {d.giudice?.pericoloso && <p className={`mt-2 rounded-lg border px-3 py-2 text-[13px] ${TONO.no.morbido}`}>Il revisore segnala: {d.giudice.errore_pericoloso}</p>}
          {d.errore && aperta && <p className={`mt-2 rounded-lg border px-3 py-2 text-[13px] ${TONO.attesa.morbido}`}>Non è partita: {d.errore}</p>}
        </Blocco>

        {m.scrive && (
          <Blocco titolo={aperta ? 'La mail che parte' : 'La mail'}>
            {(parti.a || parti.oggetto) && (
              <p className="mb-2 text-[12.5px] text-tenue">{parti.a && <>A <b className="text-inchiostro">{parti.a}</b>{parti.cc && <> · Cc <b className="text-inchiostro">{parti.cc}</b></>}</>}{parti.oggetto && <> · Oggetto: <b className="text-inchiostro">{parti.oggetto}</b></>}</p>
            )}
            {modifico && aperta ? (
              <textarea value={testo} onChange={(e) => setTesto(e.target.value)} rows={Math.min(18, Math.max(8, testo.split('\n').length + 2))}
                        className="w-full rounded-xl border border-navy bg-white p-3 text-[14px] leading-relaxed text-inchiostro outline-none" />
            ) : (
              <pre className="whitespace-pre-wrap rounded-xl bg-fondo/70 p-3.5 font-sans text-[14px] leading-relaxed text-inchiostro">{testo}</pre>
            )}
            {d.mossa === 'send_analysis' && <p className="mt-2 text-[12.5px] text-tenue">{d.analisi_pdf ? 'Allega il PDF dell’analisi' + (d.analisi_mandata ? '.' : ' e la presentazione.') : 'Il PDF non è ancora pronto: parte appena c’è.'}</p>}
            {d.mossa === 'book_meeting' && <p className="mt-2 text-[12.5px] text-tenue">Ricorda l’invito dal calendario: la mail dice che arriva.</p>}
          </Blocco>
        )}
      </div>

      <footer className="space-y-2 border-t border-bordo p-4 lg:p-5">
        {aperta && m.scrive && !chiedoNo && (
          <>
            <div className="grid grid-cols-2 gap-2">
              <Bottone tipo="primo" onClick={() => void invia()} disabled={lavoro || !testo.trim()} className="col-span-2">
                <Icona nome="mail" className="h-4 w-4" /> {modifico ? 'Invia così' : m.bottone}
              </Bottone>
              {modifico
                ? <Bottone onClick={() => { void salvaTesto(d.id, testoIntero()); setModifico(false); aggiorna({ ...d, testo: testoIntero() }) }} disabled={lavoro}>Salva senza inviare</Bottone>
                : <Bottone onClick={() => setModifico(true)} disabled={lavoro}>Modifica</Bottone>}
              <Bottone onClick={() => setChiedoNo(true)} disabled={lavoro}>No</Bottone>
            </div>
            <p className="text-[12px] text-tenue">Invia = parte entro 5 minuti dalla casella della campagna, nel thread. Se cambi il testo, Clara lo impara.</p>
          </>
        )}
        {aperta && d.mossa === 'callback' && !chiedoNo && (
          <>
            <p className="text-[12.5px] font-semibold text-tenue">Dopo la chiamata:</p>
            <div className="grid grid-cols-2 gap-2">
              {ESITI_CHIAMATA.map((e) => <Bottone key={e.esito} tipo={e.esito === 'fissata' ? 'primo' : 'secondo'} onClick={() => void esito(e.esito)} disabled={lavoro}>{e.nome}</Bottone>)}
            </div>
            <Bottone tipo="piatto" onClick={() => setChiedoNo(true)} disabled={lavoro} className="w-full">Non andava chiamato</Bottone>
          </>
        )}
        {aperta && d.mossa === 'escalate' && !chiedoNo && (
          <>
            <p className="text-[12.5px] font-semibold text-tenue">Questa è tua. Quando hai fatto:</p>
            <div className="grid grid-cols-3 gap-2">
              {ESITI_TUA.map((e) => <Bottone key={e.esito} onClick={() => void esito(e.esito)} disabled={lavoro} className="px-2 text-[13px]">{e.nome}</Bottone>)}
            </div>
            <Bottone tipo="piatto" onClick={() => setChiedoNo(true)} disabled={lavoro} className="w-full">Poteva farlo Clara</Bottone>
          </>
        )}
        {aperta && (d.mossa === 'wait' || d.mossa === 'close') && !chiedoNo && d.dre_giudizio !== 'ok' && (
          <div className="grid grid-cols-2 gap-2">
            <Bottone onClick={() => void okCosi()} disabled={lavoro}>{m.bottone}</Bottone>
            <Bottone onClick={() => setChiedoNo(true)} disabled={lavoro}>No, avrei fatto altro</Bottone>
          </div>
        )}
        {chiedoNo && (
          <div className="space-y-2">
            <label className="block text-[13px] font-semibold text-inchiostro">Cosa avresti fatto tu? (una riga basta, Clara impara da qui)</label>
            <textarea value={motivo} onChange={(e) => setMotivo(e.target.value)} rows={3} autoFocus className="w-full rounded-xl border border-navy p-3 text-[14px] outline-none" />
            <div className="grid grid-cols-2 gap-2">
              <Bottone tipo="primo" onClick={() => void ((m.scrive || d.mossa === 'callback' || d.mossa === 'escalate') ? no() : nonCosi())} disabled={lavoro}>Conferma il No</Bottone>
              <Bottone onClick={() => setChiedoNo(false)} disabled={lavoro}>Annulla</Bottone>
            </div>
          </div>
        )}
        {inPartenza && <p className={`rounded-lg border px-3 py-2 text-[13px] ${TONO.attesa.morbido}`}>In partenza{d.approvata_il ? `, approvata ${quando(d.approvata_il)}` : ''}. {d.errore ? `Il postino dice: ${d.errore}` : 'Il postino la manda al prossimo giro.'}</p>}
        {d.stato === 'inviata' && <p className={`rounded-lg border px-3 py-2 text-[13px] ${TONO.ok.morbido}`}>Inviata {quando(d.inviata_il)}{d.verificata_il ? ', vista nel thread.' : '.'}</p>}
        {d.stato === 'fatta' && <p className={`rounded-lg border px-3 py-2 text-[13px] ${TONO.ok.morbido}`}>Fatto: {d.esito} ({quando(d.esito_il)})</p>}
        {(d.stato === 'scartata' || d.stato === 'superata') && <p className="rounded-lg border border-bordo px-3 py-2 text-[13px] text-tenue">{s.testo}.</p>}
        {aperta && d.dre_giudizio === 'ok' && (d.mossa === 'wait' || d.mossa === 'close') && <p className="text-[13px] text-tenue">Hai detto che va bene così.</p>}
      </footer>
    </section>
  )
}

function Blocco({ titolo, children }: { titolo: string; children: React.ReactNode }) {
  return (
    <div>
      <h3 className="mb-1.5 text-[11.5px] font-extrabold uppercase tracking-[.08em] text-tenue">{titolo}</h3>
      {children}
    </div>
  )
}
