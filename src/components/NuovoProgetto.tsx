import { useState } from 'react'
import { supabase } from '../lib/supabase'

// IL PEDAGGIO DEL CLIENTE (Dre, 4/9): quando una carta arriva su Cliente si
// chiede una cosa sola, cosa gli abbiamo venduto. E' il passaggio di consegne
// dal commerciale alla delivery, fatto nell'unico istante in cui qualcuno ha
// quelle informazioni in testa. Se non si chiedono li', evaporano.

interface Props {
  prospectId: string
  nomeCliente: string
  onFatto: () => void
}

export default function NuovoProgetto({ prospectId, nomeCliente, onFatto }: Props) {
  const [nome, setNome] = useState('')
  const [valore, setValore] = useState('')
  const [scadenza, setScadenza] = useState('')
  const [chi, setChi] = useState('')
  const [salvo, setSalvo] = useState(false)
  const [errore, setErrore] = useState('')

  async function salva() {
    const t = nome.trim()
    if (!t || salvo) return
    setSalvo(true)
    const { data } = await supabase.from('progetti').insert({
      prospect_id: prospectId,
      nome: t,
      valore: valore ? Number(valore.replace(',', '.')) : null,
      scadenza: scadenza || null,
      chi_segue: chi.trim() || null,
      stato: 'da_iniziare',
    }).select().single()
    setSalvo(false)
    if (!data) { setErrore('Non è stato salvato. Quello che hai scritto è ancora qui: riprova.'); return }
    onFatto()
  }

  return (
    <div className="fixed inset-0 z-[80] flex items-center justify-center bg-inchiostro/30 px-4">
      <div className="salta-su w-full max-w-lg rounded-2xl bg-white p-6 shadow-xl">
        <p className="text-base font-extrabold">🏆 {nomeCliente} è cliente</p>
        <p className="mt-1 text-sm text-tenue">Cosa gli abbiamo venduto?</p>

        <input
          autoFocus
          value={nome}
          onChange={(e) => setNome(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && salva()}
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
          onChange={(e) => setChi(e.target.value)}
          placeholder="Chi lo segue (Carlo, Alex…)"
          className="mt-2 w-full rounded-lg border border-bordo px-3 py-2 text-sm outline-none focus:border-blu"
        />

        {errore && (
          <p className="mt-2 rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm font-semibold text-red-800">
            {errore}
          </p>
        )}

        <div className="mt-4 flex items-center justify-end gap-2.5">
          <button
            onClick={onFatto}
            className="rounded-full border border-bordo px-4 py-2 text-sm font-semibold text-tenue hover:border-spento"
          >
            Nessun progetto
          </button>
          <button
            onClick={salva}
            disabled={!nome.trim() || salvo}
            className="rounded-full bg-navy px-5 py-2 text-sm font-bold text-white hover:bg-navy-scuro disabled:cursor-not-allowed disabled:opacity-30"
          >
            {salvo ? 'Salvo…' : 'Passa alla delivery →'}
          </button>
        </div>
      </div>
    </div>
  )
}
