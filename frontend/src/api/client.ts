import type { ApiError } from '@/types'

const API_BASE = '/api/v1'
const TOKEN_KEY = 'mm_auth_token'

class ApiClient {
  private async request<T>(path: string, options: RequestInit = {}): Promise<T> {
    const url = `${API_BASE}${path}`
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
      ...((options.headers as Record<string, string>) ?? {}),
    }

    const token = localStorage.getItem(TOKEN_KEY)
    if (token) {
      headers['Authorization'] = `Bearer ${token}`
    }

    const response = await fetch(url, { ...options, headers })

    if (response.status === 401) {
      const currentPath = window.location.pathname
      if (currentPath !== '/login' && currentPath !== '/setup') {
        localStorage.removeItem(TOKEN_KEY)
        window.location.href = '/login'
      }
    }

    if (!response.ok) {
      let detail = `HTTP ${response.status}`
      try {
        const error = (await response.json()) as ApiError
        detail = error.detail ?? detail
      } catch {
        // response wasn't JSON
      }
      throw new Error(detail)
    }

    if (response.status === 204) {
      return undefined as T
    }

    return response.json() as Promise<T>
  }

  async get<T>(path: string, params?: Record<string, string | number | boolean | undefined>): Promise<T> {
    let url = path
    if (params) {
      const filtered = Object.entries(params).filter(([, v]) => v !== undefined)
      if (filtered.length > 0) {
        const searchParams = new URLSearchParams()
        for (const [key, value] of filtered) {
          searchParams.set(key, String(value))
        }
        url = `${path}?${searchParams.toString()}`
      }
    }
    return this.request<T>(url)
  }

  async post<T>(path: string, body?: unknown): Promise<T> {
    return this.request<T>(path, {
      method: 'POST',
      body: body !== undefined ? JSON.stringify(body) : undefined,
    })
  }

  async patch<T>(path: string, body: unknown): Promise<T> {
    return this.request<T>(path, {
      method: 'PATCH',
      body: JSON.stringify(body),
    })
  }

  async put<T>(path: string, body: unknown): Promise<T> {
    return this.request<T>(path, {
      method: 'PUT',
      body: JSON.stringify(body),
    })
  }

  async delete(path: string): Promise<void> {
    return this.request<void>(path, { method: 'DELETE' })
  }
}

export const api = new ApiClient()
