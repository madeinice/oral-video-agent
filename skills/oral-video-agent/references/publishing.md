# GitHub 上传与安装

当前目录就是可上传的单 Skill 仓库，`SKILL.md` 位于根目录；运行项目放在仓库之外。用户仅要求“可上传”时，完成本地文件和校验即可，不擅自创建远端仓库或推送。

## 上传前

1. 检查这些明确路径：`README.md`、`SKILL.md`、`LICENSE`、`.gitignore`、`agents/`、`references/`、`scripts/`、`assets/`。
2. 不包含 `.env`、个人配置、脸/声音/视频、任务结果、下载 URL、模型、依赖目录和评测答案。`.gitignore` 不能保护已经暂存的文件，仍需检查暂存列表和 diff。
3. 本地语法、初始化、时间定位、重复提交防护、工程编译和短渲染测试通过；实际云端工作流是否重新验证需单独说明。
4. 在 GitHub 建好你选择公开/私有的空仓库后，可使用 GitHub 网页“上传文件”，上传上述文件及目录。

如用户授权用 Git 推送，先确认 owner/repo、可见性和分支；只暂存明确列出的路径，不使用 `git add .`。GitHub 发布、安装验证和 tag/Release 是分别记录的动作。

## 安装命令

发布后将 `OWNER/REPO` 替换成真实仓库：

```text
npx skills add OWNER/REPO --skill oral-video-agent -g
```

也可以直接把此完整文件夹放入 Agent 识别的 skills 目录，或让 Agent 读取绝对路径的 SKILL.md。只复制 SKILL.md 会丢失脚本和模板。

## 发布后验收

在隔离目录验证从 GitHub 安装，确认发现的技能名、文件内容与源仓库一致，并运行一次不收费的本地演示。仅写出安装命令不算安装成功。模板不包含个人资产，使用者需要自己的素材、API 环境和工作流权限。
