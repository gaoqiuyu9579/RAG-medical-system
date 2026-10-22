<template>
  <router-view />
</template>


<script setup>
// 根组件
// 页面显示由 vue-router 控制
</script>


<style>
/* 全局基础样式 */

html,
body,
#app {
  width: 100%;
  height: 100%;
  margin: 0;
  padding: 0;
}


* {
  box-sizing: border-box;
}

.el-dialog { max-width: calc(100vw - 24px); }
@media (max-width: 768px) {
  .page-header { gap: 12px; flex-wrap: wrap; }
  .el-message-box { max-width: calc(100vw - 24px); }
  .welcome-banner { padding: 20px !important; flex-direction: column; align-items: flex-start !important; gap: 16px; }
  .stats-grid, .link-grid { grid-template-columns: repeat(2, minmax(0, 1fr)) !important; }
  .stat-card { padding: 16px !important; flex-wrap: wrap; }
  .login-left { display: none !important; }
  .login-right { width: 100% !important; flex: 1; min-width: 0; padding: 24px !important; }
  .login-form-wrap { width: 100% !important; max-width: 440px; }
  .chat-page { height: calc(100dvh - 92px) !important; }
}

</style>
