import request from './request'

export function login(data) {
  return request.post('/user/login', data)
}

export function getUsers() {
  return request.get('/user/list')
}

export function getCurrentUser() {
  return request.get('/user/me')
}

export function changePassword(data) {
  return request.post('/user/password', data)
}

export function getStats() {
  return request.get('/user/stats')
}

export function getHealth() {
  return request.get('/health')
}
