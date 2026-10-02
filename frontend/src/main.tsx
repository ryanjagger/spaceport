// One variable file covers every weight and Latin Extended, for free-text pilot
// names (Łukasz, Şebnem).
import '@fontsource-variable/inter/wght.css'
import './styles/global.css'

import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter, Route, Routes } from 'react-router-dom'
import { Layout } from './components/Layout'
import { CharterPage } from './pages/CharterPage'
import { FleetDashboard } from './pages/FleetDashboard'

const queryClient = new QueryClient({
  defaultOptions: {
    queries: { retry: 1, refetchOnWindowFocus: true, refetchOnReconnect: true },
    mutations: { retry: false },
  },
})

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Routes>
          <Route element={<Layout />}>
            <Route path="/" element={<CharterPage />} />
            <Route path="/fleet" element={<FleetDashboard />} />
            <Route path="*" element={<CharterPage />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  </StrictMode>,
)
