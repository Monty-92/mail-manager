import { ref, computed } from 'vue'
import { defineStore } from 'pinia'
import {
  getMe,
  login as apiLogin,
  verifyTotp as apiVerifyTotp,
  getSetupStatus,
  type LoginRequest,
} from '@/api/auth'

const TOKEN_KEY = 'mm_auth_token'

export const useAuthStore = defineStore('auth', () => {
  const token = ref<string | null>(localStorage.getItem(TOKEN_KEY))
  const username = ref<string | null>(null)
  const userId = ref<string | null>(null)
  const isSetupComplete = ref<boolean | null>(null)
  const challengeToken = ref<string | null>(null)

  const isAuthenticated = computed(() => !!token.value)

  function setToken(t: string) {
    token.value = t
    localStorage.setItem(TOKEN_KEY, t)
  }

  function clearToken() {
    token.value = null
    username.value = null
    userId.value = null
    challengeToken.value = null
    localStorage.removeItem(TOKEN_KEY)
  }

  async function checkSetupStatus(): Promise<boolean> {
    const resp = await getSetupStatus()
    isSetupComplete.value = resp.is_setup_complete
    return resp.is_setup_complete
  }

  async function login(req: LoginRequest): Promise<string> {
    const resp = await apiLogin(req)
    challengeToken.value = resp.challenge_token
    return resp.challenge_token
  }

  async function verifyTotp(totpCode: string): Promise<void> {
    if (!challengeToken.value) throw new Error('No challenge token')
    const resp = await apiVerifyTotp({
      challenge_token: challengeToken.value,
      totp_code: totpCode,
    })
    setToken(resp.token)
    username.value = resp.username
    challengeToken.value = null
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
    challengeToken,
    checkSetupStatus,
    login,
    verifyTotp,
    fetchMe,
    logout,
  }
})
