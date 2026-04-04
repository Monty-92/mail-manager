<script setup lang="ts">
defineProps<{
  title: string
  subtitle?: string
  noPadding?: boolean
}>()
</script>

<template>
  <div
    class="rounded-xl border"
    :style="{
      backgroundColor: 'var(--color-bg-secondary)',
      borderColor: 'var(--color-border)',
    }"
  >
    <div
      v-if="title || $slots.header"
      class="flex items-center justify-between border-b px-5 py-3.5"
      :style="{ borderColor: 'var(--color-border)' }"
    >
      <div>
        <h3
          class="text-sm font-semibold"
          :style="{ color: 'var(--color-text-primary)' }"
        >
          {{ title }}
        </h3>
        <p
          v-if="subtitle"
          class="mt-0.5 text-xs"
          :style="{ color: 'var(--color-text-muted)' }"
        >
          {{ subtitle }}
        </p>
      </div>
      <slot name="header" />
    </div>
    <div :class="noPadding ? '' : 'p-5'">
      <slot />
    </div>
  </div>
</template>
