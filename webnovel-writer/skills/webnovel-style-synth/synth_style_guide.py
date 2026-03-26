#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
参考拆书风格综合指南生成器

从项目的 参考拆书/ 目录中提取文笔风格信息，
综合分析多本参考书的写作特点，整合成适合当前项目的风格指南。
"""

import os
import re
import json
from pathlib import Path
from typing import Dict, List, Any
from collections import defaultdict


class StyleSynthesizer:
    """风格综合分析器"""

    def __init__(self, project_root: str, source_dir: str = "参考拆书"):
        self.project_root = Path(project_root)
        self.source_dir = self.project_root / source_dir
        self.output_file = self.project_root / "设定集" / "参考拆书综合风格指南.md"

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

    def read_style_file(self, book_name: str) -> Dict[str, Any]:
        """读取单本拆书的文笔风格文件"""
        style_file = self.source_dir / book_name / "03_文笔风格.md"
        overview_file = self.source_dir / book_name / "00_总览.md"

        data = {
            "name": book_name,
            "style_content": "",
            "overview": "",
            "features": {}
        }

        if style_file.exists():
            with open(style_file, 'r', encoding='utf-8') as f:
                data["style_content"] = f.read()

        if overview_file.exists():
            with open(overview_file, 'r', encoding='utf-8') as f:
                data["overview"] = f.read()

        return data

    def extract_features(self, content: str) -> Dict[str, Any]:
        """从文笔风格文件中提取特征"""
        features = {
            "sentence_length": [],
            "paragraph_length": [],
            "dialogue_ratio": [],
            "action_ratio": [],
            "patterns": []
        }

        # 提取句长信息
        sentence_match = re.search(r'平均句长[：:]\s*约\s*(\d+[-~到]\d*)\s*字', content)
        if sentence_match:
            features["sentence_length"].append(sentence_match.group(1))

        # 提取段长信息
        paragraph_match = re.search(r'平均段长[：:]\s*约\s*(\d+[-~到]\d*)\s*字', content)
        if paragraph_match:
            features["paragraph_length"].append(paragraph_match.group(1))

        # 提取对白占比
        dialogue_match = re.search(r'对白占比[：:]\s*约\s*(\d+[-~到]\d*)\s*%', content)
        if dialogue_match:
            features["dialogue_ratio"].append(dialogue_match.group(1))

        # 提取动作描写占比
        action_match = re.search(r'动作描写[（(](约\s*)?(\d+)%[）)]', content)
        if action_match:
            features["action_ratio"].append(action_match.group(2))

        # 提取风格特征关键词
        if "短句" in content:
            features["patterns"].append("短句为主")
        if "对话" in content:
            features["patterns"].append("对话丰富")
        if "动作" in content:
            features["patterns"].append("动作密集")
        if "心理" in content:
            features["patterns"].append("心理描写")

        return features

    def analyze_all(self) -> None:
        """分析所有拆书"""
        books = self.collect_books()

        print(f"找到 {len(books)} 本拆书:")
        for book in books:
            print(f"  - {book}")

        for book in books:
            print(f"分析 {book}...")
            data = self.read_style_file(book)
            if data["style_content"]:
                data["features"] = self.extract_features(data["style_content"])
            self.style_data[book] = data

    def generate_guide(self) -> str:
        """生成风格指南"""
        lines = []

        # 标题
        lines.append("# 参考拆书综合风格指南\n")
        lines.append("> 本文件由 `webnovel-style-synth` 自动生成，综合分析了项目中所有参考拆书的文笔风格。\n")
        lines.append("---\n")

        # 参考书目
        lines.append("## 参考书目\n")
        for book_name in sorted(self.style_data.keys()):
            data = self.style_data[book_name]
            lines.append(f"### {book_name}")

            # 从总览中提取基本信息
            if data["overview"]:
                # 提取类型、题材等信息
                type_match = re.search(r'类型[：:]\s*([^\n]+)', data["overview"])
                if type_match:
                    lines.append(f"- **类型**: {type_match.group(1)}")

                genre_match = re.search(r'题材[：:]\s*([^\n]+)', data["overview"])
                if genre_match:
                    lines.append(f"- **题材**: {genre_match.group(1)}")

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
        for book_name, data in self.style_data.items():
            if data["features"].get("dialogue_ratio"):
                dialogue_ratios.append((book_name, data["features"]["dialogue_ratio"][0]))

        if dialogue_ratios:
            lines.append("**对白占比**: " + "、".join([f"{book}({ratio}%)" for book, ratio in dialogue_ratios]) + "\n")

        lines.append("")

        # 动作描写
        lines.append("### 描写特点\n")
        action_ratios = []
        for book_name, data in self.style_data.items():
            if data["features"].get("action_ratio"):
                action_ratios.append((book_name, data["features"]["action_ratio"][0]))

        if action_ratios:
            lines.append("**动作描写占比**: " + "、".join([f"{book}({ratio}%)" for book, ratio in action_ratios]) + "\n")

        lines.append("")

        # 详细分析每本书
        lines.append("## 各书详细特征\n")
        for book_name in sorted(self.style_data.keys()):
            data = self.style_data[book_name]
            if not data["style_content"]:
                continue

            lines.append(f"### {book_name}\n")

            # 提取关键章节
            content = data["style_content"]

            # 提取句长段长倾向
            if "句长与段长倾向" in content or "句长特征" in content:
                lines.append("#### 句式特征\n")
                # 简化处理，直接摘录部分内容
                lines.extend(self._extract_section(content, ["句长特征", "句式特点", "句长与段长倾向"]))
                lines.append("")

            # 提取对白特征
            if "对白" in content:
                lines.append("#### 对白特征\n")
                lines.extend(self._extract_section(content, ["对白特点", "对白比例趋势", "对白特征"]))
                lines.append("")

            # 提取动作描写
            if "动作描写" in content:
                lines.append("#### 动作描写\n")
                lines.extend(self._extract_section(content, ["动作描写", "动作/心理/说明占比"]))
                lines.append("")

        # 可复用模式
        lines.append("## 可复用模式建议\n")
        lines.append("基于以上分析，以下是推荐的写作模式：\n")

        lines.append("### 开头模式")
        lines.append("- 快速进入场景，避免长篇背景铺陈")
        lines.append("- 从动作或对话开始，吸引读者注意力\n")

        lines.append("### 对话模式")
        lines.append("- 对话要推动剧情，不要为了对话而对话")
        lines.append("- 每句对话都应该有目的：试探、施压、回避、诱导等")
        lines.append("- 允许自然口语，不必过于书面化\n")

        lines.append("### 动作描写模式")
        lines.append("- 动作要具体，避免笼统描述")
        lines.append("- 用动作暗示心理和情绪")
        lines.append("- 动作链要清晰：拿起→转身→走过去\n")

        lines.append("")

        # 避坑指南
        lines.append("## 避坑指南\n")
        lines.append("根据拆书分析，以下是需要避免的问题：\n")
        lines.append("- 避免大段纯说明，信息要融入动作和对话")
        lines.append("- 避免机械的三段式结构（首先、其次、最后）")
        lines.append("- 避免所有角色说话一个口气")
        lines.append("- 避免过度修饰，多用动词少用形容词\n")

        lines.append("")

        # 项目适配建议
        lines.append("## 项目适配建议\n")
        lines.append("结合当前项目特点，建议：\n")
        lines.append("1. **重点参考**：选择与当前项目题材最接近的拆书作为主要参考")
        lines.append("2. **风格融合**：从多本拆书中提取优点，融合成自己的风格")
        lines.append("3. **本地化**：将参考风格与项目已有的 `设定集/写作风格.md` 结合")
        lines.append("4. **持续优化**：根据写作实际情况，不断调整和优化风格指南\n")

        lines.append("---\n")
        lines.append("*本文件由工具自动生成，请根据项目实际情况进行调整和完善。*")

        return "\n".join(lines)

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

    def run(self) -> None:
        """执行完整的分析流程"""
        print("开始分析参考拆书...")

        self.analyze_all()

        print("\n生成风格指南...")
        guide_content = self.generate_guide()

        self.save_guide(guide_content)

        print("\n完成!")


def main():
    import argparse

    parser = argparse.ArgumentParser(description="参考拆书风格综合指南生成器")
    parser.add_argument("--project-root", default=".", help="项目根目录")
    parser.add_argument("--source-dir", default="参考拆书", help="拆书目录名称")

    args = parser.parse_args()

    synthesizer = StyleSynthesizer(
        project_root=args.project_root,
        source_dir=args.source_dir
    )

    synthesizer.run()


if __name__ == "__main__":
    main()
