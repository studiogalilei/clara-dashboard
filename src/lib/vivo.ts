import { useEffect, useRef } from 'react'
import type { RealtimeChannel } from '@supabase/supabase-js'
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
// 3. in demo non esiste: li' non c'e' database;
// 4. un canale per tabella, non uno per schermata: Oggi, Clara e il menu
//    ascoltano tutti `proposte`, ma il filo verso il database e' uno solo.
//
// Si chiama useVivo e non vivo perche' dentro usa altri hook: il prefisso
// «use» e' la regola di React, non una scelta di lingua.

interface Filo { canale: RealtimeChannel; orecchie: Set<() => void> }
const fili = new Map<string, Filo>()

function ascolta(tabella: string, orecchio: () => void): () => void {
  let filo = fili.get(tabella)
  if (!filo) {
    const nuovo: Filo = { canale: supabase.channel(`vivo:${tabella}`), orecchie: new Set() }
    nuovo.canale.on('postgres_changes', { event: '*', schema: 'public', table: tabella }, () => {
      for (const o of nuovo.orecchie) o()
    })
    nuovo.canale.subscribe()
    fili.set(tabella, nuovo)
    filo = nuovo
  }
  filo.orecchie.add(orecchio)
  return () => {
    filo.orecchie.delete(orecchio)
    if (filo.orecchie.size === 0) {
      fili.delete(tabella)
      void supabase.removeChannel(filo.canale)
    }
  }
}

export function useVivo(tabelle: string[], quando: () => void, attivo = true) {
  const ultimo = useRef(quando)
  ultimo.current = quando

  useEffect(() => {
    if (demo || !attivo || tabelle.length === 0) return
    let attesa = 0
    const sveglia = () => {
      window.clearTimeout(attesa)
      attesa = window.setTimeout(() => ultimo.current(), 500)
    }
    const stacca = tabelle.map((t) => ascolta(t, sveglia))
    return () => {
      window.clearTimeout(attesa)
      for (const s of stacca) s()
    }
    // le tabelle sono una lista fissa scritta a mano nei componenti
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [tabelle.join(','), attivo])
}
