import { api } from './client'

export function getSettings(): Promise<Record<string, string>> {
  return api.get<Record<string, string>>('/settings')
}

export function updateSetting(key: string, value: string): Promise<void> {
  return api.patch<void>(`/settings/${key}`, { value })
}

export function bulkUpdateSettings(settings: Record<string, string>): Promise<void> {
  return api.put<void>('/settings', settings)
}
