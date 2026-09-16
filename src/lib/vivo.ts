import { useEffect, useRef } from 'react'
import { supabase, demo } from './supabase'

// IL WORKSPACE VIVO (Dre, 16/9): «tutti gli update li voglio in realtime,
// deve essere proprio vivo, come se arrivassero segnali e li categorizza».
//
// Questo e' il filo: il database avvisa il browser quando una riga cambia, e
// la schermata si ricarica da sola. Non e' un polling piu' veloce, e' il
// contrario del polling: zero richieste finche' non succede niente.
//
// Regole che ci siamo dati:
// 1. l'avviso non porta i dati, dice solo «e' cambiato qualcosa»: a rileggere
//    ci pensa la funzione che gia' c'era, cosi' le regole di accesso valgono
//    sempre e non c'e' un secondo modo di calcolare le stesse cose;
// 2. si aspetta mezzo secondo prima di rileggere, perche' quando Clara
//    finisce un giro cambia venti righe in due secondi e non ha senso
//    rileggere venti volte;
// 3. in demo non esiste: li' non c'e' database.

export function vivo(tabelle: string[], quando: () => void, attivo = true) {
  const ultimo = useRef(quando)
  ultimo.current = quando

  useEffect(() => {
    if (demo || !attivo || tabelle.length === 0) return
    let attesa = 0
    const sveglia = () => {
      window.clearTimeout(attesa)
      attesa = window.setTimeout(() => ultimo.current(), 500)
    }
    const canale = supabase.channel(`vivo:${tabelle.join(',')}:${Math.random().toString(36).slice(2, 8)}`)
    for (const t of tabelle) {
      canale.on('postgres_changes', { event: '*', schema: 'public', table: t }, sveglia)
    }
    canale.subscribe()
    return () => {
      window.clearTimeout(attesa)
      void supabase.removeChannel(canale)
    }
    // le tabelle sono una lista fissa scritta a mano nei componenti
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [tabelle.join(','), attivo])
}
