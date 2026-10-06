import { useMemo, useState } from 'react'
import { supabase } from '../../lib/supabase'
import type { Prospect } from '../../lib/types'
import { CLS_LABEL } from '../../lib/types'
import { tappaDi, riprendiDallArchivio } from '../../lib/percorso'
import { giorno } from '../../lib/regole'
import { fmtDateShort } from '../ui'

// L'ARCHIVIO (Dre, 6/10 sera): «dopo il follow-up parte un timer di 10 giorni, il
// timer per l'archiviazione. Se non abbiamo riscontro finisce in archivio: tutte le
// aziende alle quali abbiamo inviato l'analisi e che non si sono fatte sentire. Lo
// teniamo al sicuro, perche' in futuro ci possiamo fare qualcosa: posso prendere
// se voglio.» Il timer c'e' gia' (scripts/silenzi.py, 10 giorni dopo il follow-up
// partito). Qui il posto dove ritrovarli: filtrabili, esportabili per una campagna,
// e uno alla volta si rimettono fra i lead. Nessuna mail parte da qui.

export const ARCHIVIATO = /^Nessuna risposta dopo l'analisi/i
export const eArchiviato = (p: Prospect) => tappaDi(p) === 'perso' && ARCHIVIATO.test(p.lost_reason ?? '')

// chi non si ricontatta comunque: il no detto, i nervosi, i soppressi
const MAI = new Set(['negativo', 'nervoso', 'soppresso', 'fuori_target', 'persona_sbagliata'])

const nomeDi = (p: Prospect) => p.company || p.name || p.email
const settoreDi = (p: Prospect) => (p.sector ?? '').replace(/_/g, ' ') || 'senza settore'
const meseDi = (iso: string | null) => iso ? new Date(iso).toLocaleDateString('it-IT', { month: 'long', year: 'numeric' }) : 'senza data'

function fitDi(p: Prospect): string | null {
  const e = (p.enriched ?? {}) as Record<string, unknown>
  const v = ((e.google_fit_v2 as { verdetto?: string } | undefined)?.verdetto) ?? ((e.google_fit as { verdetto?: string } | undefined)?.verdetto)
  return v ?? null
}

function csv(righe: Prospect[]): string {
  const q = (x: unknown) => `"${String(x ?? '').replace(/"/g, '""')}"`
  const testa = ['azienda', 'email', 'referente', 'settore', 'citta', 'sito', 'analisi_del', 'aveva_detto', 'google_fit', 'codice']
  return [testa.join(','), ...righe.map((p) => [
    nomeDi(p), p.email, p.name, settoreDi(p), p.city, p.website, (p.analysis_sent_at ?? '').slice(0, 10),
    p.classificazione ? CLS_LABEL[p.classificazione] : '', fitDi(p) ?? '', p.sg_id != null ? `SG-${p.sg_id}` : '',
  ].map(q).join(','))].join('\n')
}

export default function Archivio({ righe, onScheda, onCambiato }: {
  righe: Prospect[]
  onScheda: (id: string) => void
  onCambiato: (p: Prospect) => void
}) {
  const [settore, setSettore] = useState<string | null>(null)
  const [soloSi, setSoloSi] = useState(false)
  const [chiedo, setChiedo] = useState<string | null>(null)
  const [guaio, setGuaio] = useState<string | null>(null)

  const settori = useMemo(() => {
    const m = new Map<string, number>()
    for (const p of righe) m.set(settoreDi(p), (m.get(settoreDi(p)) ?? 0) + 1)
    return [...m.entries()].sort((a, b) => b[1] - a[1])
  }, [righe])

  const visibili = useMemo(() => righe
    .filter((p) => (!settore || settoreDi(p) === settore) && (!soloSi || p.classificazione === 'positivo'))
    .sort((a, b) => (b.analysis_sent_at ?? '').localeCompare(a.analysis_sent_at ?? '')), [righe, settore, soloSi])

  // per mese dell'analisi: l'archivio si legge come uno scaffale, dal piu' recente
  const perMese = useMemo(() => {
    const m = new Map<string, Prospect[]>()
    for (const p of visibili) m.set(meseDi(p.analysis_sent_at), [...(m.get(meseDi(p.analysis_sent_at)) ?? []), p])
    return [...m.entries()]
  }, [visibili])

  const si = righe.filter((p) => p.classificazione === 'positivo').length

  function esporta() {
    const url = URL.createObjectURL(new Blob(['﻿' + csv(visibili)], { type: 'text/csv;charset=utf-8' }))
    const a = document.createElement('a')
    a.href = url; a.download = `archivio-${giorno()}${settore ? `-${settore.replace(/\s+/g, '-')}` : ''}.csv`; a.click()
    setTimeout(() => URL.revokeObjectURL(url), 5000)
  }

  // RIMETTERE FRA I LEAD: torna con l'analisi gia' ricevuta, il motivo d'uscita si toglie,
  // e da li' valgono le regole di sempre. Nessuna mail parte da qui: se nasce una bozza,
  // passa dalla Posta come tutte.
  async function riprendi(p: Prospect) {
    if (chiedo !== p.id) { setChiedo(p.id); return }
    setChiedo(null); setGuaio(null)
    const m = riprendiDallArchivio(p)
    if ('no' in m) { setGuaio(`${nomeDi(p)}: ${m.no}`); return }
    const { data, error } = await supabase.from('prospects').update(m.patch).eq('id', p.id).select().single()
    if (error || !data) { setGuaio(`${nomeDi(p)} resta in archivio: ${error?.message ?? 'il database non ha risposto'}`); return }
    const { error: e2 } = await supabase.from('interactions').insert({
      prospect_id: p.id, at: new Date().toISOString(), kind: 'nota', body: m.nota,
    })
    if (e2) setGuaio(`${nomeDi(p)} è tornato fra i lead, ma la nota in storia non è nata: ${e2.message}`)
    onCambiato(data as Prospect)
  }

  return (
    <div>
      <div className="mb-3 flex flex-wrap items-center gap-2">
        <p className="mr-2 text-[14px] text-tenue">
          <b className="text-inchiostro">{righe.length}</b> hanno avuto l'analisi e poi il silenzio, <b className="text-inchiostro">{si}</b> avevano detto sì.
        </p>
        <button onClick={() => setSoloSi((v) => !v)}
                className={`rounded-full border px-3 py-1 text-[12px] font-semibold ${soloSi ? 'border-green-700 bg-green-50 text-green-800' : 'border-bordo text-tenue hover:border-navy hover:text-navy'}`}>
          Solo chi aveva detto sì
        </button>
        <button onClick={esporta} disabled={!visibili.length}
                className="ml-auto rounded-full bg-blu px-3.5 py-1.5 text-[12px] font-bold text-white hover:bg-navy disabled:opacity-40">
          Esporta {visibili.length} per una campagna
        </button>
      </div>
      {settori.length > 1 && (
        <div className="mb-4 flex flex-wrap gap-1.5">
          <button onClick={() => setSettore(null)}
                  className={`rounded-full px-3 py-1 text-[12px] font-semibold ${!settore ? 'bg-navy text-white' : 'text-tenue hover:text-navy'}`}>Tutti</button>
          {settori.map(([s, n]) => (
            <button key={s} onClick={() => setSettore(settore === s ? null : s)}
                    className={`rounded-full px-3 py-1 text-[12px] font-semibold ${settore === s ? 'bg-navy text-white' : 'text-tenue hover:text-navy'}`}>
              {s} <span className="tabular-nums opacity-70">{n}</span>
            </button>
          ))}
        </div>
      )}
      {guaio && <p className="mb-3 inline-block rounded-full bg-red-50 px-3 py-1 text-[12px] font-semibold text-red-700">{guaio}</p>}
      {visibili.length === 0 && <p className="text-sm text-spento">L'archivio è vuoto: ci finisce chi, dopo analisi e follow-up, tace per 10 giorni.</p>}
      <div className="space-y-5">
        {perMese.map(([mese, lista]) => (
          <section key={mese}>
            <h3 className="mb-1.5 text-[11px] font-bold uppercase tracking-[0.06em] text-navy/70">
              Analisi di {mese} <span className="tabular-nums text-tenue">{lista.length}</span>
            </h3>
            <ul className="divide-y divide-velo rounded-2xl border border-bordo bg-white">
              {lista.map((p) => {
                const fit = fitDi(p)
                const mai = MAI.has(p.classificazione ?? '')
                return (
                  <li key={p.id} className="flex flex-wrap items-center gap-x-3 gap-y-1 px-4 py-2.5">
                    <button onClick={() => onScheda(p.id)} className="min-w-0 flex-1 text-left">
                      <span className="block truncate text-[14px] font-semibold text-inchiostro hover:text-navy">{nomeDi(p)}</span>
                      <span className="block truncate text-[12.5px] text-tenue">
                        {[settoreDi(p), p.city, p.analysis_sent_at ? `analisi del ${fmtDateShort(p.analysis_sent_at)}` : null].filter(Boolean).join(', ')}
                      </span>
                    </button>
                    {p.classificazione === 'positivo' && <span className="shrink-0 rounded-full bg-green-50 px-2.5 py-0.5 text-[11px] font-bold text-green-800">aveva detto sì</span>}
                    {fit && <span className="shrink-0 text-[11px] font-semibold text-tenue">fit {fit}</span>}
                    {mai
                      ? <span className="shrink-0 text-[11px] font-semibold text-spento">non si ricontatta</span>
                      : (
                        <button onClick={() => void riprendi(p)}
                                className={`shrink-0 rounded-full px-3 py-1 text-[12px] font-semibold ${chiedo === p.id ? 'bg-blu text-white' : 'border border-bordo text-navy hover:border-navy'}`}>
                          {chiedo === p.id ? 'Sicuro? Torna fra i lead' : 'Riprendi'}
                        </button>
                      )}
                  </li>
                )
              })}
            </ul>
          </section>
        ))}
      </div>
    </div>
  )
}
