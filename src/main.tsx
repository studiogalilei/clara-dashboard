import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import Radice from './Radice.tsx'

// 15/10: la porta d'ingresso sceglie fra la versione snella e il Workspace completo (Radice.tsx)
createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <Radice />
  </StrictMode>,
)
