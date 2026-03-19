---
name: output-spec
purpose: 定义 /webnovel-study 的输出文件清单、最小字段与按 mode 裁剪规则
---

# Output Spec

## 1. 标准输出目录

```text
参考拆书/{book_safe}/
├── 00_总览.md
├── 01_剧情结构.md
├── 02_人物特点.md
├── 03_文笔风格.md
├── 04_常用词句.md
├── 05_章节节奏.json
├── 06_可复用模式.json
└── 07_对当前项目建议.md
```

缓存目录：

```text
.webnovel/study_cache/{book_safe}/
├── chapter_index.json
├── chapter_source.jsonl
├── chapter_analysis.jsonl
└── study_meta.json
```

说明：
- `chapter_source.jsonl` 是内部结构化源数据缓存，不属于给用户看的报告。
- `07_对当前项目建议.md` 仅在 `--compare-current` 时要求生成。

## 2. mode -> 输出裁剪表

| mode | 必须输出 |
|------|----------|
| full | 00 01 02 03 04 05 06 |
| plot | 00 01 05 06 |
| characters | 00 02 06 |
| style | 00 03 04 06 |
| phrases | 00 04 06 |
| pacing | 00 01 05 06 |

说明：
- `chapter_index.json`、`chapter_source.jsonl`、`chapter_analysis.jsonl`、`study_meta.json` 默认都要生成。
- `verify` 按此表校验公共产物是否齐全。

## 3. 逐文件最小要求

### 00_总览.md
必须包含：
- 一句话定位
- 题材/赛道判断
- 标题承诺
- 最强卖点 3 条
- 明显短板 2-3 条
- 适合学习人群
- 研究边界/置信度说明（当 `analysis_mode != full_text` 时为必填）

### 01_剧情结构.md
必须包含：
- 开篇前 3 章抓读分析
- 主线/支线/反派压力结构
- 卷或阶段承诺
- 中段反转/最低谷/大兑现
- 节奏失速点与原因

### 02_人物特点.md
必须包含：
- 主角卖点与缺陷
- 主角决策模型
- 核心配角功能分工
- 反派分层
- 人物话风区分
- 若为退化分析，需标明“基于标题序列/抽样片段推断”

### 03_文笔风格.md
必须包含：
- 句长与段长倾向
- 对白比例趋势
- 动作/心理/说明占比
- 常用推进方式
- 风格风险点
- 若为退化分析，需标明“非全文逐句统计”

### 04_常用词句.md
必须包含：
- 高频动词
- 高频意象
- 常见句式
- 对白口头语/语气词
- 建议避开的低价值表达
- 若为退化分析，需标明来源边界

### 05_章节节奏.json
最小结构：
```json
{
  "book": "书名",
  "range": "all",
  "source_quality": "A/B/C/D",
  "analysis_mode": "full_text/degraded_structure_only/blocked",
  "chapters": [
    {
      "chapter_number": 1,
      "chapter_title": "章名",
      "plot_role": "开局",
      "hook_types": ["事故钩"],
      "payoffs": ["主角第一次强反馈"],
      "conflict_level": 4,
      "new_question": "更大的问题",
      "confidence": "high/medium/low",
      "evidence_basis": ["title", "excerpt"]
    }
  ],
  "global_findings": {
    "title_payoff_speed": "快/中/慢",
    "opening_closure": true,
    "midpoint_reversal": true,
    "late_stage_acceleration": "强/中/弱"
  }
}
```

### 06_可复用模式.json
最小结构：
```json
{
  "book": "书名",
  "source_quality": "A/B/C/D",
  "analysis_mode": "full_text/degraded_structure_only/blocked",
  "patterns": [
    {
      "pattern_type": "hook",
      "name": "事故兑现开篇",
      "description": "标题承诺在第一章末落地",
      "evidence_range": "第1-3章",
      "transfer_rule": "适合事故型男频开篇",
      "risk": "若后续反馈跟不上会掉速",
      "adaptation_note": "用于本项目时应嫁接治河任务",
      "score": 9,
      "learnability": "可直接学",
      "confidence": "high/medium/low",
      "evidence_basis": ["title", "excerpt"]
    }
  ]
}
```

### 07_对当前项目建议.md
必须包含：
- 直接可学
- 需要改造后再学
- 不建议学
- 下一步最值得改的 3 个动作

### chapter_index.json
建议字段：
```json
[
  {
    "chapter_number": 1,
    "volume": "卷一",
    "chapter_title": "暴雨夜",
    "start_offset": 120,
    "end_offset": 3540,
    "valid": true,
    "quality": "A",
    "source_ref": "chapter_0001.xhtml"
  }
]
```

### chapter_source.jsonl
每行建议字段：
```json
{
  "chapter_number": 1,
  "chapter_title": "暴雨夜",
  "content_excerpt": "清洗后的可读片段",
  "source_ref": "chapter_0001.xhtml",
  "quality": "B",
  "confidence": "medium",
  "evidence_basis": ["title", "excerpt"],
  "obfuscation_detected": true,
  "text_stats": {
    "visible_chars": 860,
    "cjk_ratio": 0.42,
    "private_use_ratio": 0.18
  }
}
```

### study_meta.json
至少包含：
```json
{
  "source_path": "/path/to/book.epub",
  "source_format": "epub",
  "book_title": "书名",
  "book_safe": "书名-safe",
  "chapter_count": 94,
  "selected_chapter_count": 94,
  "mode": "full",
  "range": "all",
  "batch_count": 1,
  "text_quality": "B",
  "analysis_mode": "degraded_structure_only",
  "obfuscation_detected": true,
  "compare_current": true,
  "write_memory": false,
  "warnings": [],
  "generated_at": "2026-03-19"
}
```

## 4. 退化模式约束

- `full_text`：可按正常精读口径输出全部分析。
- `degraded_structure_only`：允许输出 `00-06`，但人物/文风/词句必须标置信度和研究边界。
- `blocked`：只允许输出错误/阻断信息，不应伪装生成完整报告。

## 5. 不合格输出示例

- 只生成一份大长文，没有结构化文件
- `05_章节节奏.json` 里只有自然语言，没有字段
- `06_可复用模式.json` 只有名称，没有迁移规则和风险
- `03_文笔风格.md` 变成剧情复述
- `04_常用词句.md` 堆长摘录原文
- 正文已混淆却不写退化说明

## 6. 验收口径

通过标准：
- 人能看懂：文档可读、能指导创作
- 机能消费：JSON/JSONL 字段稳定、后续可复用
- 可重跑：prepare/verify 后能补缺文件而不是重做全流程
- 可迁移：结论能落到别的项目，而不是只对这一本书成立
