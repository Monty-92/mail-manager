<script setup lang="ts">
import SidebarNav from '@/components/SidebarNav.vue'
import HeaderBar from '@/components/HeaderBar.vue'
import ChatPanel from '@/components/ChatPanel.vue'
import ToastContainer from '@/components/ToastContainer.vue'
import { useThemeStore } from '@/stores/theme'

// Initialize theme on mount
const themeStore = useThemeStore()
themeStore.applyTheme()
</script>

<template>
  <div class="flex h-screen overflow-hidden" :style="{ backgroundColor: 'var(--color-bg-primary)' }">
    <SidebarNav />
    <div class="flex flex-1 flex-col overflow-hidden">
      <HeaderBar />
      <main class="flex-1 overflow-y-auto p-6">
        <RouterView />
      </main>
    </div>
    <ChatPanel />
    <ToastContainer />
  </div>
</template>
