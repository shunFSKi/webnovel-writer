# Webnovel Writer

[![License](https://img.shields.io/badge/License-GPL%20v3-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://www.python.org/)
[![Claude Code](https://img.shields.io/badge/Claude%20Code-Compatible-purple.svg)](https://claude.ai/claude-code)

[项目仓库](https://github.com/shunFSKi/webnovel-writer)

## 项目简单介绍

`Webnovel Writer` 是基于 Claude Code 的长篇网文创作系统，目标是降低 AI 写作中的“遗忘”和“幻觉”，支持长周期连载创作。

详细文档已拆分到 `docs/`：

- 架构与模块：`docs/architecture.md`
- 命令详解：`docs/commands.md`
- RAG 与配置：`docs/rag-and-config.md`
- 题材模板：`docs/genres.md`
- 运维与恢复：`docs/operations.md`
- 文档导航：`docs/README.md`

## 快速开始

### 1) 安装插件（自定义 Marketplace）

```bash
claude plugin marketplace add shunFSKi/webnovel-writer --scope user
claude plugin install webnovel-writer@shunfski-webnovel-marketplace --scope user
```

> 仅当前项目生效时，将 `--scope user` 改为 `--scope project`。

如果你不想依赖远程仓库，也可以直接从本地仓库目录安装：

```bash
claude plugin marketplace add /absolute/path/to/webnovel-writer --scope user
claude plugin install webnovel-writer@shunfski-webnovel-marketplace --scope user
```

### 2) 安装 Python 依赖

```bash
python -m pip install -r https://raw.githubusercontent.com/shunFSKi/webnovel-writer/HEAD/requirements.txt
```

说明：该入口会同时安装核心写作链路与 Dashboard 依赖。

### 3) 初始化小说项目

在 Claude Code 中执行：

```bash
/webnovel-init
```

说明：`/webnovel-init` 会在当前 Workspace 下按书名创建 `PROJECT_ROOT`（子目录），并在 `workspace/.claude/.webnovel-current-project` 写入当前项目指针。

### 4) 配置 RAG 环境（必做）

进入初始化后的书项目根目录，创建 `.env`：

```bash
cp .env.example .env
```

最小配置示例：

```bash
EMBED_BASE_URL=https://api-inference.modelscope.cn/v1
EMBED_MODEL=Qwen/Qwen3-Embedding-8B
EMBED_API_KEY=your_embed_api_key

RERANK_BASE_URL=https://api.jina.ai/v1
RERANK_MODEL=jina-reranker-v3
RERANK_API_KEY=your_rerank_api_key
```

说明：

- 环境变量加载顺序：进程环境变量 > `${PROJECT_ROOT}/.env` > `~/.claude/webnovel-writer/.env`
- 未配置 `EMBED_API_KEY` 时，语义检索会自动回退到 BM25
- 建议每本书单独维护自己的 `.env`，避免多项目串配置

### 5) 开始使用

```bash
/webnovel-plan 1
/webnovel-write 1
/webnovel-review 1-5
/webnovel-query 伏笔
/webnovel-resume
/webnovel-learn "这章的危机钩设计有效"
/webnovel-style-synth
```

### 6) 启动可视化面板（可选）

```bash
/webnovel-dashboard
```

说明：

- Dashboard 为只读面板（项目状态、实体图谱、章节/大纲浏览、追读力查看）
- 前端构建产物已随插件发布，使用者无需本地 `npm build`

### 7) Agent 模型设置（可选）

本项目所有内置 Agent 默认配置为：

```yaml
model: inherit
```

表示子 Agent 继承当前 Claude 会话所用模型。

如果要单独给某个 Agent 指定模型，编辑对应文件（`webnovel-writer/agents/*.md`）的 frontmatter，例如：

```yaml
---
name: context-agent
description: ...
tools: Read, Grep, Bash
model: sonnet
---
```

常见可选值：`inherit` / `sonnet` / `opus` / `haiku`（以 Claude Code 当前支持为准）。

## 命令总览

| 命令 | 用途 | 主要产物 |
|------|------|----------|
| `/webnovel-init` | 初始化整本书项目 | `.webnovel/state.json`、`设定集/`、`大纲/总纲.md`、`.webnovel/idea_bank.json` |
| `/webnovel-plan [卷号]` | 生成卷纲与章纲 | `大纲/第X卷-节拍表.md`、`大纲/第X卷-时间线.md`、`大纲/第X卷-详细大纲.md` |
| `/webnovel-write [章号]` | 生成单章正文并回写数据 | `正文/第NNNN章*.md`、`.webnovel/summaries/`、`index.db.review_metrics` |
| `/webnovel-review [范围]` | 审查章节质量 | `审查报告/第start-end章审查报告.md`、`state.json.review_checkpoints` |
| `/webnovel-query [关键词]` | 查询角色、设定、伏笔、节奏 | 终端结构化查询结果 |
| `/webnovel-resume` | 恢复中断任务 | `workflow_state.json` 清理/恢复结果 |
| `/webnovel-dashboard` | 启动只读面板 | 本地 Dashboard 服务 |
| `/webnovel-learn [内容]` | 沉淀写作模式到项目记忆 | `.webnovel/project_memory.json` |
| `/webnovel-study [样书路径]` | 拆解整本样书并输出结构化分析 | `参考拆书/{book_safe}/`、`.webnovel/study_cache/{book_safe}/` |
| `/webnovel-style-synth` | 综合参考拆书风格生成项目风格指南 | `设定集/参考拆书综合风格指南.md` |

## 命令详细用法

### `/webnovel-init`

用途：深度初始化一本新书，按阶段收集信息，再生成可直接进入规划与写作的项目骨架。

适用场景：

- 新开一本书，还没有项目结构
- 只有模糊创意，需要把题材、主角、金手指、世界观一次性结构化
- 希望后续 `/webnovel-plan` 和 `/webnovel-write` 直接可用

执行方式：

```bash
/webnovel-init
```

会重点收集的信息：

- 书名、题材、目标字数或目标章节数
- 一句话故事、核心冲突、目标读者、平台
- 主角姓名、欲望、缺陷、主角结构、感情线配置
- 金手指类型、名称、风格、可见度、不可逆代价
- 世界规模、势力格局、力量体系、社会阶层、资源分配
- 创意约束、反套路规则、核心卖点、开篇钩子

主要产物：

- `.webnovel/state.json`
- `设定集/世界观.md`
- `设定集/力量体系.md`
- `设定集/主角卡.md`
- `设定集/金手指设计.md`
- `大纲/总纲.md`
- `.webnovel/idea_bank.json`

行为特点：

- 先收集、后生成；关键信息不足时不会直接落盘
- 会把当前 Workspace 与新书项目根绑定到 `.claude/.webnovel-current-project`
- 不会把小说项目生成到插件目录内

### `/webnovel-plan [卷号]`

用途：把 `总纲` 细化为可写作的卷纲、节拍表、时间线和章纲，不会重做整本书的世界观设计。

常见调用：

```bash
/webnovel-plan 1
/webnovel-plan 2-3
```

前置要求：

- 已完成 `/webnovel-init`
- `大纲/总纲.md` 存在
- 至少有基础设定集文件和 `.webnovel/state.json`

执行结果：

- 生成本卷节拍表：`大纲/第{volume_id}卷-节拍表.md`
- 生成本卷时间线：`大纲/第{volume_id}卷-时间线.md`
- 生成本卷详细章纲：`大纲/第{volume_id}卷-详细大纲.md`
- 将本卷新增角色、势力、规则增量回写到已有 `设定集/*`
- 更新 `state.json.progress.volumes_planned`

规划内容包括：

- 卷级承诺、危机递增、中段反转、最低谷、大兑现、新钩子
- Strand 分配（Quest / Fire / Constellation）
- 爽点密度规划
- 每章目标、阻力、代价、时间锚点、章末钩子
- 与创意约束、反派层级、总纲高潮的一致性校验

适合的使用时机：

- 刚完成项目初始化，准备写第一卷
- 已经写到新卷开头，需要先补卷纲
- 发现后续章节规划松散，想先把整卷节奏钉住

### `/webnovel-write [章号]`

用途：执行完整单章写作流水线，默认输出一章可直接发布的正文，并把审查、摘要、索引、RAG 数据一起回写。

常见调用：

```bash
/webnovel-write 1
/webnovel-write 12 --fast
/webnovel-write 25 --minimal
```

模式说明：

| 模式 | 说明 | 适合场景 |
|------|------|----------|
| 默认 | 完整流程：上下文 -> 起草 -> 风格适配 -> 审查 -> 润色 -> 数据回写 -> Git 备份 | 正常写作 |
| `--fast` | 跳过风格适配，保留审查与数据回写 | 赶进度但仍要质量闭环 |
| `--minimal` | 仅保留核心审查器，依然保留润色与数据回写 | 临时快速产章 |

前置要求：

- `preflight` 成功
- 已有 `总纲` 与对应章纲
- 能解析到真实 `PROJECT_ROOT`

默认产物：

- `正文/第{NNNN}章-{title_safe}.md`，若没有章名则回退为 `正文/第{NNNN}章.md`
- `.webnovel/summaries/ch{NNNN}.md`
- `index.db` 中新增 `review_metrics`
- `.webnovel/state.json` 中的进度和 `chapter_meta`

执行流程：

1. 统一预检并解析项目根
2. `context-agent` 生成本章写作执行包
3. 起草正文，默认目标字数约 `2000-2500`
4. 可选进行风格适配（默认开启，`--fast` / `--minimal` 跳过）
5. 用审查子代理做一致性、连贯性、OOC 等检查
6. 先修 `critical`，再修 `high`，最后做 Anti-AI 终检
7. `data-agent` 回写摘要、状态、实体、RAG 索引与风格样本
8. 最后尝试做 Git 备份提交

注意：

- `--fast` / `--minimal` 也不会跳过审查落库和状态回写
- 若某一步失败，优先最小重跑，不回滚整条写作链
- 上一章有明确钩子时，本章必须回应或部分兑现

### `/webnovel-review [范围]`

用途：对已写正文做质量审查，输出报告、评分和返工优先级。

常见调用：

```bash
/webnovel-review 45
/webnovel-review 1-5
```

默认审查深度：

- Core：`consistency` / `continuity` / `ooc` / `reader-pull`
- Full：关键章或用户明确要求时，追加 `high-point` / `pacing`

主要产物：

- `审查报告/第{start}-{end}章审查报告.md`
- `index.db` 中的审查指标记录
- `state.json.review_checkpoints` 中的审查回写

报告会包含：

- 综合评分与维度分数
- 高、中、低优先级问题
- `critical` 问题列表
- 可执行返工建议

注意：

- 如果检测到 `critical` 问题，流程会要求用户决定“立即修复”还是“仅保存报告”
- 审查本身不等于直接改文，除非用户明确授权做最小修复

### `/webnovel-query [关键词]`

用途：查询项目中的角色、设定、势力、伏笔、金手指、节奏等信息，适合在写作前快速取数。

常见调用：

```bash
/webnovel-query 主角
/webnovel-query 金手指
/webnovel-query 伏笔
/webnovel-query 紧急
/webnovel-query 节奏
```

支持的典型查询：

- 标准查询：角色、境界、势力、地点、物品
- 伏笔紧急度分析：查看哪些伏笔接近超期未回收
- 金手指状态：名称、类型、等级、技能、冷却、升级条件
- Strand 节奏分析：Quest / Fire / Constellation 分布与断档警告

内部常用能力：

- `status -- --focus urgency`
- `status -- --focus strand`
- `state.json + 设定集 + 大纲` 联合检索

适合的使用时机：

- 写一章前确认角色当前状态
- 检查某个伏笔是否该兑现
- 看当前节奏是否长期偏 Quest 或偏 Fire
- 追踪金手指成长进度

### `/webnovel-resume`

用途：检测并恢复被中断的写作或审查任务，不猜测中断点，只基于 `workflow` 状态做恢复。

执行方式：

```bash
/webnovel-resume
```

它会做什么：

- 检测当前是否存在中断任务
- 展示任务命令、已完成步骤、当前中断步骤、剩余步骤
- 给出恢复选项和风险等级
- 在用户确认后执行清理或回滚

常见恢复动作：

```bash
python -X utf8 "${SCRIPTS_DIR}/webnovel.py" --project-root "$PROJECT_ROOT" workflow detect
python -X utf8 "${SCRIPTS_DIR}/webnovel.py" --project-root "$PROJECT_ROOT" workflow cleanup --chapter {N} --confirm
python -X utf8 "${SCRIPTS_DIR}/webnovel.py" --project-root "$PROJECT_ROOT" workflow clear
```

恢复原则：

- 不做“智能续写半成品”
- 不跳过中断检测
- 不自动选择恢复策略
- Step 2A 这类正文半成品通常建议删除重来
- Git 回滚属于高风险操作，只作为备选方案

### `/webnovel-dashboard`

用途：启动本地只读 Dashboard，实时查看项目状态、实体图谱、章节和大纲内容。

执行方式：

```bash
/webnovel-dashboard
```

行为特点：

- 默认打开本地浏览器访问 `http://127.0.0.1:8765`
- 通过 `watchdog` 监听 `.webnovel/` 目录变化并实时刷新
- 仅读取 `PROJECT_ROOT` 范围内的数据，不会修改项目文件

手动启动示例：

```bash
python -m dashboard.server --project-root "${PROJECT_ROOT}"
python -m dashboard.server --project-root "${PROJECT_ROOT}" --no-browser
python -m dashboard.server --project-root "${PROJECT_ROOT}" --no-browser --port 9000
```

适合的使用场景：

- 浏览章节和大纲，不想手动翻文件
- 查看实体关系、Strand 节奏和追读力数据
- 排查上下文是否正确写回

### `/webnovel-learn [内容]`

用途：把一次成功的写作经验沉淀进项目记忆，供后续章节复用。

常见调用：

```bash
/webnovel-learn "本章的危机钩设计很有效，悬念拉满"
/webnovel-learn "这段对话节奏适合男女主拉扯"
```

写入结果：

- 文件：`.webnovel/project_memory.json`
- 分类：`hook` / `pacing` / `dialogue` / `payoff` / `emotion`
- 附带来源章节号和学习时间

适合记录的内容：

- 有效的章末钩子类型
- 某类节奏切换方式
- 某种情绪推进或对白写法
- 爽点与微兑现的组合方式

### `/webnovel-study [样书路径]`

用途：先用统一 CLI 做切章、质量分级与缓存准备，再由 Claude 输出整本样书的剧情、人物、文风、节奏与可复用模式分析。

常见调用：

```bash
/webnovel-study "/path/to/book.epub"
/webnovel-study "/path/to/book.epub" --mode full --range all --compare-current
/webnovel-study "/path/to/book.md" --mode style --write-memory
```

主要产物：

- 公共输出：`参考拆书/{book_safe}/00_总览.md` 到 `07_对当前项目建议.md`
- 内部缓存：`.webnovel/study_cache/{book_safe}/chapter_index.json`、`chapter_source.jsonl`、`chapter_analysis.jsonl`、`study_meta.json`
- 可选桥接：`.webnovel/project_memory.json`

说明：

- 支持 `txt`、`md`、`epub`，条件支持带文本层的 `pdf`
- 番茄 EPUB 若检测到私有码混淆，会诚实降级为结构级分析，不伪装成全文精读
- `--compare-current` 只输出建议文件，不直接改当前项目大纲或设定

### `/webnovel-style-synth`

用途：综合分析项目中所有参考拆书的文笔风格，自动提取共性特征和可复用模式，生成适合当前项目的风格指南。

**基础用法**（仅生成风格指南）：

```bash
/webnovel-style-synth
```

或指定拆书目录：

```bash
python3 /path/to/synth_style_guide.py --project-root . --source-dir 参考拆书
```

**策略同步用法**（生成指南 + 同步到项目文件）：

支持三种同步策略：
- `append` - 追加模式：在现有内容后添加新内容
- `merge` - 合并模式：智能合并现有和新内容
- `replace` - 替换模式：完全替换特定章节

```bash
# 追加到写作风格（保留现有内容）
/webnovel-style-synth --strategy append --target style

# 合并到所有文件（智能融合）
/webnovel-style-synth --strategy merge --target all

# 替换风格契约（完全重构）
/webnovel-style-synth --strategy replace --target contract
```

**目标文件**：
- `preferences` - 同步到 `.webnovel/preferences.json`
- `style` - 同步到 `设定集/写作风格.md`
- `contract` - 同步到 `设定集/风格契约.md`
- `all` - 同步到所有文件

主要产物：

- `设定集/参考拆书综合风格指南.md`，包含：
  - 参考书目清单
  - 题材与类型分布
  - 开篇钩子分析
  - 节奏与结构特点
  - 共性风格特征（句长、段长、对白、描写特点）
  - 各书详细特征分析（剧情、人物、文笔、词句）
  - 可复用模式建议
  - 避坑指南
  - 项目适配建议

功能特点：

- 读取所有 5 个拆书分析文件（00-04）
- 从题材类型、剧情结构、人物特点、文笔风格、常用词句多维度分析
- 统计句长、段长、对白占比、动作描写比例等数据
- 识别常见写作模式和特征
- 生成可操作的风格指南
- **新增**：支持策略同步到项目风格文件

适合的使用时机：

- 项目初始化后，参考拆书积累到一定数量
- 需要整理参考风格并形成项目专属风格指南时
- 想要快速了解多本参考书的共同特点和差异时
- **新增**：需要将参考风格同步到项目配置文件时

与现有工具的配合：

- 生成风格指南后，可与 `设定集/写作风格.md` 结合使用
- 为 `/webnovel-write` 提供更明确的风格参考
- 作为 `/webnovel-init` 的补充，在项目建立后进一步完善风格约束
- **新增**：与 `设定集/风格契约.md` 配合，提供运行时风格约束

## 手动 CLI 与排障入口

当 slash command 不方便、需要批处理、需要调试路径解析，或者想单独验证某个步骤时，推荐直接走统一入口脚本：`webnovel.py`。

### 统一前置环境

```bash
export WORKSPACE_ROOT="${CLAUDE_PROJECT_DIR:-$PWD}"
export SCRIPTS_DIR="${CLAUDE_PLUGIN_ROOT}/scripts"
export PROJECT_ROOT="$(python -X utf8 "${SCRIPTS_DIR}/webnovel.py" --project-root "${WORKSPACE_ROOT}" where)"
```

统一帮助：

```bash
python -X utf8 "${SCRIPTS_DIR}/webnovel.py" --help
```

查看透传子命令帮助时，统一在子命令后加 `-- --help`：

```bash
python -X utf8 "${SCRIPTS_DIR}/webnovel.py" --project-root "${PROJECT_ROOT}" index -- --help
python -X utf8 "${SCRIPTS_DIR}/webnovel.py" --project-root "${PROJECT_ROOT}" state -- --help
python -X utf8 "${SCRIPTS_DIR}/webnovel.py" --project-root "${PROJECT_ROOT}" rag -- --help
```

### 顶层子命令总览

| 子命令 | 作用 | 备注 |
|--------|------|------|
| `where` | 打印解析出的真实项目根 | 常用于排查工作区和书项目不一致 |
| `preflight` | 统一预检 | 校验脚本、Skill 路径、项目根解析 |
| `use` | 绑定当前工作区对应的书项目 | 写入 workspace pointer 和 global registry |
| `init` | 直接创建小说项目骨架 | `/webnovel-init` 的底层生成入口 |
| `extract-context` | 导出某章上下文 | 常配合 context-agent 或调试使用 |
| `workflow` | 任务断点管理 | detect / cleanup / clear / start-step 等 |
| `status` | 生成项目状态报告 | 支持 `all` / `urgency` / `strand` |
| `index` | 管理索引与审查指标 | 处理章节、保存 review metrics、统计 |
| `state` | 管理状态数据 | 透传到 `state_manager` |
| `rag` | 管理向量索引与检索 | 重建章节向量、看 stats |
| `style` | 管理风格样本 | 透传到 `style_sampler` |
| `entity` | 管理实体链接 | 透传到 `entity_linker` |
| `context` | 管理上下文抽取 | 透传到 `context_manager` |
| `migrate` | 状态迁移 | 透传到 `migrate_state_to_sqlite` |
| `update-state` | 增量更新 `state.json` | 卷规划、审查记录等 |
| `backup` | 备份运行数据 | 透传到 `backup_manager.py` |
| `archive` | 归档项目数据 | 透传到 `archive_manager.py` |

### 定位与环境相关命令

#### `where`

用途：打印当前工作区最终解析到的 `PROJECT_ROOT`。

```bash
python -X utf8 "${SCRIPTS_DIR}/webnovel.py" --project-root "${WORKSPACE_ROOT}" where
```

适合：

- 工作区根不是书项目根时确认解析结果
- 排查为什么命令写到了错误目录

#### `preflight`

用途：统一检查 `scripts`、`skills`、`extract_chapter_context.py` 与项目根解析是否正常。

```bash
python -X utf8 "${SCRIPTS_DIR}/webnovel.py" --project-root "${WORKSPACE_ROOT}" preflight
python -X utf8 "${SCRIPTS_DIR}/webnovel.py" --project-root "${WORKSPACE_ROOT}" preflight --format json
```

适合：

- 写作前先做一次环境体检
- 调试插件路径问题、项目根问题
- CI 或 smoke test 中做基础验证

#### `use`

用途：将某本书绑定为当前工作区默认项目。

```bash
python -X utf8 "${SCRIPTS_DIR}/webnovel.py" use "/path/to/你的小说项目"
python -X utf8 "${SCRIPTS_DIR}/webnovel.py" use "/path/to/你的小说项目" --workspace-root "/path/to/workspace"
```

行为：

- 写入 `workspace/.claude/.webnovel-current-project`
- 同步更新 `~/.claude/webnovel-writer/workspaces.json`

### 初始化与上下文命令

#### `init`

用途：不走交互式 skill，直接通过 CLI 生成项目骨架，适合批量初始化、自动化测试或排查初始化问题。

最小示例：

```bash
python -X utf8 "${SCRIPTS_DIR}/webnovel.py" init \
  "${WORKSPACE_ROOT}/烟雨试剑录" \
  "烟雨试剑录" \
  "修仙"
```

常用选项：

- `--protagonist-name`
- `--target-words`
- `--target-chapters`
- `--golden-finger-name`
- `--golden-finger-type`
- `--golden-finger-style`
- `--core-selling-points`
- `--world-scale`
- `--factions`
- `--power-system-type`
- `--protagonist-desire`
- `--protagonist-flaw`
- `--target-reader`
- `--platform`

#### `extract-context`

用途：直接导出某章的上下文包，方便调试 context-agent 输入。

```bash
python -X utf8 "${SCRIPTS_DIR}/webnovel.py" --project-root "${PROJECT_ROOT}" extract-context --chapter 12 --format text
python -X utf8 "${SCRIPTS_DIR}/webnovel.py" --project-root "${PROJECT_ROOT}" extract-context --chapter 12 --format json
```

### Workflow 断点恢复命令

#### `workflow`

常见用法：

```bash
python -X utf8 "${SCRIPTS_DIR}/webnovel.py" --project-root "${PROJECT_ROOT}" workflow detect
python -X utf8 "${SCRIPTS_DIR}/webnovel.py" --project-root "${PROJECT_ROOT}" workflow cleanup --chapter 12 --confirm
python -X utf8 "${SCRIPTS_DIR}/webnovel.py" --project-root "${PROJECT_ROOT}" workflow clear
```

适合：

- `/webnovel-resume` 底层排障
- 强制清理中断任务残留
- 手动检查当前 Step 记录是否异常

### 状态与健康检查命令

#### `status`

用途：生成项目级健康报告或特定维度报告。

```bash
python -X utf8 "${SCRIPTS_DIR}/webnovel.py" --project-root "${PROJECT_ROOT}" status -- --focus all
python -X utf8 "${SCRIPTS_DIR}/webnovel.py" --project-root "${PROJECT_ROOT}" status -- --focus urgency
python -X utf8 "${SCRIPTS_DIR}/webnovel.py" --project-root "${PROJECT_ROOT}" status -- --focus strand
```

常见场景：

- 查看总体健康状况
- 查看伏笔紧急度
- 查看 Strand 断档和节奏失衡

#### `update-state`

用途：对 `state.json` 做受控增量更新。

```bash
python -X utf8 "${SCRIPTS_DIR}/webnovel.py" --project-root "${PROJECT_ROOT}" update-state -- --volume-planned 1 --chapters-range "1-50"
python -X utf8 "${SCRIPTS_DIR}/webnovel.py" --project-root "${PROJECT_ROOT}" update-state -- --add-review "1-5" "审查报告/第1-5章审查报告.md"
```

### 索引、RAG 与数据处理命令

#### `index`

用途：处理章节索引、统计数据、保存审查指标。

```bash
python -X utf8 "${SCRIPTS_DIR}/webnovel.py" --project-root "${PROJECT_ROOT}" index process-chapter --chapter 1
python -X utf8 "${SCRIPTS_DIR}/webnovel.py" --project-root "${PROJECT_ROOT}" index stats
python -X utf8 "${SCRIPTS_DIR}/webnovel.py" --project-root "${PROJECT_ROOT}" index save-review-metrics --data "@${PROJECT_ROOT}/.webnovel/tmp/review_metrics.json"
```

#### `rag`

用途：构建或检查语义检索索引。

```bash
python -X utf8 "${SCRIPTS_DIR}/webnovel.py" --project-root "${PROJECT_ROOT}" rag index-chapter --chapter 1
python -X utf8 "${SCRIPTS_DIR}/webnovel.py" --project-root "${PROJECT_ROOT}" rag stats
```

#### `state` / `style` / `entity` / `context` / `migrate`

这几类命令是统一入口到对应数据模块的透传封装，适合高级运维或排障时直接查看子模块帮助：

```bash
python -X utf8 "${SCRIPTS_DIR}/webnovel.py" --project-root "${PROJECT_ROOT}" state -- --help
python -X utf8 "${SCRIPTS_DIR}/webnovel.py" --project-root "${PROJECT_ROOT}" style -- --help
python -X utf8 "${SCRIPTS_DIR}/webnovel.py" --project-root "${PROJECT_ROOT}" entity -- --help
python -X utf8 "${SCRIPTS_DIR}/webnovel.py" --project-root "${PROJECT_ROOT}" context -- --help
python -X utf8 "${SCRIPTS_DIR}/webnovel.py" --project-root "${PROJECT_ROOT}" migrate -- --help
```

### 备份与归档命令

#### `backup` / `archive`

用于运行数据备份和归档，同样建议先查看帮助再执行：

```bash
python -X utf8 "${SCRIPTS_DIR}/webnovel.py" --project-root "${PROJECT_ROOT}" backup -- --help
python -X utf8 "${SCRIPTS_DIR}/webnovel.py" --project-root "${PROJECT_ROOT}" archive -- --help
```

## 常见问题与排障建议

### 1) 命令找不到正确的书项目目录

先跑：

```bash
python -X utf8 "${SCRIPTS_DIR}/webnovel.py" --project-root "${WORKSPACE_ROOT}" where
```

如果输出的不是你当前这本书：

- 检查 `workspace/.claude/.webnovel-current-project`
- 必要时重新执行 `use`

### 2) 写作链启动前就失败

先跑统一预检：

```bash
python -X utf8 "${SCRIPTS_DIR}/webnovel.py" --project-root "${WORKSPACE_ROOT}" preflight --format json
```

重点看：

- `scripts_dir`
- `entry_script`
- `extract_context_script`
- `skill_root`
- `project_root`

### 3) RAG 检索效果弱或完全不可用

检查：

- `${PROJECT_ROOT}/.env` 是否存在
- `EMBED_API_KEY` / `RERANK_API_KEY` 是否可用
- `rag stats` 是否已有索引

如果没配 Embedding Key，系统会回退到 BM25，不会阻断写作，但语义召回能力会下降。

### 4) 中断任务恢复不干净

按顺序执行：

```bash
python -X utf8 "${SCRIPTS_DIR}/webnovel.py" --project-root "${PROJECT_ROOT}" workflow detect
python -X utf8 "${SCRIPTS_DIR}/webnovel.py" --project-root "${PROJECT_ROOT}" workflow cleanup --chapter {N} --confirm
python -X utf8 "${SCRIPTS_DIR}/webnovel.py" --project-root "${PROJECT_ROOT}" workflow clear
```

### 5) Dashboard 启不来

检查：

- 依赖是否已安装：`python -m pip install -r "${CLAUDE_PLUGIN_ROOT}/dashboard/requirements.txt"`
- 前端产物是否存在：`${CLAUDE_PLUGIN_ROOT}/dashboard/frontend/dist/index.html`
- 当前 `PYTHONPATH` 是否包含 `${CLAUDE_PLUGIN_ROOT}`

## 更新简介

| 版本 | 说明 |
|------|------|
| **v5.5.7 (当前)** | 新增 /webnovel-style-synth 技能，自动分析参考拆书并生成项目风格指南；移除硬编码风格指南，项目本地 `设定集/写作风格.md` 成为最高优先级，工具更加通用化。 |
| **v5.5.6** | 新增项目风格约束包、project-style-checker、Step 4 规则复检与 Step 5 硬闸门，确保写作流程真正阻断风格违规章节进入数据回写。 |
| **v5.5.5** | 新增 /webnovel-study 整本拆书能力；补齐 study CLI 路由、缓存契约、调用矩阵与仓库命令文档。 |
| **v5.5.4** | 补齐写作链提示词强约束（流程硬约束、中文思维写作约束、Step 职责边界）；统一中文化审查/润色/Agent 报告文案；清理文档内部版本号与版本历史，降低与插件发版版本混淆。 |
| **v5.5.3** | 新增统一 `preflight` 预检命令；写作链 CLI 示例统一为 UTF-8 运行方式，收口文档中的长 shell 预检片段并降低 Windows 终端乱码风险。 |
| **v5.5.2** | 支持将详细大纲中的章节名同步到正文文件名；修复 workflow_manager 在无参 find_project_root monkeypatch 下的兼容性问题。 |
| **v5.5.1** | 修复卷级单文件大纲在上下文快照中的章节提取问题；补齐命令文档中遗漏的 `/webnovel-dashboard` 与 `/webnovel-learn`。 |
| **v5.5.0** | 新增只读可视化 Dashboard Skill（`/webnovel-dashboard`）与实时刷新能力；支持插件目录启动与预构建前端分发 |
| **v5.4.4** | 引入官方 Plugin Marketplace 安装机制；统一修复 Skills/Agents/References 的 CLI 调用（`CLAUDE_PLUGIN_ROOT` 单路径，透传命令统一 `--`） |
| **v5.4.3** | 增强智能 RAG 上下文辅助（`auto/graph_hybrid` 回退 BM25） |
| **v5.3** | 引入追读力系统（Hook / Cool-point / 微兑现 / 债务追踪） |

## 插件发版

推荐使用 GitHub Actions 的 `Plugin Release` 工作流统一发版：

1. 先在本地同步版本信息：
   ```bash
   python -X utf8 webnovel-writer/scripts/sync_plugin_version.py --version 5.5.4 --release-notes "本次版本说明"
   ```
2. 提交并推送版本变更（`README.md`、`plugin.json`、`marketplace.json`）。
3. 打开仓库的 Actions 页面，选择 `Plugin Release`。
4. 输入与当前仓库元数据一致的 `version`（例如 `5.5.4`）和用于 GitHub Release 的 `release_notes`。
5. 工作流会执行以下动作：
   - 校验 `plugin.json`、`marketplace.json` 与 README 当前版本已经一致
   - 校验当前版本与输入的 `version` 一致
   - 创建并推送 `vX.Y.Z` Tag
   - 创建同名 GitHub Release

日常开发中，`Plugin Version Check` 会在 Push / PR 时自动校验版本信息是否一致。

## 开源协议

本项目使用 `GPL v3` 协议，详见 `LICENSE`。

## 仓库地址

`shunFSKi/webnovel-writer`：`https://github.com/shunFSKi/webnovel-writer`

## 致谢

本项目使用 **Claude Code + Gemini CLI + Codex** 配合 Vibe Coding 方式开发。
灵感来源：[Linux.do 帖子](https://linux.do/t/topic/1397944/49)

## 贡献

欢迎提交 Issue 和 PR：

```bash
git checkout -b feature/your-feature
git commit -m "feat: add your feature"
git push origin feature/your-feature
```
