import { Link } from 'react-router-dom'

export default function LandingPage() {
  return (
    <div className="min-h-screen flex flex-col">
      {/* Nav */}
      <nav className="flex items-center justify-between px-6 py-4 border-b border-gray-800">
        <span className="text-xl font-black text-white tracking-tight">Jump<span className="text-sky-400">AI</span></span>
        <div className="flex gap-4 text-sm text-gray-400">
          <Link to="/history" className="hover:text-white transition-colors">History</Link>
          <Link to="/upload" className="bg-sky-600 hover:bg-sky-500 text-white px-4 py-1.5 rounded-lg font-medium transition-colors">Analyze Jump</Link>
        </div>
      </nav>

      {/* Hero */}
      <div className="flex-1 flex flex-col items-center justify-center text-center px-6 py-24">
        <div className="inline-block bg-sky-500/10 border border-sky-500/20 text-sky-400 text-xs font-semibold px-3 py-1 rounded-full mb-6 uppercase tracking-wider">
          CV + AI Powered
        </div>

        <h1 className="text-5xl md:text-7xl font-black text-white leading-tight mb-6">
          Know exactly<br />
          <span className="text-sky-400">why you jump</span><br />
          the way you do.
        </h1>

        <p className="text-gray-400 text-lg max-w-lg mb-10">
          Upload raw footage. Get your jump height, biomechanics score, and a personalized Claude AI coaching report — in seconds.
        </p>

        <Link
          to="/upload"
          className="bg-sky-600 hover:bg-sky-500 text-white font-semibold text-lg px-8 py-4 rounded-2xl transition-colors"
        >
          Analyze My Jump →
        </Link>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-3 border-t border-gray-800">
        {[
          { value: '0–99', label: 'Score Scale' },
          { value: '9', label: 'Biomechanics Metrics' },
          { value: 'Claude', label: 'AI Coach' },
        ].map(({ value, label }) => (
          <div key={label} className="p-8 text-center border-r border-gray-800 last:border-0">
            <p className="text-3xl font-black text-sky-400">{value}</p>
            <p className="text-gray-500 text-sm mt-1">{label}</p>
          </div>
        ))}
      </div>
    </div>
  )
}
