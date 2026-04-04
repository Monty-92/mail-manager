<script setup lang="ts">
defineProps<{
  type?: 'text' | 'email' | 'password' | 'search' | 'date' | 'number'
  modelValue: string | number
  placeholder?: string
  label?: string
  error?: string
  disabled?: boolean
}>()

defineEmits<{
  'update:modelValue': [value: string | number]
}>()
</script>

<template>
  <div class="flex flex-col gap-1.5">
    <label
      v-if="label"
      class="text-xs font-medium"
      :style="{ color: 'var(--color-text-secondary)' }"
    >
      {{ label }}
    </label>
    <input
      :type="type ?? 'text'"
      :value="modelValue"
      :placeholder="placeholder"
      :disabled="disabled"
      class="w-full rounded-lg border bg-transparent px-3 py-2 text-sm outline-none transition-colors duration-150 focus:ring-2 focus:ring-offset-0 disabled:cursor-not-allowed disabled:opacity-50"
      :style="{
        borderColor: error ? 'var(--color-error)' : 'var(--color-border)',
        color: 'var(--color-text-primary)',
        '--tw-ring-color': 'var(--color-primary)',
      }"
      @input="$emit('update:modelValue', ($event.target as HTMLInputElement).value)"
    />
    <p
      v-if="error"
      class="text-xs"
      :style="{ color: 'var(--color-error)' }"
    >
      {{ error }}
    </p>
  </div>
</template>
