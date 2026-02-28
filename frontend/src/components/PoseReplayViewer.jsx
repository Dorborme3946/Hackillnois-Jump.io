import { useRef, useEffect, useState } from 'react'

const CONNECTIONS = [
  [5, 6], [5, 7], [7, 9], [6, 8], [8, 10],   // arms
  [5, 11], [6, 12], [11, 12],                  // torso
  [11, 13], [13, 15], [12, 14], [14, 16],      // legs
  [0, 1], [0, 2], [1, 3], [2, 4],              // face
]

const KEYPOINT_NAMES = [
  'nose', 'left_eye', 'right_eye', 'left_ear', 'right_ear',
  'left_shoulder', 'right_shoulder', 'left_elbow', 'right_elbow',
  'left_wrist', 'right_wrist', 'left_hip', 'right_hip',
  'left_knee', 'right_knee', 'left_ankle', 'right_ankle',
]

function drawPose(ctx, keypoints, width, height, jumpEvent, frameIdx) {
  ctx.clearRect(0, 0, width, height)
  if (!keypoints) return

  const pts = KEYPOINT_NAMES.map(n => keypoints[n] || [0, 0, 0])

  // Draw skeleton connections
  CONNECTIONS.forEach(([a, b]) => {
    const [ax, ay, ac] = pts[a]
    const [bx, by, bc] = pts[b]
    if (ac > 0.3 && bc > 0.3) {
      ctx.beginPath()
      ctx.moveTo(ax, ay)
      ctx.lineTo(bx, by)
      ctx.strokeStyle = '#0ea5e9'
      ctx.lineWidth = 2
      ctx.stroke()
    }
  })

  // Draw keypoints
  pts.forEach(([x, y, conf]) => {
    if (conf > 0.3 && x > 0 && y > 0) {
      ctx.beginPath()
      ctx.arc(x, y, 4, 0, Math.PI * 2)
      ctx.fillStyle = '#38bdf8'
      ctx.fill()
    }
  })

  // Highlight flight phase
  if (jumpEvent) {
    const inFlight = frameIdx >= jumpEvent.takeoff_frame && frameIdx <= jumpEvent.landing_frame
    if (inFlight) {
      ctx.fillStyle = 'rgba(14, 165, 233, 0.12)'
      ctx.fillRect(0, 0, width, height)
      ctx.fillStyle = '#0ea5e9'
      ctx.font = '12px monospace'
      ctx.fillText('AIRBORNE', 8, 16)
    }
  }
}

export default function PoseReplayViewer({ poseFrames = [], jumpEvent = null }) {
  const canvasRef = useRef(null)
  const [currentFrame, setCurrentFrame] = useState(0)
  const [playing, setPlaying] = useState(false)
  const animRef = useRef(null)

  const totalFrames = poseFrames.length

  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas || !poseFrames[currentFrame]) return
    const ctx = canvas.getContext('2d')
    drawPose(ctx, poseFrames[currentFrame].keypoints, canvas.width, canvas.height, jumpEvent, poseFrames[currentFrame].frame_idx)
  }, [currentFrame, poseFrames, jumpEvent])

  useEffect(() => {
    if (!playing) {
      cancelAnimationFrame(animRef.current)
      return
    }

    let lastTime = 0
    const FPS = 30
    const interval = 1000 / FPS

    function tick(timestamp) {
      if (timestamp - lastTime >= interval) {
        lastTime = timestamp
        setCurrentFrame(f => {
          if (f >= totalFrames - 1) {
            setPlaying(false)
            return 0
          }
          return f + 1
        })
      }
      animRef.current = requestAnimationFrame(tick)
    }
    animRef.current = requestAnimationFrame(tick)
    return () => cancelAnimationFrame(animRef.current)
  }, [playing, totalFrames])

  if (!poseFrames.length) return null

  return (
    <div className="bg-gray-900 rounded-2xl p-6 border border-gray-800">
      <h2 className="text-lg font-semibold text-white mb-4">Pose Replay</h2>

      <div className="relative bg-gray-950 rounded-xl overflow-hidden aspect-[9/16] max-w-xs mx-auto">
        <canvas
          ref={canvasRef}
          width={360}
          height={640}
          className="w-full h-full"
        />
      </div>

      <div className="mt-4 space-y-2">
        <input
          type="range"
          min={0}
          max={totalFrames - 1}
          value={currentFrame}
          onChange={e => { setCurrentFrame(Number(e.target.value)); setPlaying(false) }}
          className="w-full accent-sky-500"
        />
        <div className="flex items-center justify-between">
          <span className="text-xs text-gray-500">
            Frame {currentFrame + 1}/{totalFrames} — {(poseFrames[currentFrame]?.timestamp_ms / 1000).toFixed(2)}s
          </span>
          <button
            onClick={() => setPlaying(p => !p)}
            className="px-4 py-1.5 bg-sky-600 hover:bg-sky-500 text-white text-sm rounded-lg transition-colors"
          >
            {playing ? 'Pause' : 'Play'}
          </button>
        </div>
      </div>
    </div>
  )
}
