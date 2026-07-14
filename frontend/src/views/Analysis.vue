<template>
  <n-grid :cols="2" :x-gap="16">
    <n-grid-item>
      <n-card title="热门关键词 Top 50">
        <n-data-table
          :columns="columns"
          :data="store.keywords"
          :loading="store.loading"
          :bordered="false"
          size="small"
          :max-height="500"
        />
      </n-card>
    </n-grid-item>
    <n-grid-item>
      <n-card title="搜索量分布（Top 20）">
        <VChart :option="chartOption" style="height: 480px" autoresize />
      </n-card>
    </n-grid-item>
  </n-grid>
</template>

<script setup lang="ts">
import { computed, onMounted } from 'vue'
import VChart from 'vue-echarts'
import 'echarts'
import { useAnalysisStore } from '../stores/analysis'
import type { DataTableColumn } from 'naive-ui'

const store = useAnalysisStore()

const columns: DataTableColumn[] = [
  { title: '#', key: 'index', width: 50, render(_: any, i: number) { return i + 1 } },
  { title: '关键词', key: 'keyword', width: 180 },
  {
    title: '搜索量', key: 'search_volume', width: 100,
    sorter: (a: any, b: any) => a.search_volume - b.search_volume,
  },
  {
    title: '竞争度', key: 'competition', width: 100,
    render(row: any) { return (row.competition * 100).toFixed(0) + '%' },
  },
  { title: '分类', key: 'category', width: 100 },
]

const chartOption = computed(() => ({
  tooltip: { trigger: 'axis' as const },
  xAxis: {
    type: 'category' as const,
    data: store.keywords.slice(0, 20).map((k: any) => k.keyword),
    axisLabel: { rotate: 45, fontSize: 10 },
  },
  yAxis: { type: 'value' as const },
  series: [
    {
      name: '搜索量',
      type: 'bar',
      data: store.keywords.slice(0, 20).map((k: any) => k.search_volume),
      itemStyle: { borderRadius: [4, 4, 0, 0] },
    },
  ],
}))

onMounted(() => store.fetchKeywords())
</script>
