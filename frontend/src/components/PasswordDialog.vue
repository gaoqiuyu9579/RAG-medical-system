<template>
  <el-dialog v-model="visible" title="修改密码" width="460px" :close-on-click-modal="false">
    <el-form label-position="top" @submit.prevent="submit">
      <el-form-item label="原密码">
        <el-input v-model="form.old_password" type="password" show-password autocomplete="current-password" placeholder="请输入原密码" />
      </el-form-item>
      <el-form-item label="新密码">
        <el-input v-model="form.new_password" type="password" show-password autocomplete="new-password" placeholder="请输入8到128个字符的新密码" maxlength="128" />
      </el-form-item>
      <el-form-item label="确认新密码">
        <el-input v-model="confirmation" type="password" show-password autocomplete="new-password" placeholder="请再次输入新密码" @keyup.enter="submit" />
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="visible = false" :disabled="saving">取消</el-button>
      <el-button type="primary" @click="submit" :loading="saving">确认修改</el-button>
    </template>
  </el-dialog>
</template>

<script setup>
import { reactive, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { changePassword } from '../api/user'
import { clearSession } from '../utils/auth'

const visible = defineModel({ type: Boolean, default: false })
const form = reactive({ old_password: '', new_password: '' })
const confirmation = ref('')
const saving = ref(false)
const router = useRouter()

watch(visible, opened => {
  if (opened) {
    form.old_password = ''
    form.new_password = ''
    confirmation.value = ''
  }
})

async function submit() {
  if (saving.value) return
  if (!form.old_password) return ElMessage.warning('请输入原密码')
  if (form.new_password.length < 8 || form.new_password.length > 128) {
    return ElMessage.warning('新密码长度应为8到128个字符')
  }
  if (form.new_password !== confirmation.value) return ElMessage.warning('两次新密码不一致')
  saving.value = true
  try {
    await changePassword(form)
    clearSession()
    visible.value = false
    ElMessage.success('密码已修改，请使用新密码登录')
    await router.replace('/login')
  } catch {
    // 统一请求拦截器已经展示服务器错误。
  } finally {
    saving.value = false
  }
}
</script>
