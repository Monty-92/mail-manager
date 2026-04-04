import { api } from './client'
import type { EmailAnalysis } from '@/types'

export function getAnalysis(emailId: string): Promise<EmailAnalysis> {
  return api.get<EmailAnalysis>(`/analyze/${emailId}`)
}

export function analyzeBatch(limit = 50): Promise<Record<string, unknown>> {
  return api.post<Record<string, unknown>>(`/analyze/batch?limit=${limit}`)
}

export function analyzeEmail(emailId: string): Promise<EmailAnalysis> {
  return api.post<EmailAnalysis>(`/analyze/${emailId}`)
}
