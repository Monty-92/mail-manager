<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import {
  PlusIcon,
  FunnelIcon,
  CheckCircleIcon,
  ChevronDownIcon,
  ChevronRightIcon,
  TrashIcon,
  PencilSquareIcon,
  ListBulletIcon,
  Squares2X2Icon,
  EllipsisHorizontalIcon,
} from '@heroicons/vue/24/outline'
import { useTaskStore } from '@/stores/task'
import type { Task, TaskStatus, TaskPriority, CreateTaskPayload } from '@/types'
import BaseCard from '@/components/ui/BaseCard.vue'
import BaseButton from '@/components/ui/BaseButton.vue'
import BaseInput from '@/components/ui/BaseInput.vue'
import StatusBadge from '@/components/ui/StatusBadge.vue'
import EmptyState from '@/components/ui/EmptyState.vue'
import SkeletonLoader from '@/components/ui/SkeletonLoader.vue'
import { useToast } from '@/composables/useToast'

const taskStore = useTaskStore()
const toast = useToast()

const search = ref('')
const statusFilter = ref<TaskStatus | ''>('')
const priorityFilter = ref<TaskPriority | ''>('')
const selectedListId = ref<string | ''>('')
const showCreateForm = ref(false)
const expandedTasks = ref<Set<string>>(new Set())

// New task form
const newTaskTitle = ref('')
const newTaskPriority = ref<TaskPriority>('none')
const newTaskDueDate = ref('')

const filteredTasks = computed(() => {
  let result = taskStore.tasks
  if (search.value) {
    const q = search.value.toLowerCase()
    result = result.filter(
      (t) => t.title.toLowerCase().includes(q) || t.notes?.toLowerCase().includes(q),
    )
  }
  if (statusFilter.value) {
    result = result.filter((t) => t.status === statusFilter.value)
  }
  if (priorityFilter.value) {
    result = result.filter((t) => t.priority === priorityFilter.value)
  }
  return result
})

const tasksByList = computed(() => {
  const grouped = new Map<string, Task[]>()
  grouped.set('unassigned', [])
  for (const list of taskStore.taskLists) {
    grouped.set(list.id, [])
  }
  for (const task of filteredTasks.value) {
    const key = task.list_id ?? 'unassigned'
    const bucket = grouped.get(key)
    if (bucket) bucket.push(task)
    else grouped.set(key, [task])
  }
  return grouped
})

function getListName(listId: string): string {
  if (listId === 'unassigned') return 'Unassigned'
  return taskStore.taskLists.find((l) => l.id === listId)?.name ?? 'Unknown List'
}

function toggleExpanded(taskId: string) {
  if (expandedTasks.value.has(taskId)) {
    expandedTasks.value.delete(taskId)
  } else {
    expandedTasks.value.add(taskId)
  }
}

async function createTask() {
  if (!newTaskTitle.value.trim()) return
  const payload: CreateTaskPayload = {
    title: newTaskTitle.value.trim(),
    priority: newTaskPriority.value,
    due_date: newTaskDueDate.value || undefined,
    list_id: selectedListId.value || undefined,
  }
  try {
    await taskStore.createTask(payload)
    newTaskTitle.value = ''
    newTaskPriority.value = 'none'
    newTaskDueDate.value = ''
    showCreateForm.value = false
    toast.success('Task created')
  } catch (e) {
    toast.error('Failed to create task')
  }
}

async function toggleTaskStatus(task: Task) {
  const newStatus: TaskStatus = task.status === 'done' ? 'pending' : 'done'
  try {
    await taskStore.updateTask(task.id, { status: newStatus })
  } catch {
    toast.error('Failed to update task')
  }
}

async function deleteTask(taskId: string) {
  try {
    await taskStore.removeTask(taskId)
    toast.success('Task deleted')
  } catch {
    toast.error('Failed to delete task')
  }
}

function formatDueDate(date: string | null): string {
  if (!date) return ''
  const d = new Date(date)
  const now = new Date()
  const diff = d.getTime() - now.getTime()
  const days = Math.ceil(diff / (1000 * 60 * 60 * 24))
  if (days < 0) return `${Math.abs(days)}d overdue`
  if (days === 0) return 'Today'
  if (days === 1) return 'Tomorrow'
  return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
}

function isDueOverdue(date: string | null): boolean {
  if (!date) return false
  return new Date(date) < new Date()
}

onMounted(async () => {
  await Promise.all([taskStore.fetchTasks(), taskStore.fetchTaskLists()])
})
</script>

<template>
  <div class="mx-auto max-w-7xl">
    <!-- Header -->
    <div class="mb-6 flex items-center justify-between">
      <div class="flex items-center gap-3">
        <div class="w-64">
          <BaseInput v-model="search" type="search" placeholder="Search tasks..." />
        </div>

        <!-- Status filter -->
        <select
          v-model="statusFilter"
          class="rounded-lg border bg-transparent px-3 py-2 text-sm outline-none"
          :style="{
            borderColor: 'var(--color-border)',
            color: 'var(--color-text-secondary)',
          }"
        >
          <option value="">All statuses</option>
          <option value="pending">Pending</option>
          <option value="in_progress">In Progress</option>
          <option value="done">Done</option>
          <option value="cancelled">Cancelled</option>
        </select>

        <!-- Priority filter -->
        <select
          v-model="priorityFilter"
          class="rounded-lg border bg-transparent px-3 py-2 text-sm outline-none"
          :style="{
            borderColor: 'var(--color-border)',
            color: 'var(--color-text-secondary)',
          }"
        >
          <option value="">All priorities</option>
          <option value="high">High</option>
          <option value="medium">Medium</option>
          <option value="low">Low</option>
          <option value="none">None</option>
        </select>
      </div>

      <BaseButton variant="primary" @click="showCreateForm = !showCreateForm">
        <PlusIcon class="h-4 w-4" />
        New Task
      </BaseButton>
    </div>

    <!-- Create task form -->
    <Transition
      enter-active-class="transition duration-200 ease-out"
      enter-from-class="-translate-y-2 opacity-0"
      enter-to-class="translate-y-0 opacity-100"
      leave-active-class="transition duration-150 ease-in"
      leave-from-class="translate-y-0 opacity-100"
      leave-to-class="-translate-y-2 opacity-0"
    >
      <BaseCard v-if="showCreateForm" title="Create Task" class="mb-6">
        <form class="flex flex-wrap items-end gap-4" @submit.prevent="createTask">
          <div class="flex-1">
            <BaseInput
              v-model="newTaskTitle"
              placeholder="Task title..."
              label="Title"
            />
          </div>
          <div class="w-40">
            <label class="mb-1.5 block text-xs font-medium" :style="{ color: 'var(--color-text-secondary)' }">
              Priority
            </label>
            <select
              v-model="newTaskPriority"
              class="w-full rounded-lg border bg-transparent px-3 py-2 text-sm outline-none"
              :style="{ borderColor: 'var(--color-border)', color: 'var(--color-text-primary)' }"
            >
              <option value="none">None</option>
              <option value="low">Low</option>
              <option value="medium">Medium</option>
              <option value="high">High</option>
            </select>
          </div>
          <div class="w-44">
            <BaseInput v-model="newTaskDueDate" type="date" label="Due date" />
          </div>
          <div class="flex gap-2">
            <BaseButton variant="primary" type="submit">Create</BaseButton>
            <BaseButton variant="ghost" @click="showCreateForm = false">Cancel</BaseButton>
          </div>
        </form>
      </BaseCard>
    </Transition>

    <!-- Task lists -->
    <SkeletonLoader v-if="taskStore.loading" variant="list" :lines="8" />
    <EmptyState
      v-else-if="filteredTasks.length === 0 && !taskStore.loading"
      message="No tasks yet. Create one above or they'll be automatically extracted from your emails."
    >
      <template #icon>
        <CheckCircleIcon class="h-8 w-8" :style="{ color: 'var(--color-text-muted)' }" />
      </template>
    </EmptyState>

    <div v-else class="space-y-6">
      <div v-for="[listId, tasks] in tasksByList" :key="listId">
        <div v-if="tasks.length > 0">
          <h3
            class="mb-3 flex items-center gap-2 text-xs font-semibold uppercase tracking-wider"
            :style="{ color: 'var(--color-text-muted)' }"
          >
            <ListBulletIcon class="h-4 w-4" />
            {{ getListName(listId) }}
            <span
              class="rounded-full px-1.5 py-0.5 text-xs"
              :style="{ backgroundColor: 'var(--color-bg-tertiary)' }"
            >
              {{ tasks.length }}
            </span>
          </h3>

          <div class="space-y-1">
            <div
              v-for="task in tasks"
              :key="task.id"
              class="group rounded-lg border p-3 transition-all duration-150"
              :style="{
                backgroundColor: 'var(--color-bg-secondary)',
                borderColor: 'var(--color-border)',
              }"
            >
              <div class="flex items-start gap-3">
                <!-- Checkbox -->
                <button
                  class="mt-0.5 flex h-5 w-5 flex-shrink-0 items-center justify-center rounded border transition-colors"
                  :style="{
                    borderColor: task.status === 'done' ? 'var(--color-success)' : 'var(--color-border)',
                    backgroundColor: task.status === 'done' ? 'var(--color-success)' : 'transparent',
                  }"
                  @click="toggleTaskStatus(task)"
                >
                  <CheckCircleIcon
                    v-if="task.status === 'done'"
                    class="h-3.5 w-3.5 text-white"
                  />
                </button>

                <!-- Task content -->
                <div class="min-w-0 flex-1">
                  <div class="flex items-center gap-2">
                    <!-- Expand toggle for subtasks -->
                    <button
                      v-if="task.subtasks?.length"
                      class="rounded p-0.5"
                      :style="{ color: 'var(--color-text-muted)' }"
                      @click="toggleExpanded(task.id)"
                    >
                      <component
                        :is="expandedTasks.has(task.id) ? ChevronDownIcon : ChevronRightIcon"
                        class="h-3.5 w-3.5"
                      />
                    </button>
                    <p
                      class="text-sm font-medium"
                      :class="{ 'line-through opacity-50': task.status === 'done' }"
                      :style="{ color: 'var(--color-text-primary)' }"
                    >
                      {{ task.title }}
                    </p>
                  </div>
                  <div class="mt-1.5 flex flex-wrap items-center gap-2">
                    <StatusBadge variant="status" :value="task.status" />
                    <StatusBadge v-if="task.priority !== 'none'" variant="priority" :value="task.priority" />
                    <span
                      v-if="task.due_date"
                      class="text-xs"
                      :style="{
                        color: isDueOverdue(task.due_date) ? 'var(--color-error)' : 'var(--color-text-muted)',
                      }"
                    >
                      {{ formatDueDate(task.due_date) }}
                    </span>
                  </div>
                </div>

                <!-- Actions -->
                <div class="flex items-center gap-1 opacity-0 transition-opacity group-hover:opacity-100">
                  <button
                    class="rounded p-1 transition-colors hover:opacity-70"
                    :style="{ color: 'var(--color-text-muted)' }"
                    title="Delete"
                    @click="deleteTask(task.id)"
                  >
                    <TrashIcon class="h-4 w-4" />
                  </button>
                </div>
              </div>

              <!-- Subtasks -->
              <div
                v-if="expandedTasks.has(task.id) && task.subtasks?.length"
                class="ml-8 mt-3 space-y-2 border-l-2 pl-4"
                :style="{ borderColor: 'var(--color-border)' }"
              >
                <div
                  v-for="subtask in task.subtasks"
                  :key="subtask.id"
                  class="flex items-center gap-3"
                >
                  <button
                    class="flex h-4 w-4 flex-shrink-0 items-center justify-center rounded border"
                    :style="{
                      borderColor: subtask.status === 'done' ? 'var(--color-success)' : 'var(--color-border)',
                      backgroundColor: subtask.status === 'done' ? 'var(--color-success)' : 'transparent',
                    }"
                    @click="toggleTaskStatus(subtask)"
                  >
                    <CheckCircleIcon
                      v-if="subtask.status === 'done'"
                      class="h-3 w-3 text-white"
                    />
                  </button>
                  <p
                    class="text-sm"
                    :class="{ 'line-through opacity-50': subtask.status === 'done' }"
                    :style="{ color: 'var(--color-text-secondary)' }"
                  >
                    {{ subtask.title }}
                  </p>
                  <StatusBadge v-if="subtask.priority !== 'none'" variant="priority" :value="subtask.priority" />
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
