import { create } from 'zustand'
import { persist } from 'zustand/middleware'

const useUserStore = create(
  persist(
    (set, get) => ({
      userId: 'anonymous',
      displayName: '',
      recentJobIds: [],

      setUserId: (id) => set({ userId: id }),
      setDisplayName: (name) => set({ displayName: name }),

      addJobId: (jobId) => {
        const existing = get().recentJobIds
        const updated = [jobId, ...existing.filter(id => id !== jobId)].slice(0, 20)
        set({ recentJobIds: updated })
      },

      removeJobId: (jobId) => {
        set({ recentJobIds: get().recentJobIds.filter(id => id !== jobId) })
      },

      clearHistory: () => set({ recentJobIds: [] }),
    }),
    {
      name: 'jumpai-user',
    }
  )
)

export default useUserStore
