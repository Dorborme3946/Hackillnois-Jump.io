import { BrowserRouter, Routes, Route } from 'react-router-dom'
import LandingPage from './pages/LandingPage'
import UploadPage from './pages/UploadPage'
import ResultsPage from './pages/ResultsPage'
import HistoryPage from './pages/HistoryPage'
import ComparePage from './pages/ComparePage'

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<LandingPage />} />
        <Route path="/upload" element={<UploadPage />} />
        <Route path="/results/:jobId" element={<ResultsPage />} />
        <Route path="/history" element={<HistoryPage />} />
        <Route path="/compare/:id1/:id2" element={<ComparePage />} />
      </Routes>
    </BrowserRouter>
  )
}
