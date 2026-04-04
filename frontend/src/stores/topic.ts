import { ref, computed } from 'vue'
import { defineStore } from 'pinia'
import type { Topic } from '@/types'
import * as topicsApi from '@/api/topics'

export const useTopicStore = defineStore('topic', () => {
  const topics = ref<Topic[]>([])
  const currentTopic = ref<Topic | null>(null)
  const loading = ref(false)
  const error = ref<string | null>(null)

  const topicCount = computed(() => topics.value.length)

  const sortedTopics = computed(() =>
    [...topics.value].sort((a, b) => (b.email_count ?? 0) - (a.email_count ?? 0)),
  )

  async function fetchTopics(limit = 100, offset = 0) {
    loading.value = true
    error.value = null
    try {
      topics.value = await topicsApi.listTopics(limit, offset)
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Failed to fetch topics'
    } finally {
      loading.value = false
    }
  }

  async function fetchTopic(topicId: string) {
    loading.value = true
    error.value = null
    try {
      currentTopic.value = await topicsApi.getTopic(topicId)
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Failed to fetch topic'
    } finally {
      loading.value = false
    }
  }

  async function removeTopic(topicId: string) {
    await topicsApi.deleteTopic(topicId)
    topics.value = topics.value.filter((t) => t.id !== topicId)
    if (currentTopic.value?.id === topicId) currentTopic.value = null
  }

  return {
    topics,
    currentTopic,
    loading,
    error,
    topicCount,
    sortedTopics,
    fetchTopics,
    fetchTopic,
    removeTopic,
  }
})
