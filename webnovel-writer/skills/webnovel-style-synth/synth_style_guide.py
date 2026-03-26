#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
参考拆书风格综合指南生成器

从项目的 参考拆书/ 目录中提取文笔风格信息，
综合分析多本参考书的写作特点，整合成适合当前项目的风格指南。

支持策略同步：
- append: 追加模式 - 在现有内容后添加新内容
- merge: 合并模式 - 智能合并现有和新内容
- replace: 替换模式 - 完全替换特定章节
"""

import os
import re
import json
from pathlib import Path
from typing import Dict, List, Any, Optional
from collections import defaultdict
from datetime import datetime


class StyleSynthesizer:
    """风格综合分析器"""

    def __init__(self, project_root: str, source_dir: str = "参考拆书"):
        self.project_root = Path(project_root)
        self.source_dir = self.project_root / source_dir
        self.output_file = self.project_root / "设定集" / "参考拆书综合风格指南.md"

        # 目标文件路径
        self.preferences_file = self.project_root / ".webnovel" / "preferences.json"
        self.writing_style_file = self.project_root / "设定集" / "写作风格.md"
        self.style_contract_file = self.project_root / "设定集" / "风格契约.md"

        # 存储所有拆书数据
        self.style_data: Dict[str, Dict] = {}

    def collect_books(self) -> List[str]:
        """收集所有拆书目录"""
        if not self.source_dir.exists():
            raise FileNotFoundError(f"拆书目录不存在: {self.source_dir}")

        books = []
        for item in self.source_dir.iterdir():
            if item.is_dir() and not item.name.startswith('.'):
                books.append(item.name)

        return sorted(books)

    def read_all_files(self, book_name: str) -> Dict[str, Any]:
        """读取单本拆书的所有分析文件"""
        data = {
            "name": book_name,
            "overview": "",
            "plot_structure": "",
            "character_features": "",
            "style_content": "",
            "common_phrases": "",
            "features": {}
        }

        # 定义文件映射
        file_mapping = {
            "00_总览.md": "overview",
            "01_剧情结构.md": "plot_structure",
            "02_人物特点.md": "character_features",
            "03_文笔风格.md": "style_content",
            "04_常用词句.md": "common_phrases"
        }

        book_dir = self.source_dir / book_name
        for filename, key in file_mapping.items():
            file_path = book_dir / filename
            if file_path.exists():
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        data[key] = f.read()
                except Exception as e:
                    print(f"  警告: 读取 {filename} 失败: {e}")

        return data

    def extract_all_features(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """从所有文件中提取特征"""
        features = {
            # 从00_总览提取
            "genre": [],
            "type": [],
            "target_reader": [],

            # 从01_剧情结构提取
            "opening_hooks": [],
            "plot_structure": [],
            "pacing_pattern": [],
            "arc_types": [],

            # 从02_人物特点提取
            "protagonist_traits": [],
            "dialogue_style": [],
            "character_functions": [],

            # 从03_文笔风格提取
            "sentence_length": [],
            "paragraph_length": [],
            "dialogue_ratio": [],
            "action_ratio": [],
            "psychology_ratio": [],
            "patterns": [],

            # 从04_常用词句提取
            "high_freq_verbs": [],
            "common_images": [],
            "sentence_patterns": []
        }

        # 从00_总览提取基本信息
        if data["overview"]:
            # 提取类型
            type_match = re.search(r'类型[：:]\s*([^\n]+)', data["overview"])
            if type_match:
                features["type"].append(type_match.group(1).strip())

            # 提取题材
            genre_match = re.search(r'题材[：:]\s*([^\n]+)', data["overview"])
            if genre_match:
                features["genre"].append(genre_match.group(1).strip())

            # 提取目标读者
            reader_match = re.search(r'目标读者[：:]\s*([^\n]+)', data["overview"])
            if reader_match:
                features["target_reader"].append(reader_match.group(1).strip())

        # 从01_剧情结构提取特征
        if data["plot_structure"]:
            # 提取开篇钩子类型
            hook_types = re.findall(r'钩子类型[：:]\s*([^\n]+)', data["plot_structure"])
            features["opening_hooks"].extend(hook_types)

            # 提取节奏模式
            if "螺旋上升" in data["plot_structure"]:
                features["pacing_pattern"].append("螺旋上升")
            if "三幕式" in data["plot_structure"]:
                features["pacing_pattern"].append("三幕式")
            if "闭环" in data["plot_structure"]:
                features["arc_types"].append("闭环式")

        # 从02_人物特点提取特征
        if data["character_features"]:
            # 提取主角特点
            protagonist_section = re.search(r'## 主角.*?(?=\n##|\Z)', data["character_features"], re.DOTALL)
            if protagonist_section:
                # 提取核心卖点
                selling_points = re.findall(r'核心卖点|卖点|特点.*?[:：]\s*([^\n]+)', data["character_features"])
                features["protagonist_traits"].extend(selling_points[:3])  # 只取前3个

            # 提取对话风格相关
            if "对话" in data["character_features"] or "对白" in data["character_features"]:
                features["dialogue_style"].append("有明确对话风格")

        # 从03_文笔风格提取特征
        if data["style_content"]:
            # 提取句长信息
            sentence_match = re.search(r'平均句长[：:]\s*约\s*(\d+[-~到]\d*)\s*字', data["style_content"])
            if sentence_match:
                features["sentence_length"].append(sentence_match.group(1))

            # 提取段长信息
            paragraph_match = re.search(r'平均段长[：:]\s*约\s*(\d+[-~到]\d*)\s*字', data["style_content"])
            if paragraph_match:
                features["paragraph_length"].append(paragraph_match.group(1))

            # 提取对白占比
            dialogue_match = re.search(r'对白占比[：:]\s*约\s*(\d+[-~到]\d*)\s*%', data["style_content"])
            if dialogue_match:
                features["dialogue_ratio"].append(dialogue_match.group(1))

            # 提取动作描写占比
            action_match = re.search(r'动作描写[（(](约\s*)?(\d+)%[）)]', data["style_content"])
            if action_match:
                features["action_ratio"].append(action_match.group(2))

            # 提取心理描写占比
            psych_match = re.search(r'心理描写[（(](约\s*)?(\d+)%[）)]', data["style_content"])
            if psych_match:
                features["psychology_ratio"].append(psych_match.group(2))

            # 提取风格特征关键词
            if "短句" in data["style_content"]:
                features["patterns"].append("短句为主")
            if "对话" in data["style_content"]:
                features["patterns"].append("对话丰富")
            if "动作" in data["style_content"]:
                features["patterns"].append("动作密集")
            if "心理" in data["style_content"]:
                features["patterns"].append("心理描写")

        # 从04_常用词句提取特征
        if data["common_phrases"]:
            # 提取高频动词
            verb_section = re.search(r'## 高频动词.*?(?=\n##|\Z)', data["common_phrases"], re.DOTALL)
            if verb_section:
                verbs = re.findall(r'[\u4e00-\u9fff]+', verb_section.group())
                features["high_freq_verbs"].extend(verbs[:10])  # 取前10个

            # 提取常见意象
            if "意象" in data["common_phrases"]:
                features["common_images"].append("有意象运用")

            # 提取句式特点
            if "三字短句" in data["common_phrases"]:
                features["sentence_patterns"].append("三字短句")
            if "对话短句" in data["common_phrases"]:
                features["sentence_patterns"].append("对话短句")

        return features

    def analyze_all(self) -> None:
        """分析所有拆书"""
        books = self.collect_books()

        print(f"找到 {len(books)} 本拆书:")
        for book in books:
            print(f"  - {book}")

        for book in books:
            print(f"分析 {book}...")
            data = self.read_all_files(book)
            data["features"] = self.extract_all_features(data)
            self.style_data[book] = data

    def generate_guide(self) -> str:
        """生成风格指南"""
        lines = []

        # 标题
        lines.append("# 参考拆书综合风格指南\n")
        lines.append("> 本文件由 `webnovel-style-synth` 自动生成，综合分析了项目中所有参考拆书的文笔风格。\n")
        lines.append(f"> 生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        lines.append("---\n")

        # 参考书目
        lines.append("## 参考书目\n")
        for book_name in sorted(self.style_data.keys()):
            data = self.style_data[book_name]
            lines.append(f"### {book_name}")

            # 从总览中提取基本信息
            if data["overview"]:
                type_match = re.search(r'类型[：:]\s*([^\n]+)', data["overview"])
                if type_match:
                    lines.append(f"- **类型**: {type_match.group(1)}")

                genre_match = re.search(r'题材[：:]\s*([^\n]+)', data["overview"])
                if genre_match:
                    lines.append(f"- **题材**: {genre_match.group(1)}")

            lines.append("")

        # 题材与类型分析
        lines.append("## 题材与类型分布\n")

        # 统计类型
        type_count = defaultdict(int)
        for data in self.style_data.values():
            for t in data["features"].get("type", []):
                type_count[t] += 1

        if type_count:
            lines.append("**类型分布**:\n")
            for t, count in sorted(type_count.items(), key=lambda x: -x[1]):
                lines.append(f"- {t} ({count}本)")
            lines.append("")

        # 统计题材
        genre_count = defaultdict(int)
        for data in self.style_data.values():
            for g in data["features"].get("genre", []):
                genre_count[g] += 1

        if genre_count:
            lines.append("**题材分布**:\n")
            for g, count in sorted(genre_count.items(), key=lambda x: -x[1]):
                lines.append(f"- {g} ({count}本)")
            lines.append("")

        # 开篇钩子分析
        lines.append("## 开篇钩子分析\n")

        hook_types = defaultdict(int)
        for data in self.style_data.values():
            for hook in data["features"].get("opening_hooks", []):
                hook_types[hook] += 1

        if hook_types:
            lines.append("**常见钩子类型**:\n")
            for hook, count in sorted(hook_types.items(), key=lambda x: -x[1]):
                lines.append(f"- {hook} ({count}本)")
            lines.append("")

        # 节奏模式分析
        lines.append("## 节奏与结构特点\n")

        pacing_patterns = defaultdict(int)
        for data in self.style_data.values():
            for pattern in data["features"].get("pacing_pattern", []):
                pacing_patterns[pattern] += 1

        if pacing_patterns:
            lines.append("**节奏模式**:\n")
            for pattern, count in sorted(pacing_patterns.items(), key=lambda x: -x[1]):
                lines.append(f"- {pattern} ({count}本)")
            lines.append("")

        # 共性风格特征
        lines.append("## 共性风格特征\n")

        # 句式特征
        lines.append("### 句式与段落\n")
        all_sentence_lengths = []
        all_paragraph_lengths = []

        for book_name, data in self.style_data.items():
            if data["features"].get("sentence_length"):
                all_sentence_lengths.extend(data["features"]["sentence_length"])
            if data["features"].get("paragraph_length"):
                all_paragraph_lengths.extend(data["features"]["paragraph_length"])

        if all_sentence_lengths:
            lines.append("**句长范围**: " + "、".join(set(all_sentence_lengths)) + " 字\n")

        if all_paragraph_lengths:
            lines.append("**段长范围**: " + "、".join(set(all_paragraph_lengths)) + " 字\n")

        # 统计常见模式
        pattern_count = defaultdict(int)
        for data in self.style_data.values():
            for pattern in data["features"].get("patterns", []):
                pattern_count[pattern] += 1

        if pattern_count:
            lines.append("**常见特征**:\n")
            for pattern, count in sorted(pattern_count.items(), key=lambda x: -x[1]):
                if count >= 2:  # 至少2本书才有共性
                    lines.append(f"- {pattern} ({count}本)")

        lines.append("")

        # 对白特征
        lines.append("### 对白特点\n")

        dialogue_ratios = []
        dialogue_styles = []

        for book_name, data in self.style_data.items():
            if data["features"].get("dialogue_ratio"):
                dialogue_ratios.append((book_name, data["features"]["dialogue_ratio"][0]))
            if data["features"].get("dialogue_style"):
                dialogue_styles.extend(data["features"]["dialogue_style"])

        if dialogue_ratios:
            lines.append("**对白占比**: " + "、".join([f"{book}({ratio}%)" for book, ratio in dialogue_ratios]) + "\n")

        if dialogue_styles:
            lines.append("**对话风格**: " + "、".join(set(dialogue_styles)) + "\n")

        lines.append("")

        # 描写特点
        lines.append("### 描写特点\n")

        action_ratios = []
        psychology_ratios = []

        for book_name, data in self.style_data.items():
            if data["features"].get("action_ratio"):
                action_ratios.append((book_name, data["features"]["action_ratio"][0]))
            if data["features"].get("psychology_ratio"):
                psychology_ratios.append((book_name, data["features"]["psychology_ratio"][0]))

        if action_ratios:
            lines.append("**动作描写占比**: " + "、".join([f"{book}({ratio}%)" for book, ratio in action_ratios]) + "\n")

        if psychology_ratios:
            lines.append("**心理描写占比**: " + "、".join([f"{book}({ratio}%)" for book, ratio in psychology_ratios]) + "\n")

        lines.append("")

        # 句式分析
        lines.append("### 句式与用词\n")

        sentence_patterns = defaultdict(int)
        for data in self.style_data.values():
            for pattern in data["features"].get("sentence_patterns", []):
                sentence_patterns[pattern] += 1

        if sentence_patterns:
            lines.append("**常见句式**:\n")
            for pattern, count in sorted(sentence_patterns.items(), key=lambda x: -x[1]):
                if count >= 2:
                    lines.append(f"- {pattern} ({count}本)")
            lines.append("")

        # 各书详细特征
        lines.append("## 各书详细特征\n")
        for book_name in sorted(self.style_data.keys()):
            data = self.style_data[book_name]
            lines.append(f"### {book_name}\n")

            # 剧情结构亮点
            if data["plot_structure"]:
                lines.append("#### 剧情结构\n")
                # 提取关键信息
                if "开篇" in data["plot_structure"]:
                    lines.append("- " + self._extract_first_line(data["plot_structure"], "开篇"))
                if "主线" in data["plot_structure"]:
                    lines.append("- " + self._extract_first_line(data["plot_structure"], "主线"))
                if "反派" in data["plot_structure"]:
                    lines.append("- " + self._extract_first_line(data["plot_structure"], "反派"))
                lines.append("")

            # 人物特点
            if data["character_features"]:
                lines.append("#### 人物特点\n")
                if "主角" in data["character_features"]:
                    lines.append("- " + self._extract_first_line(data["character_features"], "主角"))
                if "配角" in data["character_features"]:
                    lines.append("- " + self._extract_first_line(data["character_features"], "配角"))
                lines.append("")

            # 文笔风格
            if data["style_content"]:
                lines.append("#### 文笔风格\n")
                lines.extend(self._extract_section(data["style_content"], ["句长特征", "句式特点", "句长与段长倾向"]))
                lines.append("")

            # 常用词句
            if data["common_phrases"]:
                lines.append("#### 常用词句\n")
                lines.extend(self._extract_section(data["common_phrases"], ["高频动词", "常见句式", "意象"]))
                lines.append("")

        # 可复用模式建议
        lines.append("## 可复用模式建议\n")
        lines.append("基于以上分析，以下是推荐的写作模式：\n")

        lines.append("### 开头模式\n")
        common_hooks = list(hook_types.keys())[:3]
        if common_hooks:
            for hook in common_hooks:
                lines.append(f"- 优先使用 {hook} 作为开篇钩子")
        lines.append("- 快速进入场景，避免长篇背景铺陈")
        lines.append("- 从动作或对话开始，吸引读者注意力\n")

        lines.append("### 对话模式\n")
        lines.append("- 对话要推动剧情，不要为了对话而对话")
        lines.append("- 每句对话都应该有目的：试探、施压、回避、诱导等")
        lines.append("- 允许自然口语，不必过于书面化")

        if dialogue_styles:
            lines.append(f"- 参考风格：{', '.join(set(dialogue_styles))}\n")

        lines.append("### 动作描写模式\n")
        lines.append("- 动作要具体，避免笼统描述")
        lines.append("- 用动作暗示心理和情绪")
        lines.append("- 动作链要清晰：拿起→转身→走过去\n")

        lines.append("### 节奏模式\n")
        if pacing_patterns:
            lines.append(f"- 推荐节奏：{', '.join(set(pacing_patterns.keys()))}\n")
        lines.append("- 每3-5章完成一个小闭环")
        lines.append("- 章节之间要有压力递进\n")

        # 避坑指南
        lines.append("## 避坑指南\n")
        lines.append("根据拆书分析，以下是需要避免的问题：\n")
        lines.append("- 避免大段纯说明，信息要融入动作和对话")
        lines.append("- 避免机械的三段式结构（首先、其次、最后）")
        lines.append("- 避免所有角色说话一个口气")
        lines.append("- 避免过度修饰，多用动词少用形容词")
        lines.append("- 避免主角性格单薄，要有成长弧光")
        lines.append("- 避免配角工具化，要有独立动机\n")

        # 项目适配建议
        lines.append("## 项目适配建议\n")
        lines.append("结合当前项目特点，建议：\n")
        lines.append("1. **重点参考**：选择与当前项目题材最接近的拆书作为主要参考")
        lines.append("2. **风格融合**：从多本拆书中提取优点，融合成自己的风格")
        lines.append("3. **本地化**：将参考风格与项目已有的 `设定集/写作风格.md` 结合")
        lines.append("4. **持续优化**：根据写作实际情况，不断调整和优化风格指南")

        if type_count:
            top_type = sorted(type_count.items(), key=lambda x: -x[1])[0][0]
            lines.append(f"5. **类型侧重**：本项目属于{top_type}类型，重点参考同类拆书")

        lines.append("")

        lines.append("---\n")
        lines.append("*本文件由工具自动生成，请根据项目实际情况进行调整和完善。*")

        return "\n".join(lines)

    def _extract_first_line(self, content: str, keyword: str) -> str:
        """提取包含关键词的第一行"""
        for line in content.split("\n"):
            if keyword in line:
                # 清理格式
                cleaned = re.sub(r'^#+\s*', '', line.strip())
                if cleaned and len(cleaned) > 3:
                    return cleaned
        return f"(详见{keyword}相关内容)"

    def _extract_section(self, content: str, keywords: List[str]) -> List[str]:
        """提取特定章节的内容"""
        lines = []
        content_lower = content.lower()

        for keyword in keywords:
            if keyword in content or keyword.lower() in content_lower:
                # 简化处理：提取包含该关键词的段落
                for line in content.split("\n"):
                    if keyword in line or (len(keyword) > 2 and keyword.lower() in line.lower()):
                        # 清理格式
                        cleaned = re.sub(r'^#+\s*', '', line.strip())
                        if cleaned and len(cleaned) > 5:
                            lines.append(f"- {cleaned}")
                break

        if not lines:
            lines.append("- (详见原拆书文件)")

        return lines

    def save_guide(self, content: str) -> None:
        """保存风格指南"""
        self.output_file.parent.mkdir(parents=True, exist_ok=True)

        with open(self.output_file, 'w', encoding='utf-8') as f:
            f.write(content)

        print(f"\n风格指南已生成: {self.output_file}")

    # ========== 策略同步功能 ==========

    def sync_to_preferences(self, strategy: str = "merge") -> None:
        """同步到 .webnovel/preferences.json"""
        print(f"\n同步到 .webnovel/preferences.json (策略: {strategy})")

        # 读取现有配置
        existing_prefs = {}
        if self.preferences_file.exists():
            with open(self.preferences_file, 'r', encoding='utf-8') as f:
                existing_prefs = json.load(f)

        # 生成新的风格配置
        new_prefs = self._generate_preferences_content()

        if strategy == "replace":
            # 替换模式：完全替换风格相关字段
            merged_prefs = {**existing_prefs, **new_prefs}
        elif strategy == "append":
            # 追加模式：保留现有，追加新字段
            merged_prefs = existing_prefs.copy()
            for key, value in new_prefs.items():
                if key not in merged_prefs:
                    merged_prefs[key] = value
                else:
                    # 对于嵌套字段，进行追加
                    if isinstance(value, dict) and isinstance(merged_prefs.get(key), dict):
                        merged_prefs[key].update(value)
        else:  # merge
            # 合并模式：智能合并
            merged_prefs = self._merge_preferences(existing_prefs, new_prefs)

        # 保存
        self.preferences_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.preferences_file, 'w', encoding='utf-8') as f:
            json.dump(merged_prefs, f, ensure_ascii=False, indent=2)

        print(f"✓ 已同步到 {self.preferences_file}")

    def sync_to_writing_style(self, strategy: str = "append") -> None:
        """同步到 设定集/写作风格.md"""
        print(f"\n同步到 设定集/写作风格.md (策略: {strategy})")

        # 生成新的风格内容
        new_content = self._generate_writing_style_content()

        if not self.writing_style_file.exists():
            # 文件不存在，直接创建
            with open(self.writing_style_file, 'w', encoding='utf-8') as f:
                f.write(new_content)
            print(f"✓ 已创建 {self.writing_style_file}")
            return

        # 读取现有内容
        with open(self.writing_style_file, 'r', encoding='utf-8') as f:
            existing_content = f.read()

        if strategy == "replace":
            # 替换模式：完全替换
            final_content = new_content
        elif strategy == "append":
            # 追加模式：在现有内容后追加
            final_content = existing_content + "\n\n" + new_content
        else:  # merge
            # 合并模式：智能合并（这里简化为追加，保留原有）
            final_content = existing_content + "\n\n" + new_content

        # 保存
        with open(self.writing_style_file, 'w', encoding='utf-8') as f:
            f.write(final_content)

        print(f"✓ 已同步到 {self.writing_style_file}")

    def sync_to_style_contract(self, strategy: str = "replace") -> None:
        """同步到 设定集/风格契约.md"""
        print(f"\n同步到 设定集/风格契约.md (策略: {strategy})")

        # 生成新的契约内容
        new_content = self._generate_style_contract_content()

        if not self.style_contract_file.exists():
            # 文件不存在，直接创建
            with open(self.style_contract_file, 'w', encoding='utf-8') as f:
                f.write(new_content)
            print(f"✓ 已创建 {self.style_contract_file}")
            return

        # 读取现有内容
        with open(self.style_contract_file, 'r', encoding='utf-8') as f:
            existing_content = f.read()

        if strategy == "replace":
            # 替换模式：完全替换
            final_content = new_content
        elif strategy == "append":
            # 追加模式：在现有内容后追加
            final_content = existing_content + "\n\n" + new_content
        else:  # merge
            # 合并模式：保留现有，在指定位置插入
            # 这里简化为追加，保留原有内容
            final_content = existing_content + "\n\n" + new_content

        # 保存
        with open(self.style_contract_file, 'w', encoding='utf-8') as f:
            f.write(final_content)

        print(f"✓ 已同步到 {self.style_contract_file}")

    def _generate_preferences_content(self) -> Dict:
        """生成 preferences.json 内容"""
        # 统计共性特征
        pattern_count = defaultdict(int)
        for data in self.style_data.values():
            for pattern in data["features"].get("patterns", []):
                pattern_count[pattern] += 1

        # 统计句长
        all_sentence_lengths = []
        for data in self.style_data.values():
            all_sentence_lengths.extend(data["features"].get("sentence_length", []))

        # 统计对白占比
        dialogue_ratios = []
        for data in self.style_data.values():
            dialogue_ratios.extend(data["features"].get("dialogue_ratio", []))

        return {
            "tone": "基于参考拆书综合分析",
            "style": {
                "sentence_rhythm": f"参考句长范围: {'、'.join(set(all_sentence_lengths))}字" if all_sentence_lengths else "自然节奏",
                "dialogue_ratio_avg": f"{sum(map(int, dialogue_ratios)) // len(dialogue_ratios)}%" if dialogue_ratios else "待统计",
                "common_patterns": [p for p, c in pattern_count.items() if c >= 2]
            },
            "source": "webnovel-style-synth 自动生成",
            "generated_at": datetime.now().isoformat()
        }

    def _merge_preferences(self, existing: Dict, new: Dict) -> Dict:
        """合并 preferences 配置"""
        merged = existing.copy()

        # 合并 style 字段
        if "style" in new:
            if "style" not in merged:
                merged["style"] = {}
            merged["style"].update(new["style"])

        # 保留其他新字段
        for key, value in new.items():
            if key not in merged:
                merged[key] = value

        return merged

    def _generate_writing_style_content(self) -> str:
        """生成写作风格内容"""
        lines = []

        lines.append("## 参考拆书综合风格补充\n")
        lines.append(f"> 本节由 `webnovel-style-synth` 自动生成，基于 {len(self.style_data)} 本参考拆书的综合分析。\n")
        lines.append(f"> 生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        lines.append("---\n")

        # 统计共性特征
        pattern_count = defaultdict(int)
        for data in self.style_data.values():
            for pattern in data["features"].get("patterns", []):
                pattern_count[pattern] += 1

        lines.append("### 共性风格特征\n")
        if pattern_count:
            lines.append("**高频特征** (出现2次以上):\n")
            for pattern, count in sorted(pattern_count.items(), key=lambda x: -x[1]):
                if count >= 2:
                    lines.append(f"- {pattern}: {count}本拆书")
            lines.append("")

        # 题材特点
        lines.append("### 题材与类型特点\n")
        type_count = defaultdict(int)
        genre_count = defaultdict(int)
        for data in self.style_data.values():
            for t in data["features"].get("type", []):
                type_count[t] += 1
            for g in data["features"].get("genre", []):
                genre_count[g] += 1

        if type_count:
            lines.append("**主要类型**:\n")
            for t, count in sorted(type_count.items(), key=lambda x: -x[1]):
                lines.append(f"- {t}: {count}本")
            lines.append("")

        if genre_count:
            lines.append("**主要题材**:\n")
            for g, count in sorted(genre_count.items(), key=lambda x: -x[1]):
                lines.append(f"- {g}: {count}本")
            lines.append("")

        # 句式建议
        lines.append("### 句式建议\n")
        lines.append("- 句子长短服从自然口气，不机械切短也不故意拉长")
        lines.append("- 判断标准：念出来是否顺口")
        lines.append("- 区分'自然短句'（15-30字，有停顿感）和'碎句'（5字内超短句连续3个以上）")
        lines.append("- 允许自然短句存在，只有后者才需要合并\n")

        # 对白建议
        lines.append("### 对白建议\n")
        lines.append("- 对话要推动剧情，不要为了对话而对话")
        lines.append("- 每句对话都应该有目的：试探、施压、回避、诱导等")
        lines.append("- 允许自然口语，不必过于书面化")
        lines.append("- 不同身份的人要有不同口气\n")

        return "\n".join(lines)

    def _generate_style_contract_content(self) -> str:
        """生成风格契约内容"""
        lines = []

        lines.append("## 参考拆书风格约束补充\n")
        lines.append(f"> 本节由 `webnovel-style-synth` 自动生成，基于 {len(self.style_data)} 本参考拆书的综合分析。\n")
        lines.append(f"> 生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        lines.append("---\n")

        # 统计特征
        pattern_count = defaultdict(int)
        for data in self.style_data.values():
            for pattern in data["features"].get("patterns", []):
                pattern_count[pattern] += 1

        lines.append("### 参考拆书共性约束\n")
        if pattern_count:
            lines.append("**高频特征**:\n")
            for pattern, count in sorted(pattern_count.items(), key=lambda x: -x[1]):
                if count >= 2:
                    lines.append(f"- **{pattern}**: {count}本拆书推荐")
            lines.append("")

        lines.append("### 基于参考拆书的硬约束\n")
        lines.append("- 句子长短服从自然口气，不机械切短也不故意拉长")
        lines.append("- 动作描写要具体，避免笼统描述")
        lines.append("- 用动作暗示心理和情绪")
        lines.append("- 对话要推动剧情，不要为了对话而对话")
        lines.append("- 不同身份的人要有不同口气")
        lines.append("- 避免机械的三段式结构（首先、其次、最后）")
        lines.append("- 避免过度修饰，多用动词少用形容词\n")

        return "\n".join(lines)

    def run(self, strategy: str = "none", target: str = "none") -> None:
        """执行完整的分析流程"""
        print("开始分析参考拆书...")

        self.analyze_all()

        print("\n生成风格指南...")
        guide_content = self.generate_guide()
        self.save_guide(guide_content)

        # 策略同步
        if target != "none":
            if target in ["preferences", "all"]:
                self.sync_to_preferences(strategy)
            if target in ["style", "all"]:
                self.sync_to_writing_style(strategy)
            if target in ["contract", "all"]:
                self.sync_to_style_contract(strategy)

        print("\n完成!")


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="参考拆书风格综合指南生成器",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
策略说明:
  append   追加模式 - 在现有内容后添加新内容
  merge    合并模式 - 智能合并现有和新内容
  replace  替换模式 - 完全替换特定章节

目标说明:
  preferences  同步到 .webnovel/preferences.json
  style        同步到 设定集/写作风格.md
  contract     同步到 设定集/风格契约.md
  all          同步到所有文件

示例:
  # 只生成风格指南
  python3 synth_style_guide.py --project-root .

  # 追加到写作风格
  python3 synth_style_guide.py --project-root . --strategy append --target style

  # 合并到所有文件
  python3 synth_style_guide.py --project-root . --strategy merge --target all

  # 替换风格契约
  python3 synth_style_guide.py --project-root . --strategy replace --target contract
        """
    )

    parser.add_argument("--project-root", default=".", help="项目根目录")
    parser.add_argument("--source-dir", default="参考拆书", help="拆书目录名称")
    parser.add_argument("--strategy", choices=["append", "merge", "replace", "none"], default="none",
                        help="同步策略 (默认: none 不进行同步)")
    parser.add_argument("--target", choices=["preferences", "style", "contract", "all"], default="none",
                        help="同步目标 (默认: none 不进行同步)")

    args = parser.parse_args()

    synthesizer = StyleSynthesizer(
        project_root=args.project_root,
        source_dir=args.source_dir
    )

    synthesizer.run(strategy=args.strategy, target=args.target)


if __name__ == "__main__":
    main()
