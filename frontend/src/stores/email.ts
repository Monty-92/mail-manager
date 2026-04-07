import { ref, computed } from 'vue'
import { defineStore } from 'pinia'
import type { Email, EmailAnalysis, PaginationParams } from '@/types'
import { getEmails, getEmail, getEmailLabels, type EmailListParams } from '@/api/emails'
import { api } from '@/api/client'

export const useEmailStore = defineStore('email', () => {
  const emails = ref<Email[]>([])
  const currentEmail = ref<Email | null>(null)
  const currentAnalysis = ref<EmailAnalysis | null>(null)
  const loading = ref(false)
  const error = ref<string | null>(null)
  const totalCount = ref(0)
  const labels = ref<string[]>([])
  const activeLabel = ref<string | null>(null)

  const recentEmails = computed(() =>
    [...emails.value].sort((a, b) => new Date(b.received_at).getTime() - new Date(a.received_at).getTime()).slice(0, 10),
  )

  async function fetchEmails(params?: EmailListParams) {
    loading.value = true
    error.value = null
    try {
      const mergedParams: EmailListParams = { ...params }
      if (activeLabel.value) {
        mergedParams.label = activeLabel.value
      }
      const resp = await getEmails(mergedParams)
      emails.value = resp.emails
      totalCount.value = resp.total
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Failed to fetch emails'
    } finally {
      loading.value = false
    }
  }

  async function fetchEmailDetail(emailId: string): Promise<Email | null> {
    try {
      const email = await getEmail(emailId)
      currentEmail.value = email
      return email
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Failed to fetch email'
      return null
    }
  }

  async function fetchLabels() {
    try {
      labels.value = await getEmailLabels()
    } catch {
      labels.value = []
    }
  }

  function setActiveLabel(label: string | null) {
    activeLabel.value = label
  }

  async function fetchAnalysis(emailId: string) {
    loading.value = true
    error.value = null
    try {
      currentAnalysis.value = await api.get<EmailAnalysis>(`/analyze/${emailId}`)
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Failed to fetch analysis'
    } finally {
      loading.value = false
    }
  }

  function setCurrentEmail(email: Email | null) {
    currentEmail.value = email
    currentAnalysis.value = null
  }

  return {
    emails,
    currentEmail,
    currentAnalysis,
    loading,
    error,
    totalCount,
    labels,
    activeLabel,
    recentEmails,
    fetchEmails,
    fetchEmailDetail,
    fetchLabels,
    setActiveLabel,
    fetchAnalysis,
    setCurrentEmail,
  }
})
