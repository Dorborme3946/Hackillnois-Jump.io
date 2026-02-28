import { useState } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import VideoUploader from '../components/VideoUploader'
import { api } from '../api/client'
import useUserStore from '../stores/userStore'

export default function UploadPage() {
  const [readyFile, setReadyFile] = useState(null)
  const [uploading, setUploading] = useState(false)
  const [error, setError] = useState(null)
  const navigate = useNavigate()
  const { userId, addJobId } = useUserStore()

  async function handleSubmit() {
    if (!readyFile) return
    setUploading(true)
    setError(null)

    try {
      const job = await api.uploadVideo(readyFile, userId)
      addJobId(job.job_id)
      navigate(`/results/${job.job_id}`)
    } catch (err) {
      setError(err.message || 'Upload failed. Please try again.')
      setUploading(false)
    }
  }

  return (
    <div className="min-h-screen">
      <nav className="flex items-center justify-between px-6 py-4 border-b border-gray-800">
        <Link to="/" className="text-xl font-black text-white tracking-tight">Jump<span className="text-sky-400">AI</span></Link>
        <Link to="/history" className="text-sm text-gray-400 hover:text-white transition-colors">History</Link>
      </nav>

      <div className="max-w-xl mx-auto px-6 py-12">
        <h1 className="text-3xl font-black text-white mb-2">Upload Your Jump</h1>
        <p className="text-gray-400 mb-8">Film in landscape or portrait. Make sure your full body is visible.</p>

        <VideoUploader onFileReady={setReadyFile} disabled={uploading} />

        {error && (
          <div className="mt-4 bg-red-500/10 border border-red-500/30 text-red-400 rounded-xl px-4 py-3 text-sm">
            {error}
          </div>
        )}

        <button
          onClick={handleSubmit}
          disabled={!readyFile || uploading}
          className="mt-6 w-full bg-sky-600 hover:bg-sky-500 disabled:opacity-40 disabled:cursor-not-allowed text-white font-semibold text-lg px-6 py-4 rounded-2xl transition-colors"
        >
          {uploading ? 'Uploading...' : 'Analyze Jump →'}
        </button>

        <div className="mt-6 bg-gray-900 rounded-xl p-4 border border-gray-800">
          <p className="text-gray-400 text-sm font-semibold mb-2">Tips for best results</p>
          <ul className="text-gray-500 text-sm space-y-1 list-disc list-inside">
            <li>Film from the side (perpendicular to your jump direction)</li>
            <li>Ensure your full body is in frame — especially ankles</li>
            <li>Good lighting, contrasting background</li>
            <li>At least 30 FPS (slow-motion works too)</li>
            <li>No objects in hands (basketball etc. may reduce accuracy)</li>
          </ul>
        </div>
      </div>
    </div>
  )
}
