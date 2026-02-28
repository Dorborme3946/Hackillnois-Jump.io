import { useState, useCallback } from 'react'

const MIN_WIDTH = 854
const MIN_HEIGHT = 480
const MAX_DURATION_SEC = 60
const MIN_DURATION_SEC = 0.5
const SUPPORTED_FORMATS = ['video/mp4', 'video/quicktime', 'video/avi', 'video/webm']
const MAX_SIZE_MB = 500

/**
 * Client-side video file validation (mirrors backend constraints).
 * Returns { validate(file) => Promise<{ok, errors, warnings}> }
 */
export function useVideoValidation() {
  const [validationResult, setValidationResult] = useState(null)

  const validate = useCallback((file) => {
    return new Promise((resolve) => {
      const errors = []
      const warnings = []

      if (!file) {
        resolve({ ok: false, errors: ['No file provided.'], warnings: [] })
        return
      }

      // Size check
      const sizeMb = file.size / (1024 * 1024)
      if (sizeMb > MAX_SIZE_MB) {
        errors.push(`File too large: ${sizeMb.toFixed(0)} MB (max ${MAX_SIZE_MB} MB)`)
      }

      // Format check
      if (!SUPPORTED_FORMATS.includes(file.type)) {
        errors.push(`Unsupported format: ${file.type || 'unknown'}. Use MP4, MOV, AVI, or WebM.`)
      }

      // Duration / resolution via HTMLVideoElement
      const url = URL.createObjectURL(file)
      const video = document.createElement('video')
      video.preload = 'metadata'

      video.onloadedmetadata = () => {
        URL.revokeObjectURL(url)
        const { videoWidth: w, videoHeight: h, duration } = video

        const effectiveW = Math.max(w, h)
        const effectiveH = Math.min(w, h)

        if (effectiveH < MIN_HEIGHT || effectiveW < MIN_WIDTH) {
          errors.push(`Resolution too low: ${w}×${h}. Minimum: 480p (854×480).`)
        }

        if (duration < MIN_DURATION_SEC) {
          errors.push(`Video too short: ${duration.toFixed(1)}s. Minimum: ${MIN_DURATION_SEC}s.`)
        }

        if (duration > MAX_DURATION_SEC) {
          warnings.push(`Long video: ${duration.toFixed(0)}s. Processing may take a while.`)
        }

        const result = { ok: errors.length === 0, errors, warnings }
        setValidationResult(result)
        resolve(result)
      }

      video.onerror = () => {
        URL.revokeObjectURL(url)
        errors.push('Could not read video file. It may be corrupted.')
        const result = { ok: false, errors, warnings }
        setValidationResult(result)
        resolve(result)
      }

      video.src = url
    })
  }, [])

  return { validate, validationResult }
}
