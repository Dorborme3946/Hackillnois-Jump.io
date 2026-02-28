import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend
} from 'recharts'

export default function ProgressChart({ history = [] }) {
  if (!history.length) {
    return (
      <div className="bg-gray-900 rounded-2xl p-6 border border-gray-800 text-center">
        <p className="text-gray-500">No history yet. Upload your first jump to start tracking progress.</p>
      </div>
    )
  }

  const data = history.map((entry, i) => ({
    jump: `#${i + 1}`,
    height: entry.jump_height_inches ?? 0,
    score: entry.scorecard?.overall_score ?? 0,
  }))

  return (
    <div className="bg-gray-900 rounded-2xl p-6 border border-gray-800">
      <h2 className="text-lg font-semibold text-white mb-4">Progress Over Time</h2>
      <div className="h-56">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={data} margin={{ top: 5, right: 10, left: -10, bottom: 5 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#1f2937" />
            <XAxis dataKey="jump" tick={{ fill: '#6b7280', fontSize: 11 }} />
            <YAxis yAxisId="left" domain={[0, 50]} tick={{ fill: '#6b7280', fontSize: 11 }} unit='"' />
            <YAxis yAxisId="right" orientation="right" domain={[0, 99]} tick={{ fill: '#6b7280', fontSize: 11 }} />
            <Tooltip
              contentStyle={{ backgroundColor: '#111827', border: '1px solid #374151', borderRadius: 8 }}
              labelStyle={{ color: '#e5e7eb' }}
            />
            <Legend wrapperStyle={{ fontSize: 12 }} />
            <Line yAxisId="left" type="monotone" dataKey="height" name='Height (")' stroke="#0ea5e9" strokeWidth={2} dot={{ r: 3 }} />
            <Line yAxisId="right" type="monotone" dataKey="score" name="Score /99" stroke="#a78bfa" strokeWidth={2} dot={{ r: 3 }} />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  )
}
