import { ref, computed, watch } from 'vue'
import { defineStore } from 'pinia'
import type { ThemeMode, ThemeColors, ThemePreset } from '@/types'

const defaultDarkColors: ThemeColors = {
  primary: '#a78bfa',
  primaryHover: '#c4b5fd',
  accent: '#7c3aed',
  accentHover: '#6d28d9',
  bgPrimary: '#0f0f14',
  bgSecondary: '#1a1a24',
  bgTertiary: '#252533',
  bgSidebar: '#12121a',
  textPrimary: '#f0f0f5',
  textSecondary: '#a0a0b8',
  textMuted: '#6b6b80',
  border: '#2a2a3c',
  borderHover: '#3a3a50',
  success: '#34d399',
  warning: '#fbbf24',
  error: '#f87171',
  info: '#60a5fa',
}

const defaultLightColors: ThemeColors = {
  primary: '#7c3aed',
  primaryHover: '#6d28d9',
  accent: '#a78bfa',
  accentHover: '#8b5cf6',
  bgPrimary: '#ffffff',
  bgSecondary: '#f8f8fc',
  bgTertiary: '#f0f0f6',
  bgSidebar: '#fafaff',
  textPrimary: '#1a1a2e',
  textSecondary: '#4a4a68',
  textMuted: '#8888a0',
  border: '#e2e2ee',
  borderHover: '#d0d0e0',
  success: '#059669',
  warning: '#d97706',
  error: '#dc2626',
  info: '#2563eb',
}

const defaultPreset: ThemePreset = {
  name: 'default',
  label: 'Violet',
  colors: { light: defaultLightColors, dark: defaultDarkColors },
}

const STORAGE_KEY = 'mm-theme-mode'
const STORAGE_CUSTOM_KEY = 'mm-theme-custom'

function getStoredMode(): ThemeMode {
  const stored = localStorage.getItem(STORAGE_KEY)
  if (stored === 'light' || stored === 'dark' || stored === 'system') return stored
  return 'dark'
}

function getStoredCustomColors(): { light: Partial<ThemeColors>; dark: Partial<ThemeColors> } | null {
  const stored = localStorage.getItem(STORAGE_CUSTOM_KEY)
  if (!stored) return null
  try {
    return JSON.parse(stored)
  } catch {
    return null
  }
}

function getSystemPreference(): 'light' | 'dark' {
  return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'
}

export const useThemeStore = defineStore('theme', () => {
  const mode = ref<ThemeMode>(getStoredMode())
  const customColors = ref(getStoredCustomColors())

  const resolvedMode = computed<'light' | 'dark'>(() => {
    if (mode.value === 'system') return getSystemPreference()
    return mode.value
  })

  const activeColors = computed<ThemeColors>(() => {
    const base = resolvedMode.value === 'dark' ? defaultPreset.colors.dark : defaultPreset.colors.light
    const overrides = customColors.value?.[resolvedMode.value]
    if (!overrides) return base
    return { ...base, ...overrides }
  })

  function setMode(newMode: ThemeMode) {
    mode.value = newMode
    localStorage.setItem(STORAGE_KEY, newMode)
  }

  function setCustomColor(colorKey: keyof ThemeColors, value: string, target?: 'light' | 'dark') {
    const targetMode = target ?? resolvedMode.value
    const current = customColors.value ?? { light: {}, dark: {} }
    current[targetMode] = { ...current[targetMode], [colorKey]: value }
    customColors.value = { ...current }
    localStorage.setItem(STORAGE_CUSTOM_KEY, JSON.stringify(customColors.value))
  }

  function resetCustomColors() {
    customColors.value = null
    localStorage.removeItem(STORAGE_CUSTOM_KEY)
  }

  function applyTheme() {
    const root = document.documentElement
    const colors = activeColors.value

    // Toggle dark class
    if (resolvedMode.value === 'dark') {
      root.classList.add('dark')
    } else {
      root.classList.remove('dark')
    }

    // Apply CSS custom properties
    for (const [key, value] of Object.entries(colors)) {
      root.style.setProperty(`--color-${camelToKebab(key)}`, value)
    }
  }

  // Watch and apply
  watch([resolvedMode, activeColors], () => applyTheme(), { immediate: true })

  // Listen for system preference changes
  window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', () => {
    if (mode.value === 'system') applyTheme()
  })

  return {
    mode,
    resolvedMode,
    activeColors,
    customColors,
    setMode,
    setCustomColor,
    resetCustomColors,
    applyTheme,
  }
})

function camelToKebab(str: string): string {
  return str.replace(/([a-z0-9])([A-Z])/g, '$1-$2').toLowerCase()
}
