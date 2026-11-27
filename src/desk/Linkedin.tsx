// IL LINKEDIN DESK (27/11/2026). Tre giri con Dre nello stesso giorno; questo e' il terzo:
// «un calendario tipo Google Calendar, da sinistra a destra: la data sopra, l'immagine, il testo leggermente visibile
// che si espande... ogni settimana prepara i post per tutta la settimana... sopra la foto profilo con il nome, la
// camera per caricare una foto e l'audio che si trascrive in live come su Claude o ChatGPT, poi Ottimizza e migliora
// lo storytelling, poi Schedule e scegli il giorno e l'ora. Easy».
// Sopra il compositore, sotto il calendario che scorre di lato. Un tocco su un giorno apre il post (testo, foto, ora).
import { useCallback, useEffect, useLayoutEffect, useRef, useState } from 'react'
import { Bottone, Errore, Icona } from '../ui/pezzi'
import { useAvviso, useDati } from '../ui/uso'
import {
  approva, cambiaFotoPost, cambiaOra, caricaFoto, collegaLinkedin, leggiCollegamento, leggiPost, leggiProfilo, leggiUno, nuovoPost, programma, salvaProfilo, salvaTesto,
  scarta, urlFoto, useAscoltaPost, useDettatura, type Post, type Profilo,
} from './datiLinkedin'

const GIORNI = 21

function Svg({ d, className = 'h-6 w-6' }: { d: string; className?: string }) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.9" strokeLinecap="round" strokeLinejoin="round" className={className} aria-hidden="true">
      <path d={d} />
    </svg>
  )
}
const MICROFONO = 'M12 2a3 3 0 0 0-3 3v7a3 3 0 0 0 6 0V5a3 3 0 0 0-3-3zM19 10v2a7 7 0 0 1-14 0v-2M12 19v3'
const CAMERA = 'M23 19a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h4l2-3h6l2 3h4a2 2 0 0 1 2 2zM12 17a4 4 0 1 0 0-8 4 4 0 0 0 0 8z'
const STELLINE = 'M12 3l1.9 4.6L18.5 9.5l-4.6 1.9L12 16l-1.9-4.6L5.5 9.5l4.6-1.9L12 3zM19 15l.9 2.1L22 18l-2.1.9L19 21l-.9-2.1L16 18l2.1-.9L19 15z'

const chiaveGiorno = (d: Date) => `${d.getFullYear()}-${d.getMonth()}-${d.getDate()}`
const ora = (iso: string) => new Date(iso).toLocaleTimeString('it-IT', { hour: '2-digit', minute: '2-digit' })
const dataInput = (d: Date) => `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
const iniziali = (n: string) => n.split(/\s+/).filter(Boolean).slice(0, 2).map((x) => x[0]?.toUpperCase()).join('') || 'Tu'

function Testata({ d }: { d: Date }) {
  const oggi = new Date(); oggi.setHours(0, 0, 0, 0)
  const diff = Math.round((d.getTime() - oggi.getTime()) / 86400000)
  const giorno = d.toLocaleDateString('it-IT', { weekday: 'short' }).replace('.', '')
  return (
    <span className="flex items-baseline gap-2">
      <span className={`font-titolo text-[30px] font-extrabold leading-none ${diff === 0 ? 'text-blu-scuro' : 'text-inchiostro'}`}>{d.getDate()}</span>
      <span className="text-[14px] font-semibold text-tenue">{diff === 0 ? 'oggi' : diff === 1 ? 'domani' : giorno}</span>
    </span>
  )
}

function FotoPost({ percorso, className }: { percorso: string; className: string }) {
  const [url, setUrl] = useState<string | null>(null)
  useEffect(() => { let vivo = true; void urlFoto(percorso).then((u) => { if (vivo) setUrl(u) }); return () => { vivo = false } }, [percorso])
  return url ? <img src={url} alt="" className={className} /> : <span className={`block ${className} bg-velo`} />
}

/** Il foglio che sale dal basso: per scegliere giorno e ora, o per aprire un post del calendario. */
function Foglio({ titolo, chiudi, children }: { titolo: string; chiudi: () => void; children: React.ReactNode }) {
  return (
    <div role="dialog" aria-modal="true" aria-label={titolo} className="fixed inset-0 z-50 flex items-end justify-center bg-inchiostro/40 lg:items-center" onClick={chiudi}>
      <div className="max-h-[92dvh] w-full max-w-lg overflow-y-auto rounded-t-3xl bg-white p-5 pb-[calc(20px+env(safe-area-inset-bottom))] lg:rounded-3xl" onClick={(e) => e.stopPropagation()}>
        <div className="mb-3 flex items-center justify-between">
          <h2 className="font-titolo text-[21px] font-extrabold text-navy">{titolo}</h2>
          <button type="button" onClick={chiudi} aria-label="Chiudi" className="flex h-11 w-11 items-center justify-center rounded-full hover:bg-velo"><Icona nome="chiudi" /></button>
        </div>
        {children}
      </div>
    </div>
  )
}

/** Scegli il giorno e l'ora: di base domani alle 8:30. */
function SceltaQuando({ ok, chiudi }: { ok: (d: Date) => Promise<void>; chiudi: () => void }) {
  const domani = new Date(); domani.setDate(domani.getDate() + 1)
  const [giorno, setGiorno] = useState(dataInput(domani))
  const [alle, setAlle] = useState('08:30')
  const [errore, setErrore] = useState<string | null>(null)
  const [invio, setInvio] = useState(false)
  const vai = async () => {
    const [h, m] = alle.split(':').map(Number); const [a, me, g] = giorno.split('-').map(Number)
    setInvio(true); setErrore(null)
    try { await ok(new Date(a, me - 1, g, h, m)) } catch (e) { setErrore(e instanceof Error ? e.message : 'Non sono riuscito a programmarlo.'); setInvio(false) }
  }
  return (
    <Foglio titolo="Quando esce" chiudi={chiudi}>
      <div className="grid grid-cols-2 gap-3">
        <label className="block"><span className="text-[14px] font-semibold text-inchiostro">Giorno</span>
          <input type="date" value={giorno} min={dataInput(new Date())} onChange={(e) => setGiorno(e.target.value)}
                 className="mt-1 min-h-12 w-full rounded-xl border border-bordo px-3 text-[16px] text-inchiostro focus:border-blu-scuro focus:outline-none" /></label>
        <label className="block"><span className="text-[14px] font-semibold text-inchiostro">Ora</span>
          <input type="time" value={alle} onChange={(e) => setAlle(e.target.value)}
                 className="mt-1 min-h-12 w-full rounded-xl border border-bordo px-3 text-[16px] text-inchiostro focus:border-blu-scuro focus:outline-none" /></label>
      </div>
      <p className="mt-2 text-[14px] text-tenue">I post automatici escono lunedì, mercoledì e venerdì. Negli altri giorni puoi mettere i tuoi; se scegli un giorno con un automatico, il tuo prende il suo posto.</p>
      {errore && <p role="alert" className="mt-2 text-[14px] font-semibold text-no-testo">{errore}</p>}
      <Bottone tipo="primo" onClick={() => void vai()} disabled={invio || !giorno || !alle} className="mt-4 min-h-12 w-full text-[16px]">{invio ? 'Lo programmo…' : 'Programma'}</Bottone>
    </Foglio>
  )
}

/** Il compositore: foto profilo e nome, il testo che si scrive parlando, la foto, Ottimizza, Programma. */
function Compositore({ profilo, apriProfilo, avvisa, rifai }: { profilo: Profilo | null; apriProfilo: () => void; avvisa: (t: string) => void; rifai: () => void }) {
  const [testo, setTesto] = useState('')
  const [foto, setFoto] = useState<File | null>(null)
  const [anteprima, setAnteprima] = useState<string | null>(null)
  const [bozza, setBozza] = useState<string | null>(null)       // il post nato da «Ottimizza»
  const [lavoro, setLavoro] = useState(false)
  const [quando, setQuando] = useState(false)
  const input = useRef<HTMLInputElement>(null)
  const area = useRef<HTMLTextAreaElement>(null)
  const aggiungi = useCallback((t: string) => { if (t) setTesto((x) => (x ? `${x.trimEnd()} ${t}` : t)) }, [])
  const d = useDettatura(aggiungi)
  const visto = testo + (d.provvisorio ? ` ${d.provvisorio}` : '')
  useLayoutEffect(() => { const a = area.current; if (a) { a.style.height = 'auto'; a.style.height = `${Math.max(a.scrollHeight + 2, 96)}px` } }, [visto])
  useEffect(() => { if (!foto) { setAnteprima(null); return } const u = URL.createObjectURL(foto); setAnteprima(u); return () => URL.revokeObjectURL(u) }, [foto])

  // la versione ottimizzata arriva dalla routine: si guarda la riga finche' e' pronta
  useEffect(() => {
    if (!bozza || !lavoro) return
    let vivo = true
    const guarda = async () => {
      const p = await leggiUno(bozza).catch(() => null)
      if (!vivo || !p) return
      if (p.stato === 'bozza' && p.versioni?.[0]?.testo) { setTesto(p.versioni[0].testo); setLavoro(false); avvisa(p.versioni[0].framework === 'Copy video' ? 'Ecco il copione del video. Puoi ancora cambiarlo.' : 'Ecco la versione migliorata. Puoi ancora cambiarla.') }
      if (p.stato === 'errore') { setLavoro(false); avvisa(p.errore || 'Non sono riuscito a migliorarlo.') }
    }
    void guarda()
    const t = window.setInterval(() => void guarda(), 8000)
    return () => { vivo = false; window.clearInterval(t) }
  }, [bozza, lavoro, avvisa])

  const [video, setVideo] = useState(false)
  const ottimizza = async (copione = false) => {
    d.ferma(); setLavoro(true); setVideo(copione)
    try {
      const percorso = foto ? await caricaFoto(foto) : null
      if (bozza) await scarta(bozza)
      setBozza(await nuovoPost(testo, percorso, true, copione))
    } catch (e) { setLavoro(false); avvisa(e instanceof Error ? e.message : 'Non sono riuscito a mandarlo.') }
  }

  const programmaQui = async (q: Date) => {
    let id = bozza
    if (id) await salvaTesto(id, 0, testo)
    else id = await nuovoPost(testo, foto ? await caricaFoto(foto) : null, false)
    await programma(id, q)
    setQuando(false); setTesto(''); setFoto(null); setBozza(null)
    avvisa(`Programmato per ${q.toLocaleDateString('it-IT', { weekday: 'long', day: 'numeric', month: 'long' })} alle ${q.toLocaleTimeString('it-IT', { hour: '2-digit', minute: '2-digit' })}.`)
    rifai()
  }

  const pieno = testo.trim().length > 0 || foto !== null
  return (
    <section aria-label="Nuovo post" className="rounded-2xl border border-bordo bg-white p-4 lg:p-5">
      <button type="button" onClick={apriProfilo} className="flex min-h-11 items-center gap-3 text-left">
        <span className="flex h-11 w-11 shrink-0 items-center justify-center rounded-full bg-navy text-[15px] font-bold text-white">{iniziali(profilo?.nome ?? '')}</span>
        <span className="font-titolo text-[17px] font-bold text-navy">{profilo?.nome || 'Il tuo nome'}</span>
      </button>

      <label className="mt-3 block">
        <span className="sr-only">Il post</span>
        <textarea ref={area} value={visto} onChange={(e) => setTesto(e.target.value)} readOnly={d.ascolto || lavoro}
                  placeholder="Di cosa vuoi parlare? Scrivi o tocca il microfono."
                  className="w-full resize-none overflow-hidden rounded-xl border border-transparent px-1 py-1 text-[17px] leading-relaxed text-inchiostro placeholder:text-tenue focus:outline-none" />
      </label>
      {anteprima && (
        <div className="relative mt-1 inline-block">
          <img src={anteprima} alt="La foto del post" className="h-24 w-24 rounded-xl object-cover" />
          <button type="button" onClick={() => setFoto(null)} aria-label="Togli la foto" className="absolute -right-2 -top-2 flex h-8 w-8 items-center justify-center rounded-full bg-inchiostro text-white"><Icona nome="chiudi" className="h-4 w-4" /></button>
        </div>
      )}
      {d.problema && <p className="mt-1 text-[14px] font-semibold text-no-testo">{d.problema}</p>}
      {lavoro && <p className="mt-1 flex items-center gap-2 text-[14px] font-semibold text-blu-scuro"><span className="h-2 w-2 animate-pulse rounded-full bg-blu-scuro motion-reduce:animate-none" /> {video ? 'Scrivo il copione del video' : 'Lo sto migliorando'}, ci vuole qualche minuto. Puoi chiudere l’app.</p>}

      <div className="mt-3 flex flex-wrap items-center gap-2 border-t border-bordo pt-3">
        <button type="button" onClick={() => input.current?.click()} aria-label="Aggiungi una foto" disabled={lavoro}
                className="flex h-12 w-12 items-center justify-center rounded-full text-inchiostro hover:bg-velo disabled:opacity-40"><Svg d={CAMERA} /></button>
        <input ref={input} type="file" accept="image/*" className="hidden" onChange={(e) => { setFoto(e.target.files?.[0] ?? null); e.target.value = '' }} />
        <button type="button" onClick={d.ascolto ? d.ferma : d.parti} aria-pressed={d.ascolto} aria-label={d.ascolto ? 'Ferma' : 'Parla'} disabled={lavoro}
                className={`flex h-12 w-12 items-center justify-center rounded-full disabled:opacity-40 ${d.ascolto ? 'bg-no-segno text-white' : 'text-inchiostro hover:bg-velo'}`}>
          {d.ascolto ? <span className="h-4 w-4 animate-pulse rounded-sm bg-white motion-reduce:animate-none" /> : <Svg d={MICROFONO} />}
        </button>
        <span className="flex-1" />
        {/* su telefono i tre bottoni vanno su una riga loro: in una sola non ci stanno */}
        <div className="flex w-full items-center justify-end gap-2 sm:w-auto">
          <Bottone tipo="piatto" className="whitespace-nowrap" onClick={() => void ottimizza(true)} disabled={!pieno || lavoro || d.ascolto}>Copy video</Bottone>
          <Bottone onClick={() => void ottimizza()} disabled={!pieno || lavoro || d.ascolto}><Svg d={STELLINE} className="h-4 w-4" /> Ottimizza</Bottone>
          <Bottone tipo="primo" onClick={() => setQuando(true)} disabled={!pieno || lavoro || d.ascolto}>Programma</Bottone>
        </div>
      </div>
      {quando && <SceltaQuando chiudi={() => setQuando(false)} ok={programmaQui} />}
    </section>
  )
}

/** Un post del calendario, aperto: testo che si salva da solo, foto, ora, togli. */
function PostAperto({ p, chiudi, rifai, avvisa }: { p: Post; chiudi: () => void; rifai: () => void; avvisa: (t: string) => void }) {
  const [testo, setTesto] = useState(p.testo ?? p.versioni?.[p.scelta ?? 0]?.testo ?? '')
  const salva = useRef(0)
  const area = useRef<HTMLTextAreaElement>(null)
  const input = useRef<HTMLInputElement>(null)
  useLayoutEffect(() => { const a = area.current; if (a) { a.style.height = 'auto'; a.style.height = `${a.scrollHeight + 4}px` } }, [testo])
  const cambia = (t: string) => { setTesto(t); window.clearTimeout(salva.current); salva.current = window.setTimeout(() => { void salvaTesto(p.id, p.scelta ?? 0, t) }, 800) }
  const nuovaOra = async (hhmm: string) => {
    if (!p.uscita_il || !/^\d\d:\d\d$/.test(hhmm) || hhmm === ora(p.uscita_il)) return
    const d = new Date(p.uscita_il); const [h, m] = hhmm.split(':').map(Number); d.setHours(h, m, 0, 0)
    try { await cambiaOra(p.id, d); avvisa(`Esce alle ${hhmm}.`); rifai() } catch (e) { avvisa(e instanceof Error ? e.message : 'Non ho cambiato l’ora.') }
  }
  const nuovaFoto = async (f: File | null) => {
    try { await cambiaFotoPost(p.id, f ? await caricaFoto(f) : null); rifai() } catch (e) { avvisa(e instanceof Error ? e.message : 'Non ho cambiato la foto.') }
  }
  const titolo = p.uscita_il ? new Date(p.uscita_il).toLocaleDateString('it-IT', { weekday: 'long', day: 'numeric', month: 'long' }) : 'Post'
  return (
    <Foglio titolo={titolo.charAt(0).toUpperCase() + titolo.slice(1)} chiudi={() => { window.clearTimeout(salva.current); void salvaTesto(p.id, p.scelta ?? 0, testo).then(rifai); chiudi() }}>
      {p.stato === 'bozza' && p.uscita_il && (
        <div className="mb-3 rounded-xl bg-attesa-fondo px-4 py-3 text-[14px] text-attesa-testo">
          <p className="font-semibold">Da rivedere: la storia l'ha scritta il sistema.</p>
          <p className="mt-1">Mettila con i tuoi dettagli veri. Esce solo quando tocchi «Approva».</p>
          <Bottone tipo="primo" className="mt-2" onClick={() => { window.clearTimeout(salva.current); void salvaTesto(p.id, p.scelta ?? 0, testo).then(() => approva(p.id)).then(() => { avvisa('Approvato: esce da solo all’ora del calendario.'); rifai(); chiudi() }).catch((e) => avvisa(e instanceof Error ? e.message : 'Non ho approvato.')) }}>Approva</Bottone>
        </div>
      )}
      {p.foto && <FotoPost percorso={p.foto} className="mb-3 max-h-64 w-full rounded-xl object-cover" />}
      <textarea ref={area} value={testo} onChange={(e) => cambia(e.target.value)} rows={4} aria-label="Testo del post"
                className="w-full resize-none overflow-hidden rounded-xl border border-bordo px-3 py-2.5 text-[16px] leading-relaxed text-inchiostro focus:border-blu-scuro focus:outline-none" />
      <div className="mt-3 flex flex-wrap items-center gap-2">
        {p.uscita_il && p.stato !== 'pubblicato' && (
          <label className="flex min-h-11 items-center gap-2 rounded-full border border-bordo px-4 text-[14px] font-semibold text-inchiostro">
            Esce alle <input type="time" defaultValue={ora(p.uscita_il)} onBlur={(e) => void nuovaOra(e.target.value)} className="bg-transparent text-[16px] font-bold focus:outline-none" />
          </label>
        )}
        <Bottone onClick={() => input.current?.click()}><Svg d={CAMERA} className="h-4 w-4" /> {p.foto ? 'Cambia foto' : 'Aggiungi foto'}</Bottone>
        {p.foto && <Bottone tipo="piatto" onClick={() => void nuovaFoto(null)}>Togli foto</Bottone>}
        <input ref={input} type="file" accept="image/*" className="hidden" onChange={(e) => { const f = e.target.files?.[0]; if (f) void nuovaFoto(f); e.target.value = '' }} />
      </div>
      <button type="button" onClick={() => void scarta(p.id).then(() => { avvisa('Tolto dal calendario.'); rifai(); chiudi() })}
              className="mt-3 min-h-11 px-1 text-[14px] font-semibold text-no-testo">Togli il post</button>
    </Foglio>
  )
}

/** Un giorno del calendario: la data sopra, l'immagine, il testo che si intravede. */
function Giorno({ giorno, p, apri }: { giorno: Date; p: Post | undefined; apri: (p: Post) => void }) {
  const testo = p ? (p.testo ?? p.versioni?.[p.scelta ?? 0]?.testo ?? '') : ''
  const pronto = Boolean(p && testo && p.stato !== 'errore' && p.stato !== 'da_scrivere' && p.stato !== 'in_scrittura')
  return (
    <li className="w-[78vw] max-w-[300px] shrink-0 snap-start">
      <div className="mb-2 flex items-baseline justify-between px-1">
        <Testata d={giorno} />
        {p?.uscita_il && <span className="text-[14px] font-semibold text-tenue">{p.stato === 'pubblicato' ? 'uscito ' : ''}{ora(p.uscita_il)}</span>}
      </div>
      <button type="button" onClick={() => p && pronto && apri(p)} disabled={!pronto}
              className="flex h-[420px] w-full flex-col overflow-hidden rounded-2xl border border-bordo bg-white text-left disabled:cursor-default">
        {!p ? <span className="m-auto px-6 text-center text-[15px] text-tenue">Giorno libero. Se vuoi, programma qui un tuo post.</span>
          : p.stato === 'errore' ? <span className="m-auto px-6 text-center text-[15px] text-no-testo">{p.errore || 'Non sono riuscito a scriverlo.'}</span>
            : !pronto ? <span className="m-auto flex items-center gap-2 text-[15px] text-tenue"><span className="h-2 w-2 animate-pulse rounded-full bg-blu-scuro motion-reduce:animate-none" /> Lo sto scrivendo</span>
              : (
                <>
                  {p.foto && <FotoPost percorso={p.foto} className="h-40 w-full shrink-0 object-cover" />}
                  <span className={`block flex-1 overflow-hidden whitespace-pre-line px-4 pt-3 text-[15px] font-normal leading-relaxed text-inchiostro/90 ${p.foto ? 'line-clamp-[9]' : 'line-clamp-[15]'}`}>{testo}</span>
                  <span className="flex items-center justify-between px-4 py-3 text-[14px] font-semibold text-blu-scuro">
                    Leggi e modifica
                    {p.stato === 'bozza' ? <span className="rounded-full bg-attesa-fondo px-2 py-0.5 text-[12px] text-attesa-testo">da rivedere</span>
                      : p.origine === 'mio' && <span className="rounded-full bg-noi-fondo px-2 py-0.5 text-[12px] text-noi-testo">tuo</span>}
                  </span>
                </>
              )}
      </button>
    </li>
  )
}

const CAMPI_PROFILO: Array<{ k: keyof Profilo; nome: string; esempio: string }> = [
  { k: 'nome', nome: 'Nome', esempio: 'Nome e cognome' },
  { k: 'ruolo', nome: 'Cosa fai', esempio: 'Per esempio: sviluppatore a Studio Galilei, costruisco gestionali su misura' },
  { k: 'temi', nome: 'Di cosa vuoi parlare', esempio: 'Due o tre temi, per esempio: gestionali su misura, ordine nei processi, AI che serve davvero' },
]

function ProfiloFoglio({ p, chiudi, salvato }: { p: Profilo; chiudi: () => void; salvato: (p: Profilo) => void }) {
  const [x, setX] = useState(p)
  const [salvo, setSalvo] = useState(false)
  const salva = async () => { setSalvo(true); try { await salvaProfilo(x); salvato(x) } finally { setSalvo(false) } }
  return (
    <Foglio titolo="Il tuo profilo" chiudi={chiudi}>
      <div className="space-y-3">
        {CAMPI_PROFILO.map((c) => (
          <label key={c.k} className="block">
            <span className="text-[14px] font-semibold text-inchiostro">{c.nome}</span>
            <textarea value={x[c.k]} rows={c.k === 'nome' ? 1 : 2} placeholder={c.esempio} onChange={(e) => setX({ ...x, [c.k]: e.target.value })}
                      className="mt-1 w-full resize-y rounded-xl border border-bordo px-3 py-2 text-[16px] text-inchiostro placeholder:text-tenue focus:border-blu-scuro focus:outline-none" />
          </label>
        ))}
      </div>
      <Bottone tipo="primo" onClick={() => void salva()} disabled={salvo || !x.nome.trim()} className="mt-4 min-h-12 w-full">Salva</Bottone>
    </Foglio>
  )
}

// Il collegamento a LinkedIn: senza, i post programmati restano nel calendario e non escono da soli
function Collegamento({ avvisa }: { avvisa: (t: string) => void }) {
  const [c, setC] = useState<{ nome: string | null; scade_il: string } | null | undefined>(undefined)
  const [vado, setVado] = useState(false)
  useEffect(() => {
    void leggiCollegamento().then(setC).catch(() => setC(null))
    const esito = /linkedin=([a-z]+)/.exec(window.location.hash)?.[1]
    if (esito) {
      avvisa(esito === 'collegato' ? 'LinkedIn collegato: i post programmati usciranno da soli.' : esito === 'annullato' ? 'Collegamento annullato.' : 'Il collegamento non è riuscito: riprova.')
      window.history.replaceState(null, '', window.location.pathname + window.location.search + '#/d/post')
    }
  }, [avvisa])
  if (c === undefined) return null
  const scade = c ? new Date(c.scade_il) : null
  const presto = scade ? scade.getTime() - Date.now() < 7 * 86400000 : false
  const vai = async () => { setVado(true); try { await collegaLinkedin() } catch (e) { avvisa(e instanceof Error ? e.message : 'Non riesco ad aprire LinkedIn.'); setVado(false) } }
  if (c && !presto) return <p className="mt-3 text-center text-[13px] text-tenue">LinkedIn collegato: i post programmati escono da soli, fino al {scade!.toLocaleDateString('it-IT', { day: 'numeric', month: 'long' })}.</p>
  return (
    <div className="mt-3 flex items-center justify-between gap-3 rounded-2xl border border-bordo bg-white px-4 py-3">
      <p className="text-[14px] text-inchiostro">{c ? 'Il collegamento a LinkedIn scade tra pochi giorni.' : 'Collega LinkedIn e i post programmati usciranno da soli.'}</p>
      <Bottone tipo="primo" onClick={() => void vai()} disabled={vado}>{c ? 'Ricollega' : 'Collega LinkedIn'}</Bottone>
    </div>
  )
}

export default function Linkedin() {
  const { dati, errore, rifai } = useDati(leggiPost)
  const ricarica = useCallback(() => { void rifai() }, [rifai])
  useAscoltaPost(ricarica)
  const { mostra, vista } = useAvviso()
  const avvisa = useCallback((testo: string) => mostra({ testo }), [mostra])
  const [aperto, setAperto] = useState<Post | null>(null)
  const [profilo, setProfilo] = useState<Profilo | null>(null)
  const [modProfilo, setModProfilo] = useState(false)
  useEffect(() => { void leggiProfilo().then((x) => { setProfilo(x); if (!x?.nome) setModProfilo(true) }).catch(() => undefined) }, [])

  const perGiorno = new Map<string, Post>()
  for (const p of dati ?? []) if (p.uscita_il) perGiorno.set(chiaveGiorno(new Date(p.uscita_il)), p)
  const giorni = Array.from({ length: GIORNI }, (_, i) => { const d = new Date(); d.setHours(0, 0, 0, 0); d.setDate(d.getDate() + i); return d })

  return (
    <div className="mx-auto max-w-5xl pb-10">
      <div className="mx-auto max-w-2xl">
        <Compositore profilo={profilo} apriProfilo={() => setModProfilo(true)} avvisa={avvisa} rifai={ricarica} />
        <Collegamento avvisa={avvisa} />
      </div>
      <h2 className="mb-3 mt-8 font-titolo text-[22px] font-extrabold text-navy">Calendario</h2>
      {errore ? <Errore testo={errore} riprova={ricarica} /> : (
        <ul aria-label="I prossimi giorni" className="-mx-[max(0.875rem,env(safe-area-inset-left))] flex snap-x snap-mandatory gap-3 overflow-x-auto scroll-px-[max(0.875rem,env(safe-area-inset-left))] px-[max(0.875rem,env(safe-area-inset-left))] pb-3 lg:mx-0 lg:scroll-px-0 lg:px-0">
          {giorni.map((g) => <Giorno key={g.toISOString()} giorno={g} p={perGiorno.get(chiaveGiorno(g))} apri={setAperto} />)}
        </ul>
      )}
      {aperto && <PostAperto key={aperto.id} p={aperto} chiudi={() => setAperto(null)} rifai={ricarica} avvisa={avvisa} />}
      {modProfilo && <ProfiloFoglio p={profilo ?? { nome: '', ruolo: '', temi: '' }} chiudi={() => setModProfilo(false)} salvato={(x) => { setProfilo(x); setModProfilo(false) }} />}
      {vista}
    </div>
  )
}
