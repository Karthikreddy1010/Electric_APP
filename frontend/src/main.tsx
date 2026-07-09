import React from 'react'
import ReactDOM from 'react-dom/client'
import axios from 'axios'
import App from './App.tsx'
import './index.css'
import 'leaflet/dist/leaflet.css'
// Unwrap the StandardResponseMiddleware envelope { success: true, data: {...} }
// so every component can read res.data directly instead of res.data.data
axios.interceptors.response.use((response) => {
  const d = response.data;
  if (d && typeof d === 'object' && 'success' in d && 'data' in d) {
    response.data = d.data;
  }
  return response;
});

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
)
