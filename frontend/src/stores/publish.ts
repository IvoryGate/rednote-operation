import { defineStore } from 'pinia'
import { ref } from 'vue'
import { api, type QueueItem } from '../api'

export const usePublishStore = defineStore('publish', () => {
  const items = ref<QueueItem[]>([])
  const loading = ref(false)
  const filterStatus = ref('pending')

  async function fetchItems(status = 'pending') {
    filterStatus.value = status
    loading.value = true
    try {
      items.value = await api.queue.list(status)
    } finally {
      loading.value = false
    }
  }

  return { items, loading, filterStatus, fetchItems }
})
