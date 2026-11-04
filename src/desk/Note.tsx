// LE NOTE DI DRE (4/11: «fai che si vedano un po' di più, sono cose che ho scritto io»): un foglietto giallo,
// l'etichetta «Tua nota» e la data piccola. Uguale nelle call e nel Profilo.
import { quando } from '../snella/regole'

export function Note({ note, className = '' }: { note: Array<{ at: string; testo: string }>; className?: string }) {
  if (note.length === 0) return null
  return (
    <ul className={`space-y-2 ${className}`}>
      {note.map((n, i) => (
        <li key={i} className="rounded-xl border border-giallo-bordo bg-giallo-fondo px-3 py-2.5">
          <p className="mb-0.5 text-[11px] font-extrabold uppercase tracking-[.08em] text-giallo-testo">Tua nota <span className="font-semibold normal-case tracking-normal text-giallo-testo/80">{quando(n.at)}</span></p>
          <p className="text-[14.5px] font-semibold leading-snug text-inchiostro">{n.testo}</p>
        </li>
      ))}
    </ul>
  )
}
