<template>
  <n-layout-sider bordered>
    <div
      style="
        height: 48px;
        display: flex;
        align-items: center;
        padding: 0 16px;
        font-weight: 600;
        border-bottom: 1px solid var(--n-border-color);
      "
    >
      RedNote BI
    </div>
    <n-menu
      :value="activeKey"
      :collapsed-width="64"
      :collapsed-icon-size="20"
      :options="menuOptions"
      @update:value="handleMenuSelect"
    />
  </n-layout-sider>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { h } from 'vue'

const router = useRouter()
const route = useRoute()

const activeKey = computed(() => route.name as string)

const iconRender = (emoji: string) => () => h('span', null, emoji)

const menuOptions = [
  { label: '运营看板', key: 'dashboard', icon: iconRender('📊') },
  { label: '竞品调研', key: 'competitive', icon: iconRender('🔍') },
  { label: '内容管理', key: 'content', icon: iconRender('📝') },
  { label: '发布管理', key: 'publish', icon: iconRender('🚀') },
  { label: '数据分析', key: 'analysis', icon: iconRender('📈') },
]

function handleMenuSelect(key: string) {
  router.push({ name: key })
}
</script>
