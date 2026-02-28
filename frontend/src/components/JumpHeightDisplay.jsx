import { clsx } from 'clsx'

const TIERS = [
  { min: 40, label: 'Elite', color: 'text-yellow-400' },
  { min: 30, label: 'Advanced', color: 'text-sky-400' },
  { min: 20, label: 'Intermediate', color: 'text-green-400' },
  { min: 0,  label: 'Developing', color: 'text-gray-400' },
]

function getTier(inches) {
  return TIERS.find(t => inches >= t.min) || TIERS[TIERS.length - 1]
}

export default function JumpHeightDisplay({ inches = 0, cm = 0, score = 0, flightTimeMs = 0 }) {
  const tier = getTier(inches)

  return (
    <div className="bg-gray-900 rounded-2xl p-8 text-center border border-gray-800">
      <p className="text-gray-400 text-sm uppercase tracking-widest mb-2">Jump Height</p>

      <div className="flex items-end justify-center gap-2 mb-1">
        <span className={clsx('text-7xl font-black tabular-nums', tier.color)}>
          {inches.toFixed(1)}
        </span>
        <span className="text-gray-400 text-2xl mb-3">in</span>
        <span className="text-gray-500 text-lg mb-3 ml-2">/ {cm.toFixed(1)} cm</span>
      </div>

      <span className={clsx('inline-block px-3 py-1 rounded-full text-xs font-semibold uppercase tracking-wider border', {
        'border-yellow-500/40 bg-yellow-500/10 text-yellow-400': tier.label === 'Elite',
        'border-sky-500/40 bg-sky-500/10 text-sky-400': tier.label === 'Advanced',
        'border-green-500/40 bg-green-500/10 text-green-400': tier.label === 'Intermediate',
        'border-gray-600/40 bg-gray-600/10 text-gray-400': tier.label === 'Developing',
      })}>
        {tier.label}
      </span>

      <div className="mt-6 grid grid-cols-2 gap-4 text-center">
        <div>
          <p className="text-2xl font-bold text-white">{score}<span className="text-sm text-gray-500">/99</span></p>
          <p className="text-xs text-gray-500 mt-1">Height Score</p>
        </div>
        <div>
          <p className="text-2xl font-bold text-white">{flightTimeMs.toFixed(0)}<span className="text-sm text-gray-500">ms</span></p>
          <p className="text-xs text-gray-500 mt-1">Flight Time</p>
        </div>
      </div>
    </div>
  )
}
