import { onMounted, onUnmounted } from 'vue'

type KeyHandler = (e: KeyboardEvent) => void

interface Shortcut {
  key: string
  meta?: boolean
  ctrl?: boolean
  shift?: boolean
  handler: KeyHandler
}

export function useKeyboardShortcuts(shortcuts: Shortcut[]) {
  function handleKeydown(e: KeyboardEvent) {
    for (const s of shortcuts) {
      const metaMatch = s.meta ? e.metaKey : true
      const ctrlMatch = s.ctrl ? e.ctrlKey : true
      const shiftMatch = s.shift ? e.shiftKey : !e.shiftKey
      if (e.key.toLowerCase() === s.key.toLowerCase() && metaMatch && ctrlMatch && shiftMatch) {
        // Don't trigger when user is typing in an input
        const target = e.target as HTMLElement
        if (target.tagName === 'INPUT' || target.tagName === 'TEXTAREA' || target.isContentEditable) {
          return
        }
        e.preventDefault()
        s.handler(e)
        return
      }
    }
  }

  onMounted(() => {
    window.addEventListener('keydown', handleKeydown)
  })

  onUnmounted(() => {
    window.removeEventListener('keydown', handleKeydown)
  })
}
