// LE CALL: le conoscitive in agenda e chi va richiamato. Esiti a un tocco.
import { useState } from 'react'
import { leggiCall, segnaConsiglio, segnaEsito } from './dati'
import { agendaPulita, ESITI_CHIAMATA, telefonoDa } from './regole'
import { Bottone, Carico, Errore, Icona, Pillola, Vuoto } from '../snella/pezzi'
import { useAvviso, useDati } from '../snella/uso'
import { TONO } from '../snella/toni'
import type { Consiglio } from './dati'
import { giornoRoma, nomeGiorno, ora, quando } from '../snella/regole'
import type { Dove } from './Desk'

export default function Call({ vai }: { vai: (d: Dove) => void }) {
  const { dati, setDati, errore, caricando, rifai } = useDati(() => leggiCall())
  const { mostra, vista } = useAvviso()
  const [lavoro, setLavoro] = useState<string | null>(null)
  if (caricando) return <Carico righe={3} etichetta="Carico le call" />
  if (errore && !dati) return <Errore testo={errore} riprova={() => void rifai()} />
  const c = dati ?? { prossime: [], richiami: [], consigli: [] }
  const giorni = new Map<string, typeof c.prossime>()
  for (const p of agendaPulita(c.prossime)) { const g = giornoRoma(new Date(p.at)); giorni.set(g, [...(giorni.get(g) ?? []), p]) }

  const consiglioFatto = async (id: string, c: Consiglio | null, e: string) => {
    setLavoro(id)
    try {
      await segnaConsiglio({ id, consiglio: c }, e)
      setDati((prev) => prev ? { ...prev, consigli: (prev.consigli ?? []).filter((r) => r.id !== id) } : prev)
      mostra({ testo: 'Segnato.' })
    } catch (err) { mostra({ testo: err instanceof Error ? err.message : String(err) }) } finally { setLavoro(null) }
  }
  const esito = async (id: string, e: string) => {
    setLavoro(id)
    try {
      await segnaEsito(id, e)
      setDati((prev) => prev ? { ...prev, richiami: prev.richiami.filter((r) => r.id !== id) } : prev)
      mostra({ testo: 'Segnato.' })
    } catch (err) { mostra({ testo: err instanceof Error ? err.message : String(err) }) } finally { setLavoro(null) }
  }

  return (
    <div className="space-y-4 lg:grid lg:grid-cols-2 lg:items-start lg:gap-4 lg:space-y-0">
      <div className="space-y-4">
      <section className="rounded-2xl border border-bordo bg-white">
        <header className="border-b border-bordo p-4 lg:p-5">
          <h1 className="text-[22px] font-bold leading-tight text-inchiostro lg:text-[26px]">Da richiamare</h1>
          <p className="mt-1 text-[13.5px] text-tenue">Solo chi l’ha chiesto. Chiami, poi un tocco sull’esito.</p>
        </header>
        {c.richiami.length === 0 ? <Vuoto>Nessuno da richiamare adesso.</Vuoto> : (
          <ul className="space-y-2.5 p-3 lg:p-4">
            {c.richiami.map((r) => {
              const tel = telefonoDa(r.telefono)
              return (
              <li key={r.id} className="space-y-2.5 rounded-xl border border-bordo bg-white p-4">
                <button onClick={() => vai({ voce: 'filo', id: r.prospect_id })} className="block w-full min-w-0 text-left">
                  <span className="block truncate text-[15px] font-bold text-inchiostro">{r.azienda}</span>
                  <span className="block text-[13px] text-tenue">{[r.persona, quando(r.risposta_il)].filter(Boolean).join(' · ')}</span>
                </button>
                {r.quando && <p className="text-[13.5px] text-inchiostro"><span className="font-semibold">Quando:</span> {r.quando}</p>}
                {tel ? (
                  <a href={`tel:${tel.replace(/[^\d+]/g, '')}`} className="inline-flex min-h-11 items-center gap-2 rounded-full bg-ok-testo px-4 text-[15px] font-bold text-white">
                    <Icona nome="telefono" className="h-4 w-4" /> {tel}
                  </a>
                ) : <Pillola testo="Senza numero: chiedilo" tono="attesa" />}
                {r.perche && <p className="text-[13.5px] leading-relaxed text-inchiostro">{r.perche}</p>}
                {r.lead_testo && <blockquote className="rounded-r-xl border-l-2 border-loro-segno bg-loro-fondo/60 px-3 py-2 text-[13px] text-inchiostro">{r.lead_testo.replace(/\s+/g, ' ').slice(0, 240)}</blockquote>}
                <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
                  {ESITI_CHIAMATA.map((e) => <Bottone key={e.esito} tipo={e.esito === 'fissata' ? 'primo' : 'secondo'} onClick={() => void esito(r.id, e.esito)} disabled={lavoro === r.id} className="px-2 text-[13px]">{e.nome}</Bottone>)}
                </div>
              </li>
              )
            })}
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
            {(c.consigli ?? []).map((r) => {
              const tel = telefonoDa(r.telefono)
              return (
                <li key={r.id} className={`space-y-2 rounded-xl border p-4 ${TONO.giallo.morbido}`}>
                  <button onClick={() => vai({ voce: 'filo', id: r.prospect_id })} className="block w-full min-w-0 text-left">
                    <span className="block truncate text-[15px] font-bold">{r.azienda}</span>
                    <span className="block text-[13px] opacity-80">{[r.persona, quando(r.risposta_il)].filter(Boolean).join(' · ')}</span>
                  </button>
                  {r.perche && <p className="text-[13.5px] leading-relaxed">{r.perche}</p>}
                  <div className="flex flex-wrap items-center gap-2">
                    {tel && <a href={`tel:${tel.replace(/[^\d+]/g, '')}`} className="inline-flex min-h-10 items-center gap-2 rounded-full bg-ok-testo px-4 text-[14px] font-bold text-white"><Icona nome="telefono" className="h-4 w-4" /> {tel}</a>}
                    <Bottone onClick={() => void consiglioFatto(r.id, r.consiglio, 'chiamato')} disabled={lavoro === r.id} className="text-[13px]">Chiamato</Bottone>
                    <Bottone tipo="piatto" onClick={() => void consiglioFatto(r.id, r.consiglio, 'non_ora')} disabled={lavoro === r.id} className="text-[13px]">Non ora</Bottone>
                  </div>
                </li>
              )
            })}
          </ul>
        )}
      </section>
      </div>

      <section className="rounded-2xl border border-bordo bg-white">
        <header className="border-b border-bordo p-4 lg:p-5">
          <h2 className="text-[22px] font-bold leading-tight text-inchiostro lg:text-[26px]">Le call in agenda</h2>
          <p className="mt-1 text-[13.5px] text-tenue">Le prossime due settimane, dal tuo calendario.</p>
        </header>
        {giorni.size === 0 ? <Vuoto>Niente in agenda nei prossimi 14 giorni.</Vuoto> : (
          <div className="divide-y divide-velo">
            {[...giorni.entries()].map(([g, call]) => (
              <div key={g} className="p-4">
                <h3 className="mb-2 text-[12px] font-extrabold uppercase tracking-[.08em] text-tenue">{nomeGiorno(g)}</h3>
                <ul className="space-y-2">
                  {call.map((p, i) => (
                    <li key={i} className="flex items-center gap-3 rounded-xl bg-fondo/70 px-3.5 py-2.5">
                      <span className="w-12 shrink-0 text-[15px] font-extrabold text-navy">{ora(p.at)}</span>
                      <button onClick={() => p.prospect_id && vai({ voce: 'filo', id: p.prospect_id })} className="min-w-0 flex-1 text-left" disabled={!p.prospect_id}>
                        <span className="block truncate text-[14.5px] font-bold text-inchiostro">{p.azienda || p.titolo}</span>
                        <span className="block truncate text-[12.5px] text-tenue">{[p.tipo, p.persona].filter(Boolean).join(' · ')}</span>
                      </button>
                      {p.link && <a href={p.link} target="_blank" rel="noreferrer" className="grid h-10 w-10 shrink-0 place-items-center rounded-full border border-bordo text-navy hover:border-navy" aria-label="Apri la call"><Icona nome="video" className="h-4 w-4" /></a>}
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </div>
        )}
      </section>
      {vista}
    </div>
  )
}
