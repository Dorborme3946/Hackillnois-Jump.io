import { useState, useEffect } from 'react'
import { api } from '../api/client'

/**
 * Fetch and return a user's jump history + aggregate stats.
 */
export function useUserHistory(userId, limit = 10) {
  const [history, setHistory] = useState([])
  const [stats, setStats] = useState(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    if (!userId) return

    let cancelled = false
    setIsLoading(true)
    setError(null)

    Promise.all([
      api.getUserHistory(userId, limit),
      api.getUserStats(userId),
    ])
      .then(([historyRes, statsRes]) => {
        if (cancelled) return
        setHistory(historyRes.results || [])
        setStats(statsRes.stats || null)
        setIsLoading(false)
      })
      .catch(err => {
        if (!cancelled) {
          setError(err.message)
          setIsLoading(false)
        }
      })

    return () => { cancelled = true }
  }, [userId, limit])

  return { history, stats, isLoading, error }
}
