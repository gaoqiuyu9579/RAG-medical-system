<template>
  <div class="chat-page">
    <div class="page-header">
      <div class="header-left">
        <h2 class="page-title">AI智能问诊</h2>
        <p class="page-desc">基于医学知识库的AI智能问答系统</p>
      </div>
      <el-button type="success" size="large" @click="showUpload = true" class="upload-btn">
        <span class="btn-icon">📚</span> 上传知识库
      </el-button>
    </div>

    <!-- 对话区域 -->
    <div class="chat-container">
      <div class="messages" ref="messagesRef">
        <div v-if="messages.length === 0" class="empty-state">
          <div class="empty-icon">🤖</div>
          <p>您好！我是AI医疗助手，请问有什么可以帮您的？</p>
          <p class="empty-hint">您可以上传医学资料，我将基于知识库为您智能问答</p>
        </div>

        <div
          v-for="(msg, i) in messages"
          :key="i"
          :class="['message', msg.role]"
        >
          <div class="msg-avatar">
            {{ msg.role === 'user' ? '👤' : '🤖' }}
          </div>
          <div class="msg-content">
            {{ msg.content }}
            <div v-if="msg.sources?.length" class="msg-sources">参考资料：{{ msg.sources.join('、') }}</div>
          </div>
        </div>

        <div v-if="loading" class="message ai">
          <div class="msg-avatar">🤖</div>
          <div class="msg-content loading-dots">
            <span></span><span></span><span></span>
          </div>
        </div>
      </div>

      <div class="input-area">
        <el-input
          v-model="question"
          type="textarea"
          :rows="3"
          placeholder="请输入医学问题，按 Enter 发送"
          class="chat-input"
          maxlength="2000"
          @keydown.enter="handleEnter"
        />
        <div class="input-actions">
          <span class="input-hint">Enter 发送 · Shift+Enter 换行</span>
          <el-button type="primary" @click="send" :loading="loading" class="send-btn">
            发送
          </el-button>
        </div>
      </div>
    </div>

    <!-- 知识库上传弹窗 -->
    <el-dialog
      v-model="showUpload"
      title="上传医学知识库"
      width="620px"
      class="upload-dialog"
    >
      <el-tabs v-model="uploadTab" class="upload-tabs">
        <el-tab-pane label="粘贴文本" name="text">
          <el-input
            v-model="uploadText"
            type="textarea"
            :rows="10"
            placeholder="请粘贴或输入医学资料内容..."
            class="upload-textarea"
          />
        </el-tab-pane>
        <el-tab-pane label="上传文件" name="file">
          <el-upload
            ref="uploadRef"
            class="upload-file"
            drag
            :auto-upload="false"
            :limit="1"
            accept=".txt,.md,.json,.csv,.pdf"
            :on-change="handleFileChange"
            v-model:file-list="fileList"
            :on-remove="handleFileRemove"
            :on-exceed="() => ElMessage.warning('请先移除已选文件再选择新文件')"
          >
            <div class="upload-icon-area">
              <el-icon class="upload-icon"><UploadFilled /></el-icon>
              <div class="upload-text">将文件拖到此处，或<em>点击上传</em></div>
              <div class="upload-hint">支持 .txt .md .json .csv .pdf 等文件</div>
            </div>
          </el-upload>
        </el-tab-pane>
      </el-tabs>

      <template #footer>
        <el-button @click="showUpload = false">取消</el-button>
        <el-button type="primary" @click="upload" :loading="uploading">
          {{ uploading ? '上传中...' : '开始上传' }}
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, nextTick } from 'vue'
import { ElMessage } from 'element-plus'
import { UploadFilled } from '@element-plus/icons-vue'
import { chat, uploadKnowledge, uploadFile } from '../api/rag'

const question = ref('')
const messages = ref([])
const loading = ref(false)
const showUpload = ref(false)
const uploadTab = ref('text')
const uploadText = ref('')
const uploading = ref(false)
const messagesRef = ref(null)
const fileList = ref([])
function scrollToBottom() {
  nextTick(() => {
    if (messagesRef.value) {
      messagesRef.value.scrollTop = messagesRef.value.scrollHeight
    }
  })
}

const selectedFile = ref(null)

function handleEnter(event) {
  if (event.shiftKey || event.isComposing || event.keyCode === 229) { return }
  event.preventDefault()
  send()
}

function send() {
  if (loading.value) return
  const q = question.value.trim()
  if (!q) return

  messages.value.push({ role: 'user', content: q })
  question.value = ''
  scrollToBottom()
  loading.value = true

  chat(q)
    .then(res => {
      messages.value.push({ role: 'ai', content: res.data.answer, sources: res.data.sources })
    })
    .catch(error => {
      messages.value.push({ role: 'ai', content: error.message || 'AI服务暂时不可用，请稍后重试。' })
    })
    .finally(() => {
      loading.value = false
      scrollToBottom()
    })
}

function handleFileChange(file) {
  if (file.raw.size > 16 * 1024 * 1024) {
    ElMessage.warning('文件不能超过16 MB')
    fileList.value = []
    selectedFile.value = null
    return
  }
  selectedFile.value = file.raw
}

function handleFileRemove() {
  selectedFile.value = null
}

function upload() {
  if (uploading.value) return
  if (uploadTab.value === 'text') {
    const content = uploadText.value.trim()
    if (!content) {
      ElMessage.warning('请输入知识文本')
      return
    }
    uploading.value = true
    uploadKnowledge(content)
      .then(() => {
        ElMessage.success('知识库构建成功')
        uploadText.value = ''
        showUpload.value = false
      })
      .catch(() => {})
      .finally(() => { uploading.value = false })
  } else {
    if (!selectedFile.value) {
      ElMessage.warning('请选择文件')
      return
    }
    uploading.value = true
    uploadFile(selectedFile.value)
      .then(() => {
        ElMessage.success('知识库构建成功')
        fileList.value = []
        selectedFile.value = null
        showUpload.value = false
      })
      .catch(() => {})
      .finally(() => { uploading.value = false })
  }
}
</script>

<style scoped>
.chat-page {
  display: flex;
  flex-direction: column;
  gap: 20px;
  height: calc(100vh - 80px);
  height: calc(100dvh - 116px);
  min-height: 400px;
}

.page-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-shrink: 0;
}

.page-title {
  font-size: 22px;
  font-weight: 700;
  color: #1a202c;
  margin: 0 0 4px;
}

.page-desc {
  font-size: 13px;
  color: #718096;
  margin: 0;
}

.upload-btn {
  padding: 10px 24px;
  border-radius: 10px;
  font-weight: 600;
}

.btn-icon {
  margin-right: 4px;
}

.chat-container {
  flex: 1;
  display: flex;
  flex-direction: column;
  background: #fff;
  border-radius: 20px;
  border: 1px solid #e2e8f0;
  overflow: hidden;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.06);
  min-height: 0;
}

.messages {
  flex: 1;
  overflow-y: auto;
  padding: 24px;
  display: flex;
  flex-direction: column;
  gap: 16px;
  background: linear-gradient(180deg, #f7fafc 0%, #edf2f7 100%);
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 60px 20px;
  color: #a0aec0;
  text-align: center;
}

.empty-icon {
  font-size: 64px;
  margin-bottom: 16px;
}

.empty-state p {
  font-size: 16px;
  color: #4a5568;
  margin: 4px 0;
}

.empty-hint {
  font-size: 13px !important;
  color: #a0aec0 !important;
}

.message {
  display: flex;
  gap: 12px;
  max-width: 80%;
  animation: fadeIn 0.3s ease;
}

@keyframes fadeIn {
  from { opacity: 0; transform: translateY(10px); }
  to { opacity: 1; transform: translateY(0); }
}

.message.user {
  align-self: flex-end;
  flex-direction: row-reverse;
}

.message.ai {
  align-self: flex-start;
}

.msg-avatar {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 18px;
  flex-shrink: 0;
  background: #fff;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
}

.message.user .msg-avatar {
  background: linear-gradient(135deg, #667eea, #764ba2);
}

.message.ai .msg-avatar {
  background: linear-gradient(135deg, #38b2ac, #3182ce);
}

.msg-content {
  padding: 12px 18px;
  border-radius: 16px;
  font-size: 14px;
  line-height: 1.7;
  white-space: pre-wrap;
  word-break: break-word;
}
.msg-sources { margin-top: 8px; font-size: 12px; color: #718096; }

.message.user .msg-content {
  background: linear-gradient(135deg, #667eea, #764ba2);
  color: #fff;
  border-bottom-right-radius: 4px;
}

.message.ai .msg-content {
  background: #fff;
  color: #2d3748;
  border: 1px solid #e2e8f0;
  border-bottom-left-radius: 4px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
}

.loading-dots {
  display: flex;
  gap: 4px;
  padding: 16px 18px;
}

.loading-dots span {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #a0aec0;
  animation: bounce 1.2s infinite;
}

.loading-dots span:nth-child(2) { animation-delay: 0.2s; }
.loading-dots span:nth-child(3) { animation-delay: 0.4s; }

@keyframes bounce {
  0%, 80%, 100% { transform: scale(0.6); opacity: 0.4; }
  40% { transform: scale(1); opacity: 1; }
}

.input-area {
  padding: 16px 20px;
  background: #fff;
  border-top: 1px solid #e2e8f0;
  display: flex;
  flex-direction: column;
  gap: 10px;
  flex-shrink: 0;
}

.chat-input :deep(.el-textarea__inner) {
  border-radius: 12px;
  padding: 12px 16px;
  font-size: 14px;
  border: 1px solid #e2e8f0;
  transition: all 0.3s;
}

.chat-input :deep(.el-textarea__inner:focus) {
  border-color: #63b3ed;
  box-shadow: 0 0 0 3px rgba(99, 179, 237, 0.1);
}

.input-actions {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.input-hint {
  font-size: 12px;
  color: #a0aec0;
}

.send-btn {
  padding: 8px 28px;
  border-radius: 10px;
  font-weight: 600;
}

.upload-tabs :deep(.el-tabs__content) {
  padding-top: 12px;
}

.upload-textarea :deep(.el-textarea__inner) {
  border-radius: 12px;
}

.upload-file :deep(.el-upload-dragger) {
  border-radius: 16px;
  border: 2px dashed #cbd5e0;
}

.upload-file :deep(.el-upload-list__item .el-icon--close) { display: inline-flex !important; }
.upload-file :deep(.el-upload-list__item-status-label) { display: none !important; }

.upload-icon-area {
  padding: 40px 0;
}

.upload-icon {
  font-size: 48px;
  color: #63b3ed;
}

.upload-text {
  margin-top: 12px;
  font-size: 14px;
  color: #4a5568;
}

.upload-hint {
  margin-top: 6px;
  font-size: 12px;
  color: #a0aec0;
}

:deep(.upload-dialog) {
  border-radius: 16px !important;
  overflow: hidden;
}

:deep(.upload-dialog .el-dialog__header) {
  background: linear-gradient(135deg, #276749, #38a169);
  padding: 20px 24px;
}

:deep(.upload-dialog .el-dialog__title) {
  color: #fff;
  font-weight: 600;
}

:deep(.upload-dialog .el-dialog__headerbtn .el-dialog__close) {
  color: #fff;
}
</style>
