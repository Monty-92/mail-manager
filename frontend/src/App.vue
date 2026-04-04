<script setup lang="ts">
import { useRouter } from 'vue-router'
import AppLayout from '@/components/AppLayout.vue'
import { useChatStore } from '@/stores/chat'
import { useKeyboardShortcuts } from '@/composables/useKeyboardShortcuts'

const router = useRouter()
const chatStore = useChatStore()

// Global keyboard shortcuts
useKeyboardShortcuts([
  { key: '1', meta: true, handler: () => router.push('/') },
  { key: '2', meta: true, handler: () => router.push('/emails') },
  { key: '3', meta: true, handler: () => router.push('/topics') },
  { key: '4', meta: true, handler: () => router.push('/tasks') },
  { key: '5', meta: true, handler: () => router.push('/calendar') },
  { key: '.', meta: true, handler: () => chatStore.togglePanel() },
])
</script>

<template>
  <AppLayout />
</template>
