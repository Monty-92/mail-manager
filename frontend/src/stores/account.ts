import { ref, computed } from 'vue'
import { defineStore } from 'pinia'
import {
  getAccounts,
  disconnectAccount as apiDisconnect,
  getAuthUrl,
  authCallback as apiAuthCallback,
  startDeviceFlow as apiStartDevice,
  pollDeviceFlow as apiPollDevice,
  type ConnectedAccount,
  type DeviceFlowStartResponse,
} from '@/api/accounts'

export const useAccountStore = defineStore('account', () => {
  const accounts = ref<ConnectedAccount[]>([])
  const loading = ref(false)

  const gmailAccounts = computed(() => accounts.value.filter((a) => a.provider === 'gmail'))
  const outlookAccounts = computed(() => accounts.value.filter((a) => a.provider === 'outlook'))

  async function fetchAccounts(): Promise<void> {
    loading.value = true
    try {
      accounts.value = await getAccounts()
    } finally {
      loading.value = false
    }
  }

  async function connectViaRedirect(provider: string): Promise<void> {
    const resp = await getAuthUrl(provider)
    window.location.href = resp.auth_url
  }

  async function handleCallback(code: string, provider: string, state?: string): Promise<void> {
    await apiAuthCallback(code, provider, state)
    await fetchAccounts()
  }

  async function startDeviceFlow(provider: string): Promise<DeviceFlowStartResponse> {
    return apiStartDevice(provider)
  }

  async function pollDeviceFlow(provider: string, deviceCode: string) {
    const resp = await apiPollDevice(provider, deviceCode)
    if (resp.status === 'complete') {
      await fetchAccounts()
    }
    return resp
  }

  async function disconnect(id: string): Promise<void> {
    await apiDisconnect(id)
    accounts.value = accounts.value.filter((a) => a.id !== id)
  }

  return {
    accounts,
    loading,
    gmailAccounts,
    outlookAccounts,
    fetchAccounts,
    connectViaRedirect,
    handleCallback,
    startDeviceFlow,
    pollDeviceFlow,
    disconnect,
  }
})
