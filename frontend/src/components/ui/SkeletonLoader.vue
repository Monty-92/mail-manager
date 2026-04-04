<script setup lang="ts">
defineProps<{
  lines?: number
  variant?: 'text' | 'card' | 'list'
}>()
</script>

<template>
  <!-- Card skeleton -->
  <div v-if="variant === 'card'" class="animate-pulse space-y-3">
    <div
      class="h-4 w-1/3 rounded"
      :style="{ backgroundColor: 'var(--color-bg-tertiary)' }"
    />
    <div
      class="h-20 rounded-lg"
      :style="{ backgroundColor: 'var(--color-bg-tertiary)' }"
    />
  </div>

  <!-- List skeleton -->
  <div v-else-if="variant === 'list'" class="animate-pulse space-y-3">
    <div
      v-for="i in (lines ?? 5)"
      :key="i"
      class="flex items-center gap-3"
    >
      <div
        class="h-8 w-8 rounded-lg"
        :style="{ backgroundColor: 'var(--color-bg-tertiary)' }"
      />
      <div class="flex-1 space-y-1.5">
        <div
          class="h-3 rounded"
          :style="{
            backgroundColor: 'var(--color-bg-tertiary)',
            width: `${60 + Math.random() * 30}%`,
          }"
        />
        <div
          class="h-2.5 w-1/2 rounded"
          :style="{ backgroundColor: 'var(--color-bg-tertiary)' }"
        />
      </div>
    </div>
  </div>

  <!-- Text skeleton (default) -->
  <div v-else class="animate-pulse space-y-2">
    <div
      v-for="i in (lines ?? 3)"
      :key="i"
      class="h-3 rounded"
      :style="{
        backgroundColor: 'var(--color-bg-tertiary)',
        width: i === (lines ?? 3) ? '60%' : '100%',
      }"
    />
  </div>
</template>
