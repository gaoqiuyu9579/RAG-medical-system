import fs from 'node:fs/promises';

const ROOT = 'D:/Thesis/thesis medical';
const FONT = 'Microsoft YaHei';
const C = {navy:'#102A40',teal:'#087F8C',ink:'#17354D',muted:'#567083',bg:'#F4F8FA',white:'#FFFFFF',rule:'#D5E2E9'};

function text(s, value, x, y, w, h, size=30, color=C.ink, bold=false) {
  const sh=s.shapes.add({geometry:'textbox',name:value.slice(0,32),position:{left:x,top:y,width:w,height:h},fill:'none',line:{fill:'none',width:0}});
  sh.text=value;
  sh.text.style={typeface:FONT,fontSize:size,color,bold,insets:0,alignment:'left',verticalAlignment:'top'};
  return sh;
}
function change(s,oldValue,newValue) {
  const sh=s.shapes.items.find(x=>String(x.text)===oldValue);
  if(!sh) throw new Error('Missing text: '+oldValue);
  sh.text=newValue;
  return sh;
}
function note(s,time,speech,sources,extra='') {
  s.speakerNotes.text=`时间安排：${time}\n\n讲稿：\n${speech}${extra?'\n\n'+extra:''}\n\n资料依据：\n${sources.map(x=>ROOT+'/'+x).join('\n')}`;
  s.speakerNotes.setVisible(true);
}
function group(s,head,body,x,y,w,h=120) {
  text(s,head,x,y,w,53,34,C.teal,true);
  text(s,body,x,y+62,w,h,29);
}

export async function shorten(p) {
  if(p.slides.items.length!==18) throw new Error('Expected original 18-slide report');
  p.slides.keep([0,1,3,10,17]);
  let [cover,needs,architecture,rag,demo]=p.slides.items;

  note(cover,'第 1 页 20 秒，全程 0:00 至 0:20',
    '各位老师好，我们汇报的项目是 RAG 医疗系统，也就是智慧医疗问诊平台。项目将患者档案、电子病历和知识库辅助问答整合到同一网页，下面先介绍设计与实现，再演示核心功能。',
    ['README.md','docs/评审技术文档.md'],
    '全程预算：PPT 讲解 4 分 30 秒，项目演示 3 分钟，页面切换及等待缓冲 30 秒。\n时间节点：第 2 页结束 1:05，第 3 页结束 1:55，第 4 页结束 3:10，3:20 开始演示，6:20 返回第 6 页，7:30 完成收尾。');

  change(needs,'项目背景与建设目标','项目需求与核心功能');
  change(needs,'围绕档案、病历和知识资料分散的问题，建立统一的业务入口','将患者档案、电子病历与资料问答集中在同一网页');
  change(needs,'现有问题','实际需求');
  change(needs,'患者信息与病历缺少统一关联\n知识资料需要人工查找和反复核对\n功能演示与运行配置难以复现','患者与病历需要统一关联\n知识资料需要快速查找并核对');
  change(needs,'项目目标','已完成功能');
  change(needs,'统一登记患者与录入病历\n基于上传资料回答，并返回来源\n用环境模板、容器与测试支持复现','患者登记与电子病历管理\n资料导入、RAG 问答与来源展示');
  const highlight=change(needs,'项目定位：可运行的教学原型，支持资料辅助问答。','关联病历删除保护，重复资料导入去重');
  highlight.position={left:80,top:610,width:1440,height:65};
  const boundary=change(needs,'问答模块不查询患者和病历表生成个体诊断。','项目定位：教学原型，问答用于资料辅助，不替代医生诊断');
  boundary.position={left:80,top:728,width:1440,height:55};
  note(needs,'第 2 页 45 秒，全程 0:20 至 1:05',
    '项目围绕两类需求展开：第一，患者档案与病历需要统一关联；第二，上传的知识资料需要便于检索和核对。系统已经实现登录、患者登记、病历录入，以及资料导入和单轮问答。业务部分对已有关联病历的患者提供删除保护，知识库通过内容哈希减少重复导入。问答只检索上传资料，不读取患者表生成个体诊断。项目目前定位为教学原型。具体页面操作放在后面的演示中展示。',
    ['README.md','docs/评审技术文档.md']);

  note(architecture,'第 3 页 50 秒，全程 1:05 至 1:55',
    '系统采用前后端分离架构。前端使用 Vue 3 和 Element Plus，后端使用 Flask，按接口、业务服务与数据模型组织代码。右侧分成两类存储：MySQL 保存用户、患者和病历，Chroma 保存知识片段、向量与资料来源。资料问答时，后端分别调用向量接口和对话接口。这样业务数据与知识检索能够独立维护。部署时由 Waitress 提供网页和 API，Docker Compose 组织应用与 MySQL，并持久化业务数据和知识库。',
    ['docs/评审技术文档.md','docs/assets/architecture.png','compose.yaml']);

  change(rag,'RAG 问答与资料来源','RAG 问答与工程改进');
  change(rag,'先检索项目资料，再把参考上下文与用户问题提交给对话模型','先检索上传资料，再生成带来源的回答');
  change(rag,'检索','检索与生成');
  const pipeline=change(rag,'问题向量化，最多取 3 个片段。','资料分块并向量化，存入 Chroma\n问题检索 Top-3 片段后提交对话模型');
  pipeline.position={left:80,top:291,width:700,height:100};
  change(rag,'生成','已实现的优化');
  const optimization=change(rag,'组合参考上下文，返回回答与 sources。','内容哈希去重，完成向量化后写入\n空库直接提示，来源文件随答案返回');
  optimization.position={left:840,top:291,width:680,height:100};
  change(rag,'演示问题：随访登记窗口何时开放，需要准备哪些材料？','真实调用案例：随访登记时间与所需材料');
  change(rag,'答案依据','模型配置');
  change(rag,'demo_knowledge.md\n\n文件名便于回查\n原始资料。','text-embedding-v3\ndeepseek-chat');
  change(rag,'来源为参与检索的文件名，可用于回查资料。','资料不足时要求说明不足，当前仍需人工核对');
  note(rag,'第 4 页 75 秒，全程 1:55 至 3:10',
    'RAG 是本项目的技术重点。导入资料后，系统按五百字符分块，保留五十字符重叠，再调用向量模型，存入本地 Chroma。用户提问时，系统先检索最多三个相关片段，把资料与问题一起提交给对话模型，并返回回答和来源文件名。当前向量模型配置为 text-embedding-v3，对话模型配置为 deepseek-chat。工程改进主要针对两个问题：重复资料用内容哈希去重，新增片段先全部完成向量化再写入，减少外部调用中断造成的半份导入。空知识库会直接提示。图中是真实调用返回的登记信息及来源。系统要求资料不足时说明不足，但一次演示不能代表全面可靠，回答仍需人工核对。',
    ['backend/rag/vector_store.py','backend/rag/embedding.py','backend/rag/llm.py','docs/评审技术文档.md','output/video/demo-evidence.json']);

  change(demo,'当前成果与后续规划','项目演示');
  change(demo,'已完成核心业务与知识问答原型，下一步补齐治理和质量评价','患者与病历关联、资料导入及知识问答');
  change(demo,'第一阶段  完善业务与权限','患者与病历管理');
  change(demo,'补充编辑与分页，细化病历访问授权、操作审计和登录限流。','查看患者与关联病历，验证关联删除保护');
  change(demo,'第二阶段  建立问答质量评测','知识资料导入');
  change(demo,'由专业人员审核问题、参考答案与来源，评估召回、忠实性和拒答行为。','导入合成随访登记资料，查看知识片段');
  change(demo,'第三阶段  评估检索与交互扩展','问答与来源核对');
  change(demo,'在评测基础上比较 OCR、混合检索、重排序和受控会话历史。','查询登记时间与材料，再追问资料外的问题');
  change(demo,'汇报结束，欢迎交流','演示使用合成患者与合成资料');
  note(demo,'第 5 页引导 10 秒，全程 3:10 至 3:20；随后项目演示 3 分钟，全程 3:20 至 6:20',
    '下面切换到系统，依次展示患者与病历关联、资料导入，以及带来源的问答和资料不足时的回答。',
    ['docs/评审技术文档.md','output/video/智慧医疗系统演示.srt','output/video/demo-evidence.json'],
    '演示前准备：提前登录，准备好合成患者和关联病历，将 demo_knowledge.md 放到方便选择的位置，使用已验证的本地演示实例。\n\n3 分钟操作路线：\n0:00 至 0:40：查看合成患者与对应病历，尝试删除已关联患者，展示后端拒绝删除。\n0:40 至 1:05：导入 demo_knowledge.md，指出分块结果；重复导入时新增为零。\n1:05 至 2:15：提问“随访登记窗口何时开放，需要准备哪些材料？”，展示答案和来源文件名。\n2:15 至 3:00：追问“请根据资料给出演示患者的药物剂量”，展示资料不足的回答，并返回第 6 页。\n\n控时：页面只说明本次要验证的结果，等待接口时不重复介绍架构。出现持续等待时，用已有真实调用截图说明结果并继续。现有完整视频约 7 分 29 秒，答辩时不播放全片。');

  const last=p.slides.add({layout:'Blank',width:1600,height:900,background:{fill:C.bg}});
  text(last,'测试成果与后续计划',80,60,1440,78,54,C.navy,true);
  text(last,'已完成核心业务与 RAG 原型，支持容器化部署',82,151,1430,58,25,C.muted);
  const values=[
    ['验证项','记录结果'],
    ['后端与数据库','常规 34 项通过\nMySQL 专项另测 4 项通过'],
    ['前端单元测试','6 / 6 通过'],
    ['桌面与移动浏览器','16 / 16 通过\n8 个场景、2 种视口'],
    ['真实 AI 联调','向量化、问答与来源核对通过']
  ];
  const heights=[66,116,88,116,100];
  const t=last.tables.add({rows:5,columns:2,left:80,top:241,width:920,height:486,columnWidths:[330,590],values});
  t.styleOptions={headerRow:true,bandedRows:false};
  t.cells.block({row:0,column:0,rowCount:5,columnCount:2}).assign({fill:C.white,textStyle:{typeface:FONT,fontSize:28,color:C.ink},margins:{left:18,right:18,top:13,bottom:10},anchor:'center'});
  t.borders.assign({fill:C.rule,width:1,style:'solid'});
  for(let r=0;r<5;r++) {t.rows[r].height=heights[r];if(r>0)t.cells.block({row:r,column:0,rowCount:1,columnCount:2}).fill=r%2?C.white:'#EAF2F5';}
  t.cells.block({row:0,column:0,rowCount:1,columnCount:2}).assign({fill:C.navy,textStyle:{typeface:FONT,fontSize:28,color:C.white,bold:true}});
  group(last,'交付成果','源码、环境模板与技术文档\nDocker Compose 部署',1060,251,460,130);
  group(last,'后续工作','细化权限与操作审计\n建立问答质量评测集',1060,501,460,130);
  text(last,'感谢各位，欢迎交流',80,788,1440,50,34,C.teal,true);
  text(last,'06',1460,841,70,30,20,C.muted);
  note(last,'第 6 页 70 秒，全程 6:20 至 7:30；余下 30 秒作为切换与等待缓冲',
    '刚才演示了患者与病历关联，以及从资料导入到问答返回来源的完整流程。验证方面，后端常规回归三十四项通过，四项 MySQL 专项另行启用后通过；前端单元测试六项通过，浏览器测试在桌面和移动两种视口共十六项通过。自动化回归使用可控的模型替身，真实向量化与问答另行联调，不能把测试通过率理解成医疗答案准确率。项目已经交付源码、环境模板、技术文档和容器部署配置。高秋雨负责架构、后端与部署，郝崇泽负责前端与联调，栾子璇负责测试与辅助文档。后续重点是细化权限和审计，并建立专业审核的问答评测集。我的汇报到此结束，谢谢各位老师。',
    ['docs/验收测试报告.md','docs/评审技术文档.md','README.md','output/video/demo-evidence.json']);

  p.slides.items.forEach((s,i)=>{
    const marker=s.shapes.items.find(x=>/^\d{2}$/.test(String(x.text)));
    if(marker) marker.text=String(i+1).padStart(2,'0');
  });
  return {slides:p.slides.items.length,talkSeconds:270,demoSeconds:180,bufferSeconds:30};
}

export async function exportShort(p) {
  const draft=await p.export({format:'pptx',fileName:'智慧医疗系统_8分钟精简版.pptx'});
  const path=ROOT+'/output/presentation/智慧医疗系统_8分钟精简版.pptx';
  await fs.writeFile(path,new Uint8Array(await draft.arrayBuffer()));
  return path;
}
