import { NOVITA } from '../lib/novita'
import { useEffect, useState } from 'react'
import { supabase } from '../lib/supabase'
import { Card, TitoloCard, Micro } from './ui'
import { chiSono } from '../lib/accessi'

// DIMMI COSA CAMBIERESTI (Dre, 15/9, il giorno degli accessi): «una sezione
// dove loro provano la piattaforma e scrivono cosa cambiare, anche le cose
// minime, tipo bottoni o posizioni, o i desideri».
//
// Sta dentro lo strumento e non su WhatsApp per la stessa ragione di tutto
// il resto: su WhatsApp si perde. Una riga, un clic sulla sezione, invio.
// Niente titolo, niente priorita', niente campi obbligatori: piu' e' facile
// scrivere, piu' roba arriva, e la roba che arriva e' il valore.

interface Riga {
  id: number
  user_id: string
  at: string
  testo: string
  dove: string | null
  genere: string
  stato: string
  risposta: string | null
  voto?: number | null       // le stelle date a una novita'
  novita?: string | null
}

const DOVE = ['Oggi', 'Pipeline', 'Clienti', 'Calendario', 'Documenti', 'Posta di Clara', 'Condividi', 'Preventivi', 'Tutto']
const GENERI: Array<[string, string, string]> = [
  ['guasto', 'Non funziona', 'border-red-200 bg-red-50 text-red-800'],
  ['scomodo', 'Scomodo', 'border-amber-200 bg-amber-50 text-amber-800'],
  ['desiderio', 'Sarebbe bello', 'border-blu/30 bg-blu/5 text-navy'],
  // Dre, 16/9: «chiedi loro cosa vorrebbero che Clara sapesse fare, voglio
  // che si sentano accuditi». Sta qui e non in un altro posto perche' e' lo
  // stesso gesto: dire cosa ti renderebbe la giornata piu' facile
  ['clara', 'Vorrei che Clara…', 'border-navy/30 bg-navy/5 text-navy'],
]

// il campo cambia faccia a seconda di cosa stai per dire
const INVITO: Record<string, string> = {
  guasto: 'Ho cliccato qui e invece di aprirsi…',
  scomodo: 'Per aggiungere una task dal telefono devo scorrere fino in fondo…',
  desiderio: 'Mi piacerebbe poter vedere…',
  clara: 'Vorrei che mi preparasse da sola il report di fine mese…',
}
const NOME_GENERE = Object.fromEntries(GENERI.map(([v, n]) => [v, n]))

const quando = (iso: string) => {
  const d = new Date(iso)
  const g = Math.floor((Date.now() - d.getTime()) / 86400e3)
  if (g === 0) return `oggi, ${d.toLocaleTimeString('it-IT', { hour: '2-digit', minute: '2-digit' })}`
  if (g === 1) return 'ieri'
  return d.toLocaleDateString('it-IT', { day: 'numeric', month: 'short' })
}

// il cruscotto di chi guida lo Studio: quanto e' aperto, cosa dicono le
// stelle sulle novita', cosa ha risposto la squadra alle domande di Clara
function Cantiere({ righe, nomi, diario }: {
  righe: Riga[]
  nomi: Record<string, string>
  diario: Array<{ user_id: string; at: string; domanda: string; testo: string }>
}) {
  const aperti = righe.filter((r) => r.stato !== 'fatto' && r.genere !== 'novita')
  const fatti = righe.filter((r) => r.stato === 'fatto' && r.genere !== 'novita')
  const perGenere = (g: string) => aperti.filter((r) => r.genere === g).length
  const voti = NOVITA.map((n) => {
    const suoi = righe.filter((r) => r.genere === 'novita' && r.novita === n.chiave)
    const stelle = suoi.map((r) => r.voto).filter((v): v is number => typeof v === 'number' && v > 0)
    const media = stelle.length ? stelle.reduce((a, b) => a + b, 0) / stelle.length : null
    const parole = suoi.filter((r) => r.testo && !/^\d stell[ae] a «/.test(r.testo))
    return { ...n, media, quanti: stelle.length, parole }
  })
  return (
    <Card>
      <header className="border-b border-velo px-4 py-3">
        <TitoloCard>Il cantiere</TitoloCard>
        <p className="mt-0.5 text-xs text-tenue">Quello che la squadra chiede, cosa pensa delle novità, e cosa risponde a Clara. Da qui si decide cosa si cambia.</p>
      </header>
      <div className="grid grid-cols-2 divide-x divide-velo border-b border-velo sm:grid-cols-4">
        {([
          ['Aperti', aperti.length], ['Non funziona', perGenere('guasto')],
          ['Per Clara', perGenere('clara')], ['Fatti', fatti.length],
        ] as Array<[string, number]>).map(([n, v]) => (
          <div key={n} className="px-4 py-3">
            <p className="text-[24px] font-extrabold leading-none tabular-nums">{v}</p>
            <p className="mt-1 text-[11px] font-bold uppercase tracking-[0.06em] text-spento">{n}</p>
          </div>
        ))}
      </div>
      <div className="border-b border-velo px-4 py-3">
        <Micro>Le novità, con le stelle</Micro>
        <ul className="mt-1.5 space-y-1.5">
          {voti.map((v) => (
            <li key={v.chiave} className="text-sm">
              <span className="font-semibold text-navy">{v.titolo}</span>
              <span className="ml-2 text-xs text-tenue">
                {v.media === null ? 'nessun voto ancora' : `${v.media.toFixed(1)} su 5, ${v.quanti === 1 ? 'un voto' : `${v.quanti} voti`}`}
                {v.parole.length > 0 ? `, ${v.parole.length === 1 ? 'un commento' : `${v.parole.length} commenti`}` : ''}
              </span>
            </li>
          ))}
        </ul>
      </div>
      <div className="px-4 py-3">
        <Micro>Le domande di Clara, e le risposte</Micro>
        {diario.length === 0 ? (
          <p className="mt-1 text-xs text-tenue">Ancora nessuna risposta al diario.</p>
        ) : (
          <ul className="mt-1.5 space-y-2">
            {diario.map((d, i) => (
              <li key={i} className="text-sm">
                <p className="text-xs text-tenue">{nomi[d.user_id] ? `${nomi[d.user_id]}, ` : ''}{quando(d.at)}: {d.domanda}</p>
                <p className="text-navy">{d.testo}</p>
              </li>
            ))}
          </ul>
        )}
      </div>
    </Card>
  )
}

export default function Feedback() {
  const [testo, setTesto] = useState('')
  const [dove, setDove] = useState<string | null>(null)
  const [genere, setGenere] = useState('scomodo')
  const [righe, setRighe] = useState<Riga[]>([])
  const [mando, setMando] = useState(false)
  const [guaio, setGuaio] = useState('')
  const [grazie, setGrazie] = useState(false)
  const [ceo, setCeo] = useState(false)
  const [nomi, setNomi] = useState<Record<string, string>>({})
  // IL CANTIERE (Dre, 17/9): «serve un sistema anche a me per gestire e
  // migliorare la piattaforma, connesso ai feedback e alle domande che
  // Clara fa ogni tot». Sta qui perche' e' lo stesso posto dove arrivano
  // le cose: quanto e' aperto, cosa dicono le stelle, cosa ha risposto la
  // squadra alle domande del diario
  const [filtro, setFiltro] = useState<'aperti' | 'fatti' | 'tutti'>('aperti')
  const [diario, setDiario] = useState<Array<{ user_id: string; at: string; domanda: string; testo: string }>>([])

  async function carica() {
    const { data } = await supabase.from('feedback').select('*').order('at', { ascending: false }).limit(200)
    setRighe((data as Riga[] | null) ?? [])
  }
  useEffect(() => {
    void carica()
    void chiSono().then((c) => {
      setCeo(c.ruolo === 'ceo')
      if (c.ruolo === 'ceo') {
        void supabase.from('profili').select('id,nome').then(({ data }) => {
          setNomi(Object.fromEntries(((data as Array<{ id: string; nome: string | null }> | null) ?? []).map((p) => [p.id, p.nome ?? ''])))
        })
        void supabase.from('diario').select('user_id,at,domanda,testo').order('at', { ascending: false }).limit(8)
          .then(({ data }) => setDiario((data as typeof diario | null) ?? []))
      }
    })
  }, [])

  async function manda() {
    const t = testo.trim()
    if (!t || mando) return
    setMando(true)
    setGuaio('')
    const { error } = await supabase.from('feedback').insert({ testo: t, dove, genere })
    setMando(false)
    if (error) { setGuaio(`Non è partito: ${error.message}. Quello che hai scritto è ancora qui.`); return }
    setTesto(''); setDove(null); setGenere('scomodo')
    setGrazie(true)
    setTimeout(() => setGrazie(false), 2600)
    await carica()
  }

  async function segna(r: Riga, stato: string) {
    await supabase.from('feedback').update({ stato }).eq('id', r.id)
    await carica()
  }

  return (
    <div className="space-y-4">
      <Card className="p-5">
        <TitoloCard>Cosa cambieresti</TitoloCard>
        <p className="mt-1 text-sm text-tenue">
          Qualunque cosa: un bottone nel posto sbagliato, un giro troppo lungo, una cosa che non funziona,
          o una cosa che vorresti che Clara sapesse fare per te. Anche minima. Si legge tutto, e si cambia.
        </p>

        <textarea
          value={testo}
          onChange={(e) => setTesto(e.target.value)}
          onKeyDown={(e) => { if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) void manda() }}
          placeholder={INVITO[genere] ?? 'Scrivi qui…'}
          className="mt-3 min-h-28 w-full rounded-xl border border-bordo px-3 py-2.5 text-sm outline-none focus:border-blu"
        />

        <div className="mt-2 flex flex-wrap items-center gap-1.5">
          <Micro>Dove</Micro>
          {DOVE.map((d) => (
            <button key={d} onClick={() => setDove(dove === d ? null : d)}
                    className={`rounded-full border px-3 py-1 text-xs font-semibold ${dove === d ? 'border-blu bg-blu text-white' : 'border-bordo bg-white text-navy hover:border-blu'}`}>
              {d}
            </button>
          ))}
        </div>

        <div className="mt-2 flex flex-wrap items-center gap-1.5">
          <Micro>Che cos'è</Micro>
          {GENERI.map(([v, nome, colore]) => (
            <button key={v} onClick={() => setGenere(v)}
                    className={`rounded-full border px-3 py-1 text-xs font-semibold ${genere === v ? colore : 'border-bordo bg-white text-tenue hover:border-spento'}`}>
              {nome}
            </button>
          ))}
        </div>

        {guaio && <p className="mt-2 rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm font-semibold text-red-800">{guaio}</p>}

        <div className="mt-3 flex items-center gap-3">
          <button onClick={() => void manda()} disabled={!testo.trim() || mando}
                  className="rounded-full bg-blu px-5 py-2 text-sm font-bold text-white hover:bg-blu-scuro disabled:cursor-not-allowed disabled:opacity-30">
            {mando ? 'Mando…' : 'Manda'}
          </button>
          {grazie && <span className="text-sm font-semibold text-green-800">Arrivato. Grazie.</span>}
          <span className="ml-auto text-[11px] text-spento">cmd + invio</span>
        </div>
      </Card>

      {ceo && <Cantiere righe={righe} nomi={nomi} diario={diario} />}

      {righe.length > 0 && (
        <Card>
          <header className="flex flex-wrap items-center justify-between gap-2 border-b border-velo px-4 py-3">
            <TitoloCard>{ceo ? 'Quello che è arrivato' : 'Quello che hai mandato'}</TitoloCard>
            {ceo && (
              <div className="flex overflow-hidden rounded-full border border-bordo">
                {([['aperti', 'Aperti'], ['fatti', 'Fatti'], ['tutti', 'Tutti']] as const).map(([v, n]) => (
                  <button key={v} onClick={() => setFiltro(v)}
                          className={`px-3 py-1 text-xs font-bold ${filtro === v ? 'bg-blu text-white' : 'bg-white text-tenue'}`}>{n}</button>
                ))}
              </div>
            )}
          </header>
          <ul>
            {righe.filter((r) => !ceo || filtro === 'tutti' || (filtro === 'fatti' ? r.stato === 'fatto' : r.stato !== 'fatto')).map((r) => (
              <li key={r.id} className="flex flex-wrap items-start gap-x-3 gap-y-1.5 border-t border-velo px-4 py-3 first:border-t-0">
                <div className="min-w-[200px] flex-1">
                  <p className={`text-sm ${r.stato === 'fatto' ? 'text-spento line-through' : ''}`}>{r.testo}</p>
                  <p className="mt-0.5 text-[11px] text-spento">
                    {ceo && nomi[r.user_id] ? `${nomi[r.user_id]}, ` : ''}{quando(r.at)}
                    {r.dove ? `, ${r.dove}` : ''}
                  </p>
                  {r.risposta && <p className="mt-1 text-xs text-navy"><span className="font-bold">Risposta:</span> {r.risposta}</p>}
                </div>
                <span className={`rounded-full border px-2.5 py-0.5 text-[11px] font-semibold ${GENERI.find(([v]) => v === r.genere)?.[2] ?? 'border-bordo text-tenue'}`}>
                  {r.genere === 'novita' ? (r.voto ? `Novità, ${r.voto} su 5` : 'Novità') : (NOME_GENERE[r.genere] ?? r.genere)}
                </span>
                {ceo && (
                  <div className="flex items-center gap-1.5">
                    {r.stato !== 'fatto' ? (
                      <button onClick={() => void segna(r, 'fatto')}
                              className="rounded-full border border-bordo px-3 py-1 text-[11px] font-bold text-navy hover:border-navy">
                        Fatto
                      </button>
                    ) : (
                      <button onClick={() => void segna(r, 'nuovo')}
                              className="rounded-full border border-bordo px-3 py-1 text-[11px] font-bold text-tenue hover:border-spento">
                        Riapri
                      </button>
                    )}
                  </div>
                )}
              </li>
            ))}
          </ul>
        </Card>
      )}
    </div>
  )
}
