import { createRouter, createWebHistory } from "vue-router";

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: "/",
      name: "dashboard",
      component: () => import("@/views/DashboardView.vue"),
    },
    {
      path: "/emails",
      name: "email-browser",
      component: () => import("@/views/EmailBrowserView.vue"),
    },
    {
      path: "/topics",
      name: "topic-explorer",
      component: () => import("@/views/TopicExplorerView.vue"),
    },
    {
      path: "/tasks",
      name: "task-manager",
      component: () => import("@/views/TaskManagerView.vue"),
    },
    {
      path: "/calendar",
      name: "calendar",
      component: () => import("@/views/CalendarView.vue"),
    },
    {
      path: "/settings",
      name: "settings",
      component: () => import("@/views/SettingsView.vue"),
    },
  ],
});

export default router;
