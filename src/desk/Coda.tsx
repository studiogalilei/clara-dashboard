// LA CODA DI CLARA (4/11 pomeriggio). Dre: «una zona ad elenco dove c'è in ordine quello che Clara sta
// gestendo, per avere sempre in vista le sue attività, cosa sta facendo e cosa farà». Qui si sbircia: un
// tocco apre la relazione. Niente bottoni: quelli stanno in Relazioni.
import { useMemo } from 'react'
import { leggiCoda, type Decisione } from './dati'
import { MOSSE, iniziali } from './regole'
import { Carico, Errore, Icona, Pillola, Vuoto } from '../snella/pezzi'
import { useDati } from '../snella/uso'
import { quando } from '../snella/regole'
import type { Dove } from './Desk'

type Fascia = 'adesso' | 'ferme' | 'prossime' | 'tue' | 'fatte' | 'chiuse'
const FASCE: Record<Fascia, { nome: string; sotto: string }> = {
  adesso: { nome: 'Adesso', sotto: 'In partenza col postino, entro cinque minuti.' },
  ferme: { nome: 'Ferme', sotto: 'Non partono finché non guardi tu.' },
  prossime: { nome: 'Prossime', sotto: 'Aspetta: ripassa alla data segnata o alla prossima risposta.' },
  tue: { nome: 'Passate a te', sotto: 'Call, consigli di chiamata, decisioni tue. Le trovi in Relazioni e in Call.' },
  fatte: { nome: 'Fatte', sotto: 'Mandate e verificate nel thread.' },
  chiuse: { nome: 'Chiuse', sotto: 'Un no, una risposta automatica, una relazione superata.' },
}

function fasciaDi(d: Decisione): Fascia {
  if (d.stato === 'approvata' || d.stato === 'in_invio') return d.errore ? 'ferme' : 'adesso'
  if (d.stato === 'inviata' || d.stato === 'fatta') return 'fatte'
  if (d.stato === 'scartata' || d.stato === 'superata') return 'chiuse'
  if (d.errore) return 'ferme'
  if (d.mossa === 'wait') return 'prossime'
  if (d.mossa === 'close') return 'chiuse'
  if (d.mossa === 'callback' || d.mossa === 'escalate') return 'tue'
  return d.in_mano_a ? 'tue' : 'adesso'
}

/** Il momento che conta per l'ordine: quando e' partita, quando ripassa, quando ha deciso. */
function momento(d: Decisione, f: Fascia): string {
  if (f === 'fatte') return d.inviata_il || d.esito_il || d.creato_il
  if (f === 'prossime') return d.entro_il ? `${d.entro_il}T00:00:00` : d.creato_il
  return d.approvata_il || d.creato_il
}

function cosa(d: Decisione, f: Fascia): string {
  const m = MOSSE[d.mossa]?.nome ?? d.mossa
  if (f === 'fatte') return d.mossa === 'send_analysis' ? 'Ha mandato l’analisi' : d.mossa === 'offer_slots' ? 'Ha proposto due orari' : d.mossa === 'reply' ? 'Ha risposto' : d.esito ? `Fatto: ${d.esito}` : m
  if (f === 'adesso') return d.mossa === 'send_analysis' ? 'Manda l’analisi' : d.mossa === 'offer_slots' ? 'Propone due orari' : d.mossa === 'reply' ? 'Risponde' : m
  if (f === 'prossime') return d.entro_il ? `Ripassa il ${new Date(d.entro_il).toLocaleDateString('it-IT', { day: 'numeric', month: 'short' })}` : 'Aspetta la sua risposta'
  if (f === 'ferme') return `Ferma: ${d.errore}`
  if (f === 'tue') return d.in_mano_a ? 'In mano a te' : d.mossa === 'callback' ? 'Da chiamare' : 'Decidi tu'
  return d.stato === 'superata' ? 'Superata: ha riscritto' : d.stato === 'scartata' ? 'Scartata da te' : 'Chiude'
}

export default function Coda({ vai }: { vai: (d: Dove) => void }) {
  const { dati, errore, caricando, rifai } = useDati(() => leggiCoda(14))
  const fasce = useMemo(() => {
    const out: Record<Fascia, Decisione[]> = { adesso: [], ferme: [], prossime: [], tue: [], fatte: [], chiuse: [] }
    for (const d of dati ?? []) out[fasciaDi(d)].push(d)
    out.adesso.sort((a, b) => momento(b, 'adesso').localeCompare(momento(a, 'adesso')))
    out.prossime.sort((a, b) => momento(a, 'prossime').localeCompare(momento(b, 'prossime')))
    out.fatte.sort((a, b) => momento(b, 'fatte').localeCompare(momento(a, 'fatte')))
    out.tue.sort((a, b) => b.creato_il.localeCompare(a.creato_il))
    out.chiuse.sort((a, b) => b.creato_il.localeCompare(a.creato_il))
    return out
  }, [dati])
  if (caricando) return <Carico righe={4} etichetta="Carico la coda di Clara" />
  if (errore && !dati) return <Errore testo={errore} riprova={() => void rifai()} />
  const oggi = new Date(); oggi.setHours(0, 0, 0, 0)
  const fatteOggi = fasce.fatte.filter((d) => new Date(momento(d, 'fatte')) >= oggi).length
  const ordine: Fascia[] = ['adesso', 'ferme', 'prossime', 'tue', 'fatte', 'chiuse']
  return (
    <div className="mx-auto max-w-[980px] space-y-4">
      <header className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-[22px] font-bold leading-tight text-inchiostro lg:text-[26px]">La coda di Clara</h1>
          <p className="mt-1 text-[13.5px] text-tenue">Cosa sta facendo, cosa ha fatto, cosa farà. Ultimi 14 giorni, un tocco apre la relazione.</p>
        </div>
        <div className="flex gap-2 text-[13px]">
          <span className="rounded-full bg-white px-3 py-1 font-bold text-inchiostro ring-1 ring-bordo">{fasce.adesso.length} in partenza</span>
          <span className="rounded-full bg-white px-3 py-1 font-bold text-inchiostro ring-1 ring-bordo">{fatteOggi} fatte oggi</span>
          <span className="rounded-full bg-white px-3 py-1 font-bold text-inchiostro ring-1 ring-bordo">{fasce.prossime.length} in attesa</span>
        </div>
      </header>
      {ordine.map((f) => {
        const righe = fasce[f]
        if (righe.length === 0 && (f === 'ferme' || f === 'tue')) return null
        const mostra = f === 'chiuse' ? righe.slice(0, 12) : f === 'fatte' ? righe.slice(0, 40) : righe
        return (
          <section key={f} className="rounded-2xl border border-bordo bg-white">
            <header className="flex items-baseline justify-between gap-3 border-b border-bordo px-4 py-3 lg:px-5">
              <h2 className="text-[15px] font-extrabold text-inchiostro">{FASCE[f].nome} <span className="ml-1 text-[13px] font-semibold text-tenue">{righe.length}</span></h2>
              <p className="hidden text-[12.5px] text-tenue sm:block">{FASCE[f].sotto}</p>
            </header>
            {mostra.length === 0 ? <Vuoto>Niente qui adesso.</Vuoto> : (
              <ul className="space-y-2 p-3 lg:p-4">
                {mostra.map((d) => {
                  const m = MOSSE[d.mossa]
                  const t = momento(d, f)
                  return (
                    <li key={d.id}>
                      <button onClick={() => vai({ voce: 'relazioni', id: d.id })}
                              className="grid w-full grid-cols-[40px_minmax(0,1fr)_auto] items-center gap-3 rounded-xl border border-bordo bg-white px-3.5 py-2.5 text-left hover:border-tenue hover:bg-fondo/60">
                        <span className="grid h-9 w-9 place-items-center rounded-lg bg-navy/[0.07] text-[12.5px] font-extrabold text-navy">{iniziali(d.azienda)}</span>
                        <span className="min-w-0">
                          <span className="block truncate text-[14.5px] font-bold text-inchiostro">{d.azienda || d.email}</span>
                          <span className="block truncate text-[12.5px] text-tenue">{cosa(d, f)}{d.perche && f !== 'fatte' ? ` · ${d.perche.replace(/\s+/g, ' ').slice(0, 90)}` : ''}</span>
                        </span>
                        <span className="flex flex-col items-end gap-1">
                          {f === 'fatte' || f === 'adesso' ? <Pillola testo={m?.nome ?? d.mossa} tono={m?.tono ?? 'neutro'} piena={m?.tono === 'ok'} /> : d.consiglio?.numero && !d.consiglio.esito ? <Pillola testo="Ti consiglio di chiamare" tono="giallo" /> : null}
                          <span className="text-[11.5px] text-tenue">{f === 'prossime' && d.entro_il ? new Date(d.entro_il).toLocaleDateString('it-IT', { weekday: 'short', day: 'numeric', month: 'short' }) : quando(t)}</span>
                        </span>
                      </button>
                    </li>
                  )
                })}
                {righe.length > mostra.length && <li className="px-1 text-[12.5px] text-tenue">…e altre {righe.length - mostra.length}: le trovi in Relazioni con il filtro «{f === 'fatte' ? 'Fatte' : 'Chiuse'}».</li>}
              </ul>
            )}
          </section>
        )
      })}
      <p className="flex items-center gap-2 text-[12.5px] text-tenue"><Icona nome="ok" className="h-3.5 w-3.5" /> Qui non si tocca niente: per agire vai in Relazioni.</p>
    </div>
  )
}
