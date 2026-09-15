import { useEffect, useState } from 'react'
import { supabase } from '../lib/supabase'
import { sgid, Faccia, type FacciaP } from './ui'

// LA RICERCA DELL'AZIENDA (QA Dre, 14/9). Prima ogni pagina si scaricava il
// suo pezzo di rubrica con un limite diverso (300, 1000, 2000, 3000) e
// cercava li' dentro: dei 4 clienti veri il pannello dei preventivi non ne
// trovava tre, perche' in ordine alfabetico stavano oltre il taglio.
// Adesso la domanda va al database mentre scrivi, su tutte le 13.193.

export const CAMPI_AZIENDA = 'id,company,name,email,sg_id,fuori,stage,pipeline_stage,fatturazione'

export type Azienda = FacciaP & {
  id: string
  email: string
  fatturazione?: Record<string, string> | null
}

export const nomeAzienda = (a: { company?: string | null; name?: string | null; email?: string }) =>
  a.company || a.name || a.email || 'senza nome'

// QUELLO CHE SI LEGGE DENTRO IL NOME DI UN FILE (Dre, 15/9: «come fa
// Google, il software sa gia' quello che vuoi»). «contratto-klavzar-2026.pdf»
// vuol dire Klavzar: si passa alla ricerca come punto di partenza, non come
// decisione presa. Le parole di mestiere si scartano, se no cercherebbe
// «contratto» in tutta la rubrica.
const PAROLE_NOSTRE = /^(bozza|copia|final|finale|nuovo|nuova|firmato|firmata|contratto|preventivo|analisi|report|documento|fattura|proposta|condizioni|economiche|studio|galilei|sg|def|rev|ver|versione|scan|scansione|img|foto|screenshot)$/i
export function indizio(nome: string): string {
  const parole = nome
    .replace(/\.[^.]+$/, '')
    .split(/[^a-zA-ZÀ-ÿ0-9]+/)
    .filter((p) => p.length >= 4 && !/^\d+$/.test(p) && !PAROLE_NOSTRE.test(p))
  return parole[0] ?? ''
}

export default function CercaAzienda<T extends Azienda>({ onScegli, placeholder, piccolo, iniziale = '', sopra = false }: {
  onScegli: (a: T) => void
  placeholder: string
  piccolo?: boolean
  // in fondo alla pagina i suggerimenti si aprono in su, se no coprono
  // il campo dove stai per scrivere
  sopra?: boolean
  // quello che l'app ha gia' capito da sola: il nome dentro il file, la
  // parola che hai appena scritto. Si parte da li' invece che dal vuoto.
  iniziale?: string
}) {
  const [testo, setTesto] = useState(iniziale)
  const [lista, setLista] = useState<T[]>([])
  const [cercando, setCercando] = useState(false)
  const [scelto, setScelto] = useState(false)

  useEffect(() => {
    const s = testo.trim().replace(/[,()"%]/g, ' ').trim()
    if (s.length < 2) { setLista([]); setCercando(false); return }
    setCercando(true)
    const t = setTimeout(async () => {
      const term = `%${s}%`
      const { data } = await supabase.from('prospects').select(CAMPI_AZIENDA)
        .or(`company.ilike.${term},name.ilike.${term},email.ilike.${term}`)
        .order('company').limit(8)
      setLista((data as T[]) ?? [])
      setCercando(false)
    }, 220)
    return () => clearTimeout(t)
  }, [testo])

  return (
    <div className="relative">
      <input autoFocus={!piccolo} value={testo}
             onChange={(e) => { setScelto(false); setTesto(e.target.value) }}
             onKeyDown={(e) => {
               // Invio prende il primo suggerimento: cercare e scegliere
               // senza staccare le mani dalla tastiera
               if (e.key === 'Enter' && lista[0]) { e.preventDefault(); setScelto(true); onScegli(lista[0]); setTesto('') }
             }}
             placeholder={placeholder}
             className={`w-full rounded-xl border border-bordo bg-white outline-none focus:border-blu ${piccolo ? 'px-2 py-1 text-[11px]' : 'px-3 py-2 text-sm'}`} />
      {testo.trim().length >= 2 && !scelto && (
        <div className={`absolute z-20 w-full overflow-hidden rounded-xl border border-bordo bg-white shadow-[0_8px_24px_rgba(16,24,40,0.12)] ${
          sopra ? 'bottom-full mb-1' : 'mt-1'}`}>
          {lista.length === 0
            ? <p className="px-3 py-2 text-xs text-spento">
                {cercando ? 'Cerco…' : 'Nessuna azienda con questo nome: prima entra in Pipeline, poi torna qui'}
              </p>
            : lista.map((a) => (
              <button key={a.id} onClick={() => { setScelto(true); onScegli(a); setTesto('') }} className="flex w-full items-center gap-2.5 px-3 py-2 text-left text-sm hover:bg-velo">
                <Faccia p={a} size={24} />
                <span className="min-w-0 flex-1 truncate">{nomeAzienda(a)}</span>
                {sgid(a.sg_id, a) && <span className="text-[11px] font-semibold text-spento">{sgid(a.sg_id, a)}</span>}
              </button>
            ))}
        </div>
      )}
    </div>
  )
}
