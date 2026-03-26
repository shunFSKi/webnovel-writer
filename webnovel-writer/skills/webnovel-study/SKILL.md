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

**核心问题：这本书为什么能签约/火，我能学到什么？**

- 用确定性 CLI 先完成源文件预检、切章、缓存和退化模式判断
- 再由 Claude 按**六维度分析框架**完成结构化拆解
- 所有分析必须落到"可复用"层面，提供可直接用于写作的提示词指令
- 保持公共产物契约稳定，并让流程可重跑、可验证、可恢复

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

- `full`：输出全部六维度分析（00-05），可选 06
- `opening`：只做开篇钩子分析（00-01）
- `payoff`：只做爽点结构分析（00、02、05）
- `character`：只做人物塑造分析（00、03、05）
- `emotion`：只做情绪与节奏分析（00、04、05）
- `pattern`：只做可复用技巧提取（00、05）

默认：`--mode full --range all`

## 默认产物

**六维度分析输出**：
- `参考拆书/{book_safe}/00_总览.md`
- `参考拆书/{book_safe}/01_开篇钩子分析.md`（重点拆前三章）
- `参考拆书/{book_safe}/02_爽点结构分析.md`（压制→释放→反馈循环）
- `参考拆书/{book_safe}/03_人物塑造分析.md`（对话差异）
- `参考拆书/{book_safe}/04_情绪与节奏分析.md`（情绪设计+叙事节奏）
- `参考拆书/{book_safe}/05_可复用技巧清单.json`（含提示词指令）
- `参考拆书/{book_safe}/06_对当前项目建议.md`（仅 `--compare-current`）

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
- [ ] Step 1: 读取六维度分析框架与 study_meta
- [ ] Step 2: 读取 chapter_index/chapter_source 并确定分析边界
- [ ] Step 3: 生成 chapter_analysis.jsonl（按六维度标记）
- [ ] Step 4: 输出开篇钩子分析（01）
- [ ] Step 5: 输出爽点结构分析（02）
- [ ] Step 6: 输出人物塑造分析（03）
- [ ] Step 7: 输出情绪与节奏分析（04）
- [ ] Step 8: 提炼可复用技巧清单（05）
- [ ] Step 9: 对当前项目给出建议（可选，06）
- [ ] Step 10: bridge-memory（可选）
- [ ] Step 11: verify 并交付
```

## References（按步骤导航）

- Step 1：`references/output-spec.md`（输出规范）
- Step 1：`references/copyright-boundary.md`（版权边界）
- Step 1-2：`references/source-normalization.md`（源数据规范）
- Step 3：`references/analysis-dimensions.md`（**六维度分析框架主文档**）
- Step 4：`references/payoff-structure-analysis.md`（爽点结构专项）
- Step 5：`references/character-analysis-guide.md`（人物塑造专项）
- Step 6：`references/emotion-design-guide.md`（情绪设计专项）
- Step 7：`references/pacing-narrative-guide.md`（节奏叙事专项）
- Step 8：`references/pattern-extraction.md`（可复用技巧提取）
- Step 10：`references/memory-bridge.md`（记忆桥接）

**六维度分析框架**：
1. **开篇钩子分析**（Step 4）- 重点拆前三章
2. **爽点结构分析**（Step 5）- 压制→释放→反馈循环
3. **人物塑造分析**（Step 6）- 对话差异、辨识度
4. **情绪设计分析**（Step 7）- 情绪密度、制造方式
5. **节奏叙事分析**（Step 7）- 对话叙述比例、场景转换
6. **可复用技巧清单**（Step 8）- 含提示词指令

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
- `hook_types`（章末钩子类型）
- `payoffs`（爽点类型）
- `buildup_level`（压制程度 1-10）
- `payoff_satisfaction`（爽点满足度 1-10）
- `new_question`
- `characters_entered`
- `emotional_intensity`（情绪强度 1-10）
- `emotion_type`（情绪类型：爽/紧张/虐/平淡）
- `dialogue_ratio`（对话占比估计）
- `narrative_pacing`（叙事节奏：快/中/慢）
- `notes`
- `confidence`
- `evidence_basis`

要求：
- 基于 `chapter_source.jsonl` 逐章写入 `chapter_analysis.jsonl`
- **为六维度分析做准备**：标记每章的钩子、爽点、情绪、节奏
- `confidence` 与 `evidence_basis` 必须和源数据质量一致

## Step 4：输出开篇钩子分析（01）

必读：
```bash
cat “${SKILL_ROOT}/references/analysis-dimensions.md”
```

输出：
- `01_开篇钩子分析.md`

硬要求：
- **第一章第一段在做什么？**
  - 是先交代背景还是直接进事件？
  - 读者读完第一段知道了什么信息？
  - 有没有悬念或冲突？
- **前三章的核心功能分别是什么？**
  - 第一章完成了什么任务？
  - 第二章完成了什么任务？
  - 第三章完成了什么任务？
- **读者读完前三章会不会继续看？为什么？**
  - 吸引读者继续看的钩子是什么？
  - 如果你要弃书，会在哪里弃？为什么？
- **信息投放节奏**
  - 前三章给了读者多少信息？
  - 哪些信息是立刻告诉读者的？
  - 哪些信息是藏着的（制造悬念）？
  - 信息投放的密度是不是合理？

## Step 5：输出爽点结构分析（02）

必读：
```bash
cat “${SKILL_ROOT}/references/payoff-structure-analysis.md”
```

输出：
- `02_爽点结构分析.md`

硬要求：
- **标记出每一个爽点的位置**（第几章第几段）
- **每个爽点的类型是什么？**
  - 打脸/碾压/获得宝物/升级/身份揭示/逆转局面/智商碾压
- **每个爽点之前有多少章的铺垫/压制？**
  - 压制的具体方式是什么？
  - 压制到什么程度？
- **爽点释放的方式是什么？**
  - 是一次性释放还是分层释放？
  - 释放之后有没有收获/反馈环节？
- **总结这本书的爽点循环模式**
  - 小循环大概几章一轮？
  - 大循环大概几章一轮？
  - 这个节奏给你什么感觉？太快/太慢/刚好？

## Step 6：输出人物塑造分析（03）

必读：
```bash
cat “${SKILL_ROOT}/references/character-analysis-guide.md”
```

输出：
- `03_人物塑造分析.md`

硬要求：
- **主角**
  - 第一次出场时读者对他的印象是什么？
  - 作者用了什么手段让读者记住他？（一个动作/一句话/一个决定）
  - 他的核心性格是什么？是通过什么展示的？
  - 他说话有没有辨识度？举例。
- **配角/反派**
  - 写得最好的配角是谁？好在哪里？
  - 反派是怎么出场的？第一次出场是不是就让人讨厌？
  - 反派有没有”人味”？还是纯工具人？
- **对话差异**
  - 不同角色说话有没有区别？
  - 能不能遮住名字分辨出是谁在说话？
  - 举出两段对话，说明角色语言差异在哪里

## Step 7：输出情绪与节奏分析（04）

必读：
```bash
cat “${SKILL_ROOT}/references/emotion-design-guide.md”
cat “${SKILL_ROOT}/references/pacing-narrative-guide.md”
```

输出：
- `04_情绪与节奏分析.md`

硬要求：
- **情绪设计分析**
  - 标记出你读的时候产生情绪波动的位置
  - 情绪是怎么制造的？（直接描写 vs 情境）
  - 章末处理：抽取5个章节的结尾，分析钩子类型
  - 情绪密度：平均每章有几次情绪起伏？
- **节奏和叙事分析**
  - 对话与叙述的比例大概是多少？
  - 有没有大段的环境描写或心理描写？
  - 信息传递的方式：世界观是怎么告诉读者的？
  - 场景转换：过渡是怎么处理的？
  - 节奏快慢：哪些地方加速/减速？

## Step 8：提炼可复用技巧清单（05）

必读：
```bash
cat “${SKILL_ROOT}/references/pattern-extraction.md”
```

输出：
- `05_可复用技巧清单.json`

硬要求：
- **每条技巧必须包含**：
  - 技巧名称
  - 原书怎么用的（具体描述）
  - 怎么用到自己的书里（应用建议）
  - **在提示词里怎么写**（可直接放进提示词的指令）
- **至少提取 5 个可复用技巧**
## Step 9：对当前项目给出建议（可选）

触发条件：
- 用户显式传 `--compare-current`

读取：
- `大纲/总纲.md`
- `设定集/写作风格.md`
- 必要时读取 `设定集/主角卡.md`、`设定集/反派设计.md`

输出：
- `06_对当前项目建议.md`

硬要求：
- **直接可学**：哪些技巧可以直接套用到当前项目？
- **需要改造后再学**：哪些技巧需要适配当前题材？
- **不建议学**：哪些技巧不适合当前项目？
- **下一步最值得改的 3 个动作**：给出具体优先级

## Step 10：bridge-memory（可选）

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

## Step 11：verify 并交付

必须执行：
```bash
"$PYTHON_BIN" "${SCRIPTS_DIR}/webnovel.py" --project-root "$PROJECT_ROOT" study verify \
  --book-safe "{book_safe}" --mode {mode} {compare_current_flag} {write_memory_flag}
```

必须检查：
- 公共输出是否齐全（按 mode 对应的文件）
- 缓存文件是否齐全
- `study_meta.json` 中 `mode/range/analysis_mode/text_quality` 是否完整
- 若启用 `--write-memory`，确认 `.webnovel/project_memory.json` 已更新

## 成功标准

- CLI 已完成确定性准备、桥接和校验
- Claude 按**六维度分析框架**完成结构化拆解
- 每个维度都回答了"这本书为什么能签约/火，我能学到什么？"
- 可复用技巧都提供了可直接用于写作的提示词指令
- 当 EPUB 正文混淆时，流程会诚实降级，而不是伪装成全文精读
- `study_meta.json` 中 `mode/range/analysis_mode/text_quality` 是否完整
- 若启用 `--write-memory`，确认 `.webnovel/project_memory.json` 已更新

## 成功标准

- CLI 已完成确定性准备、桥接和校验
- Claude 只负责语义分析与报告生成，不再手搓底层缓存
- 当 EPUB 正文混淆时，流程会诚实降级，而不是伪装成全文精读
- 输出文件既能给人看，也能继续被后续命令消费
