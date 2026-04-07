import { api } from './client'
import type { CalendarAccount, CalendarEvent, CalendarSource } from '@/types'

export interface SyncCalendarResponse {
  synced: number
  provider: string
  account_email: string
}

export async function getCalendarEvents(params?: {
  start_after?: string
  end_before?: string
  provider?: string
  limit?: number
}): Promise<CalendarEvent[]> {
  return api.get<CalendarEvent[]>('/calendar/events', params)
}

export async function getCalendarSources(): Promise<CalendarAccount[]> {
  return api.get<CalendarAccount[]>('/calendar/sources')
}

export async function syncCalendar(accountId?: string): Promise<SyncCalendarResponse[]> {
  return api.post<SyncCalendarResponse[]>('/calendar/sync', accountId ? { account_id: accountId } : {})
}

export async function deleteCalendarEvent(eventId: string): Promise<void> {
  await api.delete(`/calendar/events/${eventId}`)
}
