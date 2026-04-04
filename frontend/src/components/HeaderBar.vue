<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import {
  MagnifyingGlassIcon,
  ChatBubbleLeftRightIcon,
  SunIcon,
  MoonIcon,
  ComputerDesktopIcon,
} from '@heroicons/vue/24/outline'
import { useThemeStore } from '@/stores/theme'
import { useChatStore } from '@/stores/chat'

const route = useRoute()
const themeStore = useThemeStore()
const chatStore = useChatStore()

const pageTitle = computed(() => {
  const titles: Record<string, string> = {
    dashboard: 'Dashboard',
    'email-browser': 'Emails',
    'topic-explorer': 'Topics',
    'task-manager': 'Tasks',
    calendar: 'Calendar',
    settings: 'Settings',
  }
  return titles[route.name as string] ?? 'mail-manager'
})

const themeIcon = computed(() => {
  if (themeStore.mode === 'dark') return MoonIcon
  if (themeStore.mode === 'light') return SunIcon
  return ComputerDesktopIcon
})

function cycleTheme() {
  const order = ['dark', 'light', 'system'] as const
  const idx = order.indexOf(themeStore.mode)
  themeStore.setMode(order[(idx + 1) % order.length])
}
</script>

<template>
  <header
    class="flex h-14 items-center justify-between border-b px-6"
    :style="{
      backgroundColor: 'var(--color-bg-primary)',
      borderColor: 'var(--color-border)',
    }"
  >
    <!-- Page title -->
    <h1
      class="text-lg font-semibold"
      :style="{ color: 'var(--color-text-primary)' }"
    >
      {{ pageTitle }}
    </h1>

    <!-- Right actions -->
    <div class="flex items-center gap-1">
      <!-- Search -->
      <button
        class="rounded-lg p-2 transition-colors duration-150 hover:opacity-80"
        :style="{ color: 'var(--color-text-muted)' }"
        title="Search (⌘K)"
      >
        <MagnifyingGlassIcon class="h-5 w-5" />
      </button>

      <!-- Theme toggle -->
      <button
        class="rounded-lg p-2 transition-colors duration-150 hover:opacity-80"
        :style="{ color: 'var(--color-text-muted)' }"
        :title="`Theme: ${themeStore.mode}`"
        @click="cycleTheme"
      >
        <component :is="themeIcon" class="h-5 w-5" />
      </button>

      <!-- AI Chat toggle -->
      <button
        class="rounded-lg p-2 transition-colors duration-150 hover:opacity-80"
        :style="{
          color: chatStore.isOpen ? 'var(--color-primary)' : 'var(--color-text-muted)',
        }"
        title="AI Assistant"
        @click="chatStore.togglePanel"
      >
        <ChatBubbleLeftRightIcon class="h-5 w-5" />
      </button>
    </div>
  </header>
</template>
