<script setup lang="ts">
import { onMounted, computed, ref } from 'vue'
import {
  EnvelopeIcon,
  ClipboardDocumentListIcon,
  TagIcon,
  ExclamationTriangleIcon,
  ClockIcon,
  CalendarDaysIcon,
  ArrowPathIcon,
  SunIcon,
  MoonIcon,
} from '@heroicons/vue/24/outline'
import { useTaskStore } from '@/stores/task'
import { useSummaryStore } from '@/stores/summary'
import { useTopicStore } from '@/stores/topic'
import { useMarkdown } from '@/composables/useMarkdown'
import BaseCard from '@/components/ui/BaseCard.vue'
import StatCard from '@/components/ui/StatCard.vue'
import StatusBadge from '@/components/ui/StatusBadge.vue'
import SkeletonLoader from '@/components/ui/SkeletonLoader.vue'
import EmptyState from '@/components/ui/EmptyState.vue'
import BaseButton from '@/components/ui/BaseButton.vue'
import { getDashboardStats } from '@/api/stats'
import type { DashboardStats } from '@/api/stats'

const taskStore = useTaskStore()
const summaryStore = useSummaryStore()
const topicStore = useTopicStore()
const { renderMarkdown } = useMarkdown()

const stats = ref<DashboardStats | null>(null)

const today = computed(() => new Date().toISOString().split('T')[0])

const todayMorning = computed(() =>
  summaryStore.summaries.find(
    (s) => s.summary_type === 'morning' && s.date === today.value,
  ),
)

const todayEvening = computed(() =>
  summaryStore.summaries.find(
    (s) => s.summary_type === 'evening' && s.date === today.value,
  ),
)

function formatDueDate(date: string | null): string {
  if (!date) return 'No due date'
  const d = new Date(date)
  const now = new Date()
  const diff = d.getTime() - now.getTime()
  const days = Math.ceil(diff / (1000 * 60 * 60 * 24))
  if (days < 0) return `${Math.abs(days)}d overdue`
  if (days === 0) return 'Due today'
  if (days === 1) return 'Due tomorrow'
  return `Due in ${days}d`
}

function priorityLabel(p: string): string {
  return p.charAt(0).toUpperCase() + p.slice(1)
}

onMounted(async () => {
  await Promise.all([
    taskStore.fetchTasks(),
    taskStore.fetchTaskLists(),
    summaryStore.fetchSummaries(),
    topicStore.fetchTopics(),
    getDashboardStats().then((d) => { stats.value = d }).catch(() => {}),
  ])
})
</script>

<template>
  <div class="mx-auto max-w-7xl space-y-6">
    <!-- Stats row -->
    <div class="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-6">
      <StatCard
        label="Unread Emails"
        :value="stats?.emails.unread_emails ?? '—'"
        :icon="EnvelopeIcon"
        color="var(--color-primary)"
      />
      <StatCard
        label="Emails Today"
        :value="stats?.emails.emails_today ?? '—'"
        :icon="CalendarDaysIcon"
        color="var(--color-info)"
      />
      <StatCard
        label="Active Tasks"
        :value="taskStore.pendingTasks.length"
        :icon="ClipboardDocumentListIcon"
      />
      <StatCard
        label="Overdue"
        :value="taskStore.overdueTasks.length"
        :icon="ExclamationTriangleIcon"
        :color="taskStore.overdueTasks.length > 0 ? 'var(--color-error)' : undefined"
      />
      <StatCard
        label="Due This Week"
        :value="taskStore.upcomingTasks.length"
        :icon="ClockIcon"
        color="var(--color-warning)"
      />
      <StatCard
        label="Topics"
        :value="topicStore.topicCount"
        :icon="TagIcon"
        color="var(--color-info)"
      />
    </div>

    <!-- Main content grid -->
    <div class="grid grid-cols-1 gap-6 lg:grid-cols-3">
      <!-- Summaries column (2/3 width) -->
      <div class="space-y-6 lg:col-span-2">
        <!-- Morning Summary -->
        <BaseCard title="Morning Summary" :subtitle="today">
          <template #header>
            <div class="flex items-center gap-2">
              <SunIcon class="h-4 w-4" :style="{ color: 'var(--color-warning)' }" />
              <BaseButton
                v-if="!todayMorning"
                size="sm"
                variant="secondary"
                :loading="summaryStore.loading"
                @click="summaryStore.generateSummary('morning', today)"
              >
                <ArrowPathIcon class="h-3.5 w-3.5" />
                Generate
              </BaseButton>
            </div>
          </template>
          <SkeletonLoader v-if="summaryStore.loading && !todayMorning" :lines="4" />
          <div
            v-else-if="todayMorning"
            class="prose-theme text-sm"
            v-html="renderMarkdown(todayMorning.markdown_body)"
          />
          <div v-else-if="summaryStore.error" class="rounded-lg bg-red-50 p-3 text-sm text-red-700 dark:bg-red-900/20 dark:text-red-400">
            {{ summaryStore.error }}
          </div>
          <EmptyState v-else message="No morning summary yet for today." />
        </BaseCard>

        <!-- Evening Summary -->
        <BaseCard title="Evening Summary" :subtitle="today">
          <template #header>
            <div class="flex items-center gap-2">
              <MoonIcon class="h-4 w-4" :style="{ color: 'var(--color-primary)' }" />
              <BaseButton
                v-if="!todayEvening"
                size="sm"
                variant="secondary"
                :loading="summaryStore.loading"
                @click="summaryStore.generateSummary('evening', today)"
              >
                <ArrowPathIcon class="h-3.5 w-3.5" />
                Generate
              </BaseButton>
            </div>
          </template>
          <SkeletonLoader v-if="summaryStore.loading && !todayEvening" :lines="4" />
          <div
            v-else-if="todayEvening"
            class="prose-theme text-sm"
            v-html="renderMarkdown(todayEvening.markdown_body)"
          />
          <div v-else-if="summaryStore.error" class="rounded-lg bg-red-50 p-3 text-sm text-red-700 dark:bg-red-900/20 dark:text-red-400">
            {{ summaryStore.error }}
          </div>
          <EmptyState v-else message="No evening summary yet for today." />
        </BaseCard>
      </div>

      <!-- Tasks sidebar (1/3 width) -->
      <div class="space-y-6">
        <!-- Overdue tasks -->
        <BaseCard title="Overdue" no-padding>
          <template #header>
            <StatusBadge
              v-if="taskStore.overdueTasks.length > 0"
              variant="custom"
              :color="'var(--color-error)'"
              :bg-color="'var(--color-error)' + '22'"
            >
              {{ taskStore.overdueTasks.length }}
            </StatusBadge>
          </template>
          <SkeletonLoader v-if="taskStore.loading" variant="list" :lines="3" />
          <div v-else-if="taskStore.overdueTasks.length > 0" class="divide-y" :style="{ borderColor: 'var(--color-border)' }">
            <RouterLink
              v-for="task in taskStore.overdueTasks.slice(0, 5)"
              :key="task.id"
              :to="{ name: 'task-manager' }"
              class="flex items-start gap-3 px-5 py-3 transition-colors hover:opacity-80"
            >
              <ExclamationTriangleIcon
                class="mt-0.5 h-4 w-4 flex-shrink-0"
                :style="{ color: 'var(--color-error)' }"
              />
              <div class="min-w-0 flex-1">
                <p
                  class="truncate text-sm font-medium"
                  :style="{ color: 'var(--color-text-primary)' }"
                >
                  {{ task.title }}
                </p>
                <p class="text-xs" :style="{ color: 'var(--color-error)' }">
                  {{ formatDueDate(task.due_date) }}
                </p>
              </div>
              <StatusBadge variant="priority" :value="task.priority" />
            </RouterLink>
          </div>
          <div v-else class="px-5 pb-2">
            <p class="text-sm" :style="{ color: 'var(--color-text-muted)' }">No overdue tasks</p>
          </div>
        </BaseCard>

        <!-- Upcoming tasks -->
        <BaseCard title="Upcoming (7 days)" no-padding>
          <template #header>
            <CalendarDaysIcon class="h-4 w-4" :style="{ color: 'var(--color-text-muted)' }" />
          </template>
          <SkeletonLoader v-if="taskStore.loading" variant="list" :lines="4" />
          <div v-else-if="taskStore.upcomingTasks.length > 0" class="divide-y" :style="{ borderColor: 'var(--color-border)' }">
            <RouterLink
              v-for="task in taskStore.upcomingTasks.slice(0, 6)"
              :key="task.id"
              :to="{ name: 'task-manager' }"
              class="flex items-start gap-3 px-5 py-3 transition-colors hover:opacity-80"
            >
              <ClockIcon
                class="mt-0.5 h-4 w-4 flex-shrink-0"
                :style="{ color: 'var(--color-warning)' }"
              />
              <div class="min-w-0 flex-1">
                <p
                  class="truncate text-sm font-medium"
                  :style="{ color: 'var(--color-text-primary)' }"
                >
                  {{ task.title }}
                </p>
                <p class="text-xs" :style="{ color: 'var(--color-text-muted)' }">
                  {{ formatDueDate(task.due_date) }}
                </p>
              </div>
              <StatusBadge variant="priority" :value="task.priority" />
            </RouterLink>
          </div>
          <div v-else class="px-5 pb-2">
            <p class="text-sm" :style="{ color: 'var(--color-text-muted)' }">No upcoming tasks</p>
          </div>
        </BaseCard>

        <!-- Active tasks -->
        <BaseCard title="In Progress" no-padding>
          <SkeletonLoader v-if="taskStore.loading" variant="list" :lines="3" />
          <div
            v-else-if="taskStore.pendingTasks.length > 0"
            class="divide-y"
            :style="{ borderColor: 'var(--color-border)' }"
          >
            <RouterLink
              v-for="task in taskStore.pendingTasks.slice(0, 5)"
              :key="task.id"
              :to="{ name: 'task-manager' }"
              class="flex items-start gap-3 px-5 py-3 transition-colors hover:opacity-80"
            >
              <div class="min-w-0 flex-1">
                <p
                  class="truncate text-sm font-medium"
                  :style="{ color: 'var(--color-text-primary)' }"
                >
                  {{ task.title }}
                </p>
                <div class="mt-1 flex items-center gap-2">
                  <StatusBadge variant="status" :value="task.status" />
                  <StatusBadge variant="priority" :value="task.priority" />
                </div>
              </div>
            </RouterLink>
          </div>
          <div v-else class="px-5 pb-2">
            <p class="text-sm" :style="{ color: 'var(--color-text-muted)' }">No active tasks</p>
          </div>
        </BaseCard>
      </div>
    </div>
  </div>
</template>
