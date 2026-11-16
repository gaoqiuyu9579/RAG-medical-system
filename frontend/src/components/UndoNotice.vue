<template>
  <div class="undo-stack" aria-live="polite">
    <div v-for="item in items" :key="item.token" class="undo-notice" role="status">
      <span>✓ {{ item.label }}已删除 <small>可在 {{ item.seconds }} 秒内撤销</small></span>
      <el-button type="primary" link :loading="item.busy" @click="undo(item)">撤销</el-button>
    </div>
  </div>
</template>
<script setup>
import { ref, onBeforeUnmount } from 'vue'
import { ElMessage } from 'element-plus'
const props = defineProps({ restore: { type: Function, required: true } })
const emit = defineEmits(['restored'])
const items = ref([])
const timer = setInterval(() => {
  const now = Date.now()
  for (const item of items.value) item.seconds = Math.max(0, Math.ceil((item.expires - now) / 1000))
  items.value = items.value.filter(item => item.seconds > 0 || item.busy)
}, 250)
function show(label, receipt) {
  items.value.push({ label, token: receipt.restore_token, seconds: receipt.undo_seconds, expires: Date.now() + receipt.undo_seconds * 1000, busy: false })
}
async function undo(item) {
  if (item.busy) return
  item.busy = true
  try {
    const response = await props.restore(item.token)
    emit('restored', response.data)
    items.value = items.value.filter(value => value !== item)
    ElMessage.success('已撤销删除，原记录已恢复')
  } catch { /* 请求拦截器展示错误，允许在有效期内重试。 */ }
  finally { item.busy = false }
}
defineExpose({ show })
onBeforeUnmount(() => clearInterval(timer))
</script>
<style scoped>
.undo-stack { position: fixed; bottom: 24px; right: 24px; z-index: 2001; display: grid; gap: 10px; max-width: calc(100vw - 32px); }
.undo-notice { display: flex; align-items: center; gap: 24px; background: #f0fdf4; border: 1px solid #86ceaa; color: #166534; border-radius: 12px; padding: 15px 20px; box-shadow: 0 8px 30px #172f4820; }
small { display: block; margin-top: 3px; color: #54796a; }
</style>
