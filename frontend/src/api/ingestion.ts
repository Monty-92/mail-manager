import { api } from './client'
import type { AuthUrlResponse, SyncResponse, FetchResponse } from '@/types'

export function getAuthUrl(provider: string): Promise<AuthUrlResponse> {
  return api.get<AuthUrlResponse>(`/ingest/auth/url/${provider}`)
}

export function authCallback(body: { provider: string; code: string; redirect_uri: string }): Promise<Record<string, unknown>> {
  return api.post<Record<string, unknown>>('/ingest/auth/callback', body)
}

export function syncProvider(provider: string, maxResults = 100): Promise<SyncResponse> {
  return api.post<SyncResponse>(`/ingest/sync/${provider}`, undefined, { max_results: maxResults })
}

export function fetchProvider(provider: string, maxResults = 500, pageToken?: string): Promise<FetchResponse> {
  return api.post<FetchResponse>(`/ingest/fetch/${provider}`, undefined, {
    max_results: maxResults,
    ...(pageToken ? { page_token: pageToken } : {}),
  })
}
