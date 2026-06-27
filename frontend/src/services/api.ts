import type { EnhanceResponse, Health, Limits, TaskResult } from '../types'

const API_BASE = import.meta.env.VITE_API_BASE || ''

const json = async <T>(res: Response): Promise<T> => {
  if (!res.ok) {
    let detail = res.statusText
    try {
      const data = await res.json()
      detail = data?.detail || detail
    } catch {
      /* ignore */
    }
    throw new Error(detail)
  }
  return res.json()
}

export const api = {
  async getHealth(): Promise<Health> {
    return json<Health>(await fetch(`${API_BASE}/api/health`))
  },

  async getConfig(): Promise<Limits> {
    return json<Limits>(await fetch(`${API_BASE}/api/config`))
  },

  async enhance(file: File, scale = 4): Promise<EnhanceResponse> {
    const form = new FormData()
    form.append('file', file)
    const res = await fetch(`${API_BASE}/api/enhance?scale=${scale}`, { method: 'POST', body: form })
    return json<EnhanceResponse>(res)
  },

  async getStatus(taskId: string): Promise<TaskResult> {
    return json<TaskResult>(await fetch(`${API_BASE}/api/status/${taskId}`))
  },

  pollStatus(taskId: string, onUpdate: (r: TaskResult) => void, intervalMs = 1500): () => void {
    let stopped = false
    const timer = setInterval(async () => {
      if (stopped) return
      try {
        const r = await api.getStatus(taskId)
        onUpdate(r)
        if (r.status === 'done' || r.status === 'error') {
          stopped = true
          clearInterval(timer)
        }
      } catch (e) {
        stopped = true
        clearInterval(timer)
        onUpdate({ task_id: taskId, status: 'error', original_filename: null, original_url: null, result_url: null, elapsed_sec: null, detail: String(e), backend: null })
      }
    }, intervalMs)
    return () => {
      stopped = true
      clearInterval(timer)
    }
  },

  asset(url: string | null): string | null {
    if (!url) return null
    return `${API_BASE}${url}`
  },
}