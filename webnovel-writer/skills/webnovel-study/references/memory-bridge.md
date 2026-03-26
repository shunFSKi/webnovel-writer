---
name: memory-bridge
purpose: 说明 /webnovel-study 如何将高分模式桥接到 project_memory.json，同时兼容现有 schema
---

# Memory Bridge

## 1. 目标

`webnovel-study` 产出的模式更完整，但 `project_memory.json` 当前 schema 很轻。
因此写回 memory 时必须做降维映射，保证兼容已有读取逻辑。

## 2. 来源与执行入口

来源文件：
- `参考拆书/{book_safe}/06_可复用模式.json`

目标文件：
- `.webnovel/project_memory.json`

执行入口：
```bash
python "${SCRIPTS_DIR}/webnovel.py" --project-root "$PROJECT_ROOT" study bridge-memory \
  --book-safe "{book_safe}" --limit 10
```

规则：
- 由 CLI `study bridge-memory` 统一执行
- Skill 不手工直接改 `.webnovel/project_memory.json`

## 3. 允许写回的条件

只有以下情况才写回：
- 用户显式传 `--write-memory`
- 或用户明确要求“记进项目 memory”

## 4. 映射规则

### study pattern -> project_memory pattern

源：
```json
{
  "pattern_type": "hook",
  "name": "事故兑现开篇",
  "description": "标题承诺在第一章末落地",
  "evidence_range": "第1-3章",
  "transfer_rule": "适合事故型男频开篇",
  "risk": "后续反馈跟不上会掉速",
  "adaptation_note": "迁移到治河文时改成堤身黑浆异象",
  "prompt_instruction": "开篇第一章必须让主角直接接触核心冲突，而不是只做旁观者。事故要落地、要具体、要让主角当场接任务。",
  "score": 9,
  "learnability": "可直接学"
}
```

写回 memory：
```json
{
  "pattern_type": "hook",
  "description": "事故兑现开篇；标题承诺在第一章末落地；适合事故型男频开篇；迁移到治河文时改成堤身黑浆异象；提示词指令：开篇第一章必须让主角直接接触核心冲突，而不是只做旁观者。事故要落地、要具体、要让主角当场接任务。",
  "source_chapter": 0,
  "learned_at": "2026-03-19T00:00:00Z"
}
```

说明：
- `description` 由 `name + description + transfer_rule + adaptation_note + prompt_instruction` 拼接降维而成
- `prompt_instruction` 是新增核心字段，确保可复用技巧能落地到提示词层面
- `risk` 不直接写入 memory，但会体现在筛选环节

## 5. source_chapter 规则

- 若 `evidence_range` 可明确到单章，填该章号
- 若为多章区间、卷级模式或不明确，填 `0`

## 6. 去重规则

以下任一满足视为重复：
- `pattern_type` 相同且 `description` 完全一致
- `pattern_type` 相同且 `description` 只存在轻微标点差异

## 7. 选择策略

建议只写入：
- `score >= 8`
- `learnability != 不建议学`
- 每次最多 5-10 条

CLI 默认：
- `--min-score 8`
- `--limit 10`

## 8. 不要写入的内容

- 只适用于原书设定的专属桥段
- 明显依赖原书角色关系的细部表达
- 含长摘录的描述
- 低分或风险明显高于收益的模式

## 9. 成功校验

执行 `study verify --write-memory` 时，应至少确认：
- `.webnovel/project_memory.json` 存在
- `patterns` 列表可读
- `study_meta.json.memory_bridge_status = success`
