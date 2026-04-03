<script setup lang="ts">
import SidebarNav from "@/components/SidebarNav.vue";
</script>

<template>
  <div class="flex h-screen bg-gray-50">
    <SidebarNav />
    <main class="flex-1 overflow-y-auto p-6">
      <RouterView />
    </main>
  </div>
</template>
