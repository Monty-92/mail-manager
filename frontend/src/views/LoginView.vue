<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import BaseCard from '@/components/ui/BaseCard.vue'
import BaseButton from '@/components/ui/BaseButton.vue'
import BaseInput from '@/components/ui/BaseInput.vue'

const router = useRouter()
const authStore = useAuthStore()

const username = ref('')
const password = ref('')
const totpCode = ref('')
const error = ref('')
const loading = ref(false)

async function handleLogin() {
  error.value = ''
  loading.value = true
  try {
    await authStore.login({
      username: username.value,
      password: password.value,
      totp_code: totpCode.value,
    })
    router.replace({ name: 'dashboard' })
  } catch (e: unknown) {
    error.value = e instanceof Error ? e.message : 'Login failed'
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="flex min-h-screen items-center justify-center" :style="{ backgroundColor: 'var(--color-bg-primary)' }">
    <div class="w-full max-w-md px-4">
      <div class="mb-8 text-center">
        <h1 class="text-2xl font-bold" :style="{ color: 'var(--color-text-primary)' }">mail-manager</h1>
        <p class="mt-2 text-sm" :style="{ color: 'var(--color-text-muted)' }">Sign in to continue</p>
      </div>

      <BaseCard title="Login">
        <form class="space-y-4" @submit.prevent="handleLogin">
          <div>
            <label class="mb-1.5 block text-xs font-medium" :style="{ color: 'var(--color-text-secondary)' }">
              Username
            </label>
            <BaseInput v-model="username" placeholder="Username" required />
          </div>
          <div>
            <label class="mb-1.5 block text-xs font-medium" :style="{ color: 'var(--color-text-secondary)' }">
              Password
            </label>
            <BaseInput v-model="password" type="password" placeholder="Password" required />
          </div>
          <div>
            <label class="mb-1.5 block text-xs font-medium" :style="{ color: 'var(--color-text-secondary)' }">
              Authenticator Code
            </label>
            <BaseInput
              v-model="totpCode"
              placeholder="000000"
              maxlength="6"
              class="text-center text-lg tracking-widest"
              required
            />
          </div>
          <p v-if="error" class="text-sm" :style="{ color: 'var(--color-error)' }">{{ error }}</p>
          <BaseButton type="submit" variant="primary" class="w-full" :disabled="loading">
            {{ loading ? 'Signing in...' : 'Sign In' }}
          </BaseButton>
        </form>
      </BaseCard>
    </div>
  </div>
</template>
