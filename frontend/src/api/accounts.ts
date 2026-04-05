import { api } from './client'

export interface ConnectedAccount {
  id: string
  provider: 'gmail' | 'outlook'
  email: string
  display_name: string
  scopes: string[]
  created_at: string
  updated_at: string
}

export interface AuthUrlResponse {
  auth_url: string
  provider: string
}

export interface AuthCallbackResponse {
  provider: string
  email: string
  account_id: string
}

export interface DeviceFlowStartResponse {
  device_code: string
  user_code: string
  verification_uri: string
  verification_uri_complete: string | null
  expires_in: number
  interval: number
}

export interface DeviceFlowPollResponse {
  status: 'pending' | 'complete' | 'expired'
  account_id: string | null
  email: string | null
}

export async function getAccounts(): Promise<ConnectedAccount[]> {
  return api.get<ConnectedAccount[]>('/accounts')
}

export async function disconnectAccount(id: string): Promise<void> {
  await api.delete(`/accounts/${id}`)
}

export async function getAuthUrl(provider: string): Promise<AuthUrlResponse> {
  return api.get<AuthUrlResponse>(`/accounts/auth/url/${provider}`)
}

export async function authCallback(code: string, provider: string, state?: string): Promise<AuthCallbackResponse> {
  return api.post<AuthCallbackResponse>('/accounts/auth/callback', { code, provider, state })
}

export async function startDeviceFlow(provider: string): Promise<DeviceFlowStartResponse> {
  return api.post<DeviceFlowStartResponse>(`/accounts/auth/device/${provider}`)
}

export async function pollDeviceFlow(provider: string, deviceCode: string): Promise<DeviceFlowPollResponse> {
  return api.post<DeviceFlowPollResponse>(
    `/accounts/auth/device/${provider}/poll?device_code=${encodeURIComponent(deviceCode)}`
  )
}
