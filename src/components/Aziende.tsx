import { useEffect, useState } from 'react'
import { leggi as leggiPref, scrivi as scriviPref } from '../lib/preferenze'
import { supabase } from '../lib/supabase'
import Lista from './Lista'
import TuttiFoglio from './TuttiFoglio'
import NuovaAzienda from './NuovaAzienda'
import { nomeSalvato } from '../lib/profilo'

// PIPELINE (Dre, 12/9): chi sta arrivando, dalla risposta alla firma. Una
// lista sola in due forme: la bacheca a colonne (le fasi, si trascina) e il
// foglio. I preventivi e i clienti stanno in Clienti: qui c'e' la vendita.

type Modo = 'bacheca' | 'foglio'
const MODI: Array<[Modo, string]> = [['bacheca', 'Bacheca'], ['foglio', 'Foglio']]

interface Props { onOpen: (id: string) => void; q: string }

export default function Aziende({ onOpen, q }: Props) {
  const [modo, setModo] = useState<Modo>(() => ((leggiPref('tutti-modo') as Modo) === 'foglio' ? 'foglio' : 'bacheca'))
  const [aggiungo, setAggiungo] = useState(false)
  const [nome, setNome] = useState(nomeSalvato())
  // il nome serve per «chi segue»: se non e' nel browser si chiede al database
  useEffect(() => {
    if (nome) return
    void supabase.auth.getSession().then(async ({ data }) => {
      const id = data.session?.user?.id
      if (!id) return
      const { data: p } = await supabase.from('profili').select('nome').eq('id', id).maybeSingle()
      const n = (p as { nome: string | null } | null)?.nome
      if (n) setNome(n)
      else setNome((data.session?.user?.email ?? '').split('@')[0])
    })
  }, [nome])
  function cambia(m: Modo) { setModo(m); scriviPref('tutti-modo', m) }
  // cercando un nome si va sempre nella Bacheca: il Foglio la ricerca non la
  // sa fare e mostrava la tabella intera dicendo che aveva trovato qualcosa
  // (QA Dre, 14/9)
  const vista: Modo = q.trim() ? 'bacheca' : modo
  return (
    <div className="space-y-4">
      <div className="flex items-center gap-6 border-b border-bordo">
        {MODI.map(([m, etichetta]) => (
          <button key={m} onClick={() => cambia(m)}
            className={`-mb-px border-b-2 pb-2.5 text-[15px] font-semibold transition-colors ${
              vista === m ? 'border-navy text-navy' : 'border-transparent text-tenue hover:text-inchiostro'}`}>
            {etichetta}
          </button>
        ))}
        {/* un'azienda che trovi tu (LinkedIn, un evento, un referral) entra
            da qui: prima si poteva solo aspettare che arrivasse dall'outbound */}
        <button onClick={() => setAggiungo((v) => !v)}
                className="ml-auto mb-1.5 rounded-full bg-blu px-3.5 py-1.5 text-xs font-bold text-white hover:bg-blu-scuro">
          + Aggiungi un'azienda
        </button>
      </div>
      {aggiungo && (
        <NuovaAzienda
          nome={nome}
          onChiudi={() => setAggiungo(false)}
          onFatto={(id) => { setAggiungo(false); onOpen(id) }}
        />
      )}
      {vista === 'bacheca' ? <Lista onOpen={onOpen} q={q} /> : <TuttiFoglio onOpen={onOpen} />}
    </div>
  )
}
