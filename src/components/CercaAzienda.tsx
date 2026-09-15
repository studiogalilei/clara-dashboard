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

export default function CercaAzienda<T extends Azienda>({ onScegli, placeholder, piccolo }: {
  onScegli: (a: T) => void
  placeholder: string
  piccolo?: boolean
}) {
  const [testo, setTesto] = useState('')
  const [lista, setLista] = useState<T[]>([])
  const [cercando, setCercando] = useState(false)

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
      <input autoFocus={!piccolo} value={testo} onChange={(e) => setTesto(e.target.value)} placeholder={placeholder}
             className={`w-full rounded-xl border border-bordo bg-white outline-none focus:border-blu ${piccolo ? 'px-2 py-1 text-[11px]' : 'px-3 py-2 text-sm'}`} />
      {testo.trim().length >= 2 && (
        <div className="absolute z-20 mt-1 w-full overflow-hidden rounded-xl border border-bordo bg-white shadow-[0_8px_24px_rgba(16,24,40,0.12)]">
          {lista.length === 0
            ? <p className="px-3 py-2 text-xs text-spento">
                {cercando ? 'Cerco…' : 'Nessuna azienda con questo nome: prima entra in Pipeline, poi torna qui'}
              </p>
            : lista.map((a) => (
              <button key={a.id} onClick={() => { onScegli(a); setTesto('') }} className="flex w-full items-center gap-2.5 px-3 py-2 text-left text-sm hover:bg-velo">
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
