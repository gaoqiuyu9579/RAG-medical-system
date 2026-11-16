import fs from 'node:fs/promises';

const additions = [
  ['讲解补充（按需融入原讲稿）',
   '项目包含业务管理和知识问答两部分：前者保存患者及病历记录，后者帮助用户查找上传资料中的信息。开场先让老师了解这两部分各自解决什么问题。',
   '衔接句：接下来先介绍项目需求，以及我们已经完成的核心功能。'],
  ['讲解补充（按需融入原讲稿）',
   '例如，同一位患者可以关联多条病历。系统在删除患者前检查关联记录，避免病历失去所属患者。知识问答则帮助用户从已有资料中查找信息，并回到来源核对。',
   '衔接句：为实现这些功能，我们采用了下面的系统架构。'],
  ['讲解补充（按需融入原讲稿）',
   '讲图时从左往右说明：浏览器发起请求，Flask 完成身份校验和业务处理，再访问右侧的数据存储或 AI 接口。MySQL 保存结构化业务记录，Chroma 保存供检索使用的知识片段和向量。',
   '衔接句：下面重点介绍知识问答部分，也就是 RAG 的处理过程。'],
  ['讲解补充（按需融入原讲稿）',
   'RAG 的中文名称是检索增强生成，可以理解为先查资料，再结合查到的内容回答。向量化把文本转换为便于比较的数字表示。返回来源文件名，方便用户回到原资料核对。',
   '衔接句：下面进入实际系统，演示这些设计如何体现在操作中。'],
  ['演示时可用的讲解短句',
   '查看患者与病历：这里可以看到患者和对应病历的关联关系。尝试删除后，系统提示存在关联病历，并保留原有记录。\n导入资料：现在导入合成的随访登记资料，生成知识片段供后续检索。\n查看问答：问题提交后，系统返回登记时间和所需材料，下方显示参与检索的来源文件名。\n查看资料不足的回答：这个追问涉及资料里没有的药物剂量，本次调用明确说明无法据此给出答案。',
   '衔接句：以上是核心流程的演示，接下来介绍测试结果和后续计划。'],
  ['讲解补充（按需融入原讲稿）',
   '这些测试结果对应功能流程、数据约束和接口调用的检查。项目已经具备可运行的原型，下一步重点完善权限与审计，并用经过专业审核的问题集评估问答质量。',
   '收尾句：我的汇报到此结束，感谢各位老师，欢迎批评指正。']
];

export async function addNotes(p) {
  if(p.slides.items.length!==6) throw new Error('Expected six slides');
  p.slides.items.forEach((s,i)=>{
    const old=s.speakerNotes.text;
    if(old.includes(additions[i][0])) throw new Error('Notes already added');
    const marker='\n\n讲稿：\n';
    if(!old.includes(marker)) throw new Error('Missing speech notes on slide '+(i+1));
    const [heading,body,transition]=additions[i];
    s.speakerNotes.text=old.replace(marker,`\n\n${heading}：\n${body}\n\n${transition}${marker}`);
    s.speakerNotes.setVisible(true);
  });
  const dir='D:/Thesis/thesis medical/tmp/report-notes';
  await fs.mkdir(dir,{recursive:true});
  await fs.writeFile(dir+'/final-proto.json',JSON.stringify(p.toProto()));
  return {slides:6,updatedNotes:6};
}
