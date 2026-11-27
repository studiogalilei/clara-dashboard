// IL LINKEDIN DESK (27/11/2026). Dre, mattina: «registrare un audio, mettere una foto e trasforma la roba in un post».
// Dre, mezzogiorno: «il default deve essere che ci sono i post automatici e un calendario... un post al giorno... al
// massimo posso cambiare l'ora... modificare il post e cambiare le immagini... clicco un bottone e schedulo un altro
// post: audio oppure scrivere, scattare la foto oppure caricarla. In easy, veloce, e basta».
// Quindi: il calendario dei prossimi giorni, un post per giorno; un tocco apre il post (testo, foto, ora); il «+»
// apre «Nuovo post». Scrive una routine di Claude Code sull'abbonamento di Dre: ci mette qualche minuto.
import { useCallback, useEffect, useLayoutEffect, useRef, useState } from 'react'
import { Bottone, Carico, Errore, Icona } from '../snella/pezzi'
import { useAvviso, useDati } from '../snella/uso'
import {
  cambiaFotoPost, cambiaOra, caricaFoto, leggiPost, leggiProfilo, nuovoPost, salvaProfilo, salvaTesto, scarta, urlFoto,
  useAscoltaPost, useDettatura, type Post, type Profilo,
} from './datiLinkedin'

const GIORNI = 14

function Microfono({ className = 'h-7 w-7' }: { className?: string }) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.9" strokeLinecap="round" strokeLinejoin="round" className={className} aria-hidden="true">
      <path d="M12 2a3 3 0 0 0-3 3v7a3 3 0 0 0 6 0V5a3 3 0 0 0-3-3zM19 10v2a7 7 0 0 1-14 0v-2M12 19v3" />
    </svg>
  )
}

function Camera({ className = 'h-6 w-6' }: { className?: string }) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.9" strokeLinecap="round" strokeLinejoin="round" className={className} aria-hidden="true">
      <path d="M23 19a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h4l2-3h6l2 3h4a2 2 0 0 1 2 2zM12 17a4 4 0 1 0 0-8 4 4 0 0 0 0 8z" />
    </svg>
  )
}

function Galleria({ className = 'h-6 w-6' }: { className?: string }) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.9" strokeLinecap="round" strokeLinejoin="round" className={className} aria-hidden="true">
      <path d="M5 3h14a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2zM8.5 10a1.5 1.5 0 1 0 0-3 1.5 1.5 0 0 0 0 3zM21 15l-5-5L5 21" />
    </svg>
  )
}

const chiaveGiorno = (d: Date) => `${d.getFullYear()}-${d.getMonth()}-${d.getDate()}`
const ora = (iso: string) => new Date(iso).toLocaleTimeString('it-IT', { hour: '2-digit', minute: '2-digit' })

function nomeGiorno(d: Date): string {
  const oggi = new Date(); oggi.setHours(0, 0, 0, 0)
  const diff = Math.round((d.getTime() - oggi.getTime()) / 86400000)
  if (diff === 0) return 'Oggi'
  if (diff === 1) return 'Domani'
  const s = d.toLocaleDateString('it-IT', { weekday: 'long', day: 'numeric', month: 'long' })
  return s.charAt(0).toUpperCase() + s.slice(1)
}

/** I due modi di mettere una foto: scattarla adesso o prenderla dalla galleria. */
function SceltaFoto({ scelta }: { scelta: (f: File) => void }) {
  const scatta = useRef<HTMLInputElement>(null)
  const prendi = useRef<HTMLInputElement>(null)
  const prendiFile = (e: React.ChangeEvent<HTMLInputElement>) => { const f = e.target.files?.[0]; if (f) scelta(f); e.target.value = '' }
  return (
    <div className="grid grid-cols-2 gap-2">
      <Bottone onClick={() => scatta.current?.click()} className="min-h-12"><Camera className="h-5 w-5" /> Scatta</Bottone>
      <Bottone onClick={() => prendi.current?.click()} className="min-h-12"><Galleria className="h-5 w-5" /> Galleria</Bottone>
      <input ref={scatta} type="file" accept="image/*" capture="environment" className="hidden" onChange={prendiFile} />
      <input ref={prendi} type="file" accept="image/*" className="hidden" onChange={prendiFile} />
    </div>
  )
}

function Anteprima({ file, togli }: { file: File; togli: () => void }) {
  const [u, setU] = useState<string | null>(null)
  useEffect(() => { const x = URL.createObjectURL(file); setU(x); return () => URL.revokeObjectURL(x) }, [file])
  if (!u) return null
  return (
    <div className="relative inline-block">
      <img src={u} alt="La foto del post" className="h-28 w-28 rounded-xl object-cover" />
      <button type="button" onClick={togli} aria-label="Togli la foto" className="absolute -right-2 -top-2 flex h-8 w-8 items-center justify-center rounded-full bg-inchiostro text-white">
        <Icona nome="chiudi" className="h-4 w-4" />
      </button>
    </div>
  )
}

/** «Nuovo post»: parli o scrivi, una foto se vuoi, e va nel primo giorno libero. */
function NuovoPost({ chiudi, fatto }: { chiudi: () => void; fatto: (uscita: string | null) => void }) {
  const [testo, setTesto] = useState('')
  const [foto, setFoto] = useState<File | null>(null)
  const [invio, setInvio] = useState(false)
  const [errore, setErrore] = useState<string | null>(null)
  const aggiungi = useCallback((t: string) => { if (t) setTesto((x) => (x ? `${x.trimEnd()} ${t}` : t)) }, [])
  const d = useDettatura(aggiungi)

  const manda = async () => {
    d.ferma(); setInvio(true); setErrore(null)
    try {
      const percorso = foto ? await caricaFoto(foto) : null
      fatto(await nuovoPost(testo, percorso))
    } catch (e) { setErrore(e instanceof Error ? e.message : 'Non sono riuscito a programmarlo.'); setInvio(false) }
  }

  return (
    <div role="dialog" aria-modal="true" aria-labelledby="nuovo" className="fixed inset-0 z-50 flex items-end justify-center bg-inchiostro/40 lg:items-center" onClick={chiudi}>
      <div className="max-h-[92dvh] w-full max-w-lg overflow-y-auto rounded-t-3xl bg-white p-5 pb-[calc(20px+env(safe-area-inset-bottom))] lg:rounded-3xl" onClick={(e) => e.stopPropagation()}>
        <div className="flex items-center justify-between">
          <h2 id="nuovo" className="text-[20px] font-extrabold text-inchiostro">Nuovo post</h2>
          <button type="button" onClick={chiudi} aria-label="Chiudi" className="flex h-11 w-11 items-center justify-center rounded-full hover:bg-velo"><Icona nome="chiudi" /></button>
        </div>

        <button type="button" onClick={d.ascolto ? d.ferma : d.parti} aria-pressed={d.ascolto}
                className={`mt-4 flex min-h-20 w-full items-center gap-4 rounded-2xl px-5 text-left text-white transition-colors ${d.ascolto ? 'bg-no-segno' : 'bg-blu-scuro hover:bg-navy'}`}>
          {d.ascolto ? <span className="h-6 w-6 shrink-0 animate-pulse rounded-md bg-white motion-reduce:animate-none" /> : <Microfono className="h-8 w-8 shrink-0" />}
          <span>
            <span className="block text-[18px] font-bold">{d.ascolto ? 'Ti ascolto' : 'Parla'}</span>
            <span className="block text-[14px] text-white/85">{d.ascolto ? 'Tocca quando hai finito.' : 'Racconta la cosa come la diresti a un amico.'}</span>
          </span>
        </button>
        {d.problema && <p className="mt-2 text-[14px] font-semibold text-no-testo">{d.problema}</p>}

        <label className="mt-3 block">
          <span className="sr-only">Oppure scrivi</span>
          <textarea value={testo + (d.provvisorio ? ` ${d.provvisorio}` : '')} onChange={(e) => setTesto(e.target.value)} readOnly={d.ascolto}
                    rows={4} placeholder="Oppure scrivi qui."
                    className="w-full resize-y rounded-xl border border-bordo px-3.5 py-3 text-[16px] leading-relaxed text-inchiostro placeholder:text-tenue focus:border-blu-scuro focus:outline-none" />
        </label>

        <div className="mt-3">{foto ? <Anteprima file={foto} togli={() => setFoto(null)} /> : <SceltaFoto scelta={setFoto} />}</div>

        {errore && <p role="alert" className="mt-3 text-[14px] font-semibold text-no-testo">{errore}</p>}
        <Bottone tipo="primo" onClick={() => void manda()} disabled={(!testo.trim() && !foto) || invio} className="mt-4 min-h-12 w-full text-[16px]">
          {invio ? 'Lo programmo…' : 'Programma'}
        </Bottone>
      </div>
    </div>
  )
}

function FotoPost({ percorso, className }: { percorso: string; className: string }) {
  const [url, setUrl] = useState<string | null>(null)
  useEffect(() => { let vivo = true; void urlFoto(percorso).then((u) => { if (vivo) setUrl(u) }); return () => { vivo = false } }, [percorso])
  return url ? <img src={url} alt="" className={className} /> : <span className={`${className} bg-velo`} />
}

/** Il post di un giorno, aperto: il testo si corregge e si salva da solo, la foto si cambia, l'ora si sposta. */
function PostAperto({ p, rifai, avvisa }: { p: Post; rifai: () => void; avvisa: (t: string) => void }) {
  const versioni = p.versioni ?? []
  const quale = p.scelta ?? 0
  const [testo, setTesto] = useState(p.testo ?? versioni[quale]?.testo ?? '')
  const [cambiaFoto, setCambiaFoto] = useState(false)
  const salva = useRef(0)
  const area = useRef<HTMLTextAreaElement>(null)
  useLayoutEffect(() => { const a = area.current; if (a) { a.style.height = 'auto'; a.style.height = `${a.scrollHeight + 4}px` } }, [testo])
  useEffect(() => { setTesto(p.testo ?? (p.versioni ?? [])[p.scelta ?? 0]?.testo ?? '') }, [p.testo, p.versioni, p.scelta])

  const cambia = (t: string) => {
    setTesto(t)
    window.clearTimeout(salva.current)
    salva.current = window.setTimeout(() => { void salvaTesto(p.id, quale, t) }, 800)
  }
  const altra = async () => {
    const n = (quale + 1) % versioni.length
    await salvaTesto(p.id, n, versioni[n].testo); rifai()
  }
  const nuovaOra = async (hhmm: string) => {
    if (!p.uscita_il || !/^\d\d:\d\d$/.test(hhmm) || hhmm === ora(p.uscita_il)) return
    const d = new Date(p.uscita_il); const [h, m] = hhmm.split(':').map(Number); d.setHours(h, m, 0, 0)
    try { await cambiaOra(p.id, d); avvisa(`Esce alle ${hhmm}.`); rifai() } catch (e) { avvisa(e instanceof Error ? e.message : 'Non ho cambiato l’ora.') }
  }
  const nuovaFoto = async (f: File | null) => {
    try { await cambiaFotoPost(p.id, f ? await caricaFoto(f) : null); setCambiaFoto(false); rifai() } catch (e) { avvisa(e instanceof Error ? e.message : 'Non ho cambiato la foto.') }
  }
  const caratteri = testo.length

  return (
    <div className="mt-3 border-t border-bordo pt-3">
      <label className="block">
        <span className="sr-only">Testo del post</span>
        <textarea ref={area} value={testo} onChange={(e) => cambia(e.target.value)} rows={4}
                  className="w-full resize-none overflow-hidden rounded-xl border border-bordo px-3 py-2.5 text-[16px] leading-relaxed text-inchiostro focus:border-blu-scuro focus:outline-none" />
      </label>
      <p className={`mt-1 text-[13px] font-semibold ${caratteri >= 900 && caratteri <= 1500 ? 'text-ok-testo' : 'text-attesa-testo'}`}>{caratteri} caratteri</p>

      <div className="mt-3">
        {p.foto && !cambiaFoto ? (
          <div className="flex flex-wrap items-center gap-3">
            <FotoPost percorso={p.foto} className="h-20 w-20 rounded-xl object-cover" />
            <Bottone onClick={() => setCambiaFoto(true)}>Cambia foto</Bottone>
            <Bottone tipo="piatto" onClick={() => void nuovaFoto(null)}>Togli</Bottone>
          </div>
        ) : <SceltaFoto scelta={(f) => void nuovaFoto(f)} />}
      </div>

      <div className="mt-3 flex flex-wrap items-center gap-2">
        {p.uscita_il && p.stato !== 'pubblicato' && (
          <label className="flex min-h-11 items-center gap-2 rounded-full border border-bordo px-4 text-[14px] font-semibold text-inchiostro">
            Esce alle
            <input type="time" defaultValue={ora(p.uscita_il)} onBlur={(e) => void nuovaOra(e.target.value)} className="bg-transparent text-[16px] font-bold focus:outline-none" />
          </label>
        )}
        {versioni.length > 1 && <Bottone onClick={() => void altra()}>Un’altra versione</Bottone>}
        <Bottone tipo="piatto" onClick={() => void scarta(p.id).then(() => { avvisa('Tolto dal calendario.'); rifai() })}>Togli il post</Bottone>
      </div>
    </div>
  )
}

function Giorno({ giorno, p, aperto, apri, rifai, avvisa }: {
  giorno: Date; p: Post | undefined; aperto: boolean; apri: () => void; rifai: () => void; avvisa: (t: string) => void
}) {
  const testo = p ? (p.testo ?? p.versioni?.[p.scelta ?? 0]?.testo ?? '') : ''
  const pronto = Boolean(p && (p.stato === 'programmato' || p.stato === 'bozza' || p.stato === 'pubblicato') && testo)
  return (
    <article className={`rounded-2xl border bg-white p-4 ${aperto ? 'border-blu-scuro' : 'border-bordo'}`}>
      <button type="button" onClick={pronto ? apri : undefined} disabled={!pronto} aria-expanded={pronto ? aperto : undefined}
              className="flex w-full items-start gap-3 text-left disabled:cursor-default">
        <div className="min-w-0 flex-1">
          <p className="flex flex-wrap items-center gap-x-2 text-[15px] font-bold text-inchiostro">
            {nomeGiorno(giorno)}
            {p?.uscita_il && <span className="font-semibold text-tenue">{p.stato === 'pubblicato' ? 'uscito alle' : 'alle'} {ora(p.uscita_il)}</span>}
            {p?.origine === 'mio' && <span className="rounded-full bg-noi-fondo px-2 py-0.5 text-[12px] font-semibold text-noi-testo">tuo</span>}
          </p>
          {!p ? <p className="mt-1 text-[15px] text-tenue">Lo preparo stanotte.</p>
            : p.stato === 'errore' ? <p className="mt-1 text-[15px] text-no-testo">{p.errore || 'Non sono riuscito a scriverlo.'}</p>
              : !pronto ? <p className="mt-1 flex items-center gap-2 text-[15px] text-tenue"><span className="h-2 w-2 animate-pulse rounded-full bg-blu-scuro motion-reduce:animate-none" /> Lo sto scrivendo</p>
                : !aperto && <p className="mt-1 line-clamp-3 whitespace-pre-line text-[15px] leading-relaxed text-inchiostro">{testo}</p>}
        </div>
        {p?.foto && !aperto && <FotoPost percorso={p.foto} className="h-16 w-16 shrink-0 rounded-xl object-cover" />}
      </button>
      {aperto && p && <PostAperto p={p} rifai={rifai} avvisa={avvisa} />}
    </article>
  )
}

const CAMPI_PROFILO: Array<{ k: keyof Profilo; nome: string; esempio: string }> = [
  { k: 'nome', nome: 'Nome', esempio: 'Nome e cognome' },
  { k: 'ruolo', nome: 'Cosa fai', esempio: 'Per esempio: sviluppatore a Studio Galilei, costruisco gestionali su misura' },
  { k: 'temi', nome: 'Di cosa vuoi parlare', esempio: 'Due o tre temi, per esempio: gestionali su misura, ordine nei processi, AI che serve davvero' },
]

/** Chi sei e di cosa parli: aperto la prima volta, poi una riga. */
function ProfiloCard() {
  const [p, setP] = useState<Profilo | null>(null)
  const [aperto, setAperto] = useState(false)
  const [salvo, setSalvo] = useState(false)
  useEffect(() => { void leggiProfilo().then((x) => { setP(x ?? { nome: '', ruolo: '', temi: '' }); if (!x?.nome) setAperto(true) }).catch(() => setP(null)) }, [])
  if (!p) return null
  if (!aperto) {
    return (
      <button type="button" onClick={() => setAperto(true)} className="mb-3 flex min-h-11 items-center gap-2 px-1 text-left text-[14px] text-tenue hover:text-inchiostro">
        <Icona nome="penna" className="h-4 w-4 shrink-0" /> {p.nome || 'Il tuo profilo'}. Modifica
      </button>
    )
  }
  const salva = async () => { setSalvo(true); try { await salvaProfilo(p); setAperto(false) } finally { setSalvo(false) } }
  return (
    <section aria-labelledby="profilo" className="mb-4 rounded-2xl border border-bordo bg-white p-4 lg:p-5">
      <h2 id="profilo" className="text-[17px] font-bold text-inchiostro">Il tuo profilo</h2>
      <div className="mt-3 space-y-3">
        {CAMPI_PROFILO.map((c) => (
          <label key={c.k} className="block">
            <span className="text-[14px] font-semibold text-inchiostro">{c.nome}</span>
            <textarea value={p[c.k]} rows={c.k === 'nome' ? 1 : 2} placeholder={c.esempio} onChange={(e) => setP({ ...p, [c.k]: e.target.value })}
                      className="mt-1 w-full resize-y rounded-xl border border-bordo px-3 py-2 text-[16px] text-inchiostro placeholder:text-tenue focus:border-blu-scuro focus:outline-none" />
          </label>
        ))}
      </div>
      <Bottone tipo="primo" onClick={() => void salva()} disabled={salvo || !p.nome.trim()} className="mt-3 w-full">Salva</Bottone>
    </section>
  )
}

export default function Linkedin() {
  const { dati, errore, caricando, rifai } = useDati(leggiPost)
  const ricarica = useCallback(() => { void rifai() }, [rifai])
  useAscoltaPost(ricarica)
  const { mostra, vista } = useAvviso()
  const avvisa = useCallback((testo: string) => mostra({ testo }), [mostra])
  const [nuovo, setNuovo] = useState(false)
  const [aperto, setAperto] = useState<string | null>(null)

  const perGiorno = new Map<string, Post>()
  for (const p of dati ?? []) if (p.uscita_il) perGiorno.set(chiaveGiorno(new Date(p.uscita_il)), p)
  const giorni = Array.from({ length: GIORNI }, (_, i) => { const d = new Date(); d.setHours(0, 0, 0, 0); d.setDate(d.getDate() + i); return d })

  return (
    <div className="mx-auto max-w-2xl pb-24">
      <h1 className="mb-2 text-[26px] font-extrabold text-inchiostro">LinkedIn</h1>
      <ProfiloCard />
      {errore ? <Errore testo={errore} riprova={ricarica} />
        : caricando && !dati ? <Carico righe={4} />
          : (
            <div className="space-y-2.5">
              {giorni.map((g) => {
                const p = perGiorno.get(chiaveGiorno(g))
                return <Giorno key={g.toISOString()} giorno={g} p={p} aperto={!!p && aperto === p.id}
                               apri={() => setAperto((x) => (x === p?.id ? null : p?.id ?? null))} rifai={ricarica} avvisa={avvisa} />
              })}
            </div>
          )}

      <button type="button" onClick={() => setNuovo(true)} aria-label="Nuovo post"
              className="fixed bottom-[calc(84px+env(safe-area-inset-bottom))] right-[max(1rem,env(safe-area-inset-right))] z-40 flex h-16 items-center gap-2 rounded-full bg-blu-scuro px-6 text-[16px] font-bold text-white shadow-lg hover:bg-navy lg:bottom-8 lg:right-8">
        <span aria-hidden="true" className="text-[26px] leading-none">+</span> Nuovo post
      </button>
      {nuovo && <NuovoPost chiudi={() => setNuovo(false)} fatto={(u) => {
        setNuovo(false)
        avvisa(u ? `Programmato: ${nomeGiorno(new Date(new Date(u).setHours(0, 0, 0, 0))).toLowerCase()} alle ${ora(u)}. Lo scrivo in qualche minuto.` : 'Programmato.')
        ricarica()
      }} />}
      {vista}
    </div>
  )
}
