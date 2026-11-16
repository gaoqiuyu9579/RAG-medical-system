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

body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Microsoft YaHei', sans-serif; }
.page-enter-active, .page-leave-active { transition: opacity .22s ease, transform .22s ease; }
.page-enter-from { opacity: 0; transform: translateY(8px); }.page-leave-to { opacity: 0; transform: translateY(-6px); }
.el-table .recently-saved > td.el-table__cell { animation: saved-row 2.8s ease-out; }
@keyframes saved-row { 0%,25% { background-color: #bdebd5; } 100% { background-color: transparent; } }
.validation-shake .el-form-item.is-error { animation: validation-shake .4s; }
@keyframes validation-shake { 20%,60% { transform: translateX(-5px); } 40%,80% { transform: translateX(5px); } }
.danger-confirm .el-message-box__message { color: #c53030; line-height: 1.8; }
.save-error { margin-bottom: 18px; }
.table-card { transition: box-shadow .25s; }
@media(prefers-reduced-motion: reduce) { *, *::before, *::after { animation-duration: .01ms !important; transition-duration: .01ms !important; } }

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
