import { defineStore } from 'pinia'
import { ref } from 'vue'
import { api, type CompetitorSummary } from '../api'

export const useCompetitiveStore = defineStore('competitive', () => {
  const list = ref<CompetitorSummary[]>([])
  const loading = ref(false)

  async function fetchList() {
    loading.value = true
    try {
      list.value = await api.competitors.list()
    } finally {
      loading.value = false
    }
  }

  return { list, loading, fetchList }
})
