<script setup lang="ts">
defineProps<{
  variant?: 'primary' | 'secondary' | 'ghost' | 'danger'
  size?: 'sm' | 'md' | 'lg'
  loading?: boolean
  disabled?: boolean
}>()
</script>

<template>
  <button
    class="inline-flex items-center justify-center gap-2 rounded-lg font-medium transition-all duration-150 focus:outline-none focus:ring-2 focus:ring-offset-1 disabled:cursor-not-allowed disabled:opacity-50"
    :class="{
      'px-3 py-1.5 text-xs': size === 'sm',
      'px-4 py-2 text-sm': !size || size === 'md',
      'px-5 py-2.5 text-sm': size === 'lg',
    }"
    :style="{
      backgroundColor:
        variant === 'primary'
          ? 'var(--color-primary)'
          : variant === 'danger'
            ? 'var(--color-error)'
            : variant === 'ghost'
              ? 'transparent'
              : 'var(--color-bg-tertiary)',
      color:
        variant === 'primary' || variant === 'danger'
          ? '#ffffff'
          : 'var(--color-text-primary)',
      '--tw-ring-color': 'var(--color-primary)',
    }"
    :disabled="disabled || loading"
  >
    <svg
      v-if="loading"
      class="h-4 w-4 animate-spin"
      viewBox="0 0 24 24"
      fill="none"
    >
      <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" />
      <path
        class="opacity-75"
        fill="currentColor"
        d="M4 12a8 8 0 018-8v4a4 4 0 00-4 4H4z"
      />
    </svg>
    <slot />
  </button>
</template>
