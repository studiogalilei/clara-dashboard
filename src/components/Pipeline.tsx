import Radar from './Radar'

// La home: la giornata e basta (Dre, 4/9). Prima qui sopra c'erano i quattro
// numeri delle fasi, ma quelli sono lo stato della pipeline, non la giornata:
// stanno nella sezione Pipeline, dove ci sono anche le carte che li fanno.
// Qui resta cosa devi fare adesso, la prossima call e cosa non va.

interface Props {
  onOpen: (id: string) => void
  onOggi?: () => void
  onCalendario?: () => void
  onTutti?: () => void
}

export default function Pipeline({ onOpen, onOggi, onCalendario }: Props) {
  return (
    <div className="pb-24 sm:pb-8">
      <Radar onOpen={onOpen} onOggi={onOggi} onCalendario={onCalendario} />
    </div>
  )
}
