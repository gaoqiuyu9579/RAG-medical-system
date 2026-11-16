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
    // 401 可能同时跳转登录页；Locator 断言会重试，不读取已销毁的页面执行环境。
    await expect(page.locator('.aside.mobile-open')).toHaveCount(0)
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
  await patientRow.getByRole('button', { name: /删除/ }).click()
  await page.getByRole('button', { name: '确定', exact: true }).click()
  await expect(page.getByText('该患者仍有关联病历，请先处理病历后再删除')).toBeVisible()
  await expect(patientRow).toBeVisible()

  await navigate(page, '电子病历')
  await page.getByRole('row').filter({ hasText: '仅用于自动测试' }).getByRole('button', { name: /删除/ }).click()
  await page.getByRole('button', { name: '确定', exact: true }).click()
  await expect(page.getByRole('row').filter({ hasText: '仅用于自动测试' })).toHaveCount(0)
  await navigate(page, '患者管理')
  await patientRow.getByRole('button', { name: /删除/ }).click()
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
  await expect(page.locator('.upload-progress')).toContainText('完成 · 新增 1 个片段')
  await page.getByRole('button', { name: '完成', exact: true }).click()
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

test('required field focuses error, saved rows highlight, editing and undo preserve archive', async ({ page }) => {
  await login(page)
  await navigate(page, '患者管理')
  await page.getByRole('button', { name: '新增患者' }).click()
  await page.getByRole('button', { name: '保存', exact: true }).click()
  const name = page.getByPlaceholder('请输入姓名', { exact: true })
  await expect(page.getByText('请输入患者姓名', { exact: true })).toBeVisible()
  await expect(name).toBeFocused()
  await name.fill('张某某')
  await page.getByPlaceholder('请输入年龄', { exact: true }).fill('65')
  await page.getByRole('button', { name: '保存', exact: true }).click()
  await expect(page.getByRole('button', { name: '已保存', exact: true })).toBeVisible()
  const row = page.getByRole('row').filter({ hasText: '张某某' })
  await expect(row).toHaveClass(/recently-saved/)
  const originalId = await row.locator('td').first().innerText()
  await row.getByRole('button', { name: /编辑/ }).click()
  await page.getByPlaceholder('请输入电话', { exact: true }).fill('13800000001')
  await page.getByRole('button', { name: '保存', exact: true }).click()
  await expect(row).toContainText('13800000001')
  await row.getByRole('button', { name: /删除/ }).click()
  await expect(page.locator('.el-message-box__message')).toContainText('张某某')
  await page.getByRole('button', { name: '确定', exact: true }).click()
  await expect(row).toHaveCount(0)
  await page.getByRole('button', { name: '撤销', exact: true }).click()
  await expect(row).toContainText('13800000001')
  await expect(row.locator('td').first()).toHaveText(originalId)
})

test('stream shows thinking, progressive answer, failure and retry without duplicate question', async ({ page }) => {
  await login(page)
  await navigate(page, 'AI智能问诊')
  let calls = 0
  await page.route('**/api/rag/chat-stream', async route => {
    calls++
    await new Promise(resolve => setTimeout(resolve, 500))
    await route.fulfill({ contentType: 'text/event-stream', body: calls === 1
      ? 'data: {"type":"delta","content":"部分回答"}\n\ndata: {"type":"error","message":"服务连接中断"}\n\n'
      : 'data: {"type":"delta","content":"高血压随访资料已检索。请核对引用中的原文。"}\n\ndata: {"type":"done","citations":[{"source":"随访资料.txt","excerpt":"高血压随访需要核对登记材料。","chunk":1}]}\n\n' })
  })
  const input = page.getByPlaceholder('请输入医学问题，按 Enter 发送')
  await input.fill('高血压如何随访？')
  await input.press('Enter')
  await expect(input).toBeDisabled()
  await expect(page.locator('.thinking')).toBeVisible()
  await expect(page.locator('.failure')).toContainText('服务连接中断')
  await input.fill('下一条尚未发送的问题')
  await page.getByRole('button', { name: '重试', exact: true }).click()
  await expect(input).toBeDisabled()
  await expect(page.locator('.answer-text').last()).toContainText('高血压')
  await expect(input).toBeEnabled()
  await expect(input).toHaveValue('下一条尚未发送的问题')
  await expect(page.locator('.message.user')).toHaveCount(1)
  await expect(page.locator('.message.ai')).toHaveCount(1)
  expect(calls).toBe(2)
  await page.locator('.citation-card summary').click()
  await expect(page.locator('.citation-excerpt mark').first()).toContainText('高血压')
})

test('statistics renders database totals and responsive ECharts for both time ranges', async ({ page, request }, testInfo) => {
  const errors = []
  page.on('pageerror', error => errors.push(error.message))
  await login(page)
  const token = await page.evaluate(() => localStorage.getItem('token'))
  const headers = { Authorization: 'Bearer ' + token }
  const patient = await request.post('/api/patient/add', { headers, data: { name: '李某某', age: 65 } })
  await request.post('/api/medical/add', { headers, data: { patient_id: (await patient.json()).data.id, diagnosis: '合成随访' } })
  await navigate(page, '数据统计分析')
  await expect(page.locator('.chart canvas')).toHaveCount(2)
  await expect(page.locator('.analytics-card').first().locator('strong')).toContainText('1')
  await expect(page.locator('.chart').first()).toHaveAttribute('aria-label', /60–74 岁1人/)
  await page.locator('.trend-heading .el-select').click()
  const response = page.waitForResponse(value => value.url().includes('/api/user/analytics?days=7'))
  await page.getByRole('option', { name: '近 7 天', exact: true }).click()
  expect((await (await response).json()).data.trend).toHaveLength(7)
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBeTruthy()
  await page.screenshot({ path: testInfo.outputPath('statistics.png'), fullPage: true })
  await navigate(page, '患者管理')
  expect(errors).toEqual([])
})

test('upload continues across navigation and restores progress when reopening the dialog', async ({ page }) => {
  await login(page)
  await navigate(page, 'AI智能问诊')
  let release
  const gate = new Promise(resolve => { release = resolve })
  let requests = 0
  await page.route('**/api/rag/upload-stream', async route => {
    requests++
    await gate
    await route.continue()
  })
  try {
    await page.getByRole('button', { name: '上传知识库' }).click()
    await page.getByPlaceholder('请粘贴或输入医学资料内容...').fill('导航期间持续导入的合成医学资料。')
    await page.getByRole('button', { name: '开始上传' }).click()
    await expect(page.locator('.knowledge-status')).toContainText('上传中')
    await page.goBack()
    await expect(page).toHaveURL(/\/home$/)
    await expect(page.locator('.knowledge-status')).toContainText('上传中')
    await navigate(page, 'AI智能问诊')
    await page.getByRole('button', { name: '上传知识库' }).click()
    await expect(page.getByRole('button', { name: '处理中' })).toBeDisabled()
    await expect(page.locator('.upload-progress')).toContainText('上传中 · 正在传输资料')
    release()
    await expect(page.locator('.upload-progress')).toContainText('完成 · 新增 1 个片段')
    await expect(page.locator('.knowledge-status')).toContainText('1 份文档')
    await expect(page.locator('.knowledge-status')).toContainText('已就绪')
    expect(requests).toBe(1)
  } finally { release() }
})

test('failed patient save keeps input, shows an inline error and retries only once', async ({ page }) => {
  await login(page)
  await navigate(page, '患者管理')
  let calls = 0
  await page.route('**/api/patient/add', async route => {
    calls++
    if (calls === 1) await route.fulfill({ status: 503, json: { code: 503, msg: '保存服务暂时不可用' } })
    else await route.continue()
  })
  await page.getByRole('button', { name: '新增患者' }).click()
  const name = page.getByPlaceholder('请输入姓名', { exact: true })
  await name.fill('张某某')
  await page.getByRole('button', { name: '保存', exact: true }).click()
  await expect(page.locator('.save-error')).toContainText('保存服务暂时不可用')
  await expect(name).toHaveValue('张某某')
  await page.getByRole('button', { name: '重试保存', exact: true }).click()
  await expect(page.getByRole('row').filter({ hasText: '张某某' })).toBeVisible()
  await expect(page.getByRole('dialog')).toHaveCount(0)
  expect(calls).toBe(2)
})

test('editing a patient highlights the same row without changing its position', async ({ page, request }) => {
  await login(page)
  const token = await page.evaluate(() => localStorage.getItem('token'))
  const headers = { Authorization: 'Bearer ' + token }
  const created = await request.post('/api/patient/add', { headers, data: { name: '张某某', age: 65, address: '合成地址', medical_history: '合成既往病史' } })
  const patient = (await created.json()).data
  await request.post('/api/patient/add', { headers, data: { name: '李某某', age: 58 } })
  await navigate(page, '患者管理')
  const ids = page.locator('.el-table__body-wrapper tbody tr td:first-child')
  await expect(ids).toHaveCount(2)
  const before = await ids.allTextContents()
  const row = page.getByRole('row').filter({ hasText: '张某某' })
  await row.getByRole('button', { name: /编辑/ }).click()
  await page.getByPlaceholder('请输入电话', { exact: true }).fill('13800000001')
  await page.getByRole('button', { name: '保存', exact: true }).click()
  await expect(row).toContainText('13800000001')
  await expect(row).toHaveClass(/recently-saved/)
  expect(await ids.allTextContents()).toEqual(before)
  const detail = (await (await request.get(`/api/patient/detail/${patient.id}`, { headers })).json()).data
  expect(detail.address).toBe('合成地址')
  expect(detail.medical_history).toBe('合成既往病史')
})

test('patient query entry searches, filters, shows details and resets', async ({ page, request }, testInfo) => {
  await login(page)
  const token = await page.evaluate(() => localStorage.getItem('token'))
  const headers = { Authorization: 'Bearer ' + token }
  for (const data of [
    { name: '张同名', patient_no: 'QUERY-100', gender: '男', age: 65, phone: '13800000001', address: '合成地址一号', medical_history: '合成高血压既往史' },
    { name: '张同名', patient_no: 'QUERY-1000', gender: '女', age: 28, phone: '13900000001' },
    { name: '李患者', patient_no: 'QUERY-200', gender: '男', age: 0 }
  ]) expect((await request.post('/api/patient/add', { headers, data })).ok()).toBeTruthy()

  await navigate(page, '电子病历')
  await page.getByRole('button', { name: '查询患者', exact: true }).click()
  await expect(page).toHaveURL(/\/patient$/)
  const form = page.getByRole('form', { name: '患者查询', exact: true })
  const keyword = form.getByRole('textbox', { name: '患者检索' })
  const rows = page.locator('.el-table__body-wrapper tbody tr')
  await expect(rows).toHaveCount(3)
  await keyword.fill('张同名')
  await keyword.press('Enter')
  await expect(rows).toHaveCount(2)
  await form.locator('.el-select').click()
  await page.getByRole('option', { name: '男', exact: true }).click()
  await form.getByRole('spinbutton', { name: '最小年龄' }).fill('60')
  await form.getByRole('spinbutton', { name: '最大年龄' }).fill('80')
  await form.getByRole('button', { name: '查询', exact: true }).click()
  await expect(rows).toHaveCount(1)
  await expect(rows.first()).toContainText('QUERY-100')
  await expect(rows.first()).not.toContainText('QUERY-1000')
  await expect(page.locator('.card-header')).toContainText('共 1 位患者')
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBeTruthy()
  await page.screenshot({ path: testInfo.outputPath('patient-query.png'), fullPage: true })
  await rows.first().getByRole('button', { name: /查看/ }).click()
  const detail = page.getByRole('dialog', { name: '患者详情' })
  await expect(detail).toContainText('合成地址一号')
  await expect(detail).toContainText('合成高血压既往史')
  await detail.getByRole('button', { name: '关闭', exact: true }).click()

  await form.getByRole('button', { name: '重置', exact: true }).click()
  await expect(rows).toHaveCount(3)
  await expect(keyword).toHaveValue('')
  await expect(form.getByRole('spinbutton', { name: '最小年龄' })).toHaveValue('')
  await keyword.fill('QUERY-100')
  await keyword.press('Enter')
  await expect(rows).toHaveCount(1)
  await expect(rows.first()).not.toContainText('QUERY-1000')
  await keyword.fill('13900000001')
  await keyword.press('Enter')
  await expect(rows).toHaveCount(1)
  await expect(rows.first()).toContainText('QUERY-1000')
  await keyword.fill('无匹配档案')
  await keyword.press('Enter')
  await expect(page.getByText('未找到符合条件的患者，请调整查询条件')).toBeVisible()
  await expect(page.locator('.card-header')).toContainText('共 0 位患者')
  await form.getByRole('button', { name: '重置', exact: true }).click()
  await expect(rows).toHaveCount(3)
  await form.getByRole('spinbutton', { name: '最小年龄' }).fill('80')
  await form.getByRole('spinbutton', { name: '最大年龄' }).fill('60')
  await form.getByRole('button', { name: '查询', exact: true }).click()
  await expect(page.locator('.search-validation')).toContainText('最小年龄不能大于最大年龄')
  await expect(rows).toHaveCount(3)
})

test('patient query paginates, returns to a valid page after deletion and restores', async ({ page, request }) => {
  await login(page)
  const token = await page.evaluate(() => localStorage.getItem('token'))
  const headers = { Authorization: 'Bearer ' + token }
  for (let i = 1; i <= 21; i++) {
    expect((await request.post('/api/patient/add', { headers, data: { name: `分页患者${String(i).padStart(2, '0')}` } })).ok()).toBeTruthy()
  }
  await navigate(page, '患者管理')
  const rows = page.locator('.el-table__body-wrapper tbody tr')
  await expect(rows).toHaveCount(20)
  await page.locator('.el-pagination .btn-next').click()
  await expect(rows).toHaveCount(1)
  await expect(rows.first()).toContainText('分页患者01')
  await expect(page.locator('.page-summary')).toContainText('第 2 页')
  await rows.first().getByRole('button', { name: /删除/ }).click()
  await page.getByRole('button', { name: '确定', exact: true }).click()
  await expect(page.locator('.page-summary')).toContainText('第 1 页')
  await expect(rows).toHaveCount(20)
  await expect(page.locator('.card-header')).toContainText('共 20 位患者')
  await page.getByRole('button', { name: '撤销', exact: true }).click()
  await expect(page.locator('.card-header')).toContainText('共 21 位患者')
  await page.locator('.el-pagination .btn-next').click()
  await expect(rows).toHaveCount(1)
  await expect(rows.first()).toContainText('分页患者01')
  const keyword = page.getByRole('textbox', { name: '患者检索' })
  await keyword.fill('分页患者21')
  await keyword.press('Enter')
  await expect(rows).toHaveCount(1)
  await expect(rows.first()).toContainText('分页患者21')
  await expect(page.locator('.page-summary')).toContainText('第 1 页')
  await page.getByRole('button', { name: '重置', exact: true }).click()
  await expect(rows).toHaveCount(20)
  await page.locator('.el-pagination__sizes .el-select').click()
  await page.getByRole('option', { name: '10条/页', exact: true }).click()
  await expect(rows).toHaveCount(10)
})

test('patient query ignores an older response after resetting and supports retry', async ({ page, request }) => {
  await login(page)
  const token = await page.evaluate(() => localStorage.getItem('token'))
  const headers = { Authorization: 'Bearer ' + token }
  for (const name of ['旧查询患者', '另一患者']) {
    await request.post('/api/patient/add', { headers, data: { name } })
  }
  await navigate(page, '患者管理')
  const rows = page.locator('.el-table__body-wrapper tbody tr')
  await expect(rows).toHaveCount(2)
  let release, fail = false
  const held = new Promise(resolve => { release = resolve })
  await page.route('**/api/patient/search?**', async route => {
    if (new URL(route.request().url()).searchParams.get('keyword') === '旧查询患者') await held
    if (fail) {
      fail = false
      await route.fulfill({ status: 503, json: { code: 503, msg: '查询服务暂时不可用' } })
    } else await route.continue()
  })
  const keyword = page.getByRole('textbox', { name: '患者检索' })
  try {
    await keyword.fill('旧查询患者')
    const pending = page.waitForRequest(request => new URL(request.url()).searchParams.get('keyword') === '旧查询患者')
    await keyword.press('Enter')
    await pending
    await page.getByRole('button', { name: '重置', exact: true }).click()
    await expect(page.getByRole('button', { name: '查询', exact: true })).not.toBeDisabled()
    const finished = page.waitForResponse(response => new URL(response.url()).searchParams.get('keyword') === '旧查询患者')
    release()
    await (await finished).finished()
    await page.evaluate(() => new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve))))
    await expect(rows).toHaveCount(2)
    await expect(page.locator('.card-header')).toContainText('共 2 位患者')
    fail = true
    await page.getByRole('button', { name: '查询', exact: true }).click()
    await expect(page.locator('.table-card .el-alert')).toContainText('查询服务暂时不可用')
    await page.getByRole('button', { name: '重新加载', exact: true }).click()
    await expect(page.locator('.table-card .el-alert')).toHaveCount(0)
    await expect(rows).toHaveCount(2)
  } finally { release() }
})
