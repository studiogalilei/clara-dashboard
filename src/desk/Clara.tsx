// CLARA: come sta e cosa ha imparato. Numeri veri degli ultimi 7 giorni, senza fronzoli.
import { leggiCoda, leggiOperazioni, type Decisione, type Operazione } from './dati'
import { MOSSE } from './regole'
import { Carico, Errore, Pillola } from '../snella/pezzi'
import { useDati } from '../snella/uso'
import { quando } from '../snella/regole'
import type { Mossa } from './dati'

const NOMI: Record<string, string> = { clara_prova: 'Clara legge e decide', clara_manda: 'Il postino', sync_smartlead: 'Smartlead', analisi: 'Le analisi PDF', webhooks: 'Il campanello' }

export default function Clara() {
  const { dati, errore, caricando, rifai } = useDati(async () => {
    const [d, o] = await Promise.all([leggiCoda(14), leggiOperazioni()])
    return { d, o }
  })
  if (caricando) return <Carico righe={3} etichetta="Carico Clara" />
  if (errore && !dati) return <Errore testo={errore} riprova={() => void rifai()} />
  const sette = new Date(Date.now() - 7 * 864e5).toISOString()
  const d = (dati?.d ?? []).filter((x) => x.creato_il >= sette)
  const n = (f: (x: Decisione) => boolean) => d.filter(f).length
  const perMossa = (Object.keys(MOSSE) as Mossa[]).map((m) => ({ m, q: n((x) => x.mossa === m) })).filter((x) => x.q > 0).sort((a, b) => b.q - a.q)
  const spesa = d.reduce((s, x) => s + (Number(x.dollari) || 0), 0)
  const ok = n((x) => x.dre_giudizio === 'ok'), no = n((x) => x.dre_giudizio === 'no')
  const pericolose = n((x) => Boolean(x.giudice?.pericoloso))
  const versione = dati?.d[0]?.versione
  return (
    <div className="mx-auto max-w-[900px] space-y-4">
      <header>
        <h1 className="text-[22px] font-bold leading-tight text-navy lg:text-[26px]">Clara</h1>
        <p className="mt-1 text-[13.5px] text-tenue">Gli ultimi 7 giorni. Identità {versione ? `v${versione}` : '…'}.</p>
      </header>
      <section className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        <Kpi nome="Decisioni" valore={d.length} sotto={`${n((x) => x.stato === 'inviata')} mail partite`} />
        <Kpi nome="Call e richiami" valore={n((x) => x.mossa === 'book_meeting' || x.mossa === 'callback' || x.mossa === 'offer_slots')} sotto="proposti da Clara" />
        <Kpi nome="Il tuo giudizio" valore={`${ok} ok`} sotto={`${no} no${no + ok ? ` · ${Math.round(ok / (ok + no) * 100)}% d'accordo` : ''}`} />
        <Kpi nome="Segnalate dal revisore" valore={pericolose} sotto={pericolose ? 'da guardare' : 'nessun errore pericoloso'} tono={pericolose ? 'no' : 'ok'} />
      </section>
      <section className="rounded-2xl border border-bordo bg-white p-4 lg:p-5">
        <h2 className="mb-3 text-[12px] font-extrabold uppercase tracking-[.08em] text-tenue">Cosa ha deciso</h2>
        <ul className="space-y-2">
          {perMossa.map((x) => (
            <li key={x.m} className="grid grid-cols-[150px_1fr_36px] items-center gap-3 text-[13.5px]">
              <span className="font-semibold text-inchiostro">{MOSSE[x.m].nome}</span>
              <span className="h-2 overflow-hidden rounded-full bg-velo"><span className="block h-full rounded-full bg-navy" style={{ width: `${Math.round(x.q / d.length * 100)}%` }} /></span>
              <b className="text-right">{x.q}</b>
            </li>
          ))}
          {perMossa.length === 0 && <li className="text-[13.5px] text-tenue">Ancora niente in questi giorni.</li>}
        </ul>
        <p className="mt-3 text-[12.5px] text-tenue">Costo del cervello in questi 7 giorni: {spesa.toFixed(2)} $.</p>
      </section>
      <section className="rounded-2xl border border-bordo bg-white p-4 lg:p-5">
        <h2 className="mb-3 text-[12px] font-extrabold uppercase tracking-[.08em] text-tenue">Il sistema</h2>
        <ul className="space-y-2">
          {(dati?.o ?? []).map((o) => <Riga key={o.chiave} o={o} />)}
        </ul>
      </section>
      <section className="rounded-2xl border border-bordo bg-white p-4 text-[13.5px] leading-relaxed text-inchiostro lg:p-5">
        <h2 className="mb-2 text-[12px] font-extrabold uppercase tracking-[.08em] text-tenue">Come impara</h2>
        <p>Manda da sola: ogni mail la vota prima un giudice indipendente, e la sera la rilegge con quello che è successo dopo. Il resoconto ti arriva nella mail delle 19. Ogni No con una riga di perché, ogni testo che cambi, ogni esito di una call entra nel suo esame e l’identità si corregge dove sbaglia. Niente regole nuove dopo un caso solo.</p>
      </section>
    </div>
  )
}

function Kpi({ nome, valore, sotto, tono }: { nome: string; valore: number | string; sotto: string; tono?: 'ok' | 'no' }) {
  return (
    <div className="rounded-2xl border border-bordo bg-white p-4">
      <p className="text-[12px] font-bold text-tenue">{nome}</p>
      <p className={`mt-1 text-[28px] font-extrabold leading-none tracking-tight ${tono === 'no' ? 'text-no-testo' : 'text-navy'}`}>{valore}</p>
      <p className="mt-1.5 text-[12px] text-tenue">{sotto}</p>
    </div>
  )
}

function Riga({ o }: { o: Operazione }) {
  const ferma = !o.ultima_corsa || Date.now() - new Date(o.ultima_corsa).getTime() > 40 * 60_000
  const tono = !o.attiva ? 'neutro' : o.ultimo_esito === 'errore' ? 'no' : ferma ? 'attesa' : 'ok'
  return (
    <li className="flex items-center justify-between gap-3 rounded-xl border border-bordo px-3.5 py-2.5 text-[13.5px]">
      <span className="font-semibold text-inchiostro">{NOMI[o.chiave] ?? o.nome}</span>
      <span className="flex items-center gap-2 text-tenue">
        {o.ultima_corsa && <span className="hidden sm:inline">{quando(o.ultima_corsa)}</span>}
        <Pillola testo={!o.attiva ? 'spento' : o.ultimo_esito === 'errore' ? 'errore' : ferma ? 'fermo' : 'ok'} tono={tono} />
      </span>
    </li>
  )
}
