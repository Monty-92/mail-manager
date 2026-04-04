import { ref, computed } from 'vue'
import { defineStore } from 'pinia'
import type { Summary } from '@/types'
import * as summariesApi from '@/api/summaries'

export const useSummaryStore = defineStore('summary', () => {
  const summaries = ref<Summary[]>([])
  const currentSummary = ref<Summary | null>(null)
  const loading = ref(false)
  const error = ref<string | null>(null)

  const morningSummaries = computed(() =>
    summaries.value.filter((s) => s.summary_type === 'morning'),
  )

  const eveningSummaries = computed(() =>
    summaries.value.filter((s) => s.summary_type === 'evening'),
  )

  async function fetchSummaries(limit = 30, offset = 0) {
    loading.value = true
    error.value = null
    try {
      summaries.value = await summariesApi.listSummaries(limit, offset)
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Failed to fetch summaries'
    } finally {
      loading.value = false
    }
  }

  async function fetchDailySummary(type: 'morning' | 'evening', date: string) {
    loading.value = true
    error.value = null
    try {
      currentSummary.value = await summariesApi.getDailySummary(type, date)
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Failed to fetch summary'
    } finally {
      loading.value = false
    }
  }

  async function generateSummary(type: 'morning' | 'evening', date: string) {
    loading.value = true
    error.value = null
    try {
      const summary = await summariesApi.generateDailySummary(type, date)
      currentSummary.value = summary
      // Update list if present
      const idx = summaries.value.findIndex((s) => s.id === summary.id)
      if (idx !== -1) {
        summaries.value[idx] = summary
      } else {
        summaries.value.unshift(summary)
      }
      return summary
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Failed to generate summary'
      throw e
    } finally {
      loading.value = false
    }
  }

  return {
    summaries,
    currentSummary,
    loading,
    error,
    morningSummaries,
    eveningSummaries,
    fetchSummaries,
    fetchDailySummary,
    generateSummary,
  }
})
