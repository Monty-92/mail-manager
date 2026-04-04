<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useAccountStore } from '@/stores/account'

const router = useRouter()
const route = useRoute()
const accountStore = useAccountStore()

const status = ref<'processing' | 'success' | 'error'>('processing')
const errorMessage = ref('')

onMounted(async () => {
  const code = route.query.code as string | undefined
  const state = route.query.state as string | undefined

  if (!code) {
    status.value = 'error'
    errorMessage.value = 'No authorization code received'
    return
  }

  // Determine provider from state or URL
  // For now, try to detect from the URL or default to gmail
  // The state parameter can be used for CSRF protection and provider identification
  const provider = (route.query.provider as string) || detectProvider()

  try {
    await accountStore.handleCallback(code, provider)
    status.value = 'success'
    setTimeout(() => {
      router.replace({ name: 'settings' })
    }, 1500)
  } catch (e: unknown) {
    status.value = 'error'
    errorMessage.value = e instanceof Error ? e.message : 'Failed to connect account'
  }
})

function detectProvider(): string {
  // Microsoft callbacks include session_state, Google does not
  if (route.query.session_state) return 'outlook'
  return 'gmail'
}
</script>

<template>
  <div class="flex min-h-screen items-center justify-center" :style="{ backgroundColor: 'var(--color-bg-primary)' }">
    <div class="text-center">
      <div v-if="status === 'processing'" class="space-y-4">
        <div
          class="mx-auto h-12 w-12 animate-spin rounded-full border-4 border-t-transparent"
          :style="{ borderColor: 'var(--color-border)', borderTopColor: 'var(--color-primary)' }"
        />
        <p class="text-sm" :style="{ color: 'var(--color-text-secondary)' }">Connecting your account...</p>
      </div>
      <div v-else-if="status === 'success'" class="space-y-4">
        <div
          class="mx-auto flex h-12 w-12 items-center justify-center rounded-full"
          :style="{ backgroundColor: 'var(--color-success)' + '22' }"
        >
          <svg class="h-6 w-6" :style="{ color: 'var(--color-success)' }" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" />
          </svg>
        </div>
        <p class="text-sm" :style="{ color: 'var(--color-text-secondary)' }">Account connected! Redirecting...</p>
      </div>
      <div v-else class="space-y-4">
        <div
          class="mx-auto flex h-12 w-12 items-center justify-center rounded-full"
          :style="{ backgroundColor: 'var(--color-error)' + '22' }"
        >
          <svg class="h-6 w-6" :style="{ color: 'var(--color-error)' }" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
          </svg>
        </div>
        <p class="text-sm" :style="{ color: 'var(--color-error)' }">{{ errorMessage }}</p>
        <button
          class="text-sm underline"
          :style="{ color: 'var(--color-primary)' }"
          @click="router.replace({ name: 'settings' })"
        >
          Back to Settings
        </button>
      </div>
    </div>
  </div>
</template>
