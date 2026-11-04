// LE CALL (4/11 pomeriggio, Dre): in cima al Desk. Le chiamate da fare, quelle che porta Clara («Da chiamare», chi
// ha chiesto lui) e quelle che aggiunge Dre col «+» (azienda o numero: se e' in scheda si correla, se no si aggiunge
// lo stesso); per ognuna un giorno in cui richiamare, note veloci, l'esito a un tocco. Sotto, «Ti consiglio di
// chiamare» e le call in agenda. Niente che non serva a telefonare.
import { useEffect, useState } from 'react'
import { aggiungiChiamata, aggiungiNota, cerca, collegaCall, esitoChiamata, leggiCall, notaChiamata, prendiInMano, programmaChiamata, segnaConsiglio, type Call as DatiCall, type Chiamata, type Consiglio, type Trovato } from './dati'

type Consigliato = NonNullable<DatiCall['consigli']>[number]
import { MOTIVO_WHATSAPP, NOTA_WHATSAPP, agendaPulita, telefonoDa, whatsappDa } from './regole'
import { Bottone, Carico, Errore, Icona, Pillola, Vuoto } from '../snella/pezzi'
import { useAvviso, useDati } from '../snella/uso'
import { giornoRoma, nomeGiorno, ora, quando } from '../snella/regole'
import { TONO } from '../snella/toni'
import type { Dove } from './Desk'
import { Note } from './Note'

const oggiIso = () => { const d = new Date(); return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}` }
const giornoBreve = (iso: string) => new Date(`${iso}T12:00:00`).toLocaleDateString('it-IT', { weekday: 'short', day: 'numeric', month: 'short' })
const ESITI: Array<{ esito: string; nome: string; tipo?: 'primo' }> = [
  { esito: 'fissata', nome: 'Call fissata', tipo: 'primo' }, { esito: 'richiamare', nome: 'Richiamare' }, { esito: 'non_interessato', nome: 'Non interessato' },
]

export default function Call({ vai }: { vai: (d: Dove) => void }) {
  const { dati, setDati, errore, caricando, rifai } = useDati(() => leggiCall())
  const { mostra, vista } = useAvviso()
  const [aggiungo, setAggiungo] = useState(false)
  if (caricando) return <Carico righe={3} etichetta="Carico le call" />
  if (errore && !dati) return <Errore testo={errore} riprova={() => void rifai()} />
  const c = dati ?? { prossime: [], richiami: [], consigli: [], mie: [] }
  const giorni = new Map<string, typeof c.prossime>()
  for (const p of agendaPulita(c.prossime)) { const g = giornoRoma(new Date(p.at)); giorni.set(g, [...(giorni.get(g) ?? []), p]) }
  // una lista sola: prima le programmate per oggi o in ritardo, poi le programmate dopo, poi le senza data (le piu' fresche prima)
  const oggi = oggiIso()
  const tutte: Chiamata[] = [...(c.mie ?? []), ...c.richiami].sort((a, b) => {
    const ka = a.richiamare_il ? (a.richiamare_il <= oggi ? `0${a.richiamare_il}` : `1${a.richiamare_il}`) : '2'
    const kb = b.richiamare_il ? (b.richiamare_il <= oggi ? `0${b.richiamare_il}` : `1${b.richiamare_il}`) : '2'
    return ka.localeCompare(kb) || (b.risposta_il ?? b.creato_il ?? '').localeCompare(a.risposta_il ?? a.creato_il ?? '')
  })
  // 4/11, Dre: le telefonate pianificate stanno anche in agenda, per giorno, piu' piccole; «Oggi» con lo sfondo diverso
  const telefonate = new Map<string, Chiamata[]>()
  for (const t of tutte) if (t.richiamare_il) { const g = t.richiamare_il < oggi ? oggi : t.richiamare_il; telefonate.set(g, [...(telefonate.get(g) ?? []), t]) }
  const giorniTutti = [...new Set([...giorni.keys(), ...telefonate.keys()])].sort()
  // 4/11, Dre: «se non riesce a collegare o non e' sicura, me lo dica e glielo collego io»: gli eventi senza azienda
  const sconosciuti = agendaPulita(c.prossime.filter((p) => !p.prospect_id && (p.tipo === 'altro' || !p.tipo)).map((p) => ({ ...p, tipo: 'da_collegare' })))
  const collegata = (id: number, prospectId: string | null, lead: boolean) => void (async () => {
    try { await collegaCall(id, prospectId, lead); mostra({ testo: lead ? 'Collegata: Clara la vede nella relazione.' : 'Segnata come interna.' }); await rifai() }
    catch (e) { mostra({ testo: e instanceof Error ? e.message : String(e) }) }
  })()
  const aggiorna = (vecchia: Chiamata, nuova: Chiamata | null) => setDati((prev) => {
    if (!prev) return prev
    const f = (xs: Chiamata[] = []) => xs.flatMap((x) => x.id === vecchia.id ? (nuova ? [nuova] : []) : [x])
    return { ...prev, richiami: f(prev.richiami), mie: f(prev.mie) }
  })

  return (
    <div className="space-y-4 lg:grid lg:grid-cols-2 lg:items-start lg:gap-4 lg:space-y-0">
      <div className="space-y-4">
        <section className="rounded-2xl border border-bordo bg-white">
          <header className="flex items-start justify-between gap-3 border-b border-bordo p-4 lg:p-5">
            <div>
              <h1 className="text-[22px] font-bold leading-tight text-inchiostro lg:text-[26px]">Da chiamare</h1>
              <p className="mt-1 text-[13.5px] text-tenue">Chi ha chiesto di sentirci e le chiamate che aggiungi tu. Un giorno, una nota, l’esito.</p>
            </div>
            <Bottone tipo="primo" onClick={() => setAggiungo((v) => !v)} etichetta="Aggiungi una chiamata" className="shrink-0 px-3"><span className="text-[18px] leading-none">+</span><span className="hidden sm:inline"> Chiamata</span></Bottone>
          </header>
          {aggiungo && <Nuova chiudi={() => setAggiungo(false)} fatta={(ch) => { setDati((prev) => prev ? { ...prev, mie: [ch, ...(prev.mie ?? [])] } : prev); setAggiungo(false); mostra({ testo: 'Aggiunta alla lista.' }) }} mostra={mostra} />}
          {tutte.length === 0 ? <Vuoto>Nessuno da chiamare adesso. Col «+» ne aggiungi una.</Vuoto> : (
            <ul className="space-y-2.5 p-3 lg:p-4">
              {tutte.map((r) => <Scheda key={r.id} r={r} oggi={oggi} vai={vai} aggiorna={aggiorna} mostra={mostra} />)}
            </ul>
          )}
        </section>

        <section className="rounded-2xl border border-bordo bg-white">
          <header className="border-b border-bordo p-4 lg:p-5">
            <h2 className="text-[18px] font-bold leading-tight text-inchiostro">Ti consiglio di chiamare</h2>
            <p className="mt-1 text-[13.5px] text-tenue">Clara manda avanti il lavoro; qui ha trovato un numero e pensa che una tua telefonata farebbe bene.</p>
          </header>
          {(c.consigli ?? []).length === 0 ? <Vuoto>Nessun consiglio adesso.</Vuoto> : (
            <ul className="space-y-2.5 p-3 lg:p-4">
              {(c.consigli ?? []).map((r) => <Consigliata key={r.id} r={r} vai={vai} mostra={mostra} togli={() => setDati((prev) => prev ? { ...prev, consigli: (prev.consigli ?? []).filter((x) => x.id !== r.id) } : prev)} />)}
            </ul>
          )}
        </section>
      </div>

      <section className="rounded-2xl border border-bordo bg-white">
        <header className="border-b border-bordo p-4 lg:p-5">
          <h2 className="text-[22px] font-bold leading-tight text-inchiostro lg:text-[26px]">Le call in agenda</h2>
          <p className="mt-1 text-[13.5px] text-tenue">Le prossime due settimane, dal tuo calendario.</p>
        </header>
        {giorniTutti.length === 0 ? <Vuoto>Niente in agenda nei prossimi 14 giorni.</Vuoto> : (
          <div className="divide-y divide-velo">
            {giorniTutti.map((g) => { const call = giorni.get(g) ?? []; const tel = telefonate.get(g) ?? []; return (
              <div key={g} className={`p-4 ${g === oggi ? 'bg-navy/[0.045]' : ''}`}>
                <h3 className={`mb-2 text-[12px] font-extrabold uppercase tracking-[.08em] ${g === oggi ? 'text-navy' : 'text-tenue'}`}>{nomeGiorno(g)}{g === oggi && (call.length + tel.length) ? <span className="ml-2 font-semibold normal-case tracking-normal text-tenue">{call.length ? `${call.length} call` : ''}{call.length && tel.length ? ', ' : ''}{tel.length ? `${tel.length} da chiamare` : ''}</span> : null}</h3>
                <ul className="space-y-2">
                  {call.map((p, i) => (
                    <li key={i} className="flex items-center gap-3 rounded-xl border border-bordo px-3.5 py-2.5">
                      <span className="w-12 shrink-0 text-[15px] font-extrabold text-inchiostro">{ora(p.at)}</span>
                      <button onClick={() => p.prospect_id && vai({ voce: 'filo', id: p.prospect_id })} className="min-w-0 flex-1 text-left" disabled={!p.prospect_id}>
                        <span className="block truncate text-[14.5px] font-bold text-inchiostro">{p.azienda || p.titolo}</span>
                        <span className="block truncate text-[12.5px] text-tenue">{[p.tipo, p.persona].filter(Boolean).join(', ')}</span>
                      </button>
                      {!p.prospect_id && p.id != null && <Collega evento={p.id} fatto={(pid, lead) => collegata(p.id as number, pid, lead)} />}
                      {p.link && <a href={p.link} target="_blank" rel="noreferrer" className="grid h-10 w-10 shrink-0 place-items-center rounded-lg border border-bordo text-navy hover:border-navy" aria-label="Apri la call"><Icona nome="video" className="h-4 w-4" /></a>}
                    </li>
                  ))}
                  {tel.map((t) => {
                    const n = telefonoDa(t.telefono)
                    return (
                      <li key={`tel-${t.id}`} className="flex items-center gap-3 rounded-lg border border-dashed border-bordo bg-white/70 px-3 py-1.5">
                        <span className="grid h-7 w-7 shrink-0 place-items-center rounded-md bg-ok-testo/10 text-ok-testo"><Icona nome="telefono" className="h-3.5 w-3.5" /></span>
                        <span className="min-w-0 flex-1 truncate text-[13px]"><b className="text-inchiostro">{t.azienda || t.persona}</b>{t.persona && t.azienda ? <span className="text-tenue">, {t.persona}</span> : null}{t.richiamare_il && t.richiamare_il < oggi ? <span className="text-giallo-testo"> (era per {giornoBreve(t.richiamare_il)})</span> : null}</span>
                        {n ? <a href={`tel:${n.replace(/[^\d+]/g, '')}`} className="shrink-0 text-[13px] font-bold text-ok-testo hover:underline">{n}</a> : <span className="shrink-0 text-[12px] text-tenue">senza numero</span>}
                      </li>
                    )
                  })}
                </ul>
              </div>
            ) })}
          </div>
        )}
        {sconosciuti.length > 0 && (
          <div className="border-t border-bordo p-4 lg:p-5">
            <h3 className="mb-1 text-[12px] font-extrabold uppercase tracking-[.08em] text-giallo-testo">Non so di chi sono</h3>
            <p className="mb-2 text-[13px] text-tenue">Eventi del tuo calendario senza un'azienda riconosciuta. Se è un lead, collegalo: Clara lo vede nella relazione e sa quando fare il follow-up.</p>
            <ul className="space-y-2">
              {sconosciuti.map((p) => (
                <li key={p.id ?? p.at} className="flex flex-wrap items-center gap-3 rounded-xl border border-dashed border-bordo px-3.5 py-2.5">
                  <span className="shrink-0 text-[13px] font-bold text-inchiostro">{nomeGiorno(giornoRoma(new Date(p.at)))} {ora(p.at)}</span>
                  <span className="min-w-0 flex-1 truncate text-[14px] text-inchiostro">{p.titolo}</span>
                  {p.id != null && <Collega evento={p.id} fatto={(pid, lead) => collegata(p.id as number, pid, lead)} />}
                </li>
              ))}
            </ul>
          </div>
        )}
      </section>
      {vista}
    </div>
  )
}

/** «Collega all'azienda» (4/11): una call del calendario senza azienda si cerca e si collega con un tocco; o si dice che non e' un lead. */
function Collega({ evento, fatto }: { evento: number; fatto: (prospectId: string | null, lead: boolean) => void }) {
  const [aperto, setAperto] = useState(false)
  const [q, setQ] = useState('')
  const [trovati, setTrovati] = useState<Trovato[]>([])
  useEffect(() => {
    const t = q.trim()
    if (!aperto || t.length < 2) { setTrovati([]); return }
    let vivo = true
    const h = setTimeout(() => { cerca(t).then((r) => { if (vivo) setTrovati(r.slice(0, 6)) }).catch(() => { if (vivo) setTrovati([]) }) }, 300)
    return () => { vivo = false; clearTimeout(h) }
  }, [q, aperto])
  if (!aperto) return <button type="button" onClick={() => setAperto(true)} className="inline-flex min-h-9 shrink-0 items-center rounded-lg border border-navy px-3 text-[12.5px] font-bold text-navy hover:bg-navy/[0.06]">Collega all'azienda</button>
  return (
    <div className="relative w-full basis-full">
      <div className="flex gap-2">
        <input value={q} onChange={(e) => setQ(e.target.value)} autoFocus placeholder="Azienda, persona o email" aria-label="Cerca l'azienda"
               className="min-h-10 min-w-0 flex-1 rounded-lg border border-bordo px-3 text-[14px] outline-none focus:border-navy" />
        <Bottone tipo="piatto" onClick={() => fatto(null, false)} className="text-[12.5px]">Non è un lead</Bottone>
        <Bottone tipo="piatto" onClick={() => setAperto(false)} className="text-[12.5px]">Annulla</Bottone>
      </div>
      {trovati.length > 0 && (
        <ul className="absolute left-0 right-0 z-10 mt-1 max-h-64 overflow-auto rounded-xl border border-bordo bg-white shadow-lg">
          {trovati.map((t) => (
            <li key={t.id}><button type="button" onClick={() => fatto(t.id, true)} className="flex w-full min-h-11 items-center gap-2 px-3 text-left hover:bg-velo">
              <span className="truncate text-[14px] font-semibold text-inchiostro">{t.azienda || t.email}</span>
              <span className="truncate text-[12.5px] text-tenue">{[t.persona, t.citta].filter(Boolean).join(', ')}</span>
            </button></li>
          ))}
        </ul>
      )}
    </div>
  )
}

/** Il «+»: azienda o numero; se e' in scheda si sceglie e si correla, se no si aggiunge lo stesso. */
function Nuova({ chiudi, fatta, mostra }: { chiudi: () => void; fatta: (c: Chiamata) => void; mostra: (a: { testo: string }) => void }) {
  const [q, setQ] = useState('')
  const [trovati, setTrovati] = useState<Trovato[]>([])
  const [scelto, setScelto] = useState<Trovato | null>(null)
  const [numero, setNumero] = useState('')
  const [persona, setPersona] = useState('')
  const [giorno, setGiorno] = useState(oggiIso())
  const [nota, setNota] = useState('')
  const [lavoro, setLavoro] = useState(false)
  useEffect(() => {
    const t = q.trim()
    if (scelto || t.length < 2) { setTrovati([]); return }
    let vivo = true
    const h = setTimeout(() => { cerca(t).then((r) => { if (vivo) setTrovati(r.slice(0, 6)) }).catch(() => { if (vivo) setTrovati([]) }) }, 300)
    return () => { vivo = false; clearTimeout(h) }
  }, [q, scelto])
  const scegli = (t: Trovato) => { setScelto(t); setQ(t.azienda || t.email); if (t.telefono && !numero) setNumero(t.telefono); if (t.persona && !persona) setPersona(t.persona); setTrovati([]) }
  const salva = async () => {
    const azienda = (scelto?.azienda || q).trim()
    if (!azienda) return
    setLavoro(true)
    try {
      const ch = await aggiungiChiamata({ prospect_id: scelto?.id ?? null, azienda, persona, numero, richiamare_il: giorno || null, nota })
      fatta(ch)
    } catch (e) { mostra({ testo: e instanceof Error ? e.message : String(e) }) } finally { setLavoro(false) }
  }
  const numeroPulito = telefonoDa(numero)
  return (
    <div className="space-y-3 border-b border-bordo bg-fondo/50 p-4 lg:p-5">
      <div className="relative">
        <label className="block text-[12px] font-bold uppercase tracking-[.06em] text-tenue">Azienda o numero</label>
        <input value={q} onChange={(e) => { setQ(e.target.value); setScelto(null) }} autoFocus placeholder="Scrivi il nome, o un numero" aria-label="Azienda o numero"
               className="mt-1 min-h-11 w-full rounded-xl border border-bordo bg-white px-3 text-[15px] text-inchiostro outline-none focus:border-navy" />
        {scelto && <p className="mt-1 flex items-center gap-1.5 text-[12.5px] text-ok-testo"><Icona nome="ok" className="h-3.5 w-3.5" /> In scheda: {[scelto.persona, scelto.citta, scelto.fase?.replace(/_/g, ' ')].filter(Boolean).join(', ') || 'lead del sistema'}. Clara ci mette quello che sa.</p>}
        {trovati.length > 0 && (
          <ul className="absolute z-10 mt-1 w-full overflow-hidden rounded-xl border border-bordo bg-white shadow-lg">
            {trovati.map((t) => (
              <li key={t.id}><button onClick={() => scegli(t)} className="flex w-full items-center justify-between gap-3 px-3.5 py-2.5 text-left hover:bg-fondo">
                <span className="min-w-0"><span className="block truncate text-[14px] font-bold text-inchiostro">{t.azienda || t.email}</span><span className="block truncate text-[12px] text-tenue">{[t.persona, t.citta].filter(Boolean).join(', ')}</span></span>
                <span className="shrink-0 text-[12.5px] font-semibold text-tenue">{t.telefono ? telefonoDa(t.telefono) ?? t.telefono : 'senza numero'}</span>
              </button></li>
            ))}
          </ul>
        )}
        {!scelto && q.trim().length >= 2 && trovati.length === 0 && <p className="mt-1 text-[12.5px] text-tenue">Non è in scheda: la aggiungo lo stesso.</p>}
      </div>
      <div className="grid gap-3 sm:grid-cols-3">
        <label className="block"><span className="block text-[12px] font-bold uppercase tracking-[.06em] text-tenue">Numero</span>
          <input value={numero} onChange={(e) => setNumero(e.target.value)} inputMode="tel" placeholder="Se ce l’hai" className="mt-1 min-h-11 w-full rounded-xl border border-bordo bg-white px-3 text-[15px] outline-none focus:border-navy" /></label>
        <label className="block"><span className="block text-[12px] font-bold uppercase tracking-[.06em] text-tenue">Persona</span>
          <input value={persona} onChange={(e) => setPersona(e.target.value)} placeholder="Con chi parli" className="mt-1 min-h-11 w-full rounded-xl border border-bordo bg-white px-3 text-[15px] outline-none focus:border-navy" /></label>
        <label className="block"><span className="block text-[12px] font-bold uppercase tracking-[.06em] text-tenue">Quando</span>
          <input type="date" value={giorno} min={oggiIso()} onChange={(e) => setGiorno(e.target.value)} className="mt-1 min-h-11 w-full rounded-xl border border-bordo bg-white px-3 text-[15px] outline-none focus:border-navy" /></label>
      </div>
      <input value={nota} onChange={(e) => setNota(e.target.value)} placeholder="Una nota (di cosa parlare, chi te l’ha passata)" aria-label="Nota" className="min-h-11 w-full rounded-xl border border-bordo bg-white px-3 text-[14px] outline-none focus:border-navy" />
      <div className="flex flex-wrap gap-2">
        <Bottone tipo="primo" onClick={() => void salva()} disabled={lavoro || !(scelto?.azienda || q.trim())}>Aggiungi{numeroPulito ? ` (${numeroPulito})` : ''}</Bottone>
        <Bottone tipo="piatto" onClick={chiudi} disabled={lavoro}>Annulla</Bottone>
      </div>
    </div>
  )
}

/** Una chiamata nella lista: numero, giorno, note, esito. Uguale per quelle di Clara e quelle di Dre. */
function Scheda({ r, oggi, vai, aggiorna, mostra }: { r: Chiamata; oggi: string; vai: (d: Dove) => void; aggiorna: (v: Chiamata, n: Chiamata | null) => void; mostra: (a: { testo: string }) => void }) {
  const [nota, setNota] = useState('')
  const [programmo, setProgrammo] = useState(false)
  const [giorno, setGiorno] = useState(r.richiamare_il ?? oggi)
  const [lavoro, setLavoro] = useState(false)
  const tel = telefonoDa(r.telefono)
  const ritardo = !!r.richiamare_il && r.richiamare_il < oggi
  const fai = async (cosa: () => Promise<void>) => { setLavoro(true); try { await cosa() } catch (e) { mostra({ testo: e instanceof Error ? e.message : String(e) }) } finally { setLavoro(false) } }
  const programma = (g: string | null) => fai(async () => { const id = await programmaChiamata(r, g); aggiorna(r, { ...r, chiamata_id: id, richiamare_il: g }); setProgrammo(false); mostra({ testo: g ? `Programmata per ${giornoBreve(g)}.` : 'Programmazione tolta.' }) })
  const annota = () => fai(async () => { if (!nota.trim()) return; const { id, nota: n } = await notaChiamata(r, nota); aggiorna(r, { ...r, chiamata_id: id, note: [...(r.note ?? []), n] }); setNota(''); mostra({ testo: r.prospect_id ? 'Nota salvata, anche per Clara.' : 'Nota salvata.' }) })
  const esito = (e: string) => { if (e === 'richiamare') { setProgrammo(true); return } void fai(async () => { await esitoChiamata(r, e); aggiorna(r, null); mostra({ testo: 'Segnato.' }) }) }
  const pid = r.prospect_id
  const wa = whatsappDa(tel)
  // WhatsApp (4/11): apre la chat e, insieme, la nota e il lead in mano a Dre: Clara si ferma, niente consigli ne' solleciti
  const whatsapp = () => {
    if (wa) window.open(wa, '_blank', 'noopener')
    void fai(async () => {
      const { id, nota: n } = await notaChiamata(r, NOTA_WHATSAPP)
      if (pid) await prendiInMano(pid, MOTIVO_WHATSAPP)
      aggiorna(r, { ...r, chiamata_id: id, note: [...(r.note ?? []), n] })
      mostra({ testo: pid ? 'Segnato: è in mano a te, Clara si ferma.' : 'Segnato.' })
    })
  }
  return (
    <li className={`space-y-2.5 rounded-xl border bg-white p-4 ${ritardo ? 'border-giallo-bordo' : 'border-bordo'}`}>
      <div className="flex items-start justify-between gap-3">
        <button onClick={() => pid && vai({ voce: 'filo', id: pid })} disabled={!pid} className="block min-w-0 flex-1 text-left disabled:cursor-default">
          <span className="block truncate text-[15px] font-bold text-inchiostro">{r.azienda || r.persona || 'Senza nome'}</span>
          <span className="block text-[13px] text-tenue">{[r.persona, r.origine === 'clara' ? `ha scritto ${quando(r.risposta_il ?? '')}` : pid ? 'in scheda' : 'fuori scheda'].filter(Boolean).join(', ')}</span>
        </button>
        <div className="flex shrink-0 flex-col items-end gap-1">
          {r.origine === 'clara' ? <Pillola testo="Ha chiesto lui" tono="ok" piena /> : <Pillola testo="Tua" tono="neutro" />}
          {r.richiamare_il && <button onClick={() => setProgrammo(true)} className={`text-[12.5px] font-semibold ${ritardo ? 'text-giallo-testo' : 'text-tenue'} hover:underline`}>{ritardo ? 'Era per ' : ''}{giornoBreve(r.richiamare_il)}</button>}
        </div>
      </div>
      {r.quando && <p className="text-[13.5px] text-inchiostro"><span className="font-semibold">Quando:</span> {r.quando}</p>}
      {tel ? (
        <div className="flex flex-wrap items-center gap-2">
          <a href={`tel:${tel.replace(/[^\d+]/g, '')}`} className="inline-flex min-h-11 items-center gap-2 rounded-lg bg-ok-testo px-4 text-[15px] font-bold text-white">
            <Icona nome="telefono" className="h-4 w-4" /> {tel}
          </a>
          {wa && <button type="button" onClick={whatsapp} disabled={lavoro} className="inline-flex min-h-11 items-center gap-2 rounded-lg border border-ok-testo px-4 text-[14px] font-bold text-ok-testo hover:bg-ok-fondo"><Icona nome="whatsapp" className="h-4 w-4" /> WhatsApp</button>}
        </div>
      ) : <Pillola testo="Senza numero" tono="attesa" />}
      {r.perche && <p className="text-[13.5px] leading-relaxed text-inchiostro">{r.perche}</p>}
      {r.lead_testo && <blockquote className="rounded-r-xl border-l-2 border-loro-segno bg-loro-fondo/60 px-3 py-2 text-[13px] text-inchiostro">{r.lead_testo.replace(/\s+/g, ' ').slice(0, 240)}</blockquote>}
      <Note note={r.note ?? []} />
      <div className="flex gap-2">
        <input value={nota} onChange={(e) => setNota(e.target.value)} placeholder="Nota veloce" aria-label="Nota veloce" onKeyDown={(e) => { if (e.key === 'Enter') void annota() }}
               className="min-h-10 min-w-0 flex-1 rounded-lg border border-bordo px-3 text-[14px] outline-none focus:border-navy" />
        <Bottone onClick={() => void annota()} disabled={lavoro || !nota.trim()} className="px-3">Salva</Bottone>
      </div>
      {programmo ? (
        <div className="flex flex-wrap items-center gap-2 rounded-lg border border-bordo bg-fondo/60 p-2.5">
          <span className="text-[13px] font-semibold">Richiamare il</span>
          <input type="date" value={giorno} min={oggi} onChange={(e) => setGiorno(e.target.value)} className="min-h-10 rounded-lg border border-bordo bg-white px-2 text-[14px] outline-none focus:border-navy" />
          <Bottone tipo="primo" onClick={() => void programma(giorno)} disabled={lavoro || !giorno}>Ok</Bottone>
          {r.richiamare_il && <Bottone tipo="piatto" onClick={() => void programma(null)} disabled={lavoro}>Togli</Bottone>}
          <Bottone tipo="piatto" onClick={() => setProgrammo(false)} disabled={lavoro}>Annulla</Bottone>
        </div>
      ) : (
        <div className="grid grid-cols-3 gap-2">
          {ESITI.map((e) => <Bottone key={e.esito} tipo={e.tipo ?? 'secondo'} onClick={() => esito(e.esito)} disabled={lavoro} className="px-2 text-[13px]">{e.nome}</Bottone>)}
        </div>
      )}
    </li>
  )
}

function Consigliata({ r, vai, mostra, togli }: { r: Consigliato; vai: (d: Dove) => void; mostra: (a: { testo: string }) => void; togli: () => void }) {
  const [lavoro, setLavoro] = useState(false)
  const tel = telefonoDa(r.telefono)
  const fatto = async (e: string) => {
    setLavoro(true)
    try { await segnaConsiglio({ id: r.id, consiglio: r.consiglio as Consiglio | null }, e); togli(); mostra({ testo: 'Segnato.' }) } catch (err) { mostra({ testo: err instanceof Error ? err.message : String(err) }) } finally { setLavoro(false) }
  }
  return (
    <li className={`space-y-2 rounded-xl border p-4 ${TONO.giallo.morbido}`}>
      <button onClick={() => vai({ voce: 'filo', id: r.prospect_id })} className="block w-full min-w-0 text-left">
        <span className="block truncate text-[15px] font-bold">{r.azienda}</span>
        <span className="block text-[13px] opacity-80">{[r.persona, quando(r.risposta_il)].filter(Boolean).join(', ')}</span>
      </button>
      {r.perche && <p className="text-[13.5px] leading-relaxed">{r.perche}</p>}
      <div className="flex flex-wrap items-center gap-2">
        {tel && <a href={`tel:${tel.replace(/[^\d+]/g, '')}`} className="inline-flex min-h-10 items-center gap-2 rounded-lg bg-ok-testo px-4 text-[14px] font-bold text-white"><Icona nome="telefono" className="h-4 w-4" /> {tel}</a>}
        {whatsappDa(tel) && <button type="button" disabled={lavoro} className="inline-flex min-h-10 items-center gap-2 rounded-lg border border-ok-testo px-3 text-[13px] font-bold text-ok-testo hover:bg-ok-fondo"
          onClick={() => { window.open(whatsappDa(tel) ?? '', '_blank', 'noopener'); void (async () => { setLavoro(true); try { await aggiungiNota(r.prospect_id, NOTA_WHATSAPP); await prendiInMano(r.prospect_id, MOTIVO_WHATSAPP); await segnaConsiglio(r, 'whatsapp'); togli(); mostra({ testo: 'Segnato: è in mano a te, Clara si ferma.' }) } catch (e) { mostra({ testo: e instanceof Error ? e.message : String(e) }) } finally { setLavoro(false) } })() }}>
          <Icona nome="whatsapp" className="h-4 w-4" /> WhatsApp</button>}
        <Bottone onClick={() => void fatto('chiamato')} disabled={lavoro} className="text-[13px]">Chiamato</Bottone>
        <Bottone tipo="piatto" onClick={() => void fatto('lascia_stare')} disabled={lavoro} className="text-[13px]">Lascia stare</Bottone>
      </div>
    </li>
  )
}

