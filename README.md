# oral-video-agent

中文口播视频制作 Skill：先审核文案、分镜、人物与声音参考、语速、画幅和画质；确认后按需生成配音和数字人，再用 Remotion 制作可编辑的成片。可选接入独立安装的 `video-talkcraft` 设计动效，见 [动效协作说明](skills/oral-video-agent/references/video-talkcraft.md)。

完整说明：[oral-video-agent README](skills/oral-video-agent/README.md) · [Skill 入口](skills/oral-video-agent/SKILL.md) · [审核单模板](skills/oral-video-agent/assets/review-template.md)

## 安装

```text
npx skills add madeinice/oral-video-agent --skill oral-video-agent -g
```

也可以下载本仓库，直接让 Agent 读取 `skills/oral-video-agent/SKILL.md`。需要 Node.js 22+、FFmpeg、Remotion 4.0.519、Python 3.10+；实际配音和人物生成需自己的 RunningHub 工作流与账号。项目素材、模型和运行记录保存在仓库之外，密钥由环境变量读取。

仓库中的代码和文档使用 [MIT License](skills/oral-video-agent/LICENSE)；第三方模型、素材和服务遵循其各自许可。
