import { api } from './client'
import type { Topic } from '@/types'

export function listTopics(limit = 100, offset = 0): Promise<Topic[]> {
  return api.get<Topic[]>('/topics', { limit, offset })
}

export function getEmailTopics(emailId: string): Promise<Topic[]> {
  return api.get<Topic[]>(`/topics/email/${emailId}`)
}

export function assignTopics(emailId: string): Promise<Topic[]> {
  return api.post<Topic[]>(`/topics/assign/${emailId}`)
}

export function getTopic(topicId: string): Promise<Topic> {
  return api.get<Topic>(`/topics/${topicId}`)
}

export function deleteTopic(topicId: string): Promise<void> {
  return api.delete(`/topics/${topicId}`)
}

export function getTopicEmails(topicId: string, limit = 100): Promise<string[]> {
  return api.get<string[]>(`/topics/${topicId}/emails`, { limit })
}
