// 在隔离的演示实例中录制真实浏览器操作；不拦截接口或替换模型回答。
import fs from 'node:fs/promises'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import { createRequire } from 'node:module'

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..')
const require = createRequire(path.join(root, 'frontend', 'package.json'))
const { chromium, expect } = require('@playwright/test')
const raw = path.join(root, 'output', 'video', 'raw')
const assets = path.join(root, 'docs', 'assets')
await fs.mkdir(raw, { recursive: true })
await fs.mkdir(assets, { recursive: true })
const browser = await chromium.launch({ channel: 'msedge', headless: true })
let state
const evidence = { recorded_at_utc: new Date().toISOString(), ai_mode: 'real-configured-clients',
  business_database: 'isolated SQLite; deployment uses MySQL', events: [] }

async function scene(id, route, action) {
  const context = await browser.newContext({ viewport: { width: 1920, height: 936 },
    recordVideo: { dir: raw, size: { width: 1920, height: 936 } },
    storageState: state, locale: 'zh-CN' })
  const page = await context.newPage()
  page.setDefaultTimeout(120000)
  const errors = []
  page.on('pageerror', error => errors.push(error.message))
  await page.goto('http://127.0.0.1:5502' + route)
  await page.waitForTimeout(1000)
  await action(page)
  await page.waitForTimeout(2500)
  await page.screenshot({ path: path.join(assets, `demo-${id}.png`) })
  state = await context.storageState()
  const video = page.video()
  await context.close()
  await video.saveAs(path.join(raw, `${id}.webm`))
  await video.delete()
  expect(errors).toEqual([])
  console.log(`Recorded scene ${id}`)
}

async function click(locator) {
  const box = await locator.boundingBox()
  if (box) await locator.page().mouse.move(box.x + box.width / 2, box.y + box.height / 2, { steps: 12 })
  await locator.click()
  await locator.page().waitForTimeout(500)
}

async function readEvents(response) {
  expect(response.ok()).toBeTruthy()
  const events = (await response.text()).split(/\r?\n\r?\n/).filter(Boolean).map(frame => JSON.parse(frame.replace(/^data: /, '')))
  expect(events.some(event => event.type === 'error')).toBeFalsy()
  expect(events.at(-1).type).toBe('done')
  return { events, answer: events.filter(event => event.type === 'delta').map(event => event.content).join(''), ...events.at(-1) }
}

try {
  await scene('03', '/login', async page => {
    await page.getByPlaceholder('请输入账号', { exact: true }).pressSequentially('admin', { delay: 80 })
    await page.getByPlaceholder('请输入密码', { exact: true }).fill('admin123456')
    await click(page.locator('.login-btn'))
    await expect(page).toHaveURL(/\/home$/)
    await expect(page.getByText('已登记患者')).toBeVisible()
    evidence.events.push({ scene: '03', login_and_home: 'passed' })
  })
  await scene('04', '/patient', async page => {
    await click(page.getByRole('button', { name: '新增患者' }))
    await click(page.getByRole('button', { name: '保存', exact: true }))
    await expect(page.getByText('请输入患者姓名', { exact: true })).toBeVisible()
    await page.waitForTimeout(1500)
    await page.getByPlaceholder('请输入姓名', { exact: true }).pressSequentially('钱某某', { delay: 150 })
    await page.getByPlaceholder('请输入年龄', { exact: true }).fill('65')
    await page.locator('.el-form-item').filter({ hasText: '性别' }).locator('.el-select').click()
    await page.getByRole('option', { name: '男', exact: true }).click()
    await page.getByPlaceholder('请输入电话', { exact: true }).fill('13800000021')
    await page.getByPlaceholder('请输入地址', { exact: true }).fill('青岛市示范社区21号（合成地址）')
    await page.getByPlaceholder('请输入既往病史', { exact: true }).fill('高血压病史 8 年，定期复诊（合成档案）')
    await page.waitForTimeout(1500)
    await click(page.getByRole('button', { name: '保存', exact: true }))
    const row = page.getByRole('row').filter({ hasText: '钱某某' })
    await expect(row).toBeVisible()
    await page.waitForTimeout(1500)
    await click(row.getByRole('button', { name: /编辑/ }))
    await page.getByPlaceholder('请输入电话', { exact: true }).fill('13800000022')
    await click(page.getByRole('button', { name: '保存', exact: true }))
    await expect(row).toContainText('13800000022')
    evidence.events.push({ scene: '04', patient_creation: 'passed' })
  })
  await scene('05', '/medical', async page => {
    await click(page.getByRole('button', { name: '新增病历' }))
    await click(page.getByRole('combobox', { name: /选择患者/ }))
    await click(page.getByRole('option', { name: /钱某某/ }))
    await page.getByPlaceholder('请输入医生姓名').fill('王医生')
    await page.getByPlaceholder('请输入诊断结果').fill('高血压随访（合成记录）')
    await page.getByPlaceholder('请输入症状描述').fill('常规随访，记录近期自述情况（合成）')
    await page.getByPlaceholder('请输入治疗方案').fill('完善随访记录，按既有诊疗计划复诊（合成）')
    await page.getByPlaceholder('请输入用药信息').fill('按原处方核对，示例不含剂量')
    await page.waitForTimeout(2000)
    await click(page.getByRole('button', { name: '保存', exact: true }))
    await expect(page.getByRole('row').filter({ hasText: '钱某某' })).toBeVisible()
    evidence.events.push({ scene: '05', medical_record_creation: 'passed' })
  })
  await scene('06', '/patient', async page => {
    const row = page.getByRole('row').filter({ hasText: '钱某某' })
    await click(row.getByRole('button', { name: /删除/ }))
    await page.waitForTimeout(1500)
    const denied = page.waitForResponse(r => r.url().includes('/api/patient/delete/'))
    await click(page.getByRole('button', { name: '确定', exact: true }))
    const response = await denied
    expect(response.status()).toBe(409)
    await expect(page.getByText('该患者仍有关联病历，请先处理病历后再删除')).toBeVisible()
    await page.screenshot({ path: path.join(assets, 'demo-protection.png') })
    await expect(row).toBeVisible()
    evidence.events.push({ scene: '06', related_patient_delete_status: response.status() })
    await click(page.getByRole('button', { name: '新增患者' }))
    await page.getByPlaceholder('请输入姓名', { exact: true }).fill('何某某')
    await page.getByPlaceholder('请输入年龄', { exact: true }).fill('52')
    await page.getByPlaceholder('请输入电话', { exact: true }).fill('13800000023')
    await page.getByPlaceholder('请输入地址', { exact: true }).fill('青岛市示范社区23号（合成地址）')
    await page.getByPlaceholder('请输入既往病史', { exact: true }).fill('无特殊既往史（合成）')
    await click(page.getByRole('button', { name: '保存', exact: true }))
    const temporary = page.getByRole('row').filter({ hasText: '何某某' })
    await click(temporary.getByRole('button', { name: /删除/ }))
    await click(page.getByRole('button', { name: '确定', exact: true }))
    await expect(temporary).toHaveCount(0)
    await page.waitForTimeout(1400)
    await click(page.getByRole('button', { name: '撤销', exact: true }))
    await expect(temporary).toBeVisible()
    evidence.events.push({ scene: '06', undo_delete: 'original archive restored' })
  })
  await scene('07', '/ai', async page => {
    await click(page.getByRole('button', { name: '上传知识库' }))
    await click(page.getByRole('tab', { name: '上传文件' }))
    await page.locator('input[type=file]').setInputFiles(path.join(root, 'docs', 'demo_knowledge.md'))
    await page.waitForTimeout(1800)
    const upload = page.waitForResponse(r => r.url().endsWith('/api/rag/upload-stream'))
    await click(page.getByRole('button', { name: '开始上传' }))
    const response = await upload
    expect(response.ok()).toBeTruthy()
    const body = await readEvents(response)
    evidence.events.push({ scene: '07', upload: body.result, stages: body.events, status: response.status() })
    await expect(page.locator('.upload-progress')).toContainText('完成 · 新增')
    await page.waitForTimeout(1800)
    await click(page.getByRole('button', { name: '完成', exact: true }))
    // 使用同一个实际 HTTP 端点验证重复导入；不替换或拦截浏览器接口。
    const token = await page.evaluate(() => localStorage.getItem('token'))
    const repeated = await page.context().request.post('http://127.0.0.1:5502/api/rag/upload-file', {
      headers: { Authorization: 'Bearer ' + token },
      multipart: { file: { name: 'demo_knowledge.md', mimeType: 'text/markdown',
        buffer: await fs.readFile(path.join(root, 'docs', 'demo_knowledge.md')) } }
    })
    expect(repeated.ok()).toBeTruthy()
    const again = await repeated.json()
    expect(again.data.added).toBe(0)
    evidence.events.push({ scene: '07', duplicate_upload: again.data })
  })
  await scene('08', '/ai', async page => {
    const input = page.getByPlaceholder('请输入医学问题，按 Enter 发送')
    await input.pressSequentially('演示随访登记窗口什么时候开放，需要准备哪些登记材料？', { delay: 80 })
    const chat = page.waitForResponse(r => r.url().endsWith('/api/rag/chat-stream'))
    await click(page.getByRole('button', { name: '发送', exact: true }))
    const response = await chat
    expect(response.ok()).toBeTruthy()
    const body = await readEvents(response)
    expect(body.sources).toContain('demo_knowledge.md')
    expect(body.answer).toMatch(/预约编号/)
    await expect(input).toBeEnabled({ timeout: 120000 })
    await expect(page.locator('.msg-sources')).toContainText('demo_knowledge.md')
    await click(page.locator('.citation-card summary').first())
    await expect(page.locator('.citation-card[open] mark').first()).toBeVisible()
    evidence.events.push({ scene: '08', status: response.status(), ...body })
  })
  await scene('09', '/ai', async page => {
    const input = page.getByPlaceholder('请输入医学问题，按 Enter 发送')
    await input.pressSequentially('请仅根据资料给出演示患者的药物剂量。', { delay: 100 })
    const chat = page.waitForResponse(r => r.url().endsWith('/api/rag/chat-stream'))
    await click(page.getByRole('button', { name: '发送', exact: true }))
    const response = await chat
    expect(response.ok()).toBeTruthy()
    const body = await readEvents(response)
    expect(body.answer).toMatch(/不足|无法|不能|未.*提供|没有.*剂量|不包含/)
    await expect(input).toBeEnabled({ timeout: 120000 })
    await expect(page.locator('.message.ai .msg-content')).toContainText(body.answer)
    evidence.events.push({ scene: '09', status: response.status(), ...body })
  })
  await scene('10', '/statistics', async page => {
    await expect(page.locator('.chart canvas')).toHaveCount(2)
    await page.waitForTimeout(1800)
    await page.locator('.chart').first().hover({ position: { x: 390, y: 150 } })
    await page.waitForTimeout(2000)
    await page.locator('.trend-heading .el-select').click()
    await page.getByRole('option', { name: '近 7 天', exact: true }).click()
    await page.waitForTimeout(1800)
    await page.locator('.trend-heading .el-select').click()
    const stats = page.waitForResponse(r => r.url().includes('/api/user/analytics?days=30'))
    await page.getByRole('option', { name: '近 30 天', exact: true }).click()
    const result = (await (await stats).json()).data
    expect(result.patientCount).toBeGreaterThanOrEqual(12)
    expect(result.periodRecords).toBeGreaterThan(30)
    evidence.events.push({ scene: '10', analytics: result })
  })
  await fs.writeFile(path.join(root, 'output', 'video', 'demo-evidence.json'), JSON.stringify(evidence, null, 2))
} finally {
  await browser.close()
}
