import { test, expect } from '@playwright/test'

async function login(page, password = 'E2ePassword123') {
  await page.goto('/login')
  await page.getByPlaceholder('请输入账号', { exact: true }).fill('e2e-admin')
  await page.getByPlaceholder('请输入密码', { exact: true }).fill(password)
  await page.locator('.login-btn').click()
  await expect(page).toHaveURL(/\/home$/)
}

async function navigate(page, label) {
  const menuButton = page.getByRole('button', { name: '打开菜单' })
  if (await menuButton.isVisible()) await menuButton.click()
  await page.getByRole('menuitem', { name: new RegExp(label) }).click()
  if (await menuButton.isVisible()) {
    await expect.poll(() => page.evaluate(() => document.querySelector('.aside')?.getBoundingClientRect().right ?? 0)).toBeLessThanOrEqual(1)
  }
}

test.beforeEach(async ({ request }) => {
  const response = await request.post('/__test__/reset')
  expect(response.ok()).toBeTruthy()
})

test('login, navigation and mobile layout work without page errors', async ({ page }, testInfo) => {
  const errors = []
  page.on('pageerror', error => errors.push(error.message))
  await page.goto('/patient')
  await expect(page).toHaveURL(/\/login$/)
  await login(page)
  await expect(page.getByText('已登记患者')).toBeVisible()
  await navigate(page, '患者管理')
  await expect(page.getByRole('button', { name: '新增患者' })).toBeVisible()
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBeTruthy()
  await page.screenshot({ path: testInfo.outputPath('patient-page.png'), fullPage: true })
  expect(errors).toEqual([])
})

test('patient and medical record creation and deletion protect related data', async ({ page }) => {
  await login(page)
  await navigate(page, '患者管理')
  await page.getByRole('button', { name: '新增患者' }).click()
  await page.getByPlaceholder('请输入姓名', { exact: true }).fill('浏览器测试患者')
  await page.getByRole('button', { name: '保存', exact: true }).click()
  const patientRow = page.getByRole('row').filter({ hasText: '浏览器测试患者' })
  await expect(patientRow).toBeVisible()

  await navigate(page, '电子病历')
  await page.getByRole('button', { name: '新增病历' }).click()
  await page.getByRole('combobox', { name: /选择患者/ }).click()
  await page.getByRole('option', { name: /浏览器测试患者/ }).click()
  await page.getByPlaceholder('请输入诊断结果').fill('仅用于自动测试')
  await page.getByRole('button', { name: '保存', exact: true }).click()
  await expect(page.getByRole('row').filter({ hasText: '仅用于自动测试' })).toBeVisible()

  await navigate(page, '患者管理')
  await patientRow.getByRole('button').click()
  await page.getByRole('button', { name: '确定', exact: true }).click()
  await expect(page.getByText('该患者仍有关联病历，请先处理病历后再删除')).toBeVisible()
  await expect(patientRow).toBeVisible()

  await navigate(page, '电子病历')
  await page.getByRole('row').filter({ hasText: '仅用于自动测试' }).getByRole('button').click()
  await page.getByRole('button', { name: '确定', exact: true }).click()
  await expect(page.getByRole('row').filter({ hasText: '仅用于自动测试' })).toHaveCount(0)
  await navigate(page, '患者管理')
  await patientRow.getByRole('button').click()
  await page.getByRole('button', { name: '确定', exact: true }).click()
  await expect(patientRow).toHaveCount(0)
})

test('historical records with missing patients are marked for review', async ({ page }) => {
  await login(page)
  await page.route('**/api/patient/list', route => route.fulfill({ json: {
    code: 200, data: [{ id: 4, name: '合成患者', patient_no: 'P4' }]
  } }))
  await page.route('**/api/medical/list', route => route.fulfill({ json: {
    code: 200, data: [
      { id: 1, patient_id: 1, diagnosis: '历史合成记录一' },
      { id: 2, patient_id: 2, diagnosis: '历史合成记录二' },
      { id: 7, patient_id: 1, diagnosis: '历史合成记录三' },
      { id: 8, patient_id: 4, diagnosis: '有效合成记录' }
    ]
  } }))
  await navigate(page, '电子病历')
  await expect(page.getByText('有 3 条历史病历的患者信息缺失，待核对', { exact: true })).toBeVisible()
  await expect(page.getByRole('row').filter({ hasText: '历史合成记录二' })).toContainText('待核对（ID:2）')
  await expect(page.getByRole('row').filter({ hasText: '有效合成记录' })).toContainText('合成患者')
  await expect(page.getByRole('button', { name: '新增病历' })).toBeVisible()
})

test('knowledge upload and question submission return answer and sources', async ({ page }) => {
  await login(page)
  await navigate(page, 'AI智能问诊')
  await page.getByRole('button', { name: '上传知识库' }).click()
  await page.getByPlaceholder('请粘贴或输入医学资料内容...').fill('演示资料编号 MED-DEMO-01，仅用于自动测试。')
  await page.getByRole('button', { name: '开始上传' }).click()
  await expect(page.getByText('知识库构建成功')).toBeVisible()
  const input = page.getByPlaceholder('请输入医学问题，按 Enter 发送')
  await input.fill('资料编号是什么？')
  await input.press('Enter')
  await expect(page.locator('.message.ai .msg-content')).toContainText('MED-DEMO-01')
  await expect(page.locator('.msg-sources')).toContainText('粘贴文本')
})

test('removing an upload selection prevents uploading the stale file', async ({ page }) => {
  await login(page)
  await navigate(page, 'AI智能问诊')
  await page.getByRole('button', { name: '上传知识库' }).click()
  await page.getByRole('tab', { name: '上传文件' }).click()
  await page.locator('input[type=file]').setInputFiles({
    name: 'example.txt', mimeType: 'text/plain', buffer: Buffer.from('test knowledge')
  })
  await expect(page.locator('.el-upload-list__item')).toHaveCount(1)
  await page.getByRole('button', { name: '删除', exact: true }).click()
  await page.getByRole('button', { name: '开始上传' }).click()
  await expect(page.getByText('请选择文件', { exact: true })).toBeVisible()
  await expect(page.locator('.el-upload-list__item')).toHaveCount(0)
})

test('password change rejects incorrect password and invalidates old sessions', async ({ page, request }) => {
  await login(page)
  const oldToken = await page.evaluate(() => localStorage.getItem('token'))
  await page.getByRole('button', { name: '修改密码', exact: true }).click()
  await page.getByPlaceholder('请输入原密码', { exact: true }).fill('wrong-password')
  await page.getByPlaceholder('请输入8到128个字符的新密码').fill('ChangedBrowserPassword456')
  await page.getByPlaceholder('请再次输入新密码').fill('ChangedBrowserPassword456')
  await page.getByRole('button', { name: '确认修改' }).click()
  await expect(page.getByText('原密码不正确', { exact: true })).toBeVisible()
  await page.getByPlaceholder('请输入原密码', { exact: true }).fill('E2ePassword123')
  await page.getByRole('button', { name: '确认修改' }).click()
  await expect(page).toHaveURL(/\/login$/)
  const response = await request.get('/api/user/me', { headers: { Authorization: 'Bearer ' + oldToken } })
  expect(response.status()).toBe(401)
  await login(page, 'ChangedBrowserPassword456')
})

test('corrupted local state redirects to login without crashing', async ({ page }) => {
  const errors = []
  page.on('pageerror', error => errors.push(error.message))
  await page.goto('/login')
  await page.evaluate(() => {
    localStorage.setItem('user', '{broken')
    localStorage.setItem('token', 'invalid-token')
  })
  await page.goto('/home')
  await expect(page).toHaveURL(/\/login$/)
  expect(errors).toEqual([])
})

test('server-side invalidation redirects an already open page', async ({ page, request }) => {
  await login(page)
  const token = await page.evaluate(() => localStorage.getItem('token'))
  const response = await request.post('/api/user/password', {
    headers: { Authorization: 'Bearer ' + token },
    data: { old_password: 'E2ePassword123', new_password: 'InvalidationTest456' }
  })
  expect(response.ok()).toBeTruthy()
  await navigate(page, '患者管理')
  await expect(page).toHaveURL(/\/login$/)
})
