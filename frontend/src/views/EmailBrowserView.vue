<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import {
  MagnifyingGlassIcon,
  FunnelIcon,
  EnvelopeIcon,
  ArrowPathIcon,
  ChevronRightIcon,
  TagIcon,
  ExclamationCircleIcon,
  ClockIcon,
} from '@heroicons/vue/24/outline'
import { useEmailStore } from '@/stores/email'
import { useMarkdown } from '@/composables/useMarkdown'
import type { Email, EmailAnalysis } from '@/types'
import BaseCard from '@/components/ui/BaseCard.vue'
import BaseButton from '@/components/ui/BaseButton.vue'
import BaseInput from '@/components/ui/BaseInput.vue'
import StatusBadge from '@/components/ui/StatusBadge.vue'
import EmptyState from '@/components/ui/EmptyState.vue'
import SkeletonLoader from '@/components/ui/SkeletonLoader.vue'

const emailStore = useEmailStore()
const { renderMarkdown } = useMarkdown()
const search = ref('')
const selectedEmail = ref<Email | null>(null)
const analysis = ref<EmailAnalysis | null>(null)
const loadingAnalysis = ref(false)

const filteredEmails = computed(() => {
  if (!search.value) return emailStore.emails
  const q = search.value.toLowerCase()
  return emailStore.emails.filter(
    (e) =>
      e.subject.toLowerCase().includes(q) ||
      e.sender.toLowerCase().includes(q) ||
      e.markdown_body.toLowerCase().includes(q),
  )
})

async function selectEmail(email: Email) {
  selectedEmail.value = email
  loadingAnalysis.value = true
  try {
    await emailStore.fetchAnalysis(email.id)
    analysis.value = emailStore.currentAnalysis
  } catch {
    analysis.value = null
  } finally {
    loadingAnalysis.value = false
  }
}

function formatDate(dateStr: string): string {
  const d = new Date(dateStr)
  const now = new Date()
  const diff = now.getTime() - d.getTime()
  const hours = Math.floor(diff / (1000 * 60 * 60))
  if (hours < 1) return 'Just now'
  if (hours < 24) return `${hours}h ago`
  const days = Math.floor(hours / 24)
  if (days < 7) return `${days}d ago`
  return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
}

function senderName(email: string): string {
  const match = email.match(/^(.+?)\s*</)
  if (match) return match[1].trim()
  return email.split('@')[0]
}

onMounted(() => {
  emailStore.fetchEmails()
})
</script>

<template>
  <div class="mx-auto flex h-full max-w-7xl gap-6">
    <!-- Email list panel -->
    <div class="flex w-96 flex-shrink-0 flex-col">
      <!-- Search and filters -->
      <div class="mb-4 flex items-center gap-2">
        <div class="flex-1">
          <BaseInput
            v-model="search"
            type="search"
            placeholder="Search emails..."
          />
        </div>
        <button
          class="rounded-lg border p-2 transition-colors"
          :style="{
            borderColor: 'var(--color-border)',
            color: 'var(--color-text-muted)',
          }"
        >
          <FunnelIcon class="h-5 w-5" />
        </button>
      </div>

      <!-- Email list -->
      <div class="flex-1 overflow-y-auto">
        <SkeletonLoader v-if="emailStore.loading" variant="list" :lines="8" />
        <EmptyState
          v-else-if="filteredEmails.length === 0"
          message="No emails found. Connect your email accounts in Settings to get started."
        >
          <template #icon>
            <EnvelopeIcon class="h-8 w-8" :style="{ color: 'var(--color-text-muted)' }" />
          </template>
          <template #action>
            <RouterLink :to="{ name: 'settings' }">
              <BaseButton variant="primary" size="sm">
                Connect Account
              </BaseButton>
            </RouterLink>
          </template>
        </EmptyState>

        <div v-else class="space-y-1">
          <button
            v-for="email in filteredEmails"
            :key="email.id"
            class="group w-full rounded-lg p-3 text-left transition-colors duration-150"
            :style="{
              backgroundColor:
                selectedEmail?.id === email.id ? 'var(--color-bg-tertiary)' : 'transparent',
            }"
            @click="selectEmail(email)"
          >
            <div class="flex items-start justify-between gap-2">
              <p
                class="truncate text-sm font-medium"
                :style="{ color: 'var(--color-text-primary)' }"
              >
                {{ senderName(email.sender) }}
              </p>
              <span
                class="flex-shrink-0 text-xs"
                :style="{ color: 'var(--color-text-muted)' }"
              >
                {{ formatDate(email.received_at) }}
              </span>
            </div>
            <p
              class="mt-0.5 truncate text-sm"
              :style="{ color: 'var(--color-text-secondary)' }"
            >
              {{ email.subject }}
            </p>
            <p
              class="mt-0.5 truncate text-xs"
              :style="{ color: 'var(--color-text-muted)' }"
            >
              {{ email.markdown_body.slice(0, 100) }}
            </p>
            <div class="mt-1.5 flex gap-1.5">
              <StatusBadge
                v-for="label in email.labels.slice(0, 3)"
                :key="label"
                variant="custom"
              >
                {{ label }}
              </StatusBadge>
            </div>
          </button>
        </div>
      </div>
    </div>

    <!-- Email detail panel -->
    <div class="flex-1 overflow-y-auto">
      <div v-if="!selectedEmail" class="flex h-full items-center justify-center">
        <EmptyState message="Select an email to view its content and analysis.">
          <template #icon>
            <EnvelopeIcon class="h-8 w-8" :style="{ color: 'var(--color-text-muted)' }" />
          </template>
        </EmptyState>
      </div>

      <div v-else class="space-y-4">
        <!-- Email header -->
        <BaseCard :title="selectedEmail.subject">
          <template #header>
            <StatusBadge variant="custom">
              {{ selectedEmail.provider }}
            </StatusBadge>
          </template>
          <div class="space-y-3">
            <div class="flex items-center gap-3">
              <div
                class="flex h-9 w-9 items-center justify-center rounded-full text-sm font-semibold text-white"
                :style="{ backgroundColor: 'var(--color-primary)' }"
              >
                {{ senderName(selectedEmail.sender).charAt(0).toUpperCase() }}
              </div>
              <div>
                <p
                  class="text-sm font-medium"
                  :style="{ color: 'var(--color-text-primary)' }"
                >
                  {{ senderName(selectedEmail.sender) }}
                </p>
                <p class="text-xs" :style="{ color: 'var(--color-text-muted)' }">
                  {{ selectedEmail.sender }} · {{ formatDate(selectedEmail.received_at) }}
                </p>
              </div>
            </div>

            <hr :style="{ borderColor: 'var(--color-border)' }" />

            <!-- Rendered email body -->
            <div
              class="prose-theme text-sm"
              v-html="renderMarkdown(selectedEmail.markdown_body)"
            />
          </div>
        </BaseCard>

        <!-- Analysis card -->
        <BaseCard title="AI Analysis">
          <template #header>
            <BaseButton
              v-if="!analysis && !loadingAnalysis"
              size="sm"
              variant="secondary"
              @click="selectEmail(selectedEmail!)"
            >
              <ArrowPathIcon class="h-3.5 w-3.5" />
              Analyze
            </BaseButton>
          </template>

          <SkeletonLoader v-if="loadingAnalysis" :lines="5" />

          <div v-else-if="analysis" class="space-y-4">
            <div class="grid grid-cols-3 gap-3">
              <div>
                <p class="text-xs font-medium" :style="{ color: 'var(--color-text-muted)' }">
                  Category
                </p>
                <StatusBadge variant="custom" class="mt-1">
                  {{ analysis.category }}
                </StatusBadge>
              </div>
              <div>
                <p class="text-xs font-medium" :style="{ color: 'var(--color-text-muted)' }">
                  Urgency
                </p>
                <StatusBadge
                  variant="custom"
                  class="mt-1"
                  :color="analysis.urgency === 'high' ? 'var(--color-error)' : analysis.urgency === 'medium' ? 'var(--color-warning)' : 'var(--color-text-secondary)'"
                  :bg-color="(analysis.urgency === 'high' ? 'var(--color-error)' : analysis.urgency === 'medium' ? 'var(--color-warning)' : 'var(--color-text-muted)') + '22'"
                >
                  {{ analysis.urgency }}
                </StatusBadge>
              </div>
              <div>
                <p class="text-xs font-medium" :style="{ color: 'var(--color-text-muted)' }">
                  Sentiment
                </p>
                <StatusBadge variant="custom" class="mt-1">
                  {{ analysis.sentiment }}
                </StatusBadge>
              </div>
            </div>

            <div v-if="analysis.summary">
              <p class="text-xs font-medium mb-1" :style="{ color: 'var(--color-text-muted)' }">
                Summary
              </p>
              <p class="text-sm" :style="{ color: 'var(--color-text-secondary)' }">
                {{ analysis.summary }}
              </p>
            </div>

            <div v-if="analysis.action_items?.length">
              <p class="text-xs font-medium mb-2" :style="{ color: 'var(--color-text-muted)' }">
                Action Items
              </p>
              <ul class="space-y-2">
                <li
                  v-for="(item, idx) in analysis.action_items"
                  :key="idx"
                  class="flex items-start gap-2 rounded-lg p-2"
                  :style="{ backgroundColor: 'var(--color-bg-tertiary)' }"
                >
                  <ClipboardDocumentListIcon
                    class="mt-0.5 h-4 w-4 flex-shrink-0"
                    :style="{ color: 'var(--color-primary)' }"
                  />
                  <div>
                    <p class="text-sm" :style="{ color: 'var(--color-text-primary)' }">
                      {{ item.description }}
                    </p>
                    <div class="mt-1 flex gap-2">
                      <StatusBadge variant="priority" :value="item.priority" />
                      <span
                        v-if="item.due_date"
                        class="text-xs"
                        :style="{ color: 'var(--color-text-muted)' }"
                      >
                        Due: {{ item.due_date }}
                      </span>
                    </div>
                  </div>
                </li>
              </ul>
            </div>
          </div>

          <EmptyState v-else message="Click Analyze to get AI insights for this email." />
        </BaseCard>
      </div>
    </div>
  </div>
</template>
