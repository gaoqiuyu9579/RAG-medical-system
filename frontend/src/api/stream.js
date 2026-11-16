import { clearSession, getToken } from '../utils/auth.js'

// UTF-8 和 SSE 帧可能跨任意网络分块；只在完整帧到齐后解析。
export async function consumeEvents(body, onEvent) {
  const reader = body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''
  let completed = false
  function frame(value) {
    const data = value.split('\n').filter(line => line.startsWith('data:')).map(line => line.slice(5).trimStart()).join('\n')
    if (!data) return
    const event = JSON.parse(data)
    if (event.type === 'error') throw new Error(event.message || '服务处理失败，请重试')
    onEvent(event)
    if (event.type === 'done') completed = true
  }
  try {
    while (true) {
      const { done, value } = await reader.read()
      buffer += decoder.decode(value, { stream: !done })
      buffer = buffer.replace(/\r\n/g, '\n')
      let boundary
      while ((boundary = buffer.indexOf('\n\n')) >= 0) {
        frame(buffer.slice(0, boundary))
        buffer = buffer.slice(boundary + 2)
        // 业务完成后立即恢复输入，不等待代理或连接池关闭 HTTP 流。
        if (completed) return
      }
      if (done) break
    }
    if (buffer.trim()) frame(buffer)
    if (!completed) throw new Error('连接已中断，回答或处理尚未完成，请重试')
  } finally {
    await reader.cancel().catch(() => {})
    reader.releaseLock()
  }
}

export async function postEvents(path, body, onEvent, signal) {
  const controller = new AbortController()
  const abort = () => controller.abort()
  if (signal?.aborted) abort()
  signal?.addEventListener('abort', abort, { once: true })
  const timer = setTimeout(abort, 180000)
  const isFile = body instanceof FormData
  try {
    const response = await fetch(`/api/rag/${path}`, {
      method: 'POST', signal: controller.signal,
      headers: { Authorization: `Bearer ${getToken() || ''}`, ...(isFile ? {} : { 'Content-Type': 'application/json' }) },
      body: isFile ? body : JSON.stringify(body)
    })
    if (response.status === 401) {
      clearSession()
      window.location.replace('/login')
    }
    if (!response.ok) {
      const error = await response.json().catch(() => ({}))
      throw new Error(error.msg || '服务暂时不可用，请重试')
    }
    if (!response.body || !response.headers.get('content-type')?.includes('text/event-stream')) {
      throw new Error('服务未返回有效的数据流，请重试')
    }
    await consumeEvents(response.body, onEvent)
  } catch (error) {
    if (error.name === 'AbortError' && !signal?.aborted) throw new Error('请求超时，请重试')
    if (error instanceof TypeError) throw new Error('网络连接失败，请检查网络后重试')
    throw error
  } finally {
    clearTimeout(timer)
    signal?.removeEventListener('abort', abort)
  }
}
