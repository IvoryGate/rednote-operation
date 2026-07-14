import { defineStore } from 'pinia'
import { ref } from 'vue'
import { api, type NoteSummary } from '../api'

export const useContentStore = defineStore('content', () => {
  const notes = ref<NoteSummary[]>([])
  const loading = ref(false)

  async function fetchNotes(limit = 50, offset = 0) {
    loading.value = true
    try {
      notes.value = await api.notes.list(limit, offset)
    } finally {
      loading.value = false
    }
  }

  return { notes, loading, fetchNotes }
})
