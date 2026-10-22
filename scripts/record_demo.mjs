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

try {
  await scene('03', '/login', async page => {
    await page.getByPlaceholder('请输入账号', { exact: true }).pressSequentially('reviewer', { delay: 80 })
    await page.getByPlaceholder('请输入密码', { exact: true }).fill('ReviewDemo2026!')
    await click(page.locator('.login-btn'))
    await expect(page).toHaveURL(/\/home$/)
    await expect(page.getByText('已登记患者')).toBeVisible()
    evidence.events.push({ scene: '03', login_and_home: 'passed' })
  })
  await scene('04', '/patient', async page => {
    await click(page.getByRole('button', { name: '新增患者' }))
    await page.getByPlaceholder('请输入姓名', { exact: true }).pressSequentially('演示患者', { delay: 150 })
    await page.getByPlaceholder('请输入年龄', { exact: true }).fill('35')
    await page.getByPlaceholder('请输入地址', { exact: true }).fill('合成演示数据，不对应真实住址')
    await page.getByPlaceholder('请输入既往病史', { exact: true }).fill('仅用于系统评审，不含真实病史')
    await page.waitForTimeout(1500)
    await click(page.getByRole('button', { name: '保存', exact: true }))
    await expect(page.getByRole('row').filter({ hasText: '演示患者' })).toBeVisible()
    evidence.events.push({ scene: '04', patient_creation: 'passed' })
  })
  await scene('05', '/medical', async page => {
    await click(page.getByRole('button', { name: '新增病历' }))
    await click(page.getByRole('combobox', { name: /选择患者/ }))
    await click(page.getByRole('option', { name: /演示患者/ }))
    await page.getByPlaceholder('请输入医生姓名').fill('演示医生')
    await page.getByPlaceholder('请输入诊断结果').fill('合成就诊记录，用于功能展示')
    await page.getByPlaceholder('请输入症状描述').fill('演示录入，不包含临床判断')
    await page.getByPlaceholder('请输入治疗方案').fill('展示病历关联与数据保存流程')
    await page.getByPlaceholder('请输入用药信息').fill('无用药示例')
    await page.waitForTimeout(2000)
    await click(page.getByRole('button', { name: '保存', exact: true }))
    await expect(page.getByRole('row').filter({ hasText: '合成就诊记录' })).toBeVisible()
    evidence.events.push({ scene: '05', medical_record_creation: 'passed' })
  })
  await scene('06', '/patient', async page => {
    const row = page.getByRole('row').filter({ hasText: '演示患者' })
    await click(row.getByRole('button'))
    const denied = page.waitForResponse(r => r.url().includes('/api/patient/delete/'))
    await click(page.getByRole('button', { name: '确定', exact: true }))
    const response = await denied
    expect(response.status()).toBe(409)
    await expect(page.getByText('该患者仍有关联病历，请先处理病历后再删除')).toBeVisible()
    await page.screenshot({ path: path.join(assets, 'demo-protection.png') })
    await expect(row).toBeVisible()
    evidence.events.push({ scene: '06', related_patient_delete_status: response.status() })
  })
  await scene('07', '/ai', async page => {
    await click(page.getByRole('button', { name: '上传知识库' }))
    await click(page.getByRole('tab', { name: '上传文件' }))
    await page.locator('input[type=file]').setInputFiles(path.join(root, 'docs', 'demo_knowledge.md'))
    await page.waitForTimeout(1800)
    const upload = page.waitForResponse(r => r.url().endsWith('/api/rag/upload-file'))
    await click(page.getByRole('button', { name: '开始上传' }))
    const response = await upload
    expect(response.ok()).toBeTruthy()
    const body = await response.json()
    evidence.events.push({ scene: '07', upload: body.data, status: response.status() })
    await expect(page.getByText('知识库构建成功', { exact: true })).toBeVisible()
    // 再次上传相同文件，实际验证哈希去重。
    await click(page.getByRole('button', { name: '上传知识库' }))
    await page.locator('input[type=file]').setInputFiles(path.join(root, 'docs', 'demo_knowledge.md'))
    const repeated = page.waitForResponse(r => r.url().endsWith('/api/rag/upload-file'))
    await click(page.getByRole('button', { name: '开始上传' }))
    const again = await (await repeated).json()
    expect(again.data.added).toBe(0)
    evidence.events.push({ scene: '07', duplicate_upload: again.data })
  })
  await scene('08', '/ai', async page => {
    const input = page.getByPlaceholder('请输入医学问题，按 Enter 发送')
    await input.pressSequentially('演示随访登记窗口什么时候开放，需要准备哪些登记材料？', { delay: 80 })
    const chat = page.waitForResponse(r => r.url().endsWith('/api/rag/chat'))
    await click(page.getByRole('button', { name: '发送', exact: true }))
    const response = await chat
    expect(response.ok()).toBeTruthy()
    const body = await response.json()
    expect(body.data.sources).toContain('demo_knowledge.md')
    expect(body.data.answer).toMatch(/预约编号/)
    await expect(page.locator('.msg-sources')).toContainText('demo_knowledge.md')
    evidence.events.push({ scene: '08', status: response.status(), ...body.data })
  })
  await scene('09', '/ai', async page => {
    const input = page.getByPlaceholder('请输入医学问题，按 Enter 发送')
    await input.pressSequentially('请仅根据资料给出演示患者的药物剂量。', { delay: 100 })
    const chat = page.waitForResponse(r => r.url().endsWith('/api/rag/chat'))
    await click(page.getByRole('button', { name: '发送', exact: true }))
    const response = await chat
    expect(response.ok()).toBeTruthy()
    const body = await response.json()
    expect(body.data.answer).toMatch(/不足|无法|不能|未.*提供|没有.*剂量|不包含/)
    await expect(page.locator('.message.ai .msg-content')).toContainText(body.data.answer)
    evidence.events.push({ scene: '09', status: response.status(), ...body.data })
  })
  await fs.writeFile(path.join(root, 'output', 'video', 'demo-evidence.json'), JSON.stringify(evidence, null, 2))
} finally {
  await browser.close()
}
