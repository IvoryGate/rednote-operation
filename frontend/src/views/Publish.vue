<template>
  <n-space vertical>
    <n-card title="发布队列">
      <template #header-extra>
        <n-button-group size="small">
          <n-button
            v-for="s in statusFilters"
            :key="s.value"
            :type="store.filterStatus === s.value ? 'primary' : 'default'"
            @click="store.fetchItems(s.value)"
          >
            {{ s.label }}
          </n-button>
        </n-button-group>
      </template>

      <n-data-table
        :columns="columns"
        :data="store.items"
        :loading="store.loading"
        :bordered="false"
        size="small"
      />
    </n-card>
  </n-space>
</template>

<script setup lang="ts">
import { onMounted, h } from 'vue'
import { NTag } from 'naive-ui'
import { usePublishStore } from '../stores/publish'
import type { DataTableColumn } from 'naive-ui'

const store = usePublishStore()

const statusFilters = [
  { label: '待发布', value: 'pending' },
  { label: '已发布', value: 'published' },
  { label: '失败', value: 'failed' },
]

const statusColors: Record<string, string> = {
  pending: 'warning',
  published: 'success',
  failed: 'error',
}

const columns: DataTableColumn[] = [
  { title: 'ID', key: 'id', width: 60 },
  { title: '标题', key: 'title', width: 300, ellipsis: true },
  {
    title: '状态', key: 'status', width: 100,
    render(row: any) {
      return h(NTag, { type: statusColors[row.status] || 'default' as any, size: 'small' }, () => row.status)
    },
  },
  {
    title: '计划时间', key: 'scheduled_for', width: 160,
    render(row: any) {
      return row.scheduled_for ? new Date(row.scheduled_for).toLocaleString('zh-CN') : '-'
    },
  },
]

onMounted(() => store.fetchItems())
</script>
