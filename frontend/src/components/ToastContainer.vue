<script setup lang="ts">
import {
  CheckCircleIcon,
  ExclamationTriangleIcon,
  XCircleIcon,
  InformationCircleIcon,
  XMarkIcon,
} from '@heroicons/vue/24/outline'
import { useToast } from '@/composables/useToast'
import type { Toast } from '@/composables/useToast'

const { toasts, removeToast } = useToast()

function iconForType(type: Toast['type']) {
  switch (type) {
    case 'success':
      return CheckCircleIcon
    case 'warning':
      return ExclamationTriangleIcon
    case 'error':
      return XCircleIcon
    case 'info':
      return InformationCircleIcon
  }
}

function colorForType(type: Toast['type']): string {
  switch (type) {
    case 'success':
      return 'var(--color-success)'
    case 'warning':
      return 'var(--color-warning)'
    case 'error':
      return 'var(--color-error)'
    case 'info':
      return 'var(--color-info)'
  }
}
</script>

<template>
  <div class="pointer-events-none fixed bottom-4 right-4 z-50 flex flex-col gap-2">
    <TransitionGroup
      enter-active-class="transition duration-300 ease-out"
      enter-from-class="translate-y-2 opacity-0"
      enter-to-class="translate-y-0 opacity-100"
      leave-active-class="transition duration-200 ease-in"
      leave-from-class="translate-y-0 opacity-100"
      leave-to-class="translate-y-2 opacity-0"
    >
      <div
        v-for="toast in toasts"
        :key="toast.id"
        class="pointer-events-auto flex max-w-sm items-start gap-3 rounded-lg border p-4 shadow-lg"
        :style="{
          backgroundColor: 'var(--color-bg-secondary)',
          borderColor: 'var(--color-border)',
        }"
      >
        <component
          :is="iconForType(toast.type)"
          class="h-5 w-5 flex-shrink-0 mt-0.5"
          :style="{ color: colorForType(toast.type) }"
        />
        <p
          class="flex-1 text-sm"
          :style="{ color: 'var(--color-text-primary)' }"
        >
          {{ toast.message }}
        </p>
        <button
          class="flex-shrink-0 rounded p-0.5 transition-colors hover:opacity-70"
          :style="{ color: 'var(--color-text-muted)' }"
          @click="removeToast(toast.id)"
        >
          <XMarkIcon class="h-4 w-4" />
        </button>
      </div>
    </TransitionGroup>
  </div>
</template>
