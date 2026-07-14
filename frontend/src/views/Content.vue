<template>
  <n-card title="笔记列表">
    <n-data-table
      :columns="columns"
      :data="store.notes"
      :loading="store.loading"
      :bordered="false"
      size="small"
      :max-height="600"
    />
  </n-card>
</template>

<script setup lang="ts">
import { onMounted } from 'vue'
import { useContentStore } from '../stores/content'
import type { DataTableColumn } from 'naive-ui'

const store = useContentStore()

const columns: DataTableColumn[] = [
  { title: '标题', key: 'title', width: 300, ellipsis: true },
  {
    title: '❤ 点赞', key: 'like_count', width: 90,
    sorter: (a: any, b: any) => a.like_count - b.like_count,
  },
  {
    title: '🔖 收藏', key: 'collect_count', width: 90,
    sorter: (a: any, b: any) => a.collect_count - b.collect_count,
  },
  {
    title: '💬 评论', key: 'comment_count', width: 90,
    sorter: (a: any, b: any) => a.comment_count - b.comment_count,
  },
  { title: '分享', key: 'share_count', width: 80 },
  {
    title: '发布时间', key: 'published_at', width: 160,
    render(row: any) {
      return row.published_at ? new Date(row.published_at).toLocaleDateString('zh-CN') : '-'
    },
  },
]

onMounted(() => store.fetchNotes())
</script>
