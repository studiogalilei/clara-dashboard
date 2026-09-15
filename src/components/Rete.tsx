import { Component, type ErrorInfo, type ReactNode } from 'react'

// LA RETE (QA browser, 15/9). Un errore dentro una pagina portava via tutta
// l'app: schermo bianco, niente menu, niente modo di tornare indietro, e
// nessuno capiva perche'. Adesso l'errore resta dentro la pagina e si
// ricomincia da li'.

interface Props { children: ReactNode; dove?: string; onTorna?: () => void }
interface Stato { guaio: Error | null }

export default class Rete extends Component<Props, Stato> {
  state: Stato = { guaio: null }

  static getDerivedStateFromError(guaio: Error): Stato {
    return { guaio }
  }

  componentDidCatch(guaio: Error, info: ErrorInfo) {
    console.error('SG Workspace:', guaio, info.componentStack)
  }

  componentDidUpdate(prima: Props) {
    // cambiando pagina si riparte puliti
    if (prima.dove !== this.props.dove && this.state.guaio) this.setState({ guaio: null })
  }

  render() {
    if (!this.state.guaio) return this.props.children
    return (
      <div className="mx-auto max-w-lg px-4 py-16 text-center">
        <p className="text-base font-extrabold">Questa pagina si è inceppata.</p>
        <p className="mt-1 text-sm text-tenue">
          Il resto funziona. Riprova, e se torna a succedere scrivilo a Dre.
        </p>
        <div className="mt-4 flex justify-center gap-2">
          <button
            onClick={() => this.setState({ guaio: null })}
            className="rounded-full bg-blu px-5 py-2 text-sm font-bold text-white hover:bg-blu-scuro"
          >
            Riprova
          </button>
          <button
            onClick={() => window.location.reload()}
            className="rounded-full border border-bordo bg-white px-5 py-2 text-sm font-semibold text-tenue hover:border-navy hover:text-navy"
          >
            Ricarica tutto
          </button>
        </div>
        <p className="mt-4 break-words text-[11px] text-spento">{this.state.guaio.message}</p>
      </div>
    )
  }
}
