---
name: integration-notes
purpose: 说明 /webnovel-study 与现有 /webnovel-learn、/webnovel-plan、/webnovel-write 的联动边界
---

# Integration Notes

## 1. 与 /webnovel-learn 的关系

- `webnovel-study`：从样书提炼模式
- `webnovel-learn`：把确认有效的模式写进当前项目 memory

推荐流程：
1. `/webnovel-study` 产出 `06_可复用模式.json`
2. 用户勾选或明确同意
3. 再把高分模式写进 `.webnovel/project_memory.json`

## 2. 与 /webnovel-plan 的关系

`webnovel-study` 的结果可以给 `/webnovel-plan` 提供：
- 开篇抓读模板（开篇钩子分析）
- 卷级承诺与反转节奏
- 爽点循环模式（压制→释放→反馈）
- 章末留钩模式
- 反派压力升级方式

但不能直接替代本项目总纲。

## 3. 与 /webnovel-write 的关系

`webnovel-study` 可以为 `/webnovel-write` 提供：
- 对白推进方式（对话差异分析）
- 微兑现节奏（爽点结构分析）
- 技术/情绪/官场场景的推进信号
- 情绪设计模式（情境制造 vs 直接描写）
- 可直接用于提示词的指令（`prompt_instruction` 字段）

但不能输出”照这个风格仿写”。

## 4. 推荐用户心智

- `study`：学打法
- `learn`：记打法
- `plan`：把打法放进你的卷纲
- `write`：真正把打法落进章节
