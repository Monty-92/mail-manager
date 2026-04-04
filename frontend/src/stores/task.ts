import { ref, computed } from 'vue'
import { defineStore } from 'pinia'
import type { Task, TaskList, CreateTaskPayload, UpdateTaskPayload } from '@/types'
import * as tasksApi from '@/api/tasks'

export const useTaskStore = defineStore('task', () => {
  const tasks = ref<Task[]>([])
  const taskLists = ref<TaskList[]>([])
  const currentTask = ref<Task | null>(null)
  const loading = ref(false)
  const error = ref<string | null>(null)

  const overdueTasks = computed(() => {
    const now = new Date()
    return tasks.value.filter(
      (t) => t.due_date && new Date(t.due_date) < now && t.status !== 'done' && t.status !== 'cancelled',
    )
  })

  const pendingTasks = computed(() =>
    tasks.value.filter((t) => t.status === 'pending' || t.status === 'in_progress'),
  )

  const completedTasks = computed(() => tasks.value.filter((t) => t.status === 'done'))

  const upcomingTasks = computed(() => {
    const now = new Date()
    const weekFromNow = new Date(now.getTime() + 7 * 24 * 60 * 60 * 1000)
    return tasks.value.filter(
      (t) =>
        t.due_date &&
        new Date(t.due_date) >= now &&
        new Date(t.due_date) <= weekFromNow &&
        t.status !== 'done' &&
        t.status !== 'cancelled',
    )
  })

  async function fetchTasks(params?: { list_id?: string; status?: string; priority?: string; limit?: number; offset?: number }) {
    loading.value = true
    error.value = null
    try {
      tasks.value = await tasksApi.listTasks(params)
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Failed to fetch tasks'
    } finally {
      loading.value = false
    }
  }

  async function fetchTaskLists() {
    loading.value = true
    error.value = null
    try {
      taskLists.value = await tasksApi.listTaskLists()
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Failed to fetch task lists'
    } finally {
      loading.value = false
    }
  }

  async function createTask(payload: CreateTaskPayload) {
    const task = await tasksApi.createTask(payload)
    tasks.value.push(task)
    return task
  }

  async function updateTask(taskId: string, payload: UpdateTaskPayload) {
    const updated = await tasksApi.updateTask(taskId, payload)
    const idx = tasks.value.findIndex((t) => t.id === taskId)
    if (idx !== -1) tasks.value[idx] = updated
    if (currentTask.value?.id === taskId) currentTask.value = updated
    return updated
  }

  async function removeTask(taskId: string) {
    await tasksApi.deleteTask(taskId)
    tasks.value = tasks.value.filter((t) => t.id !== taskId)
    if (currentTask.value?.id === taskId) currentTask.value = null
  }

  async function fetchTask(taskId: string) {
    loading.value = true
    error.value = null
    try {
      currentTask.value = await tasksApi.getTask(taskId)
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Failed to fetch task'
    } finally {
      loading.value = false
    }
  }

  return {
    tasks,
    taskLists,
    currentTask,
    loading,
    error,
    overdueTasks,
    pendingTasks,
    completedTasks,
    upcomingTasks,
    fetchTasks,
    fetchTaskLists,
    createTask,
    updateTask,
    removeTask,
    fetchTask,
  }
})
