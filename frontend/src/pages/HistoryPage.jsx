import { Link } from 'react-router-dom'
import { useUserHistory } from '../hooks/useUserHistory'
import ProgressChart from '../components/ProgressChart'
import useUserStore from '../stores/userStore'

function StatCard({ label, value, unit = '' }) {
  return (
    <div className="bg-gray-900 rounded-xl p-4 border border-gray-800 text-center">
      <p className="text-2xl font-black text-sky-400">{value}<span className="text-gray-500 text-sm ml-1">{unit}</span></p>
      <p className="text-gray-500 text-xs mt-1">{label}</p>
    </div>
  )
}

function JumpCard({ entry }) {
  const height = entry.jump_height_inches?.toFixed(1) ?? '—'
  const score = entry.scorecard?.overall_score ?? '—'
  const date = entry.timestamp ? new Date(entry.timestamp).toLocaleDateString() : ''

  return (
    <div className="bg-gray-900 rounded-xl p-4 border border-gray-800 flex items-center justify-between">
      <div>
        <p className="text-white font-semibold">{height}" <span className="text-gray-500 text-sm">/ {score}/99</span></p>
        <p className="text-gray-500 text-xs mt-0.5">{date}</p>
      </div>
      {entry.id && (
        <Link
          to={`/results/${entry.id}`}
          className="text-sky-400 hover:text-sky-300 text-sm transition-colors"
        >
          View →
        </Link>
      )}
    </div>
  )
}

export default function HistoryPage() {
  const { userId } = useUserStore()
  const { history, stats, isLoading, error } = useUserHistory(userId, 20)

  return (
    <div className="min-h-screen">
      <nav className="flex items-center justify-between px-6 py-4 border-b border-gray-800">
        <Link to="/" className="text-xl font-black text-white tracking-tight">Jump<span className="text-sky-400">AI</span></Link>
        <Link to="/upload" className="bg-sky-600 hover:bg-sky-500 text-white px-4 py-1.5 rounded-lg text-sm font-medium transition-colors">
          Analyze Jump
        </Link>
      </nav>

      <div className="max-w-3xl mx-auto px-6 py-10 space-y-6">
        <h1 className="text-3xl font-black text-white">Your Progress</h1>

        {isLoading && (
          <p className="text-gray-500 text-center py-8 animate-pulse">Loading history...</p>
        )}

        {error && (
          <div className="bg-red-500/10 border border-red-500/30 text-red-400 rounded-xl px-4 py-3 text-sm">
            {error}
          </div>
        )}

        {stats && (
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            <StatCard label="Total Jumps" value={stats.total_jumps} />
            <StatCard label="Best Height" value={stats.best_height_inches?.toFixed(1) ?? '—'} unit='"' />
            <StatCard label="Best Score" value={stats.best_overall_score ?? '—'} unit="/99" />
            <StatCard label="Avg Height" value={stats.avg_height_inches?.toFixed(1) ?? '—'} unit='"' />
          </div>
        )}

        {history.length > 0 && <ProgressChart history={history} />}

        {!isLoading && !error && history.length === 0 && (
          <div className="text-center py-16">
            <p className="text-gray-500 mb-4">No jumps yet.</p>
            <Link to="/upload" className="text-sky-400 hover:text-sky-300">Upload your first jump →</Link>
          </div>
        )}

        {history.length > 0 && (
          <div>
            <h2 className="text-lg font-semibold text-white mb-3">Jump Log</h2>
            <div className="space-y-2">
              {[...history].reverse().map((entry, i) => (
                <JumpCard key={entry.id || i} entry={entry} />
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
