# RunningHub 适配与恢复

工具：`scripts/runninghub.py`。仅适配 AI 应用 `/task/openapi/ai-app/run` 与 V2 上传/查询；其他通用模型直连接口需另写适配。

## 配置

从所选应用的 API 页面复制应用 ID、nodeId、fieldName 和实例规格到任务目录的请求 JSON，禁止复制带密钥的 curl。

请求文件形状：

```json
{
  "webappId": "1965612801706348546",
  "instanceType": "default",
  "nodeInfoList": [
    {"nodeId": "2", "fieldName": "audio", "fieldValue": "平台上传返回的文件名"},
    {"nodeId": "4", "fieldName": "value", "fieldValue": "这是一段配音示例。"}
  ]
}
```

该例只说明历史 IndexTTS2 应用的节点结构；上传返回值须替换成真实结果，应用可用性和节点必须以当前 API 页核实。

曾成功使用的候选（2026-10-14，本机既有项目证据；不代表永久可用或官方推荐）：

| 用途 | 应用 ID | 历史节点 |
| --- | --- | --- |
| IndexTTS2 | 1965612801706348546 | 2/audio 声音样本，4/value 文案 |
| InfiniteTalk | 2006270540499128322 | 284/image，125/audio，312/value 长边，314/prompt，369/value=0，370/value=1 |
| SeedVR2 | 2079805313208905730 | 16/video，71/value 输出尺度 |

InfiniteTalk 该历史配置曾在较小实例显存不足，plus 实例成功。不要把这个结果推广到所有应用；规格、价格、输入长度和模型版本需当前核实。用户有预算上限时先核算；不要直接把 RH 币写成人民币。

## 接口依据

- [官方上传接口](https://www.runninghub.cn/runninghub-api-doc-en/api-425761098)：multipart 文件上传。官方页面存在 `filename`/`fileName` 及成功码 200/0 的不同样例，工具兼容这两种成功返回，缺文件标识则停止。
- [官方查询接口](https://www.runninghub.cn/runninghub-api-doc-en/api-425767807)：任务 ID 查询，成功结果包含状态和结果 URL。
- [官方 AI 应用接入例](https://www.runninghub.ai/runninghub-api-doc-en/doc-8287470)：应用提交结构。历史项目使用该提交路由；每次接入新应用仍核对其自身 API 页。

密钥通过 `os.getenv("RUNNINGHUB_API_KEY")` 获取。进程读不到新设置的环境变量时，重开终端/宿主；仅报告是否存在，禁止输出值。API 服务地址只允许 RunningHub 官方中国/国际域名，防止配置错误将密钥发到别处。

## 命令顺序

```text
python scripts/runninghub.py --jobs TASK/work/jobs upload --file TASK/inputs/voice.m4a --out TASK/work/voice-upload.json
python scripts/runninghub.py --jobs TASK/work/jobs submit --tag voice-01 --request TASK/work/tts-request.json
python scripts/runninghub.py --jobs TASK/work/jobs submit --tag voice-01 --request TASK/work/tts-request.json --execute
python scripts/runninghub.py --jobs TASK/work/jobs poll --tag voice-01
python scripts/runninghub.py --jobs TASK/work/jobs download --tag voice-01 --out TASK/work/downloads
```

第二条只检查并显示应用/节点数量；第三条才发出收费请求。执行上传与收费生成前，先按 SKILL.md 展示完整审核稿并取得用户对本版的确认；在任务 work/approval.json 保存确认依据。`TASK` 表示实际任务目录。每次 poll 只查一次，Agent 在合理间隔后再查，避免循环阻塞交流。

### 不确定提交

提交前使用独占 pending 文件防止并发重复调用。请求成功时立即保存 taskId。网络超时、HTTP 错误或业务错误均保守保留 pending；工具不会猜测是否扣费。

1. 查询平台历史任务与实际请求时间。
2. 找到任务：`reconcile --tag voice-01 --task-id 平台任务ID`，然后继续 poll。
3. 平台明确确认没有创建任务：`reconcile --tag voice-01 --confirmed-not-created --note "核实依据"`，保留审计记录后才允许再次提交。没有明确证据不得使用此开关。

同 tag 不同请求会被拒绝。上传内容或文案变化时必须使用新请求/新 tag。任务失败后先读错误，明确失败原因和是否需新费用，再决定新 tag；不要删除原记录。

下载结果使用独立无认证会话，结果签名 URL 只保存在本地状态中。任务记录、voice-upload.json、请求 JSON 和结果文件永远不提交到公开仓库。
