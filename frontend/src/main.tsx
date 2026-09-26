import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App.tsx'
import './index.css'
import 'leaflet/dist/leaflet.css'
// The StandardResponseMiddleware envelope is unwrapped by apiClient's own
// interceptor (src/lib/apiClient.ts). A global axios interceptor used to live
// here for the two pages that called axios directly; they now go through
// apiClient, and axios.create() instances do not inherit global interceptors,
// so this had become dead code.

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
)
