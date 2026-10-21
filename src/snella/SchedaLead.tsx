// LA SCHEDA di un lead nella versione snella (pulita il 20/10, Dre: «fa abbastanza schifo,
// impostala clean con le info anche del sito»). In quest'ordine: chi e' (azienda, persona, stato in
// una riga); come si contatta (telefono, mail, sito, citta', settore, campagna); il prossimo messaggio
// di Clara, col testo esatto e «Ferma»; la conversazione con l'analisi; stato e prossima azione; note.
// 20/10 sera (Dre: «lo vedevo, ma non potevo agire»): un messaggio fermo che aspetta lui si decide qui,
// «Manda» o «Non mandare», e il lead si chiude con «Chiudi: non interessato». Ogni gesto lascia una nota.
// 22/10 notte (Dre: «vorrei poterle MODIFICARE», «due-tre alternative tipo ChatGPT», «i messaggi a ritroso, la
// bozza pronta in alto, come su Smartlead»): sotto il titolo la bozza da decidere, modificabile, con le altre
// versioni da scegliere; poi il prossimo messaggio; poi la conversazione dal piu' recente; poi i contatti.
import { useEffect, useLayoutEffect, useRef, useState } from 'react'
import {
  GRUPPI, INFO_STATI, RESPONSABILI, aggiungiNota, chiudiLead, fermaMessaggi, ioSono, leggiScheda, linkAnalisi, mandaDallApp, nonMandareDallApp,
  salvaDecisione, scegliStrada, togliNota,
  type Call, type Decisione, type Lead, type Messaggio, type Nota, type Scheda, type Telefono,
} from './dati'
import {
  NOTE_APP, allegaAnalisi, azioneApprovata, confermaStrada, conTestoDiDre, dettaglioStrada, filoAlContrario, giornoRoma, infoStato, mailEGesti,
  messaggioInAttesa, nomeGiorno, nomeStato, ora, prossimoMessaggio, quando, scritturaNonMandare, scrittureChiusura, scrittureStrada, sitoBreve,
  sitoCliccabile, stradeDi, statoDi,
  type ConStrade, type InAttesa, type Strada,
} from './regole'
import { Bottone, Carico, Errore, Icona, PillolaStato, type NomeIcona } from './pezzi'
import { linkCompleto, useAvviso, useDati } from './uso'

export default function SchedaLead({ id, indietro }: { id: string; indietro: () => void }) {
  const { dati, setDati, errore, caricando, rifai } = useDati(() => leggiScheda(id), [id])
  const { mostra, vista: avviso } = useAvviso()

  useEffect(() => { window.scrollTo(0, 0) }, [id])

  if (caricando) return <><Torna indietro={indietro} /><Carico righe={5} etichetta="Carico la scheda" /></>
  if (errore && !dati) return <><Torna indietro={indietro} /><Errore testo={errore} riprova={() => void rifai()} /></>
  if (!dati) return null
  const sc = dati.scheda
  const b = dati.base
  if (!sc && !b) {
    return <><Torna indietro={indietro} /><Errore testo="Questo lead non c'è più nel Workspace." /></>
  }
  const lead = dati.lead
  const d = dati.decisione
  const s = sc?.scheda
  // la scheda piena (chi ha risposto negli ultimi 60 giorni, scripts/schede.py) o la riga di «Tutti»
  const stato = sc ? statoDi(sc, d) : (d?.stato || b!.stato_sistema)
  const sistema = sc ? (nomeStato(sc.stato) ?? 'Da rispondere') : b!.stato_sistema
  const suggerita = sc
    ? (nomeStato(sc.stato) === sc.stato ? s!.prossima : { mossa: null, il: null })
    : (b!.mossa_tua ? { mossa: null, il: null } : { mossa: b!.mossa, il: b!.mossa_il })
  const azienda = s?.azienda || sc?.azienda || b?.azienda || b?.email || 'Senza nome'
  const persona = [s?.nome || sc?.persona || b?.persona, s?.ruolo].filter(Boolean).join(', ')
  const ultima = sc ? sc.ultima_risposta : b!.ultima_risposta
  const unico = b?.telefono || lead?.phone || ''
  const telefoni: Telefono[] = s?.telefoni.length ? s.telefoni
    : unico ? [{ numero: unico, tel: unico.replace(/[^\d+]/g, ''), etichetta: '' }] : []
  // l'analisi della scheda; se la scheda non la sa, quella della riga del lead
  const analisi: Scheda['scheda']['analisi'] = s?.analisi.mandata ? s.analisi : {
    mandata: Boolean(lead?.analysis_sent_at), il: lead?.analysis_sent_at ?? null, link: lead?.analysis_pdf ?? '', percorso: '', punto: s?.analisi.punto ?? '',
  }
  const chiuso = ['Opportunità', 'Chiusi'].includes(infoStato(stato)?.gruppo ?? '')
  const filo = sc?.filo ?? []
  const prossimo = prossimoMessaggio(lead ?? VUOTO, dati.proposte, dati.calendario,
    filo.filter((m) => m.chi === 'noi' && m.at).map((m) => m.at!))
  // 20/10 sera, Dre: «lo vedevo, ma non potevo agire». Un messaggio fermo che aspetta lui si decide qui:
  // Manda o Non mandare. Se e' lo stesso del «prossimo messaggio», si mostra una volta sola.
  // 21/10 (Dre: «mi dà 2 o 3 strade e io scelgo, e lui procede»): se il sistema ha scritto le strade, le mail sono
  // le versioni da scegliere e gli altri gesti stanno sotto; senza strade, la bozza ferma da sola (22/10: tutte modificabili).
  const strade = stradeDi(dati.proposte)
  const attesa = strade ? null : messaggioInAttesa(dati.proposte)
  const mostraProssimo = prossimo?.proposta == null || (prossimo.proposta !== attesa?.id && prossimo.proposta !== strade?.id)
  const daChiudere = dati.proposte.filter((p) => (p.stato === 'aperta' || p.stato === 'approvata') && (p.tipo === 'risposta' || p.tipo === 'umano')).map((p) => p.id)
  const conNota = (x: NonNullable<typeof dati>, n: Nota | null) => n ? { ...x, note: [n, ...x.note] } : x

  return (
    <article aria-labelledby="titolo-scheda">
      <Torna indietro={indietro} />
      <header>
        <h1 id="titolo-scheda" className="text-[26px] font-bold leading-tight tracking-[-0.01em] text-inchiostro">{azienda}</h1>
        <div className="mt-2 flex flex-wrap items-center gap-x-2 gap-y-1.5 text-[15px] text-tenue">
          <PillolaStato stato={stato} />
          {persona && <span className="text-inchiostro">{persona}</span>}
        </div>
        <p className="mt-1 text-[14px] text-tenue">{ultima ? `Ha scritto ${quando(ultima)}` : 'Non ha mai risposto'}</p>
        {/* 21/10: lo «Stato» della Conversazione del foglio, sola lettura (si cambia nel foglio, non qui) */}
        {d?.stato_conv && <p className="mt-1 text-[14px] text-tenue">Nel foglio: <span className="font-semibold text-inchiostro">{d.stato_conv}</span></p>}
        {/* 22/10 notte: con una bozza da decidere l'attivita' sta in due righe, cosi' la bozza sale */}
        {s?.attivita && <p className={`mt-3 max-w-[65ch] text-[15px] leading-relaxed text-tenue ${strade || attesa ? 'line-clamp-2' : ''}`}>{s.attivita}</p>}
        <ProssimaCall call={dati.call} />
        {/* 22/10 notte: i contatti sono scesi sotto la conversazione; il numero resta a un tocco */}
        {telefoni[0] && (
          <a href={`tel:${telefoni[0].tel}`} aria-label={`Chiama ${telefoni[0].numero}`}
             className="mt-3 inline-flex min-h-11 items-center gap-2 rounded-full border border-bordo bg-white px-4 text-[15px] font-semibold text-blu-scuro transition-colors duration-150 hover:bg-velo">
            <Icona nome="telefono" className="h-4 w-4" /> <span className="tabular-nums">{telefoni[0].numero}</span>
          </a>
        )}
      </header>

      {(strade || attesa) && (
        <Blocco titolo="Da decidere">
          <DaDecidere key={strade?.id ?? attesa?.id} id={id} con={strade} attesa={attesa} lead={lead ?? VUOTO}
            onScelta={(scelta, r, testo) => {
              const s = scrittureStrada(strade!, scelta, {}, lead ?? VUOTO, new Date(), testo)
              const az = s.proposta.azione as Record<string, unknown> | undefined
              setDati((x) => x ? conNota({
                ...x,
                proposte: x.proposte.map((p) => p.id === strade!.id ? { ...p, stato: String(s.proposta.stato), risposta: (s.proposta.risposta as string | undefined) ?? p.risposta,
                  bozza: (az?.bozza as string | undefined) ?? p.bozza } : p),
                lead: x.lead && s.lead ? { ...x.lead, ...(s.lead as Partial<Lead>) } : x.lead,
                decisione: r.decisione ?? x.decisione,
                calendario: s.togliCalendario ? null : x.calendario,
              }, r.nota) : x)
              mostra({ testo: !scelta ? 'Chiuso senza fare nulla' : scelta.azione === 'manda' ? 'Parte al prossimo giro' : scelta.azione === 'ricontatta' ? 'Segnato: da ricontattare'
                : scelta.azione === 'chiudi' ? 'Chiuso: non interessato' : scelta.azione === 'chiama' ? 'Da chiamare oggi' : 'Chiuso, nessun gesto' })
            }}
            onMandato={(n, testo) => {
              setDati((x) => x ? conNota({ ...x, proposte: x.proposte.map((p) => p.id === attesa!.id ? { ...p, stato: 'approvata', bozza: testo } : p) }, n) : x)
              mostra({ testo: 'Parte al prossimo giro' })
            }}
            onNonMandato={(n) => {
              setDati((x) => x ? conNota({ ...x, proposte: x.proposte.map((p) => p.id === attesa!.id ? { ...p, stato: 'no', risposta: "NO: Dre dall'app" } : p) }, n) : x)
              mostra({ testo: 'Non parte' })
            }} />
        </Blocco>
      )}

      {mostraProssimo && (
        <Blocco titolo="Il prossimo messaggio di Clara">
          <ProssimoMessaggio id={id} prossimo={prossimo} fermato={Boolean(lead?.no_followup)} chiuso={chiuso} onFermato={(partite) => {
            setDati((x) => x ? {
              ...x, calendario: null, lead: x.lead ? { ...x.lead, no_followup: true, coda: null } : x.lead,
              proposte: x.proposte.map((p) => prossimo?.da_chiudere.includes(p.id) && (p.stato === 'aperta' || p.stato === 'approvata')
                ? { ...p, stato: 'no', risposta: 'NO: fermato da Dre' } : p),
            } : x)
            mostra({ testo: partite ? 'Fermato. Una mail era già partita.' : 'Fermato' })
          }} />
        </Blocco>
      )}

      <Blocco titolo="La conversazione, dalla più recente">
        {sc ? <Filo filo={filo} analisi={analisi} lui={(s?.nome || sc.persona || '').trim().split(/\s+/)[0] || ''} />
          : <>
              <Analisi a={analisi} />
              <p className="mt-3 text-[15px] text-tenue">Le mail arrivano qui entro dieci minuti da quando salvi uno stato o una nota.</p>
            </>}
      </Blocco>

      <Blocco titolo="Contatti">
        <Contatti telefoni={telefoni} email={s?.email || b?.email || lead?.email || ''} lead={lead}
                  campagna={s?.campagna || b?.campagna || lead?.campaign || ''} />
      </Blocco>

      <Blocco titolo="Stato e prossima azione">
        {/* 21/10: dopo un gesto che cambia lo stato (una strada, Chiudi) il modulo si rifa' con i valori nuovi */}
        <Decidi key={d?.aggiornato_il ?? 'nuova'} id={id} sistema={sistema} suggerita={suggerita} decisione={d} onSalvato={(nuova) => {
          setDati((x) => x ? { ...x, decisione: nuova } : x)
          mostra({ testo: 'Salvato' })
        }} />
        {!chiuso && (
          <ChiudiLead id={id} proposte={daChiudere} onChiuso={(nuova, n) => {
            setDati((x) => x ? conNota({
              ...x, decisione: nuova, calendario: null,
              lead: x.lead ? { ...x.lead, no_followup: true, classificazione: 'negativo', coda: null } : x.lead,
              proposte: x.proposte.map((p) => daChiudere.includes(p.id) ? { ...p, stato: 'no', risposta: "NO: Dre dall'app, lead chiuso" } : p),
            }, n) : x)
            mostra({ testo: 'Chiuso: non interessato' })
          }} />
        )}
      </Blocco>

      <Blocco titolo="Note">
        <Note id={id} note={dati.note} mostra={mostra}
              onNota={(n) => setDati((x) => x ? { ...x, note: [n, ...x.note] } : x)}
              onTolta={(nid) => setDati((x) => x ? { ...x, note: x.note.filter((n) => n.id !== nid) } : x)} />
      </Blocco>

      <p className="mt-10 border-t border-velo pt-3 text-[14px]">
        <a href={linkCompleto(`azienda/${id}`)} className="inline-flex min-h-11 items-center gap-1.5 font-semibold text-blu-scuro hover:underline">
          Apri nel Workspace completo <Icona nome="esterno" className="h-4 w-4" />
        </a>
      </p>
      {avviso}
    </article>
  )
}

const VUOTO: Lead = {
  website: null, city: null, sector: null, campaign: null, phone: null, email: null, analysis_pdf: null, analysis_sent_at: null,
  last_reply_at: null, no_followup: null, fuori: null, stage: null, classificazione: null, coda: null, awaiting_us: null,
}

/** «esperienze_turistiche» → «Esperienze turistiche» */
function settore(s: string | null | undefined): string {
  const t = (s ?? '').replace(/_/g, ' ').trim()
  return t ? t.charAt(0).toUpperCase() + t.slice(1) : ''
}

/** Come si contatta e chi e': una riga per cosa, come la rubrica del telefono. Quello che manca non c'e'. */
function Contatti({ telefoni, email, lead, campagna }: { telefoni: Telefono[]; email: string; lead: Lead | null; campagna: string }) {
  const sito = sitoCliccabile(lead?.website)
  const righe: Array<{ icona: NomeIcona; testo: string; sotto?: string; href?: string; fuori?: boolean; etichetta?: string }> = [
    ...telefoni.map((t) => ({ icona: 'telefono' as const, testo: t.numero, sotto: t.etichetta, href: `tel:${t.tel}`, etichetta: `Chiama ${t.numero}` })),
    ...(email ? [{ icona: 'mail' as const, testo: email, href: `mailto:${email}`, etichetta: `Scrivi a ${email}` }] : []),
    ...(sito ? [{ icona: 'sito' as const, testo: sitoBreve(sito), href: sito, fuori: true, etichetta: `Apri il sito ${sitoBreve(sito)}` }] : []),
    ...(lead?.city ? [{ icona: 'luogo' as const, testo: lead.city }] : []),
    ...(settore(lead?.sector) ? [{ icona: 'settore' as const, testo: settore(lead?.sector) }] : []),
    ...(campagna ? [{ icona: 'campagna' as const, testo: campagna, sotto: 'campagna' }] : []),
  ]
  if (!righe.length) return <p className="text-[15px] text-tenue">Nessun contatto oltre la mail.</p>
  return (
    <section aria-label="Contatti" className="rounded-2xl border border-bordo bg-white px-2 py-1">
      <ul className="grid sm:grid-cols-2 sm:gap-x-2">
        {righe.map((r) => {
          const dentro = (
            <>
              <Icona nome={r.icona} className={`h-5 w-5 shrink-0 ${r.href ? 'text-blu-scuro' : 'text-tenue'}`} />
              <span className="min-w-0">
                <span className={`block truncate text-[15px] ${r.href ? 'font-semibold text-blu-scuro' : 'text-inchiostro'} ${r.icona === 'telefono' ? 'tabular-nums tracking-wide' : ''}`}>{r.testo}</span>
                {r.sotto && <span className="block truncate text-[13px] text-tenue">{r.sotto}</span>}
              </span>
              {r.fuori && <Icona nome="esterno" className="ml-auto h-4 w-4 shrink-0 text-tenue" />}
            </>
          )
          const stile = 'flex min-h-12 items-center gap-3 rounded-xl px-3 py-2'
          return (
            <li key={`${r.icona}-${r.testo}`} className="min-w-0">
              {r.href ? (
                <a href={r.href} aria-label={r.etichetta} {...(r.fuori ? { target: '_blank', rel: 'noreferrer' } : {})}
                   className={`${stile} transition-colors duration-150 hover:bg-velo focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blu-scuro`}>
                  {dentro}
                </a>
              ) : <div className={stile}>{dentro}</div>}
            </li>
          )
        })}
      </ul>
    </section>
  )
}

const RIGHE_MESSAGGIO = 8

/** Il prossimo messaggio che Clara gli mandera': quando, il testo esatto (se e' gia' scritto) e
 *  «Ferma», che chiede conferma prima di fermare questo e i messaggi automatici dopo. */
function ProssimoMessaggio({ id, prossimo, fermato, chiuso, onFermato }: {
  id: string; prossimo: ReturnType<typeof prossimoMessaggio>; fermato: boolean; chiuso: boolean; onFermato: (partite: number) => void
}) {
  const [chiedo, setChiedo] = useState(false)
  const [lavoro, setLavoro] = useState(false)
  const [sbaglio, setSbaglio] = useState<string | null>(null)

  if (!prossimo) {
    return (
      <p className="text-[15px] text-tenue">
        {chiuso ? 'Nessun messaggio automatico.'
          : fermato ? 'Fermato: Clara non gli scrive finché non risponde lui.' : 'Nessun messaggio in programma.'}
      </p>
    )
  }

  async function ferma() {
    setLavoro(true); setSbaglio(null)
    try {
      const { partite } = await fermaMessaggi(id, prossimo!.da_chiudere)
      setChiedo(false)
      onFermato(partite)
    } catch (e) {
      setSbaglio(`Non fermato: ${e instanceof Error ? e.message : e}`)
    } finally {
      setLavoro(false)
    }
  }

  return (
    <div className="overflow-hidden rounded-2xl border border-noi-bordo bg-white">
      <p className="border-b border-noi-bordo px-4 py-3 text-[16px] font-bold text-inchiostro">
        {prossimo.quando}
        <span className="block text-[14px] font-normal text-tenue">{prossimo.tipo}</span>
      </p>
      <div className="px-4 py-3">
        {prossimo.testo ? <TestoMessaggio testo={prossimo.testo} />
          : <p className="text-[15px] text-tenue">Clara lo scrive quel giorno, dopo aver riletto la conversazione.</p>}
      </div>
      {!chiedo && (
        <div className="border-t border-velo px-2 py-1">
          <button onClick={() => setChiedo(true)}
                  className="inline-flex min-h-11 items-center gap-1.5 rounded-full px-3 text-[14px] font-semibold text-no-testo transition-colors duration-150 hover:bg-no-fondo focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-no-testo">
            <Icona nome="divieto" className="h-4 w-4" /> Ferma
          </button>
        </div>
      )}
      {chiedo && (
        <div role="alertdialog" aria-labelledby={`ferma-${id}`} className="border-t border-no-bordo bg-no-fondo px-4 py-3">
          <p id={`ferma-${id}`} className="text-[15px] font-semibold text-no-testo">Fermarlo? Clara non gli scrive più finché non risponde lui.</p>
          <div className="mt-2 flex flex-wrap gap-2">
            <button onClick={() => void ferma()} disabled={lavoro} autoFocus
                    className="inline-flex min-h-11 items-center rounded-full border border-no-testo bg-no-testo px-4 text-[14px] font-semibold text-white transition-opacity duration-150 hover:opacity-90 disabled:opacity-50">
              {lavoro ? 'Fermo…' : 'Sì, ferma'}
            </button>
            <Bottone onClick={() => setChiedo(false)} disabled={lavoro}>Annulla</Bottone>
          </div>
        </div>
      )}
      {sbaglio && <p role="alert" className="px-4 pb-3 text-[14px] font-semibold text-no-testo">{sbaglio}</p>}
    </div>
  )
}

/** Il testo di una mail di Clara: le prime righe, il resto a richiesta. */
function TestoMessaggio({ testo, righe: quante = RIGHE_MESSAGGIO }: { testo: string; righe?: number }) {
  const [intero, setIntero] = useState(false)
  const righe = testo.split('\n')
  const lungo = righe.length > quante + 2
  const mostrato = lungo && !intero ? righe.slice(0, quante).join('\n').trimEnd() + '…' : testo
  return (
    <>
      <p className="whitespace-pre-wrap break-words text-[15px] leading-relaxed text-inchiostro">{mostrato}</p>
      {lungo && (
        <button onClick={() => setIntero(!intero)} aria-expanded={intero}
                className="mt-1 inline-flex min-h-11 items-center text-[14px] font-semibold text-blu-scuro hover:underline">
          {intero ? 'Mostra meno' : 'Mostra tutto'}
        </button>
      )}
    </>
  )
}

/** La domanda prima di un gesto che non si annulla: una riga e due pulsanti, dentro la carta. */
function Conferma({ id, testo, si, lavoro, lavoroTesto, tono, onSi, onNo }: {
  id: string; testo: string; si: string; lavoro: boolean; lavoroTesto: string; tono: 'noi' | 'no'; onSi: () => void; onNo: () => void
}) {
  const rosso = tono === 'no'
  return (
    <div role="alertdialog" aria-labelledby={id} className={`border-t px-4 py-3 ${rosso ? 'border-no-bordo bg-no-fondo' : 'border-noi-bordo bg-noi-fondo'}`}>
      <p id={id} className={`text-[15px] font-semibold ${rosso ? 'text-no-testo' : 'text-noi-testo'}`}>{testo}</p>
      <div className="mt-2 flex flex-wrap gap-2">
        <button onClick={onSi} disabled={lavoro} autoFocus
                className={`inline-flex min-h-11 items-center rounded-full border px-4 text-[14px] font-semibold text-white transition-opacity duration-150 hover:opacity-90 disabled:opacity-50 ${rosso ? 'border-no-testo bg-no-testo' : 'border-blu-scuro bg-blu-scuro'}`}>
          {lavoro ? lavoroTesto : si}
        </button>
        <Bottone onClick={onNo} disabled={lavoro}>Annulla</Bottone>
      </div>
    </div>
  )
}

/** Il campo della bozza (22/10 notte, Dre: «vorrei poterle MODIFICARE»): un testo vero, che cresce con quello che
 *  c'e' scritto, a 16px (sotto, l'iPhone ingrandisce la pagina quando lo tocchi). */
function CampoBozza({ id, valore, onCambia, disabled }: { id: string; valore: string; onCambia: (t: string) => void; disabled?: boolean }) {
  const ref = useRef<HTMLTextAreaElement>(null)
  useLayoutEffect(() => {
    const t = ref.current
    if (!t) return
    t.style.height = 'auto'
    t.style.height = `${t.scrollHeight + 2}px`
  }, [valore])
  return (
    <textarea ref={ref} id={id} value={valore} onChange={(e) => onCambia(e.target.value)} rows={5} disabled={disabled} spellCheck
              className="block w-full resize-none overflow-hidden rounded-xl border border-bordo bg-white px-3 py-2.5 text-[16px] leading-relaxed text-inchiostro outline-none transition-colors duration-150 focus:border-blu-scuro disabled:opacity-60" />
  )
}

type Gesto = number | 'nessuna' | 'no'

/** DA DECIDERE (22/10 notte; prima «Messaggio in attesa» e «Decidi tu»). In alto la bozza pronta, gia' aperta e
 *  modificabile: «Manda» manda il testo cosi' com'e' nel campo. Se le strade hanno piu' mail, le altre versioni
 *  stanno sotto con «Usa questa» (come le due risposte di ChatGPT). Sotto ancora, piccoli, i gesti senza mail
 *  (rimanda, chiudi, chiama, niente) e «Nessuna di queste» o «Non mandare». Ogni gesto chiede conferma e lascia
 *  una nota; la scelta resta sulla proposta (azione.scelta), ed e' da li' che il sistema impara. */
function DaDecidere({ id, con, attesa, lead, onScelta, onMandato, onNonMandato }: {
  id: string; con: ConStrade | null; attesa: InAttesa | null; lead: Lead
  onScelta: (scelta: Strada | null, r: { decisione: Decisione | null; nota: Nota | null }, testo?: string) => void
  onMandato: (nota: Nota | null, testo: string) => void; onNonMandato: (nota: Nota | null) => void
}) {
  const { mail: stradeMail, gesti } = con ? mailEGesti(con) : { mail: [] as Strada[], gesti: [] as Strada[] }
  const mail: Array<{ strada: Strada | null; testo: string }> = con
    ? stradeMail.map((st) => ({ strada: st, testo: (st.bozza ?? '').trim() }))
    : attesa ? [{ strada: null, testo: attesa.testo }] : []
  const [aperta, setAperta] = useState(0)
  const [testi, setTesti] = useState<string[]>(() => mail.map((m) => m.testo))
  const [chiedo, setChiedo] = useState<'manda' | Gesto | null>(null)
  const [lavoro, setLavoro] = useState(false)
  const [sbaglio, setSbaglio] = useState<string | null>(null)
  const carta = useRef<HTMLDivElement>(null)
  const scelta = mail[aperta]
  const testo = testi[aperta] ?? ''
  const cambiato = scelta ? testo.trim() !== scelta.testo.trim() : false
  const allega = scelta ? allegaAnalisi({ bozza: testo }, lead) : false
  const motivo = con?.motivo ?? attesa?.motivo ?? ''

  async function fai(cosa: 'manda' | Gesto) {
    setLavoro(true); setSbaglio(null)
    try {
      if (cosa === 'manda' && scelta?.strada && con) {
        const st = scelta.strada
        const r = await scegliStrada(id, con.id, (azione) => scrittureStrada(con, st, azione, lead, new Date(), testo))
        setChiedo(null); onScelta(st, r, testo)
      } else if (cosa === 'manda' && attesa) {
        const r = await mandaDallApp(id, attesa.id, (az) => azioneApprovata(conTestoDiDre(az, testo, attesa.testo), lead),
          cambiato ? NOTE_APP.mandato_cambiato : NOTE_APP.mandato)
        setChiedo(null); onMandato(r.nota, testo.trim())
      } else if (cosa === 'no' && attesa) {
        const r = await nonMandareDallApp(id, attesa.id, scritturaNonMandare(), NOTE_APP.non_mandato)
        setChiedo(null); onNonMandato(r.nota)
      } else if (con && (cosa === 'nessuna' || typeof cosa === 'number')) {
        const g = cosa === 'nessuna' ? null : gesti[cosa]
        const r = await scegliStrada(id, con.id, (azione) => scrittureStrada(con, g, azione, lead))
        setChiedo(null); onScelta(g, r)
      }
    } catch (e) {
      setSbaglio(`Non fatto: ${e instanceof Error ? e.message : e}`)
    } finally {
      setLavoro(false)
    }
  }

  function usa(i: number) {
    setAperta(i); setChiedo(null); setSbaglio(null)
    carta.current?.scrollIntoView({ behavior: 'smooth', block: 'start' })
  }

  const piccolo = 'inline-flex min-h-11 items-center gap-1.5 rounded-full border bg-white px-3.5 text-[14px] font-semibold transition-colors duration-150 hover:bg-velo focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blu-scuro disabled:opacity-50'
  const altri: Array<{ chiave: Gesto; etichetta: string; dettaglio: string | null; rosso: boolean }> = [
    ...gesti.map((g, i) => ({ chiave: i as Gesto, etichetta: g.etichetta, dettaglio: dettaglioStrada(g), rosso: g.azione === 'chiudi' })),
    ...(con ? [{ chiave: 'nessuna' as Gesto, etichetta: 'Nessuna di queste', dettaglio: null, rosso: false }] : []),
    ...(attesa ? [{ chiave: 'no' as Gesto, etichetta: 'Non mandare', dettaglio: null, rosso: true }] : []),
  ]
  const gestoAperto = altri.find((a) => a.chiave === chiedo)
  const stradaAperta = gestoAperto && typeof gestoAperto.chiave === 'number' ? gesti[gestoAperto.chiave] : null

  return (
    <div>
      <div ref={carta} className="scroll-mt-4 overflow-hidden rounded-2xl border border-attesa-bordo bg-white">
        <div className="border-b border-attesa-bordo bg-attesa-fondo px-4 py-3">
          <p className="text-[16px] font-bold text-attesa-testo">Aspetta te</p>
          {motivo && <p className="mt-0.5 max-w-[65ch] text-[14px] leading-snug text-attesa-testo">{motivo}</p>}
        </div>
        {scelta ? (
          <>
            <div className="px-4 pb-1 pt-3">
              <div className="mb-2 flex items-baseline justify-between gap-3">
                <label htmlFor={`bozza-${id}`} className="min-w-0 text-[16px] font-bold leading-snug text-inchiostro">
                  {scelta.strada?.etichetta ?? (attesa?.tipo || 'La bozza')}
                </label>
                {mail.length > 1 && <span className="shrink-0 text-[13px] font-semibold text-tenue">{aperta + 1} di {mail.length}</span>}
              </div>
              {scelta.strada?.perche && <p className="mb-2 max-w-[65ch] text-[14px] leading-snug text-tenue">{scelta.strada.perche}</p>}
              <CampoBozza id={`bozza-${id}`} valore={testo} disabled={lavoro}
                          onCambia={(t) => setTesti((xs) => xs.map((x, i) => i === aperta ? t : x))} />
              <div className="flex min-h-11 flex-wrap items-center gap-x-3 text-[13px] text-tenue">
                {cambiato ? (
                  <>
                    <span className="font-semibold text-noi-testo">Cambiata da te: parte così</span>
                    <button onClick={() => setTesti((xs) => xs.map((x, i) => i === aperta ? scelta.testo : x))} disabled={lavoro}
                            className="inline-flex min-h-11 items-center font-semibold text-blu-scuro hover:underline">
                      Torna al testo di Clara
                    </button>
                  </>
                ) : <span>Tocca il testo per cambiarlo</span>}
              </div>
            </div>
            {chiedo !== 'manda' ? (
              <div className="flex flex-wrap items-center gap-2 border-t border-velo px-3 py-2">
                <Bottone tipo="primo" onClick={() => setChiedo('manda')} disabled={lavoro || !testo.trim()}>Manda</Bottone>
                {!testo.trim() && <span className="text-[14px] text-no-testo">Il testo è vuoto</span>}
              </div>
            ) : (
              <Conferma id={`manda-${id}`} tono="noi" lavoro={lavoro} lavoroTesto="Mando…" si="Sì, manda"
                        testo={`Parte al prossimo giro${allega ? ', con analisi e presentazione' : ''}${cambiato ? ', col testo cambiato da te' : ''}. Confermi?`}
                        onSi={() => void fai('manda')} onNo={() => setChiedo(null)} />
            )}
          </>
        ) : (
          <p className="px-4 py-3 text-[15px] text-tenue">Nessuna mail da mandare: scegli qui sotto cosa fare.</p>
        )}
      </div>

      {mail.length > 1 && (
        <div className="mt-4">
          <h3 className="mb-2 text-[14px] font-semibold text-tenue">{mail.length === 2 ? "Un'altra versione" : 'Altre versioni'}</h3>
          <ol className="space-y-3">
            {mail.map((m, i) => i === aperta ? null : (
              <li key={`${m.strada?.etichetta ?? 'bozza'}-${i}`} className="overflow-hidden rounded-2xl border border-bordo bg-white">
                <div className="px-4 pt-3">
                  <p className="text-[16px] font-bold leading-snug text-inchiostro">{m.strada?.etichetta}</p>
                  {m.strada?.perche && <p className="mt-0.5 max-w-[65ch] text-[14px] leading-snug text-tenue">{m.strada.perche}</p>}
                  <div className="mt-2"><TestoMessaggio testo={testi[i] ?? m.testo} righe={3} /></div>
                </div>
                <div className="border-t border-velo px-3 py-2">
                  <Bottone onClick={() => usa(i)} disabled={lavoro}>Usa questa</Bottone>
                </div>
              </li>
            ))}
          </ol>
        </div>
      )}

      {altri.length > 0 && (
        <div className="mt-4">
          <h3 className="mb-2 text-[14px] font-semibold text-tenue">{scelta ? 'Oppure' : 'Cosa fare'}</h3>
          <div className="flex flex-wrap gap-2">
            {altri.map((a) => (
              <button key={String(a.chiave)} onClick={() => setChiedo(chiedo === a.chiave ? null : a.chiave)} disabled={lavoro} aria-expanded={chiedo === a.chiave}
                      className={`${piccolo} ${a.rosso ? 'text-no-testo' : 'text-inchiostro'} ${chiedo === a.chiave ? 'border-blu-scuro' : 'border-bordo'}`}>
                {a.rosso && <Icona nome="divieto" className="h-4 w-4" />}
                {a.etichetta}
              </button>
            ))}
          </div>
          {gestoAperto && (
            <div className="mt-2 overflow-hidden rounded-2xl border border-bordo bg-white">
              {stradaAperta?.perche && (
                <p className="px-4 pt-3 text-[14px] leading-snug text-tenue">
                  {stradaAperta.perche}{gestoAperto.dettaglio ? ` ${gestoAperto.dettaglio}.` : ''}
                </p>
              )}
              <Conferma id={`gesto-${id}`} tono={gestoAperto.rosso || gestoAperto.chiave === 'nessuna' ? 'no' : 'noi'} lavoro={lavoro} lavoroTesto="Faccio…"
                        si={gestoAperto.chiave === 'no' ? 'Sì, non mandare' : gestoAperto.chiave === 'nessuna' ? 'Sì, nessuna' : `Sì: ${gestoAperto.etichetta.toLowerCase()}`}
                        testo={gestoAperto.chiave === 'no' ? 'Non parte e resta qui come non mandato. Confermi?'
                          : gestoAperto.chiave === 'nessuna' ? "Chiudo la domanda senza fare nulla: il lead resta com'è. Confermi?"
                          : stradaAperta ? confermaStrada(stradaAperta, false) : 'Confermi?'}
                        onSi={() => void fai(gestoAperto.chiave)} onNo={() => setChiedo(null)} />
            </div>
          )}
        </div>
      )}
      {sbaglio && <p role="alert" className="mt-2 text-[14px] font-semibold text-no-testo">{sbaglio}</p>}
    </div>
  )
}

/** «Chiudi: non interessato» (20/10 sera): il lead diventa un no deciso da Dre, Clara non gli scrive
 *  piu', le mail in attesa si chiudono. Con conferma, e una nota che resta. */
function ChiudiLead({ id, proposte, onChiuso }: { id: string; proposte: number[]; onChiuso: (d: Decisione, nota: Nota | null) => void }) {
  const [chiedo, setChiedo] = useState(false)
  const [lavoro, setLavoro] = useState(false)
  const [sbaglio, setSbaglio] = useState<string | null>(null)

  async function chiudi() {
    setLavoro(true); setSbaglio(null)
    try {
      const r = await chiudiLead(id, proposte, scrittureChiusura(), NOTE_APP.chiuso)
      setChiedo(false); onChiuso(r.decisione, r.nota)
    } catch (e) {
      setSbaglio(`Non chiuso: ${e instanceof Error ? e.message : e}`)
    } finally {
      setLavoro(false)
    }
  }

  return (
    <div className="mt-3 overflow-hidden rounded-2xl border border-bordo bg-white">
      {!chiedo ? (
        <div className="px-2 py-1">
          <button onClick={() => setChiedo(true)}
                  className="inline-flex min-h-11 items-center gap-1.5 rounded-full px-3 text-[14px] font-semibold text-no-testo transition-colors duration-150 hover:bg-no-fondo focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-no-testo">
            <Icona nome="divieto" className="h-4 w-4" /> Chiudi: non interessato
          </button>
        </div>
      ) : (
        <div className="-mt-px">
          <Conferma id={`chiudi-${id}`} tono="no" lavoro={lavoro} lavoroTesto="Chiudo…" si="Sì, chiudi"
                    testo={`Lo segno come non interessato: Clara non gli scrive più${proposte.length ? ' e le mail in attesa si chiudono' : ''}. Confermi?`}
                    onSi={() => void chiudi()} onNo={() => setChiedo(false)} />
        </div>
      )}
      {sbaglio && <p role="alert" className="px-4 pb-3 text-[14px] font-semibold text-no-testo">{sbaglio}</p>}
    </div>
  )
}

/** La prossima call con lui (17/10: la scheda di chi aveva la call lunedi' non la diceva). */
function ProssimaCall({ call }: { call: Call[] }) {
  const adesso = Date.now()
  const c = [...call].sort((a, b) => a.at.localeCompare(b.at)).find((x) => new Date(x.at).getTime() > adesso - 90 * 60_000)
  if (!c) return null
  const giorno = nomeGiorno(giornoRoma(new Date(c.at)))
  return (
    <div className="mt-3 flex flex-wrap items-center gap-x-3 gap-y-2 rounded-2xl border border-ok-bordo bg-ok-fondo px-4 py-3">
      <p className="flex items-center gap-2 text-[15px] text-inchiostro">
        <Icona nome="ok" className="h-5 w-5 shrink-0 text-ok-testo" />
        <b className="text-ok-testo">Call {giorno === 'Oggi' || giorno === 'Domani' ? giorno.toLowerCase() : giorno.charAt(0).toLowerCase() + giorno.slice(1)} alle {ora(c.at)}</b>
        {c.di_chi && <span className="text-tenue">, nel calendario di {c.di_chi}</span>}
      </p>
      {c.meet && (
        <a href={c.meet} target="_blank" rel="noreferrer"
           className="inline-flex min-h-11 items-center gap-1.5 rounded-full bg-blu-scuro px-4 text-[14px] font-semibold text-white hover:bg-navy">
          <Icona nome="video" className="h-4 w-4" /> Apri il Meet
        </a>
      )}
    </div>
  )
}

function Torna({ indietro }: { indietro: () => void }) {
  return (
    <button onClick={indietro} className="-ml-2 mb-3 inline-flex min-h-11 items-center gap-1 rounded-full pl-1 pr-3 text-[15px] font-semibold text-blu-scuro hover:bg-velo">
      <Icona nome="indietro" /> Indietro
    </button>
  )
}

function Blocco({ titolo, children }: { titolo: string; children: React.ReactNode }) {
  return (
    <section className="mt-8">
      <h2 className="mb-3 text-[13px] font-bold uppercase tracking-[0.06em] text-tenue">{titolo}</h2>
      {children}
    </section>
  )
}

/** Stato, responsabile, prossima azione e data: quello che decide Dre (19/10, i 12 stati). Vuoto vuol
 *  dire «come dice il sistema»: la voce vuota porta il nome di quello che vale adesso. */
function Decidi({ id, sistema, suggerita, decisione, onSalvato }: {
  id: string; sistema: string; suggerita: { mossa: string | null; il: string | null }; decisione: Decisione | null; onSalvato: (d: Decisione) => void
}) {
  const [stato, setStato] = useState(decisione?.stato ?? '')
  const [chi, setChi] = useState<string>(decisione?.responsabile ?? '')
  const [mossa, setMossa] = useState(decisione?.prossima_mossa ?? '')
  const [il, setIl] = useState(decisione?.prossima_il ?? '')
  const [lavoro, setLavoro] = useState(false)
  const [sbaglio, setSbaglio] = useState<string | null>(null)
  const cambiato = stato !== (decisione?.stato ?? '') || chi !== (decisione?.responsabile ?? '')
    || mossa !== (decisione?.prossima_mossa ?? '') || il !== (decisione?.prossima_il ?? '')
  const info = infoStato(stato || sistema)
  const proposta = stato && stato !== sistema ? (info?.azione ?? null) : (suggerita.mossa || info?.azione || null)

  async function salva() {
    setLavoro(true); setSbaglio(null)
    try {
      onSalvato(await salvaDecisione(id, {
        stato: (stato || null) as Decisione['stato'], responsabile: (chi || null) as Decisione['responsabile'],
        prossima_mossa: mossa.trim() || null, prossima_il: il || null,
      }))
    } catch (e) {
      setSbaglio(`Non salvato: ${e instanceof Error ? e.message : e}`)
    } finally {
      setLavoro(false)
    }
  }

  const campo = 'h-11 w-full rounded-xl border border-bordo bg-white px-3 text-[16px] text-inchiostro outline-none transition-colors duration-150 focus:border-blu-scuro'
  const etichetta = 'mb-1 block text-[13px] font-semibold text-tenue'
  return (
    <form onSubmit={(e) => { e.preventDefault(); void salva() }} className="rounded-2xl border border-bordo bg-white p-4">
      <div className="grid gap-3 sm:grid-cols-2">
        <div>
          <label htmlFor="stato" className={etichetta}>Stato</label>
          <select id="stato" value={stato} onChange={(e) => setStato(e.target.value)} className={campo}>
            <option value="">{sistema}</option>
            {GRUPPI.map((g) => (
              <optgroup key={g} label={g}>
                {INFO_STATI.filter((s) => s.gruppo === g).map((s) => <option key={s.nome} value={s.nome}>{s.nome}</option>)}
              </optgroup>
            ))}
          </select>
        </div>
        <div>
          <label htmlFor="responsabile" className={etichetta}>Chi</label>
          <select id="responsabile" value={chi} onChange={(e) => setChi(e.target.value)} className={campo}>
            <option value="">{info?.responsabile ?? 'Claude'}</option>
            {RESPONSABILI.map((r) => <option key={r} value={r}>{r}</option>)}
          </select>
        </div>
        <div>
          <label htmlFor="mossa" className={etichetta}>Prossima azione</label>
          <input id="mossa" value={mossa} onChange={(e) => setMossa(e.target.value)} maxLength={200}
                 placeholder={proposta ?? 'Cosa fare'}
                 className={`${campo} placeholder:text-spento`} />
        </div>
        <div>
          <label htmlFor="quando" className={etichetta}>Quando</label>
          <input id="quando" type="date" value={il || ''} onChange={(e) => setIl(e.target.value)} className={campo} />
        </div>
      </div>
      <div className="mt-4 flex items-center gap-3">
        <Bottone tipo="primo" type="submit" disabled={lavoro || !cambiato}>{lavoro ? 'Salvo…' : 'Salva'}</Bottone>
        {sbaglio && <p role="alert" className="text-[14px] font-semibold text-no-testo">{sbaglio}</p>}
      </div>
    </form>
  )
}

function Note({ id, note, onNota, onTolta, mostra }: {
  id: string; note: Nota[]; onNota: (n: Nota) => void; onTolta: (id: number) => void; mostra: (a: { testo: string }) => void
}) {
  const [testo, setTesto] = useState('')
  const [lavoro, setLavoro] = useState(false)
  const [sbaglio, setSbaglio] = useState<string | null>(null)
  const [io, setIo] = useState<string | null>(null)
  useEffect(() => { void ioSono().then(setIo) }, [])

  // 17/10: una nota scritta sul lead sbagliato o con un errore non si poteva togliere.
  // Chi l'ha scritta la cancella (il database non lascia cancellare quelle degli altri).
  async function togli(n: Nota) {
    if (!window.confirm('Cancellare questa nota?')) return
    setSbaglio(null)
    try {
      await togliNota(n.id)
      onTolta(n.id)
      mostra({ testo: 'Nota cancellata' })
    } catch (e) {
      setSbaglio(`Nota non cancellata: ${e instanceof Error ? e.message : e}`)
    }
  }

  async function aggiungi() {
    if (!testo.trim()) return
    setLavoro(true); setSbaglio(null)
    try {
      onNota(await aggiungiNota(id, testo))
      setTesto('')
    } catch (e) {
      setSbaglio(`Nota non salvata: ${e instanceof Error ? e.message : e}`)
    } finally {
      setLavoro(false)
    }
  }

  return (
    <div>
      <form onSubmit={(e) => { e.preventDefault(); void aggiungi() }}>
        <label htmlFor="nuova-nota" className="sr-only">Nuova nota</label>
        <textarea id="nuova-nota" value={testo} onChange={(e) => setTesto(e.target.value)} rows={3} maxLength={4000}
                  placeholder="Scrivi una nota: cosa vi siete detti, cosa fare"
                  className="w-full rounded-xl border border-bordo px-3 py-2 text-[16px] text-inchiostro outline-none placeholder:text-spento focus:border-blu-scuro" />
        <div className="mt-2 flex items-center gap-2">
          <Bottone tipo="primo" type="submit" disabled={lavoro || !testo.trim()}>{lavoro ? 'Salvo…' : 'Aggiungi la nota'}</Bottone>
        </div>
        {sbaglio && <p role="alert" className="mt-2 text-[14px] font-semibold text-no-testo">{sbaglio}</p>}
      </form>
      {note.length ? (
        <ol className="mt-4 space-y-3">
          {note.map((n) => (
            <li key={n.id} className="border-l-2 border-bordo pl-3">
              <p className="flex items-center justify-between gap-2 text-[13px] text-tenue">
                <span>{quando(n.at)}{n.autore_nome && `, ${n.autore_nome}`}{n.tipo === 'chiamata' && ', telefonata'}</span>
                {io && n.autore === io && (
                  <button onClick={() => void togli(n)} aria-label="Cancella questa nota"
                          className="-my-2 inline-flex min-h-11 items-center rounded-full px-3 text-[13px] font-semibold text-tenue hover:bg-velo hover:text-no-testo">
                    Cancella
                  </button>
                )}
              </p>
              <p className="whitespace-pre-wrap text-[15px] text-inchiostro">{n.testo}</p>
            </li>
          ))}
        </ol>
      ) : <p className="mt-3 text-[14px] text-tenue">Ancora nessuna nota.</p>}
    </div>
  )
}

function Analisi({ a }: { a: Scheda['scheda']['analisi'] }) {
  const [apro, setApro] = useState(false)
  const [sbaglio, setSbaglio] = useState(false)
  if (!a.mandata) return <p className="text-[15px] text-tenue">Analisi non ancora mandata.</p>
  const apribile = Boolean(a.percorso || a.link)

  async function apri() {
    // la finestra si apre subito (Safari blocca quelle aperte dopo un'attesa), poi si punta al PDF
    const w = window.open('', '_blank')
    if (w) { try { w.opener = null } catch { /* niente */ } }
    setApro(true); setSbaglio(false)
    const url = await linkAnalisi(a)
    setApro(false)
    if (!url) { w?.close(); setSbaglio(true); return }
    if (w) w.location.replace(url); else window.open(url, '_blank')
  }

  return (
    <div className="rounded-2xl border border-bordo bg-white px-4 py-3">
      <div className="flex flex-wrap items-center justify-between gap-x-3 gap-y-1">
        <p className="text-[15px] text-inchiostro"><b className="font-semibold">Analisi mandata</b>{a.il ? <span className="text-tenue"> {quando(a.il)}</span> : ''}</p>
        {apribile ? (
          <Bottone onClick={() => void apri()} disabled={apro} className="-mr-2">{apro ? 'Apro…' : 'Apri il PDF'} <Icona nome="esterno" className="h-4 w-4" /></Bottone>
        ) : <span className="text-[14px] text-tenue">PDF non agganciato</span>}
      </div>
      {a.punto && <p className="mt-1 max-w-[65ch] text-[14px] leading-snug text-tenue">{a.punto}</p>}
      {sbaglio && <p role="alert" className="mt-1 text-[14px] font-semibold text-no-testo">Il PDF non si apre: provalo dal Workspace completo.</p>}
    </div>
  )
}

/** LA CONVERSAZIONE AL CONTRARIO (22/10 notte, Dre: «voglio vedere i messaggi a ritroso, come su Smartlead»):
 *  in cima la sua ultima mail, sotto la nostra prima di quella, e cosi' indietro. L'analisi e' una riga col PDF
 *  nel suo punto del tempo. Le piu' vecchie oltre le prime quattro si aprono in fondo. */
function Filo({ filo, analisi, lui }: { filo: Messaggio[]; analisi: Scheda['scheda']['analisi']; lui: string }) {
  const [tutto, setTutto] = useState(false)
  const voci = filoAlContrario(filo, analisi)
  if (!voci.length) return <p className="text-[15px] text-tenue">Nessuna mail.</p>
  // si contano le mail, non la riga dell'analisi
  let mail = 0
  const fino = tutto ? -1 : voci.findIndex((v) => v.tipo === 'mail' && ++mail > 4)
  const mostrate = fino === -1 ? voci : voci.slice(0, fino)
  const nascoste = voci.length - mostrate.length
  return (
    <div>
      <ol className="space-y-3">
        {mostrate.map((v, i) => v.tipo === 'analisi'
          ? <li key="analisi"><Analisi a={analisi} /></li>
          : <Mail key={`${v.m.at}-${i}`} m={v.m} lui={lui} />)}
      </ol>
      {nascoste > 0 && (
        <div className="mt-3">
          <Bottone onClick={() => setTutto(true)}>{nascoste === 1 ? 'Mostra la mail più vecchia' : `Mostra le ${nascoste} più vecchie`}</Bottone>
        </div>
      )}
    </div>
  )
}

const RIGHE = 6
const CARATTERI = 600

function Mail({ m, lui: nome }: { m: Messaggio; lui: string }) {
  const [citato, setCitato] = useState(false)
  const lui = m.chi === 'lui'
  // le mail lunghe (le nostre con firma e informativa, le sue con l'invito del calendario) si
  // leggono dalle prime righe, il resto a richiesta. Le sue brevi restano intere.
  const righe = m.testo.split('\n')
  const lunga = righe.length > RIGHE + 2 || m.testo.length > CARATTERI + 200
  const [intera, setIntera] = useState(false)
  const testo = lunga && !intera ? righe.slice(0, RIGHE).join('\n').slice(0, CARATTERI).trimEnd() + '…' : m.testo
  // 17/10, Dre: «"noi" e "loro" in piccolissimo: devo rileggere ogni messaggio per capire qual e'
  // il mio». Ogni mail ha la sua barra a sinistra e la parola grande: Noi in blu, sul fondo
  // azzurro e spostata a destra; Loro nel colore caldo, sul bianco e a sinistra.
  return (
    <li className={`rounded-xl border border-l-[5px] p-4 ${lui
      ? 'mr-6 border-bordo border-l-loro-segno bg-white sm:mr-16'
      : 'ml-6 border-noi-bordo border-l-noi-segno bg-noi-fondo sm:ml-16'}`}>
      <p className="mb-2 flex flex-wrap items-baseline gap-x-2">
        <span className={`text-[15px] font-bold ${lui ? 'text-loro-testo' : 'text-noi-testo'}`}>
          {lui ? `Loro${nome ? ` (${nome})` : ''}` : 'Noi'}
        </span>
        <span className="text-[14px] text-inchiostro/75">{quando(m.at)}</span>
      </p>
      {m.testo ? <p className="whitespace-pre-wrap break-words text-[15px] leading-relaxed text-inchiostro">{testo}</p>
        : <p className="text-[14px] italic text-tenue">Solo testo citato.</p>}
      {lunga && (
        <button onClick={() => setIntera(!intera)} aria-expanded={intera}
                className="mt-1 inline-flex min-h-11 items-center text-[14px] font-semibold text-blu-scuro hover:underline">
          {intera ? 'Mostra meno' : 'Mostra tutta la mail'}
        </button>
      )}
      {m.citato && (
        <div className="mt-2">
          <button onClick={() => setCitato(!citato)} aria-expanded={citato}
                  className="inline-flex min-h-11 items-center text-[14px] font-semibold text-blu-scuro hover:underline">
            {citato ? 'Nascondi il testo citato' : 'Mostra il testo citato'}
          </button>
          {citato && <p className="mt-1 whitespace-pre-wrap break-words border-l-2 border-bordo pl-3 text-[14px] leading-relaxed text-tenue">{m.citato}</p>}
        </div>
      )}
    </li>
  )
}
