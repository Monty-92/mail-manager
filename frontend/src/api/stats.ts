import { api } from './client'

export interface EmailStats {
  total_emails: number
  emails_today: number
  unread_emails: number
  preprocessed_emails: number
  analyzed_emails: number
}

export interface TaskStats {
  active: number
  overdue: number
  due_this_week: number
  in_progress: number
}

export interface PipelineStageInfo {
  last_event: string | null
  details: Record<string, unknown>
}

export interface DashboardStats {
  emails: EmailStats
  tasks: TaskStats
  pipeline: Record<string, PipelineStageInfo>
}

export interface PipelineEvent {
  id: string
  stage: string
  email_id: string
  details: Record<string, unknown>
  occurred_at: string
}

export function getDashboardStats(): Promise<DashboardStats> {
  return api.get<DashboardStats>('/stats')
}

export function getPipelineEvents(): Promise<PipelineEvent[]> {
  return api.get<PipelineEvent[]>('/stats/pipeline')
}
