import { api } from './client'

export interface SetupStatusResponse {
  is_setup_complete: boolean
}

export interface SetupRequest {
  username: string
  password: string
}

export interface SetupResponse {
  username: string
  totp_uri: string
}

export interface LoginRequest {
  username: string
  password: string
}

export interface LoginResponse {
  requires_totp: boolean
  challenge_token: string
}

export interface TotpVerifyRequest {
  challenge_token: string
  totp_code: string
}

export interface TotpVerifyResponse {
  token: string
  username: string
}

export interface MeResponse {
  user_id: string
  username: string
}

export async function getSetupStatus(): Promise<SetupStatusResponse> {
  return api.get<SetupStatusResponse>('/auth/setup-status')
}

export async function setupAccount(req: SetupRequest): Promise<SetupResponse> {
  return api.post<SetupResponse>('/auth/setup', req)
}

export async function login(req: LoginRequest): Promise<LoginResponse> {
  return api.post<LoginResponse>('/auth/login', req)
}

export async function verifyTotp(req: TotpVerifyRequest): Promise<TotpVerifyResponse> {
  return api.post<TotpVerifyResponse>('/auth/verify-totp', req)
}

export async function getMe(): Promise<MeResponse> {
  return api.get<MeResponse>('/auth/me')
}

export function getSetupQrUrl(username: string, secret: string): string {
  return `/api/v1/auth/setup-qr?username=${encodeURIComponent(username)}&secret=${encodeURIComponent(secret)}`
}
