/** HTTP 与业务码统一处理，错误只提示一次。 */
import axios from 'axios'
import { ElMessage } from 'element-plus'
import { clearSession, getToken } from '../utils/auth'

const request = axios.create({ baseURL: '/api', timeout: 180000 })

request.interceptors.request.use(config => {
  const token = getToken()
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

function reportFailure(message, status) {
  if (status === 401) {
    clearSession()
    if (window.location.pathname !== '/login') window.location.replace('/login')
  }
  ElMessage.error({ message, grouping: true })
  const error = new Error(message)
  error.status = status
  return error
}

request.interceptors.response.use(response => {
  const res = response.data
  if (!res || typeof res !== 'object' || typeof res.code !== 'number') {
    return Promise.reject(reportFailure('服务器响应格式错误，请检查接口地址', 502))
  }
  if (res.code !== 200 && res.code !== 0) {
    return Promise.reject(reportFailure(res.msg || '请求失败', res.code))
  }
  return res
}, error => {
  const message = error.response?.data?.msg ||
    (error.code === 'ECONNABORTED' ? '请求超时，请稍后重试' : '网络连接失败，请检查服务是否启动')
  return Promise.reject(reportFailure(message, error.response?.status))
})

export default request
