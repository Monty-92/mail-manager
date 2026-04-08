<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import {
  SunIcon,
  MoonIcon,
  ComputerDesktopIcon,
  SwatchIcon,
  ArrowPathIcon,
  PlusIcon,
  TrashIcon,
  CheckIcon,
  QrCodeIcon,
} from '@heroicons/vue/24/outline'
import { useThemeStore } from '@/stores/theme'
import { useAccountStore } from '@/stores/account'
import { useToast } from '@/composables/useToast'
import type { ThemeMode, ThemeColors } from '@/types'
import BaseCard from '@/components/ui/BaseCard.vue'
import BaseButton from '@/components/ui/BaseButton.vue'
import BaseInput from '@/components/ui/BaseInput.vue'
import { getSettings, updateSetting } from '@/api/settings'
import { api } from '@/api/client'

const themeStore = useThemeStore()
const accountStore = useAccountStore()
const toast = useToast()

const activeTab = ref<'appearance' | 'accounts' | 'llm' | 'sync'>('appearance')

// Device flow state
const deviceFlowActive = ref(false)
const deviceFlowProvider = ref('')
const deviceFlowUserCode = ref('')
const deviceFlowUri = ref('')
const deviceFlowPolling = ref(false)

// ─── LLM / Sync settings ───
const settingsLoaded = ref(false)
const settingsSaving = ref<Record<string, boolean>>({})
const llmModel = ref('llama3.1:8b')
const embedModel = ref('nomic-embed-text')
const autoSync = ref(true)
const autoAnalyze = ref(true)
const syncLoading = ref<Record<string, boolean>>({})

async function loadSettings() {
  try {
    const data = await getSettings()
    if (data.llm_model) llmModel.value = data.llm_model
    if (data.embed_model) embedModel.value = data.embed_model
    autoSync.value = data.auto_sync !== 'false'
    autoAnalyze.value = data.auto_analyze !== 'false'
    settingsLoaded.value = true
  } catch {
    // non-fatal — use defaults
    settingsLoaded.value = true
  }
}

async function saveSetting(key: string, value: string) {
  settingsSaving.value[key] = true
  try {
    await updateSetting(key, value)
    toast.success('Setting saved')
  } catch (e: unknown) {
    toast.error(e instanceof Error ? e.message : 'Failed to save')
  } finally {
    settingsSaving.value[key] = false
  }
}

async function toggleAutoSync() {
  autoSync.value = !autoSync.value
  await saveSetting('auto_sync', String(autoSync.value))
}

async function toggleAutoAnalyze() {
  autoAnalyze.value = !autoAnalyze.value
  await saveSetting('auto_analyze', String(autoAnalyze.value))
}

async function triggerSync(endpoint: string, label: string) {
  syncLoading.value[endpoint] = true
  try {
    await api.post(`/${endpoint}`)
    toast.success(`${label} triggered`)
  } catch (e: unknown) {
    toast.error(e instanceof Error ? e.message : `Failed to trigger ${label}`)
  } finally {
    syncLoading.value[endpoint] = false
  }
}

onMounted(async () => {
  await Promise.all([accountStore.fetchAccounts(), loadSettings()])
})

const tabs = [
  { id: 'appearance' as const, label: 'Appearance' },
  { id: 'accounts' as const, label: 'Accounts' },
  { id: 'llm' as const, label: 'LLM' },
  { id: 'sync' as const, label: 'Sync' },
]

const themeOptions: Array<{ mode: ThemeMode; label: string; icon: typeof SunIcon }> = [
  { mode: 'light', label: 'Light', icon: SunIcon },
  { mode: 'dark', label: 'Dark', icon: MoonIcon },
  { mode: 'system', label: 'System', icon: ComputerDesktopIcon },
]

// Color customization
const editingColor = ref<keyof ThemeColors | null>(null)
const colorValue = ref('')

const colorGroups = [
  {
    label: 'Brand',
    colors: [
      { key: 'primary' as const, label: 'Primary' },
      { key: 'primaryHover' as const, label: 'Primary Hover' },
      { key: 'accent' as const, label: 'Accent' },
      { key: 'accentHover' as const, label: 'Accent Hover' },
    ],
  },
  {
    label: 'Backgrounds',
    colors: [
      { key: 'bgPrimary' as const, label: 'Primary BG' },
      { key: 'bgSecondary' as const, label: 'Secondary BG' },
      { key: 'bgTertiary' as const, label: 'Tertiary BG' },
      { key: 'bgSidebar' as const, label: 'Sidebar BG' },
    ],
  },
  {
    label: 'Text',
    colors: [
      { key: 'textPrimary' as const, label: 'Primary Text' },
      { key: 'textSecondary' as const, label: 'Secondary Text' },
      { key: 'textMuted' as const, label: 'Muted Text' },
    ],
  },
  {
    label: 'Status',
    colors: [
      { key: 'success' as const, label: 'Success' },
      { key: 'warning' as const, label: 'Warning' },
      { key: 'error' as const, label: 'Error' },
      { key: 'info' as const, label: 'Info' },
    ],
  },
]

function startEditColor(key: keyof ThemeColors) {
  editingColor.value = key
  colorValue.value = themeStore.activeColors[key]
}

function applyColor() {
  if (editingColor.value && colorValue.value) {
    themeStore.setCustomColor(editingColor.value, colorValue.value)
    editingColor.value = null
    toast.success('Color updated')
  }
}

function resetColors() {
  themeStore.resetCustomColors()
  toast.info('Colors reset to defaults')
}

// Account management (placeholder)
const connectedAccounts = computed(() =>
  accountStore.accounts.map((a) => ({
    id: a.id,
    provider: a.provider,
    email: a.email,
    status: 'connected',
  }))
)

async function connectProvider(provider: string) {
  try {
    await accountStore.connectViaRedirect(provider)
  } catch (e: unknown) {
    toast.error(e instanceof Error ? e.message : 'Failed to start connection')
  }
}

async function startDeviceFlow(provider: string) {
  try {
    deviceFlowProvider.value = provider
    const resp = await accountStore.startDeviceFlow(provider)
    deviceFlowUserCode.value = resp.user_code
    deviceFlowUri.value = resp.verification_uri_complete || resp.verification_uri
    deviceFlowActive.value = true
    deviceFlowPolling.value = true

    // Start polling
    const deviceCode = resp.device_code
    const interval = (resp.interval || 5) * 1000
    const pollInterval = setInterval(async () => {
      try {
        const poll = await accountStore.pollDeviceFlow(provider, deviceCode)
        if (poll.status === 'complete') {
          clearInterval(pollInterval)
          deviceFlowActive.value = false
          deviceFlowPolling.value = false
          toast.success(`Connected ${poll.email}`)
        } else if (poll.status === 'expired') {
          clearInterval(pollInterval)
          deviceFlowActive.value = false
          deviceFlowPolling.value = false
          toast.error('Device flow expired. Please try again.')
        }
      } catch {
        clearInterval(pollInterval)
        deviceFlowActive.value = false
        deviceFlowPolling.value = false
      }
    }, interval)
  } catch (e: unknown) {
    toast.error(e instanceof Error ? e.message : 'Failed to start device flow')
  }
}

async function removeAccount(id: string) {
  try {
    await accountStore.disconnect(id)
    toast.success('Account disconnected')
  } catch (e: unknown) {
    toast.error(e instanceof Error ? e.message : 'Failed to disconnect')
  }
}
</script>

<template>
  <div class="mx-auto max-w-4xl">
    <!-- Tab navigation -->
    <div class="mb-6 flex border-b" :style="{ borderColor: 'var(--color-border)' }">
      <button
        v-for="tab in tabs"
        :key="tab.id"
        class="relative px-4 py-3 text-sm font-medium transition-colors"
        :style="{
          color: activeTab === tab.id ? 'var(--color-primary)' : 'var(--color-text-muted)',
        }"
        @click="activeTab = tab.id"
      >
        {{ tab.label }}
        <div
          v-if="activeTab === tab.id"
          class="absolute bottom-0 left-0 right-0 h-0.5"
          :style="{ backgroundColor: 'var(--color-primary)' }"
        />
      </button>
    </div>

    <!-- Appearance tab -->
    <div v-if="activeTab === 'appearance'" class="space-y-6">
      <!-- Theme mode -->
      <BaseCard title="Theme Mode" subtitle="Choose how mail-manager looks to you">
        <div class="flex gap-3">
          <button
            v-for="opt in themeOptions"
            :key="opt.mode"
            class="flex flex-1 flex-col items-center gap-2 rounded-xl border p-4 transition-all duration-150"
            :style="{
              borderColor:
                themeStore.mode === opt.mode ? 'var(--color-primary)' : 'var(--color-border)',
              backgroundColor:
                themeStore.mode === opt.mode ? 'var(--color-primary)' + '0a' : 'transparent',
            }"
            @click="themeStore.setMode(opt.mode)"
          >
            <component
              :is="opt.icon"
              class="h-6 w-6"
              :style="{
                color:
                  themeStore.mode === opt.mode
                    ? 'var(--color-primary)'
                    : 'var(--color-text-muted)',
              }"
            />
            <span
              class="text-sm font-medium"
              :style="{
                color:
                  themeStore.mode === opt.mode
                    ? 'var(--color-primary)'
                    : 'var(--color-text-secondary)',
              }"
            >
              {{ opt.label }}
            </span>
          </button>
        </div>
      </BaseCard>

      <!-- Color customization -->
      <BaseCard title="Color Customization" subtitle="Customize colors for the current theme mode">
        <template #header>
          <BaseButton variant="ghost" size="sm" @click="resetColors">
            <ArrowPathIcon class="h-3.5 w-3.5" />
            Reset
          </BaseButton>
        </template>

        <div class="space-y-5">
          <div v-for="group in colorGroups" :key="group.label">
            <h4
              class="mb-3 text-xs font-semibold uppercase tracking-wider"
              :style="{ color: 'var(--color-text-muted)' }"
            >
              {{ group.label }}
            </h4>
            <div class="grid grid-cols-2 gap-3 sm:grid-cols-4">
              <button
                v-for="color in group.colors"
                :key="color.key"
                class="flex items-center gap-2.5 rounded-lg border p-2.5 transition-all duration-150"
                :style="{
                  borderColor:
                    editingColor === color.key ? 'var(--color-primary)' : 'var(--color-border)',
                }"
                @click="startEditColor(color.key)"
              >
                <span
                  class="h-6 w-6 rounded-md flex-shrink-0 border"
                  :style="{
                    backgroundColor: themeStore.activeColors[color.key],
                    borderColor: 'var(--color-border)',
                  }"
                />
                <span class="text-xs" :style="{ color: 'var(--color-text-secondary)' }">
                  {{ color.label }}
                </span>
              </button>
            </div>
          </div>

          <!-- Color editor -->
          <Transition
            enter-active-class="transition duration-200 ease-out"
            enter-from-class="-translate-y-2 opacity-0"
            enter-to-class="translate-y-0 opacity-100"
            leave-active-class="transition duration-150 ease-in"
            leave-from-class="translate-y-0 opacity-100"
            leave-to-class="-translate-y-2 opacity-0"
          >
            <div
              v-if="editingColor"
              class="flex items-center gap-3 rounded-lg border p-3"
              :style="{
                backgroundColor: 'var(--color-bg-tertiary)',
                borderColor: 'var(--color-border)',
              }"
            >
              <input
                v-model="colorValue"
                type="color"
                class="h-10 w-10 cursor-pointer rounded border-0"
              />
              <BaseInput
                v-model="colorValue"
                placeholder="#000000"
                class="flex-1"
              />
              <BaseButton variant="primary" size="sm" @click="applyColor">
                <CheckIcon class="h-4 w-4" />
                Apply
              </BaseButton>
              <BaseButton variant="ghost" size="sm" @click="editingColor = null">
                Cancel
              </BaseButton>
            </div>
          </Transition>
        </div>
      </BaseCard>
    </div>

    <!-- Accounts tab -->
    <div v-if="activeTab === 'accounts'" class="space-y-6">
      <!-- Device flow modal -->
      <div
        v-if="deviceFlowActive"
        class="fixed inset-0 z-50 flex items-center justify-center bg-black/50"
        @click.self="deviceFlowActive = false"
      >
        <div
          class="mx-4 w-full max-w-sm rounded-xl p-6 shadow-xl"
          :style="{ backgroundColor: 'var(--color-bg-secondary)' }"
        >
          <h3 class="mb-2 text-lg font-semibold" :style="{ color: 'var(--color-text-primary)' }">
            Connect via QR Code
          </h3>
          <p class="mb-4 text-sm" :style="{ color: 'var(--color-text-secondary)' }">
            Open this URL on your phone and enter the code:
          </p>
          <div
            class="mb-4 rounded-lg p-4 text-center"
            :style="{ backgroundColor: 'var(--color-bg-tertiary)' }"
          >
            <a
              :href="deviceFlowUri"
              target="_blank"
              class="text-sm underline break-all"
              :style="{ color: 'var(--color-primary)' }"
            >
              {{ deviceFlowUri }}
            </a>
            <p class="mt-3 text-2xl font-mono font-bold tracking-widest" :style="{ color: 'var(--color-text-primary)' }">
              {{ deviceFlowUserCode }}
            </p>
          </div>
          <div v-if="deviceFlowPolling" class="flex items-center justify-center gap-2">
            <div
              class="h-4 w-4 animate-spin rounded-full border-2 border-t-transparent"
              :style="{ borderColor: 'var(--color-border)', borderTopColor: 'var(--color-primary)' }"
            />
            <span class="text-xs" :style="{ color: 'var(--color-text-muted)' }">Waiting for authorization...</span>
          </div>
          <BaseButton variant="ghost" size="sm" class="mt-4 w-full" @click="deviceFlowActive = false">
            Cancel
          </BaseButton>
        </div>
      </div>

      <BaseCard title="Connected Accounts" subtitle="Manage your Gmail connections">
        <div class="space-y-4">
          <!-- Provider connection buttons -->
          <div class="max-w-sm">
            <div class="space-y-2">
              <button
                class="flex w-full items-center gap-3 rounded-lg border p-4 transition-all duration-150 hover:shadow-sm"
                :style="{ borderColor: 'var(--color-border)', backgroundColor: 'var(--color-bg-primary)' }"
                @click="connectProvider('gmail')"
              >
                <div class="flex h-10 w-10 items-center justify-center rounded-lg" style="background-color: #4285f41a">
                  <svg class="h-5 w-5" viewBox="0 0 24 24" fill="#4285f4">
                    <path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92a5.06 5.06 0 01-2.2 3.32v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" />
                    <path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" fill="#34a853" />
                    <path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" fill="#fbbc05" />
                    <path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" fill="#ea4335" />
                  </svg>
                </div>
                <div class="text-left">
                  <p class="text-sm font-medium" :style="{ color: 'var(--color-text-primary)' }">Gmail</p>
                  <p class="text-xs" :style="{ color: 'var(--color-text-muted)' }">Connect via redirect</p>
                </div>
              </button>
              <button
                class="flex w-full items-center gap-2 rounded-lg px-4 py-2 text-xs transition-colors"
                :style="{ color: 'var(--color-text-muted)' }"
                @click="startDeviceFlow('gmail')"
              >
                <QrCodeIcon class="h-4 w-4" />
                Use QR code instead
              </button>
            </div>
          </div>

          <!-- Connected accounts list -->
          <div v-if="connectedAccounts.length > 0" class="space-y-3">
            <h4 class="text-xs font-semibold uppercase tracking-wider" :style="{ color: 'var(--color-text-muted)' }">
              Connected
            </h4>
            <div
              v-for="account in connectedAccounts"
              :key="account.id"
              class="flex items-center justify-between rounded-lg border p-3"
              :style="{ borderColor: 'var(--color-border)' }"
            >
              <div class="flex items-center gap-3">
                <div
                  class="h-8 w-8 rounded-full flex items-center justify-center text-white text-sm font-semibold"
                  :style="{ backgroundColor: account.provider === 'gmail' ? '#4285f4' : '#0078d4' }"
                >
                  {{ account.email.charAt(0).toUpperCase() }}
                </div>
                <div>
                  <p class="text-sm font-medium" :style="{ color: 'var(--color-text-primary)' }">
                    {{ account.email }}
                  </p>
                  <p class="text-xs capitalize" :style="{ color: 'var(--color-text-muted)' }">
                    {{ account.provider }} · {{ account.status }}
                  </p>
                </div>
              </div>
              <button
                class="rounded p-1.5 transition-colors hover:opacity-70"
                :style="{ color: 'var(--color-error)' }"
                @click="removeAccount(account.id)"
              >
                <TrashIcon class="h-4 w-4" />
              </button>
            </div>
          </div>
        </div>
      </BaseCard>
    </div>

    <!-- LLM tab -->
    <div v-if="activeTab === 'llm'" class="space-y-6">
      <BaseCard title="LLM Configuration" subtitle="Configure the local language model settings">
        <div class="space-y-4">
          <div>
            <label class="mb-1.5 block text-xs font-medium" :style="{ color: 'var(--color-text-secondary)' }">
              Model
            </label>
            <div class="flex gap-2">
              <select
                v-model="llmModel"
                class="flex-1 rounded-lg border bg-transparent px-3 py-2 text-sm outline-none"
                :style="{ borderColor: 'var(--color-border)', color: 'var(--color-text-primary)' }"
              >
                <option value="llama3.1:8b">llama3.1:8b (default)</option>
                <option value="llama3.1:70b">llama3.1:70b</option>
                <option value="mistral:7b">mistral:7b</option>
              </select>
              <BaseButton
                variant="secondary"
                size="sm"
                :loading="settingsSaving['llm_model']"
                @click="saveSetting('llm_model', llmModel)"
              >
                Save
              </BaseButton>
            </div>
          </div>
          <div>
            <label class="mb-1.5 block text-xs font-medium" :style="{ color: 'var(--color-text-secondary)' }">
              Embedding Model
            </label>
            <div class="flex gap-2">
              <select
                v-model="embedModel"
                class="flex-1 rounded-lg border bg-transparent px-3 py-2 text-sm outline-none"
                :style="{ borderColor: 'var(--color-border)', color: 'var(--color-text-primary)' }"
              >
                <option value="nomic-embed-text">nomic-embed-text (default)</option>
              </select>
              <BaseButton
                variant="secondary"
                size="sm"
                :loading="settingsSaving['embed_model']"
                @click="saveSetting('embed_model', embedModel)"
              >
                Save
              </BaseButton>
            </div>
          </div>
          <div>
            <label class="mb-1.5 block text-xs font-medium" :style="{ color: 'var(--color-text-secondary)' }">
              Ollama URL
            </label>
            <BaseInput model-value="http://ollama:11434" placeholder="http://ollama:11434" disabled />
            <p class="mt-1 text-xs" :style="{ color: 'var(--color-text-muted)' }">
              Managed by Docker Compose
            </p>
          </div>
        </div>
      </BaseCard>
    </div>

    <!-- Sync tab -->
    <div v-if="activeTab === 'sync'" class="space-y-6">
      <BaseCard title="Email Sync" subtitle="Control email ingestion and processing">
        <div class="space-y-4">
          <div class="flex items-center justify-between">
            <div>
              <p class="text-sm font-medium" :style="{ color: 'var(--color-text-primary)' }">Auto-sync</p>
              <p class="text-xs" :style="{ color: 'var(--color-text-muted)' }">
                Automatically sync new emails from connected accounts
              </p>
            </div>
            <button
              class="relative h-6 w-11 rounded-full transition-colors focus:outline-none"
              :style="{ backgroundColor: autoSync ? 'var(--color-primary)' : 'var(--color-border)' }"
              :aria-checked="autoSync"
              role="switch"
              @click="toggleAutoSync"
            >
              <span
                class="absolute top-0.5 h-5 w-5 rounded-full bg-white shadow transition-transform duration-200"
                :style="{ transform: autoSync ? 'translateX(20px)' : 'translateX(2px)' }"
              />
            </button>
          </div>
          <div class="flex items-center justify-between">
            <div>
              <p class="text-sm font-medium" :style="{ color: 'var(--color-text-primary)' }">Auto-analyze</p>
              <p class="text-xs" :style="{ color: 'var(--color-text-muted)' }">
                Automatically analyze new emails with the LLM
              </p>
            </div>
            <button
              class="relative h-6 w-11 rounded-full transition-colors focus:outline-none"
              :style="{ backgroundColor: autoAnalyze ? 'var(--color-primary)' : 'var(--color-border)' }"
              :aria-checked="autoAnalyze"
              role="switch"
              @click="toggleAutoAnalyze"
            >
              <span
                class="absolute top-0.5 h-5 w-5 rounded-full bg-white shadow transition-transform duration-200"
                :style="{ transform: autoAnalyze ? 'translateX(20px)' : 'translateX(2px)' }"
              />
            </button>
          </div>
        </div>
      </BaseCard>

      <BaseCard title="Manual Actions" subtitle="Trigger batch operations manually">
        <div class="flex flex-wrap gap-3">
          <BaseButton
            variant="secondary"
            :loading="syncLoading['ingest/sync/gmail']"
            @click="triggerSync('ingest/sync/gmail', 'Gmail sync')"
          >
            <ArrowPathIcon class="h-4 w-4" />
            Sync All Emails
          </BaseButton>
          <BaseButton
            variant="secondary"
            :loading="syncLoading['tasks/sync/full']"
            @click="triggerSync('tasks/sync/full', 'Google Tasks sync')"
          >
            <ArrowPathIcon class="h-4 w-4" />
            Sync Google Tasks
          </BaseButton>
          <BaseButton
            variant="secondary"
            :loading="syncLoading['preprocessing/run']"
            @click="triggerSync('preprocessing/run', 'Preprocessing batch')"
          >
            <ArrowPathIcon class="h-4 w-4" />
            Preprocess Batch
          </BaseButton>
          <BaseButton
            variant="secondary"
            :loading="syncLoading['analysis/run']"
            @click="triggerSync('analysis/run', 'Analysis batch')"
          >
            <ArrowPathIcon class="h-4 w-4" />
            Analyze Batch
          </BaseButton>
        </div>
      </BaseCard>
    </div>
  </div>
</template>
