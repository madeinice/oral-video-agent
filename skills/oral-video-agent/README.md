# oral-video-agent · 中文口播视频工作流

让具备文件、浏览器和终端工具的 AI Agent 根据文案制作口播视频，并交付可继续编辑的 Remotion 工程。

**默认路线：文案与制作参数审核确认 → RunningHub / IndexTTS2 配音 → 时间对齐 → InfiniteTalk 按需生成口播 → B-roll 与动效 → Remotion。**

它是给 Agent 的操作规范、实用脚本和工程模板，不是独立运行的一键桌面软件。不会安装模型、读取个人素材或自动开始收费生成。

## 能做什么

- 收到新文案后先给出完整审核稿：五列分镜表、人物与声音参考、语速、画幅和画质；确认该版本后才开始生成。
- 从逐字稿形成按句分镜，按具体口播词定位文字、头像、步骤线、画面让位和素材。
- 只为人物需要出镜的时间段安排数字人生成。
- 保存云端任务 ID，重启后恢复，阻止不确定提交后的重复扣费。
- 提供分层的 Remotion 工程、中文字幕、少量音效与 MP4。
- 修改后期时复用已有配音和人物视频。
- Windows Studio 启动/停止脚本，避免服务已关闭却交付一个打不开的网址。

## 目录

| 路径 | 内容 |
| --- | --- |
| [SKILL.md](SKILL.md) | Agent 的入口指令 |
| [references](references) | 接口、剪辑、命令、排障、发布说明 |
| [scripts](scripts) | 项目初始化/时间处理、RunningHub 任务工具、Studio 启动器 |
| [assets/remotion-template](assets/remotion-template) | 可编译的图层模板与不含私人素材的演示 |
| [assets/examples](assets/examples) | 配置与来源登记示例 |

## 最短使用方法

让 Agent 阅读本文件夹中的 `SKILL.md`，然后发：

> 使用 oral-video-agent。文案是……。人物照片和声音样本在我指定的文件夹。先给我逐句画面安排，画幅 9:16，1080p，发声约每秒 5 个字，暖调、中文字幕、有少量动效音效、无背景音乐。素材出现位置按口播词对齐。确认后开始生成，最后保留可编辑工程。

Skill 会先在对话中完整展示 [生成前审核单](assets/review-template.md)：

1. 文案脚本：**口播位置、画面安排、动效、音效、是否需要人物**，逐句覆盖全文。
2. 人物和声音参考：具体文件名与路径、照片或视频、保留的背景，以及声音样本/成品配音。
3. 语速：实际发声每秒汉字数、停顿规则与预计时长。
4. 画幅和画质：横竖屏、比例、导出像素尺寸、帧率、原生生成分辨率与超分计划。

你确认本版方案后，Agent 才生成配音和视频。修改审核稿时会整合为新版供确认；已确认版本的恢复执行不重复询问。审核稿与确认记录保存在当前视频项目中。

已经确认本版审核稿时直接说“按已确认脚本开始生成”。已有视频只改后期时说：

> 只把“记录数据”这句的画面改成竖向步骤线，复用现有声音和人物视频。

如果已经单独安装且有权使用 `video-talkcraft`，可说：

> 使用 oral-video-agent 制作这条片；动效剪辑启用 video-talkcraft。配音、人物和已确认脚本沿用本项目，按口播词选动效配方，保留分层 Remotion 工程。

Agent 会在审核稿里写清画面动作，音频锁定后用词级时间戳定位，再按 [动效协作说明](references/video-talkcraft.md) 选配方并落到本工程。`video-talkcraft` 是可选的外部 Skill，不随本仓库安装；它的[许可证](https://github.com/Vincentwei1021/video-talkcraft/blob/main/LICENSE)对商业使用要求事先取得作者授权。

## 安装

本地：把整个文件夹放入所用 Agent 支持的 skills 目录，或让 Agent 按绝对路径读取 `SKILL.md`。不同宿主的技能目录不同，不需要把代码、模型或素材重复复制到系统盘。

从 GitHub 安装本 Skill：

```text
npx skills add madeinice/oral-video-agent --skill oral-video-agent -g
```

此命令只安装本 Skill，不会安装 `video-talkcraft`。详见 [发布说明](references/publishing.md)。

## 依赖

- Python 3.10+；项目/锚点脚本仅用标准库，RunningHub 工具另需 `requests`。
- Node.js 22+、FFmpeg/ffprobe、Chrome 或 Remotion 支持的浏览器。
- Remotion 模板固定在 **4.0.519**；同组包保持同版。使用已装共享依赖可减少磁盘占用。
- RunningHub 账户、可用应用、环境变量 `RUNNINGHUB_API_KEY`；密钥由 Python `os.getenv` 读取。
- 可用的 ASR/对齐工具：例如 SenseVoice、Whisper 或 FireRed，按现有环境选择，不强制全部安装。

模板示例不需要 API 密钥即可初始化、编译和预览。生成真人口播需要另外提供自己的素材和可用工作流。当前提供的是 RunningHub 的 AI 应用提交适配器；其他供应商不是内置替代接口。

## 编辑能力

`timeline.json` 可调整素材路径、时间、文字、位置和音量，然后生成显式 Remotion 图层。Studio 中可修改受支持的文字/变换；复杂动画仍在源码中编辑。不要把它理解成剪映完整拖拽编辑器。Studio 直接修改源码后，应保留修改并合并回时间表，再决定是否重新生成。

模板内置文字进入、圆形头像、竖向步骤线、人物缩位、素材切换与分层字幕/音效。人物身后字需要额外制作逐帧遮罩；模板支持带透明通道的前景视频，但不自带人像分割模型。

## 隐私、费用与许可

本仓库不包含任何人的声音、脸、成片、工作流执行记录和密钥。不要把实际项目放进本仓库。云端生成上传哪些素材、预计生成多少秒，应在提交前由 Agent 按用户已授权范围说明。

本仓库原创代码和文档采用 [MIT License](LICENSE)。Remotion、IndexTTS2、InfiniteTalk、第三方应用以及外部素材各有独立许可/服务条款，使用本 Skill 不转授它们的权利。

官方参考：[Remotion Studio](https://www.remotion.dev/docs/studio/interactivity)、[RunningHub 查询接口](https://www.runninghub.cn/runninghub-api-doc-en/api-425767807)。接口和应用节点会变化；具体可用性以所选应用的 API 页为准。
