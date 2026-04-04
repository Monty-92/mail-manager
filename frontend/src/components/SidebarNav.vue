<script setup lang="ts">
import { ref } from 'vue'
import { RouterLink, useRoute } from 'vue-router'
import {
  HomeIcon,
  EnvelopeIcon,
  TagIcon,
  ClipboardDocumentListIcon,
  CalendarDaysIcon,
  Cog6ToothIcon,
  ChevronDoubleLeftIcon,
  ChevronDoubleRightIcon,
} from '@heroicons/vue/24/outline'

const route = useRoute()
const collapsed = ref(false)

const navItems = [
  { name: 'Dashboard', to: '/', icon: HomeIcon },
  { name: 'Emails', to: '/emails', icon: EnvelopeIcon },
  { name: 'Topics', to: '/topics', icon: TagIcon },
  { name: 'Tasks', to: '/tasks', icon: ClipboardDocumentListIcon },
  { name: 'Calendar', to: '/calendar', icon: CalendarDaysIcon },
] as const

const bottomItems = [
  { name: 'Settings', to: '/settings', icon: Cog6ToothIcon },
] as const

function isActive(to: string): boolean {
  if (to === '/') return route.path === '/'
  return route.path.startsWith(to)
}
</script>

<template>
  <nav
    class="flex flex-col border-r transition-all duration-300"
    :class="collapsed ? 'w-16' : 'w-60'"
    :style="{
      backgroundColor: 'var(--color-bg-sidebar)',
      borderColor: 'var(--color-border)',
    }"
  >
    <!-- Logo -->
    <div class="flex h-14 items-center gap-3 px-4">
      <div
        class="flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-lg font-bold text-white"
        :style="{ backgroundColor: 'var(--color-primary)' }"
      >
        M
      </div>
      <span
        v-if="!collapsed"
        class="text-sm font-semibold tracking-tight truncate"
        :style="{ color: 'var(--color-text-primary)' }"
      >
        mail-manager
      </span>
    </div>

    <!-- Nav items -->
    <ul class="mt-2 flex-1 space-y-0.5 px-2">
      <li v-for="item in navItems" :key="item.to">
        <RouterLink
          :to="item.to"
          class="group flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors duration-150"
          :class="collapsed ? 'justify-center' : ''"
          :style="{
            backgroundColor: isActive(item.to) ? 'var(--color-bg-tertiary)' : 'transparent',
            color: isActive(item.to) ? 'var(--color-primary)' : 'var(--color-text-secondary)',
          }"
          :title="collapsed ? item.name : undefined"
        >
          <component
            :is="item.icon"
            class="h-5 w-5 flex-shrink-0 transition-colors duration-150"
            :style="{
              color: isActive(item.to) ? 'var(--color-primary)' : 'var(--color-text-muted)',
            }"
          />
          <span v-if="!collapsed" class="truncate">{{ item.name }}</span>
        </RouterLink>
      </li>
    </ul>

    <!-- Bottom items -->
    <ul class="space-y-0.5 px-2 pb-2">
      <li v-for="item in bottomItems" :key="item.to">
        <RouterLink
          :to="item.to"
          class="group flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors duration-150"
          :class="collapsed ? 'justify-center' : ''"
          :style="{
            backgroundColor: isActive(item.to) ? 'var(--color-bg-tertiary)' : 'transparent',
            color: isActive(item.to) ? 'var(--color-primary)' : 'var(--color-text-secondary)',
          }"
          :title="collapsed ? item.name : undefined"
        >
          <component
            :is="item.icon"
            class="h-5 w-5 flex-shrink-0 transition-colors duration-150"
            :style="{
              color: isActive(item.to) ? 'var(--color-primary)' : 'var(--color-text-muted)',
            }"
          />
          <span v-if="!collapsed" class="truncate">{{ item.name }}</span>
        </RouterLink>
      </li>

      <!-- Collapse toggle -->
      <li>
        <button
          class="flex w-full items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors duration-150"
          :class="collapsed ? 'justify-center' : ''"
          :style="{ color: 'var(--color-text-muted)' }"
          @click="collapsed = !collapsed"
        >
          <component
            :is="collapsed ? ChevronDoubleRightIcon : ChevronDoubleLeftIcon"
            class="h-5 w-5 flex-shrink-0"
          />
          <span v-if="!collapsed" class="truncate">Collapse</span>
        </button>
      </li>
    </ul>
  </nav>
</template>
