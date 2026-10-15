# 命令与工程约定

在 Skill 根目录运行下列命令，`TASK` 是仓库之外的实际任务绝对路径，Python 可换成已安装解释器的绝对路径。先确认目标磁盘写入权限。

## 本地初始化

```text
python scripts/project.py init --project TASK
```

输出：

```text
TASK/
  profile.local.json         任务私有默认值，不存密钥
  timeline.json              真实时间与分层参数；初始是无声演示
  sources.json               外部素材来源
  inputs/                    用户原始素材
  work/                      对齐结果、状态、缓存、任务日志；approval.json 记录已确认版本与依据
  outputs/
    review-v001.md           Agent 按审核模板填写；在对话展示并经确认后进入生成
    captions.srt
    editor/                  可交付的 Remotion 源工程
      src/Generated.tsx      显式图层与时间区间
      src/Layers.tsx         动效组件
      src/meta.json          实际尺寸、帧率、时长
      public/                本地媒体
      Studio.ps1
```

初始化不读 API 密钥、不收费、不下载模型。已有任务目录会拒绝覆盖。生产时把 `demo` 改为 false，填写真实时间和媒体。

初始化脚本不自动填写审核稿或伪造确认记录。由 Agent 根据用户文案、实际参考素材与参数填写 review 文件，在对话展示并等待明确确认，再记录 approval.json。新文案尚未确认时，只做这一步及文件/工作流检查。

已有个人配置时添加 `--profile 个人配置文件路径`，会复制到新任务的 profile.local.json；其中可选 runtime 对象会写到编辑工程的 runtime.local.json。个人配置只保存素材/工具路径与偏好，不包含密钥。初始演示保持自身 4 秒布局，真实制作时由 Agent 按配置重建 timeline。

## 对齐、人物计划与编译

```text
python scripts/project.py anchor --words TASK/work/words.json --phrase 数据化 --occurrence 1
python scripts/project.py validate --timeline TASK/timeline.json
python scripts/project.py plan-host --timeline TASK/timeline.json
python scripts/project.py compile --project TASK
```

`plan-host` 只算人物需要的区间，不要求人物已生成。`compile` 检查生产媒体存在、人物覆盖、字幕区间，然后生成源图层与 SRT，不调用云端。

timeline 字段：

- `script` 为已批准全文。`scenes[].text` 拼接后必须覆盖全文。
- `meta` 含 width/height/fps/duration/background/subtitle_size。时间统一用秒，编译时一次转换为帧。
- `scenes` 按时间连续覆盖配音；`needs_host` 为 true/false。
- `layers` 按从底到顶排列。`kind` 可用 video/image/audio/text/portrait/steps；媒体 `src` 是相对于 editor/public 的路径。
- `rect: [left,top,width,height]` 使用输出画布像素；`source_start` 是素材截取起点，秒；video 默认静音，配音单独 audio/role=narration。
- 人物视频 `role: host`；音效用 audio/role=sfx，建议起始 volume=0.08 后试听。人物平滑缩位用 from_rect 指定原始画面矩形、rect 指定最终矩形、move_seconds 指定移动时长（默认 0.32 秒）。
- steps.items 为 `[{text, at}]`，at 是全片绝对秒数，必须来自词语锚点。
- portrait 用圆形图片，side 为 left/right。身后文字上方的前景 video 设置 transparent=true，并使用真实透明素材。
- captions 为 `[{start,end,text}]`，顺序排列，不重叠。

编译器会保护 Studio/源码直接编辑。若检测到变化，先合并到 timeline 或继续直接修改源码；`--overwrite-edits` 只在确认丢弃旧编辑时使用。

## 依赖与 Studio

在 outputs/editor 中安装 package.json 固定版本依赖（不要安装到 Skill 模板内部），或使用经验证相同版本的共享 node_modules。Windows 可创建目录联接；跨机器交付应移除外部依赖联接，并依据 package.json/package-lock.json 重新安装依赖。

安装 npm 依赖前，把 TEMP/TMP、npm 缓存和浏览器缓存指向任务 work 下。若 Chrome 已有安装，复用其路径。复制 [runtime.example.json](../assets/examples/runtime.example.json) 为 editor/runtime.local.json，填写真实 Node/Chrome 路径。

```text
powershell -NoProfile -ExecutionPolicy Bypass -File TASK/outputs/editor/Studio.ps1 -Action Doctor
powershell -NoProfile -ExecutionPolicy Bypass -File TASK/outputs/editor/Studio.ps1 -Action Start
powershell -NoProfile -ExecutionPolicy Bypass -File TASK/outputs/editor/Studio.ps1 -Action Render
powershell -NoProfile -ExecutionPolicy Bypass -File TASK/outputs/editor/Studio.ps1 -Action Stop
```

启动后检查实际打印的网址，后台进程保持运行。该启动器面向 Windows x64，使用进程级参数，不改系统执行策略；受管理设备的策略可能需要管理员正常处理。Linux/macOS 可使用 package.json 中 npm studio/render，并自行指定缓存目录。

渲染后用 ffprobe 检查尺寸、时间、音轨，并完整解码检查。修改字体/位置可先渲染关键帧，不必每次完整渲染。输出 final.mp4 已存在时启动器会拒绝覆盖，使用 -OutputPath 指定新版文件。
