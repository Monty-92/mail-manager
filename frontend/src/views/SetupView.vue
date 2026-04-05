<script setup lang="ts">
import { ref, onMounted, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import { setupAccount, getSetupQrUrl } from '@/api/auth'
import { useAuthStore } from '@/stores/auth'
import BaseCard from '@/components/ui/BaseCard.vue'
import BaseButton from '@/components/ui/BaseButton.vue'
import BaseInput from '@/components/ui/BaseInput.vue'

const router = useRouter()
const authStore = useAuthStore()

const step = ref<'credentials' | 'totp'>('credentials')
const username = ref('')
const password = ref('')
const confirmPassword = ref('')
const totpUri = ref('')
const totpSecret = ref('')
const qrUrl = ref('')
const totpCode = ref('')
const error = ref('')
const loading = ref(false)
const totpInput = ref<InstanceType<typeof BaseInput> | null>(null)

onMounted(async () => {
  const done = await authStore.checkSetupStatus()
  if (done) {
    router.replace({ name: 'login' })
  }
})

async function handleSetup() {
  error.value = ''
  if (password.value !== confirmPassword.value) {
    error.value = 'Passwords do not match'
    return
  }
  loading.value = true
  try {
    const resp = await setupAccount({ username: username.value, password: password.value })
    totpUri.value = resp.totp_uri

    // Extract secret from otpauth URI
    const match = resp.totp_uri.match(/secret=([A-Z2-7]+)/i)
    totpSecret.value = match ? match[1] : ''
    qrUrl.value = getSetupQrUrl(resp.username, totpSecret.value)
    step.value = 'totp'
    await nextTick()
    totpInput.value?.$el?.querySelector('input')?.focus()
  } catch (e: unknown) {
    error.value = e instanceof Error ? e.message : 'Setup failed'
  } finally {
    loading.value = false
  }
}

async function handleVerify() {
  error.value = ''
  loading.value = true
  try {
    await authStore.login({
      username: username.value,
      password: password.value,
    })
    await authStore.verifyTotp(totpCode.value)
    authStore.isSetupComplete = true
    router.replace({ name: 'dashboard' })
  } catch (e: unknown) {
    error.value = e instanceof Error ? e.message : 'Verification failed'
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
        <p class="mt-2 text-sm" :style="{ color: 'var(--color-text-muted)' }">Initial Setup</p>
      </div>

      <!-- Step 1: Create account -->
      <BaseCard v-if="step === 'credentials'" title="Create Your Account" subtitle="Set up your admin credentials">
        <form class="space-y-4" @submit.prevent="handleSetup">
          <div>
            <label class="mb-1.5 block text-xs font-medium" :style="{ color: 'var(--color-text-secondary)' }">
              Username
            </label>
            <BaseInput v-model="username" placeholder="admin" required autofocus />
          </div>
          <div>
            <label class="mb-1.5 block text-xs font-medium" :style="{ color: 'var(--color-text-secondary)' }">
              Password
            </label>
            <BaseInput v-model="password" type="password" placeholder="Min 8 characters" required />
          </div>
          <div>
            <label class="mb-1.5 block text-xs font-medium" :style="{ color: 'var(--color-text-secondary)' }">
              Confirm Password
            </label>
            <BaseInput v-model="confirmPassword" type="password" placeholder="Repeat password" required />
          </div>
          <p v-if="error" class="text-sm" :style="{ color: 'var(--color-error)' }">{{ error }}</p>
          <BaseButton type="submit" variant="primary" class="w-full" :disabled="loading">
            {{ loading ? 'Creating...' : 'Continue' }}
          </BaseButton>
        </form>
      </BaseCard>

      <!-- Step 2: TOTP setup -->
      <BaseCard v-if="step === 'totp'" title="Set Up Two-Factor Auth" subtitle="Scan this QR code with your authenticator app">
        <div class="space-y-4">
          <div class="flex justify-center">
            <img
              v-if="qrUrl"
              :src="qrUrl"
              alt="TOTP QR Code"
              class="h-48 w-48 rounded-lg border"
              :style="{ borderColor: 'var(--color-border)' }"
            />
          </div>
          <div>
            <label class="mb-1.5 block text-xs font-medium" :style="{ color: 'var(--color-text-secondary)' }">
              Manual entry key
            </label>
            <code
              class="block rounded-lg px-3 py-2 text-xs break-all"
              :style="{ backgroundColor: 'var(--color-bg-tertiary)', color: 'var(--color-text-secondary)' }"
            >
              {{ totpSecret }}
            </code>
          </div>
          <form @submit.prevent="handleVerify">
            <label class="mb-1.5 block text-xs font-medium" :style="{ color: 'var(--color-text-secondary)' }">
              Enter the 6-digit code from your authenticator
            </label>
            <BaseInput
              ref="totpInput"
              v-model="totpCode"
              placeholder="000000"
              maxlength="6"
              class="mb-3 text-center text-lg tracking-widest"
              required
            />
            <p v-if="error" class="mb-3 text-sm" :style="{ color: 'var(--color-error)' }">{{ error }}</p>
            <BaseButton type="submit" variant="primary" class="w-full" :disabled="loading">
              {{ loading ? 'Verifying...' : 'Verify & Login' }}
            </BaseButton>
          </form>
        </div>
      </BaseCard>
    </div>
  </div>
</template>
