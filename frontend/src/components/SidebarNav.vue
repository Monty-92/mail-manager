<script setup lang="ts">
import { RouterLink, useRoute } from "vue-router";

const route = useRoute();

const navItems = [
  { name: "Dashboard", to: "/", icon: "📊" },
  { name: "Emails", to: "/emails", icon: "📧" },
  { name: "Topics", to: "/topics", icon: "🏷️" },
  { name: "Tasks", to: "/tasks", icon: "✅" },
  { name: "Calendar", to: "/calendar", icon: "📅" },
  { name: "Settings", to: "/settings", icon: "⚙️" },
] as const;
</script>

<template>
  <nav class="flex w-64 flex-col bg-gray-900 text-gray-100">
    <div class="flex h-16 items-center px-6">
      <h1 class="text-xl font-bold">mail-manager</h1>
    </div>
    <ul class="mt-4 flex-1 space-y-1 px-3">
      <li v-for="item in navItems" :key="item.to">
        <RouterLink
          :to="item.to"
          class="flex items-center gap-3 rounded-lg px-3 py-2 text-sm transition-colors"
          :class="
            route.path === item.to
              ? 'bg-gray-700 text-white'
              : 'text-gray-400 hover:bg-gray-800 hover:text-white'
          "
        >
          <span>{{ item.icon }}</span>
          <span>{{ item.name }}</span>
        </RouterLink>
      </li>
    </ul>
  </nav>
</template>
