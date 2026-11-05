// LE RELAZIONI (ex Coda, 4/11): ogni relazione aperta con la mossa che Clara ha scelto e il testo pronto. Dre legge,
// tocca Invia (o aggiusta il testo e poi Invia), o dice No con una riga di perche'. Le call e le
// cose sue (Decidi tu) si chiudono con un esito. Sul computer: elenco a sinistra, scheda a destra;
// sul telefono: elenco, poi la scheda.
import { useEffect, useMemo, useState } from 'react'
import { aggiungiNota, approva, cerca, chiamataDaDecisione, esitoChiamata, giudica, invitoFatto, leggiCoda, nonInteressato, prendiInMano, programmaChiamata, rimanda, salvaTesto, scarta, scriviNota, segnaChiamato, segnaConsiglio, segnaEsito, suWhatsapp, telefonoDre, type Decisione, type Trovato } from './dati'
import { NotaUnica } from './Note'
import { consiglioNuovo, conta, destinatari, ESITI_CHIAMATA, ESITI_TUA, filtra, FILTRI, interesse, MOSSE, MOTIVI_IN_MANO, ordina, statoBreve, telefonoDa, whatsappDa, type Filtro } from './regole'
import { Bottone, Carico, Errore, Icona, Pillola, Vuoto } from '../snella/pezzi'
import { useAvviso, useDati } from '../snella/uso'
import { quando } from '../snella/regole'
import { TONO } from '../snella/toni'
import type { Dove } from './Desk'
import { NumeroDre } from './NumeroDre'

export default function Relazioni({ dove, vai, indietro }: { dove: Dove; vai: (d: Dove) => void; indietro: () => void }) {
  const { dati, setDati, errore, caricando, rifai } = useDati(() => leggiCoda(30))
  const [filtro, setFiltro] = useState<Filtro>('tutte')
  const [tendina, setTendina] = useState(false)
  const [q, setQ] = useState('')
  const { mostra, vista } = useAvviso()
  const adesso = new Date()
  // la ricerca tra TUTTE le aziende (non solo quelle con una decisione): si apre il filo
  const [altre, setAltre] = useState<Trovato[]>([])
  useEffect(() => {
    const t = q.trim()
    if (t.length < 2) { setAltre([]); return }
    let vivo = true
    const h = setTimeout(() => { cerca(t).then((r) => { if (vivo) setAltre(r) }).catch(() => { if (vivo) setAltre([]) }) }, 350)
    return () => { vivo = false; clearTimeout(h) }
  }, [q])
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
            <h1 className="text-[22px] font-bold leading-tight text-inchiostro lg:text-[26px]">Relazioni</h1>
          </div>
          {conti && <span className="shrink-0 rounded-lg bg-navy/[0.08] px-3 py-1 text-[13px] font-bold text-navy">{conti.tutte} da fare</span>}
        </div>
        {/* 4/11, Dre: «un bottone solo, clicco e in tendina escono gli altri» */}
        <div className="relative mt-3 flex items-center gap-2">
          <button onClick={() => setTendina((v) => !v)} aria-haspopup="listbox" aria-expanded={tendina}
                  className="inline-flex min-h-10 items-center gap-2 rounded-xl border border-bordo bg-white px-3.5 text-[14px] font-bold text-inchiostro hover:border-tenue">
            {FILTRI.find((f) => f.f === filtro)?.nome}{conti ? <span className="font-semibold text-tenue">{conti[filtro]}</span> : null}
            <Icona nome="indietro" className={`h-3.5 w-3.5 text-tenue transition-transform ${tendina ? 'rotate-90' : '-rotate-90'}`} />
          </button>
          {tendina && (
            <>
              <button aria-label="Chiudi" onClick={() => setTendina(false)} className="fixed inset-0 z-10 cursor-default bg-transparent" />
              <ul role="listbox" className="absolute left-0 top-full z-20 mt-1 min-w-[240px] overflow-hidden rounded-xl border border-bordo bg-white py-1 shadow-lg">
                {FILTRI.map((f) => (
                  <li key={f.f} role="option" aria-selected={filtro === f.f}>
                    <button onClick={() => { setFiltro(f.f); setTendina(false) }}
                            className={`flex w-full items-center justify-between gap-4 px-3.5 py-2 text-left text-[14px] ${filtro === f.f ? 'bg-navy/[0.06] font-bold text-inchiostro' : 'text-inchiostro hover:bg-fondo'}`}>
                      {f.nome}<span className="text-[13px] font-semibold text-tenue">{conti ? conti[f.f] : ''}</span>
                    </button>
                  </li>
                ))}
              </ul>
            </>
          )}
        </div>
        <label className="mt-3 flex min-h-10 items-center gap-2 rounded-xl border border-bordo bg-white px-3 text-tenue focus-within:border-navy">
          <Icona nome="cerca" className="h-4 w-4 shrink-0" />
          <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Cerca azienda o persona" aria-label="Cerca"
                 className="min-w-0 flex-1 bg-transparent text-[14px] text-inchiostro outline-none placeholder:text-spento" />
        </label>
      </header>
      {altre.length > 0 && altre.some((t) => !dati?.some((d) => d.prospect_id === t.id)) && (
        <div className="border-b border-bordo px-3 pt-3 lg:px-4">
          <p className="mb-1.5 text-[11.5px] font-extrabold uppercase tracking-[.08em] text-tenue">Altre aziende</p>
          <ul className="space-y-1.5 pb-3">
            {altre.filter((t) => !dati?.some((d) => d.prospect_id === t.id)).slice(0, 8).map((t) => (
              <li key={t.id}><button onClick={() => vai({ voce: 'filo', id: t.id })} className="flex w-full items-center justify-between gap-3 rounded-xl border border-bordo px-3.5 py-2 text-left hover:border-tenue">
                <span className="min-w-0"><span className="block truncate text-[14px] font-bold text-inchiostro">{t.azienda || t.email}</span><span className="block truncate text-[12px] text-tenue">{[t.persona, t.citta].filter(Boolean).join(', ')}</span></span>
                <span className="shrink-0 text-[12px] text-tenue">{t.fase ? t.fase.replace(/_/g, ' ') : 'apri'}</span>
              </button></li>
            ))}
          </ul>
        </div>
      )}
      {righe.length === 0 ? <Vuoto>Niente qui. {filtro === 'tutte' ? 'Nessuna relazione da fare: Clara ha tutto in mano.' : 'Prova un altro filtro.'}</Vuoto> : (
        <ul className="space-y-2 p-3 lg:p-4">
          {righe.map((d) => {
            const su = (scelta ?? prima)?.id === d.id
            const s = statoBreve(d)
            return (
              <li key={d.id}>
                <button onClick={() => vai({ voce: 'relazioni', id: d.id })} aria-current={su ? 'true' : undefined}
                        className={`grid w-full grid-cols-[44px_minmax(0,1fr)_auto] items-center gap-3 rounded-xl border px-3.5 py-3 text-left transition-colors ${su ? 'border-navy/40 bg-navy/[0.05]' : 'border-bordo bg-white hover:border-tenue hover:bg-fondo/60'}`}>
                  <span title={`Interesse ${interesse(d, adesso)} su 10`} className={`grid h-9 w-11 place-items-center rounded-lg text-[14px] font-extrabold ${interesse(d, adesso) >= 8 ? 'bg-ok-testo text-white' : interesse(d, adesso) >= 5 ? 'bg-navy/[0.1] text-navy' : 'bg-velo text-tenue'}`}>{interesse(d, adesso)}</span>
                  <span className="min-w-0">
                    <span className="block truncate text-[14.5px] font-bold text-inchiostro">{d.azienda || d.email}</span>
                    <span className="block truncate text-[12.5px] text-tenue">{[[d.persona, d.citta].filter(Boolean).join(', '), d.lead_testo ? `“${d.lead_testo.replace(/\s+/g, ' ').slice(0, 70)}”` : ''].filter(Boolean).join(', ')}</span>
                  </span>
                  <span className="flex flex-col items-end gap-1">
                    {d.in_mano_a ? <Pillola testo="Me ne occupo io" tono="stop" />
                      : consiglioNuovo(d) ? <Pillola testo="Consigliato chiamare" tono="loro" piena />
                        : <Pillola testo={s.testo.length > 26 ? s.testo.slice(0, 24) + '…' : s.testo} tono={s.tono} piena={s.tono === 'ok'} />}
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
        <div className={`lg:self-stretch ${scelta ? '' : 'hidden lg:block'}`}>
          {dett ? <Scheda key={dett.id} d={dett} indietro={indietro} aggiorna={aggiorna} mostra={mostra} vaiRelazione={() => vai({ voce: 'filo', id: dett.prospect_id })} vaiCall={() => vai({ voce: 'call', id: dett.id })} />
            : <div className="rounded-2xl border border-bordo bg-white p-8 text-center text-tenue">Scegli una riga.</div>}
        </div>
      </div>
      {vista}
    </>
  )
}

function Scheda({ d, indietro, aggiorna, mostra, vaiRelazione, vaiCall }: {
  d: Decisione; indietro: () => void; aggiorna: (d: Decisione) => void; mostra: (a: { testo: string }) => void; vaiRelazione: () => void; vaiCall: () => void
}) {
  const m = MOSSE[d.mossa]
  const parti = destinatari(d.testo)
  const [testo, setTesto] = useState(parti.corpo)
  const [modifico, setModifico] = useState(false)
  const [chiedoNo, setChiedoNo] = useState(false)
  const [chiedoMia, setChiedoMia] = useState(false)
  const [richiamo, setRichiamo] = useState<string | null>(null)       // la data in cui richiamare, quando si sceglie «Richiamare»
  const [motivo, setMotivo] = useState('')
  const [lavoro, setLavoro] = useState(false)
  const s = statoBreve(d)
  const mia = !!d.in_mano_a
  const aperta = d.stato === 'proposta' && !mia
  const proposta = d.mossa === 'escalate' && !!(d.testo ?? '').trim()        // la sua proposta di risposta: la manda Dre, se vuole
  const scrive = m.scrive || proposta
  const inPartenza = d.stato === 'approvata' || d.stato === 'in_invio'
  useEffect(() => { setTesto(destinatari(d.testo).corpo); setModifico(false); setChiedoNo(false); setChiedoMia(false) }, [d.id, d.testo])

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
  const esito = (e: string) => {
    if (e === 'richiamare') { const t = new Date(); setRichiamo(`${t.getFullYear()}-${String(t.getMonth() + 1).padStart(2, '0')}-${String(t.getDate()).padStart(2, '0')}`); return Promise.resolve() }
    return fai(async () => { await segnaEsito(d.id, e); if (e === 'non_interessato') await nonInteressato(d.prospect_id) }, { stato: 'fatta', esito: e, esito_il: new Date().toISOString() }, e === 'non_interessato' ? 'Segnato: non lo contattiamo più. Lo ritrovi in Analytics, in basso.' : 'Segnato.')
  }
  const programma = (g: string) => fai(() => programmaChiamata({ id: d.id, chiamata_id: null, prospect_id: d.prospect_id, azienda: d.azienda, persona: d.persona, telefono: d.richiamo?.numero || d.telefono, richiamare_il: null, note: [], origine: 'clara' }, g).then(() => undefined),
    {}, `Richiami ${new Date(`${g}T12:00:00`).toLocaleDateString('it-IT', { weekday: 'short', day: 'numeric', month: 'short' })}: la trovi in Call.`).then(() => setRichiamo(null))
  const nonCosi = () => fai(() => giudica(d.id, false, motivo), { dre_giudizio: 'no' }, 'Segnato: Clara impara.')
  const prendo = (perche: string) => fai(() => prendiInMano(d.prospect_id, perche),
    { in_mano_a: 'Dre', in_mano_motivo: perche, in_mano_il: new Date().toISOString(), ...(d.stato === 'proposta' || d.stato === 'approvata' ? { stato: 'scartata' as const } : {}) },
    'È tua: Clara si ferma su questa relazione.')
  const ridai = () => fai(() => prendiInMano(d.prospect_id, '', true), { in_mano_a: null, in_mano_motivo: null, in_mano_il: null }, 'Torna a Clara: riparte dalla prossima risposta.')
  const consiglio = d.consiglio?.numero && !mia ? d.consiglio : null
  const [chiedoNumero, setChiedoNumero] = useState(false)
  const chiuso = (e: string) => fai(async () => { await segnaConsiglio(d, e); if (e === 'non_risposto') { try { await aggiungiNota(d.prospect_id, 'Chiamata di Dre: non ha risposto', 'gesto') } catch { /* niente */ } } },
    { consiglio: { ...(d.consiglio ?? {}), esito: e, esito_il: new Date().toISOString() } }, e === 'non_risposto' ? 'Segnato: Clara continua lei, dicendo che hai chiamato.' : 'Segnato.')
  // 5/11: «Non ha risposto» vuole il numero di Dre nelle regole: la prima volta si chiede qui
  const nonRisposto = () => void telefonoDre().then((t) => t ? chiuso('non_risposto') : setChiedoNumero(true)).catch((e) => mostra({ testo: e instanceof Error ? e.message : String(e) }))
  // 5/11 (Dre): sul consiglio gli stessi gesti di Call; al primo gesto la relazione passa in Call
  const ch = chiamataDaDecisione(d)
  const [richiamo2, setRichiamo2] = useState<string | null>(null)
  const inCall = (chiamata: NonNullable<Decisione['chiamata']>, detto: string) => { aggiorna({ ...d, chiamata }); mostra({ testo: detto }) }
  const riga = (x: Partial<NonNullable<Decisione['chiamata']>>): NonNullable<Decisione['chiamata']> => ({ id: x.id ?? d.chiamata?.id ?? '', chiamato_il: null, whatsapp_il: null, richiamare_il: null, esito: null, ...(d.chiamata ?? {}), ...x })
  const chiamo = () => void segnaChiamato(ch).then(({ id, chiamato_il }) => inCall(riga({ id, chiamato_il }), 'La trovi in Call: segna l’esito quando hai finito.')).catch((e) => mostra({ testo: e instanceof Error ? e.message : String(e) }))
  const whatsapp = () => void suWhatsapp(ch).then(({ id, whatsapp_il }) => inCall(riga({ id, whatsapp_il }), 'Su WhatsApp: è in mano a te, la trovi in Call.')).catch((e) => mostra({ testo: e instanceof Error ? e.message : String(e) }))
  const richiama = (g: string) => void programmaChiamata(ch, g).then((id) => { setRichiamo2(null); inCall(riga({ id, richiamare_il: g }), 'Programmata: la trovi in Call.') }).catch((e) => mostra({ testo: e instanceof Error ? e.message : String(e) }))
  const esitoConsiglio = (e: string) => fai(() => esitoChiamata(ch, e), { consiglio: { ...(d.consiglio ?? {}), esito: e, esito_il: new Date().toISOString() } }, 'Segnato.')

  return (
    <section className="rounded-2xl border border-bordo bg-white lg:sticky lg:top-6 lg:max-h-[calc(100dvh-3rem)] lg:overflow-y-auto">
      <header className="border-b border-bordo p-4 lg:p-5">
        <div className="mb-3 flex items-center justify-between">
          <button onClick={indietro} className="-ml-2 inline-flex min-h-10 items-center gap-1 rounded-full px-2 text-[14px] font-semibold text-navy lg:hidden"><Icona nome="indietro" className="h-4 w-4" /> Relazioni</button>
          <button onClick={vaiRelazione} className="ml-auto inline-flex min-h-9 items-center gap-1.5 rounded-full border border-ok-testo bg-ok-testo px-3.5 text-[13px] font-bold text-white hover:brightness-95"><Icona nome="lead" className="h-3.5 w-3.5" /> Profilo</button>
        </div>
        <div className="flex items-center gap-3">
          <span title={`Interesse e fit: ${interesse(d)} su 10`} className={`grid h-11 w-11 shrink-0 place-items-center rounded-xl text-[18px] font-extrabold ${interesse(d) >= 8 ? 'bg-ok-testo text-white' : interesse(d) >= 5 ? 'bg-navy/[0.1] text-navy' : 'bg-velo text-tenue'}`}>{interesse(d)}</span>
          <div className="min-w-0">
            <h2 className="truncate text-[18px] font-bold leading-tight text-inchiostro">{d.azienda || d.email}</h2>
            <p className="truncate text-[13px] text-tenue">{[d.persona, d.ruolo, d.citta, d.settore].filter(Boolean).join(', ')}</p>
          </div>
        </div>
        <div className="mt-3 flex flex-wrap gap-1.5">
          {mia ? <Pillola testo={`Me ne occupo io${d.in_mano_motivo ? `: ${d.in_mano_motivo}` : ''}`} tono="stop" piena /> : <Pillola testo={m.nome} tono={m.tono} piena={m.tono === 'ok'} />}
          {!aperta && !mia && <Pillola testo={s.testo} tono={s.tono} />}
          {d.analisi_mandata && <Pillola testo="Analisi mandata" tono="noi" />}
          {d.fase && !['risposto', 'in_follow_up'].includes(d.fase) && <Pillola testo={d.fase.replace(/_/g, ' ')} tono="neutro" />}
          {d.prossima_call && <Pillola testo={`Call ${quando(d.prossima_call)}`} tono="opp" icona="video" />}
        </div>
      </header>

      <div className="space-y-4 p-4 lg:p-5">
        {d.lead_testo && (
          <Blocco titolo={`Ha scritto ${quando(d.risposta_il)}`}>
            <blockquote className="whitespace-pre-wrap [overflow-wrap:anywhere] rounded-r-xl border-l-2 border-loro-segno bg-loro-fondo/60 px-3.5 py-3 text-[14px] leading-relaxed text-inchiostro">{d.lead_testo.trim().slice(0, 1200)}</blockquote>
          </Blocco>
        )}
        {consiglio && (
          <div className="grid gap-2 sm:grid-cols-3">
            <Tessera titolo="Sito">{d.sito ? <a href={/^https?:/.test(d.sito) ? d.sito : `https://${d.sito}`} target="_blank" rel="noreferrer" className="break-all font-bold text-navy underline-offset-2 hover:underline">{d.sito.replace(/^https?:\/\/(www\.)?/, '').replace(/\/$/, '')}</a> : <span className="text-tenue">non registrato</span>}</Tessera>
            <Tessera titolo="Analisi">{d.analisi_url ? <a href={d.analisi_url} target="_blank" rel="noreferrer" className="font-bold text-navy underline-offset-2 hover:underline">Apri il PDF</a> : <span className="text-tenue">{d.analisi_mandata ? 'mandata' : 'non pronta'}</span>}</Tessera>
            <Tessera titolo="Numero"><a href={`tel:${(telefonoDa(consiglio.numero) ?? consiglio.numero ?? '').replace(/[^\d+]/g, '')}`} onClick={chiamo} className="font-bold text-navy underline-offset-2 hover:underline">{telefonoDa(consiglio.numero) ?? consiglio.numero}</a></Tessera>
          </div>
        )}
        {consiglio && <NotaUnica testo={d.nota?.testo ?? ''} at={d.nota?.at} salva={async (t) => { const n = await scriviNota(ch, t); aggiorna({ ...d, nota: n.nota ?? null }) }} />}
        <Blocco titolo="Clara">
          <p className="text-[14px] leading-relaxed text-inchiostro">{d.perche}</p>
          {d.richiamo?.numero && <p className="mt-2 text-[14px]"><span className="text-tenue">Numero:</span> <a href={`tel:${(telefonoDa(d.richiamo.numero) ?? d.richiamo.numero).replace(/[^\d+]/g, '')}`} className="font-bold text-navy underline-offset-2 hover:underline">{telefonoDa(d.richiamo.numero) ?? d.richiamo.numero}</a>{d.richiamo.quando ? <span className="text-tenue">, {d.richiamo.quando}</span> : null}</p>}
          {!d.richiamo?.numero && d.telefono && d.mossa === 'callback' && <p className="mt-2 text-[14px]"><span className="text-tenue">Numero in scheda:</span> <a href={`tel:${d.telefono.replace(/\s/g, '')}`} className="font-bold text-navy underline-offset-2 hover:underline">{d.telefono}</a></p>}
          {consiglio && (
            <div className={`mt-2 rounded-xl border p-3 ${TONO.giallo.morbido}`}>
              <p className="text-[13px] font-bold">Ti consiglio di chiamare{consiglio.esito ? ` (${consiglio.esito === 'chiamato' ? 'chiamato' : 'non ora'})` : ''}</p>
              <p className="mt-0.5 text-[13.5px]">{consiglio.perche}</p>
              <div className="mt-2 flex flex-wrap items-center gap-2">
                <a href={`tel:${(telefonoDa(consiglio.numero) ?? consiglio.numero ?? '').replace(/[^\d+]/g, '')}`} onClick={consiglio.esito ? undefined : chiamo} className="inline-flex min-h-11 items-center gap-2 rounded-lg bg-ok-testo px-4 text-[15px] font-bold text-white hover:brightness-95"><Icona nome="telefono" className="h-4 w-4" /> {telefonoDa(consiglio.numero) ?? consiglio.numero}</a>
                {d.chiamata?.whatsapp_il && whatsappDa(consiglio.numero) && <a href={whatsappDa(consiglio.numero) ?? ''} target="_blank" rel="noreferrer" className="inline-flex min-h-11 items-center gap-2 rounded-lg border border-ok-testo px-4 text-[14px] font-bold text-ok-testo hover:bg-ok-fondo"><Icona nome="whatsapp" className="h-4 w-4" /> Apri la chat</a>}
                {d.chiamata && (d.chiamata.chiamato_il || d.chiamata.whatsapp_il || d.chiamata.richiamare_il) && !consiglio.esito && <button onClick={vaiCall} className="text-[13px] font-semibold text-navy hover:underline">È in Call</button>}
              </div>
              {!consiglio.esito && (richiamo2 !== null ? (
                <div className="mt-2 flex flex-wrap items-center gap-2 rounded-lg border border-bordo bg-fondo/60 p-2.5">
                  <span className="text-[13px] font-semibold">Richiamare il</span>
                  <input type="date" value={richiamo2} onChange={(e) => setRichiamo2(e.target.value)} className="min-h-10 rounded-lg border border-bordo bg-white px-2 text-[14px] outline-none focus:border-navy" />
                  <Bottone tipo="primo" onClick={() => richiama(richiamo2)} disabled={lavoro || !richiamo2}>Ok</Bottone>
                  <Bottone tipo="piatto" onClick={() => setRichiamo2(null)} disabled={lavoro}>Annulla</Bottone>
                </div>
              ) : chiedoNumero ? <div className="mt-2"><NumeroDre fatto={() => { setChiedoNumero(false); void chiuso('non_risposto') }} annulla={() => setChiedoNumero(false)} /></div> : (
                <div className="mt-2 grid grid-cols-2 gap-2 sm:grid-cols-[repeat(auto-fit,minmax(8.25rem,1fr))]">
                  <Bottone tipo="primo" onClick={() => void esitoConsiglio('fissata')} disabled={lavoro} className="px-2 text-[13px]">Call fissata</Bottone>
                  {d.chiamata?.whatsapp_il
                    ? <span className="inline-flex min-h-11 items-center justify-center gap-1.5 rounded-lg border border-ok-testo bg-ok-fondo px-2 text-[13px] font-bold text-ok-testo"><Icona nome="ok" className="h-3.5 w-3.5" /> Su WhatsApp</span>
                    : <Bottone onClick={whatsapp} disabled={lavoro} className="px-2 text-[13px]"><Icona nome="whatsapp" className="h-4 w-4" /> WhatsApp</Bottone>}
                  <Bottone onClick={() => void nonRisposto()} disabled={lavoro} className="px-2 text-[13px]">Non ha risposto</Bottone>
                  <Bottone onClick={() => { const t = new Date(); t.setDate(t.getDate() + 1); setRichiamo2(t.toISOString().slice(0, 10)) }} disabled={lavoro} className="px-2 text-[13px]">Richiamare</Bottone>
                  <Bottone onClick={() => void esitoConsiglio('non_interessato')} disabled={lavoro} className="px-2 text-[13px]">Non interessato</Bottone>
                </div>
              ))}
              {!consiglio.esito && <Bottone tipo="piatto" onClick={() => void chiuso('lascia_stare')} disabled={lavoro} className="mt-1 text-[13px]">Lascia stare: non lo chiamo</Bottone>}
            </div>
          )}
          {d.giudice?.pericoloso && <p className={`mt-2 rounded-lg border px-3 py-2 text-[13px] ${TONO.no.morbido}`}>Il revisore segnala: {d.giudice.errore_pericoloso}</p>}
          {d.errore && aperta && <p className={`mt-2 rounded-lg border px-3 py-2 text-[13px] ${TONO.attesa.morbido}`}>Non è partita: {d.errore}</p>}
          {d.errore && aperta && d.mossa === 'book_meeting' && /Invito fatto/.test(d.errore) && (
            <Bottone tipo="primo" onClick={() => void fai(() => invitoFatto(d.id), { stato: 'approvata', approvata_il: new Date().toISOString(), errore: null }, 'In partenza: la conferma parte entro pochi minuti.')} disabled={lavoro} className="mt-2">Invito fatto, manda la conferma</Bottone>
          )}
        </Blocco>

        {scrive && (
          <Blocco titolo={proposta ? 'La sua proposta di risposta' : aperta ? 'La mail che parte' : 'La mail'}>
            {(parti.a || parti.oggetto) && (
              <p className="mb-2 text-[12.5px] text-tenue">{parti.a && <>A <b className="text-inchiostro">{parti.a}</b>{parti.cc && <>, Cc <b className="text-inchiostro">{parti.cc}</b></>}</>}{parti.oggetto && <>, Oggetto: <b className="text-inchiostro">{parti.oggetto}</b></>}</p>
            )}
            {modifico && aperta ? (
              <textarea value={testo} onChange={(e) => setTesto(e.target.value)} rows={Math.min(18, Math.max(8, testo.split('\n').length + 2))}
                        className="w-full rounded-xl border border-navy bg-white p-3 text-[14px] leading-relaxed text-inchiostro outline-none" />
            ) : (
              <pre className="whitespace-pre-wrap [overflow-wrap:anywhere] rounded-xl bg-fondo/70 p-3.5 font-sans text-[14px] leading-relaxed text-inchiostro">{testo}</pre>
            )}
            {d.mossa === 'send_analysis' && <p className="mt-2 text-[12.5px] text-tenue">{d.analisi_pdf ? 'Allega il PDF dell’analisi' + (d.analisi_mandata ? '.' : ' e la presentazione.') : 'Il PDF non è ancora pronto: parte appena c’è.'}</p>}
            {d.mossa === 'book_meeting' && <p className="mt-2 text-[12.5px] text-tenue">Ricorda l’invito dal calendario: la mail dice che arriva.</p>}
          </Blocco>
        )}
      </div>

      <footer className="space-y-2 border-t border-bordo p-4 lg:p-5">
        {aperta && scrive && !chiedoNo && (
          <>
            <div className="grid grid-cols-2 gap-2">
              <Bottone tipo="primo" onClick={() => void invia()} disabled={lavoro || !testo.trim() || /\[[^\]]+\]/.test(testo)} className="col-span-2">
                <Icona nome="mail" className="h-4 w-4" /> {modifico ? 'Invia così' : proposta ? 'Manda la sua proposta' : m.bottone}
              </Bottone>
              {modifico
                ? <Bottone onClick={() => { void salvaTesto(d.id, testoIntero()); setModifico(false); aggiorna({ ...d, testo: testoIntero() }) }} disabled={lavoro}>Salva senza inviare</Bottone>
                : <Bottone onClick={() => setModifico(true)} disabled={lavoro}>Modifica</Bottone>}
              <Bottone onClick={() => setChiedoNo(true)} disabled={lavoro}>No</Bottone>
            </div>
            <p className="text-[12px] text-tenue">{proposta && /\[[^\]]+\]/.test(testo) ? 'Tra parentesi quadre c’è un fatto che sa solo tu: tocca Modifica e completalo, poi parte.' : 'Invia = parte entro 5 minuti dalla casella della campagna, nel thread. Se cambi il testo, Clara lo impara.'}</p>
          </>
        )}
        {aperta && d.mossa === 'callback' && !chiedoNo && (
          <>
            <p className="text-[12.5px] font-semibold text-tenue">Dopo la chiamata:</p>
            {richiamo !== null ? (
              <div className="flex flex-wrap items-center gap-2 rounded-lg border border-bordo bg-fondo/60 p-2.5">
                <span className="text-[13px] font-semibold">Richiamare il</span>
                <input type="date" value={richiamo} onChange={(e) => setRichiamo(e.target.value)} className="min-h-10 rounded-lg border border-bordo bg-white px-2 text-[14px] outline-none focus:border-navy" />
                <Bottone tipo="primo" onClick={() => void programma(richiamo)} disabled={lavoro || !richiamo}>Ok</Bottone>
                <Bottone tipo="piatto" onClick={() => setRichiamo(null)} disabled={lavoro}>Annulla</Bottone>
              </div>
            ) : (
              <div className="grid grid-cols-2 gap-2 sm:grid-cols-[repeat(auto-fit,minmax(8.25rem,1fr))]">
                {ESITI_CHIAMATA.map((e) => <Bottone key={e.esito} tipo={e.esito === 'fissata' ? 'primo' : 'secondo'} onClick={() => void esito(e.esito)} disabled={lavoro} className="px-2 text-[13px]">{e.nome}</Bottone>)}
              </div>
            )}
            <Bottone tipo="piatto" onClick={() => setChiedoNo(true)} disabled={lavoro} className="w-full">Non andava chiamato</Bottone>
          </>
        )}
        {aperta && d.mossa === 'escalate' && !chiedoNo && (
          <>
            <p className="text-[12.5px] font-semibold text-tenue">{proposta ? 'Oppure, se fai altro:' : 'Questa è tua. Quando hai fatto:'}</p>
            {richiamo !== null ? (
              <div className="flex flex-wrap items-center gap-2 rounded-lg border border-bordo bg-fondo/60 p-2.5">
                <span className="text-[13px] font-semibold">Me ne occupo il</span>
                <input type="date" value={richiamo} onChange={(e) => setRichiamo(e.target.value)} className="min-h-10 rounded-lg border border-bordo bg-white px-2 text-[14px] outline-none focus:border-navy" />
                <Bottone tipo="primo" onClick={() => void fai(() => rimanda(d.id, richiamo), { entro_il: richiamo }, 'Rimandata: la ritrovi in Coda, in Prossime.').then(() => setRichiamo(null))} disabled={lavoro || !richiamo}>Ok</Bottone>
                <Bottone tipo="piatto" onClick={() => setRichiamo(null)} disabled={lavoro}>Annulla</Bottone>
              </div>
            ) : (
              <div className="grid grid-cols-3 gap-2">
                {ESITI_TUA.map((e) => <Bottone key={e.esito} onClick={() => void esito(e.esito)} disabled={lavoro} className="px-2 text-[13px]">{e.nome}</Bottone>)}
                <Bottone onClick={() => { const t = new Date(); t.setDate(t.getDate() + 1); setRichiamo(t.toISOString().slice(0, 10)) }} disabled={lavoro} className="px-2 text-[13px]">Più avanti</Bottone>
              </div>
            )}
            <Bottone tipo="piatto" onClick={() => setChiedoNo(true)} disabled={lavoro} className="w-full">Poteva farlo Clara</Bottone>
          </>
        )}
        {aperta && (d.mossa === 'wait' || d.mossa === 'close') && !chiedoNo && d.dre_giudizio !== 'no' && (
          <Bottone tipo="piatto" onClick={() => setChiedoNo(true)} disabled={lavoro} className="w-full">Non sono d’accordo: dico a Clara cosa fare</Bottone>
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
        {mia ? (
          <div className="flex flex-wrap items-center justify-between gap-2 rounded-lg border border-bordo bg-fondo/60 px-3 py-2 text-[13px] text-inchiostro">
            <span>Questa relazione è tua{d.in_mano_il ? ` da ${quando(d.in_mano_il)}` : ''}: Clara non le scrive.</span>
            <Bottone tipo="piatto" onClick={() => void ridai()} disabled={lavoro} className="text-[13px]">Ridalla a Clara</Bottone>
          </div>
        ) : chiedoMia ? (
          <div className="space-y-2 rounded-xl border border-bordo bg-fondo/50 p-3">
            <p className="text-[13px] font-semibold text-inchiostro">Perché la prendi tu? Clara si ferma su questa relazione e lo legge.</p>
            <div className="flex flex-wrap gap-1.5">
              {MOTIVI_IN_MANO.map((x) => <Bottone key={x} onClick={() => void prendo(x)} disabled={lavoro} className="text-[13px]">{x}</Bottone>)}
            </div>
            <div className="flex gap-2">
              <input value={motivo} onChange={(e) => setMotivo(e.target.value)} placeholder="Oppure scrivilo tu" aria-label="Motivo"
                     onKeyDown={(e) => { if (e.key === 'Enter' && motivo.trim()) void prendo(motivo) }}
                     className="min-h-10 min-w-0 flex-1 rounded-xl border border-bordo bg-white px-3 text-[14px] outline-none focus:border-navy" />
              <Bottone tipo="primo" onClick={() => void prendo(motivo)} disabled={lavoro || !motivo.trim()}>Ok</Bottone>
              <Bottone tipo="piatto" onClick={() => setChiedoMia(false)} disabled={lavoro}>Annulla</Bottone>
            </div>
          </div>
        ) : (
          !chiedoNo && <Bottone tipo="piatto" onClick={() => setChiedoMia(true)} disabled={lavoro} className="w-full text-[13px]">Me ne occupo io: ferma Clara su questa relazione</Bottone>
        )}
      </footer>
    </section>
  )
}

function Tessera({ titolo, children }: { titolo: string; children: React.ReactNode }) {
  return (
    <div className="rounded-xl border border-bordo bg-fondo/50 px-3 py-2 text-[14px]">
      <p className="text-[11px] font-extrabold uppercase tracking-[.08em] text-tenue">{titolo}</p>
      <div className="mt-0.5 min-w-0 break-words">{children}</div>
    </div>
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
