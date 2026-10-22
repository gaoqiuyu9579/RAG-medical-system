# GitHub 提交与评审访问

更新日期：2026-10-22。

## 仓库命名与公开访问

GitHub 账号为 `gaoqiuyu9579`。用户提供的中文名称“RAG医疗系统”保留为项目标题；GitHub 仓库名采用兼容平台命名规则的 `RAG-medical-system`。

目标地址为 `https://github.com/gaoqiuyu9579/RAG-medical-system`。地址须以实际创建和匿名访问验证为准，不能仅凭文档中的目标地址认定仓库已公开。

仓库应设为 Public。若后续改为 Private，须在 Settings → Collaborators 邀请评审，并确认其已接受邀请。不要在 Public 仓库提交实际 `.env`、个人访问令牌、业务数据库或备份。

## 真实开发历史

本次检查时，本地 Git 仓库为空，没有可恢复的历史提交或远程地址。2026-10-22 创建首个提交，保留当时已有代码、测试与文档；后续提交对应本次实际进行的规范整理、交付文档及演示制作。

这些记录真实反映本次整理过程，不能证明首次提交之前的完整开发过程。不倒填提交日期，不人为拆分现有代码伪造早期开发。若原开发曾在其他目录、设备或仓库使用 Git，应保留并迁移原 `.git` 或原远程历史，而不是覆盖已有历史。

查看记录：

```powershell
git log --oneline --graph --all --date-order
git log --format=fuller
```

## 推送与材料交付

仓库创建后，用 GitHub 登录凭据推送本地分支；不要向命令行、聊天或文档粘贴真实令牌。新建仓库时不要勾选初始化 README，以免产生无关历史。已有远程提交时先检查远程历史，不使用强制推送覆盖。

```powershell
git remote -v
git push -u origin HEAD
```

本项目将 PDF、MP4 与字幕随代码提交，保留源文档、演示脚本及复现方法。若视频后续超过 GitHub 单文件限制，应放入 Release 附件并更新 README 的下载链接。本次生成脚本会检查文件大小。

提交后使用未登录浏览器检查仓库首页、README 内链接、技术 PDF、视频下载与提交历史，并查看 Actions 结果。公网在线演示本次不提供。
