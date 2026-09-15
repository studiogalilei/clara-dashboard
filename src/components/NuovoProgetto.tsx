import { useEffect, useState } from 'react'
import { supabase } from '../lib/supabase'

// IL PEDAGGIO DEL CLIENTE (Dre, 4/9): quando una carta arriva su Cliente si
// chiede una cosa sola, cosa gli abbiamo venduto. E' il passaggio di consegne
// dal commerciale alla delivery, fatto nell'unico istante in cui qualcuno ha
// quelle informazioni in testa. Se non si chiedono li', evaporano.
//
// E il canone (15/9). Sui dati veri tutti e quattro i clienti avevano
// «canone da mettere» da sempre: nessuno lo scriveva, perche' stava in tre
// posti diversi e in nessuno di questi. Ma il software lo sa gia': o c'e'
// un abbonamento su Stripe, o c'e' un preventivo. Quindi lo propone qui,
// dicendo da dove l'ha preso, e basta un clic per confermarlo.

interface Props {
  prospectId: string
  nomeCliente: string
  onFatto: () => void
}

interface Quota { titolo: string | null; importo: number | null; mensile: number | null; stato: string; numero: string | null; voci: Array<{ nome: string }> | null }
interface Incasso { genere: string; importo: number; stato: string | null; ricorrenza: string | null }

export default function NuovoProgetto({ prospectId, nomeCliente, onFatto }: Props) {
  const [nome, setNome] = useState('')
  const [valore, setValore] = useState('')
  const [scadenza, setScadenza] = useState('')
  const [chi, setChi] = useState('')
  const [salvo, setSalvo] = useState(false)
  const [errore, setErrore] = useState('')

  // il contratto: quanto paga al mese e se e' in prova
  const [canone, setCanone] = useState('')
  const [prova, setProva] = useState(false)
  const [daDove, setDaDove] = useState<string | null>(null)
  const [chiSegue, setChiSegue] = useState<string[]>([])

  useEffect(() => {
    void (async () => {
      const [quote, incassi, gente] = await Promise.all([
        supabase.from('preventivi').select('titolo,importo,mensile,stato,numero,voci')
          .eq('prospect_id', prospectId).order('creato_il', { ascending: false }).limit(5),
        supabase.from('incassi').select('genere,importo,stato,ricorrenza').eq('prospect_id', prospectId).limit(20),
        supabase.from('progetti').select('chi_segue').not('chi_segue', 'is', null).limit(100),
      ])
      const q = ((quote.data as Quota[] | null) ?? []).find((x) => x.stato === 'accettato')
        ?? ((quote.data as Quota[] | null) ?? []).find((x) => x.stato === 'inviato')
        ?? ((quote.data as Quota[] | null) ?? [])[0]
      const abb = ((incassi.data as Incasso[] | null) ?? [])
        .find((i) => i.genere === 'abbonamento' && (i.stato === 'active' || i.stato === 'trialing'))

      // Stripe e' quello che incassiamo davvero: vince sul preventivo
      if (abb) {
        setCanone(String(Math.round(abb.ricorrenza === 'year' ? abb.importo / 12 : abb.importo)))
        setProva(abb.stato === 'trialing')
        setDaDove('da Stripe, è quello che incassiamo')
      } else if (q?.mensile) {
        setCanone(String(Math.round(Number(q.mensile))))
        setProva(Boolean(q.voci?.some((v) => /pilota|prova/i.test(v.nome))))
        setDaDove(`dal preventivo ${q.numero ?? ''}`.trim())
      }
      if (q) {
        if (q.titolo) setNome(q.titolo)
        if (q.importo) setValore(String(Math.round(Number(q.importo))))
        if (!abb && q.mensile) setDaDove(`dal preventivo ${q.numero ?? ''}`.trim())
      }
      setChiSegue([...new Set((((gente.data as Array<{ chi_segue: string }> | null) ?? []).map((x) => x.chi_segue)))].slice(0, 8))
    })()
  }, [prospectId])

  async function salva(conProgetto: boolean) {
    if (salvo) return
    const t = nome.trim()
    if (conProgetto && !t) return
    setSalvo(true)
    // il contratto sul cliente: una volta sola, qui
    const soldi = Number(canone.replace(',', '.'))
    if (soldi > 0) {
      await supabase.from('prospects')
        .update({ canone: soldi, contratto: prova ? 'prova' : 'stable' })
        .eq('id', prospectId)
    }
    if (conProgetto) {
      const { data } = await supabase.from('progetti').insert({
        prospect_id: prospectId,
        nome: t,
        valore: valore ? Number(valore.replace(',', '.')) : null,
        scadenza: scadenza || null,
        chi_segue: chi.trim() || null,
        stato: 'da_iniziare',
        tipo: prova ? 'trial' : soldi > 0 ? 'retainer' : null,
      }).select().single()
      setSalvo(false)
      if (!data) { setErrore('Non è stato salvato. Quello che hai scritto è ancora qui: riprova.'); return }
    }
    setSalvo(false)
    onFatto()
  }

  return (
    <div className="fixed inset-0 z-[80] flex items-center justify-center bg-inchiostro/30 px-4">
      <div className="salta-su w-full max-w-lg rounded-2xl bg-white p-6 shadow-xl">
        <p className="text-base font-extrabold">{nomeCliente} è cliente</p>
        <p className="mt-1 text-sm text-tenue">Cosa gli abbiamo venduto?</p>

        <input
          autoFocus
          value={nome}
          onChange={(e) => setNome(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && salva(true)}
          placeholder="Sito vetrina, gestione campagne, setup…"
          className="mt-3 w-full rounded-lg border border-bordo px-3 py-2 text-sm outline-none focus:border-blu"
        />

        <div className="mt-2 flex flex-wrap gap-2">
          <label className="flex flex-1 items-center gap-2 rounded-lg border border-bordo px-3 py-2 text-sm">
            <span className="shrink-0 text-tenue">Vale</span>
            <input
              value={valore}
              onChange={(e) => setValore(e.target.value.replace(/[^0-9.,]/g, ''))}
              placeholder="0"
              className="w-full bg-transparent text-right font-semibold outline-none"
            />
            <span className="shrink-0 text-tenue">€</span>
          </label>
          <label className="flex items-center gap-2 rounded-lg border border-bordo px-3 py-2 text-sm text-tenue">
            Entro
            <input type="date" value={scadenza} onChange={(e) => setScadenza(e.target.value)}
              className="bg-transparent text-inchiostro outline-none" />
          </label>
        </div>

        <input
          value={chi}
          list="chi-segue"
          onChange={(e) => setChi(e.target.value)}
          placeholder="Chi lo segue (Carlo, Alex…)"
          className="mt-2 w-full rounded-lg border border-bordo px-3 py-2 text-sm outline-none focus:border-blu"
        />
        <datalist id="chi-segue">
          {chiSegue.map((x) => <option key={x} value={x} />)}
        </datalist>

        {/* IL CONTRATTO: proposto, non chiesto */}
        <div className="mt-3 rounded-xl border border-bordo bg-velo/50 px-3 py-2.5">
          <div className="flex flex-wrap items-center gap-2">
            <span className="text-sm font-semibold">Quanto paga</span>
            <label className="flex items-center gap-1.5 rounded-lg border border-bordo bg-white px-2.5 py-1 text-sm">
              <input
                value={canone}
                onChange={(e) => { setCanone(e.target.value.replace(/[^0-9.,]/g, '')); setDaDove(null) }}
                placeholder="0"
                className="w-20 bg-transparent text-right font-bold tabular-nums outline-none"
              />
              <span className="text-tenue">€ al mese</span>
            </label>
            <div className="flex overflow-hidden rounded-full border border-bordo text-xs font-semibold">
              {[[false, 'Stabile'], [true, 'In prova']].map(([v, etichetta]) => (
                <button key={String(v)} onClick={() => setProva(Boolean(v))}
                        className={`px-3 py-1 ${prova === v ? 'bg-blu text-white' : 'bg-white text-tenue hover:bg-velo'}`}>
                  {etichetta}
                </button>
              ))}
            </div>
            {daDove && <span className="text-[11px] text-spento">{daDove}</span>}
          </div>
        </div>

        {errore && (
          <p className="mt-2 rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm font-semibold text-red-800">
            {errore}
          </p>
        )}

        <div className="mt-4 flex items-center justify-end gap-2.5">
          <button
            onClick={() => salva(false)}
            className="rounded-full border border-bordo px-4 py-2 text-sm font-semibold text-tenue hover:border-spento"
          >
            Nessun progetto
          </button>
          <button
            onClick={() => salva(true)}
            disabled={!nome.trim() || salvo}
            className="rounded-full bg-blu px-5 py-2 text-sm font-bold text-white hover:bg-blu-scuro disabled:cursor-not-allowed disabled:opacity-30"
          >
            {salvo ? 'Salvo…' : 'Passa alla delivery'}
          </button>
        </div>
      </div>
    </div>
  )
}
