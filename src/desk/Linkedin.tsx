// IL LINKEDIN DESK (27/11/2026). Dre: «registrare un audio, mettere una foto e trasforma la roba in un post,
// lo chiamiamo LinkedIn Desk... clean e comodo». Sopra si crea (parli, o scrivi, e una foto), sotto i post: due
// versioni con due framework diversi, si sceglie, si tocca il testo, si chiede «più corto» o «più ironico».
// Scrive una routine di Claude Code sull'abbonamento di Dre (niente API a consumo): ci mette qualche minuto.
import { useCallback, useEffect, useRef, useState } from 'react'
import { Bottone, Carico, Errore, Icona, Vuoto } from '../snella/pezzi'
import { useAvviso, useDati } from '../snella/uso'
import {
  caricaFoto, leggiPost, leggiProfilo, nuovoPost, riscrivi, salvaProfilo, salvaTesto, scarta, urlFoto, useAscoltaPost, useDettatura,
  type Post, type Profilo, type Richiesta,
} from './datiLinkedin'

const RICHIESTE: Array<{ r: Richiesta; nome: string }> = [
  { r: 'piu_corto', nome: 'Più corto' },
  { r: 'piu_ironico', nome: 'Più ironico' },
  { r: 'cambia_framework', nome: 'Cambia framework' },
]

function Microfono({ className = 'h-7 w-7' }: { className?: string }) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.9" strokeLinecap="round" strokeLinejoin="round" className={className} aria-hidden="true">
      <path d="M12 2a3 3 0 0 0-3 3v7a3 3 0 0 0 6 0V5a3 3 0 0 0-3-3zM19 10v2a7 7 0 0 1-14 0v-2M12 19v3" />
    </svg>
  )
}

function Foto({ className = 'h-6 w-6' }: { className?: string }) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.9" strokeLinecap="round" strokeLinejoin="round" className={className} aria-hidden="true">
      <path d="M23 19a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h4l2-3h6l2 3h4a2 2 0 0 1 2 2zM12 17a4 4 0 1 0 0-8 4 4 0 0 0 0 8z" />
    </svg>
  )
}

function Crea({ fatto }: { fatto: () => void }) {
  const [testo, setTesto] = useState('')
  const [foto, setFoto] = useState<File | null>(null)
  const [anteprima, setAnteprima] = useState<string | null>(null)
  const [invio, setInvio] = useState(false)
  const [errore, setErrore] = useState<string | null>(null)
  const input = useRef<HTMLInputElement>(null)
  const aggiungi = useCallback((t: string) => { if (t) setTesto((x) => (x ? `${x.trimEnd()} ${t}` : t)) }, [])
  const d = useDettatura(aggiungi)

  useEffect(() => {
    if (!foto) { setAnteprima(null); return }
    const u = URL.createObjectURL(foto); setAnteprima(u)
    return () => URL.revokeObjectURL(u)
  }, [foto])

  const manda = async () => {
    d.ferma(); setInvio(true); setErrore(null)
    try {
      const percorso = foto ? await caricaFoto(foto) : null
      await nuovoPost(testo, percorso)
      setTesto(''); setFoto(null); fatto()
    } catch (e) { setErrore(e instanceof Error ? e.message : 'Non sono riuscito a salvarlo.') }
    setInvio(false)
  }

  const pieno = testo.trim().length > 0 || foto !== null
  return (
    <section aria-labelledby="crea" className="rounded-2xl border border-bordo bg-white p-4 lg:p-5">
      <h2 id="crea" className="sr-only">Crea</h2>
      <div className="flex items-center gap-3">
        <button type="button" onClick={d.ascolto ? d.ferma : d.parti} aria-pressed={d.ascolto}
                aria-label={d.ascolto ? 'Ferma la registrazione' : 'Parla'}
                className={`flex h-20 w-20 shrink-0 items-center justify-center rounded-full text-white transition-colors ${d.ascolto ? 'animate-pulse bg-no-segno motion-reduce:animate-none' : 'bg-blu-scuro hover:bg-navy'}`}>
          {d.ascolto ? <span className="h-6 w-6 rounded-md bg-white" /> : <Microfono className="h-8 w-8" />}
        </button>
        <div className="min-w-0 flex-1">
          <p className="text-[17px] font-bold text-inchiostro">{d.ascolto ? 'Ti ascolto' : 'Parla'}</p>
          <p className="text-[14px] text-tenue">{d.ascolto ? 'Tocca il quadrato quando hai finito.' : 'Racconta la cosa come la diresti a un amico.'}</p>
        </div>
        <button type="button" onClick={() => input.current?.click()} aria-label="Aggiungi una foto"
                className="flex h-14 w-14 shrink-0 items-center justify-center rounded-full border border-bordo bg-white text-inchiostro hover:border-tenue">
          <Foto />
        </button>
        <input ref={input} type="file" accept="image/*" className="hidden"
               onChange={(e) => { setFoto(e.target.files?.[0] ?? null); e.target.value = '' }} />
      </div>

      {d.problema && <p className="mt-3 text-[14px] font-semibold text-no-testo">{d.problema}</p>}

      <label className="mt-4 block">
        <span className="sr-only">Il testo</span>
        <textarea value={testo + (d.provvisorio ? ` ${d.provvisorio}` : '')} onChange={(e) => setTesto(e.target.value)} readOnly={d.ascolto}
                  rows={4} placeholder="Oppure scrivi qui."
                  className="w-full resize-y rounded-xl border border-bordo bg-white px-3.5 py-3 text-[16px] leading-relaxed text-inchiostro placeholder:text-tenue focus:border-blu-scuro focus:outline-none" />
      </label>

      {anteprima && (
        <div className="relative mt-3 inline-block">
          <img src={anteprima} alt="La foto del post" className="h-28 w-28 rounded-xl object-cover" />
          <button type="button" onClick={() => setFoto(null)} aria-label="Togli la foto"
                  className="absolute -right-2 -top-2 flex h-8 w-8 items-center justify-center rounded-full bg-inchiostro text-white">
            <Icona nome="chiudi" className="h-4 w-4" />
          </button>
        </div>
      )}

      {errore && <p role="alert" className="mt-3 text-[14px] font-semibold text-no-testo">{errore}</p>}
      <Bottone tipo="primo" onClick={() => void manda()} disabled={!pieno || invio} className="mt-4 w-full min-h-12 text-[16px]">
        {invio ? 'Lo mando…' : 'Fai il post'}
      </Bottone>
    </section>
  )
}

const CAMPI_PROFILO: Array<{ k: keyof Profilo; nome: string; esempio: string; righe: number }> = [
  { k: 'nome', nome: 'Nome', esempio: 'Come ti firmi', righe: 1 },
  { k: 'ruolo', nome: 'Cosa fai', esempio: 'Per esempio: sviluppatore a Studio Galilei', righe: 1 },
  { k: 'temi', nome: 'Di cosa parli', esempio: 'I due o tre temi su cui vuoi farti conoscere', righe: 2 },
  { k: 'voce', nome: 'Come parli', esempio: 'Parole tue, cosa non diresti mai, quanto sei ironico', righe: 3 },
]

/** Chi sei e come parli: la routine scrive con la tua voce. Aperto la prima volta, poi una riga. */
function ProfiloCard() {
  const [p, setP] = useState<Profilo | null>(null)
  const [aperto, setAperto] = useState(false)
  const [salvo, setSalvo] = useState(false)
  useEffect(() => { void leggiProfilo().then((x) => { setP(x ?? { nome: '', ruolo: '', temi: '', voce: '' }); if (!x?.nome) setAperto(true) }).catch(() => setP(null)) }, [])
  if (!p) return null
  if (!aperto) {
    return (
      <button type="button" onClick={() => setAperto(true)} className="mb-3 flex min-h-11 w-full items-center gap-2 rounded-xl px-1 text-left text-[14px] text-tenue hover:text-inchiostro">
        <Icona nome="penna" className="h-4 w-4 shrink-0" /> Scrivo come {p.nome || 'te'}{p.ruolo ? `, ${p.ruolo}` : ''}. Modifica
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
            <textarea value={p[c.k]} rows={c.righe} placeholder={c.esempio} onChange={(e) => setP({ ...p, [c.k]: e.target.value })}
                      className="mt-1 w-full resize-y rounded-xl border border-bordo px-3 py-2 text-[16px] text-inchiostro placeholder:text-tenue focus:border-blu-scuro focus:outline-none" />
          </label>
        ))}
      </div>
      <Bottone tipo="primo" onClick={() => void salva()} disabled={salvo || !p.nome.trim()} className="mt-3 w-full">Salva</Bottone>
    </section>
  )
}

function FotoPost({ percorso }: { percorso: string }) {
  const [url, setUrl] = useState<string | null>(null)
  useEffect(() => { let vivo = true; void urlFoto(percorso).then((u) => { if (vivo) setUrl(u) }); return () => { vivo = false } }, [percorso])
  return url ? <img src={url} alt="" className="mt-3 max-h-80 w-full rounded-xl object-cover" /> : null
}

function SchedaPost({ p, rifai, avvisa }: { p: Post; rifai: () => void; avvisa: (t: string) => void }) {
  const [quale, setQuale] = useState(p.scelta ?? 0)
  const v = p.versioni[quale]
  const [testo, setTesto] = useState(p.scelta === quale && p.testo ? p.testo : v?.testo ?? '')
  const salva = useRef(0)

  useEffect(() => { setTesto(p.scelta === quale && p.testo ? p.testo : p.versioni[quale]?.testo ?? '') }, [quale, p.versioni, p.scelta, p.testo])

  const cambia = (t: string) => {
    setTesto(t)
    window.clearTimeout(salva.current)
    salva.current = window.setTimeout(() => { void salvaTesto(p.id, quale, t) }, 800)
  }

  if (p.stato === 'da_scrivere' || p.stato === 'in_scrittura') {
    return (
      <article className="rounded-2xl border border-bordo bg-white p-4">
        <p className="flex items-center gap-2 text-[15px] font-bold text-inchiostro">
          <span className="h-2.5 w-2.5 animate-pulse rounded-full bg-blu-scuro motion-reduce:animate-none" />
          {p.stato === 'in_scrittura' ? 'Lo sto scrivendo' : 'In coda, arriva in qualche minuto'}
        </p>
        {p.dettato && <p className="mt-2 line-clamp-3 text-[15px] text-tenue">{p.dettato}</p>}
      </article>
    )
  }

  if (p.stato === 'errore' || !v) {
    return (
      <article className="rounded-2xl border border-no-bordo bg-no-fondo p-4">
        <p className="text-[15px] font-bold text-no-testo">Non sono riuscito a scriverlo</p>
        {p.errore && <p className="mt-1 text-[14px] text-no-testo">{p.errore}</p>}
        <div className="mt-3 flex flex-wrap gap-2">
          <Bottone onClick={() => void riscrivi(p, 'cambia_framework').then(rifai)}>Riprova</Bottone>
          <Bottone tipo="piatto" onClick={() => void scarta(p.id).then(rifai)}>Scarta</Bottone>
        </div>
      </article>
    )
  }

  const caratteri = testo.length
  const copia = async () => {
    try { await navigator.clipboard.writeText(testo); avvisa('Testo copiato. Incollalo su LinkedIn.') } catch { avvisa('Non riesco a copiarlo da qui.') }
  }

  return (
    <article className="rounded-2xl border border-bordo bg-white p-4">
      {p.versioni.length > 1 && (
        <div role="tablist" aria-label="Versioni" className="mb-3 flex gap-2 overflow-x-auto">
          {p.versioni.map((x, i) => (
            <button key={i} role="tab" aria-selected={i === quale} onClick={() => setQuale(i)}
                    className={`min-h-10 shrink-0 rounded-full border px-3.5 text-[14px] font-semibold ${i === quale ? 'border-blu-scuro bg-blu-scuro text-white' : 'border-bordo bg-white text-inchiostro'}`}>
              {x.framework}
            </button>
          ))}
        </div>
      )}

      <div className="flex items-center gap-2.5">
        <span className="flex h-10 w-10 items-center justify-center rounded-full bg-navy text-[14px] font-bold text-white">Tu</span>
        <span className="text-[14px] font-semibold text-inchiostro">Il tuo post</span>
      </div>
      <label className="mt-2 block">
        <span className="sr-only">Testo del post</span>
        <textarea value={testo} onChange={(e) => cambia(e.target.value)} rows={Math.min(22, Math.max(8, Math.ceil(caratteri / 42)))}
                  className="w-full resize-y rounded-xl border border-transparent bg-white px-0 py-1 text-[16px] leading-relaxed text-inchiostro hover:border-bordo focus:border-blu-scuro focus:px-2 focus:outline-none" />
      </label>
      {p.foto && <FotoPost percorso={p.foto} />}
      <p className={`mt-2 text-[13px] font-semibold ${caratteri >= 900 && caratteri <= 1500 ? 'text-ok-testo' : 'text-attesa-testo'}`}>
        {caratteri} caratteri {caratteri < 900 ? '(sotto i 900)' : caratteri > 1500 ? '(sopra i 1.500)' : ''}
      </p>
      {v.giudice?.note && <p className="mt-1 text-[14px] text-tenue">{v.giudice.note}</p>}

      <div className="mt-3 grid grid-cols-[repeat(auto-fit,minmax(9rem,1fr))] gap-2">
        {RICHIESTE.map((x) => (
          <Bottone key={x.r} onClick={() => void riscrivi(p, x.r).then(() => { avvisa('Lo riscrivo.'); rifai() })}>{x.nome}</Bottone>
        ))}
        <Bottone tipo="primo" onClick={() => void copia()}>Copia il testo</Bottone>
      </div>
      <button type="button" onClick={() => void scarta(p.id).then(rifai)} className="mt-2 min-h-11 px-1 text-[14px] font-semibold text-tenue hover:text-inchiostro">
        Scarta
      </button>
    </article>
  )
}

export default function Linkedin() {
  const { dati, errore, caricando, rifai } = useDati(leggiPost)
  const ricarica = useCallback(() => { void rifai() }, [rifai])
  useAscoltaPost(ricarica)
  const { mostra, vista } = useAvviso()
  const avvisa = useCallback((testo: string) => mostra({ testo }), [mostra])

  return (
    <div className="mx-auto max-w-2xl">
      <h1 className="mb-4 text-[26px] font-extrabold text-inchiostro">LinkedIn</h1>
      <ProfiloCard />
      <Crea fatto={() => { avvisa('Ricevuto. Arriva in qualche minuto.'); ricarica() }} />
      <h2 className="mb-3 mt-8 text-[19px] font-bold text-inchiostro">Post</h2>
      {errore ? <Errore testo={errore} riprova={ricarica} />
        : caricando && !dati ? <Carico righe={2} />
          : !dati?.length ? <Vuoto>Ancora nessun post.</Vuoto>
            : <div className="space-y-3">{dati.map((p) => <SchedaPost key={p.id} p={p} rifai={ricarica} avvisa={avvisa} />)}</div>}
      {vista}
    </div>
  )
}
