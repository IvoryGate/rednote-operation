<template>
  <n-layout has-sider style="height: 100vh">
    <Sidebar />
    <n-layout>
      <n-layout-header
        style="
          height: 48px;
          padding: 0 24px;
          display: flex;
          align-items: center;
          border-bottom: 1px solid var(--n-border-color);
        "
      >
        <n-h2 style="margin: 0; font-size: 16px" prefix="bar">
          {{ route.meta?.title || 'RedNote BI' }}
        </n-h2>
      </n-layout-header>
      <n-layout-content style="padding: 24px">
        <router-view />
      </n-layout-content>
    </n-layout>
  </n-layout>
</template>

<script setup lang="ts">
import { useRoute } from 'vue-router'
import Sidebar from './components/Sidebar.vue'

const route = useRoute()
</script>
