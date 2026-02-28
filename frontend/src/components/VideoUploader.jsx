import { useState, useRef } from 'react'
import { useVideoValidation } from '../hooks/useVideoValidation'

export default function VideoUploader({ onFileReady, disabled = false }) {
  const [dragging, setDragging] = useState(false)
  const [selectedFile, setSelectedFile] = useState(null)
  const [validating, setValidating] = useState(false)
  const inputRef = useRef(null)
  const { validate, validationResult } = useVideoValidation()

  async function handleFile(file) {
    setSelectedFile(file)
    setValidating(true)
    const result = await validate(file)
    setValidating(false)
    if (result.ok) {
      onFileReady?.(file)
    }
  }

  function handleDrop(e) {
    e.preventDefault()
    setDragging(false)
    const file = e.dataTransfer.files[0]
    if (file) handleFile(file)
  }

  function handleInputChange(e) {
    const file = e.target.files[0]
    if (file) handleFile(file)
  }

  return (
    <div className="space-y-4">
      <div
        className={`
          border-2 border-dashed rounded-2xl p-10 text-center cursor-pointer transition-all
          ${dragging ? 'border-sky-500 bg-sky-500/10' : 'border-gray-700 hover:border-gray-500'}
          ${disabled ? 'opacity-50 pointer-events-none' : ''}
        `}
        onDragOver={e => { e.preventDefault(); setDragging(true) }}
        onDragLeave={() => setDragging(false)}
        onDrop={handleDrop}
        onClick={() => inputRef.current?.click()}
      >
        <input
          ref={inputRef}
          type="file"
          accept="video/mp4,video/quicktime,video/webm,video/avi"
          className="hidden"
          onChange={handleInputChange}
        />

        <div className="text-5xl mb-4">🎥</div>
        <p className="text-white font-semibold text-lg mb-1">
          {selectedFile ? selectedFile.name : 'Drop your jump video here'}
        </p>
        <p className="text-gray-500 text-sm">
          MP4, MOV, AVI, WebM · Min 480p · Min 30 FPS · Max 500 MB
        </p>
      </div>

      {validating && (
        <p className="text-sky-400 text-sm text-center animate-pulse">Checking video...</p>
      )}

      {validationResult && !validating && (
        <div className="space-y-1">
          {validationResult.errors.map((err, i) => (
            <p key={i} className="text-red-400 text-sm flex items-center gap-2">
              <span>✕</span> {err}
            </p>
          ))}
          {validationResult.warnings.map((w, i) => (
            <p key={i} className="text-yellow-400 text-sm flex items-center gap-2">
              <span>⚠</span> {w}
            </p>
          ))}
          {validationResult.ok && (
            <p className="text-green-400 text-sm flex items-center gap-2">
              <span>✓</span> Video looks good — ready to analyze
            </p>
          )}
        </div>
      )}
    </div>
  )
}
