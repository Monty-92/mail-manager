<script setup lang="ts">
import type { TaskPriority, TaskStatus } from '@/types'

defineProps<{
  variant: 'status' | 'priority' | 'custom'
  value?: string
  color?: string
  bgColor?: string
}>()

function statusColor(value: string): { bg: string; text: string } {
  switch (value as TaskStatus) {
    case 'pending':
      return { bg: 'var(--color-warning)', text: '#ffffff' }
    case 'in_progress':
      return { bg: 'var(--color-info)', text: '#ffffff' }
    case 'done':
      return { bg: 'var(--color-success)', text: '#ffffff' }
    case 'cancelled':
      return { bg: 'var(--color-text-muted)', text: '#ffffff' }
    default:
      return { bg: 'var(--color-bg-tertiary)', text: 'var(--color-text-secondary)' }
  }
}

function priorityColor(value: string): { bg: string; text: string } {
  switch (value as TaskPriority) {
    case 'high':
      return { bg: 'var(--color-error)', text: '#ffffff' }
    case 'medium':
      return { bg: 'var(--color-warning)', text: '#1a1a2e' }
    case 'low':
      return { bg: 'var(--color-info)', text: '#ffffff' }
    default:
      return { bg: 'var(--color-bg-tertiary)', text: 'var(--color-text-secondary)' }
  }
}
</script>

<template>
  <span
    class="inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium"
    :style="{
      backgroundColor:
        variant === 'status'
          ? statusColor(value ?? '').bg + '22'
          : variant === 'priority'
            ? priorityColor(value ?? '').bg + '22'
            : bgColor ?? 'var(--color-bg-tertiary)',
      color:
        variant === 'status'
          ? statusColor(value ?? '').bg
          : variant === 'priority'
            ? priorityColor(value ?? '').bg
            : color ?? 'var(--color-text-secondary)',
    }"
  >
    <slot>{{ value }}</slot>
  </span>
</template>
