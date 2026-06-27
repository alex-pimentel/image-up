export interface Limits {
  max_upload_mb: number
  max_input_px: number
  allowed_extensions: string[]
  output_quality: number
  output_format: string
}

export type TaskStatus = 'pending' | 'processing' | 'done' | 'error'

export interface EnhanceResponse {
  task_id: string
  status: TaskStatus
}

export interface TaskResult {
  task_id: string
  status: TaskStatus
  original_filename: string | null
  original_url: string | null
  result_url: string | null
  elapsed_sec: number | null
  detail: string | null
  backend: string | null
}

export interface Health {
  status: string
  version: string
  ml_available: boolean
  backend: string
  model_name: string | null
}