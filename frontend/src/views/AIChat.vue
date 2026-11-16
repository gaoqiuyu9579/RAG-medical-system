<template>
  <div class="chat-page">
    <div class="page-header">
      <div><h2 class="page-title">AI智能问诊</h2><p class="page-desc">检索医学资料，查看回答与原文依据</p></div>
      <el-button type="success" size="large" @click="showUpload = true">📚 上传知识库</el-button>
    </div>
    <div class="chat-container">
      <div ref="messagesRef" class="messages" @scroll="handleScroll" :aria-busy="loading">
        <div v-if="!messages.length" class="empty-state">
          <div class="empty-icon">🤖</div><h3>您好，我是 AI 医疗助手</h3>
          <p>上传医学资料后，即可基于知识库提问</p><span>回答会逐字呈现，引用原文可展开核对</span>
        </div>
        <div v-for="(msg, index) in messages" :key="index" :class="['message', msg.role]">
          <div class="msg-avatar">{{ msg.role === 'user' ? '👤' : '🤖' }}</div>
          <div class="msg-content" :class="{ 'failed-message': msg.error }">
            <div v-if="msg.thinking" class="thinking" role="status"><span>{{ msg.status || '思考中' }}</span><i></i><i></i><i></i></div>
            <div v-if="msg.content" class="answer-text">{{ msg.content }}<span v-if="msg.streaming && !msg.error" class="typing-cursor">▍</span></div>
            <div v-if="msg.error" class="failure" role="alert">
              <p>{{ msg.content ? '回答尚未完成：' : '回答失败：' }}{{ msg.error }}</p>
              <el-button type="danger" plain size="small" :disabled="loading" @click="send(msg.question, msg)">重试</el-button>
            </div>
            <div v-if="msg.citations?.length" class="msg-sources">
              <div class="citation-heading">检索依据 · {{ msg.citations.length }} 个知识片段 <span>点击查看原文</span></div>
              <details v-for="(citation, c) in msg.citations" :key="c" class="citation-card">
                <summary><span>📄 {{ citation.source }}</span><small>{{ citation.chunk ? `片段 ${citation.chunk}` : `检索片段 ${c + 1}` }} ▾</small></summary>
                <p class="citation-excerpt"><template v-for="(part, p) in highlightExcerpt(citation.excerpt, msg.question)" :key="p"><mark v-if="part.hit">{{ part.text }}</mark><span v-else>{{ part.text }}</span></template></p>
                <small class="citation-note">原文片段 · 黄色标记为与问题匹配的文字</small>
              </details>
            </div>
          </div>
        </div>
      </div>
      <div class="input-area">
        <el-input ref="inputRef" v-model="question" type="textarea" :rows="3" placeholder="请输入医学问题，按 Enter 发送" maxlength="2000" :disabled="loading" @keydown.enter="handleEnter" />
        <div class="input-actions"><span>{{ loading ? '正在回答，请稍候…' : 'Enter 发送 · Shift+Enter 换行' }}</span><el-button type="primary" :loading="loading" :disabled="!question.trim() && !loading" @click="send()">{{ loading ? '回答中' : '发送' }}</el-button></div>
        <small class="medical-note">AI 回答仅供参考，不能替代医生诊断。</small>
      </div>
    </div>
    <el-dialog v-model="showUpload" title="上传医学知识库" width="620px" :close-on-click-modal="!uploading" :close-on-press-escape="!uploading" :show-close="!uploading" :before-close="done => { if (!uploading) done() }">
      <el-tabs v-model="uploadTab">
        <el-tab-pane label="粘贴文本" name="text" :disabled="uploading"><el-input v-model="uploadText" type="textarea" :rows="8" placeholder="请粘贴或输入医学资料内容..." :disabled="uploading" /></el-tab-pane>
        <el-tab-pane label="上传文件" name="file" :disabled="uploading">
          <el-upload drag :auto-upload="false" :limit="1" accept=".txt,.md,.json,.csv,.pdf" :disabled="uploading" v-model:file-list="fileList" :on-change="handleFileChange" :on-remove="handleFileRemove" :on-exceed="() => ElMessage.warning('请先移除已选文件再选择新文件')">
            <el-icon :size="40"><UploadFilled /></el-icon><div>将文件拖到此处，或点击上传</div><small>支持 TXT / MD / JSON / CSV / 文本 PDF，最大 16 MB</small>
          </el-upload>
        </el-tab-pane>
      </el-tabs>
      <div v-if="uploadStage" class="upload-progress" role="status" aria-live="polite">
        <el-steps :active="stageIndex" :process-status="uploadError ? 'error' : 'process'" finish-status="success" align-center><el-step title="上传中" /><el-step title="文档解析中" /><el-step title="向量化中" /><el-step title="完成" /></el-steps>
        <el-progress :percentage="progress" :indeterminate="uploading" :status="uploadError ? 'exception' : uploadStage === 'complete' ? 'success' : undefined" :show-text="false" />
        <p :class="{ 'error-text': uploadError }">{{ uploadError || uploadMessage }}</p><small v-if="uploading">进度条表示当前处理阶段，阶段由服务器实际处理结果更新</small>
      </div>
      <template #footer>
        <el-button :disabled="uploading" @click="showUpload = false">{{ uploadStage === 'complete' ? '完成' : '取消' }}</el-button>
        <el-button v-if="uploadStage !== 'complete'" type="primary" :loading="uploading" @click="upload">{{ uploadError ? '重试上传' : uploading ? '处理中' : '开始上传' }}</el-button>
        <el-button v-else type="primary" @click="resetUpload">继续上传</el-button>
      </template>
    </el-dialog>
  </div>
</template>
<script setup>
import { ref, computed, toRefs, nextTick, onBeforeUnmount } from 'vue'
import { ElMessage } from 'element-plus'
import { UploadFilled } from '@element-plus/icons-vue'
import { postEvents } from '../api/stream'
import { knowledgeUpload, importKnowledge, resetKnowledgeUpload } from '../stores/knowledge'
import { highlightExcerpt } from '../utils/highlight'

const question = ref(''), messages = ref([]), loading = ref(false)
const messagesRef = ref(null), inputRef = ref(null)
const showUpload = ref(false), uploadTab = ref('text'), uploadText = ref('')
const fileList = ref([]), selectedFile = ref(null)
const { uploading, stage: uploadStage, message: uploadMessage, error: uploadError } = toRefs(knowledgeUpload)
const stageIndex = computed(() => ({ uploading: 0, parsing: 1, vectorizing: 2, complete: 4 })[uploadStage.value] ?? 0)
const progress = computed(() => ({ uploading: 12, parsing: 38, vectorizing: 72, complete: 100 })[uploadStage.value] || 0)
let chatController, typingTimer, drainResolve
let queue = []
let stickToBottom = true
let disposed = false
function handleScroll() {
  const el = messagesRef.value
  stickToBottom = el.scrollHeight - el.scrollTop - el.clientHeight < 90
}
function scrollToBottom(force = false) {
  nextTick(() => { if ((force || stickToBottom) && messagesRef.value) messagesRef.value.scrollTop = messagesRef.value.scrollHeight })
}
function handleEnter(event) {
  if (event.shiftKey || event.isComposing || event.keyCode === 229) return
  event.preventDefault(); send()
}
function startTyping(msg) {
  queue = []
  typingTimer = setInterval(() => {
    if (queue.length) {
      msg.content += queue.splice(0, Math.max(1, Math.ceil(queue.length / 80))).join('')
      msg.thinking = false; scrollToBottom()
    } else if (drainResolve) { drainResolve(); drainResolve = null }
  }, 18)
}
async function send(retryQuestion, retryMessage) {
  if (loading.value) return
  const q = (retryQuestion ?? question.value).trim()
  if (!q) return
  loading.value = true
  if (!retryMessage) messages.value.push({ role: 'user', content: q })
  const initial = { role: 'ai', question: q, content: '', citations: [], error: '', thinking: true, streaming: true, status: '思考中 · 正在检索资料' }
  let msg
  if (retryMessage) { Object.assign(retryMessage, initial); msg = retryMessage }
  else { messages.value.push(initial); msg = messages.value[messages.value.length - 1] }
  if (!retryMessage) question.value = ''
  stickToBottom = true; scrollToBottom(true)
  chatController = new AbortController(); startTyping(msg)
  try {
    await postEvents('chat-stream', { question: q }, event => {
      if (event.type === 'status') msg.status = `思考中 · ${event.message}`
      if (event.type === 'delta') queue.push(...Array.from(event.content))
      if (event.citations) msg.citations = event.citations
    }, chatController.signal)
    if (queue.length) await new Promise(resolve => { drainResolve = resolve })
  } catch (error) {
    msg.content += queue.join(''); queue = []
    if (!disposed) msg.error = error.message
  } finally {
    clearInterval(typingTimer); msg.thinking = false; msg.streaming = false; loading.value = false
    scrollToBottom()
    if (!disposed) nextTick(() => inputRef.value?.focus())
  }
}
function resetUpload() { resetKnowledgeUpload() }
function handleFileChange(file) {
  resetUpload()
  if (file.raw.size > 16 * 1024 * 1024) { ElMessage.warning('文件不能超过16 MB'); fileList.value = []; selectedFile.value = null; return }
  selectedFile.value = file.raw
}
function handleFileRemove() { selectedFile.value = null; resetUpload() }
async function upload() {
  if (uploading.value) return
  if (uploadTab.value === 'text' && !uploadText.value.trim()) return ElMessage.warning('请输入知识文本')
  if (uploadTab.value === 'file' && !selectedFile.value) return ElMessage.warning('请选择文件')
  const body = uploadTab.value === 'text' ? { text: uploadText.value.trim() } : new FormData()
  if (body instanceof FormData) body.append('file', selectedFile.value)
  const complete = await importKnowledge(body)
  if (disposed) return
  if (complete) {
    uploadText.value = ''; selectedFile.value = null; fileList.value = []
    ElMessage.success('知识库构建成功')
  }
}
onBeforeUnmount(() => {
  disposed = true; chatController?.abort(); clearInterval(typingTimer)
  drainResolve?.(); drainResolve = null
})
</script>
<style scoped>
.chat-page { display: flex; flex-direction: column; gap: 20px; height: calc(100dvh - 116px); min-height: 400px; }
.page-header { display: flex; align-items: center; justify-content: space-between; flex-shrink: 0; }
.page-title { margin: 0 0 5px; font-size: 22px; color: #1a202c; }.page-desc { margin: 0; color: #718096; font-size: 13px; }
.chat-container { flex: 1; min-height: 0; display: flex; flex-direction: column; background: #fff; border: 1px solid #e2e8f0; border-radius: 18px; overflow: hidden; box-shadow: 0 4px 20px #152f4810; }
.messages { flex: 1; overflow-y: auto; padding: 24px; display: flex; flex-direction: column; gap: 20px; background: #f6f9fc; }
.empty-state { margin: auto; text-align: center; padding: 30px 10px; color: #64748b; }.empty-icon { font-size: 54px; }.empty-state h3 { color: #334155; }.empty-state span { font-size: 12px; }
.message { display: flex; gap: 12px; max-width: 86%; animation: appear .25s ease; }.message.user { align-self: flex-end; flex-direction: row-reverse; }.message.ai { align-self: flex-start; }
.msg-avatar { flex-shrink: 0; width: 36px; height: 36px; display: grid; place-items: center; background: #e0eefa; border-radius: 50%; }
.msg-content { min-width: 0; padding: 14px 18px; border-radius: 14px; font-size: 14px; line-height: 1.8; overflow-wrap: anywhere; }
.message.user .msg-content { background: #4669d1; color: white; white-space: pre-wrap; border-bottom-right-radius: 4px; }.message.ai .msg-content { background: white; border: 1px solid #e2e8f0; color: #334155; border-bottom-left-radius: 4px; }
.answer-text { white-space: pre-wrap; }.typing-cursor { color: #3182ce; animation: blink .8s infinite; }
.thinking { display: flex; align-items: center; gap: 5px; color: #64748b; }.thinking span { margin-right: 8px; }.thinking i { width: 6px; height: 6px; border-radius: 50%; background: #4299ba; animation: bounce 1.2s infinite; }.thinking i:nth-of-type(2) { animation-delay: .15s; }.thinking i:nth-of-type(3) { animation-delay: .3s; }
.msg-content.failed-message { border-color: #f8b4b4; background: #fffafa; }.failure { color: #b83d3d; }.failure p { margin: 5px 0 10px; }
.msg-sources { margin-top: 14px; padding-top: 12px; border-top: 1px solid #e9edf3; }.citation-heading { font-size: 12px; color: #42657b; margin-bottom: 8px; }.citation-heading span { color: #94a3b8; margin-left: 12px; }
.citation-card { margin-top: 7px; border: 1px solid #dce6ef; border-radius: 9px; overflow: hidden; background: #f8fbfe; }.citation-card summary { display: flex; justify-content: space-between; gap: 14px; cursor: pointer; padding: 9px 12px; color: #286291; font-size: 12px; }.citation-card summary:hover { background: #edf5ff; }.citation-card summary small { flex-shrink: 0; }
.citation-excerpt { margin: 0; padding: 12px; white-space: pre-wrap; font-size: 13px; border-top: 1px solid #dce6ef; }.citation-excerpt mark { background: #fff0ad; border-radius: 2px; color: #685000; }.citation-note { display: block; padding: 0 12px 10px; color: #8190a1; }
.input-area { padding: 16px 20px 10px; border-top: 1px solid #e2e8f0; }.input-actions { display: flex; justify-content: space-between; align-items: center; margin-top: 10px; gap: 10px; }.input-actions span, .medical-note { font-size: 12px; color: #8493a6; }.medical-note { display: block; margin-top: 8px; text-align: center; }
.upload-progress { margin-top: 22px; padding: 18px 12px; border-radius: 12px; background: #f5f9fc; }.upload-progress :deep(.el-step__title) { font-size: 12px; }.upload-progress :deep(.el-progress) { margin-top: 14px; }.upload-progress p { font-size: 13px; margin: 12px 0 4px; }.upload-progress small, .el-upload small { font-size: 11px; color: #8493a6; }.error-text { color: #c53030; }
:deep(.el-upload-list__item .el-icon--close) { display: inline-flex !important; }:deep(.el-upload-list__item-status-label) { display: none !important; }
@keyframes bounce { 0%,80%,100% { transform: translateY(0); opacity: .4; } 40% { transform: translateY(-5px); opacity: 1; } } @keyframes blink { 50% { opacity: 0; } } @keyframes appear { from { opacity: 0; transform: translateY(8px); } to { opacity: 1; transform: translateY(0); } }
@media(max-width: 768px) { .messages { padding: 14px; }.message { max-width: 97%; gap: 7px; }.msg-content { padding: 10px 12px; }.msg-avatar { width: 28px; height: 28px; }.input-area { padding: 12px; }.citation-card summary { flex-wrap: wrap; gap: 2px; } }
@media(prefers-reduced-motion: reduce) { .message, .thinking i, .typing-cursor { animation: none; } }
</style>
