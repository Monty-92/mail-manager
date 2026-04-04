import { api } from './client'

export function preprocessBatch(limit = 50): Promise<Record<string, unknown>> {
  return api.post<Record<string, unknown>>(`/preprocess/batch?limit=${limit}`)
}

export function preprocessEmail(emailId: string): Promise<Record<string, unknown>> {
  return api.post<Record<string, unknown>>(`/preprocess/${emailId}`)
}
