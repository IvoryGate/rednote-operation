const BASE = '/api'

async function get<T>(path: string): Promise<T> {
  const res = await fetch(`${BASE}${path}`)
  if (!res.ok) throw new Error(`API error: ${res.status}`)
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
}
