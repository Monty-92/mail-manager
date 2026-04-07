<script setup lang="ts">
import { ref, computed, onMounted, nextTick } from 'vue'
import DOMPurify from 'dompurify'
import {
  EnvelopeIcon,
  ArrowPathIcon,
  ChevronRightIcon,
  ChevronDownIcon,
  InboxIcon,
  TagIcon,
} from '@heroicons/vue/24/outline'
import { ClipboardDocumentListIcon } from '@heroicons/vue/24/outline'
import { useEmailStore } from '@/stores/email'
import { useAccountStore } from '@/stores/account'
import { useMarkdown } from '@/composables/useMarkdown'
import type { Email, EmailAnalysis } from '@/types'
import BaseCard from '@/components/ui/BaseCard.vue'
import BaseButton from '@/components/ui/BaseButton.vue'
import BaseInput from '@/components/ui/BaseInput.vue'
import StatusBadge from '@/components/ui/StatusBadge.vue'
import EmptyState from '@/components/ui/EmptyState.vue'
import SkeletonLoader from '@/components/ui/SkeletonLoader.vue'

const emailStore = useEmailStore()
const accountStore = useAccountStore()
const { renderMarkdown } = useMarkdown()
const search = ref('')
const selectedEmail = ref<Email | null>(null)
const detailEmail = ref<Email | null>(null)
const analysis = ref<EmailAnalysis | null>(null)
const loadingAnalysis = ref(false)
const labelSidebarCollapsed = ref(false)
const activeProvider = ref<string | null>(null)
const emailIframeRef = ref<HTMLIFrameElement | null>(null)
const collapsedPaths = ref<Set<string>>(new Set())

// Flatten labels into displayable rows with depth info
interface FlatLabel {
  name: string
  fullPath: string
  depth: number
  hasChildren: boolean
  isCollapsed: boolean
}

const flatLabels = computed<FlatLabel[]>(() => {
  // Build tree first
  interface TreeNode { name: string; fullPath: string; children: TreeNode[] }
  const tree: TreeNode[] = []
  const map = new Map<string, TreeNode>()

  for (const label of emailStore.labels) {
    const parts = label.split('/')
    let parent: TreeNode[] = tree
    let path = ''
    for (let i = 0; i < parts.length; i++) {
      path = parts.slice(0, i + 1).join('/')
      let node = map.get(path)
      if (!node) {
        node = { name: parts[i], fullPath: path, children: [] }
        map.set(path, node)
        parent.push(node)
      }
      parent = node.children
    }
  }

  // Flatten with DFS
  const result: FlatLabel[] = []
  function walk(nodes: TreeNode[], depth: number) {
    for (const n of nodes) {
      const hasChildren = n.children.length > 0
      const isCollapsed = collapsedPaths.value.has(n.fullPath)
      result.push({ name: n.name, fullPath: n.fullPath, depth, hasChildren, isCollapsed })
      if (hasChildren && !isCollapsed) {
        walk(n.children, depth + 1)
      }
    }
  }
  walk(tree, 0)
  return result
})

function toggleLabelCollapse(path: string) {
  const next = new Set(collapsedPaths.value)
  if (next.has(path)) {
    next.delete(path)
  } else {
    next.add(path)
  }
  collapsedPaths.value = next
}

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
  const detail = await emailStore.fetchEmailDetail(email.id)
  detailEmail.value = detail
  nextTick(() => writeIframeContent())
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

function writeIframeContent() {
  if (!emailIframeRef.value || !detailEmail.value?.html_body) return
  const doc = emailIframeRef.value.contentDocument
  if (!doc) return
  const sanitized = DOMPurify.sanitize(detailEmail.value.html_body, {
    ADD_TAGS: ['style'],
    WHOLE_DOCUMENT: true,
    FORCE_BODY: true,
  })
  doc.open()
  doc.write(`<!DOCTYPE html><html><head><meta charset="utf-8"><style>
    body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; font-size: 14px; line-height: 1.5; color: #333; margin: 0; padding: 8px; word-wrap: break-word; }
    img { max-width: 100%; height: auto; }
    a { color: #2563eb; }
    table { max-width: 100%; }
  </style></head><body>${sanitized}</body></html>`)
  doc.close()
}

const hasHtmlBody = computed(() => {
  return detailEmail.value?.html_body && detailEmail.value.html_body.trim().length > 0
})

function selectLabel(label: string | null) {
  emailStore.setActiveLabel(label)
  emailStore.fetchEmails()
}

function filterByProvider(provider: string | null) {
  activeProvider.value = provider
  emailStore.fetchEmails(provider ? { provider } : undefined)
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

function providerIcon(provider: string): string {
  return provider === 'gmail' ? 'G' : 'O'
}

function providerColor(provider: string): string {
  return provider === 'gmail' ? '#ea4335' : '#0078d4'
}

onMounted(async () => {
  await Promise.all([
    emailStore.fetchEmails(),
    emailStore.fetchLabels(),
    accountStore.fetchAccounts(),
  ])
})
</script>

<template>
  <div class="flex h-full gap-0">
    <!-- Label sidebar (collapsible) -->
    <div
      class="flex flex-shrink-0 flex-col border-r transition-all duration-300"
      :class="labelSidebarCollapsed ? 'w-10' : 'w-52'"
      :style="{ borderColor: 'var(--color-border)', backgroundColor: 'var(--color-bg-secondary)' }"
    >
      <div class="flex items-center justify-between px-3 py-3">
        <span
          v-if="!labelSidebarCollapsed"
          class="text-xs font-semibold uppercase tracking-wider"
          :style="{ color: 'var(--color-text-muted)' }"
        >
          Labels
        </span>
        <button
          class="rounded p-0.5 transition-colors hover:opacity-70"
          :style="{ color: 'var(--color-text-muted)' }"
          @click="labelSidebarCollapsed = !labelSidebarCollapsed"
        >
          <component
            :is="labelSidebarCollapsed ? ChevronRightIcon : ChevronDownIcon"
            class="h-4 w-4"
          />
        </button>
      </div>

      <div v-if="!labelSidebarCollapsed" class="flex-1 overflow-y-auto px-2 pb-2">
        <!-- All emails -->
        <button
          class="flex w-full items-center gap-2 rounded-md px-2 py-1.5 text-xs transition-colors"
          :style="{
            backgroundColor: !emailStore.activeLabel ? 'var(--color-bg-tertiary)' : 'transparent',
            color: !emailStore.activeLabel ? 'var(--color-primary)' : 'var(--color-text-secondary)',
          }"
          @click="selectLabel(null)"
        >
          <InboxIcon class="h-3.5 w-3.5 flex-shrink-0" />
          <span class="truncate">All Emails</span>
        </button>

        <!-- Flat label list with indentation -->
        <button
          v-for="lbl in flatLabels"
          :key="lbl.fullPath"
          class="flex w-full items-center gap-1.5 rounded-md py-1.5 text-xs transition-colors"
          :style="{
            paddingLeft: (lbl.depth * 12 + 8) + 'px',
            paddingRight: '8px',
            backgroundColor: emailStore.activeLabel === lbl.fullPath ? 'var(--color-bg-tertiary)' : 'transparent',
            color: emailStore.activeLabel === lbl.fullPath ? 'var(--color-primary)' : 'var(--color-text-secondary)',
          }"
          @click="selectLabel(lbl.fullPath)"
        >
          <span
            v-if="lbl.hasChildren"
            class="flex-shrink-0 cursor-pointer"
            @click.stop="toggleLabelCollapse(lbl.fullPath)"
          >
            <ChevronDownIcon v-if="!lbl.isCollapsed" class="h-3 w-3" />
            <ChevronRightIcon v-else class="h-3 w-3" />
          </span>
          <TagIcon v-else class="h-3 w-3 flex-shrink-0" :style="{ color: 'var(--color-text-muted)' }" />
          <span class="truncate">{{ lbl.name }}</span>
        </button>
      </div>
    </div>

    <!-- Main email area -->
    <div class="flex flex-1 gap-6 overflow-hidden p-6">
      <!-- Email list panel -->
      <div class="flex w-96 flex-shrink-0 flex-col">
        <!-- Account filter icons -->
        <div class="mb-3 flex items-center gap-1.5">
          <button
            class="flex h-8 w-8 items-center justify-center rounded-lg text-xs font-semibold transition-colors"
            :style="{
              backgroundColor: !activeProvider ? 'var(--color-primary)' : 'var(--color-bg-tertiary)',
              color: !activeProvider ? '#fff' : 'var(--color-text-secondary)',
            }"
            title="All emails"
            @click="filterByProvider(null)"
          >
            <EnvelopeIcon class="h-4 w-4" />
          </button>
          <button
            v-for="account in accountStore.accounts"
            :key="account.id"
            class="flex h-8 w-8 items-center justify-center rounded-lg text-xs font-bold transition-colors"
            :style="{
              backgroundColor: activeProvider === account.provider ? providerColor(account.provider) + '22' : 'var(--color-bg-tertiary)',
              color: activeProvider === account.provider ? providerColor(account.provider) : 'var(--color-text-muted)',
              borderWidth: '1px',
              borderColor: activeProvider === account.provider ? providerColor(account.provider) : 'var(--color-border)',
            }"
            :title="account.email"
            @click="filterByProvider(account.provider)"
          >
            {{ providerIcon(account.provider) }}
          </button>
        </div>

        <!-- Search -->
        <div class="mb-4">
          <BaseInput
            v-model="search"
            type="search"
            placeholder="Search emails..."
          />
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
                <div class="flex items-center gap-1.5">
                  <span
                    class="inline-flex h-5 w-5 items-center justify-center rounded text-[10px] font-bold"
                    :style="{
                      backgroundColor: providerColor(email.provider) + '22',
                      color: providerColor(email.provider),
                    }"
                  >
                    {{ providerIcon(email.provider) }}
                  </span>
                  <p
                    class="truncate text-sm font-medium"
                    :style="{ color: 'var(--color-text-primary)' }"
                  >
                    {{ senderName(email.sender) }}
                  </p>
                </div>
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
              <div v-if="email.labels.length > 0" class="mt-1.5 flex gap-1.5">
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
                  :style="{ backgroundColor: providerColor(selectedEmail.provider) }"
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

              <!-- HTML email in sandboxed iframe, or markdown fallback -->
              <div v-if="hasHtmlBody">
                <iframe
                  ref="emailIframeRef"
                  sandbox="allow-same-origin"
                  class="w-full rounded border-0"
                  :style="{ minHeight: '400px', backgroundColor: '#fff' }"
                  @load="writeIframeContent"
                />
              </div>
              <div
                v-else
                class="prose-theme text-sm"
                v-html="renderMarkdown(detailEmail?.markdown_body || selectedEmail.markdown_body)"
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
  </div>
</template>
