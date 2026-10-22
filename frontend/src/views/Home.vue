<template>
  <div class="home">
    <!-- 欢迎区 -->
    <div class="welcome-banner">
      <div class="welcome-text">
        <h1>欢迎回来，{{ userName }} 👋</h1>
        <p>以下是今日系统运行概况</p>
      </div>
      <div class="welcome-time">
        <span class="time-value">{{ currentTime }}</span>
      </div>
    </div>

    <!-- 统计卡片 -->
    <div class="stats-grid">
      <div class="stat-card card-blue">
        <div class="stat-icon">👥</div>
        <div class="stat-info">
          <span class="stat-label">患者总数</span>
          <span class="stat-value">{{ stats.patientCount }}</span>
        </div>
        <div class="stat-trend">已登记患者</div>
      </div>

      <div class="stat-card card-green">
        <div class="stat-icon">🩺</div>
        <div class="stat-info">
          <span class="stat-label">今日病历</span>
          <span class="stat-value">{{ stats.todayVisit }}</span>
        </div>
        <div class="stat-trend">今日录入记录</div>
      </div>

      <div class="stat-card card-orange">
        <div class="stat-icon">📋</div>
        <div class="stat-info">
          <span class="stat-label">病历总数</span>
          <span class="stat-value">{{ stats.recordCount }}</span>
        </div>
        <div class="stat-trend">已保存病历</div>
      </div>

      <div class="stat-card card-purple">
        <div class="stat-icon">🤖</div>
        <div class="stat-info">
          <span class="stat-label">知识片段</span>
          <span class="stat-value">{{ stats.knowledgeChunks }}</span>
        </div>
        <div class="stat-trend">可检索医学资料</div>
      </div>
    </div>

    <!-- 快捷入口 -->
    <div class="quick-links">
      <h3 class="section-title">快捷操作</h3>
      <div class="link-grid">
        <router-link to="/patient" class="link-card">
          <span class="link-icon">➕</span>
          <span class="link-text">新增患者</span>
        </router-link>
        <router-link to="/medical" class="link-card">
          <span class="link-icon">📝</span>
          <span class="link-text">录入病历</span>
        </router-link>
        <router-link to="/ai" class="link-card">
          <span class="link-icon">💬</span>
          <span class="link-text">AI问诊</span>
        </router-link>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import { getStats } from '../api/user'
import { getKnowledgeStatus } from '../api/rag'
import { getStoredUser } from '../utils/auth'

const stats = ref({ patientCount: 0, todayVisit: 0, recordCount: 0, knowledgeChunks: 0 })
const currentTime = ref('')
const userName = ref(getStoredUser()?.real_name || '用户')

let timer = null

function updateTime() {
  const now = new Date()
  currentTime.value = now.toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit'
  })
}

function loadStats() {
  getStats().then(res => { Object.assign(stats.value, res.data) }).catch(() => {})
  getKnowledgeStatus().then(res => { stats.value.knowledgeChunks = res.data.chunks }).catch(() => {})
}

onMounted(() => {
  loadStats()
  updateTime()
  timer = setInterval(updateTime, 1000)
})

onUnmounted(() => {
  if (timer) clearInterval(timer)
})
</script>

<style scoped>
.home {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.welcome-banner {
  background: linear-gradient(135deg, #1e3a5f 0%, #2b6cb0 50%, #3182ce 100%);
  border-radius: 20px;
  padding: 32px 40px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  color: #fff;
  box-shadow: 0 8px 30px rgba(43, 108, 176, 0.3);
  position: relative;
  overflow: hidden;
}

.welcome-banner::after {
  content: '';
  position: absolute;
  top: -50%;
  right: -10%;
  width: 400px;
  height: 400px;
  background: rgba(255, 255, 255, 0.04);
  border-radius: 50%;
}

.welcome-text h1 {
  font-size: 26px;
  font-weight: 700;
  margin: 0 0 8px;
}

.welcome-text p {
  font-size: 14px;
  color: rgba(255, 255, 255, 0.7);
  margin: 0;
}

.time-value {
  font-size: 18px;
  font-weight: 600;
  color: rgba(255, 255, 255, 0.9);
  background: rgba(255, 255, 255, 0.1);
  padding: 8px 20px;
  border-radius: 12px;
  backdrop-filter: blur(10px);
}

/* 统计卡片 */
.stats-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 20px;
}

.stat-card {
  background: #fff;
  border-radius: 16px;
  padding: 24px;
  display: flex;
  flex-direction: column;
  gap: 12px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.06);
  border: 1px solid #edf2f7;
  transition: all 0.3s ease;
  position: relative;
  overflow: hidden;
}

.stat-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 12px 40px rgba(0, 0, 0, 0.1);
}

.stat-card::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 4px;
}

.card-blue::before { background: linear-gradient(90deg, #2b6cb0, #63b3ed); }
.card-green::before { background: linear-gradient(90deg, #276749, #68d391); }
.card-orange::before { background: linear-gradient(90deg, #c05621, #f6ad55); }
.card-purple::before { background: linear-gradient(90deg, #553c9a, #b794f4); }

.stat-icon {
  font-size: 32px;
  width: 56px;
  height: 56px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 14px;
  background: #f7fafc;
}

.card-blue .stat-icon { background: rgba(99, 179, 237, 0.12); }
.card-green .stat-icon { background: rgba(104, 211, 145, 0.12); }
.card-orange .stat-icon { background: rgba(246, 173, 85, 0.12); }
.card-purple .stat-icon { background: rgba(183, 148, 244, 0.12); }

.stat-info {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.stat-label {
  font-size: 13px;
  color: #718096;
}

.stat-value {
  font-size: 32px;
  font-weight: 800;
  color: #1a202c;
  line-height: 1;
}

.stat-trend {
  font-size: 12px;
  color: #68d391;
  font-weight: 500;
}

/* 快捷操作 */
.quick-links {
  background: #fff;
  border-radius: 16px;
  padding: 24px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.06);
  border: 1px solid #edf2f7;
}

.section-title {
  font-size: 16px;
  font-weight: 600;
  color: #2d3748;
  margin: 0 0 16px;
}

.link-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 16px;
}

.link-card {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 20px;
  border-radius: 12px;
  background: #f7fafc;
  border: 1px solid #edf2f7;
  text-decoration: none;
  color: #2d3748;
  font-weight: 500;
  transition: all 0.3s;
}

.link-card:hover {
  background: #ebf4ff;
  border-color: #90cdf4;
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(49, 130, 206, 0.15);
}

.link-icon {
  font-size: 24px;
}
</style>
