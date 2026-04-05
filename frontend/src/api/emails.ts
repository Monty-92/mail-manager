import { api } from './client'
import type { Email, PaginationParams } from '@/types'

export interface EmailListResponse {
  emails: Email[]
  total: number
  limit: number
  offset: number
}

export interface EmailListParams extends PaginationParams {
  provider?: string
  search?: string
}

export async function getEmails(params?: EmailListParams): Promise<EmailListResponse> {
  return api.get<EmailListResponse>('/emails', params as Record<string, string | number | undefined>)
}

export async function getEmail(emailId: string): Promise<Email> {
  return api.get<Email>(`/emails/${emailId}`)
}
