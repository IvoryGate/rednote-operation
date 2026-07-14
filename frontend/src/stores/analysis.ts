import { defineStore } from 'pinia'
import { ref } from 'vue'
import { api, type KeywordSummary } from '../api'

export const useAnalysisStore = defineStore('analysis', () => {
  const keywords = ref<KeywordSummary[]>([])
  const loading = ref(false)

  async function fetchKeywords(top = 50) {
    loading.value = true
    try {
      keywords.value = await api.keywords.list(top)
    } finally {
      loading.value = false
    }
  }

  return { keywords, loading, fetchKeywords }
})
