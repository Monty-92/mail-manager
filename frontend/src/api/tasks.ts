import { api } from './client'
import type {
  Task,
  TaskList,
  CreateTaskPayload,
  UpdateTaskPayload,
  CreateTaskListPayload,
  UpdateTaskListPayload,
} from '@/types'

// ─── Task Lists ───

export function listTaskLists(): Promise<TaskList[]> {
  return api.get<TaskList[]>('/tasks/lists')
}

export function createTaskList(payload: CreateTaskListPayload): Promise<TaskList> {
  return api.post<TaskList>('/tasks/lists', payload)
}

export function getTaskList(listId: string): Promise<TaskList> {
  return api.get<TaskList>(`/tasks/lists/${listId}`)
}

export function updateTaskList(listId: string, payload: UpdateTaskListPayload): Promise<TaskList> {
  return api.patch<TaskList>(`/tasks/lists/${listId}`, payload)
}

export function deleteTaskList(listId: string): Promise<void> {
  return api.delete(`/tasks/lists/${listId}`)
}

// ─── Task Extraction ───

export function extractTasks(emailId: string): Promise<Record<string, unknown>> {
  return api.post<Record<string, unknown>>(`/tasks/extract/${emailId}`)
}

export function getEmailTasks(emailId: string): Promise<Task[]> {
  return api.get<Task[]>(`/tasks/email/${emailId}`)
}

// ─── Tasks CRUD ───

export function listTasks(params?: {
  list_id?: string
  status?: string
  priority?: string
  limit?: number
  offset?: number
}): Promise<Task[]> {
  return api.get<Task[]>('/tasks', params)
}

export function createTask(payload: CreateTaskPayload): Promise<Task> {
  return api.post<Task>('/tasks', payload)
}

export function getTask(taskId: string): Promise<Task> {
  return api.get<Task>(`/tasks/${taskId}`)
}

export function updateTask(taskId: string, payload: UpdateTaskPayload): Promise<Task> {
  return api.patch<Task>(`/tasks/${taskId}`, payload)
}

export function deleteTask(taskId: string): Promise<void> {
  return api.delete(`/tasks/${taskId}`)
}
