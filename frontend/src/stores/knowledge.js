import { reactive } from 'vue'
import { getKnowledgeStatus } from '../api/rag'
import { postEvents } from '../api/stream'

export const knowledge = reactive({ documents: 0, chunks: 0, ready: false, loading: true, uploading: false, stage: '', error: '' })
// 上传属于知识库任务；切换页面后继续接收服务端进度，侧栏和弹窗共用状态。
export const knowledgeUpload = reactive({ uploading: false, stage: '', message: '', error: '' })

export function resetKnowledgeUpload() {
  if (knowledgeUpload.uploading) return
  Object.assign(knowledgeUpload, { stage: '', message: '', error: '' })
}

export async function importKnowledge(body) {
  if (knowledgeUpload.uploading) return false
  Object.assign(knowledgeUpload, { uploading: true, stage: 'uploading', message: '上传中 · 正在传输资料', error: '' })
  knowledge.uploading = true
  knowledge.stage = '上传中'
  try {
    await postEvents('upload-stream', body, event => {
      if (event.type === 'progress') {
        knowledgeUpload.stage = event.stage
        knowledgeUpload.message = event.message
        knowledge.stage = event.stage === 'parsing' ? '解析中' : '向量化中'
      }
      if (event.type === 'done') {
        knowledgeUpload.stage = 'complete'
        knowledgeUpload.message = `完成 · 新增 ${event.result.added} 个片段，知识库共 ${event.result.total} 个片段${event.result.added === 0 ? '（相同内容已去重）' : ''}`
      }
    })
    return true
  } catch (error) {
    knowledgeUpload.error = error.message
    return false
  } finally {
    knowledgeUpload.uploading = false
    knowledge.uploading = false
    knowledge.stage = ''
    await refreshKnowledge()
  }
}

export async function refreshKnowledge() {
  knowledge.loading = true
  try {
    const response = await getKnowledgeStatus()
    Object.assign(knowledge, response.data, { error: '' })
  } catch (error) {
    knowledge.error = error.message
  } finally {
    knowledge.loading = false
  }
}
