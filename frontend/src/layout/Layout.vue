<template>
  <el-container class="layout">
    <!-- 左侧边栏 -->
    <div v-if="sidebarOpen" class="sidebar-mask" @click="sidebarOpen = false" />
    <el-aside width="260px" class="aside" :class="{ 'mobile-open': sidebarOpen }">
      <div class="logo-wrap">
        <div class="logo-icon">🏥</div>
        <div class="logo-text">智慧医疗平台</div>
      </div>

      <el-menu
        :default-active="activeMenu"
        router
        background-color="#0f1c3f"
        text-color="#a0aec0"
        active-text-color="#63b3ed"
        class="menu"
      >
        <el-menu-item index="/home">
          <span class="menu-icon">📊</span>
          <span>首页概览</span>
        </el-menu-item>

        <el-menu-item index="/patient">
          <span class="menu-icon">👤</span>
          <span>患者管理</span>
        </el-menu-item>

        <el-menu-item index="/medical">
          <span class="menu-icon">📋</span>
          <span>电子病历</span>
        </el-menu-item>

        <el-menu-item index="/ai">
          <span class="menu-icon">🤖</span>
          <span>AI智能问诊</span>
        </el-menu-item>
      </el-menu>

      <div class="user-info">
        <div class="user-avatar">
          <img :src="userAvatar" alt="avatar" />
        </div>
        <div class="user-detail">
          <div class="user-name">{{ currentUser?.real_name || '管理员' }}</div>
          <div class="user-role">{{ currentUser?.role || 'admin' }}</div>
        </div>
        <el-button link class="logout-btn" @click="handleLogout">退出</el-button>
      </div>
    </el-aside>

    <!-- 右侧主内容区 -->
    <el-container class="content-container">
      <el-header class="header">
        <div class="header-left">
          <el-button class="mobile-menu-btn" aria-label="打开菜单" @click="sidebarOpen = true">☰</el-button>
          <span class="header-title">
            <router-link to="/home">智慧医疗信息管理平台</router-link>
          </span>
        </div>
        <div class="header-right">
          <el-button @click="showPassword = true">修改密码</el-button>
          <el-tag :type="serviceReady ? 'success' : 'warning'" effect="plain" class="status-tag">
            {{ serviceReady ? '服务已连接' : '服务连接中' }}
          </el-tag>
        </div>
      </el-header>

      <el-main class="main">
        <router-view />
      </el-main>
    </el-container>
    <PasswordDialog v-model="showPassword" />
  </el-container>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import PasswordDialog from '../components/PasswordDialog.vue'
import { getCurrentUser, getHealth } from '../api/user'
import { clearSession, getStoredUser } from '../utils/auth'

const router = useRouter()
const route = useRoute()

const activeMenu = computed(() => route.path)

const currentUser = ref(getStoredUser())
const sidebarOpen = ref(false)
const showPassword = ref(false)
const serviceReady = ref(false)
watch(() => route.path, () => { sidebarOpen.value = false })
onMounted(() => {
  getCurrentUser().then(res => {
    currentUser.value = res.data
    localStorage.setItem('user', JSON.stringify(res.data))
  }).catch(() => {})
  getHealth().then(() => { serviceReady.value = true }).catch(() => {})
})

const userAvatar =
  'data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHZpZXdCb3g9IjAgMCAxMDAgMTAwIj48Y2lyY2xlIGN4PSI1MCIgY3k9IjUwIiByPSI1MCIgZmlsbD0iIzZjNGZlYiIvPjxjaXJjbGUgY3g9IjUwIiBjeT0iMzgiIHI9IjE0IiBmaWxsPSIjZmZmIiBvcGFjaXR5PSIwLjkiLz48cGF0aCBkPSJNMjAgODVjMC0xNi41NjkgMTMuNDMxLTMwIDMwLTMwczMwIDEzLjQzMSAzMCAzMEg0MHoiIGZpbGw9IiNmZmYiIG9wYWNpdHk9IjAuOCIvPjwvc3ZnPg=='

function handleLogout() {
  clearSession()
  router.push('/login')
}
</script>

<style scoped>
.layout {
  height: 100vh;
  height: 100dvh;
  overflow: hidden;
}

.aside {
  background: linear-gradient(180deg, #0f1c3f 0%, #1a2744 100%);
  display: flex;
  flex-direction: column;
  box-shadow: 4px 0 20px rgba(0, 0, 0, 0.3);
  position: relative;
  z-index: 10;
}

.logo-wrap {
  height: 70px;
  display: flex;
  align-items: center;
  padding: 0 24px;
  gap: 12px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.08);
}

.logo-icon {
  font-size: 30px;
  filter: drop-shadow(0 0 8px rgba(99, 179, 237, 0.6));
}

.logo-text {
  font-size: 18px;
  font-weight: 700;
  color: #f0f6ff;
  letter-spacing: 1px;
  background: linear-gradient(90deg, #f0f6ff, #63b3ed);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
}

.menu {
  flex: 1;
  padding: 8px 0;
  border: none;
  background: transparent;
}

.menu-item {
  border-radius: 10px;
  margin: 4px 12px;
}

.menu-icon {
  margin-right: 10px;
  font-size: 18px;
}

/* 覆盖 Element Plus 默认样式 */
:deep(.el-menu) {
  border-right: none !important;
}

:deep(.el-menu--collapse) {
  width: 64px;
}

:deep(.el-menu-item) {
  height: 52px !important;
  line-height: 52px !important;
  border-radius: 12px !important;
  margin: 4px 12px !important;
  transition: all 0.3s ease !important;
}

:deep(.el-menu-item:hover) {
  background: rgba(99, 179, 237, 0.15) !important;
  color: #63b3ed !important;
}

:deep(.el-menu-item.is-active) {
  background: linear-gradient(135deg, rgba(99, 179, 237, 0.25), rgba(66, 153, 225, 0.15)) !important;
  color: #63b3ed !important;
  box-shadow: 0 0 15px rgba(99, 179, 237, 0.2) !important;
}

.user-info {
  display: flex;
  align-items: center;
  padding: 16px 20px;
  border-top: 1px solid rgba(255, 255, 255, 0.08);
  gap: 12px;
}

.user-avatar img {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  border: 2px solid rgba(99, 179, 237, 0.5);
}

.user-detail {
  flex: 1;
  min-width: 0;
}

.user-name {
  color: #f0f6ff;
  font-size: 14px;
  font-weight: 600;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.user-role {
  color: #718096;
  font-size: 11px;
  margin-top: 2px;
}

.logout-btn {
  color: #a0aec0 !important;
  font-size: 12px;
}

.logout-btn:hover {
  color: #fc8181 !important;
}

.header {
  background: #fff;
  border-bottom: 1px solid #edf2f7;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 32px;
  height: 60px !important;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.04);
}

.header-title {
  font-size: 16px;
  font-weight: 600;
  color: #1a202c;
  text-decoration: none;
  letter-spacing: 0.5px;
}

.header-title a {
  text-decoration: none;
  color: inherit;
  background: linear-gradient(135deg, #2b6cb0, #63b3ed);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
}

.status-tag {
  font-size: 12px;
  padding: 4px 12px;
  border-radius: 20px;
}

.main {
  background: #f7fafc;
  padding: 28px;
  overflow-y: auto;
}

.content-container, .main { min-width: 0; }
.header-left, .header-right { display: flex; align-items: center; gap: 12px; }
.mobile-menu-btn { display: none; }
.sidebar-mask { display: none; }
@media (max-width: 768px) {
  .aside { position: fixed; inset: 0 auto 0 0; height: 100dvh; transform: translateX(-100%); transition: transform .2s; z-index: 100; }
  .aside.mobile-open { transform: translateX(0); }
  .sidebar-mask { display: block; position: fixed; inset: 0; background: #0008; z-index: 90; }
  .mobile-menu-btn { display: inline-flex; }
  .header { padding: 0 12px; }
  .header-title { display: none; }
  .status-tag { display: none; }
  .main { padding: 16px 12px; }
}
</style>
