# 命令详解

## `/webnovel-init`

用途：初始化小说项目（目录、设定模板、状态文件）。

产出：

- `.webnovel/state.json`
- `设定集/`
- `大纲/总纲.md`

## `/webnovel-plan [卷号]`

用途：生成卷级规划与章节大纲。

示例：

```bash
/webnovel-plan 1
/webnovel-plan 2-3
```

## `/webnovel-write [章号]`

用途：执行完整章节创作流程（上下文 → 草稿 → 审查 → 润色 → 数据落盘）。

示例：

```bash
/webnovel-write 1
/webnovel-write 45
```

常见模式：

- 标准模式：全流程
- 快速模式：`--fast`
- 极简模式：`--minimal`

## `/webnovel-review [范围]`

用途：对历史章节做多维质量审查。

示例：

```bash
/webnovel-review 1-5
/webnovel-review 45
```

## `/webnovel-query [关键词]`

用途：查询角色、伏笔、节奏、状态等运行时信息。

示例：

```bash
/webnovel-query 萧炎
/webnovel-query 伏笔
/webnovel-query 紧急
```

## `/webnovel-resume`

用途：任务中断后自动识别断点并恢复。

示例：

```bash
/webnovel-resume
```

## `/webnovel-dashboard`

用途：启动只读可视化面板，查看项目状态、实体关系、章节与大纲内容。

示例：

```bash
/webnovel-dashboard
```

说明：

- 默认只读，不会修改项目文件
- 适合排查上下文、实体关系和章节进度

## `/webnovel-learn [内容]`

用途：从当前会话或用户输入中提取可复用写作模式，并写入项目记忆。

示例：

```bash
/webnovel-learn "本章的危机钩设计很有效，悬念拉满"
```

产出：

- `.webnovel/project_memory.json`

## `/webnovel-study [样书路径]`

用途：拆解整本样书，先走 CLI 预处理，再输出剧情、人物、文风、节奏与可复用模式，并可对当前项目给出借鉴建议。

示例：

```bash
/webnovel-study "/path/to/book.epub"
/webnovel-study "/path/to/book.epub" --mode full --range all --compare-current
/webnovel-study "/path/to/book.md" --mode style --write-memory
```

主要产出：

- `参考拆书/{book_safe}/00_总览.md`
- `参考拆书/{book_safe}/01_剧情结构.md`
- `参考拆书/{book_safe}/02_人物特点.md`
- `参考拆书/{book_safe}/03_文笔风格.md`
- `参考拆书/{book_safe}/04_常用词句.md`
- `参考拆书/{book_safe}/05_章节节奏.json`
- `参考拆书/{book_safe}/06_可复用模式.json`
- `参考拆书/{book_safe}/07_对当前项目建议.md`（仅 `--compare-current`）
- `.webnovel/study_cache/{book_safe}/chapter_index.json`
- `.webnovel/study_cache/{book_safe}/chapter_source.jsonl`
- `.webnovel/study_cache/{book_safe}/chapter_analysis.jsonl`
- `.webnovel/study_cache/{book_safe}/study_meta.json`

说明：

- 支持 `txt`、`md`、`epub`，条件支持带文本层的 `pdf`
- `--compare-current` 只输出建议，不直接改当前项目文件
- `--write-memory` 会通过 CLI 桥接高分模式到 `.webnovel/project_memory.json`
- 遇到番茄 EPUB 私有码混淆时，会自动降级为结构级分析
