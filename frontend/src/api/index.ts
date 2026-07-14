const BASE = '/api'
const TOKEN_KEY = 'rednote_api_token'

export function getApiToken(): string {
  try {
    return localStorage.getItem(TOKEN_KEY) || ''
  } catch {
    return ''
  }
}

export function setApiToken(token: string): void {
  try {
    if (token.trim()) localStorage.setItem(TOKEN_KEY, token.trim())
    else localStorage.removeItem(TOKEN_KEY)
  } catch {
    // Ignore storage failures (private mode / SSR).
  }
}

function authHeaders(includeJson = false): Record<string, string> {
  const headers: Record<string, string> = {}
  if (includeJson) headers['Content-Type'] = 'application/json'
  const token = getApiToken()
  if (token) {
    headers.Authorization = `Bearer ${token}`
    headers['X-API-Token'] = token
  }
  return headers
}

async function get<T>(path: string): Promise<T> {
  const res = await fetch(`${BASE}${path}`, { headers: authHeaders() })
  if (!res.ok) throw new Error(`API error: ${res.status}`)
  return res.json()
}

async function post<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    method: 'POST',
    headers: authHeaders(true),
    body: JSON.stringify(body ?? {}),
  })
  if (!res.ok) {
    const detail = await res.text()
    throw new Error(`API error: ${res.status} ${detail}`)
  }
  return res.json()
}

export interface DashboardStats {
  total_notes: number
  total_likes: number
  total_followers: number
  total_published: number
  daily_stats: Array<{ date: string; likes: number; notes: number }>
}

export interface CompetitorSummary {
  id: number
  competitor_name: string
  followers: number
  notes_count: number
  avg_likes: number
}

export interface QueueItem {
  id: number
  title: string
  status: string
  scheduled_for: string
}

export interface NoteSummary {
  id: number
  title: string
  like_count: number
  collect_count: number
  comment_count: number
  share_count: number
  published_at: string | null
}

export interface KeywordSummary {
  keyword: string
  search_volume: number
  competition: number
  category: string
}

export interface WorkflowInfo {
  name: string
  description: string
  requires_browser: boolean
  default_params: Record<string, unknown>
}

export interface WorkflowJob {
  id: string
  workflow: string
  status: string
  params: Record<string, unknown>
  created_at: string
  started_at: string | null
  finished_at: string | null
  returncode: number | null
  stdout: string
  stderr: string
  error: string | null
  requires_browser: boolean
}

export const api = {
  dashboard: {
    stats: () => get<DashboardStats>('/dashboard/stats'),
  },
  competitors: {
    list: () => get<CompetitorSummary[]>('/competitors'),
  },
  queue: {
    list: (status = 'pending') =>
      get<QueueItem[]>(`/queue?status=${status}`),
  },
  notes: {
    list: (limit = 50, offset = 0) =>
      get<NoteSummary[]>(`/notes?limit=${limit}&offset=${offset}`),
  },
  keywords: {
    list: (top = 50) =>
      get<KeywordSummary[]>(`/keywords?top=${top}`),
  },
  workflows: {
    list: () => get<WorkflowInfo[]>('/workflows'),
    run: (name: string, params: Record<string, unknown> = {}, background = true) =>
      post<WorkflowJob>(`/workflows/${name}/run`, { params, background }),
    jobs: (limit = 50) => get<WorkflowJob[]>(`/workflows/jobs?limit=${limit}`),
    job: (id: string) => get<WorkflowJob>(`/workflows/jobs/${id}`),
  },
}
