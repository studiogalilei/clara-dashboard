// LE CALL (4/11 pomeriggio, Dre): in cima al Desk. Una lista sola di chiamate: quelle che porta Clara («Da
// chiamare», chi ha chiesto lui; «Ti consiglio di chiamare», dopo l'analisi), quelle che aggiunge Dre col «+»
// (azienda o numero: se e' in scheda si correla, se no si aggiunge lo stesso) e quelle che ha passato su WhatsApp
// (restano qui come contatti suoi). Per ognuna un giorno in cui richiamare, note veloci, l'esito a un tocco:
// Call fissata, WhatsApp, Richiamare, Non interessato. A destra le call in agenda. Niente che non serva a telefonare.
import { useEffect, useRef, useState } from 'react'
import { aggiungiChiamata, cerca, collegaCall, esitoChiamata, leggiCall, modificaNotaChiamata, notaChiamata, numeroChiamata, programmaChiamata, suWhatsapp, type Chiamata, type Trovato } from './dati'
import { agendaPulita, ordinaChiamate, telefonoDa, whatsappDa } from './regole'
import { Bottone, Carico, Errore, Icona, Pillola, Vuoto } from '../snella/pezzi'
import { useAvviso, useDati } from '../snella/uso'
import { giornoRoma, nomeGiorno, ora, quando } from '../snella/regole'
import type { Dove } from './Desk'
import { Note } from './Note'

const oggiIso = () => { const d = new Date(); return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}` }
const giornoBreve = (iso: string) => new Date(`${iso}T12:00:00`).toLocaleDateString('it-IT', { weekday: 'short', day: 'numeric', month: 'short' })
// 4/11 sera, Dre: «tra Call fissata e Richiamare metti WhatsApp: se clicco vuol dire che l'ho passato e ce l'ho su WhatsApp»
const ESITI: Array<{ esito: string; nome: string; tipo?: 'primo' }> = [
  { esito: 'fissata', nome: 'Call fissata', tipo: 'primo' }, { esito: 'whatsapp', nome: 'WhatsApp' }, { esito: 'richiamare', nome: 'Richiamare' }, { esito: 'non_interessato', nome: 'Non interessato' },
]

export default function Call({ vai, dove }: { vai: (d: Dove) => void; dove: Dove }) {
  const { dati, setDati, errore, caricando, rifai } = useDati(() => leggiCall())
  const { mostra, vista } = useAvviso()
  const [aggiungo, setAggiungo] = useState(false)
  if (caricando) return <Carico righe={3} etichetta="Carico le call" />
  if (errore && !dati) return <Errore testo={errore} riprova={() => void rifai()} />
  const c = dati ?? { prossime: [], richiami: [], consigli: [], mie: [] }
  const giorni = new Map<string, typeof c.prossime>()
  for (const p of agendaPulita(c.prossime)) { const g = giornoRoma(new Date(p.at)); giorni.set(g, [...(giorni.get(g) ?? []), p]) }
  // una lista sola (regole.ordinaChiamate): le programmate, i consigli di Clara, le altre
  const oggi = oggiIso()
  const tutte: Chiamata[] = ordinaChiamate([...(c.mie ?? []), ...c.richiami, ...(c.consigli ?? [])], oggi)
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
    return { ...prev, richiami: f(prev.richiami), mie: f(prev.mie), consigli: f(prev.consigli) }
  })

  return (
    <div className="space-y-4 lg:grid lg:grid-cols-2 lg:items-start lg:gap-4 lg:space-y-0">
      <div className="space-y-4">
        <section className="rounded-2xl border border-bordo bg-white">
          <header className="flex items-start justify-between gap-3 border-b border-bordo p-4 lg:p-5">
            <div>
              <h1 className="text-[22px] font-bold leading-tight text-inchiostro lg:text-[26px]">Da chiamare</h1>
              <p className="mt-1 text-[13.5px] text-tenue">Chi ha chiesto di sentirci, chi Clara ti consiglia di chiamare, le chiamate che aggiungi tu e chi hai su WhatsApp. Un giorno, una nota, l’esito.</p>
            </div>
            <Bottone tipo="primo" onClick={() => setAggiungo((v) => !v)} etichetta="Aggiungi una chiamata" className="shrink-0 px-3"><span className="text-[18px] leading-none">+</span><span className="hidden sm:inline"> Chiamata</span></Bottone>
          </header>
          {aggiungo && <Nuova chiudi={() => setAggiungo(false)} fatta={(ch) => { setDati((prev) => prev ? { ...prev, mie: [ch, ...(prev.mie ?? [])] } : prev); setAggiungo(false); mostra({ testo: 'Aggiunta alla lista.' }) }} mostra={mostra} />}
          {tutte.length === 0 ? <Vuoto>Nessuno da chiamare adesso. Col «+» ne aggiungi una.</Vuoto> : (
            <ul className="space-y-2.5 p-3 lg:p-4">
              {tutte.map((r) => <Scheda key={r.id} r={r} oggi={oggi} vai={vai} aggiorna={aggiorna} mostra={mostra} scelta={dove.id === r.id} />)}
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
                    <li key={i} className="flex flex-wrap items-center gap-3 rounded-xl border border-bordo px-3.5 py-2.5">
                      <span className="w-12 shrink-0 text-[15px] font-extrabold text-inchiostro">{ora(p.at)}</span>
                      <button onClick={() => p.prospect_id && vai({ voce: 'filo', id: p.prospect_id })} className="min-w-[9rem] flex-1 text-left" disabled={!p.prospect_id}>
                        <span className="block truncate text-[14.5px] font-bold text-inchiostro">{p.azienda || p.titolo}</span>
                        <span className="block truncate text-[12.5px] text-tenue">{[p.tipo, p.persona].filter(Boolean).join(', ')}</span>
                      </button>
                      {!p.prospect_id && p.id != null && <span className="basis-full sm:basis-auto"><Collega fatto={(pid, lead) => collegata(p.id as number, pid, lead)} /></span>}
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
                  {p.id != null && <Collega fatto={(pid, lead) => collegata(p.id as number, pid, lead)} />}
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
function Collega({ fatto }: { fatto: (prospectId: string | null, lead: boolean) => void }) {
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
        <Bottone tipo="piatto" onClick={() => { setAperto(false); fatto(null, false) }} className="text-[12.5px]">Non è un lead</Bottone>
        <Bottone tipo="piatto" onClick={() => setAperto(false)} className="text-[12.5px]">Annulla</Bottone>
      </div>
      {trovati.length > 0 && (
        <ul className="absolute left-0 right-0 z-10 mt-1 max-h-64 overflow-auto rounded-xl border border-bordo bg-white shadow-lg">
          {trovati.map((t) => (
            <li key={t.id}><button type="button" onClick={() => { setAperto(false); setQ(''); fatto(t.id, true) }} className="flex w-full min-h-11 items-center gap-2 px-3 text-left hover:bg-velo">
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

/** Una chiamata nella lista: numero, giorno, note, esito. Uguale per quelle di Clara, i suoi consigli e quelle di Dre.
 *  Con scelta=true (si arriva da Relazioni, #/d/call/<id>) e' evidenziata e la pagina ci scorre sopra. */
function Scheda({ r, oggi, vai, aggiorna, mostra, scelta }: { r: Chiamata; oggi: string; vai: (d: Dove) => void; aggiorna: (v: Chiamata, n: Chiamata | null) => void; mostra: (a: { testo: string }) => void; scelta?: boolean }) {
  const [nota, setNota] = useState('')
  const riga = useRef<HTMLLIElement>(null)
  useEffect(() => { if (scelta) riga.current?.scrollIntoView({ block: 'center', behavior: 'smooth' }) }, [scelta])
  const [programmo, setProgrammo] = useState(false)
  const [giorno, setGiorno] = useState(r.richiamare_il ?? oggi)
  const [lavoro, setLavoro] = useState(false)
  const tel = telefonoDa(r.telefono)
  const ritardo = !!r.richiamare_il && r.richiamare_il < oggi
  const fai = async (cosa: () => Promise<void>) => { setLavoro(true); try { await cosa() } catch (e) { mostra({ testo: e instanceof Error ? e.message : String(e) }) } finally { setLavoro(false) } }
  const programma = (g: string | null) => fai(async () => { const id = await programmaChiamata(r, g); aggiorna(r, { ...r, chiamata_id: id, richiamare_il: g }); setProgrammo(false); mostra({ testo: g ? `Programmata per ${giornoBreve(g)}.` : 'Programmazione tolta.' }) })
  const [numero, setNumero] = useState('')
  const [aggiungoNumero, setAggiungoNumero] = useState(false)
  // 4/11, Dre: «senza numero, buono, ma mi deve dare la possibilita' di aggiungerlo»
  const salvaNumero = (n: string) => fai(async () => { const id = await numeroChiamata(r, n); aggiorna(r, { ...r, chiamata_id: id, telefono: n.trim() }); setNumero(''); setAggiungoNumero(false); mostra({ testo: r.prospect_id ? 'Numero salvato, anche in scheda.' : 'Numero salvato.' }) })
  const annota = () => fai(async () => {
    if (!nota.trim()) return
    // una nota che e' solo un numero, su una chiamata senza numero, e' il numero
    const soloNumero = !tel && telefonoDa(nota) && nota.replace(/[\s+().-]/g, '').replace(/\d/g, '') === ''
    if (soloNumero) { const id = await numeroChiamata(r, nota); aggiorna(r, { ...r, chiamata_id: id, telefono: nota.trim() }); setNota(''); mostra({ testo: 'Preso come numero.' }); return }
    const { id, nota: n } = await notaChiamata(r, nota); aggiorna(r, { ...r, chiamata_id: id, note: [...(r.note ?? []), n] }); setNota(''); mostra({ testo: r.prospect_id ? 'Nota salvata, anche per Clara.' : 'Nota salvata.' })
  })
  const pid = r.prospect_id
  const wa = whatsappDa(tel)
  // «WhatsApp» (4/11 sera, Dre): un gesto, non un link. «L'ho passato e ce l'ho su WhatsApp»: la chiamata resta qui
  // come contatto suo, la relazione passa a lui (Clara si ferma), e sopra compare il bottone per aprire la chat.
  const whatsapp = () => fai(async () => {
    const { id, whatsapp_il } = await suWhatsapp(r)
    aggiorna(r, { ...r, chiamata_id: id, whatsapp_il, origine: 'dre' })
    mostra({ testo: pid ? 'Su WhatsApp: è in mano a te, Clara si ferma. Resta qui tra i tuoi contatti.' : 'Su WhatsApp: resta qui tra i tuoi contatti.' })
  })
  const esito = (e: string) => { if (e === 'richiamare') { setProgrammo(true); return } if (e === 'whatsapp') { if (!r.whatsapp_il) void whatsapp(); return } void fai(async () => { await esitoChiamata(r, e); aggiorna(r, null); mostra({ testo: 'Segnato.' }) }) }
  return (
    <li ref={riga} className={`space-y-2.5 rounded-xl border bg-white p-4 ${scelta ? 'border-navy ring-2 ring-navy/25' : ritardo ? 'border-giallo-bordo' : 'border-bordo'}`}>
      <div className="flex items-start justify-between gap-3">
        <button onClick={() => pid && vai({ voce: 'filo', id: pid })} disabled={!pid} className="block min-w-0 flex-1 text-left disabled:cursor-default">
          <span className="block truncate text-[15px] font-bold text-inchiostro">{r.azienda || r.persona || 'Senza nome'}</span>
          <span className="block text-[13px] text-tenue">{[r.persona, r.origine === 'clara' ? `ha scritto ${quando(r.risposta_il ?? '')}` : pid ? 'in scheda' : 'fuori scheda'].filter(Boolean).join(', ')}</span>
        </button>
        <div className="flex shrink-0 flex-col items-end gap-1">
          {r.whatsapp_il ? <Pillola testo="Su WhatsApp" tono="ok" piena /> : r.origine === 'consiglio' ? <Pillola testo="Ti consiglio di chiamare" tono="giallo" piena /> : r.origine === 'clara' ? <Pillola testo="Ha chiesto lui" tono="ok" piena /> : <Pillola testo="Tua" tono="neutro" />}
          {r.richiamare_il && <button onClick={() => setProgrammo(true)} className={`text-[12.5px] font-semibold ${ritardo ? 'text-giallo-testo' : 'text-tenue'} hover:underline`}>{ritardo ? 'Era per ' : ''}{giornoBreve(r.richiamare_il)}</button>}
        </div>
      </div>
      {r.quando && <p className="text-[13.5px] text-inchiostro"><span className="font-semibold">Quando:</span> {r.quando}</p>}
      {tel ? (
        <div className="flex flex-wrap items-center gap-2">
          <a href={`tel:${tel.replace(/[^\d+]/g, '')}`} className="inline-flex min-h-11 items-center gap-2 rounded-lg bg-ok-testo px-4 text-[15px] font-bold text-white">
            <Icona nome="telefono" className="h-4 w-4" /> {tel}
          </a>
          {r.whatsapp_il && wa && <a href={wa} target="_blank" rel="noreferrer" className="inline-flex min-h-11 items-center gap-2 rounded-lg border border-ok-testo px-4 text-[14px] font-bold text-ok-testo hover:bg-ok-fondo"><Icona nome="whatsapp" className="h-4 w-4" /> Apri la chat</a>}
        </div>
      ) : aggiungoNumero ? (
        <div className="flex gap-2">
          <input value={numero} onChange={(e) => setNumero(e.target.value)} type="tel" autoFocus placeholder="+39 …" aria-label="Numero di telefono"
                 onKeyDown={(e) => { if (e.key === 'Enter' && telefonoDa(numero)) void salvaNumero(numero) }}
                 className="min-h-10 min-w-0 flex-1 rounded-lg border border-bordo px-3 text-[14px] outline-none focus:border-navy" />
          <Bottone tipo="primo" onClick={() => void salvaNumero(numero)} disabled={lavoro || !telefonoDa(numero)} className="px-3">Salva</Bottone>
          <Bottone tipo="piatto" onClick={() => setAggiungoNumero(false)} disabled={lavoro}>Annulla</Bottone>
        </div>
      ) : (
        <div className="flex flex-wrap items-center gap-2">
          <Pillola testo="Senza numero" tono="attesa" />
          <button type="button" onClick={() => setAggiungoNumero(true)} className="inline-flex min-h-9 items-center rounded-lg border border-navy px-3 text-[12.5px] font-bold text-navy hover:bg-navy/[0.06]">Aggiungi il numero</button>
        </div>
      )}
      {r.perche && <p className="text-[13.5px] leading-relaxed text-inchiostro">{r.perche}</p>}
      {r.lead_testo && <blockquote className="rounded-r-xl border-l-2 border-loro-segno bg-loro-fondo/60 px-3 py-2 text-[13px] text-inchiostro">{r.lead_testo.replace(/\s+/g, ' ').slice(0, 240)}</blockquote>}
      <Note note={r.note ?? []} modifica={async (i, t) => { try { const note = await modificaNotaChiamata(r, i, t); aggiorna(r, { ...r, note }); mostra({ testo: 'Nota corretta.' }) } catch (e) { mostra({ testo: e instanceof Error ? e.message : String(e) }) } }} />
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
        <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
          {ESITI.map((e) => e.esito === 'whatsapp' && r.whatsapp_il
            ? <span key={e.esito} aria-label="Su WhatsApp" className="inline-flex min-h-11 items-center justify-center gap-1.5 rounded-lg border border-ok-testo bg-ok-fondo px-2 text-[13px] font-bold text-ok-testo"><Icona nome="ok" className="h-3.5 w-3.5" /> Su WhatsApp</span>
            : <Bottone key={e.esito} tipo={e.tipo ?? 'secondo'} onClick={() => esito(e.esito)} disabled={lavoro} className="px-2 text-[13px]">{e.esito === 'whatsapp' ? <><Icona nome="whatsapp" className="h-4 w-4" /> {e.nome}</> : e.nome}</Bottone>)}
        </div>
      )}
    </li>
  )
}
