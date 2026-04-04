<script setup lang="ts">
import { ref, computed } from 'vue'
import {
  SunIcon,
  MoonIcon,
  ComputerDesktopIcon,
  SwatchIcon,
  ArrowPathIcon,
  PlusIcon,
  TrashIcon,
  CheckIcon,
} from '@heroicons/vue/24/outline'
import { useThemeStore } from '@/stores/theme'
import { useToast } from '@/composables/useToast'
import type { ThemeMode, ThemeColors } from '@/types'
import BaseCard from '@/components/ui/BaseCard.vue'
import BaseButton from '@/components/ui/BaseButton.vue'
import BaseInput from '@/components/ui/BaseInput.vue'

const themeStore = useThemeStore()
const toast = useToast()

const activeTab = ref<'appearance' | 'accounts' | 'llm' | 'sync'>('appearance')

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
const connectedAccounts = ref<Array<{ id: string; provider: string; email: string; status: string }>>([])
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
      <BaseCard title="Connected Accounts" subtitle="Manage your Gmail and Outlook connections">
        <template #header>
          <BaseButton variant="primary" size="sm">
            <PlusIcon class="h-4 w-4" />
            Connect Account
          </BaseButton>
        </template>

        <div v-if="connectedAccounts.length === 0">
          <p class="text-sm" :style="{ color: 'var(--color-text-muted)' }">
            No accounts connected. Click "Connect Account" to add your Gmail or Outlook email accounts.
          </p>
          <div class="mt-4 grid gap-3 sm:grid-cols-2">
            <button
              class="flex items-center gap-3 rounded-lg border p-4 transition-all duration-150 hover:shadow-sm"
              :style="{
                borderColor: 'var(--color-border)',
                backgroundColor: 'var(--color-bg-primary)',
              }"
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
                <p class="text-xs" :style="{ color: 'var(--color-text-muted)' }">Connect Gmail account</p>
              </div>
            </button>
            <button
              class="flex items-center gap-3 rounded-lg border p-4 transition-all duration-150 hover:shadow-sm"
              :style="{
                borderColor: 'var(--color-border)',
                backgroundColor: 'var(--color-bg-primary)',
              }"
            >
              <div class="flex h-10 w-10 items-center justify-center rounded-lg" style="background-color: #0078d41a">
                <svg class="h-5 w-5" viewBox="0 0 24 24" fill="#0078d4">
                  <path d="M1 5.8V18.2L8.7 12 1 5.8zM1.5 5L12 14.5 22.5 5H1.5zM15.3 12L23 18.2V5.8L15.3 12zM14.6 12.6L12 15.1 9.4 12.6 1.5 19H22.5L14.6 12.6z" />
                </svg>
              </div>
              <div class="text-left">
                <p class="text-sm font-medium" :style="{ color: 'var(--color-text-primary)' }">Outlook</p>
                <p class="text-xs" :style="{ color: 'var(--color-text-muted)' }">Connect Microsoft account</p>
              </div>
            </button>
          </div>
        </div>

        <div v-else class="space-y-3">
          <div
            v-for="account in connectedAccounts"
            :key="account.id"
            class="flex items-center justify-between rounded-lg border p-3"
            :style="{ borderColor: 'var(--color-border)' }"
          >
            <div class="flex items-center gap-3">
              <div
                class="h-8 w-8 rounded-full flex items-center justify-center text-white text-sm font-semibold"
                :style="{
                  backgroundColor: account.provider === 'gmail' ? '#4285f4' : '#0078d4',
                }"
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
            >
              <TrashIcon class="h-4 w-4" />
            </button>
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
            <select
              class="w-full rounded-lg border bg-transparent px-3 py-2 text-sm outline-none"
              :style="{ borderColor: 'var(--color-border)', color: 'var(--color-text-primary)' }"
            >
              <option value="llama3.1:8b">llama3.1:8b (default)</option>
              <option value="llama3.1:70b">llama3.1:70b</option>
              <option value="mistral:7b">mistral:7b</option>
            </select>
          </div>
          <div>
            <label class="mb-1.5 block text-xs font-medium" :style="{ color: 'var(--color-text-secondary)' }">
              Embedding Model
            </label>
            <select
              class="w-full rounded-lg border bg-transparent px-3 py-2 text-sm outline-none"
              :style="{ borderColor: 'var(--color-border)', color: 'var(--color-text-primary)' }"
            >
              <option value="nomic-embed-text">nomic-embed-text (default)</option>
            </select>
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
            <div
              class="relative h-6 w-11 cursor-pointer rounded-full transition-colors"
              :style="{ backgroundColor: 'var(--color-primary)' }"
            >
              <div
                class="absolute top-0.5 left-5 h-5 w-5 rounded-full bg-white shadow transition-transform"
              />
            </div>
          </div>
          <div class="flex items-center justify-between">
            <div>
              <p class="text-sm font-medium" :style="{ color: 'var(--color-text-primary)' }">Auto-analyze</p>
              <p class="text-xs" :style="{ color: 'var(--color-text-muted)' }">
                Automatically analyze new emails with the LLM
              </p>
            </div>
            <div
              class="relative h-6 w-11 cursor-pointer rounded-full transition-colors"
              :style="{ backgroundColor: 'var(--color-primary)' }"
            >
              <div
                class="absolute top-0.5 left-5 h-5 w-5 rounded-full bg-white shadow transition-transform"
              />
            </div>
          </div>
        </div>
      </BaseCard>

      <BaseCard title="Manual Actions" subtitle="Trigger batch operations manually">
        <div class="flex flex-wrap gap-3">
          <BaseButton variant="secondary">
            <ArrowPathIcon class="h-4 w-4" />
            Sync All Emails
          </BaseButton>
          <BaseButton variant="secondary">
            <ArrowPathIcon class="h-4 w-4" />
            Preprocess Batch
          </BaseButton>
          <BaseButton variant="secondary">
            <ArrowPathIcon class="h-4 w-4" />
            Analyze Batch
          </BaseButton>
        </div>
      </BaseCard>
    </div>
  </div>
</template>
