<template>
  <div class="login-page">
    <!-- 左侧装饰区 -->
    <div class="login-left">
      <div class="left-content">
        <div class="brand">
          <div class="brand-icon">🏥</div>
          <h1>智慧医疗平台</h1>
          <p class="brand-slogan">Intelligent Medical Platform</p>
        </div>
        <div class="features">
          <div class="feature-item">
            <span class="feature-icon">👤</span>
            <span>患者档案管理</span>
          </div>
          <div class="feature-item">
            <span class="feature-icon">📋</span>
            <span>电子病历记录</span>
          </div>
          <div class="feature-item">
            <span class="feature-icon">🤖</span>
            <span>AI 智能问诊</span>
          </div>
          <div class="feature-item">
            <span class="feature-icon">📊</span>
            <span>数据统计分析</span>
          </div>
        </div>
      </div>
      <!-- 装饰粒子 -->
      <div class="particles">
        <div class="particle p1"></div>
        <div class="particle p2"></div>
        <div class="particle p3"></div>
        <div class="particle p4"></div>
        <div class="particle p5"></div>
      </div>
    </div>

    <!-- 右侧登录表单 -->
    <div class="login-right">
      <div class="login-form-wrap">
        <div class="form-header">
          <h2>欢迎登录</h2>
          <p>请输入您的账号信息</p>
        </div>

        <el-form
          ref="formRef"
          :model="form"
          :rules="rules"
          class="login-form"
        >
          <el-form-item prop="username">
            <el-input
              v-model="form.username"
              placeholder="请输入账号"
              :prefix-icon="User"
              size="large"
              class="input-item"
            />
          </el-form-item>

          <el-form-item prop="password">
            <el-input
              v-model="form.password"
              type="password"
              placeholder="请输入密码"
              :prefix-icon="Lock"
              size="large"
              show-password
              class="input-item"
              @keyup.enter="handleLogin"
            />
          </el-form-item>

          <el-button
            type="primary"
            size="large"
            :loading="loading"
            class="login-btn"
            @click="handleLogin"
          >
            {{ loading ? '登录中...' : '登 录' }}
          </el-button>
        </el-form>

        <div class="form-footer">
          <span>请使用管理员提供的账号登录，密码可在登录后修改</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { User, Lock } from '@element-plus/icons-vue'
import { login } from '../api/user'
import { saveSession } from '../utils/auth'

const router = useRouter()
const formRef = ref(null)
const loading = ref(false)

const form = reactive({
  username: '',
  password: ''
})

const rules = {
  username: [{ required: true, message: '请输入账号', trigger: 'blur' }],
  password: [{ required: true, message: '请输入密码', trigger: 'blur' }]
}

function handleLogin() {
  if (loading.value) return
  formRef.value.validate(async (valid) => {
    if (!valid) return

    loading.value = true
    try {
      const res = await login(form)
      saveSession(res.data)
      ElMessage.success(res.msg || '登录成功')
      router.push('/home')
    } catch {
      // 请求拦截器统一展示具体错误。
    } finally {
      loading.value = false
    }
  })
}
</script>

<style scoped>
.login-page {
  height: 100vh;
  display: flex;
  overflow: hidden;
  background: #0f1c3f;
}

/* 左侧 */
.login-left {
  flex: 1;
  background: linear-gradient(135deg, #1a365d 0%, #0d47a1 50%, #1565c0 100%);
  display: flex;
  align-items: center;
  justify-content: center;
  position: relative;
  overflow: hidden;
  padding: 40px;
}

.left-content {
  position: relative;
  z-index: 2;
  text-align: center;
}

.brand-icon {
  font-size: 80px;
  display: block;
  margin-bottom: 20px;
  filter: drop-shadow(0 4px 20px rgba(255, 255, 255, 0.3));
  animation: float 3s ease-in-out infinite;
}

@keyframes float {
  0%, 100% { transform: translateY(0); }
  50% { transform: translateY(-10px); }
}

.brand h1 {
  font-size: 42px;
  font-weight: 800;
  color: #fff;
  margin: 0 0 12px;
  letter-spacing: 4px;
  text-shadow: 0 2px 20px rgba(0, 0, 0, 0.3);
}

.brand-slogan {
  font-size: 14px;
  color: rgba(255, 255, 255, 0.6);
  letter-spacing: 3px;
  text-transform: uppercase;
  margin-bottom: 48px;
}

.features {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.feature-item {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 12px;
  color: rgba(255, 255, 255, 0.85);
  font-size: 15px;
  padding: 12px 24px;
  border-radius: 12px;
  background: rgba(255, 255, 255, 0.08);
  border: 1px solid rgba(255, 255, 255, 0.12);
  backdrop-filter: blur(10px);
  transition: all 0.3s;
}

.feature-item:hover {
  background: rgba(255, 255, 255, 0.15);
  transform: translateX(8px);
}

.feature-icon {
  font-size: 20px;
}

/* 装饰粒子 */
.particle {
  position: absolute;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.06);
  animation: drift 8s ease-in-out infinite;
}

.p1 { width: 300px; height: 300px; top: -80px; right: -80px; animation-delay: 0s; }
.p2 { width: 200px; height: 200px; bottom: 60px; left: -60px; animation-delay: 2s; }
.p3 { width: 150px; height: 150px; top: 40%; right: 10%; animation-delay: 4s; }
.p4 { width: 80px; height: 80px; bottom: 20%; right: 20%; animation-delay: 1s; }
.p5 { width: 120px; height: 120px; top: 20%; left: 15%; animation-delay: 3s; }

@keyframes drift {
  0%, 100% { transform: translateY(0) scale(1); }
  50% { transform: translateY(30px) scale(1.05); }
}

/* 右侧表单区 */
.login-right {
  width: 480px;
  background: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: -10px 0 40px rgba(0, 0, 0, 0.2);
  z-index: 10;
}

.login-form-wrap {
  width: 100%;
  padding: 48px 40px;
}

.form-header {
  margin-bottom: 40px;
}

.form-header h2 {
  font-size: 28px;
  font-weight: 700;
  color: #1a202c;
  margin: 0 0 8px;
}

.form-header p {
  font-size: 14px;
  color: #718096;
  margin: 0;
}

.login-form {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.input-item :deep(.el-input__wrapper) {
  border-radius: 12px;
  padding: 12px 16px;
  box-shadow: 0 0 0 1px #e2e8f0 !important;
  transition: all 0.3s;
}

.input-item :deep(.el-input__wrapper:hover) {
  box-shadow: 0 0 0 1px #63b3ed !important;
}

.input-item :deep(.el-input__wrapper.is-focus) {
  box-shadow: 0 0 0 1px #63b3ed !important;
  box-shadow: 0 0 0 3px rgba(99, 179, 237, 0.15) !important;
}

.login-btn {
  margin-top: 8px;
  height: 50px !important;
  border-radius: 12px !important;
  font-size: 16px !important;
  font-weight: 600 !important;
  letter-spacing: 4px;
  background: linear-gradient(135deg, #2b6cb0, #3182ce) !important;
  border: none !important;
  box-shadow: 0 4px 15px rgba(49, 130, 206, 0.4) !important;
  transition: all 0.3s !important;
}

.login-btn:hover {
  transform: translateY(-2px);
  box-shadow: 0 8px 25px rgba(49, 130, 206, 0.5) !important;
}

.form-footer {
  text-align: center;
  margin-top: 24px;
  font-size: 12px;
  color: #a0aec0;
}
</style>
