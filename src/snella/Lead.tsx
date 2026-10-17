// LEAD: chi ha risposto negli ultimi 60 giorni, l'ultima risposta in cima.
// Cerca per nome o azienda, filtra coi nomi delle categorie di Dre su Smartlead.
import { useMemo, useState } from 'react'
import { STATI, leggiDecisioni, leggiRighe, type Decisione, type RigaLead } from './dati'
import { cerca, contaStati, quando, statoDi, tonoStato } from './regole'
import { Bottone, Carico, Errore, Icona, PillolaStato, Vuoto } from './pezzi'
import { TONO } from './toni'
import { linkCompleto, useDati } from './uso'

const PASSO = 80

function ricorda(k: string, v?: string): string | null {
  try {
    if (v === undefined) return sessionStorage.getItem(k)
    sessionStorage.setItem(k, v)
  } catch { /* in privato non si ricorda: pazienza */ }
  return null
}

async function caricaLead(): Promise<{ righe: RigaLead[]; decisioni: Map<string, Decisione> }> {
  const decisioni = await leggiDecisioni()
  const righe = await leggiRighe(60)
  return { righe, decisioni }
}

export default function Lead({ apri }: { apri: (id: string) => void }) {
  const { dati, errore, caricando, rifai } = useDati(caricaLead)
  const [q, setQ] = useState(() => ricorda('snella-cerca') ?? '')
  const [filtro, setFiltro] = useState<string>(() => ricorda('snella-filtro') ?? 'Tutti')
  const [quanti, setQuanti] = useState(PASSO)

  const conta = useMemo(() => dati ? contaStati(dati.righe, dati.decisioni) : new Map<string, number>(), [dati])
  const visibili = useMemo(() => {
    if (!dati) return []
    const per = filtro === 'Tutti' ? dati.righe : dati.righe.filter((r) => statoDi(r, dati.decisioni.get(r.prospect_id)) === filtro)
    return cerca(per, q)
  }, [dati, filtro, q])

  function scegli(f: string) { setFiltro(f); ricorda('snella-filtro', f); setQuanti(PASSO) }
  // 17/10: 13 lead stavano in stati senza filtro (Nel Workspace, Fuori target, Casella morta):
  // si vedevano solo in «Tutti». Ogni stato che c'e' ha il suo filtro, in fondo.
  const altri = [...conta.keys()].filter((k) => !(STATI as readonly string[]).includes(k)).sort()
  const filtri = ['Tutti', ...STATI, ...altri]

  return (
    <div>
      <div className="relative">
        <label htmlFor="cerca-lead" className="sr-only">Cerca per nome o azienda</label>
        <Icona nome="cerca" className="pointer-events-none absolute left-3.5 top-1/2 h-5 w-5 -translate-y-1/2 text-tenue" />
        <input id="cerca-lead" type="search" value={q} placeholder="Cerca per nome o azienda" autoComplete="off"
               onChange={(e) => { setQ(e.target.value); ricorda('snella-cerca', e.target.value); setQuanti(PASSO) }}
               className="h-12 w-full rounded-full border border-bordo bg-white pl-11 pr-4 text-[16px] text-inchiostro outline-none placeholder:text-spento focus:border-blu-scuro" />
      </div>

      <div role="group" aria-label="Filtra per stato" className="-mx-4 mt-3 flex gap-2 overflow-x-auto px-4 pb-1 lg:mx-0 lg:flex-wrap lg:px-0">
        {filtri.map((s) => {
          const n = !dati ? null : s === 'Tutti' ? dati.righe.length : conta.get(s) ?? 0
          const su = filtro === s
          return (
            <button key={s} onClick={() => scegli(s)} aria-pressed={su}
                    className={`inline-flex min-h-11 shrink-0 items-center gap-1.5 whitespace-nowrap rounded-full border px-3.5 text-[14px] font-semibold transition-colors ${su ? 'border-blu-scuro bg-blu-scuro text-white' : 'border-bordo bg-white text-inchiostro hover:border-tenue'}`}>
              {/* 17/10: il pallino ha il colore della pillola di quello stato, cosi' filtro e lista si riconoscono */}
              {s !== 'Tutti' && tonoStato(s) !== 'neutro' && <span aria-hidden="true" className={`h-2 w-2 rounded-full ${TONO[tonoStato(s)].segno} ${su ? 'ring-2 ring-white' : ''}`} />}
              {s}{n != null && <span className={su ? 'text-white/85' : 'text-tenue'}>{n}</span>}
            </button>
          )
        })}
      </div>

      <div className="mt-4">
        {caricando ? <Carico righe={6} etichetta="Carico i lead" />
          : errore && !dati ? <Errore testo={errore} riprova={() => void rifai()} />
            : !visibili.length ? (
              <Vuoto>
                {q ? `Nessun lead trovato per «${q}»${filtro !== 'Tutti' ? ` in ${filtro}` : ''} fra chi ha risposto negli ultimi 60 giorni.` : `Nessun lead in ${filtro} negli ultimi 60 giorni.`}
                {q && filtro !== 'Tutti' && <> <button onClick={() => scegli('Tutti')} className="font-semibold text-blu-scuro underline">Cerca in tutti</button>.</>}
                {q && filtro === 'Tutti' && <> Gli altri sono nel <a href={linkCompleto('pipeline')} className="font-semibold text-blu-scuro underline">Workspace completo</a>.</>}
              </Vuoto>
            ) : (
              <>
                <p aria-live="polite" className="mb-2 text-[14px] text-tenue">{visibili.length} {visibili.length === 1 ? 'lead' : 'lead'}, l'ultima risposta in cima</p>
                <ul className="divide-y divide-velo overflow-hidden rounded-2xl border border-bordo bg-white">
                  {visibili.slice(0, quanti).map((r) => {
                    const stato = statoDi(r, dati?.decisioni.get(r.prospect_id))
                    return (
                      <li key={r.prospect_id}>
                        <button onClick={() => apri(r.prospect_id)} className="block w-full px-4 py-3 text-left hover:bg-velo">
                          <span className="flex items-baseline justify-between gap-3">
                            <span className="truncate text-[16px] font-bold text-inchiostro">{r.azienda || r.email}</span>
                            <span className="shrink-0 text-[13px] text-tenue">{quando(r.ultima_risposta)}</span>
                          </span>
                          {r.persona && <span className="block truncate text-[14px] text-tenue">{r.persona}</span>}
                          <span className="mt-1 flex items-center gap-2">
                            <PillolaStato stato={stato} />
                            {r.frase && <span className="min-w-0 truncate text-[14px] text-inchiostro">{r.frase}</span>}
                          </span>
                        </button>
                      </li>
                    )
                  })}
                </ul>
                {visibili.length > quanti && (
                  <div className="mt-3 text-center">
                    <Bottone onClick={() => setQuanti(quanti + PASSO)}>Mostra altri {Math.min(PASSO, visibili.length - quanti)}</Bottone>
                  </div>
                )}
              </>
            )}
      </div>
    </div>
  )
}
