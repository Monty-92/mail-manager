import { api } from './client'
import type { Summary } from '@/types'

export function listSummaries(limit = 30, offset = 0): Promise<Summary[]> {
  return api.get<Summary[]>('/summaries', { limit, offset })
}

export function getDailySummary(summaryType: string, date: string): Promise<Summary> {
  return api.get<Summary>('/summaries/daily', { summary_type: summaryType, date })
}

export function generateDailySummary(summaryType: string, date: string): Promise<Summary> {
  return api.post<Summary>(`/summaries/daily?summary_type=${summaryType}&date=${date}`)
}

export function summarizeThread(threadId: string): Promise<Summary> {
  return api.post<Summary>(`/summaries/thread/${threadId}`)
}

export function getSummary(summaryId: string): Promise<Summary> {
  return api.get<Summary>(`/summaries/${summaryId}`)
}
