<template>
  <n-space vertical>
    <n-card title="工作流触发">
      <n-space>
        <n-button
          v-for="w in safeWorkflows"
          :key="w.name"
          type="primary"
          secondary
          :loading="running === w.name"
          @click="runQuick(w.name)"
        >
          {{ w.name }}
        </n-button>
      </n-space>
      <n-p depth="3" style="margin-top: 12px">
        浏览器相关工作流（crawl / publish）默认不在快捷区；publish 默认 dry-run。
      </n-p>
    </n-card>

    <n-card title="自定义运行">
      <n-form label-placement="left" label-width="110">
        <n-form-item label="工作流">
          <n-select
            v-model:value="selected"
            :options="workflowOptions"
            placeholder="选择工作流"
          />
        </n-form-item>
        <n-form-item label="参数 JSON">
          <n-input
            v-model:value="paramsText"
            type="textarea"
            :rows="6"
            placeholder='{"days":30}'
          />
        </n-form-item>
        <n-form-item>
          <n-space>
            <n-button type="primary" :loading="!!running" @click="runSelected">运行</n-button>
            <n-button @click="refreshJobs">刷新任务</n-button>
          </n-space>
        </n-form-item>
      </n-form>
      <n-alert v-if="message" :type="messageType" style="margin-top: 8px">
        {{ message }}
      </n-alert>
    </n-card>

    <n-card title="最近任务">
      <n-data-table
        :columns="columns"
        :data="jobs"
        :loading="loadingJobs"
        :bordered="false"
        size="small"
      />
    </n-card>
  </n-space>
</template>

<script setup lang="ts">
import { computed, h, onMounted, ref } from 'vue'
import { NTag } from 'naive-ui'
import type { DataTableColumn } from 'naive-ui'
import { api, type WorkflowInfo, type WorkflowJob } from '../api'

const workflows = ref<WorkflowInfo[]>([])
const jobs = ref<WorkflowJob[]>([])
const loadingJobs = ref(false)
const running = ref<string | null>(null)
const selected = ref<string | null>(null)
const paramsText = ref('{}')
const message = ref('')
const messageType = ref<'success' | 'error' | 'info'>('info')

const safeWorkflows = computed(() =>
  workflows.value.filter((w) => !w.requires_browser),
)

const workflowOptions = computed(() =>
  workflows.value.map((w) => ({
    label: `${w.name}${w.requires_browser ? ' (browser)' : ''}`,
    value: w.name,
  })),
)

const statusColors: Record<string, string> = {
  pending: 'default',
  running: 'info',
  succeeded: 'success',
  failed: 'error',
}

const columns: DataTableColumn[] = [
  { title: 'ID', key: 'id', width: 120, ellipsis: true },
  { title: '工作流', key: 'workflow', width: 180 },
  {
    title: '状态',
    key: 'status',
    width: 100,
    render(row: any) {
      return h(
        NTag,
        { type: (statusColors[row.status] || 'default') as any, size: 'small' },
        () => row.status,
      )
    },
  },
  { title: '创建时间', key: 'created_at', width: 170 },
  {
    title: '错误',
    key: 'error',
    ellipsis: true,
    render(row: any) {
      return row.error || '-'
    },
  },
]

async function loadWorkflows() {
  workflows.value = await api.workflows.list()
  if (!selected.value && workflows.value.length) {
    selected.value = workflows.value[0].name
  }
}

async function refreshJobs() {
  loadingJobs.value = true
  try {
    jobs.value = await api.workflows.jobs()
  } finally {
    loadingJobs.value = false
  }
}

async function runWorkflow(name: string, params: Record<string, unknown>) {
  running.value = name
  message.value = ''
  try {
    const job = await api.workflows.run(name, params, true)
    messageType.value = 'success'
    message.value = `已提交 ${name} → job ${job.id} (${job.status})`
    await refreshJobs()
  } catch (err: any) {
    messageType.value = 'error'
    message.value = err?.message || String(err)
  } finally {
    running.value = null
  }
}

async function runQuick(name: string) {
  await runWorkflow(name, {})
}

async function runSelected() {
  if (!selected.value) return
  let params: Record<string, unknown> = {}
  try {
    params = JSON.parse(paramsText.value || '{}')
  } catch {
    messageType.value = 'error'
    message.value = '参数 JSON 无法解析'
    return
  }
  await runWorkflow(selected.value, params)
}

onMounted(async () => {
  await loadWorkflows()
  await refreshJobs()
})
</script>
