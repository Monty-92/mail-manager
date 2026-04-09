<script setup lang="ts">
import { ref } from 'vue'
import { Menu, MenuButton, MenuItems, MenuItem } from '@headlessui/vue'
import {
  ClipboardDocumentIcon,
  DocumentTextIcon,
  CodeBracketIcon,
  CheckIcon,
  ChevronDownIcon,
} from '@heroicons/vue/24/outline'
import { marked } from 'marked'
import DOMPurify from 'dompurify'
import { useToast } from '@/composables/useToast'

const props = defineProps<{
  markdown: string
}>()

const { success, error } = useToast()
const justCopied = ref<'text' | 'md' | null>(null)

function renderedHtml(): string {
  const raw = marked.parse(props.markdown, { async: false }) as string
  return DOMPurify.sanitize(raw)
}

function htmlToPlainText(html: string): string {
  const el = document.createElement('div')
  el.innerHTML = html
  return el.innerText
}

async function copyAsText() {
  try {
    const html = renderedHtml()
    const plain = htmlToPlainText(html)
    await navigator.clipboard.write([
      new ClipboardItem({
        'text/html': new Blob([html], { type: 'text/html' }),
        'text/plain': new Blob([plain], { type: 'text/plain' }),
      }),
    ])
    justCopied.value = 'text'
    success('Copied as formatted text')
    setTimeout(() => { justCopied.value = null }, 2000)
  } catch {
    error('Copy failed — clipboard access denied')
  }
}

async function copyAsMarkdown() {
  try {
    await navigator.clipboard.writeText(props.markdown)
    justCopied.value = 'md'
    success('Copied as Markdown')
    setTimeout(() => { justCopied.value = null }, 2000)
  } catch {
    error('Copy failed — clipboard access denied')
  }
}
</script>

<template>
  <Menu as="div" class="relative">
    <MenuButton
      class="inline-flex items-center gap-1 rounded-lg px-2.5 py-1.5 text-xs font-medium transition-colors focus:outline-none focus:ring-2 focus:ring-offset-1"
      :style="{
        backgroundColor: 'var(--color-bg-tertiary)',
        color: 'var(--color-text-primary)',
        '--tw-ring-color': 'var(--color-primary)',
      }"
      :title="'Copy summary'"
    >
      <CheckIcon v-if="justCopied" class="h-3.5 w-3.5" :style="{ color: 'var(--color-success)' }" />
      <ClipboardDocumentIcon v-else class="h-3.5 w-3.5" />
      <span>Copy</span>
      <ChevronDownIcon class="h-3 w-3 opacity-60" />
    </MenuButton>

    <transition
      enter-active-class="transition duration-100 ease-out"
      enter-from-class="scale-95 opacity-0"
      enter-to-class="scale-100 opacity-100"
      leave-active-class="transition duration-75 ease-in"
      leave-from-class="scale-100 opacity-100"
      leave-to-class="scale-95 opacity-0"
    >
      <MenuItems
        class="absolute right-0 z-20 mt-1 w-52 origin-top-right rounded-lg border shadow-lg focus:outline-none"
        :style="{
          backgroundColor: 'var(--color-bg-secondary)',
          borderColor: 'var(--color-border)',
        }"
      >
        <div class="p-1">
          <MenuItem v-slot="{ active }">
            <button
              class="flex w-full items-center gap-2.5 rounded-md px-3 py-2 text-xs transition-colors"
              :style="{
                backgroundColor: active ? 'var(--color-bg-tertiary)' : 'transparent',
                color: 'var(--color-text-primary)',
              }"
              @click="copyAsText"
            >
              <DocumentTextIcon class="h-4 w-4 flex-shrink-0" :style="{ color: 'var(--color-text-muted)' }" />
              <div class="text-left">
                <div class="font-medium">Copy as text</div>
                <div class="opacity-60" :style="{ color: 'var(--color-text-muted)' }">Formatted — paste into Word</div>
              </div>
            </button>
          </MenuItem>
          <MenuItem v-slot="{ active }">
            <button
              class="flex w-full items-center gap-2.5 rounded-md px-3 py-2 text-xs transition-colors"
              :style="{
                backgroundColor: active ? 'var(--color-bg-tertiary)' : 'transparent',
                color: 'var(--color-text-primary)',
              }"
              @click="copyAsMarkdown"
            >
              <CodeBracketIcon class="h-4 w-4 flex-shrink-0" :style="{ color: 'var(--color-text-muted)' }" />
              <div class="text-left">
                <div class="font-medium">Copy as Markdown</div>
                <div class="opacity-60" :style="{ color: 'var(--color-text-muted)' }">Raw .md syntax</div>
              </div>
            </button>
          </MenuItem>
        </div>
      </MenuItems>
    </transition>
  </Menu>
</template>
