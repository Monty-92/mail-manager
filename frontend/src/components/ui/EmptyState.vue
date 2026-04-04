<script setup lang="ts">
defineProps<{
  message?: string
}>()
</script>

<template>
  <div class="flex flex-col items-center justify-center py-16 text-center">
    <div
      class="flex h-16 w-16 items-center justify-center rounded-full"
      :style="{ backgroundColor: 'var(--color-bg-tertiary)' }"
    >
      <slot name="icon">
        <svg
          class="h-8 w-8"
          :style="{ color: 'var(--color-text-muted)' }"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
        >
          <path
            stroke-linecap="round"
            stroke-linejoin="round"
            stroke-width="1.5"
            d="M20 13V6a2 2 0 00-2-2H6a2 2 0 00-2 2v7m16 0v5a2 2 0 01-2 2H6a2 2 0 01-2-2v-5m16 0h-2.586a1 1 0 00-.707.293l-2.414 2.414a1 1 0 01-.707.293h-3.172a1 1 0 01-.707-.293l-2.414-2.414A1 1 0 006.586 13H4"
          />
        </svg>
      </slot>
    </div>
    <p
      class="mt-4 text-sm"
      :style="{ color: 'var(--color-text-muted)' }"
    >
      {{ message ?? 'No items to display' }}
    </p>
    <div v-if="$slots.action" class="mt-4">
      <slot name="action" />
    </div>
  </div>
</template>
