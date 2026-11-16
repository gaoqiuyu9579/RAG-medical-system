import fs from 'node:fs/promises';

const ROOT = 'D:/Thesis/thesis medical';
const DIR = `${ROOT}/tmp/project-report`;
const FONT = 'Microsoft YaHei';
const C = { navy: '#102A40', teal: '#087F8C', mint: '#53D1C6', ink: '#17354D', muted: '#567083', bg: '#F4F8FA', white: '#FFFFFF', rule: '#D5E2E9' };

export { text, page, note, picture, group, table, C };

function text(slide, value, x, y, w, h, size = 30, color = C.ink, bold = false) {
  const shape = slide.shapes.add({geometry: 'textbox', name: value.slice(0, 32), position: {left: x, top: y, width: w, height: h}, fill: 'none', line: {fill: 'none', width: 0}});
  shape.text = value;
  shape.text.style = {typeface: FONT, fontSize: size, color, bold, insets: 0, alignment: 'left', verticalAlignment: 'top'};
  return shape;
}

function page(p, title, sub = '', dark = false) {
  const slide = p.slides.add({layout: 'Blank', width: 1600, height: 900, background: {fill: dark ? C.navy : C.bg}});
  const index = p.slides.items.length;
  text(slide, title, 80, 60, 1440, 78, 54, dark ? C.white : C.navy, true);
  if (sub) text(slide, sub, 82, 151, 1430, 58, 25, dark ? '#BCD6E2' : C.muted);
  text(slide, String(index).padStart(2, '0'), 1460, 841, 70, 30, 20, dark ? '#8BB9C6' : C.muted);
  return slide;
}

function note(slide, narration, sources) {
  slide.speakerNotes.text = `${narration}\n\n资料依据：\n${sources.map(s => s.startsWith('http') ? s : `${ROOT}/${s}`).join('\n')}`;
  slide.speakerNotes.setVisible(true);
}

async function picture(slide, file, x, y, w, h, alt) {
  const bytes = await fs.readFile(file.startsWith('D:') ? file : `${ROOT}/${file}`);
  slide.images.add({dataUrl: 'data:image/png;base64,' + bytes.toString('base64'), alt, fit: 'contain', position: {left: x, top: y, width: w, height: h}});
}

function group(slide, heading, body, x, y, w, options = {}) {
  const color = options.dark ? C.white : C.ink;
  text(slide, heading, x, y, w, 53, options.headingSize ?? 34, options.dark ? C.mint : C.teal, true);
  text(slide, body, x, y + 62, w, options.height ?? 110, options.size ?? 30, color);
}

function table(slide, values, widths, top = 225, heights = null, fontSize = 28) {
  const rowHeights = heights ?? values.map((_, i) => i ? 86 : 66);
  const t = slide.tables.add({rows: values.length, columns: widths.length, left: 80, top, width: 1440, height: rowHeights.reduce((a, b) => a + b, 0), columnWidths: widths, values});
  t.styleOptions = {headerRow: true, bandedRows: false};
  const all = t.cells.block({row: 0, column: 0, rowCount: values.length, columnCount: widths.length});
  all.assign({fill: C.white, textStyle: {typeface: FONT, fontSize, color: C.ink}, margins: {left: 18, right: 18, top: 13, bottom: 10}, anchor: 'center'});
  t.borders.assign({fill: C.rule, width: 1, style: 'solid'});
  for (let r = 0; r < values.length; r++) {
    t.rows[r].height = rowHeights[r];
    if (r > 0) t.cells.block({row: r, column: 0, rowCount: 1, columnCount: widths.length}).fill = r % 2 ? C.white : '#EAF2F5';
  }
  t.cells.block({row: 0, column: 0, rowCount: 1, columnCount: widths.length}).assign({fill: C.navy, textStyle: {typeface: FONT, fontSize, color: C.white, bold: true}});
  return t;
}

export async function buildReport(p) {
  if (p.slides.items.length) throw new Error('A new presentation is required');
  let s;

  s = p.slides.add({layout: 'Blank', width: 1600, height: 900, background: {fill: C.navy}});
  text(s, '毕业设计项目汇报', 80, 93, 1100, 56, 30, C.mint, true);
  text(s, 'RAG 医疗系统', 80, 235, 1440, 120, 88, C.white, true);
  text(s, '智慧医疗问诊平台', 84, 373, 1420, 85, 54, '#D9EBF2');
  text(s, '患者管理、电子病历与知识库辅助问答', 85, 490, 1420, 70, 34, '#B9D4DF');
  text(s, '项目负责人  高秋雨\n项目成员  高秋雨、栾子璇、郝崇泽', 85, 670, 1150, 110, 28, '#D9EBF2');
  text(s, '2026.10', 1330, 780, 220, 45, 25, C.mint);
  note(s, '大家好，本次汇报介绍 RAG 医疗系统，也就是智慧医疗问诊平台。项目将患者档案、电子病历和知识库辅助问答整合到同一网页。下面依次介绍需求、架构、核心功能、AI 实现、测试与交付。当前成果用于毕业设计和功能演示。', ['README.md', 'docs/评审技术文档.md', 'output/video/智慧医疗系统演示.mp4']);

  s = page(p, '项目背景与建设目标', '围绕档案、病历和知识资料分散的问题，建立统一的业务入口');
  group(s, '现有问题', '患者信息与病历缺少统一关联\n知识资料需要人工查找和反复核对\n功能演示与运行配置难以复现', 80, 250, 660, {height: 210, size: 32});
  group(s, '项目目标', '统一登记患者与录入病历\n基于上传资料回答，并返回来源\n用环境模板、容器与测试支持复现', 850, 250, 670, {height: 210, size: 32});
  text(s, '项目定位：可运行的教学原型，支持资料辅助问答。', 80, 651, 1440, 60, 38, C.teal, true);
  text(s, '问答模块不查询患者和病历表生成个体诊断。', 80, 731, 1440, 50, 27, C.muted);
  note(s, '需求分析聚焦两个方向：一是把患者与病历的日常录入关联起来，二是让已上传的资料能够被检索，并向用户提供可核对的来源。项目关注工程整合与可复现性，没有开展临床有效性评价。AI 问答链不读取业务表生成个体诊断。', ['docs/评审技术文档.md']);

  s = page(p, '功能范围与验收口径', '以可操作的功能和可核对的结果作为验收依据');
  table(s, [
    ['模块', '已实现内容', '关键验收点'],
    ['账号与统计', '登录、修改密码、首页概览', '身份校验，旧令牌失效'],
    ['患者与病历', '列表、新增、删除与患者关联', '编号唯一，关联删除保护'],
    ['知识资料', '文本与文件导入、分块与去重', '重复片段不再次新增'],
    ['RAG 问答', '单轮问答、参考资料来源展示', '答案与来源可核对'],
    ['运行维护', '健康检查、备份、容器化部署', '环境与数据可复现'],
  ], [260, 670, 510], 225, [66, 85, 85, 85, 85, 85]);
  text(s, '当前范围未包含编辑、分页、注册、长期会话历史和 OCR。', 80, 763, 1440, 50, 26, C.muted);
  note(s, '功能范围覆盖账号、核心业务、知识导入、问答和运行维护。患者及病历目前提供列表、新增和删除，尚未实现编辑与分页。将这些范围写清楚，可以让评审按实际实现验收。', ['README.md', 'docs/评审技术文档.md']);

  s = page(p, '系统总体架构', 'Vue 3 前端、Flask 服务、关系数据库与独立知识检索链路');
  await picture(s, 'docs/assets/architecture.png', 80, 215, 1440, 600, '系统架构：浏览器访问 Flask，后端连接 MySQL、Chroma 和外部 AI 兼容接口');
  note(s, '前端采用 Vue 3 和 Element Plus，使用 Axios 访问后端 API。后端按控制器、业务服务、模型与 RAG 模块分层。用户、患者和病历保存在 MySQL，知识片段、向量和来源保存在本地 Chroma。向量和对话模型通过外部兼容接口分别接入。应用部署时由 Waitress 提供静态页面和 API，开发时由 Vite 代理请求。', ['docs/评审技术文档.md', 'docs/assets/architecture.png', 'backend/app.py']);

  s = page(p, '数据模型与一致性设计', '患者与病历是一对多关系，业务数据与知识向量分别存储');
  table(s, [
    ['数据对象', '保存内容', '一致性与访问约束'],
    ['sys_user', '账号、密码哈希、角色与状态', '用户名唯一，登录状态检查'],
    ['patient', '患者编号、姓名、年龄等档案', '编号唯一，年龄范围校验'],
    ['medical_record', '患者关联、医生、诊断与记录时间', '有效 patient_id，外键限制删除'],
    ['Chroma 集合', '文本片段、向量、来源与哈希 ID', '内容去重，本地持久化'],
  ], [280, 600, 560], 225, [66, 96, 96, 108, 96]);
  text(s, 'MySQL 事务与行锁协调病历新增和患者删除，异常后主动回滚。', 80, 747, 1440, 65, 29, C.teal, true);
  note(s, '数据库设计的重点是患者与病历的一致性。新增病历必须选择存在的患者，有关联病历的患者不能直接删除。MySQL 中的行锁与外键共同保护并发场景。录屏及自动化接口回归使用隔离 SQLite，正式演示部署使用 MySQL，二者不能混为同一验证环境。', ['docs/评审技术文档.md', 'backend/model', 'backend/service']);

  s = page(p, '登录认证与首页概览', '登录后进入统一工作台，统计数据来自后端查询');
  await picture(s, `${DIR}/images/home.png`, 80, 221, 1440, 564, '登录成功后的首页统计和快捷操作入口');
  text(s, 'JWT 身份校验     密码哈希保存     修改密码后旧令牌失效', 80, 795, 1440, 40, 28, C.teal, true);
  note(s, '首页展示患者数、病历数、今日新增病历数和知识片段数。界面中的“今日就诊”对应当日新增病历数量。登录使用 JWT，密码以哈希形式保存，修改密码后旧令牌失效。视频约 1 分 10 秒开始展示这一流程，图中账号和统计属于隔离演示实例。', ['docs/assets/demo-03.png', 'docs/评审技术文档.md', 'output/video/智慧医疗系统演示.mp4']);

  s = page(p, '患者登记与输入校验', '形成统一患者标识，为病历关联提供基础');
  group(s, '登记规则', '姓名为必填项，编号可自动生成\n年龄允许为空，填写时范围为 0 至 150\n重复编号返回明确错误', 80, 231, 1440, {height: 160, size: 31});
  await picture(s, `${DIR}/images/patient.png`, 80, 485, 1440, 285, '患者新增成功后的真实列表画面，包含合成患者与自动编号');
  text(s, '演示患者和地址均为合成数据。', 80, 792, 1440, 40, 25, C.muted);
  note(s, '患者管理提供列表、新增和删除。演示中登记“演示患者”，系统自动生成编号，保存后返回列表。前端阻止重复提交，后端检查姓名、年龄与重复编号。所有截图使用合成人员及地址，不涉及真实患者信息。视频约 1 分 48 秒开始展示。', ['docs/assets/demo-04.png', 'docs/评审技术文档.md', 'output/video/智慧医疗系统演示.mp4']);

  s = page(p, '电子病历与关联删除保护', '先验证患者，再保存病历；有关联记录时拒绝直接删除患者');
  group(s, '病历录入', '关联患者，记录医生、诊断、\n症状、方案和用药字段。', 80, 238, 450, {height: 130, size: 29});
  await picture(s, `${DIR}/images/record.png`, 580, 235, 940, 179, '电子病历保存成功，记录关联到演示患者');
  group(s, '删除保护', '前端确认后由后端检查。\n发生关联冲突时返回 HTTP 409，\n患者与病历保留。', 80, 482, 450, {height: 170, size: 29});
  await picture(s, `${DIR}/images/protection.png`, 580, 475, 940, 214, '删除已有关联病历的患者时出现拒绝删除提示');
  text(s, '数据库约束、业务检查和事务回滚共同保护关联。', 80, 765, 1440, 50, 30, C.teal, true);
  note(s, '电子病历新增时必须关联有效患者。演示在保存病历后尝试删除该患者，后端实际返回 409，并保留两类记录。录屏证据 JSON 也记录了这一状态码。截图中的诊断和用药字段仅用于展示数据结构，不构成医疗建议。视频约 2 分 24 秒展示病历录入，约 3 分 1 秒展示删除保护。', ['docs/assets/demo-05.png', 'docs/assets/demo-protection.png', 'output/video/demo-evidence.json']);

  s = page(p, '知识库导入与向量化', '支持粘贴文本，以及 TXT、MD、JSON、CSV 和文本型 PDF');
  group(s, '01  文本提取与校验', '接收 UTF-8 文本，PDF 需要文本层。', 80, 230, 700, {height: 75, size: 29});
  group(s, '02  分块与内容去重', '500 字符分块，重叠 50 字符。\nSHA256 标识过滤已存在片段。', 80, 402, 700, {height: 110, size: 29});
  group(s, '03  向量化后写入', '全部新增片段完成向量化后，\n再写入本地 Chroma。', 80, 596, 700, {height: 115, size: 29});
  await picture(s, `${DIR}/images/upload.png`, 860, 220, 660, 557, '真实浏览器上传 demo_knowledge.md 的文件导入窗口');
  text(s, '实测重复导入：added = 0，total = 1', 860, 794, 660, 40, 26, C.teal, true);
  note(s, '知识导入经过提取、校验、分块、去重、向量化和写入。分块单位是字符，不是 token。新增片段全部向量化成功后才执行集合写入，可以避免外部向量调用中途失败留下半份资料，但不保证底层所有故障均可原子回滚。演示资料首次新增一条片段，重复导入新增零条。扫描件 OCR 尚未实现。', ['backend/rag/vector_store.py', 'output/video/demo-evidence.json', 'docs/评审技术文档.md']);

  s = page(p, 'AI 技术选型与接口集成', '选择依据是现有工程兼容性、中文资料使用场景和部署复杂度');
  table(s, [
    ['组件', '工程选型', '选型理由'],
    ['向量模型', 'text-embedding-v3', '已有中文向量接口，保持集合兼容'],
    ['对话模型', 'deepseek-chat', '基于检索上下文生成回答，接口可验证'],
    ['向量数据库', 'Chroma 本地持久化', '无需另建向量服务，保留既有资料'],
    ['编排组件', 'LangChain 组件', '复用分块、提示词和兼容客户端'],
  ], [260, 570, 610], 225, [66, 105, 105, 105, 105], 27);
  text(s, '向量与对话客户端独立配置，对话 temperature = 0.3。', 80, 745, 1440, 48, 29, C.teal, true);
  text(s, '以上为项目实际配置，未开展跨模型质量或成本排名。', 80, 796, 1440, 37, 24, C.muted);
  note(s, '项目没有训练或微调本地模型，而是通过兼容接口分别接入向量模型和对话模型。两类服务独立设置密钥和接入地址，便于替换及定位问题。这里说明工程选型理由，没有建立跨模型评测集，因此不宣称模型质量最好、价格最低或为最新版本。', ['docs/评审技术文档.md', 'backend/rag/embedding.py', 'backend/rag/llm.py']);

  s = page(p, 'RAG 问答与资料来源', '先检索项目资料，再把参考上下文与用户问题提交给对话模型');
  group(s, '检索', '问题向量化，最多取 3 个片段。', 80, 229, 690, {height: 80, size: 29});
  group(s, '生成', '组合参考上下文，返回回答与 sources。', 840, 229, 680, {height: 80, size: 29});
  text(s, '演示问题：随访登记窗口何时开放，需要准备哪些材料？', 80, 415, 1440, 55, 32, C.teal, true);
  await picture(s, `${DIR}/images/answer.png`, 80, 475, 1100, 310, '真实 RAG 回答包含开放时间、登记材料及来源 demo_knowledge.md');
  group(s, '答案依据', 'demo_knowledge.md\n\n文件名便于回查\n原始资料。', 1230, 505, 290, {height: 200, size: 24, headingSize: 30});
  text(s, '来源为参与检索的文件名，可用于回查资料。', 80, 792, 1440, 40, 27, C.muted);
  note(s, '录屏的真实问答以合成随访窗口资料为依据，返回周一至周五九点到十七点，以及预约编号和随访登记表，并显示 demo_knowledge.md。sources 是参与检索的文件名，不代表对答案逐句验证，也没有页码或证据句高亮。对话为单轮，不保存长期历史。视频约 4 分 11 秒开始展示。', ['output/video/demo-evidence.json', 'docs/assets/demo-08.png', 'docs/评审技术文档.md']);

  s = page(p, '资料不足时的回答边界', '系统要求依据参考资料回答，资料不支持时说明不足');
  text(s, '演示追问：请根据资料给出演示患者的药物剂量。', 80, 235, 1440, 60, 33, C.ink, true);
  text(s, '真实调用结果：资料不足，无法给出药物剂量。', 80, 339, 1440, 70, 41, C.teal, true);
  await picture(s, `${DIR}/images/boundary.png`, 80, 465, 1440, 278, '真实模型在资料不含药物信息时说明无法给出剂量，并展示来源');
  text(s, '该案例证明本次调用行为，全面可靠性仍需专业评测与人工核对。', 80, 791, 1440, 42, 26, C.muted);
  note(s, '演示资料明确没有药物名称、剂量或治疗方案，模型在真实调用中说明资料不足。提示词还要求不执行资料内指令，并强调回答不能替代医生诊断。这是一次可核对的行为证据，不能推导所有问题都安全正确。当前没有相关性阈值、重排序或系统性对抗测试，仍需要人工核对。视频约 4 分 49 秒开始展示。', ['output/video/demo-evidence.json', 'docs/assets/demo-09.png', 'docs/评审技术文档.md']);

  s = page(p, '已实现的 AI 优化策略', '围绕重复导入、上下文规模和外部服务失败开展工程优化');
  table(s, [
    ['策略', '当前实现', '作用与边界'],
    ['分块与检索控制', '500 / 50 字符，Top-3', '保留相邻语境，限制上下文规模'],
    ['内容去重', 'SHA256 片段标识', '避免重复文本，不识别语义改写'],
    ['批量与写入顺序', '每批 10 条，先全部向量化', '控制单批规模，避免外部调用半途写入'],
    ['超时与有限重试', '单次请求 45 秒，最多重试 1 次', '约束单次等待，整次上传可能更长'],
    ['本地持久化与空库处理', '保留向量，空库直接返回提示', '重启可读，无资料时不请求对话模型'],
  ], [340, 500, 600], 225, [66, 86, 86, 96, 96, 96], 26);
  text(s, '重排序、混合检索和系统化问答评测属于后续计划。', 80, 784, 1440, 46, 26, C.muted);
  note(s, '这些策略已经体现在代码和回归中，但现有参数没有通过标准问答集证明最优。内容哈希只处理完全相同的片段。四十五秒约束的是一次外部请求，多批导入及重试可能让整次上传超过四十五秒。后续需要结合召回率、忠实性、正确拒答率和耗时比较方案。', ['docs/评审技术文档.md', 'backend/rag/vector_store.py', 'backend/rag/embedding.py', 'backend/rag/llm.py']);

  s = page(p, '测试验证与结果', '记录日期：2026-10-22，自动化回归与真实 AI 联调分别取证');
  table(s, [
    ['验证项', '记录结果', '证据范围'],
    ['后端常规回归', '34 通过，4 项专项默认跳过', '共发现 38 项用例'],
    ['MySQL 专项', '4 / 4 通过', '同一批专项另行启用，不重复计数'],
    ['前端单元测试', '6 / 6 通过', '输入与交互逻辑'],
    ['桌面与移动浏览器', '16 / 16 通过', '8 个场景分别在 2 种视口执行'],
    ['真实 AI 与 RAG', '向量化、问答与来源核对通过', '向量维度 1024，真实配置客户端'],
  ], [350, 510, 580], 225, [66, 94, 94, 94, 94, 104], 27);
  text(s, '前端生产构建、格式检查及运行中 Docker 验证也已通过。', 80, 789, 1440, 42, 26, C.teal, true);
  note(s, '所有数字均取自本项目二〇二六年十月二十二日的测试报告。后端常规运行发现三十八项，其中四项 MySQL 专项默认跳过，另行启用后四项通过，不能重复计数。浏览器自动化使用模型替身检查流程，真实外部 AI 另行联调。未开展临床准确率、长期压测或公网渗透测试，前端构建包体积提示仍是已知问题。', ['docs/验收测试报告.md', 'output/video/demo-evidence.json']);

  s = page(p, '部署方案与交付材料', 'Docker Compose 组织应用和 MySQL，运行数据使用独立持久化卷');
  text(s, 'docker compose up -d --build --wait', 80, 231, 1440, 66, 39, C.teal, true);
  table(s, [
    ['部署对象', '配置与数据保存'],
    ['应用服务', 'Waitress 提供页面与 API，主机默认访问 localhost:8080'],
    ['MySQL 8.0', '业务数据保存至 mysql_data 卷'],
    ['知识库与签名密钥', '分别保存至 chroma_data、instance_data 卷'],
  ], [350, 1090], 347, [66, 90, 90, 90], 27);
  text(s, '交付：GitHub 源码、环境模板、依赖清单、15 页技术 PDF、7 分 29 秒演示视频。', 80, 741, 1440, 82, 29, C.ink, true);
  note(s, 'README 提供容器和本机两种启动方式，环境模板分别配置数据库、向量服务和对话服务。业务数据、知识库和 JWT 签名密钥使用独立卷。当前交付包括十五页技术 PDF 和约七分二十九秒的一〇八〇 p 演示视频。团队决定不做公网演示加分项，因此本次没有公网服务可用性承诺。若要部署，需准备实际 AI 服务配置。', ['README.md', 'compose.yaml', 'docs/交付检查清单.md', 'output/video/video-metadata.json']);

  s = page(p, '技术改进与应用创新', '创新定位：项目层面的工程整合与业务流程改进', true);
  group(s, '工程改进', '内容哈希去重，减少重复知识片段\n新增片段全部向量化后再写入\n回传来源，支持资料核对\n事务、行锁与外键保护业务关联', 80, 271, 670, {dark: true, height: 280, size: 31});
  group(s, '应用整合', '患者档案、电子病历与知识问答\n在统一页面中完成\n\n合成资料演示、真实 AI 调用\n与可复现运行材料相互对照', 850, 271, 670, {dark: true, height: 300, size: 31});
  text(s, '成果依据是功能可操作、约束可验证和交付可复现。', 80, 739, 1440, 65, 35, C.mint, true);
  note(s, '技术层面的改进集中在重复知识治理、外部调用失败处理、来源返回和数据一致性。应用层面将管理业务与知识问答放到统一入口。这里的创新是本项目组合方案中的工程与应用改进，没有发明 RAG 算法，也未通过与外部产品比较证明行业领先。', ['docs/评审技术文档.md']);

  s = page(p, '团队分工', '高秋雨负责总体设计与项目统筹，前端开发和测试分工协作');
  table(s, [
    ['成员', '承担角色', '主要工作'],
    ['高秋雨', '项目负责人', '需求与架构、后端核心模块、数据库、部署、版本管理、论文与核心技术文档、进度统筹'],
    ['郝崇泽', '前端开发', '页面开发、组件封装、页面样式、前后端接口联调'],
    ['栾子璇', '测试与辅助文档', '功能测试、Bug 记录与回归测试、用户手册辅助编写、素材整理'],
  ], [220, 300, 920], 249, [66, 160, 125, 125], 29);
  text(s, 'GitHub：gaoqiuyu9579 / RAG-medical-system', 80, 774, 1440, 48, 28, C.teal, true);
  note(s, '团队成员为高秋雨、郝崇泽和栾子璇。高秋雨统筹项目，负责需求、架构、后端、数据库、部署、版本管理及核心文档；郝崇泽负责前端与联调；栾子璇负责测试、回归和辅助材料。仓库保留本次真实提交，早期没有留存的历史不能补作真实开发证据。', ['README.md', 'docs/GitHub提交说明.md', 'https://github.com/gaoqiuyu9579/RAG-medical-system']);

  s = page(p, '当前成果与后续规划', '已完成核心业务与知识问答原型，下一步补齐治理和质量评价');
  group(s, '第一阶段  完善业务与权限', '补充编辑与分页，细化病历访问授权、操作审计和登录限流。', 80, 232, 1440, {height: 80, size: 30});
  group(s, '第二阶段  建立问答质量评测', '由专业人员审核问题、参考答案与来源，评估召回、忠实性和拒答行为。', 80, 423, 1440, {height: 90, size: 30});
  group(s, '第三阶段  评估检索与交互扩展', '在评测基础上比较 OCR、混合检索、重排序和受控会话历史。', 80, 626, 1440, {height: 80, size: 30});
  text(s, '汇报结束，欢迎交流', 80, 788, 1440, 50, 34, C.teal, true);
  note(s, '项目目前已经贯通登录、患者登记、病历关联、资料导入与 RAG 问答。下一步先完善业务功能与权限，再建立有专业审核的评测集，最后依据评测结果比较更复杂的检索和交互方案。现阶段仍需要人工审核回答，不能把功能演示等同于临床效果验证。感谢各位。', ['docs/评审技术文档.md']);

  return {slides: p.slides.items.length, font: FONT, nativeTableSlides: [3, 5, 10, 13, 14, 15, 17]};
}
