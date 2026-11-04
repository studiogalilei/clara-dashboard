// IL PROFILO (4/11): cerchi un'azienda e vedi tutto, a colpo d'occhio: sito, email, referenti, note; poi le decisioni di Clara e il filo.
import { useEffect, useState, type ReactNode } from 'react'
import { aggiungiNota, cerca, leggiRelazione, prendiInMano, type Trovato } from './dati'
import { MOSSE, iniziali } from './regole'
import { Bottone, Carico, Errore, Icona, Pillola, Vuoto } from '../snella/pezzi'
import { useAvviso, useDati } from '../snella/uso'
import { quando } from '../snella/regole'
import type { Dove } from './Desk'
import { Note } from './Note'

export default function Filo({ dove, vai, indietro }: { dove: Dove; vai: (d: Dove) => void; indietro: () => void }) {
  if (dove.id) return <Relazione id={dove.id} indietro={indietro} vai={vai} />
  return <Ricerca vai={vai} />
}

function Tessera({ titolo, children }: { titolo: string; children: ReactNode }) {
  return (
    <div className="rounded-xl border border-bordo bg-velo/40 px-3 py-2.5 text-[14px] leading-snug">
      <p className="mb-1 text-[11px] font-extrabold uppercase tracking-[.08em] text-tenue">{titolo}</p>
      {children}
    </div>
  )
}

function Ricerca({ vai }: { vai: (d: Dove) => void }) {
  const [q, setQ] = useState('')
  const [trovati, setTrovati] = useState<Trovato[] | null>(null)
  const [errore, setErrore] = useState<string | null>(null)
  useEffect(() => {
    if (q.trim().length < 2) { setTrovati(null); return }
    const t = window.setTimeout(() => { cerca(q).then((r) => { setTrovati(r); setErrore(null) }).catch((e) => setErrore(e instanceof Error ? e.message : String(e))) }, 250)
    return () => window.clearTimeout(t)
  }, [q])
  return (
    <section className="mx-auto max-w-[760px] rounded-2xl border border-bordo bg-white">
      <header className="border-b border-bordo p-4 lg:p-5">
        <h1 className="text-[22px] font-bold leading-tight text-navy lg:text-[26px]">Le relazioni</h1>
        <p className="mt-1 text-[13.5px] text-tenue">Un’azienda, tutto quello che c’è stato.</p>
        <label className="mt-3 flex min-h-11 items-center gap-2 rounded-xl border border-bordo bg-white px-3 text-tenue focus-within:border-navy">
          <Icona nome="cerca" className="h-4 w-4 shrink-0" />
          <input value={q} onChange={(e) => setQ(e.target.value)} autoFocus placeholder="Azienda, persona o email" aria-label="Cerca un'azienda"
                 className="min-w-0 flex-1 bg-transparent text-[15px] text-inchiostro outline-none placeholder:text-spento" />
        </label>
      </header>
      {errore && <Errore testo={errore} />}
      {trovati && trovati.length === 0 && <Vuoto>Nessuna azienda con questo nome.</Vuoto>}
      {trovati && trovati.length > 0 && (
        <ul className="space-y-2 p-3 lg:p-4">
          {trovati.map((t) => (
            <li key={t.id} className="rounded-xl border border-bordo bg-white hover:border-tenue">
              <button onClick={() => vai({ voce: 'filo', id: t.id })} className="flex w-full items-center gap-3 px-4 py-3 text-left hover:bg-fondo/70">
                <span className="grid h-9 w-9 shrink-0 place-items-center rounded-lg bg-navy/[0.08] text-[12px] font-extrabold text-navy">{iniziali(t.azienda)}</span>
                <span className="min-w-0 flex-1">
                  <span className="block truncate text-[14.5px] font-bold text-inchiostro">{t.azienda || t.email}</span>
                  <span className="block truncate text-[12.5px] text-tenue">{[t.persona, t.citta, t.fase?.replace(/_/g, ' ')].filter(Boolean).join(', ')}</span>
                </span>
                <span className="shrink-0 text-[12px] text-tenue">{t.ultima_risposta ? quando(t.ultima_risposta) : 'mai risposto'}</span>
              </button>
            </li>
          ))}
        </ul>
      )}
      {!trovati && !errore && <p className="p-5 text-[13.5px] text-tenue">Scrivi almeno due lettere.</p>}
    </section>
  )
}

function Relazione({ id, indietro, vai }: { id: string; indietro: () => void; vai: (d: Dove) => void }) {
  const { dati, setDati, errore, caricando, rifai } = useDati(() => leggiRelazione(id), [id])
  const { mostra, vista } = useAvviso()
  const [nota, setNota] = useState('')
  if (caricando) return <Carico righe={4} etichetta="Carico la relazione" />
  if (errore && !dati) return <Errore testo={errore} riprova={() => void rifai()} />
  if (!dati?.lead) return <Vuoto>Questa azienda non c’è più.</Vuoto>
  const l = dati.lead
  const salvaNota = async () => {
    if (!nota.trim()) return
    try {
      await aggiungiNota(l.id, nota)
      setDati((prev) => prev ? { ...prev, note: [{ at: new Date().toISOString(), tipo: 'nota', testo: nota.trim() }, ...prev.note] } : prev)
      setNota(''); mostra({ testo: 'Nota salvata. Clara la legge.' })
    } catch (e) { mostra({ testo: e instanceof Error ? e.message : String(e) }) }
  }
  const aperta = dati.decisioni.find((d) => d.stato === 'proposta' || d.stato === 'approvata')
  const mia = !!l.in_mano_a
  const cambiaMano = async (lascia: boolean) => {
    const perche = lascia ? '' : (window.prompt('Perché la prendi tu? (mi ha chiamato, l’ho chiamato io, ci ho parlato…)') ?? '')
    if (!lascia && perche === '') return
    try {
      await prendiInMano(l.id, perche, lascia)
      setDati((prev) => prev && prev.lead ? { ...prev, lead: { ...prev.lead, in_mano_a: lascia ? null : 'Dre', in_mano_motivo: lascia ? null : perche, in_mano_il: lascia ? null : new Date().toISOString() } } : prev)
      mostra({ testo: lascia ? 'Torna a Clara.' : 'È tua: Clara si ferma qui.' })
    } catch (e) { mostra({ testo: e instanceof Error ? e.message : String(e) }) }
  }
  return (
    <div className="mx-auto max-w-[900px] space-y-4">
      <section className="rounded-2xl border border-bordo bg-white p-4 lg:p-5">
        <button onClick={indietro} className="-ml-2 mb-3 inline-flex min-h-10 items-center gap-1 rounded-full px-2 text-[14px] font-semibold text-navy"><Icona nome="indietro" className="h-4 w-4" /> Indietro</button>
        <div className="flex items-start gap-3">
          <span className="grid h-12 w-12 shrink-0 place-items-center rounded-xl bg-ok-testo text-[16px] font-extrabold text-white">{iniziali(l.azienda)}</span>
          <div className="min-w-0 flex-1">
            <p className="text-[11.5px] font-extrabold uppercase tracking-[.08em] text-ok-testo">Profilo</p>
            <h1 className="text-[22px] font-bold leading-tight text-inchiostro">{l.azienda || l.email}</h1>
            <p className="text-[13.5px] text-tenue">{[l.citta, l.settore].filter(Boolean).join(', ')}</p>
            <div className="mt-2 flex flex-wrap gap-1.5">
              {l.fase && <Pillola testo={l.fase.replace(/_/g, ' ')} tono={l.fase === 'cliente' ? 'ok' : l.fase === 'perso' ? 'no' : 'neutro'} />}
              {l.analisi_mandata && <Pillola testo={`Analisi mandata ${quando(l.analisi_il)}`} tono="noi" />}
              {l.fit && <Pillola testo={`Fit ${l.fit}`} tono={l.fit === 'NO' ? 'no' : l.fit === 'SI' ? 'ok' : 'attesa'} />}
              {l.no_followup && <Pillola testo="Non contattare" tono="stop" icona="divieto" />}
              {mia && <Pillola testo={`Me ne occupo io${l.in_mano_motivo ? `: ${l.in_mano_motivo}` : ''}`} tono="stop" piena />}
            </div>
          </div>
        </div>
        <div className="mt-4 grid gap-2 sm:grid-cols-3">
          <Tessera titolo="Sito">
            {l.sito ? <a href={/^https?:/.test(l.sito) ? l.sito : `https://${l.sito}`} target="_blank" rel="noreferrer" className="break-all font-bold text-navy underline-offset-2 hover:underline">{l.sito.replace(/^https?:\/\/(www\.)?/, '').replace(/\/$/, '')}</a> : <span className="text-tenue">non registrato</span>}
          </Tessera>
          <Tessera titolo="Email">
            <a href={`mailto:${l.email}`} className="break-all font-bold text-navy underline-offset-2 hover:underline">{l.email}</a>
            {(l.altre_email ?? []).filter((e) => e && e !== l.email).map((e) => <a key={e} href={`mailto:${e}`} className="block break-all text-[13px] text-navy underline-offset-2 hover:underline">{e}</a>)}
          </Tessera>
          <Tessera titolo={l.persona ? 'Referente' : 'Referenti'}>
            {l.persona ? <span className="block font-bold text-inchiostro">{l.persona}</span> : <span className="text-tenue">nessun nome</span>}
            {l.ruolo && <span className="block text-[13px] text-tenue">{l.ruolo}</span>}
            {l.telefono && <a href={`tel:${l.telefono.replace(/\s/g, '')}`} className="block font-semibold text-navy underline-offset-2 hover:underline">{l.telefono}</a>}
          </Tessera>
        </div>
        <dl className="mt-4 grid grid-cols-[92px_1fr] gap-x-3 gap-y-1.5 text-[13.5px]">
          {l.cosa_fa && <><dt className="text-tenue">Cosa fa</dt><dd>{l.cosa_fa}</dd></>}
          {l.fit_motivo && <><dt className="text-tenue">Il fit</dt><dd>{l.fit_motivo}</dd></>}
          {l.analisi_pdf && <><dt className="text-tenue">Analisi</dt><dd><a href={l.analisi_pdf} target="_blank" rel="noreferrer" className="font-semibold text-navy underline-offset-2 hover:underline">Apri il PDF</a></dd></>}
          {aperta?.mossa === 'escalate' && aperta.testo && <><dt className="text-tenue">Proposta</dt><dd className="whitespace-pre-wrap">{aperta.testo.trim()}</dd></>}
          <dt className="text-tenue">Fonte</dt><dd>{l.fonte || 'non registrata'}</dd>
        </dl>
        <div className="mt-4 flex flex-wrap gap-2">
          {aperta && !mia && <Bottone tipo="primo" onClick={() => vai({ voce: 'relazioni', id: aperta.id })}>Vai alla mossa in coda: {MOSSE[aperta.mossa].nome}</Bottone>}
          {mia ? <Bottone onClick={() => void cambiaMano(true)}>Ridalla a Clara</Bottone> : <Bottone onClick={() => void cambiaMano(false)}>Me ne occupo io: ferma Clara</Bottone>}
        </div>
      </section>

      <section className="rounded-2xl border border-bordo bg-white p-4 lg:p-5">
        <h2 className="mb-3 text-[12px] font-extrabold uppercase tracking-[.08em] text-tenue">Note e agenda</h2>
        <div className="flex gap-2">
          <input value={nota} onChange={(e) => setNota(e.target.value)} placeholder="Una nota per te e per Clara" aria-label="Nota"
                 onKeyDown={(e) => { if (e.key === 'Enter') void salvaNota() }}
                 className="min-h-11 min-w-0 flex-1 rounded-xl border border-bordo px-3 text-[14px] outline-none focus:border-navy" />
          <Bottone onClick={() => void salvaNota()} disabled={!nota.trim()}>Salva</Bottone>
        </div>
        <Note note={dati.note} className="mt-3" />
        {dati.agenda.length > 0 && <ul className="mt-3 space-y-1 border-t border-bordo pt-3 text-[13.5px]">{dati.agenda.map((a, i) => <li key={i}><b>{quando(a.at)}</b>, {a.tipo || a.titolo}{a.link && <> (<a href={a.link} className="text-navy underline-offset-2 hover:underline" target="_blank" rel="noreferrer">apri</a>)</>}</li>)}</ul>}
      </section>

      <section className="rounded-2xl border border-bordo bg-white p-4 lg:p-5">
        <h2 className="mb-3 text-[12px] font-extrabold uppercase tracking-[.08em] text-tenue">Il filo, dal più recente</h2>
        {dati.filo.length === 0 ? <p className="text-[13.5px] text-tenue">Nessuna mail registrata.</p> : (
          <ul className="space-y-3">
            {[...dati.filo].reverse().map((m, i) => {
              const nostra = m.tipo === 'email_out'
              return (
                <li key={i} className={`max-w-[92%] rounded-2xl px-3.5 py-2.5 text-[13.5px] leading-relaxed ${nostra ? 'ml-auto rounded-br-md bg-noi-fondo text-inchiostro' : 'rounded-bl-md bg-loro-fondo/70 text-inchiostro'}`}>
                  <p className={`mb-1 text-[11.5px] font-bold ${nostra ? 'text-noi-testo' : 'text-loro-testo'}`}>{nostra ? 'Noi' : l.persona || 'Lead'}, {quando(m.at)}</p>
                  <p className="whitespace-pre-wrap">{(m.testo ?? '').trim().slice(0, 2500)}</p>
                </li>
              )
            })}
          </ul>
        )}
      </section>

      <section className="rounded-2xl border border-bordo bg-white p-4 lg:p-5">
        <h2 className="mb-3 text-[12px] font-extrabold uppercase tracking-[.08em] text-tenue">Le decisioni di Clara</h2>
        {dati.decisioni.length === 0 ? <p className="text-[13.5px] text-tenue">Ancora nessuna.</p> : (
          <ul className="space-y-2">
            {dati.decisioni.map((d) => (
              <li key={d.id} className="rounded-xl border border-bordo px-3.5 py-2.5">
                <div className="flex flex-wrap items-center gap-2">
                  <Pillola testo={MOSSE[d.mossa].nome} tono={MOSSE[d.mossa].tono} />
                  <span className="text-[12.5px] text-tenue">{quando(d.creato_il)}, {d.stato}{d.esito ? `, ${d.esito}` : ''}{d.dre_giudizio ? `, Dre: ${d.dre_giudizio}` : ''}</span>
                </div>
                {d.perche && <p className="mt-1 text-[13.5px] text-inchiostro">{d.perche}</p>}
                {d.dre_nota && <p className="mt-1 text-[13px] text-tenue">Dre: {d.dre_nota}</p>}
              </li>
            ))}
          </ul>
        )}
      </section>

      {vista}
    </div>
  )
}
