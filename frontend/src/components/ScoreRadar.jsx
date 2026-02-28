import {
  RadarChart, Radar, PolarGrid, PolarAngleAxis, PolarRadiusAxis,
  ResponsiveContainer, Tooltip, Legend
} from 'recharts'

const METRIC_LABELS = {
  arm_swing_score: 'Arm Swing',
  knee_bend_score: 'Knee Bend',
  penultimate_step_score: 'Penu. Step',
  heel_plant_score: 'Heel Plant',
  hip_drive_score: 'Hip Drive',
  body_alignment_score: 'Alignment',
  landing_score: 'Landing',
  elite_similarity_score: 'Elite Sim.',
}

function ScoreBadge({ label, score }) {
  const color = score >= 70 ? 'text-green-400' : score >= 45 ? 'text-yellow-400' : 'text-red-400'
  return (
    <div className="flex items-center justify-between py-1.5 border-b border-gray-800 last:border-0">
      <span className="text-gray-300 text-sm">{label}</span>
      <span className={`font-bold tabular-nums ${color}`}>{score}<span className="text-gray-600 text-xs">/99</span></span>
    </div>
  )
}

export default function ScoreRadar({ scorecard = {} }) {
  const chartData = Object.entries(METRIC_LABELS).map(([key, label]) => ({
    metric: label,
    score: scorecard[key] ?? 0,
  }))

  return (
    <div className="bg-gray-900 rounded-2xl p-6 border border-gray-800">
      <h2 className="text-lg font-semibold text-white mb-4">
        Overall Score: <span className="text-sky-400">{scorecard.overall_score ?? 0}</span>
        <span className="text-gray-500 text-sm">/99</span>
      </h2>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Radar Chart */}
        <div className="h-64">
          <ResponsiveContainer width="100%" height="100%">
            <RadarChart data={chartData}>
              <PolarGrid stroke="#374151" />
              <PolarAngleAxis dataKey="metric" tick={{ fill: '#9ca3af', fontSize: 11 }} />
              <PolarRadiusAxis domain={[0, 99]} tick={false} axisLine={false} />
              <Radar name="Score" dataKey="score" stroke="#0ea5e9" fill="#0ea5e9" fillOpacity={0.25} />
              <Tooltip
                contentStyle={{ backgroundColor: '#111827', border: '1px solid #374151', borderRadius: 8 }}
                labelStyle={{ color: '#e5e7eb' }}
                formatter={(v) => [`${v}/99`, 'Score']}
              />
            </RadarChart>
          </ResponsiveContainer>
        </div>

        {/* Score list */}
        <div>
          {Object.entries(METRIC_LABELS).map(([key, label]) => (
            <ScoreBadge key={key} label={label} score={scorecard[key] ?? 0} />
          ))}
        </div>
      </div>
    </div>
  )
}
