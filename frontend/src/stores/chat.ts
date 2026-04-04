import { ref } from 'vue'
import { defineStore } from 'pinia'
import type { ChatMessage, ChatContext } from '@/types'

export const useChatStore = defineStore('chat', () => {
  const messages = ref<ChatMessage[]>([])
  const isOpen = ref(false)
  const loading = ref(false)
  const error = ref<string | null>(null)
  const context = ref<ChatContext>({ scope: 'global' })

  function togglePanel() {
    isOpen.value = !isOpen.value
  }

  function openPanel() {
    isOpen.value = true
  }

  function closePanel() {
    isOpen.value = false
  }

  function setContext(newContext: ChatContext) {
    context.value = newContext
  }

  async function sendMessage(content: string) {
    const userMsg: ChatMessage = {
      id: crypto.randomUUID(),
      role: 'user',
      content,
      timestamp: new Date().toISOString(),
      context: { ...context.value },
    }
    messages.value.push(userMsg)

    loading.value = true
    error.value = null
    try {
      // Placeholder: when the chat BFF endpoint is ready, this will call the API
      // For now, return a helpful placeholder response
      const assistantMsg: ChatMessage = {
        id: crypto.randomUUID(),
        role: 'assistant',
        content: 'AI assistant integration is coming soon. The chat backend endpoint is not yet available.',
        timestamp: new Date().toISOString(),
      }
      messages.value.push(assistantMsg)
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Failed to send message'
    } finally {
      loading.value = false
    }
  }

  function clearMessages() {
    messages.value = []
  }

  return {
    messages,
    isOpen,
    loading,
    error,
    context,
    togglePanel,
    openPanel,
    closePanel,
    setContext,
    sendMessage,
    clearMessages,
  }
})
