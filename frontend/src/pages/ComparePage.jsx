import { useParams, Link } from 'react-router-dom'
import { useState, useEffect } from 'react'
import { api } from '../api/client'
import CompareView from '../components/CompareView'

export default function ComparePage() {
  const { id1, id2 } = useParams()
  const [resultA, setResultA] = useState(null)
  const [resultB, setResultB] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    if (!id1 || !id2) return
    setLoading(true)

    Promise.all([api.getResult(id1), api.getResult(id2)])
      .then(([a, b]) => {
        setResultA(a)
        setResultB(b)
        setLoading(false)
      })
      .catch(err => {
        setError(err.message)
        setLoading(false)
      })
  }, [id1, id2])

  return (
    <div className="min-h-screen">
      <nav className="flex items-center justify-between px-6 py-4 border-b border-gray-800">
        <Link to="/" className="text-xl font-black text-white tracking-tight">Jump<span className="text-sky-400">AI</span></Link>
        <div className="flex gap-4 text-sm">
          <Link to="/history" className="text-gray-400 hover:text-white transition-colors">History</Link>
          <Link to="/upload" className="bg-sky-600 hover:bg-sky-500 text-white px-4 py-1.5 rounded-lg font-medium transition-colors">New Jump</Link>
        </div>
      </nav>

      <div className="max-w-4xl mx-auto px-6 py-10 space-y-6">
        <div className="flex items-center justify-between">
          <h1 className="text-3xl font-black text-white">Compare Jumps</h1>
          <div className="text-xs text-gray-500 font-mono">
            <span className="text-sky-400">{id1?.slice(0, 8)}</span> vs <span className="text-purple-400">{id2?.slice(0, 8)}</span>
          </div>
        </div>

        {loading && <p className="text-gray-500 animate-pulse">Loading results...</p>}
        {error && <p className="text-red-400">{error}</p>}
        {!loading && !error && <CompareView resultA={resultA} resultB={resultB} />}
      </div>
    </div>
  )
}
