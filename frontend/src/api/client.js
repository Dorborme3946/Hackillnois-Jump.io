/**
 * API client — thin wrapper around fetch for all backend calls.
 */

const BASE_URL = '/api'

async function request(path, options = {}) {
  const res = await fetch(`${BASE_URL}${path}`, {
    headers: { 'Content-Type': 'application/json', ...options.headers },
    ...options,
  })

  if (!res.ok) {
    const body = await res.json().catch(() => ({}))
    throw new Error(body.detail || `HTTP ${res.status}`)
  }

  // 202 Accepted means job still processing — return partial data
  if (res.status === 202) {
    return res.json()
  }

  return res.json()
}

export const api = {
  /**
   * Upload a video file and start analysis.
   * @param {File} file
   * @param {string} userId
   * @returns {Promise<{job_id: string, status: string}>}
   */
  uploadVideo(file, userId = 'anonymous') {
    const form = new FormData()
    form.append('file', file)
    form.append('user_id', userId)
    return fetch(`${BASE_URL}/upload`, { method: 'POST', body: form })
      .then(res => res.json())
  },

  /**
   * Poll job status.
   * @param {string} jobId
   */
  getJobStatus(jobId) {
    return request(`/jobs/${jobId}`)
  },

  /**
   * Get full analysis result (only available when job.status === 'done').
   * @param {string} jobId
   */
  getResult(jobId) {
    return request(`/results/${jobId}`)
  },

  /**
   * Get paginated jump history for a user.
   */
  getUserHistory(userId, limit = 10) {
    return request(`/users/${userId}/history?limit=${limit}`)
  },

  /**
   * Get aggregate stats for a user.
   */
  getUserStats(userId) {
    return request(`/users/${userId}/stats`)
  },

  /**
   * Delete a video from storage.
   */
  deleteVideo(jobId) {
    return request(`/videos/${jobId}`, { method: 'DELETE' })
  },

  /**
   * Health check.
   */
  health() {
    return request('/health')
  },
}
