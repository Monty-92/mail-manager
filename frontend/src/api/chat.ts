const API_BASE = '/api/v1'
const TOKEN_KEY = 'mm_auth_token'

export type ChatScope = 'global' | 'project' | 'topic' | 'email'

export interface ChatRequest {
  query: string
  scope: ChatScope
  scope_id?: string
  model?: string
}

export interface ChatToken {
  token?: string
  done: boolean
}

/**
 * Stream a chat response from the BFF. Calls onToken for each streamed token
 * and resolves when the stream is done. Throws on non-2xx responses.
 */
export async function streamChat(
  request: ChatRequest,
  onToken: (token: string) => void,
  signal?: AbortSignal,
): Promise<void> {
  const token = localStorage.getItem(TOKEN_KEY)
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    Accept: 'text/event-stream',
  }
  if (token) {
    headers['Authorization'] = `Bearer ${token}`
  }

  const response = await fetch(`${API_BASE}/chat`, {
    method: 'POST',
    headers,
    body: JSON.stringify(request),
    signal,
  })

  if (!response.ok) {
    let detail = `HTTP ${response.status}`
    try {
      const err = await response.json()
      detail = err.detail ?? detail
    } catch {
      // not JSON
    }
    throw new Error(detail)
  }

  const reader = response.body?.getReader()
  if (!reader) throw new Error('No response body')

  const decoder = new TextDecoder()
  let buffer = ''

  while (true) {
    const { done, value } = await reader.read()
    if (done) break

    buffer += decoder.decode(value, { stream: true })
    const lines = buffer.split('\n')
    buffer = lines.pop() ?? ''

    for (const line of lines) {
      if (!line.startsWith('data: ')) continue
      const raw = line.slice(6).trim()
      if (!raw) continue
      try {
        const chunk = JSON.parse(raw) as ChatToken
        if (chunk.done) return
        if (chunk.token) onToken(chunk.token)
      } catch {
        // malformed SSE chunk — skip
      }
    }
  }
}
