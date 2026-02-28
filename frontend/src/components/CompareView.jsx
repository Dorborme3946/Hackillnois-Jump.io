import ScoreRadar from './ScoreRadar'
import JumpHeightDisplay from './JumpHeightDisplay'

function DiffBadge({ a, b }) {
  const diff = (a ?? 0) - (b ?? 0)
  if (Math.abs(diff) < 1) return <span className="text-gray-500 text-xs">—</span>
  return (
    <span className={`text-xs font-semibold ${diff > 0 ? 'text-green-400' : 'text-red-400'}`}>
      {diff > 0 ? '+' : ''}{diff.toFixed(1)}
    </span>
  )
}

export default function CompareView({ resultA, resultB }) {
  if (!resultA || !resultB) {
    return (
      <div className="text-center py-16 text-gray-500">
        <p>Select two analyses to compare.</p>
      </div>
    )
  }

  const metrics = [
    { key: 'arm_swing_score', label: 'Arm Swing' },
    { key: 'knee_bend_score', label: 'Knee Bend' },
    { key: 'penultimate_step_score', label: 'Penu. Step' },
    { key: 'heel_plant_score', label: 'Heel Plant' },
    { key: 'hip_drive_score', label: 'Hip Drive' },
    { key: 'body_alignment_score', label: 'Alignment' },
    { key: 'landing_score', label: 'Landing' },
    { key: 'elite_similarity_score', label: 'Elite Sim.' },
    { key: 'overall_score', label: 'OVERALL', bold: true },
  ]

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-2 gap-4">
        <JumpHeightDisplay
          inches={resultA.jump_height_inches}
          cm={resultA.jump_height_cm}
          score={resultA.scorecard?.jump_height_score}
          flightTimeMs={resultA.flight_time_ms}
        />
        <JumpHeightDisplay
          inches={resultB.jump_height_inches}
          cm={resultB.jump_height_cm}
          score={resultB.scorecard?.jump_height_score}
          flightTimeMs={resultB.flight_time_ms}
        />
      </div>

      <div className="bg-gray-900 rounded-2xl p-6 border border-gray-800">
        <h2 className="text-lg font-semibold text-white mb-4">Score Comparison</h2>
        <div className="space-y-2">
          {metrics.map(({ key, label, bold }) => {
            const a = resultA.scorecard?.[key] ?? 0
            const b = resultB.scorecard?.[key] ?? 0
            return (
              <div key={key} className={`grid grid-cols-3 items-center gap-2 py-1.5 border-b border-gray-800 last:border-0 ${bold ? 'font-bold' : ''}`}>
                <span className={`text-sm tabular-nums ${a > b ? 'text-sky-400' : 'text-gray-300'}`}>{a}/99</span>
                <div className="flex flex-col items-center">
                  <span className="text-gray-500 text-xs">{label}</span>
                  <DiffBadge a={a} b={b} />
                </div>
                <span className={`text-sm tabular-nums text-right ${b > a ? 'text-sky-400' : 'text-gray-300'}`}>{b}/99</span>
              </div>
            )
          })}
        </div>
      </div>

      <div className="grid grid-cols-2 gap-4">
        <ScoreRadar scorecard={resultA.scorecard} />
        <ScoreRadar scorecard={resultB.scorecard} />
      </div>
    </div>
  )
}
