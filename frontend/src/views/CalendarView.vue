<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import {
  ChevronLeftIcon,
  ChevronRightIcon,
  ChevronDownIcon,
  CalendarDaysIcon,
  ArrowPathIcon,
} from '@heroicons/vue/24/outline'
import { getCalendarEvents, getCalendarSources, syncCalendar } from '@/api/calendar'
import type { CalendarEvent, CalendarAccount, CalendarInfo } from '@/types'
import BaseCard from '@/components/ui/BaseCard.vue'
import BaseButton from '@/components/ui/BaseButton.vue'
import EmptyState from '@/components/ui/EmptyState.vue'

const currentDate = ref(new Date())
const viewMode = ref<'month' | 'week' | 'day'>('month')
const events = ref<CalendarEvent[]>([])
const calendarAccounts = ref<CalendarAccount[]>([])
const syncing = ref(false)
const sidebarCollapsed = ref(false)
const collapsedAccounts = ref<Set<string>>(new Set())

// Track which calendars are toggled on (by calendar id)
const enabledCalendarIds = ref<Set<string>>(new Set())

onMounted(async () => {
  await Promise.all([loadSources(), loadEvents()])
  // Initially enable all calendars
  for (const acct of calendarAccounts.value) {
    for (const cal of acct.calendars) {
      if (cal.enabled) {
        enabledCalendarIds.value.add(cal.id)
      }
    }
  }
})

async function loadEvents() {
  try {
    const now = new Date()
    const start = new Date(now.getFullYear(), now.getMonth() - 1, 1)
    const end = new Date(now.getFullYear(), now.getMonth() + 3, 0)
    events.value = await getCalendarEvents({
      start_after: start.toISOString(),
      end_before: end.toISOString(),
    })
  } catch {
    // Service unavailable
  }
}

async function loadSources() {
  try {
    calendarAccounts.value = await getCalendarSources()
  } catch {
    // No sources
  }
}

async function handleSync() {
  syncing.value = true
  try {
    await syncCalendar()
    await Promise.all([loadEvents(), loadSources()])
  } finally {
    syncing.value = false
  }
}

// Build a map from calendar_id to CalendarInfo for color lookup
const calendarMap = computed(() => {
  const map = new Map<string, CalendarInfo>()
  for (const acct of calendarAccounts.value) {
    for (const cal of acct.calendars) {
      map.set(cal.id, cal)
    }
  }
  return map
})

// Filter events by enabled calendars
const visibleEvents = computed(() => {
  if (enabledCalendarIds.value.size === 0) return events.value
  return events.value.filter((e) => enabledCalendarIds.value.has(e.calendar_id))
})

function toggleCalendar(calId: string) {
  const next = new Set(enabledCalendarIds.value)
  if (next.has(calId)) {
    next.delete(calId)
  } else {
    next.add(calId)
  }
  enabledCalendarIds.value = next
}

function toggleAccountCollapse(accountId: string) {
  const next = new Set(collapsedAccounts.value)
  if (next.has(accountId)) {
    next.delete(accountId)
  } else {
    next.add(accountId)
  }
  collapsedAccounts.value = next
}

function eventColor(event: CalendarEvent): string {
  const cal = calendarMap.value.get(event.calendar_id)
  if (cal?.color) return cal.color
  return providerColor(event.provider)
}

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

  const today = new Date()
  for (let d = 1; d <= lastDay.getDate(); d++) {
    const date = new Date(year, month, d)
    const isToday =
      date.getDate() === today.getDate() &&
      date.getMonth() === today.getMonth() &&
      date.getFullYear() === today.getFullYear()
    const dayEvents = visibleEvents.value.filter((e) => {
      const eDate = new Date(e.start_at)
      return eDate.getDate() === d && eDate.getMonth() === month && eDate.getFullYear() === year
    })
    days.push({ date, isCurrentMonth: true, isToday, events: dayEvents })
  }

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

function providerColor(provider: string): string {
  return provider === 'gmail' ? '#4285f4' : provider === 'outlook' ? '#0078d4' : 'var(--color-primary)'
}

function providerLabel(provider: string): string {
  return provider === 'gmail' ? 'Google' : provider === 'outlook' ? 'Outlook' : provider
}
</script>

<template>
  <div class="flex h-full gap-0">
    <!-- Calendar sidebar (collapsible) -->
    <div
      class="flex flex-shrink-0 flex-col border-r transition-all duration-300"
      :class="sidebarCollapsed ? 'w-10' : 'w-60'"
      :style="{ borderColor: 'var(--color-border)', backgroundColor: 'var(--color-bg-secondary)' }"
    >
      <div class="flex items-center justify-between px-3 py-3">
        <span
          v-if="!sidebarCollapsed"
          class="text-xs font-semibold uppercase tracking-wider"
          :style="{ color: 'var(--color-text-muted)' }"
        >
          Calendars
        </span>
        <button
          class="rounded p-0.5 transition-colors hover:opacity-70"
          :style="{ color: 'var(--color-text-muted)' }"
          @click="sidebarCollapsed = !sidebarCollapsed"
        >
          <component
            :is="sidebarCollapsed ? ChevronRightIcon : ChevronDownIcon"
            class="h-4 w-4"
          />
        </button>
      </div>

      <div v-if="!sidebarCollapsed" class="flex-1 overflow-y-auto px-2 pb-2">
        <template v-if="calendarAccounts.length === 0">
          <div class="px-2 py-3">
            <p class="text-xs" :style="{ color: 'var(--color-text-muted)' }">
              No calendars connected. Go to Settings to connect accounts.
            </p>
            <RouterLink :to="{ name: 'settings' }" class="mt-2 inline-block">
              <BaseButton variant="primary" size="sm">Connect Account</BaseButton>
            </RouterLink>
          </div>
        </template>

        <template v-else>
          <div
            v-for="account in calendarAccounts"
            :key="account.id"
            class="mb-2"
          >
            <!-- Account header -->
            <button
              class="flex w-full items-center gap-2 rounded-md px-2 py-1.5 text-xs font-semibold transition-colors hover:opacity-80"
              :style="{ color: 'var(--color-text-primary)' }"
              @click="toggleAccountCollapse(account.id)"
            >
              <ChevronDownIcon
                class="h-3 w-3 flex-shrink-0 transition-transform"
                :class="{ '-rotate-90': collapsedAccounts.has(account.id) }"
              />
              <span
                class="inline-flex h-5 w-5 items-center justify-center rounded text-[10px] font-bold text-white"
                :style="{ backgroundColor: providerColor(account.provider) }"
              >
                {{ account.provider === 'gmail' ? 'G' : 'O' }}
              </span>
              <span class="flex-1 truncate text-left">{{ account.account_email }}</span>
            </button>

            <!-- Nested calendars -->
            <div
              v-if="!collapsedAccounts.has(account.id)"
              class="mt-0.5 space-y-0.5 pl-5"
            >
              <button
                v-for="cal in account.calendars"
                :key="cal.id"
                class="flex w-full items-center gap-2 rounded-md px-2 py-1 text-xs transition-colors"
                :style="{ color: 'var(--color-text-secondary)' }"
                @click="toggleCalendar(cal.id)"
              >
                <span
                  class="h-3 w-3 flex-shrink-0 rounded-sm"
                  :style="{
                    backgroundColor: enabledCalendarIds.has(cal.id) ? (cal.color || providerColor(account.provider)) : 'transparent',
                    borderWidth: '2px',
                    borderColor: cal.color || providerColor(account.provider),
                  }"
                />
                <span class="flex-1 truncate text-left">{{ cal.name }}</span>
                <span
                  v-if="cal.is_primary"
                  class="text-[10px]"
                  :style="{ color: 'var(--color-text-muted)' }"
                >
                  primary
                </span>
              </button>
            </div>
          </div>
        </template>
      </div>
    </div>

    <!-- Main calendar area -->
    <div class="flex-1 overflow-auto p-6">
      <!-- Calendar header -->
      <div class="mb-4 flex items-center justify-between">
        <div class="flex items-center gap-3">
          <h2 class="text-lg font-semibold" :style="{ color: 'var(--color-text-primary)' }">
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
          <BaseButton variant="ghost" size="sm" :disabled="syncing" @click="handleSync">
            <ArrowPathIcon class="h-4 w-4" :class="{ 'animate-spin': syncing }" />
            Sync
          </BaseButton>
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

            <div v-if="day.events.length > 0" class="mt-1 space-y-0.5">
              <div
                v-for="event in day.events.slice(0, 3)"
                :key="event.id"
                class="truncate rounded px-1.5 py-0.5 text-xs"
                :style="{
                  backgroundColor: eventColor(event) + '22',
                  color: eventColor(event),
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

      <!-- Empty state -->
      <div v-if="events.length === 0" class="mt-6">
        <EmptyState message="No calendar events to display. Click Sync to fetch your events, or connect calendars in Settings.">
          <template #icon>
            <CalendarDaysIcon class="h-8 w-8" :style="{ color: 'var(--color-text-muted)' }" />
          </template>
          <template #action>
            <BaseButton variant="primary" size="sm" :disabled="syncing" @click="handleSync">
              <ArrowPathIcon class="h-4 w-4" :class="{ 'animate-spin': syncing }" />
              Sync Calendars
            </BaseButton>
          </template>
        </EmptyState>
      </div>
    </div>
  </div>
</template>
