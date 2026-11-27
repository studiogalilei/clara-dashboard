import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import Desk from './desk/Desk'
import Aggiorna from './Aggiorna'

// 27/11/2026: l'app e' solo il LinkedIn Desk (l'outbound, la versione snella e il Workspace sono stati tolti).
createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <Desk />
    <Aggiorna />
  </StrictMode>,
)
