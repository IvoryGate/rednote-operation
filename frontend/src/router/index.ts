import { createRouter, createWebHistory } from 'vue-router'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/',
      name: 'dashboard',
      component: () => import('../views/Dashboard.vue'),
      meta: { title: '运营看板' },
    },
    {
      path: '/competitive',
      name: 'competitive',
      component: () => import('../views/Competitive.vue'),
      meta: { title: '竞品调研' },
    },
    {
      path: '/content',
      name: 'content',
      component: () => import('../views/Content.vue'),
      meta: { title: '内容管理' },
    },
    {
      path: '/publish',
      name: 'publish',
      component: () => import('../views/Publish.vue'),
      meta: { title: '发布管理' },
    },
    {
      path: '/analysis',
      name: 'analysis',
      component: () => import('../views/Analysis.vue'),
      meta: { title: '数据分析' },
    },
    {
      path: '/workflows',
      name: 'workflows',
      component: () => import('../views/Workflows.vue'),
      meta: { title: '工作流' },
    },
  ],
})

export default router
