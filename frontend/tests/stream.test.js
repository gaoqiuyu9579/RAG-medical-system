import { test } from 'node:test'
import assert from 'node:assert/strict'
import { consumeEvents } from '../src/api/stream.js'
import { highlightExcerpt } from '../src/utils/highlight.js'

function stream(text, chunkSize = 1) {
  const bytes = new TextEncoder().encode(text)
  return new ReadableStream({ start(controller) {
    for (let i = 0; i < bytes.length; i += chunkSize) controller.enqueue(bytes.slice(i, i + chunkSize))
    controller.close()
  } })
}
test('SSE reconstructs UTF-8 Chinese split at every byte, CRLF and multiple frames', async () => {
  const events = []
  await consumeEvents(stream('data: {"type":"delta","content":"高血压"}\r\n\r\ndata: {"type":"done"}\r\n\r\n'), event => events.push(event))
  assert.equal(events[0].content, '高血压')
  assert.equal(events[1].type, 'done')
})
test('truncated answers and upstream error events reject for retry', async () => {
  await assert.rejects(consumeEvents(stream('data: {"type":"delta","content":"部分回答"}\n\n'), () => {}), /连接已中断/)
  await assert.rejects(consumeEvents(stream('data: {"type":"error","message":"向量服务失败"}\n\n'), () => {}), /向量服务失败/)
})
test('done restores the UI and cancels transport even when the connection stays open', { timeout: 1000 }, async () => {
  let cancelled = false
  const events = []
  const body = new ReadableStream({
    start(controller) {
      controller.enqueue(new TextEncoder().encode('data: {"type":"done"}\n\n'))
    },
    cancel() { cancelled = true }
  })
  await consumeEvents(body, event => events.push(event))
  assert.deepEqual(events, [{ type: 'done' }])
  assert.equal(cancelled, true)
})
test('citation highlighting preserves literal HTML and only marks matching text', () => {
  const excerpt = '<script>alert(1)</script>高血压随访登记'
  const parts = highlightExcerpt(excerpt, '高血压如何随访？')
  assert.equal(parts.map(item => item.text).join(''), excerpt)
  assert.ok(parts.some(item => item.hit && item.text.includes('高血压')))
  assert.ok(parts.some(item => !item.hit && item.text.includes('<script>')))
})
