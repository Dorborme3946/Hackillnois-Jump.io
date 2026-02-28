import { useParams, Link } from 'react-router-dom'
import { useJobResult } from '../hooks/useJobResult'
import ScoreRadar from '../components/ScoreRadar'
import JumpHeightDisplay from '../components/JumpHeightDisplay'
import AIReport from '../components/AIReport'
import PoseReplayViewer from '../components/PoseReplayViewer'

const STEP_LABELS = {
  queued: 'Queued',
  validating: 'Validating video',
  extracting_pose: 'Running YOLO pose extraction',
  calculating_height: 'Calculating jump height',
  analyzing_biomechanics: 'Analyzing biomechanics',
  scoring: 'Computing scores',
  fetching_history: 'Fetching your history',
  generating_report: 'Claude AI generating report',
  storing_memory: 'Storing to Supermemory',
  complete: 'Done!',
}

function AnalysisLoadingScreen({ step }) {
  const steps = Object.keys(STEP_LABELS)
  const currentIdx = steps.indexOf(step)

  return (
    <div className="min-h-screen flex flex-col items-center justify-center px-6">
      <div className="w-12 h-12 border-4 border-sky-600 border-t-transparent rounded-full animate-spin mb-6" />
      <h2 className="text-white font-semibold text-xl mb-2">Analyzing your jump...</h2>
      <p className="text-sky-400 text-sm mb-8">{STEP_LABELS[step] || 'Processing'}</p>

      <div className="w-full max-w-xs space-y-1.5">
        {steps.filter(s => s !== 'queued').map((s, i) => {
          const idx = steps.indexOf(s)
          const done = idx < currentIdx
          const active = idx === currentIdx
          return (
            <div key={s} className={`flex items-center gap-2 text-sm transition-all ${done ? 'text-green-400' : active ? 'text-sky-400' : 'text-gray-600'}`}>
              <span>{done ? '✓' : active ? '▶' : '○'}</span>
              {STEP_LABELS[s]}
            </div>
          )
        })}
      </div>
    </div>
  )
}

export default function ResultsPage() {
  const { jobId } = useParams()
  const { data, status, step, isLoading, error } = useJobResult(jobId)

  if (error) {
    return (
      <div className="min-h-screen flex flex-col items-center justify-center text-center px-6">
        <p className="text-red-400 text-lg font-semibold mb-2">Analysis Failed</p>
        <p className="text-gray-500 text-sm mb-6">{error}</p>
        <Link to="/upload" className="text-sky-400 hover:text-sky-300">← Try Again</Link>
      </div>
    )
  }

  if (isLoading) {
    return <AnalysisLoadingScreen step={step} />
  }

  return (
    <div className="min-h-screen">
      <nav className="flex items-center justify-between px-6 py-4 border-b border-gray-800">
        <Link to="/" className="text-xl font-black text-white tracking-tight">Jump<span className="text-sky-400">AI</span></Link>
        <div className="flex gap-4 text-sm">
          <Link to="/upload" className="text-gray-400 hover:text-white transition-colors">New Jump</Link>
          <Link to="/history" className="text-gray-400 hover:text-white transition-colors">History</Link>
        </div>
      </nav>

      <div className="max-w-3xl mx-auto px-6 py-10 space-y-6">
        <div>
          <h1 className="text-3xl font-black text-white mb-1">Jump Analysis</h1>
          <p className="text-gray-500 text-sm font-mono">{jobId}</p>
        </div>

        <JumpHeightDisplay
          inches={data.jump_height_inches}
          cm={data.jump_height_cm}
          score={data.scorecard?.jump_height_score}
          flightTimeMs={data.flight_time_ms}
        />

        <ScoreRadar scorecard={data.scorecard} />

        <PoseReplayViewer
          poseFrames={data.pose_frames_sample}
          jumpEvent={data.jump_event}
        />

        <AIReport report={data.claude_report} />

        <div className="flex gap-3 pt-2">
          <Link
            to="/upload"
            className="flex-1 text-center bg-sky-600 hover:bg-sky-500 text-white font-semibold py-3 rounded-xl transition-colors"
          >
            Analyze Another Jump
          </Link>
          <Link
            to="/history"
            className="flex-1 text-center bg-gray-800 hover:bg-gray-700 text-white font-semibold py-3 rounded-xl transition-colors"
          >
            View History
          </Link>
        </div>
      </div>
    </div>
  )
}
