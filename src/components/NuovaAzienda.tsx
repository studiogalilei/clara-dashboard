import { useState } from 'react'
import { supabase } from '../lib/supabase'
import { Card, TitoloCard } from './ui'
import { giorno } from '../lib/regole'

// AGGIUNGERE UN'AZIENDA A MANO (Dre, 15/9).
//
// Fino a ieri le aziende entravano solo dall'outbound o da Clara: chi ne
// trova una da un'altra parte non la poteva mettere dentro. Lorenzo lavora
// su LinkedIn con piu' profili e la sua pipeline nasce tutta a mano, e
// anche a Dre capita di conoscere qualcuno a un evento.
//
// Chi la mette dentro ci scrive il suo nome: cosi' la rivede (e' la regola
// del perimetro) e si sa di chi e'.

interface Props {
  nome: string                  // chi sta scrivendo: finisce in «chi segue»
  onFatto: (id: string) => void // si apre la scheda appena nata
  onChiudi: () => void
}

const CAMPI: Array<[string, string, string]> = [
  ['company', 'Azienda', 'Come si chiama'],
  ['name', 'Persona', 'Con chi parli'],
  ['email', 'Email', 'nome@azienda.it'],
  ['linkedin', 'LinkedIn', 'Il link al profilo'],
  ['website', 'Sito', 'azienda.it'],
  ['city', 'Città', 'Dove sono'],
  ['sector', 'Settore', 'Cosa fanno'],
  ['campaign', 'Da dove arriva', 'LinkedIn profilo 2, referral, evento…'],
]

export default function NuovaAzienda({ nome, onFatto, onChiudi }: Props) {
  const [v, setV] = useState<Record<string, string>>({})
  const [parlo, setParlo] = useState(true)   // ci sto già parlando, o l'ho solo trovata
  const [salvo, setSalvo] = useState(false)
  const [problema, setProblema] = useState<string | null>(null)

  async function salva() {
    const company = (v.company ?? '').trim()
    const email = (v.email ?? '').trim()
    if (!company && !email) { setProblema('Serve almeno il nome dell\'azienda.'); return }
    setSalvo(true)
    setProblema(null)
    const riga: Record<string, unknown> = {
      company: company || null,
      name: (v.name ?? '').trim() || null,
      email: email || `senza-mail-${Date.now()}@studiogalilei.com`,
      linkedin: (v.linkedin ?? '').trim() || null,
      website: (v.website ?? '').trim() || null,
      city: (v.city ?? '').trim() || null,
      sector: (v.sector ?? '').trim() || null,
      campaign: (v.campaign ?? '').trim() || null,
      chi_segue: nome,
      // «ci sto parlando» = ha risposto, il prossimo passo è l'analisi;
      // «l'ho solo trovata» resta fuori dalla bacheca finché non risponde
      stage: parlo ? 'risposto' : 'nuovo',
      last_reply_at: parlo ? new Date().toISOString() : null,
      first_reply_at: parlo ? new Date().toISOString() : null,
      awaiting_us: false,
      analysis_sent: false,
      fuori: false,
    }
    const { data, error } = await supabase.from('prospects').insert(riga).select('id').single()
    setSalvo(false)
    if (error || !data) {
      setProblema(error?.message.includes('row-level security')
        ? 'Non hai il permesso di aggiungere aziende: chiedilo a Dre.'
        : `Non si è salvata: ${error?.message ?? 'riprova'}`)
      return
    }
    await supabase.from('interactions').insert({
      prospect_id: (data as { id: string }).id, at: new Date().toISOString(), kind: 'nota',
      body: `Aggiunta a mano da ${nome}${riga.campaign ? `, da ${riga.campaign}` : ''}, il ${giorno()}.`,
    })
    onFatto((data as { id: string }).id)
  }

  return (
    <Card className="salta-su space-y-4 border-blu/40 p-5">
      <div className="flex items-baseline justify-between gap-3">
        <TitoloCard>Aggiungi un'azienda</TitoloCard>
        <button onClick={onChiudi} className="text-xs font-semibold text-spento hover:text-inchiostro">Annulla</button>
      </div>

      {problema && (
        <p className="rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-800">{problema}</p>
      )}

      <div className="grid gap-2.5 sm:grid-cols-2 lg:grid-cols-4">
        {CAMPI.map(([k, etichetta, esempio]) => (
          <label key={k} className={k === 'company' ? 'sm:col-span-2' : ''}>
            <span className="text-[10px] font-bold uppercase tracking-wide text-spento">{etichetta}</span>
            <input
              autoFocus={k === 'company'}
              value={v[k] ?? ''}
              onChange={(e) => setV({ ...v, [k]: e.target.value })}
              onKeyDown={(e) => { if (e.key === 'Enter') void salva() }}
              placeholder={esempio}
              className="mt-0.5 w-full rounded-lg border border-bordo bg-white px-2.5 py-1.5 text-sm outline-none focus:border-blu"
            />
          </label>
        ))}
      </div>

      <div className="flex flex-wrap items-center gap-2">
        <div className="flex overflow-hidden rounded-full border border-bordo text-xs font-semibold">
          {[[true, 'Ci sto già parlando'], [false, 'L\'ho solo trovata']].map(([val, testo]) => (
            <button key={String(val)} onClick={() => setParlo(Boolean(val))}
                    className={`px-3.5 py-1.5 ${parlo === val ? 'bg-blu text-white' : 'bg-white text-tenue hover:bg-velo'}`}>
              {testo}
            </button>
          ))}
        </div>
        <span className="text-xs text-spento">La segui tu, {nome.split(' ')[0] || 'tu'}</span>
        <button onClick={() => void salva()} disabled={salvo}
                className="ml-auto rounded-full bg-blu px-5 py-2 text-sm font-bold text-white hover:bg-blu-scuro disabled:opacity-40">
          {salvo ? 'Salvo…' : 'Aggiungi'}
        </button>
      </div>
    </Card>
  )
}
