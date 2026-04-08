import { ref } from 'vue'
import { defineStore } from 'pinia'
import type { ChatMessage, ChatContext } from '@/types'
import { streamChat } from '@/api/chat'

export const useChatStore = defineStore('chat', () => {
  const messages = ref<ChatMessage[]>([])
  const isOpen = ref(false)
  const loading = ref(false)
  const error = ref<string | null>(null)
  const context = ref<ChatContext>({ scope: 'global' })
  let _abortController: AbortController | null = null

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

    const assistantMsg: ChatMessage = {
      id: crypto.randomUUID(),
      role: 'assistant',
      content: '',
      timestamp: new Date().toISOString(),
    }
    messages.value.push(assistantMsg)

    loading.value = true
    error.value = null
    _abortController = new AbortController()

    try {
      await streamChat(
        {
          query: content,
          scope: context.value.scope,
          scope_id: context.value.scope_id,
        },
        (token) => {
          assistantMsg.content += token
          // Trigger reactivity on the last message
          messages.value[messages.value.length - 1] = { ...assistantMsg }
        },
        _abortController.signal,
      )
    } catch (e) {
      if (e instanceof Error && e.name === 'AbortError') return
      error.value = e instanceof Error ? e.message : 'Failed to send message'
      assistantMsg.content = error.value ?? 'An error occurred.'
      messages.value[messages.value.length - 1] = { ...assistantMsg }
    } finally {
      loading.value = false
      _abortController = null
    }
  }

  function cancelStream() {
    _abortController?.abort()
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
    cancelStream,
    clearMessages,
  }
})

