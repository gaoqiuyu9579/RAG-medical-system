import fs from 'node:fs/promises';
import crypto from 'node:crypto';
import { Presentation, PresentationFile } from 'file:///C:/Users/13884/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/@oai/artifact-tool/dist/artifact_tool.mjs';
import { finalizePresentation } from 'file:///E:/Codex/.codex/plugins/cache/openai-primary-runtime/presentations/26.1020.11127/skills/presentations/container_tools/artifact_tool_utils.mjs';

const root='D:/Thesis/thesis medical';
const build=root+'/tmp/report-short';
const skill='E:/Codex/.codex/plugins/cache/openai-primary-runtime/presentations/26.1020.11127/skills/presentations';
const reference=root+'/output/presentation/智慧医疗系统_项目汇报.pptx';
process.env.RUNTIME_NODE_MODULES='C:/Users/13884/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules';
const p=Presentation.load(JSON.parse(await fs.readFile(build+'/final-proto.json','utf8')));
for (const [index,file] of [[2,root+'/docs/assets/architecture.png'],[3,root+'/tmp/project-report/images/answer.png']]) {
  const picture=p.slides.items[index].images.items[0];
  const frame=picture.frame;
  const imageBytes=await fs.readFile(file);
  picture.replace({blob:imageBytes.buffer.slice(imageBytes.byteOffset,imageBytes.byteOffset+imageBytes.byteLength),contentType:'image/png',alt:picture.alt});
  picture.frame=frame;
}
const candidate=build+'/candidate-v2.pptx';
await (await PresentationFile.exportPptx(p)).save(candidate);
const result=await finalizePresentation({
  workspaceDir:root,
  candidatePath:candidate,
  finalPath:root+'/output/presentation/智慧医疗系统_8分钟精简版.pptx',
  pythonExecutable:'C:/Users/13884/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe',
  integrityValidatorPath:skill+'/container_tools/inspect_presentation_package_integrity.py',
  layoutValidatorPath:skill+'/container_tools/inspect_presentation_layout_geometry.py',
  layoutArgs:['--expected-slide-size-emu','15240000,8572500','--validate-bullet-geometry','--validate-heading-fit','--require-native-table-slide','6'],
  requiredNativeTableOwnerSlides:[6],
  fontPolicy:{basis:'reference',families:['Microsoft YaHei'],referencePath:reference,referenceSha256:crypto.createHash('sha256').update(await fs.readFile(reference)).digest('hex')},
  verifyArtifactToolImport:true,
  receiptPath:build+'/validation-v2.json'
});
console.log(JSON.stringify(result));
