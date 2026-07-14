<template>
  <n-card title="竞品列表">
    <n-data-table
      :columns="columns"
      :data="store.list"
      :loading="store.loading"
      :bordered="false"
      size="small"
    />
  </n-card>
</template>

<script setup lang="ts">
import { onMounted, h } from 'vue'
import { NTag } from 'naive-ui'
import { useCompetitiveStore } from '../stores/competitive'
import type { DataTableColumn } from 'naive-ui'

const store = useCompetitiveStore()

const columns: DataTableColumn[] = [
  { title: '名称', key: 'competitor_name', width: 180 },
  {
    title: '粉丝', key: 'followers', width: 100,
    sorter: (a: any, b: any) => a.followers - b.followers,
  },
  {
    title: '笔记数', key: 'notes_count', width: 100,
    sorter: (a: any, b: any) => a.notes_count - b.notes_count,
  },
  {
    title: '平均点赞', key: 'avg_likes', width: 100,
    sorter: (a: any, b: any) => a.avg_likes - b.avg_likes,
    render(row: any) { return h('span', row.avg_likes.toFixed(1)) },
  },
  {
    title: '分类', key: 'category', width: 120,
    render(row: any) {
      return row.category ? h(NTag, { size: 'small' }, () => row.category) : ''
    },
  },
]

onMounted(() => store.fetchList())
</script>
