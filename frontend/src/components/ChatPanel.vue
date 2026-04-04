<script setup lang="ts">
import { ref, nextTick, watch } from 'vue'
import {
  XMarkIcon,
  PaperAirplaneIcon,
  SparklesIcon,
  GlobeAltIcon,
} from '@heroicons/vue/24/outline'
import { useChatStore } from '@/stores/chat'
import { useMarkdown } from '@/composables/useMarkdown'

const chatStore = useChatStore()
const { renderMarkdown } = useMarkdown()
const inputText = ref('')
const messagesContainer = ref<HTMLElement | null>(null)

async function handleSend() {
  const text = inputText.value.trim()
  if (!text) return
  inputText.value = ''
  await chatStore.sendMessage(text)
  await nextTick()
  scrollToBottom()
}

function handleKeydown(e: KeyboardEvent) {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault()
    handleSend()
  }
}

function scrollToBottom() {
  if (messagesContainer.value) {
    messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight
  }
}

watch(
  () => chatStore.messages.length,
  () => {
    nextTick(() => scrollToBottom())
  },
)
</script>

<template>
  <Transition
    enter-active-class="transition duration-300 ease-out"
    enter-from-class="translate-x-full"
    enter-to-class="translate-x-0"
    leave-active-class="transition duration-200 ease-in"
    leave-from-class="translate-x-0"
    leave-to-class="translate-x-full"
  >
    <aside
      v-if="chatStore.isOpen"
      class="flex h-full w-96 flex-col border-l"
      :style="{
        backgroundColor: 'var(--color-bg-secondary)',
        borderColor: 'var(--color-border)',
      }"
    >
      <!-- Chat header -->
      <div
        class="flex h-14 items-center justify-between border-b px-4"
        :style="{ borderColor: 'var(--color-border)' }"
      >
        <div class="flex items-center gap-2">
          <SparklesIcon class="h-5 w-5" :style="{ color: 'var(--color-primary)' }" />
          <span
            class="text-sm font-semibold"
            :style="{ color: 'var(--color-text-primary)' }"
          >
            AI Assistant
          </span>
        </div>
        <div class="flex items-center gap-1">
          <!-- Scope indicator -->
          <span
            class="flex items-center gap-1 rounded-full px-2 py-0.5 text-xs"
            :style="{
              backgroundColor: 'var(--color-bg-tertiary)',
              color: 'var(--color-text-muted)',
            }"
          >
            <GlobeAltIcon class="h-3 w-3" />
            {{ chatStore.context.scope_name ?? chatStore.context.scope }}
          </span>
          <button
            class="rounded-lg p-1.5 transition-colors hover:opacity-70"
            :style="{ color: 'var(--color-text-muted)' }"
            @click="chatStore.closePanel"
          >
            <XMarkIcon class="h-5 w-5" />
          </button>
        </div>
      </div>

      <!-- Messages -->
      <div ref="messagesContainer" class="flex-1 overflow-y-auto p-4 space-y-4">
        <div
          v-if="chatStore.messages.length === 0"
          class="flex flex-col items-center justify-center h-full gap-3 text-center"
        >
          <SparklesIcon class="h-10 w-10" :style="{ color: 'var(--color-text-muted)' }" />
          <p class="text-sm" :style="{ color: 'var(--color-text-muted)' }">
            Ask me anything about your emails, tasks, or topics.
          </p>
        </div>

        <div
          v-for="msg in chatStore.messages"
          :key="msg.id"
          class="flex"
          :class="msg.role === 'user' ? 'justify-end' : 'justify-start'"
        >
          <div
            class="max-w-[85%] rounded-xl px-3.5 py-2.5 text-sm"
            :style="{
              backgroundColor:
                msg.role === 'user' ? 'var(--color-primary)' : 'var(--color-bg-tertiary)',
              color: msg.role === 'user' ? '#ffffff' : 'var(--color-text-primary)',
            }"
          >
            <div
              v-if="msg.role === 'assistant'"
              class="prose-theme"
              v-html="renderMarkdown(msg.content)"
            />
            <p v-else>{{ msg.content }}</p>
          </div>
        </div>

        <!-- Loading indicator -->
        <div v-if="chatStore.loading" class="flex justify-start">
          <div
            class="rounded-xl px-4 py-3"
            :style="{ backgroundColor: 'var(--color-bg-tertiary)' }"
          >
            <div class="flex gap-1">
              <span
                class="h-2 w-2 rounded-full animate-bounce"
                :style="{ backgroundColor: 'var(--color-text-muted)', animationDelay: '0ms' }"
              />
              <span
                class="h-2 w-2 rounded-full animate-bounce"
                :style="{ backgroundColor: 'var(--color-text-muted)', animationDelay: '150ms' }"
              />
              <span
                class="h-2 w-2 rounded-full animate-bounce"
                :style="{ backgroundColor: 'var(--color-text-muted)', animationDelay: '300ms' }"
              />
            </div>
          </div>
        </div>
      </div>

      <!-- Input -->
      <div
        class="border-t p-3"
        :style="{ borderColor: 'var(--color-border)' }"
      >
        <div
          class="flex items-end gap-2 rounded-xl border px-3 py-2"
          :style="{
            backgroundColor: 'var(--color-bg-primary)',
            borderColor: 'var(--color-border)',
          }"
        >
          <textarea
            v-model="inputText"
            class="max-h-32 min-h-[2.5rem] flex-1 resize-none bg-transparent text-sm outline-none"
            :style="{ color: 'var(--color-text-primary)' }"
            placeholder="Ask about your emails..."
            rows="1"
            @keydown="handleKeydown"
          />
          <button
            class="flex-shrink-0 rounded-lg p-1.5 transition-colors"
            :style="{
              backgroundColor: inputText.trim() ? 'var(--color-primary)' : 'transparent',
              color: inputText.trim() ? '#ffffff' : 'var(--color-text-muted)',
            }"
            :disabled="!inputText.trim() || chatStore.loading"
            @click="handleSend"
          >
            <PaperAirplaneIcon class="h-4 w-4" />
          </button>
        </div>
      </div>
    </aside>
  </Transition>
</template>
