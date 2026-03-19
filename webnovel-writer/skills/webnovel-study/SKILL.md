---
name: webnovel-study
description: 拆解整本样书，先走 CLI 预处理，再输出剧情、人物、文风、节奏与可复用模式，并可对当前项目给出借鉴建议。
allowed-tools: Read Write Edit Grep Bash AskUserQuestion Task
---

# /webnovel-study

## Project Root Guard（必须先确认）

- 默认要求在书项目根执行，因为输出目录与缓存目录都落到当前项目内。
- 若 `WORKSPACE_ROOT/.webnovel/state.json` 存在，直接视为 `PROJECT_ROOT`。
- 若不存在，先通过 `webnovel.py where` 解析。
- 若仍无法解析，只能做独立拆书，不支持 `--compare-current` 与 `--write-memory`。

环境设置（bash 命令执行前）：
```bash
export WORKSPACE_ROOT="${CLAUDE_PROJECT_DIR:-$PWD}"
export PYTHON_BIN="${PYTHON_BIN:-python3}"
export SCRIPTS_DIR="${CLAUDE_PLUGIN_ROOT}/scripts"
export SKILL_ROOT="${CLAUDE_PLUGIN_ROOT}/skills/webnovel-study"

if [ -f "$WORKSPACE_ROOT/.webnovel/state.json" ]; then
  export PROJECT_ROOT="$WORKSPACE_ROOT"
else
  export PROJECT_ROOT="$($PYTHON_BIN "${SCRIPTS_DIR}/webnovel.py" --project-root "$WORKSPACE_ROOT" where 2>/dev/null || true)"
fi
```

## 目标

- 用确定性 CLI 先完成源文件预检、切章、缓存和退化模式判断。
- 再由 Claude 基于结构化缓存完成剧情、人物、风格、节奏与模式分析。
- 保持公共产物契约稳定，并让流程可重跑、可验证、可恢复。

## 输入

```bash
/webnovel-study "/path/to/book.epub"
/webnovel-study "/path/to/book.epub" --mode full --range all --compare-current
/webnovel-study "/path/to/book.txt" --mode pacing --range front10
/webnovel-study "/path/to/book.md" --mode full --write-memory
```

## 支持格式

- 推荐：`txt`、`md`、`epub`
- 条件支持：带文本层的 `pdf`
- 不推荐：扫描版 PDF、严重 OCR 乱码、未转文本的 `doc/docx`

## 模式定义

- `full`：输出 `00-06`，可选 `07`
- `plot`：只做结构、节奏、模式
- `characters`：只做人物、模式
- `style`：只做文笔、词句、模式
- `phrases`：只做词句、模式
- `pacing`：只做开篇抓读、节奏、模式

默认：`--mode full --range all`

## 默认产物

公共输出：
- `参考拆书/{book_safe}/00_总览.md`
- `参考拆书/{book_safe}/01_剧情结构.md`
- `参考拆书/{book_safe}/02_人物特点.md`
- `参考拆书/{book_safe}/03_文笔风格.md`
- `参考拆书/{book_safe}/04_常用词句.md`
- `参考拆书/{book_safe}/05_章节节奏.json`
- `参考拆书/{book_safe}/06_可复用模式.json`
- `参考拆书/{book_safe}/07_对当前项目建议.md`（仅 `--compare-current`）

内部缓存：
- `.webnovel/study_cache/{book_safe}/chapter_index.json`
- `.webnovel/study_cache/{book_safe}/chapter_source.jsonl`
- `.webnovel/study_cache/{book_safe}/chapter_analysis.jsonl`
- `.webnovel/study_cache/{book_safe}/study_meta.json`

## 流程硬约束

- **禁止长段摘录原文**：只允许极短词组或极短句片段。
- **禁止伪装成全文精读**：`analysis_mode != full_text` 时，必须明确写降级说明和置信度。
- **禁止手工切章和手工判断缓存路径**：Step 0-2 必须先调 CLI `study prepare`。
- **禁止默认回写项目记忆**：只有 `--write-memory` 或用户明确要求时才桥接到 `.webnovel/project_memory.json`。
- **禁止直接改当前项目总纲/设定**：`--compare-current` 只输出建议文件。

## Workflow Checklist

```text
拆书进度：
- [ ] Step 0: 运行 study prepare 建缓存
- [ ] Step 1: 读取输出规范、边界约束与 study_meta
- [ ] Step 2: 读取 chapter_index/chapter_source 并确定分析边界
- [ ] Step 3: 生成 chapter_analysis.jsonl
- [ ] Step 4: 聚合剧情与节奏报告
- [ ] Step 5: 聚合人物、风格与词句报告
- [ ] Step 6: 提炼可复用模式
- [ ] Step 7: 对当前项目给出建议（可选）
- [ ] Step 8: bridge-memory（可选）
- [ ] Step 9: verify 并交付
```

## References（按步骤导航）

- Step 1：`references/output-spec.md`
- Step 1：`references/copyright-boundary.md`
- Step 1-2：`references/source-normalization.md`
- Step 3-4：`references/analysis-dimensions.md`
- Step 5：`references/style-signals.md`
- Step 6：`references/pattern-extraction.md`
- Step 8：`references/memory-bridge.md`

## Step 0：运行 `study prepare`

必须执行：
```bash
"$PYTHON_BIN" "${SCRIPTS_DIR}/webnovel.py" --project-root "$PROJECT_ROOT" study prepare \
  "{source_path}" --mode {mode} --range {range} {compare_current_flag} {write_memory_flag}
```

要求：
- 由 CLI 负责校验 `source_path`、识别格式、生成 `book_safe`
- 由 CLI 负责生成 `chapter_index.json`、`chapter_source.jsonl`、`study_meta.json`
- 由 CLI 负责判断：`text_quality`、`analysis_mode`、`obfuscation_detected`
- 若 `analysis_mode=blocked`，停止后续分析，只向用户解释阻断原因

## Step 1：读取规范与 study meta

必读：
```bash
cat "${SKILL_ROOT}/references/output-spec.md"
cat "${SKILL_ROOT}/references/copyright-boundary.md"
cat "$CACHE_ROOT/study_meta.json"
```

要求：
- 先确认本次 mode 对应的必须产物
- 再确认 `analysis_mode` 是否允许人物/文风/词句做高置信判断
- 若为 `degraded_structure_only`，必须在 `00_总览.md` 写清研究边界与置信度

## Step 2：读取结构化源数据

必读：
```bash
cat "$CACHE_ROOT/chapter_index.json"
cat "$CACHE_ROOT/chapter_source.jsonl"
```

要求：
- `chapter_index.json` 负责给出章节边界与标题序列
- `chapter_source.jsonl` 负责给出每章可消费片段、质量、证据来源、置信度
- 后续分析以这两个缓存为准，不再重复手搓切章

## Step 3：生成 `chapter_analysis.jsonl`

必读：
```bash
cat "${SKILL_ROOT}/references/analysis-dimensions.md"
```

逐章最小字段：
- `chapter_number`
- `chapter_title`
- `summary`
- `plot_role`
- `hook_types`
- `payoffs`
- `new_question`
- `characters_entered`
- `conflict_level`
- `style_signals`
- `notes`
- `confidence`
- `evidence_basis`

要求：
- 基于 `chapter_source.jsonl` 逐章写入 `chapter_analysis.jsonl`
- `summary` 仍然控制在 50-120 字，不写长梗概
- `confidence` 与 `evidence_basis` 必须和源数据质量一致

## Step 4：聚合剧情与节奏报告

必须生成：
- `00_总览.md`
- `01_剧情结构.md`
- `05_章节节奏.json`

硬要求：
- 说明标题承诺如何兑现
- 说明前三章是否形成小闭环
- 说明阶段承诺、最低谷、反转点、大兑现
- 标出中段是否掉速，以及掉速原因
- 若降级分析，显式说明依据是“标题序列 + 可读片段 + 结构推断”

## Step 5：聚合人物、风格与词句报告

必读：
```bash
cat "${SKILL_ROOT}/references/style-signals.md"
```

按 mode 生成：
- `02_人物特点.md`
- `03_文笔风格.md`
- `04_常用词句.md`

硬要求：
- `analysis_mode=full_text`：可正常输出
- `analysis_mode=degraded_structure_only`：仍可输出，但必须标注“中低置信/结构推断/抽样正文”
- `analysis_mode=blocked`：不生成这些文件

## Step 6：提炼可复用模式

必读：
```bash
cat "${SKILL_ROOT}/references/pattern-extraction.md"
```

输出：
- `06_可复用模式.json`

要求：
- 每条模式至少包含：`pattern_type`、`name`、`description`、`evidence_range`、`transfer_rule`、`risk`、`adaptation_note`、`score`
- 建议补充：`learnability`、`confidence`、`evidence_basis`
- 必须区分：`可直接学 / 需改造 / 不建议学`

## Step 7：对当前项目给出建议（可选）

触发条件：
- 用户显式传 `--compare-current`

读取：
- `大纲/总纲.md`
- `设定集/写作风格.md`
- 必要时读取 `设定集/主角卡.md`、`设定集/反派设计.md`

输出：
- `07_对当前项目建议.md`

## Step 8：bridge-memory（可选）

触发条件：
- 用户传 `--write-memory`

必须执行：
```bash
"$PYTHON_BIN" "${SCRIPTS_DIR}/webnovel.py" --project-root "$PROJECT_ROOT" study bridge-memory \
  --book-safe "{book_safe}" --limit 10
```

要求：
- 只桥接高分、非重复、可迁移模式
- 不手工直接改 `.webnovel/project_memory.json`

## Step 9：verify 并交付

必须执行：
```bash
"$PYTHON_BIN" "${SCRIPTS_DIR}/webnovel.py" --project-root "$PROJECT_ROOT" study verify \
  --book-safe "{book_safe}" --mode {mode} {compare_current_flag} {write_memory_flag}
```

必须检查：
- 公共输出是否齐全
- 缓存文件是否齐全
- `study_meta.json` 中 `mode/range/analysis_mode/text_quality` 是否完整
- 若启用 `--write-memory`，确认 `.webnovel/project_memory.json` 已更新

## 成功标准

- CLI 已完成确定性准备、桥接和校验
- Claude 只负责语义分析与报告生成，不再手搓底层缓存
- 当 EPUB 正文混淆时，流程会诚实降级，而不是伪装成全文精读
- 输出文件既能给人看，也能继续被后续命令消费
