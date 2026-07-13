<template>
  <n-grid :cols="4" :x-gap="16" :y-gap="16">
    <n-grid-item>
      <StatCard title="发布笔记" :value="stats?.total_notes ?? 0" unit="篇" />
    </n-grid-item>
    <n-grid-item>
      <StatCard title="获赞总数" :value="stats?.total_likes ?? 0" unit="个" />
    </n-grid-item>
    <n-grid-item>
      <StatCard title="粉丝总数" :value="stats?.total_followers ?? 0" unit="人" />
    </n-grid-item>
    <n-grid-item>
      <StatCard title="本周发布" :value="stats?.total_published ?? 0" unit="篇" />
    </n-grid-item>
  </n-grid>

  <n-card title="发布趋势" style="margin-top: 16px">
    <VChart :option="chartOption" style="height: 360px" autoresize />
  </n-card>
</template>

<script setup lang="ts">
import { computed, onMounted } from 'vue'
import VChart from 'vue-echarts'
import 'echarts'
import { useDashboardStore } from '../stores/dashboard'

const store = useDashboardStore()
const stats = computed(() => store.stats)

const chartOption = computed(() => ({
  tooltip: { trigger: 'axis' as const },
  xAxis: {
    type: 'category' as const,
    data: stats.value?.daily_stats?.map((d) => d.date) ?? [],
  },
  yAxis: { type: 'value' as const },
  series: [
    {
      name: '点赞',
      type: 'line',
      smooth: true,
      data: stats.value?.daily_stats?.map((d) => d.likes) ?? [],
      areaStyle: {},
    },
    {
      name: '笔记',
      type: 'bar',
      data: stats.value?.daily_stats?.map((d) => d.notes) ?? [],
    },
  ],
}))

onMounted(() => store.fetchStats())
</script>
