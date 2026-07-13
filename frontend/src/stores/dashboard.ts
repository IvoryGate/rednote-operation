import { defineStore } from 'pinia'
import { ref } from 'vue'
import { api, type DashboardStats } from '../api'

export const useDashboardStore = defineStore('dashboard', () => {
  const stats = ref<DashboardStats | null>(null)
  const loading = ref(false)

  async function fetchStats() {
    loading.value = true
    try {
      stats.value = await api.dashboard.stats()
    } finally {
      loading.value = false
    }
  }

  return { stats, loading, fetchStats }
})
