---
name: output-spec
purpose: 定义 /webnovel-study 的输出文件清单、最小字段与按 mode 裁剪规则
---

# Output Spec

## 1. 标准输出目录

**六维度分析输出**：
```text
参考拆书/{book_safe}/
├── 00_总览.md
├── 01_开篇钩子分析.md
├── 02_爽点结构分析.md
├── 03_人物塑造分析.md
├── 04_情绪与节奏分析.md
├── 05_可复用技巧清单.json
└── 06_对当前项目建议.md（仅 --compare-current）
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
- `chapter_source.jsonl` 是内部结构化源数据缓存，不属于给用户看的报告
- `06_对当前项目建议.md` 仅在 `--compare-current` 时要求生成

## 2. mode -> 输出裁剪表

| mode | 必须输出 |
|------|----------|
| full | 00 01 02 03 04 05 |
| opening | 00 01 |
| payoff | 00 02 05 |
| character | 00 03 05 |
| emotion | 00 04 05 |
| pattern | 00 05 |

说明：
- `chapter_index.json`、`chapter_source.jsonl`、`chapter_analysis.jsonl`、`study_meta.json` 默认都要生成
- `06_对当前项目建议.md` 仅在 `--compare-current` 时生成
- `verify` 按此表校验公共产物是否齐全

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

### 01_开篇钩子分析.md
必须包含：
- **第一章第一段在做什么？**
  - 是先交代背景还是直接进事件？
  - 读者读完第一段知道了什么信息？
  - 有没有悬念或冲突？
- **前三章的核心功能分别是什么？**
- **读者读完前三章会不会继续看？为什么？**
- **信息投放节奏**

### 02_爽点结构分析.md
必须包含：
- 标记出每一个爽点的位置（第几章第几段）
- 每个爽点的类型是什么？
- 每个爽点之前有多少章的铺垫/压制？
- 爽点释放的方式是什么？
- 总结这本书的爽点循环模式

### 03_人物塑造分析.md
必须包含：
- **主角**：第一次出场印象、记忆点手段、核心性格、说话辨识度
- **配角/反派**：写得最好的配角、反派出场方式、反派人味
- **对话差异**：能不能遮住名字分辨出是谁在说话？举例说明

### 04_情绪与节奏分析.md
必须包含：
- **情绪设计分析**：
  - 标记情绪波动位置
  - 情绪制造方式（直接描写 vs 情境）
  - 章末钩子分析
  - 情绪密度
- **节奏和叙事分析**：
  - 对话与叙述比例
  - 信息传递方式
  - 场景转换
  - 节奏快慢

### 05_可复用技巧清单.json
最小结构：
```json
{
  "book": "书名",
  "source_quality": "A/B/C/D",
  "analysis_mode": "full_text/degraded_structure_only/blocked",
  "techniques": [
    {
      "id": 1,
      "name": "技巧名称",
      "how_used_in_book": "原书怎么用的（具体描述）",
      "how_to_adapt": "怎么用到自己的书里（应用建议）",
      "prompt_instruction": "在提示词里怎么写（可直接放进提示词的指令）",
      "pattern_type": "hook/payoff/character/emotion/structure",
      "evidence_range": "第X-Y章",
      "score": 9,
      "learnability": "可直接学/需改造/不建议学",
      "confidence": "high/medium/low"
    }
  ]
}
```

### 06_对当前项目建议.md
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

- `full_text`：可按正常精读口径输出全部分析
- `degraded_structure_only`：允许输出 `00-05`，但必须标置信度和研究边界
- `blocked`：只允许输出错误/阻断信息，不应伪装生成完整报告

## 5. 不合格输出示例

- 只生成一份大长文，没有结构化文件
- `05_可复用技巧清单.json` 里只有自然语言，没有字段
- `05_可复用技巧清单.json` 只有名称，没有迁移规则和提示词指令
- 各维度分析变成剧情复述
- 堆长摘录原文
- 正文已混淆却不写退化说明

## 6. 验收口径

通过标准：
- 人能看懂：文档可读、能指导创作
- 机能消费：JSON/JSONL 字段稳定、后续可复用
- 可重跑：prepare/verify 后能补缺文件而不是重做全流程
- 可迁移：结论能落到别的项目，而不是只对这一本书成立
- **可操作**：每个技巧都提供了可直接用于提示词的指令
