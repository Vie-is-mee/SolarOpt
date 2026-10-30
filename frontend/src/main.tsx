import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App'
import './studio.css'
import './readability.css'
import './slide-theme.css'
import {dismissSplash} from './splash'

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
)
dismissSplash()

import './handover.css'
