import { ref } from 'vue'

export interface Toast {
  id: string
  type: 'success' | 'error' | 'warning' | 'info'
  message: string
  duration: number
}

const toasts = ref<Toast[]>([])

export function useToast() {
  function addToast(type: Toast['type'], message: string, duration = 4000) {
    const id = crypto.randomUUID()
    toasts.value.push({ id, type, message, duration })
    if (duration > 0) {
      setTimeout(() => removeToast(id), duration)
    }
  }

  function removeToast(id: string) {
    toasts.value = toasts.value.filter((t) => t.id !== id)
  }

  function success(message: string, duration?: number) {
    addToast('success', message, duration)
  }

  function error(message: string, duration?: number) {
    addToast('error', message, duration)
  }

  function warning(message: string, duration?: number) {
    addToast('warning', message, duration)
  }

  function info(message: string, duration?: number) {
    addToast('info', message, duration)
  }

  return { toasts, addToast, removeToast, success, error, warning, info }
}
