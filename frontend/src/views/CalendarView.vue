<script setup lang="ts">
import { ref, computed } from 'vue'
import {
  ChevronLeftIcon,
  ChevronRightIcon,
  CalendarDaysIcon,
  EyeIcon,
  EyeSlashIcon,
} from '@heroicons/vue/24/outline'
import type { CalendarEvent, CalendarSource } from '@/types'
import BaseCard from '@/components/ui/BaseCard.vue'
import BaseButton from '@/components/ui/BaseButton.vue'
import EmptyState from '@/components/ui/EmptyState.vue'

// Calendar navigation state
const currentDate = ref(new Date())
const viewMode = ref<'month' | 'week' | 'day'>('month')

// Placeholder: no calendar sync service yet
const events = ref<CalendarEvent[]>([])
const calendarSources = ref<CalendarSource[]>([])

const monthNames = [
  'January', 'February', 'March', 'April', 'May', 'June',
  'July', 'August', 'September', 'October', 'November', 'December',
]

const dayNames = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat']

const currentMonth = computed(() => currentDate.value.getMonth())
const currentYear = computed(() => currentDate.value.getFullYear())
const monthLabel = computed(() => `${monthNames[currentMonth.value]} ${currentYear.value}`)

const calendarDays = computed(() => {
  const year = currentYear.value
  const month = currentMonth.value
  const firstDay = new Date(year, month, 1)
  const lastDay = new Date(year, month + 1, 0)
  const startDayOfWeek = firstDay.getDay()

  const days: Array<{ date: Date; isCurrentMonth: boolean; isToday: boolean; events: CalendarEvent[] }> = []

  // Previous month padding
  for (let i = startDayOfWeek - 1; i >= 0; i--) {
    const d = new Date(year, month, -i)
    days.push({ date: d, isCurrentMonth: false, isToday: false, events: [] })
  }

  // Current month
  const today = new Date()
  for (let d = 1; d <= lastDay.getDate(); d++) {
    const date = new Date(year, month, d)
    const isToday =
      date.getDate() === today.getDate() &&
      date.getMonth() === today.getMonth() &&
      date.getFullYear() === today.getFullYear()
    const dayEvents = events.value.filter((e) => {
      const eDate = new Date(e.start_at)
      return eDate.getDate() === d && eDate.getMonth() === month && eDate.getFullYear() === year
    })
    days.push({ date, isCurrentMonth: true, isToday, events: dayEvents })
  }

  // Next month padding to fill grid
  const remaining = 42 - days.length
  for (let d = 1; d <= remaining; d++) {
    const date = new Date(year, month + 1, d)
    days.push({ date, isCurrentMonth: false, isToday: false, events: [] })
  }

  return days
})

function navigateMonth(delta: number) {
  const d = new Date(currentDate.value)
  d.setMonth(d.getMonth() + delta)
  currentDate.value = d
}

function goToToday() {
  currentDate.value = new Date()
}

function toggleSource(source: CalendarSource) {
  source.enabled = !source.enabled
}

function providerColor(provider: string): string {
  switch (provider) {
    case 'google':
      return '#4285f4'
    case 'outlook':
      return '#0078d4'
    default:
      return 'var(--color-primary)'
  }
}
</script>

<template>
  <div class="mx-auto flex h-full max-w-7xl gap-6">
    <!-- Calendar sidebar -->
    <div class="w-60 flex-shrink-0 space-y-4">
      <!-- Mini navigation -->
      <BaseCard title="Calendars" no-padding>
        <div v-if="calendarSources.length === 0" class="px-5 py-4">
          <p class="text-xs" :style="{ color: 'var(--color-text-muted)' }">
            No calendars connected yet. Go to Settings to connect Google or Outlook accounts.
          </p>
          <RouterLink :to="{ name: 'settings' }" class="mt-2 inline-block">
            <BaseButton variant="primary" size="sm">Connect Calendar</BaseButton>
          </RouterLink>
        </div>
        <div v-else class="px-3 py-2 space-y-1">
          <button
            v-for="source in calendarSources"
            :key="source.id"
            class="flex w-full items-center gap-2 rounded-md px-2 py-1.5 text-sm transition-colors"
            :style="{ color: 'var(--color-text-secondary)' }"
            @click="toggleSource(source)"
          >
            <span
              class="h-3 w-3 rounded-sm"
              :style="{
                backgroundColor: source.enabled ? source.color : 'transparent',
                borderWidth: '2px',
                borderColor: source.color,
              }"
            />
            <span class="flex-1 text-left truncate">{{ source.calendar_name }}</span>
            <span class="text-xs" :style="{ color: 'var(--color-text-muted)' }">
              {{ source.provider }}
            </span>
          </button>
        </div>
      </BaseCard>
    </div>

    <!-- Main calendar -->
    <div class="flex-1">
      <!-- Calendar header -->
      <div class="mb-4 flex items-center justify-between">
        <div class="flex items-center gap-3">
          <h2
            class="text-lg font-semibold"
            :style="{ color: 'var(--color-text-primary)' }"
          >
            {{ monthLabel }}
          </h2>
          <div class="flex items-center gap-1">
            <button
              class="rounded-lg p-1.5 transition-colors hover:opacity-70"
              :style="{ color: 'var(--color-text-muted)' }"
              @click="navigateMonth(-1)"
            >
              <ChevronLeftIcon class="h-5 w-5" />
            </button>
            <button
              class="rounded-lg p-1.5 transition-colors hover:opacity-70"
              :style="{ color: 'var(--color-text-muted)' }"
              @click="navigateMonth(1)"
            >
              <ChevronRightIcon class="h-5 w-5" />
            </button>
          </div>
          <BaseButton variant="ghost" size="sm" @click="goToToday">Today</BaseButton>
        </div>

        <div class="flex rounded-lg border" :style="{ borderColor: 'var(--color-border)' }">
          <button
            v-for="mode in (['month', 'week', 'day'] as const)"
            :key="mode"
            class="px-3 py-1.5 text-xs font-medium capitalize transition-colors"
            :style="{
              backgroundColor: viewMode === mode ? 'var(--color-bg-tertiary)' : 'transparent',
              color: viewMode === mode ? 'var(--color-text-primary)' : 'var(--color-text-muted)',
            }"
            @click="viewMode = mode"
          >
            {{ mode }}
          </button>
        </div>
      </div>

      <!-- Month grid -->
      <div
        class="rounded-xl border overflow-hidden"
        :style="{
          backgroundColor: 'var(--color-bg-secondary)',
          borderColor: 'var(--color-border)',
        }"
      >
        <!-- Day headers -->
        <div class="grid grid-cols-7 border-b" :style="{ borderColor: 'var(--color-border)' }">
          <div
            v-for="dayName in dayNames"
            :key="dayName"
            class="px-3 py-2 text-center text-xs font-medium"
            :style="{ color: 'var(--color-text-muted)' }"
          >
            {{ dayName }}
          </div>
        </div>

        <!-- Day cells -->
        <div class="grid grid-cols-7">
          <div
            v-for="(day, idx) in calendarDays"
            :key="idx"
            class="min-h-[100px] border-b border-r p-2"
            :style="{
              borderColor: 'var(--color-border)',
              backgroundColor: day.isToday
                ? 'var(--color-primary)' + '0a'
                : !day.isCurrentMonth
                  ? 'var(--color-bg-tertiary)' + '40'
                  : 'transparent',
            }"
          >
            <span
              class="inline-flex h-6 w-6 items-center justify-center rounded-full text-xs"
              :style="{
                backgroundColor: day.isToday ? 'var(--color-primary)' : 'transparent',
                color: day.isToday
                  ? '#ffffff'
                  : !day.isCurrentMonth
                    ? 'var(--color-text-muted)'
                    : 'var(--color-text-secondary)',
                fontWeight: day.isToday ? '600' : '400',
              }"
            >
              {{ day.date.getDate() }}
            </span>

            <!-- Events in cell -->
            <div v-if="day.events.length > 0" class="mt-1 space-y-0.5">
              <div
                v-for="event in day.events.slice(0, 3)"
                :key="event.id"
                class="truncate rounded px-1.5 py-0.5 text-xs"
                :style="{
                  backgroundColor: providerColor(event.provider) + '22',
                  color: providerColor(event.provider),
                }"
              >
                {{ event.title }}
              </div>
              <div
                v-if="day.events.length > 3"
                class="text-xs px-1.5"
                :style="{ color: 'var(--color-text-muted)' }"
              >
                +{{ day.events.length - 3 }} more
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Empty state for no events -->
      <div
        v-if="events.length === 0"
        class="mt-6"
      >
        <EmptyState message="No calendar events to display. Connect your calendars in Settings to see your schedule here.">
          <template #icon>
            <CalendarDaysIcon class="h-8 w-8" :style="{ color: 'var(--color-text-muted)' }" />
          </template>
        </EmptyState>
      </div>
    </div>
  </div>
</template>
