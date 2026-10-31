import React from 'react'
import ReactDOM from 'react-dom/client'
import Account from './Account'
import './studio.css'
import './readability.css'
import './slide-theme.css'
import {dismissSplash} from './splash'

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <Account />
  </React.StrictMode>,
)
dismissSplash()

import './handover.css'
