// IL WORKSPACE COMPLETO È CHIUSO (4/11, Dre: «elimina tutto, ho già avvisato tutti, ci faremo una
// piattaforma nostra con calma ma per ora pulizia»). Chi non è ceo e chi apre un indirizzo vecchio arriva qui.
import { supabase } from './lib/supabase'

export default function Chiuso() {
  const esci = async () => { await supabase.auth.signOut(); window.location.hash = '' ; window.location.reload() }
  return (
    <main className="mx-auto flex min-h-dvh max-w-md flex-col items-center justify-center px-6 text-center">
      <img src={`${import.meta.env.BASE_URL}brand/SG_logo_blu.png`} alt="" width={40} height={40} className="mb-5 opacity-80" onError={(e) => { (e.currentTarget as HTMLImageElement).style.display = 'none' }} />
      <h1 className="text-[22px] font-bold text-inchiostro">Il Workspace è chiuso</h1>
      <p className="mt-2 text-[15px] leading-relaxed text-tenue">Dal 4 novembre non c'è più. Ci stiamo facendo una piattaforma nostra, con calma. Per tutto il resto: Dramane.</p>
      <button onClick={() => void esci()} className="mt-6 min-h-11 rounded-lg border border-bordo px-5 text-[14px] font-semibold text-inchiostro hover:bg-velo">Esci</button>
    </main>
  )
}
