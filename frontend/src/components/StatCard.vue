<template>
  <n-card :title="title" size="small">
    <n-statistic :value="value" :precision="precision">
      <template #suffix>
        <n-text depth="3" style="font-size: 14px">{{ unit }}</n-text>
      </template>
    </n-statistic>
  </n-card>
</template>

<script setup lang="ts">
defineProps<{
  title: string
  value: number
  unit?: string
  precision?: number
}>()
</script>
