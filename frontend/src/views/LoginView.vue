<script setup lang="ts">
import { ref, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import BaseCard from '@/components/ui/BaseCard.vue'
import BaseButton from '@/components/ui/BaseButton.vue'
import BaseInput from '@/components/ui/BaseInput.vue'

const router = useRouter()
const authStore = useAuthStore()

const step = ref<'credentials' | 'totp'>('credentials')
const username = ref('')
const password = ref('')
const totpCode = ref('')
const error = ref('')
const loading = ref(false)
const usernameInput = ref<InstanceType<typeof BaseInput> | null>(null)
const totpInput = ref<InstanceType<typeof BaseInput> | null>(null)

async function handleCredentials() {
  error.value = ''
  loading.value = true
  try {
    await authStore.login({
      username: username.value,
      password: password.value,
    })
    step.value = 'totp'
    await nextTick()
    totpInput.value?.$el?.querySelector('input')?.focus()
  } catch (e: unknown) {
    error.value = e instanceof Error ? e.message : 'Login failed'
  } finally {
    loading.value = false
  }
}

async function handleTotp() {
  error.value = ''
  loading.value = true
  try {
    await authStore.verifyTotp(totpCode.value)
    router.replace({ name: 'dashboard' })
  } catch (e: unknown) {
    error.value = e instanceof Error ? e.message : 'Verification failed'
    if (error.value.includes('expired') || error.value.includes('challenge')) {
      step.value = 'credentials'
      error.value = 'Session expired, please sign in again'
    }
  } finally {
    loading.value = false
  }
}

function backToCredentials() {
  step.value = 'credentials'
  totpCode.value = ''
  error.value = ''
}
</script>

<template>
  <div class="flex min-h-screen items-center justify-center" :style="{ backgroundColor: 'var(--color-bg-primary)' }">
    <div class="w-full max-w-md px-4">
      <div class="mb-8 text-center">
        <h1 class="text-2xl font-bold" :style="{ color: 'var(--color-text-primary)' }">mail-manager</h1>
        <p class="mt-2 text-sm" :style="{ color: 'var(--color-text-muted)' }">Sign in to continue</p>
      </div>

      <!-- Step 1: Username + Password -->
      <BaseCard v-if="step === 'credentials'" title="Login">
        <form class="space-y-4" @submit.prevent="handleCredentials">
          <div>
            <label class="mb-1.5 block text-xs font-medium" :style="{ color: 'var(--color-text-secondary)' }">
              Username
            </label>
            <BaseInput ref="usernameInput" v-model="username" placeholder="Username" required autofocus />
          </div>
          <div>
            <label class="mb-1.5 block text-xs font-medium" :style="{ color: 'var(--color-text-secondary)' }">
              Password
            </label>
            <BaseInput v-model="password" type="password" placeholder="Password" required />
          </div>
          <p v-if="error" class="text-sm" :style="{ color: 'var(--color-error)' }">{{ error }}</p>
          <BaseButton type="submit" variant="primary" class="w-full" :disabled="loading">
            {{ loading ? 'Signing in...' : 'Continue' }}
          </BaseButton>
        </form>
        <div class="mt-4 text-center">
          <router-link
            to="/setup"
            class="text-sm hover:underline"
            :style="{ color: 'var(--color-accent)' }"
          >
            Create an account
          </router-link>
        </div>
      </BaseCard>

      <!-- Step 2: TOTP code -->
      <BaseCard v-if="step === 'totp'" title="Two-Factor Authentication" subtitle="Enter the code from your authenticator app">
        <form class="space-y-4" @submit.prevent="handleTotp">
          <div>
            <BaseInput
              ref="totpInput"
              v-model="totpCode"
              placeholder="000000"
              maxlength="6"
              class="text-center text-lg tracking-widest"
              required
            />
          </div>
          <p v-if="error" class="text-sm" :style="{ color: 'var(--color-error)' }">{{ error }}</p>
          <BaseButton type="submit" variant="primary" class="w-full" :disabled="loading">
            {{ loading ? 'Verifying...' : 'Verify' }}
          </BaseButton>
        </form>
        <div class="mt-4 text-center">
          <button
            class="text-sm hover:underline"
            :style="{ color: 'var(--color-text-muted)' }"
            @click="backToCredentials"
          >
            Back to login
          </button>
        </div>
      </BaseCard>
    </div>
  </div>
</template>
