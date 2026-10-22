import assert from 'node:assert/strict'
import { beforeEach, test } from 'node:test'
import { clearSession, getStoredUser, getToken, saveSession } from '../src/utils/auth.js'

const values = new Map()
globalThis.localStorage = {
  getItem: key => values.get(key) ?? null,
  setItem: (key, value) => values.set(key, String(value)),
  removeItem: key => values.delete(key)
}
beforeEach(() => values.clear())

function token(exp) {
  return 'header.' + Buffer.from(JSON.stringify({ exp })).toString('base64url') + '.signature'
}

test('missing session returns null', () => {
  assert.equal(getToken(), null)
  assert.equal(getStoredUser(), null)
})

test('corrupted user data does not crash the page', () => {
  localStorage.setItem('user', '{broken')
  assert.equal(getStoredUser(), null)
  assert.equal(localStorage.getItem('user'), null)
})

test('expired tokens clear both token and user', () => {
  saveSession({ token: token(Date.now() / 1000 - 1), user: { username: 'test' } })
  assert.equal(getToken(), null)
  assert.equal(getStoredUser(), null)
})

test('malformed tokens cannot satisfy the route guard', () => {
  for (const value of ['garbage', 'header.invalid.signature', token('forever')]) {
    localStorage.setItem('token', value)
    assert.equal(getToken(), null)
  }
})

test('valid sessions retain the signed token', () => {
  const value = token(Math.floor(Date.now() / 1000) + 60)
  saveSession({ token: value, user: { username: 'test' } })
  assert.equal(getToken(), value)
  assert.equal(getStoredUser().username, 'test')
})

test('logout clears all local authentication data', () => {
  saveSession({ token: token(Date.now() / 1000 + 60), user: { username: 'test' } })
  clearSession()
  assert.equal(getToken(), null)
  assert.equal(getStoredUser(), null)
})
