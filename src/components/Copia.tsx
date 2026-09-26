import { useState } from 'react'

// COPIARE (Dre, 26/9: «qualsiasi cosa deve essere collegata a delle possibili
// azioni; il codice preventivo deve essere legato ad azioni di cercarlo,
// trovarlo, connetterlo a un tool»). Il gesto più frequente su un dato è
// portarselo via: in chat, in una mail, in un altro strumento. Un clic sul
// dato lo copia e lo dice, senza spostare niente e senza un bottone in più.

export default function Copia({ testo, children, cosa, className = '' }: {
  testo: string; children: React.ReactNode; cosa?: string; className?: string
}) {
  const [fatto, setFatto] = useState(false)
  return (
    <button
      data-tip={fatto ? 'Copiato' : `Copia ${cosa ?? 'negli appunti'}`}
      onClick={async (e) => {
        e.stopPropagation()
        try { await navigator.clipboard.writeText(testo); setFatto(true); setTimeout(() => setFatto(false), 1400) } catch { /* niente */ }
      }}
      className={`group inline-flex items-center gap-1 rounded-[4px] hover:bg-velo ${className}`}
    >
      {children}
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"
           className={`h-3 w-3 shrink-0 transition-opacity ${fatto ? 'opacity-100 text-green-700' : 'opacity-0 group-hover:opacity-60'}`}>
        {fatto ? <path d="M5 13l4 4L19 7" /> : <><rect x="9" y="9" width="11" height="11" rx="2" /><path d="M5 15V5a2 2 0 0 1 2-2h10" /></>}
      </svg>
    </button>
  )
}
