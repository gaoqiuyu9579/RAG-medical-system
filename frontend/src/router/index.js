import { createRouter, createWebHistory } from 'vue-router'
const Login = () => import('../views/Login.vue')
const Layout = () => import('../layout/Layout.vue')
const Home = () => import('../views/Home.vue')
const Patient = () => import('../views/Patient.vue')
const MedicalRecord = () => import('../views/MedicalRecord.vue')
const AIChat = () => import('../views/AIChat.vue')
import { getToken } from '../utils/auth'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/login', component: Login },
    {
      path: '/', component: Layout, redirect: '/home',
      children: [
        { path: 'home', component: Home },
        { path: 'patient', component: Patient },
        { path: 'medical', component: MedicalRecord },
        { path: 'ai', component: AIChat }
      ]
    },
    { path: '/:pathMatch(.*)*', redirect: '/home' }
  ]
})

router.beforeEach(to => {
  if (to.path !== '/login' && !getToken()) return '/login'
})

export default router
