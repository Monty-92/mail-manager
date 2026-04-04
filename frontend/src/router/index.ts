import { createRouter, createWebHistory } from "vue-router";
import { useAuthStore } from "@/stores/auth";

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: "/setup",
      name: "setup",
      component: () => import("@/views/SetupView.vue"),
      meta: { public: true },
    },
    {
      path: "/login",
      name: "login",
      component: () => import("@/views/LoginView.vue"),
      meta: { public: true },
    },
    {
      path: "/auth/callback",
      name: "auth-callback",
      component: () => import("@/views/AuthCallbackView.vue"),
      meta: { public: false },
    },
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

router.beforeEach(async (to) => {
  const auth = useAuthStore();

  if (to.meta.public) return true;

  // Check if setup is needed
  if (auth.isSetupComplete === null) {
    await auth.checkSetupStatus();
  }

  if (!auth.isSetupComplete) {
    if (to.name !== "setup") return { name: "setup" };
    return true;
  }

  // Check authentication
  if (!auth.isAuthenticated) {
    return { name: "login" };
  }

  // Validate token on first navigation
  if (!auth.username) {
    const valid = await auth.fetchMe();
    if (!valid) return { name: "login" };
  }

  return true;
});

export default router;
