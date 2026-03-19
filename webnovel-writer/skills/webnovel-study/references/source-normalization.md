---
name: source-normalization
purpose: 指导 /webnovel-study 对样书源文本做标准化、切章与质量分级
---

# Source Normalization

## 1. 输入优先级

按稳定性从高到低：
1. `txt`
2. `md`
3. `epub`
4. 带文本层的 `pdf`
5. 其他格式先转文本再分析

## 2. 预处理职责分层

### CLI `study prepare` 负责
- 校验 `source_path`
- 识别 `source_format`
- 生成 `book_safe`
- 创建 `参考拆书/{book_safe}` 与 `.webnovel/study_cache/{book_safe}`
- 清洗文本并切章
- 写入 `chapter_index.json`
- 写入 `chapter_source.jsonl`
- 写入 `study_meta.json`
- 判断 `text_quality`、`analysis_mode`、`obfuscation_detected`

### Claude 负责
- 读取结构化缓存后做剧情/人物/风格/模式分析
- 不再重复手搓切章或自行判断缓存目录

## 3. 文本质量分级

### A 级
- 编码正常
- 有清晰章标
- 杂质少
- 可直接整本分析

### B 级
- 偶有乱码或广告
- 章标基本可识别
- 需要轻度清洗
- 可读正文仍足够支撑分析

### C 级
- 章标混乱或正文可读比例偏低
- 广告和杂质较多
- 只建议结构级分析或前段分析

### D 级
- 扫描 OCR 差
- 乱码严重
- 结构不可识别
- 禁止整本分析

## 4. analysis_mode 定义

### `full_text`
- 正文可读
- 可正常做人物/文风/词句分析

### `degraded_structure_only`
- 目录、标题、简介或部分正文片段可读
- 正文混淆严重，无法诚实宣称全文精读
- 仍可做结构、节奏、模式分析
- 人物/文风/词句只能做中低置信结论，并注明边界

### `blocked`
- 连稳定目录或章节边界都拿不到
- 必须中止整本分析

## 5. EPUB 混淆检测信号

出现以下信号时，CLI 应优先判为退化：
- 私用区字符比例异常高
- 标题可读但正文汉字比例异常低
- 多章正文重复出现相似乱码模式
- 章节文本几乎没有可读片段，但目录和标题序列正常

## 6. 章标识别优先模式

优先识别：
- `第1章`
- `第一章`
- `第001章`
- `Chapter 1`
- `卷一 第1章`
- `第1卷 第1章`
- `序章` / `楔子` / `引子`

若同时存在卷名和章名，应都写入索引。

## 7. 必要清洗

允许做：
- 去 BOM
- 统一换行
- 去重复空行
- HTML/EPUB 标签剥离
- 去明显广告头尾或站点水印
- 提取可读片段作为 `content_excerpt`

不要做：
- 不要改正文句序
- 不要私自润色
- 不要根据理解补写缺失段
- 不要把乱码“猜译”为正常文本

## 8. `chapter_index.json` 建议字段

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

## 9. `chapter_source.jsonl` 建议字段

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

## 10. 无章标处理策略

优先顺序：
1. AskUserQuestion 让用户决定
2. 若用户没回，降级为“开篇研究版”
3. 只分析前若干自然段块，不硬切整本

开篇研究版最小产物：
- `00_总览.md`
- `01_剧情结构.md`
- `05_章节节奏.json`
- `06_可复用模式.json`

## 11. 超长文本分批建议

- 1-80 章：每 20-30 章一批
- 80-200 章：每 25-40 章一批
- 200+ 章：优先抽样，不建议一次性全量细拆

批次数应回写到 `study_meta.json.batch_count`。

## 12. 失败判据

出现以下任一情况，应阻断整本分析：
- `text_quality = D`
- 无法稳定识别章节边界
- 编码损坏导致大面积缺字
- 正文与杂质混杂到无法切分
- EPUB 连可用目录/标题都拿不到

## 13. 恢复策略

- 章索引失败：只重跑 `study prepare`
- 文本清洗失败：保留现有缓存，提示用户提供更干净版本
- 章节缺失：在 `study_meta.json.warnings` 标明缺口，继续分析已识别章节
- 模式桥接失败：只重跑 `study bridge-memory`
- 文件校验失败：只重跑 `study verify` 或补缺文件
