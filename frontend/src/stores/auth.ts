import { ref, computed } from 'vue'
import { defineStore } from 'pinia'
import { getMe, login as apiLogin, getSetupStatus, type LoginRequest } from '@/api/auth'

const TOKEN_KEY = 'mm_auth_token'

export const useAuthStore = defineStore('auth', () => {
  const token = ref<string | null>(localStorage.getItem(TOKEN_KEY))
  const username = ref<string | null>(null)
  const userId = ref<string | null>(null)
  const isSetupComplete = ref<boolean | null>(null)

  const isAuthenticated = computed(() => !!token.value)

  function setToken(t: string) {
    token.value = t
    localStorage.setItem(TOKEN_KEY, t)
  }

  function clearToken() {
    token.value = null
    username.value = null
    userId.value = null
    localStorage.removeItem(TOKEN_KEY)
  }

  async function checkSetupStatus(): Promise<boolean> {
    const resp = await getSetupStatus()
    isSetupComplete.value = resp.is_setup_complete
    return resp.is_setup_complete
  }

  async function login(req: LoginRequest): Promise<void> {
    const resp = await apiLogin(req)
    setToken(resp.token)
    username.value = resp.username
  }

  async function fetchMe(): Promise<boolean> {
    try {
      const resp = await getMe()
      userId.value = resp.user_id
      username.value = resp.username
      return true
    } catch {
      clearToken()
      return false
    }
  }

  function logout() {
    clearToken()
  }

  return {
    token,
    username,
    userId,
    isSetupComplete,
    isAuthenticated,
    checkSetupStatus,
    login,
    fetchMe,
    logout,
  }
})
