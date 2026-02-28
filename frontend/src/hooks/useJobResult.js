import { useState, useEffect, useRef } from 'react'
import { api } from '../api/client'

const POLL_INTERVAL_MS = 2000
const MAX_POLLS = 120  // 4 minutes max

/**
 * Poll a job until done, then fetch the full result.
 * Returns { data, status, step, isLoading, error }
 */
export function useJobResult(jobId) {
  const [data, setData] = useState(null)
  const [status, setStatus] = useState('pending')
  const [step, setStep] = useState('queued')
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState(null)
  const pollCount = useRef(0)

  useEffect(() => {
    if (!jobId) return

    let cancelled = false
    let timer = null

    async function poll() {
      try {
        const job = await api.getJobStatus(jobId)
        if (cancelled) return

        setStatus(job.status)
        setStep(job.step || '')

        if (job.status === 'done') {
          const result = await api.getResult(jobId)
          if (!cancelled) {
            setData(result)
            setIsLoading(false)
          }
        } else if (job.status === 'failed') {
          setError(job.error || 'Analysis failed.')
          setIsLoading(false)
        } else if (pollCount.current < MAX_POLLS) {
          pollCount.current++
          timer = setTimeout(poll, POLL_INTERVAL_MS)
        } else {
          setError('Analysis timed out. Please try again.')
          setIsLoading(false)
        }
      } catch (err) {
        if (!cancelled) {
          setError(err.message)
          setIsLoading(false)
        }
      }
    }

    poll()

    return () => {
      cancelled = true
      if (timer) clearTimeout(timer)
    }
  }, [jobId])

  return { data, status, step, isLoading, error }
}
