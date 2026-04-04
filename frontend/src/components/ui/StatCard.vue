<script setup lang="ts">
defineProps<{
  label: string
  value: string | number
  icon?: object
  trend?: { value: number; label: string }
  color?: string
}>()
</script>

<template>
  <div
    class="flex items-start gap-4 rounded-xl border p-5"
    :style="{
      backgroundColor: 'var(--color-bg-secondary)',
      borderColor: 'var(--color-border)',
    }"
  >
    <div
      v-if="icon"
      class="flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-lg"
      :style="{ backgroundColor: (color ?? 'var(--color-primary)') + '1a' }"
    >
      <component
        :is="icon"
        class="h-5 w-5"
        :style="{ color: color ?? 'var(--color-primary)' }"
      />
    </div>
    <div class="min-w-0 flex-1">
      <p
        class="text-xs font-medium uppercase tracking-wider"
        :style="{ color: 'var(--color-text-muted)' }"
      >
        {{ label }}
      </p>
      <p
        class="mt-1 text-2xl font-bold tabular-nums"
        :style="{ color: 'var(--color-text-primary)' }"
      >
        {{ value }}
      </p>
      <p
        v-if="trend"
        class="mt-1 text-xs"
        :style="{
          color: trend.value >= 0 ? 'var(--color-success)' : 'var(--color-error)',
        }"
      >
        {{ trend.value >= 0 ? '↑' : '↓' }} {{ Math.abs(trend.value) }}% {{ trend.label }}
      </p>
    </div>
  </div>
</template>
