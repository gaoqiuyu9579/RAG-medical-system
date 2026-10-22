/** 本地登录状态读取；损坏或过期的数据不会导致页面崩溃。 */
export function clearSession() {
  localStorage.removeItem('token')
  localStorage.removeItem('user')
}

export function getStoredUser() {
  try {
    const user = JSON.parse(localStorage.getItem('user') || 'null')
    return user && typeof user === 'object' && !Array.isArray(user) ? user : null
  } catch {
    localStorage.removeItem('user')
    return null
  }
}

export function getToken() {
  const token = localStorage.getItem('token')
  if (!token) return null
  try {
    const part = token.split('.')[1]
    const encoded = part.replace(/-/g, '+').replace(/_/g, '/')
    const payload = JSON.parse(atob(encoded.padEnd(Math.ceil(encoded.length / 4) * 4, '=')))
    if (typeof payload.exp !== 'number' || payload.exp * 1000 <= Date.now()) {
      clearSession()
      return null
    }
    return token
  } catch {
    clearSession()
    return null
  }
}

export function saveSession(data) {
  localStorage.setItem('token', data.token)
  localStorage.setItem('user', JSON.stringify(data.user))
}
