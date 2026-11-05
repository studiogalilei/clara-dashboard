// CLARA: come sta e cosa ha imparato. Numeri veri degli ultimi 7 giorni, senza fronzoli.
import { useState } from 'react'
import { leggiCoda, leggiNonInteressati, leggiOperazioni, leggiSpesa, nonInteressato, type Decisione, type NonInteressato, type Operazione, type Spesa } from './dati'
import { useAvviso } from '../snella/uso'
import { telefonoDa } from './regole'
import { MOSSE } from './regole'
import { Bottone, Carico, Errore, Pillola } from '../snella/pezzi'
import { useDati } from '../snella/uso'
import { quando } from '../snella/regole'
import type { Mossa } from './dati'

const NOMI: Record<string, string> = { clara_prova: 'Clara legge e decide', clara_manda: 'Il postino', sync_smartlead: 'Smartlead', analisi: 'Le analisi PDF', webhooks: 'Il campanello' }

export default function Analytics() {
  const { dati, errore, caricando, rifai } = useDati(async () => {
    const [d, o, s] = await Promise.all([leggiCoda(14), leggiOperazioni(), leggiSpesa().catch((): Spesa | null => null)])
    return { d, o, s }
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
  const s = dati?.s ?? null
  const oggi = new Date(); oggi.setHours(0, 0, 0, 0)
  const deciseOggi = (dati?.d ?? []).filter((x) => new Date(x.creato_il) >= oggi).length
  const mediaGiorno = s && s.giorniConSpesa ? s.sette / s.giorniConSpesa : 0
  return (
    <div className="mx-auto max-w-[900px] space-y-4">
      <header>
        <h1 className="text-[22px] font-bold leading-tight text-inchiostro lg:text-[26px]">Analytics</h1>
        <p className="mt-1 text-[13.5px] text-tenue">Il lavoro di Clara negli ultimi 7 giorni: qui si guarda, non si tocca. Identità {versione ? `v${versione}` : '…'}.</p>
      </header>
      <section className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        <Kpi nome="Decisioni" valore={d.length} sotto={`${n((x) => x.stato === 'inviata')} mail partite`} />
        <Kpi nome="Call e richiami" valore={n((x) => x.mossa === 'book_meeting' || x.mossa === 'callback' || x.mossa === 'offer_slots')} sotto="proposti da Clara" />
        <Kpi nome="Il tuo giudizio" valore={`${ok} ok`} sotto={`${no} no${no + ok ? `, ${Math.round(ok / (ok + no) * 100)}% d'accordo` : ''}`} />
        <Kpi nome="Segnalate dal revisore" valore={pericolose} sotto={pericolose ? 'da guardare' : 'nessun errore pericoloso'} tono={pericolose ? 'no' : 'ok'} />
      </section>
      {s && (
        <section className="rounded-2xl border border-bordo bg-white p-4 lg:p-5">
          <h2 className="mb-3 text-[12px] font-extrabold uppercase tracking-[.08em] text-tenue">La spesa (API Anthropic)</h2>
          <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
            <Kpi nome="Oggi" valore={`${s.oggi.toFixed(2)} $`} sotto={`cervello ${s.oggiCervello.toFixed(2)} $, giudice ${s.oggiGiudice.toFixed(2)} $`} />
            <Kpi nome="Per decisione" valore={deciseOggi ? `${(s.oggi / deciseOggi).toFixed(2)} $` : '…'} sotto={`${deciseOggi} decisioni oggi, ${s.chiamateOggi} chiamate`} />
            <Kpi nome="Media al giorno" valore={`${mediaGiorno.toFixed(2)} $`} sotto={`sugli ultimi ${s.giorniConSpesa} giorni con attività`} />
            <Kpi nome="Stima mese" valore={`${Math.round(mediaGiorno * 30)} $`} sotto="a questo ritmo, 30 giorni" />
          </div>
          <p className="mt-3 text-[12.5px] text-tenue">Ogni chiamata al modello viene registrata con i token: il costo è calcolato dal listino, non stimato. Il cervello è Fable 5.1, il giudice Opus 5.5.</p>
        </section>
      )}
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
      <NonInteressati />
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


/** I «Non interessato» (5/11, Dre): «ritrovabili in un qualche modo, in Analytics in basso; nasconde le campagne,
 *  smettiamo di contattarli». Un bottone, la lista, e «Riapri» se cambia idea. */
function NonInteressati() {
  const [aperto, setAperto] = useState(false)
  const [lista, setLista] = useState<NonInteressato[] | null>(null)
  const [errore, setErrore] = useState<string | null>(null)
  const { mostra, vista } = useAvviso()
  const carica = () => leggiNonInteressati().then(setLista).catch((e) => setErrore(e instanceof Error ? e.message : String(e)))
  const apri = () => { setAperto((v) => !v); if (!lista) void carica() }
  const riapri = (x: NonInteressato) => void nonInteressato(x.id, true).then(() => { setLista((l) => (l ?? []).filter((y) => y.id !== x.id)); mostra({ testo: 'Riaperto: si può ricontattare.' }) }).catch((e) => mostra({ testo: e instanceof Error ? e.message : String(e) }))
  return (
    <section className="rounded-2xl border border-bordo bg-white p-4 lg:p-5">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="text-[12px] font-extrabold uppercase tracking-[.08em] text-tenue">Non interessati</h2>
          <p className="mt-1 text-[13px] text-tenue">Chi hai segnato «Non interessato» al telefono: niente campagne, niente follow-up. Restano qui, se cambiano idea li riapri.</p>
        </div>
        <Bottone onClick={apri} className="text-[13px]">{aperto ? 'Chiudi' : 'Vedi la lista'}{lista ? ` (${lista.length})` : ''}</Bottone>
      </div>
      {aperto && (errore ? <p className="mt-3 text-[13px] text-no-testo">{errore}</p> : !lista ? <p className="mt-3 text-[13px] text-tenue">Carico…</p> : lista.length === 0 ? <p className="mt-3 text-[13px] text-tenue">Nessuno, per ora.</p> : (
        <ul className="mt-3 divide-y divide-velo">
          {lista.map((x) => (
            <li key={x.id} className="flex flex-wrap items-center gap-3 py-2.5">
              <a href={`#/d/filo/${encodeURIComponent(x.id)}`} className="min-w-0 flex-1">
                <span className="block truncate text-[14.5px] font-bold text-inchiostro">{x.azienda || x.email}</span>
                <span className="block truncate text-[12.5px] text-tenue">{[x.persona, x.citta, x.quando].filter(Boolean).join(', ')}</span>
              </a>
              {telefonoDa(x.telefono) && <a href={`tel:${(telefonoDa(x.telefono) ?? '').replace(/[^\d+]/g, '')}`} className="shrink-0 text-[13px] font-semibold text-navy hover:underline">{telefonoDa(x.telefono)}</a>}
              <Bottone tipo="piatto" onClick={() => riapri(x)} className="text-[13px]">Riapri</Bottone>
            </li>
          ))}
        </ul>
      ))}
      {vista}
    </section>
  )
}
