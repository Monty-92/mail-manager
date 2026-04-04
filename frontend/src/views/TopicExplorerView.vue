<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import {
  TagIcon,
  MagnifyingGlassIcon,
  EnvelopeIcon,
  ClockIcon,
  ChevronRightIcon,
  TrashIcon,
  ArrowLeftIcon,
} from '@heroicons/vue/24/outline'
import { useTopicStore } from '@/stores/topic'
import { useMarkdown } from '@/composables/useMarkdown'
import type { Topic } from '@/types'
import BaseCard from '@/components/ui/BaseCard.vue'
import BaseButton from '@/components/ui/BaseButton.vue'
import BaseInput from '@/components/ui/BaseInput.vue'
import StatusBadge from '@/components/ui/StatusBadge.vue'
import EmptyState from '@/components/ui/EmptyState.vue'
import SkeletonLoader from '@/components/ui/SkeletonLoader.vue'

const topicStore = useTopicStore()
const { renderMarkdown } = useMarkdown()
const search = ref('')
const selectedTopic = ref<Topic | null>(null)

const filteredTopics = computed(() => {
  if (!search.value) return topicStore.sortedTopics
  const q = search.value.toLowerCase()
  return topicStore.sortedTopics.filter((t) => t.name.toLowerCase().includes(q))
})

async function selectTopic(topic: Topic) {
  selectedTopic.value = topic
  await topicStore.fetchTopic(topic.id)
  if (topicStore.currentTopic) {
    selectedTopic.value = topicStore.currentTopic
  }
}

function formatDate(dateStr: string): string {
  return new Date(dateStr).toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  })
}

onMounted(() => {
  topicStore.fetchTopics()
})
</script>

<template>
  <div class="mx-auto max-w-7xl">
    <!-- Header -->
    <div class="mb-6 flex items-center justify-between">
      <div>
        <div v-if="selectedTopic" class="flex items-center gap-2 mb-1">
          <button
            class="rounded p-1 transition-colors hover:opacity-70"
            :style="{ color: 'var(--color-text-muted)' }"
            @click="selectedTopic = null"
          >
            <ArrowLeftIcon class="h-4 w-4" />
          </button>
          <p class="text-xs" :style="{ color: 'var(--color-text-muted)' }">
            Back to topics
          </p>
        </div>
      </div>
      <div class="w-72">
        <BaseInput
          v-if="!selectedTopic"
          v-model="search"
          type="search"
          placeholder="Search topics..."
        />
      </div>
    </div>

    <!-- Topic grid view -->
    <div v-if="!selectedTopic">
      <SkeletonLoader v-if="topicStore.loading" variant="card" />

      <EmptyState
        v-else-if="filteredTopics.length === 0"
        message="No topics found. Topics are automatically created when emails are analyzed."
      >
        <template #icon>
          <TagIcon class="h-8 w-8" :style="{ color: 'var(--color-text-muted)' }" />
        </template>
      </EmptyState>

      <div v-else class="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
        <button
          v-for="topic in filteredTopics"
          :key="topic.id"
          class="group rounded-xl border p-5 text-left transition-all duration-150 hover:shadow-md"
          :style="{
            backgroundColor: 'var(--color-bg-secondary)',
            borderColor: 'var(--color-border)',
          }"
          @click="selectTopic(topic)"
        >
          <div class="flex items-start justify-between">
            <div
              class="flex h-10 w-10 items-center justify-center rounded-lg"
              :style="{ backgroundColor: 'var(--color-primary)' + '1a' }"
            >
              <TagIcon class="h-5 w-5" :style="{ color: 'var(--color-primary)' }" />
            </div>
            <ChevronRightIcon
              class="h-4 w-4 opacity-0 transition-opacity group-hover:opacity-100"
              :style="{ color: 'var(--color-text-muted)' }"
            />
          </div>
          <h3
            class="mt-3 text-sm font-semibold"
            :style="{ color: 'var(--color-text-primary)' }"
          >
            {{ topic.name }}
          </h3>
          <div class="mt-2 flex items-center gap-3">
            <span class="flex items-center gap-1 text-xs" :style="{ color: 'var(--color-text-muted)' }">
              <EnvelopeIcon class="h-3.5 w-3.5" />
              {{ topic.email_count ?? 0 }} emails
            </span>
            <span
              v-if="topic.snapshots?.length"
              class="flex items-center gap-1 text-xs"
              :style="{ color: 'var(--color-text-muted)' }"
            >
              <ClockIcon class="h-3.5 w-3.5" />
              {{ topic.snapshots.length }} snapshots
            </span>
          </div>
          <p class="mt-2 text-xs" :style="{ color: 'var(--color-text-muted)' }">
            Updated {{ formatDate(topic.updated_at) }}
          </p>
        </button>
      </div>
    </div>

    <!-- Topic detail view -->
    <div v-else class="space-y-6">
      <BaseCard :title="selectedTopic.name">
        <template #header>
          <div class="flex items-center gap-2">
            <StatusBadge variant="custom">
              {{ selectedTopic.email_count ?? 0 }} emails
            </StatusBadge>
          </div>
        </template>
        <div class="space-y-3">
          <p class="text-sm" :style="{ color: 'var(--color-text-secondary)' }">
            Created {{ formatDate(selectedTopic.created_at) }} · Updated {{ formatDate(selectedTopic.updated_at) }}
          </p>
        </div>
      </BaseCard>

      <!-- Snapshots timeline -->
      <BaseCard
        v-if="selectedTopic.snapshots?.length"
        title="Topic Evolution"
        :subtitle="`${selectedTopic.snapshots.length} snapshots`"
      >
        <div class="space-y-4">
          <div
            v-for="(snapshot, idx) in selectedTopic.snapshots"
            :key="idx"
            class="relative flex gap-4"
          >
            <!-- Timeline dot -->
            <div class="flex flex-col items-center">
              <div
                class="h-3 w-3 rounded-full"
                :style="{
                  backgroundColor: idx === 0 ? 'var(--color-primary)' : 'var(--color-border)',
                }"
              />
              <div
                v-if="idx < selectedTopic.snapshots.length - 1"
                class="w-px flex-1"
                :style="{ backgroundColor: 'var(--color-border)' }"
              />
            </div>
            <!-- Snapshot content -->
            <div class="flex-1 pb-4">
              <div class="flex items-center gap-2">
                <p class="text-xs font-medium" :style="{ color: 'var(--color-text-muted)' }">
                  {{ formatDate(snapshot.timestamp) }}
                </p>
                <StatusBadge variant="custom">
                  {{ snapshot.email_count }} emails
                </StatusBadge>
              </div>
              <div
                v-if="snapshot.summary"
                class="mt-2 prose-theme text-sm"
                v-html="renderMarkdown(snapshot.summary)"
              />
            </div>
          </div>
        </div>
      </BaseCard>
    </div>
  </div>
</template>
