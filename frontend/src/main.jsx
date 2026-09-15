import React from 'react'
import ReactDOM from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import { Toaster } from 'react-hot-toast'
import App from './App.jsx'
import './index.css'

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <BrowserRouter>
      <App />
      <Toaster
        position="top-right"
        toastOptions={{
          style: {
            background: '#0c1120',
            color: '#f0f4ff',
            border: '1px solid rgba(255,255,255,0.1)',
            borderRadius: '12px',
            fontFamily: "'Inter', sans-serif",
            fontSize: '0.875rem',
          },
          success: { iconTheme: { primary: '#34d399', secondary: '#0c1120' } },
          error: { iconTheme: { primary: '#f87171', secondary: '#0c1120' } },
        }}
      />
    </BrowserRouter>
  </React.StrictMode>,
)
