#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ContextManager - assemble context packs with weighted priorities.
"""
from __future__ import annotations

import hashlib
import json
import re
import sys
import logging
from pathlib import Path

from runtime_compat import enable_windows_utf8_stdio
from typing import Any, Dict, List, Optional

try:
    from chapter_outline_loader import load_chapter_outline
except ImportError:  # pragma: no cover
    from scripts.chapter_outline_loader import load_chapter_outline

from .config import get_config
from .index_manager import IndexManager, WritingChecklistScoreMeta
from .context_ranker import ContextRanker
from .snapshot_manager import SnapshotManager, SnapshotVersionMismatch
from .context_weights import (
    DEFAULT_TEMPLATE as CONTEXT_DEFAULT_TEMPLATE,
    TEMPLATE_WEIGHTS as CONTEXT_TEMPLATE_WEIGHTS,
    TEMPLATE_WEIGHTS_DYNAMIC_DEFAULT as CONTEXT_TEMPLATE_WEIGHTS_DYNAMIC_DEFAULT,
)
from .genre_aliases import normalize_genre_token, to_profile_key
from .genre_profile_builder import (
    build_composite_genre_hints,
    extract_genre_section,
    extract_markdown_refs,
    parse_genre_tokens,
)
from .writing_guidance_builder import (
    build_methodology_guidance_items,
    build_methodology_strategy_card,
    build_guidance_items,
    build_writing_checklist,
    is_checklist_item_completed,
)


logger = logging.getLogger(__name__)


class ContextManager:
    DEFAULT_TEMPLATE = CONTEXT_DEFAULT_TEMPLATE
    TEMPLATE_WEIGHTS = CONTEXT_TEMPLATE_WEIGHTS
    TEMPLATE_WEIGHTS_DYNAMIC = CONTEXT_TEMPLATE_WEIGHTS_DYNAMIC_DEFAULT
    EXTRA_SECTIONS = {
        "story_skeleton",
        "memory",
        "preferences",
        "alerts",
        "reader_signal",
        "genre_profile",
        "writing_guidance",
        "project_constraints",
    }
    SECTION_ORDER = [
        "core",
        "scene",
        "global",
        "reader_signal",
        "genre_profile",
        "writing_guidance",
        "project_constraints",
        "story_skeleton",
        "memory",
        "preferences",
        "alerts",
    ]
    SUMMARY_SECTION_RE = re.compile(r"##\s*剧情摘要\s*\r?\n(.*?)(?=\r?\n##|\Z)", re.DOTALL)

    def __init__(self, config=None, snapshot_manager: Optional[SnapshotManager] = None):
        self.config = config or get_config()
        self.snapshot_manager = snapshot_manager or SnapshotManager(self.config)
        self.index_manager = IndexManager(self.config)
        self.context_ranker = ContextRanker(self.config)

    def _is_snapshot_compatible(self, cached: Dict[str, Any], template: str) -> bool:
        """判断快照是否可用于当前模板。"""
        if not isinstance(cached, dict):
            return False

        meta = cached.get("meta")
        if not isinstance(meta, dict):
            # 兼容旧快照：未记录 template 时仅允许默认模板复用
            return template == self.DEFAULT_TEMPLATE

        cached_template = meta.get("template")
        if not isinstance(cached_template, str):
            return template == self.DEFAULT_TEMPLATE

        return cached_template == template

    def build_context(
        self,
        chapter: int,
        template: str | None = None,
        use_snapshot: bool = True,
        save_snapshot: bool = True,
        max_chars: Optional[int] = None,
    ) -> Dict[str, Any]:
        template = template or self.DEFAULT_TEMPLATE
        self._active_template = template
        if template not in self.TEMPLATE_WEIGHTS:
            template = self.DEFAULT_TEMPLATE
            self._active_template = template

        if use_snapshot:
            try:
                cached = self.snapshot_manager.load_snapshot(chapter)
                if cached and self._is_snapshot_compatible(cached, template):
                    return cached.get("payload", cached)
            except SnapshotVersionMismatch:
                # Snapshot incompatible; rebuild below.
                pass

        pack = self._build_pack(chapter)
        if getattr(self.config, "context_ranker_enabled", True):
            pack = self.context_ranker.rank_pack(pack, chapter)
        assembled = self.assemble_context(pack, template=template, max_chars=max_chars)

        if save_snapshot:
            meta = {"template": template}
            self.snapshot_manager.save_snapshot(chapter, assembled, meta=meta)

        return assembled

    def assemble_context(
        self,
        pack: Dict[str, Any],
        template: str = DEFAULT_TEMPLATE,
        max_chars: Optional[int] = None,
    ) -> Dict[str, Any]:
        chapter = int((pack.get("meta") or {}).get("chapter") or 0)
        weights = self._resolve_template_weights(template=template, chapter=chapter)
        max_chars = max_chars or 8000
        extra_budget = int(self.config.context_extra_section_budget or 0)

        sections = {}
        for section_name in self.SECTION_ORDER:
            if section_name in pack:
                sections[section_name] = pack[section_name]

        assembled: Dict[str, Any] = {"meta": pack.get("meta", {}), "sections": {}}
        for name, content in sections.items():
            weight = weights.get(name, 0.0)
            if weight > 0:
                budget = int(max_chars * weight)
            elif name in self.EXTRA_SECTIONS and extra_budget > 0:
                budget = extra_budget
            else:
                budget = None
            text = self._compact_json_text(content, budget)
            assembled["sections"][name] = {"content": content, "text": text, "budget": budget}

        assembled["template"] = template
        assembled["weights"] = weights
        if chapter > 0:
            assembled.setdefault("meta", {})["context_weight_stage"] = self._resolve_context_stage(chapter)
        return assembled

    def filter_invalid_items(self, items: List[Dict[str, Any]], source_type: str, id_key: str) -> List[Dict[str, Any]]:
        confirmed = self.index_manager.get_invalid_ids(source_type, status="confirmed")
        pending = self.index_manager.get_invalid_ids(source_type, status="pending")
        result = []
        for item in items:
            item_id = str(item.get(id_key, ""))
            if item_id in confirmed:
                continue
            if item_id in pending:
                item = dict(item)
                item["warning"] = "pending_invalid"
            result.append(item)
        return result

    def apply_confidence_filter(self, items: List[Dict[str, Any]], min_confidence: float) -> List[Dict[str, Any]]:
        filtered: List[Dict[str, Any]] = []
        for item in items:
            conf = item.get("confidence")
            if conf is None or conf >= min_confidence:
                filtered.append(item)
        return filtered

    def _build_pack(self, chapter: int) -> Dict[str, Any]:
        state = self._load_state()
        core = {
            "chapter_outline": self._load_outline(chapter),
            "protagonist_snapshot": state.get("protagonist_state", {}),
            "recent_summaries": self._load_recent_summaries(
                chapter,
                window=self.config.context_recent_summaries_window,
            ),
            "recent_meta": self._load_recent_meta(
                state,
                chapter,
                window=self.config.context_recent_meta_window,
            ),
        }

        scene = {
            "location_context": state.get("protagonist_state", {}).get("location", {}),
            "appearing_characters": self._load_recent_appearances(
                limit=self.config.context_max_appearing_characters,
            ),
        }
        scene["appearing_characters"] = self.filter_invalid_items(
            scene["appearing_characters"], source_type="entity", id_key="entity_id"
        )

        global_ctx = {
            "worldview_skeleton": self._load_setting("世界观"),
            "power_system_skeleton": self._load_setting("力量体系"),
            "style_contract_ref": self._load_setting("风格契约"),
        }

        preferences = self._load_json_optional(self.config.webnovel_dir / "preferences.json")
        memory = self._load_json_optional(self.config.webnovel_dir / "project_memory.json")
        project_constraint_pack = self._build_project_constraint_pack(preferences)
        story_skeleton = self._load_story_skeleton(chapter)
        alert_slice = max(0, int(self.config.context_alerts_slice))
        reader_signal = self._load_reader_signal(chapter)
        genre_profile = self._load_genre_profile(state)
        writing_guidance = self._build_writing_guidance(chapter, reader_signal, genre_profile)

        return {
            "meta": {
                "chapter": chapter,
                "constraint_pack_hash": project_constraint_pack.get("constraint_pack_hash", ""),
            },
            "core": core,
            "scene": scene,
            "global": global_ctx,
            "reader_signal": reader_signal,
            "genre_profile": genre_profile,
            "writing_guidance": writing_guidance,
            "project_constraints": project_constraint_pack,
            "story_skeleton": story_skeleton,
            "preferences": preferences,
            "memory": memory,
            "alerts": {
                "disambiguation_warnings": (
                    state.get("disambiguation_warnings", [])[-alert_slice:] if alert_slice else []
                ),
                "disambiguation_pending": (
                    state.get("disambiguation_pending", [])[-alert_slice:] if alert_slice else []
                ),
            },
        }

    def _build_project_constraint_pack(self, preferences: Dict[str, Any]) -> Dict[str, Any]:
        style_contract_text = self._load_setting("风格契约")
        writing_style_text = self._load_setting("写作风格")
        style_preferences = preferences.get("style") if isinstance(preferences, dict) else {}

        rule_specs = [
            {
                "id": "STYLE_SEQ_XIAN_TEMPLATE",
                "category": "language",
                "default_severity": "high",
                "hard_or_soft": "hard",
                "negative_signals": ["先……再……", "先……才……", "顺序提示词起手串动作"],
                "positive_evidence_required": ["动作直接落地，不靠顺序提示词串联", "动作与反应自然衔接"],
                "escalation_threshold": "同段重复出现或整章形成流程图感",
                "override_allowed": False,
                "repair_guidance": "改回直接动作链和现场反应，删除只负责挂顺序的‘先’模板。",
                "source_refs": [
                    "preferences.style.sequence_marker_policy",
                    "风格契约:语言硬约束-顺序提示词",
                    "写作风格:动作拆解-顺序提示词",
                ],
            },
            {
                "id": "STYLE_XIANG_VIRTUALIZATION",
                "category": "language",
                "default_severity": "high",
                "hard_or_soft": "hard",
                "negative_signals": ["像要……", "像在……", "像是……", "把能直接写的动作和判断又隔一层写虚"],
                "positive_evidence_required": ["直接动作、物态、触感", "真有比喻价值或物态对照时才保留‘像’"],
                "escalation_threshold": "连续出现或明显拖虚判断",
                "override_allowed": False,
                "repair_guidance": "把虚写套壳改回直接动作、物态和反应，只保留有真实比喻价值的‘像’。",
                "source_refs": [
                    "preferences.style.xiang_virtualization_policy",
                    "风格契约:语言硬约束-像字虚写",
                    "写作风格:动作拆解-像字虚写",
                ],
            },
            {
                "id": "STYLE_EXPLANATION_TRANSLATION",
                "category": "narration",
                "default_severity": "high",
                "hard_or_soft": "hard",
                "negative_signals": ["不是……是……", "其实……", "原来……", "解释腔", "盖章式判断"],
                "positive_evidence_required": ["物证先于结论", "动作、停顿、旁人反应顶出判断"],
                "escalation_threshold": "一句直接翻译场面或替读者做阅读理解",
                "override_allowed": False,
                "repair_guidance": "把解释句拆回动作、物证、停顿、岔念头和旁人反应，减少作者代读。",
                "source_refs": [
                    "preferences.style.exposition_policy",
                    "preferences.style.judgment_policy",
                    "风格契约:语言硬约束-解释型转折",
                    "写作风格:执行层-去AI化",
                ],
            },
            {
                "id": "STYLE_DIALOGUE_STIFF",
                "category": "dialogue",
                "default_severity": "high",
                "hard_or_soft": "hard",
                "negative_signals": ["对白像台词稿", "播报句", "审查意见句", "只剩结论"],
                "positive_evidence_required": ["顺话、接茬、怨气、找补、试探", "任意抽一句念出来像这个人真会说的话"],
                "escalation_threshold": "关键对白成段发硬或整场只剩信息点",
                "override_allowed": False,
                "repair_guidance": "把对白改回身份化口气，保留口头顺话和自保意味，不写成播报或判词。",
                "source_refs": [
                    "preferences.style.dialogue_policy",
                    "preferences.style.dialogue_read_aloud_rule",
                    "风格契约:对话风格",
                    "写作风格:对话风格",
                ],
            },
            {
                "id": "STYLE_SUPPORTING_CAST_TOOLIFIED",
                "category": "character",
                "default_severity": "medium",
                "hard_or_soft": "soft",
                "negative_signals": ["配角只做主角反应器", "众人统一口径反馈", "先主线后私心缺失"],
                "positive_evidence_required": ["至少一个配角先顾自己的风险、面子、工钱或站位", "同一件事存在分层反馈"],
                "escalation_threshold": "整场景配角都只围主角转",
                "override_allowed": True,
                "repair_guidance": "给配角补先顾自己的动作、回嘴或避责，再回到主线反馈。",
                "source_refs": [
                    "preferences.avoid[6]",
                    "preferences.style.crowd_feedback_policy",
                    "风格契约:必守原则-配角先顾自己",
                    "写作风格:配角群像",
                ],
            },
            {
                "id": "STYLE_CAUSALITY_TOO_STRAIGHT",
                "category": "structure",
                "default_severity": "medium",
                "hard_or_soft": "soft",
                "negative_signals": [
                    "发现异常→准确判断→继续推进→当场坐实",
                    "信息死直线",
                    "没有闲话、误听、打断、非最优反应",
                ],
                "positive_evidence_required": [
                    "至少一处弱连接信息",
                    "至少一处非最优反应或现场打断",
                    "生活噪音介入后再并回主线",
                ],
                "escalation_threshold": "整章只按最优路径推进",
                "override_allowed": True,
                "repair_guidance": "在不拖节奏前提下补入弱连接、打断、误会、生活噪音和非最优动作。",
                "source_refs": [
                    "preferences.style.information_flow_policy",
                    "风格契约:语言硬约束-主线推进以线性为主但不要死直线",
                    "写作风格:叙事视角-信息投放",
                ],
            },
            {
                "id": "STYLE_TEMPLATE_WORD_CLUSTER",
                "category": "language",
                "default_severity": "medium",
                "hard_or_soft": "soft",
                "negative_signals": [
                    "一下/这才/立刻/连忙 等过场词聚集",
                    "就/又/可/真/压/横/落 等桥词或套壳字扎堆",
                    "单字问题词成片出现",
                ],
                "positive_evidence_required": ["句子自然顺口，不靠桥词补筋骨", "动作和口气本身能完成节奏推进"],
                "escalation_threshold": "局部词群扎堆导致明显 AI 模板感",
                "override_allowed": True,
                "repair_guidance": "不要逐字硬删，回到整句整段重写，把桥词套壳并回自然动作链。",
                "source_refs": [
                    "preferences.style.template_word_policy",
                    "preferences.style.bridge_word_policy",
                    "preferences.style.true_emphasis_policy",
                    "风格契约:语言硬约束-问题词/桥词",
                ],
            },
        ]

        rules: List[Dict[str, Any]] = []
        for spec in rule_specs:
            source_snippets = self._collect_constraint_source_snippets(
                rule_id=spec["id"],
                preferences_style=style_preferences if isinstance(style_preferences, dict) else {},
                style_contract_text=style_contract_text,
                writing_style_text=writing_style_text,
            )
            rule = dict(spec)
            rule["source_snippets"] = source_snippets
            rules.append(rule)

        chapter_style_targets = [
            "正文自然顺嘴，避免解释腔和模板动作链。",
            "至少保留 1-2 处长在身份与处境里的生活噪音。",
            "至少 1 个配角先顾自己，再反馈主线。",
            "主角判断不要一步到位，允许先动手、先挨压、再补全判断。",
        ]
        chapter_positive_evidence_targets = [
            {"rule_id": "STYLE_CAUSALITY_TOO_STRAIGHT", "target": "至少 1 处弱连接信息或现场打断。"},
            {"rule_id": "STYLE_SUPPORTING_CAST_TOOLIFIED", "target": "至少 1 个配角先露出私心、顾虑或站位。"},
            {"rule_id": "STYLE_DIALOGUE_STIFF", "target": "至少 1 处对白保留顺话、接茬、怨气或找补。"},
            {"rule_id": "STYLE_SEQ_XIAN_TEMPLATE", "target": "关键动作段直接推进，不靠‘先……再/才……’串联。"},
        ]

        source_refs = {
            "preferences": ".webnovel/preferences.json",
            "style_contract": "设定集/风格契约.md",
            "writing_style": "设定集/写作风格.md",
        }
        hash_payload = {
            "rules": rules,
            "chapter_style_targets": chapter_style_targets,
            "chapter_positive_evidence_targets": chapter_positive_evidence_targets,
        }
        constraint_pack_hash = hashlib.sha256(
            json.dumps(hash_payload, ensure_ascii=False, sort_keys=True).encode("utf-8")
        ).hexdigest()

        return {
            "constraint_pack_version": "v1",
            "constraint_pack_hash": constraint_pack_hash,
            "source_refs": source_refs,
            "rules": rules,
            "chapter_style_targets": chapter_style_targets,
            "chapter_positive_evidence_targets": chapter_positive_evidence_targets,
        }

    def _collect_constraint_source_snippets(
        self,
        rule_id: str,
        preferences_style: Dict[str, Any],
        style_contract_text: str,
        writing_style_text: str,
    ) -> List[str]:
        field_map = {
            "STYLE_SEQ_XIAN_TEMPLATE": ["sequence_marker_policy"],
            "STYLE_XIANG_VIRTUALIZATION": ["xiang_virtualization_policy"],
            "STYLE_EXPLANATION_TRANSLATION": ["exposition_policy", "judgment_policy"],
            "STYLE_DIALOGUE_STIFF": ["dialogue_policy", "dialogue_read_aloud_rule"],
            "STYLE_SUPPORTING_CAST_TOOLIFIED": ["crowd_feedback_policy"],
            "STYLE_CAUSALITY_TOO_STRAIGHT": ["information_flow_policy"],
            "STYLE_TEMPLATE_WORD_CLUSTER": [
                "template_word_policy",
                "bridge_word_policy",
                "true_emphasis_policy",
                "ya_pressure_shell_policy",
            ],
        }
        keyword_map = {
            "STYLE_SEQ_XIAN_TEMPLATE": ["先……再……", "先……才……", "顺序提示词"],
            "STYLE_XIANG_VIRTUALIZATION": ["像要", "像在", "像是", "像"],
            "STYLE_EXPLANATION_TRANSLATION": ["不是……是……", "解释", "盖章式判断"],
            "STYLE_DIALOGUE_STIFF": ["对白", "台词稿", "播报", "口试规则"],
            "STYLE_SUPPORTING_CAST_TOOLIFIED": ["配角", "反应器", "分层反馈", "先顾自己"],
            "STYLE_CAUSALITY_TOO_STRAIGHT": ["线性", "死直线", "弱连接", "非最优反应"],
            "STYLE_TEMPLATE_WORD_CLUSTER": ["问题词", "桥词", "套壳", "一下", "就", "又", "可", "真"],
        }

        snippets: List[str] = []
        for field_name in field_map.get(rule_id, []):
            value = preferences_style.get(field_name)
            if isinstance(value, str) and value.strip():
                snippets.append(f"preferences:{field_name}={value.strip()[:160]}")

        keywords = keyword_map.get(rule_id, [])
        snippets.extend(self._extract_matching_lines(style_contract_text, keywords, prefix="风格契约"))
        snippets.extend(self._extract_matching_lines(writing_style_text, keywords, prefix="写作风格"))
        return snippets[:6]

    def _extract_matching_lines(self, text: str, keywords: List[str], prefix: str) -> List[str]:
        if not text:
            return []
        matches: List[str] = []
        for line in text.splitlines():
            stripped = line.strip()
            if not stripped:
                continue
            if any(keyword and keyword in stripped for keyword in keywords):
                matches.append(f"{prefix}:{stripped[:160]}")
        return matches[:4]

    def _load_reader_signal(self, chapter: int) -> Dict[str, Any]:
        if not getattr(self.config, "context_reader_signal_enabled", True):
            return {}

        recent_limit = max(1, int(getattr(self.config, "context_reader_signal_recent_limit", 5)))
        pattern_window = max(1, int(getattr(self.config, "context_reader_signal_window_chapters", 20)))
        review_window = max(1, int(getattr(self.config, "context_reader_signal_review_window", 5)))
        include_debt = bool(getattr(self.config, "context_reader_signal_include_debt", False))

        recent_power = self.index_manager.get_recent_reading_power(limit=recent_limit)
        pattern_stats = self.index_manager.get_pattern_usage_stats(last_n_chapters=pattern_window)
        hook_stats = self.index_manager.get_hook_type_stats(last_n_chapters=pattern_window)
        review_trend = self.index_manager.get_review_trend_stats(last_n=review_window)

        low_score_ranges: List[Dict[str, Any]] = []
        for row in review_trend.get("recent_ranges", []):
            score = row.get("overall_score")
            if isinstance(score, (int, float)) and float(score) < 75:
                low_score_ranges.append(
                    {
                        "start_chapter": row.get("start_chapter"),
                        "end_chapter": row.get("end_chapter"),
                        "overall_score": score,
                    }
                )

        signal: Dict[str, Any] = {
            "recent_reading_power": recent_power,
            "pattern_usage": pattern_stats,
            "hook_type_usage": hook_stats,
            "review_trend": review_trend,
            "low_score_ranges": low_score_ranges,
            "next_chapter": chapter,
        }

        if include_debt:
            signal["debt_summary"] = self.index_manager.get_debt_summary()

        return signal

    def _load_genre_profile(self, state: Dict[str, Any]) -> Dict[str, Any]:
        if not getattr(self.config, "context_genre_profile_enabled", True):
            return {}

        fallback = str(getattr(self.config, "context_genre_profile_fallback", "shuangwen") or "shuangwen")
        project = state.get("project") or {}
        project_info = state.get("project_info") or {}
        genre_raw = str(project.get("genre") or project_info.get("genre") or fallback)
        genres = self._parse_genre_tokens(genre_raw)
        if not genres:
            genres = [fallback]
        max_genres = max(1, int(getattr(self.config, "context_genre_profile_max_genres", 2)))
        genres = genres[:max_genres]

        primary_genre = genres[0]
        secondary_genres = genres[1:]
        composite = len(genres) > 1
        profile_path = self.config.project_root / ".claude" / "references" / "genre-profiles.md"
        taxonomy_path = self.config.project_root / ".claude" / "references" / "reading-power-taxonomy.md"

        profile_text = profile_path.read_text(encoding="utf-8") if profile_path.exists() else ""
        taxonomy_text = taxonomy_path.read_text(encoding="utf-8") if taxonomy_path.exists() else ""

        profile_excerpt = self._extract_genre_section(profile_text, primary_genre)
        taxonomy_excerpt = self._extract_genre_section(taxonomy_text, primary_genre)

        secondary_profiles: List[str] = []
        secondary_taxonomies: List[str] = []
        for extra in secondary_genres:
            secondary_profiles.append(self._extract_genre_section(profile_text, extra))
            secondary_taxonomies.append(self._extract_genre_section(taxonomy_text, extra))

        refs = self._extract_markdown_refs(
            "\n".join([profile_excerpt] + secondary_profiles),
            max_items=int(getattr(self.config, "context_genre_profile_max_refs", 8)),
        )

        composite_hints = self._build_composite_genre_hints(genres, refs)

        return {
            "genre": primary_genre,
            "genre_raw": genre_raw,
            "genres": genres,
            "composite": composite,
            "secondary_genres": secondary_genres,
            "profile_excerpt": profile_excerpt,
            "taxonomy_excerpt": taxonomy_excerpt,
            "secondary_profile_excerpts": secondary_profiles,
            "secondary_taxonomy_excerpts": secondary_taxonomies,
            "reference_hints": refs,
            "composite_hints": composite_hints,
        }

    def _build_writing_guidance(
        self,
        chapter: int,
        reader_signal: Dict[str, Any],
        genre_profile: Dict[str, Any],
    ) -> Dict[str, Any]:
        if not getattr(self.config, "context_writing_guidance_enabled", True):
            return {}

        limit = max(1, int(getattr(self.config, "context_writing_guidance_max_items", 6)))
        low_score_threshold = float(
            getattr(self.config, "context_writing_guidance_low_score_threshold", 75.0)
        )

        guidance_bundle = build_guidance_items(
            chapter=chapter,
            reader_signal=reader_signal,
            genre_profile=genre_profile,
            low_score_threshold=low_score_threshold,
            hook_diversify_enabled=bool(
                getattr(self.config, "context_writing_guidance_hook_diversify", True)
            ),
        )

        guidance = list(guidance_bundle.get("guidance") or [])
        methodology_strategy: Dict[str, Any] = {}

        if self._is_methodology_enabled_for_genre(genre_profile):
            methodology_strategy = build_methodology_strategy_card(
                chapter=chapter,
                reader_signal=reader_signal,
                genre_profile=genre_profile,
                label=str(getattr(self.config, "context_methodology_label", "digital-serial-v1")),
            )
            guidance.extend(build_methodology_guidance_items(methodology_strategy))

        checklist = self._build_writing_checklist(
            chapter=chapter,
            guidance_items=guidance,
            reader_signal=reader_signal,
            genre_profile=genre_profile,
            strategy_card=methodology_strategy,
        )

        checklist_score = self._compute_writing_checklist_score(
            chapter=chapter,
            checklist=checklist,
            reader_signal=reader_signal,
        )

        if getattr(self.config, "context_writing_score_persist_enabled", True):
            self._persist_writing_checklist_score(checklist_score)

        low_ranges = guidance_bundle.get("low_ranges") or []
        hook_usage = guidance_bundle.get("hook_usage") or {}
        pattern_usage = guidance_bundle.get("pattern_usage") or {}
        genre = str(guidance_bundle.get("genre") or genre_profile.get("genre") or "").strip()

        hook_types = list(hook_usage.keys())[:3] if isinstance(hook_usage, dict) else []
        top_patterns = (
            sorted(pattern_usage, key=pattern_usage.get, reverse=True)[:3]
            if isinstance(pattern_usage, dict)
            else []
        )

        return {
            "chapter": chapter,
            "guidance_items": guidance[:limit],
            "checklist": checklist,
            "checklist_score": checklist_score,
            "methodology": methodology_strategy,
            "signals_used": {
                "has_low_score_ranges": bool(low_ranges),
                "hook_types": hook_types,
                "top_patterns": top_patterns,
                "genre": genre,
                "methodology_enabled": bool(methodology_strategy.get("enabled")),
            },
        }

    def _compute_writing_checklist_score(
        self,
        chapter: int,
        checklist: List[Dict[str, Any]],
        reader_signal: Dict[str, Any],
    ) -> Dict[str, Any]:
        total_items = len(checklist)
        required_items = 0
        completed_items = 0
        completed_required = 0
        total_weight = 0.0
        completed_weight = 0.0
        pending_labels: List[str] = []

        for item in checklist:
            if not isinstance(item, dict):
                continue
            required = bool(item.get("required"))
            weight = float(item.get("weight") or 1.0)
            total_weight += weight
            if required:
                required_items += 1

            completed = self._is_checklist_item_completed(item, reader_signal)
            if completed:
                completed_items += 1
                completed_weight += weight
                if required:
                    completed_required += 1
            else:
                pending_labels.append(str(item.get("label") or item.get("id") or "未命名项"))

        completion_rate = (completed_items / total_items) if total_items > 0 else 1.0
        weighted_rate = (completed_weight / total_weight) if total_weight > 0 else completion_rate
        required_rate = (completed_required / required_items) if required_items > 0 else 1.0

        score = 100.0 * (0.5 * weighted_rate + 0.3 * required_rate + 0.2 * completion_rate)

        if getattr(self.config, "context_writing_score_include_reader_trend", True):
            trend_window = max(1, int(getattr(self.config, "context_writing_score_trend_window", 10)))
            trend = self.index_manager.get_writing_checklist_score_trend(last_n=trend_window)
            baseline = float(trend.get("score_avg") or 0.0)
            if baseline > 0:
                score += max(-10.0, min(10.0, (score - baseline) * 0.1))

        score = round(max(0.0, min(100.0, score)), 2)

        return {
            "chapter": chapter,
            "score": score,
            "completion_rate": round(completion_rate, 4),
            "weighted_completion_rate": round(weighted_rate, 4),
            "required_completion_rate": round(required_rate, 4),
            "total_items": total_items,
            "required_items": required_items,
            "completed_items": completed_items,
            "completed_required": completed_required,
            "total_weight": round(total_weight, 2),
            "completed_weight": round(completed_weight, 2),
            "pending_items": pending_labels,
            "trend_window": int(getattr(self.config, "context_writing_score_trend_window", 10)),
        }

    def _is_checklist_item_completed(self, item: Dict[str, Any], reader_signal: Dict[str, Any]) -> bool:
        return is_checklist_item_completed(item, reader_signal)

    def _persist_writing_checklist_score(self, checklist_score: Dict[str, Any]) -> None:
        if not checklist_score:
            return
        try:
            self.index_manager.save_writing_checklist_score(
                WritingChecklistScoreMeta(
                    chapter=int(checklist_score.get("chapter") or 0),
                    template=str(getattr(self, "_active_template", self.DEFAULT_TEMPLATE) or self.DEFAULT_TEMPLATE),
                    total_items=int(checklist_score.get("total_items") or 0),
                    required_items=int(checklist_score.get("required_items") or 0),
                    completed_items=int(checklist_score.get("completed_items") or 0),
                    completed_required=int(checklist_score.get("completed_required") or 0),
                    total_weight=float(checklist_score.get("total_weight") or 0.0),
                    completed_weight=float(checklist_score.get("completed_weight") or 0.0),
                    completion_rate=float(checklist_score.get("completion_rate") or 0.0),
                    score=float(checklist_score.get("score") or 0.0),
                    score_breakdown={
                        "weighted_completion_rate": checklist_score.get("weighted_completion_rate"),
                        "required_completion_rate": checklist_score.get("required_completion_rate"),
                        "trend_window": checklist_score.get("trend_window"),
                    },
                    pending_items=list(checklist_score.get("pending_items") or []),
                    source="context_manager",
                )
            )
        except Exception as exc:
            logger.warning("failed to persist writing checklist score: %s", exc)

    def _resolve_context_stage(self, chapter: int) -> str:
        early = max(1, int(getattr(self.config, "context_dynamic_budget_early_chapter", 30)))
        late = max(early + 1, int(getattr(self.config, "context_dynamic_budget_late_chapter", 120)))
        if chapter <= early:
            return "early"
        if chapter >= late:
            return "late"
        return "mid"

    def _resolve_template_weights(self, template: str, chapter: int) -> Dict[str, float]:
        template_key = template if template in self.TEMPLATE_WEIGHTS else self.DEFAULT_TEMPLATE
        base = dict(self.TEMPLATE_WEIGHTS.get(template_key, self.TEMPLATE_WEIGHTS[self.DEFAULT_TEMPLATE]))
        if not getattr(self.config, "context_dynamic_budget_enabled", True):
            return base

        stage = self._resolve_context_stage(chapter)
        dynamic_weights = getattr(self.config, "context_template_weights_dynamic", None)
        if not isinstance(dynamic_weights, dict):
            dynamic_weights = self.TEMPLATE_WEIGHTS_DYNAMIC

        stage_weights = dynamic_weights.get(stage, {}) if isinstance(dynamic_weights.get(stage, {}), dict) else {}
        staged = stage_weights.get(template_key)
        if isinstance(staged, dict):
            return dict(staged)

        return base

    def _parse_genre_tokens(self, genre_raw: str) -> List[str]:
        support_composite = bool(getattr(self.config, "context_genre_profile_support_composite", True))
        separators_raw = getattr(self.config, "context_genre_profile_separators", ("+", "/", "|", ","))
        separators = tuple(str(token) for token in separators_raw if str(token))
        return parse_genre_tokens(
            genre_raw,
            support_composite=support_composite,
            separators=separators,
        )

    def _normalize_genre_token(self, token: str) -> str:
        return normalize_genre_token(token)

    def _build_composite_genre_hints(self, genres: List[str], refs: List[str]) -> List[str]:
        return build_composite_genre_hints(genres, refs)

    def _build_writing_checklist(
        self,
        chapter: int,
        guidance_items: List[str],
        reader_signal: Dict[str, Any],
        genre_profile: Dict[str, Any],
        strategy_card: Dict[str, Any] | None = None,
    ) -> List[Dict[str, Any]]:
        _ = chapter
        if not getattr(self.config, "context_writing_checklist_enabled", True):
            return []

        min_items = max(1, int(getattr(self.config, "context_writing_checklist_min_items", 3)))
        max_items = max(min_items, int(getattr(self.config, "context_writing_checklist_max_items", 6)))
        default_weight = float(getattr(self.config, "context_writing_checklist_default_weight", 1.0))
        if default_weight <= 0:
            default_weight = 1.0

        return build_writing_checklist(
            guidance_items=guidance_items,
            reader_signal=reader_signal,
            genre_profile=genre_profile,
            strategy_card=strategy_card,
            min_items=min_items,
            max_items=max_items,
            default_weight=default_weight,
        )

    def _is_methodology_enabled_for_genre(self, genre_profile: Dict[str, Any]) -> bool:
        if not bool(getattr(self.config, "context_methodology_enabled", False)):
            return False

        whitelist_raw = getattr(self.config, "context_methodology_genre_whitelist", ("*",))
        if isinstance(whitelist_raw, str):
            whitelist_iter = [whitelist_raw]
        else:
            whitelist_iter = list(whitelist_raw or [])

        whitelist = {str(token).strip().lower() for token in whitelist_iter if str(token).strip()}
        if not whitelist:
            return True
        if "*" in whitelist or "all" in whitelist:
            return True

        genre = str((genre_profile or {}).get("genre") or "").strip()
        if not genre:
            return False

        profile_key = to_profile_key(genre)
        return profile_key in whitelist

    def _compact_json_text(self, content: Any, budget: Optional[int]) -> str:
        raw = json.dumps(content, ensure_ascii=False)
        if budget is None or len(raw) <= budget:
            return raw
        if not getattr(self.config, "context_compact_text_enabled", True):
            return raw[:budget]

        min_budget = max(1, int(getattr(self.config, "context_compact_min_budget", 120)))
        if budget <= min_budget:
            return raw[:budget]

        head_ratio = float(getattr(self.config, "context_compact_head_ratio", 0.65))
        head_budget = int(budget * max(0.2, min(0.9, head_ratio)))
        tail_budget = max(0, budget - head_budget - 10)
        compact = f"{raw[:head_budget]}…[TRUNCATED]{raw[-tail_budget:] if tail_budget else ''}"
        return compact[:budget]

    def _extract_genre_section(self, text: str, genre: str) -> str:
        return extract_genre_section(text, genre)

    def _extract_markdown_refs(self, text: str, max_items: int = 8) -> List[str]:
        return extract_markdown_refs(text, max_items=max_items)

    def _load_state(self) -> Dict[str, Any]:
        path = self.config.state_file
        if not path.exists():
            return {}
        return json.loads(path.read_text(encoding="utf-8"))

    def _load_outline(self, chapter: int) -> str:
        return load_chapter_outline(self.config.project_root, chapter, max_chars=1500)

    def _load_recent_summaries(self, chapter: int, window: int = 3) -> List[Dict[str, Any]]:
        summaries = []
        for ch in range(max(1, chapter - window), chapter):
            summary = self._load_summary_text(ch)
            if summary:
                summaries.append(summary)
        return summaries

    def _load_recent_meta(self, state: Dict[str, Any], chapter: int, window: int = 3) -> List[Dict[str, Any]]:
        meta = state.get("chapter_meta", {}) or {}
        results = []
        for ch in range(max(1, chapter - window), chapter):
            for key in (f"{ch:04d}", str(ch)):
                if key in meta:
                    results.append({"chapter": ch, **meta.get(key, {})})
                    break
        return results

    def _load_recent_appearances(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        appearances = self.index_manager.get_recent_appearances(limit=limit)
        return appearances or []

    def _load_setting(self, keyword: str) -> str:
        settings_dir = self.config.settings_dir
        candidates = [
            settings_dir / f"{keyword}.md",
        ]
        for path in candidates:
            if path.exists():
                return path.read_text(encoding="utf-8")
        # fallback: any file containing keyword
        matches = list(settings_dir.glob(f"*{keyword}*.md"))
        if matches:
            return matches[0].read_text(encoding="utf-8")
        return f"[{keyword}设定未找到]"

    def _extract_summary_excerpt(self, text: str, max_chars: int) -> str:
        if not text:
            return ""
        match = self.SUMMARY_SECTION_RE.search(text)
        excerpt = match.group(1).strip() if match else text.strip()
        if max_chars > 0 and len(excerpt) > max_chars:
            return excerpt[:max_chars].rstrip()
        return excerpt

    def _load_summary_text(self, chapter: int, snippet_chars: Optional[int] = None) -> Optional[Dict[str, Any]]:
        summary_path = self.config.webnovel_dir / "summaries" / f"ch{chapter:04d}.md"
        if not summary_path.exists():
            return None
        text = summary_path.read_text(encoding="utf-8")
        if snippet_chars:
            summary_text = self._extract_summary_excerpt(text, snippet_chars)
        else:
            summary_text = text
        return {"chapter": chapter, "summary": summary_text}

    def _load_story_skeleton(self, chapter: int) -> List[Dict[str, Any]]:
        interval = max(1, int(self.config.context_story_skeleton_interval))
        max_samples = max(0, int(self.config.context_story_skeleton_max_samples))
        snippet_chars = int(self.config.context_story_skeleton_snippet_chars)

        if max_samples <= 0 or chapter <= interval:
            return []

        samples: List[Dict[str, Any]] = []
        cursor = chapter - interval
        while cursor >= 1 and len(samples) < max_samples:
            summary = self._load_summary_text(cursor, snippet_chars=snippet_chars)
            if summary and summary.get("summary"):
                samples.append(summary)
            cursor -= interval

        samples.reverse()
        return samples

    def _load_json_optional(self, path: Path) -> Dict[str, Any]:
        if not path.exists():
            return {}
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return {}


def main():
    import argparse
    from .cli_output import print_success, print_error

    parser = argparse.ArgumentParser(description="Context Manager CLI")
    parser.add_argument("--project-root", type=str, help="项目根目录")
    parser.add_argument("--chapter", type=int, required=True)
    parser.add_argument("--template", type=str, default=ContextManager.DEFAULT_TEMPLATE)
    parser.add_argument("--no-snapshot", action="store_true")
    parser.add_argument("--max-chars", type=int, default=8000)

    args = parser.parse_args()

    config = None
    if args.project_root:
        # 允许传入“工作区根目录”，统一解析到真正的 book project_root（必须包含 .webnovel/state.json）
        from project_locator import resolve_project_root
        from .config import DataModulesConfig

        resolved_root = resolve_project_root(args.project_root)
        config = DataModulesConfig.from_project_root(resolved_root)

    manager = ContextManager(config)
    try:
        payload = manager.build_context(
            chapter=args.chapter,
            template=args.template,
            use_snapshot=not args.no_snapshot,
            save_snapshot=True,
            max_chars=args.max_chars,
        )
        print_success(payload, message="context_built")
        try:
            manager.index_manager.log_tool_call("context_manager:build", True, chapter=args.chapter)
        except Exception as exc:
            logger.warning("failed to log successful tool call: %s", exc)
    except Exception as exc:
        print_error("CONTEXT_BUILD_FAILED", str(exc), suggestion="请检查项目结构与依赖文件")
        try:
            manager.index_manager.log_tool_call(
                "context_manager:build", False, error_code="CONTEXT_BUILD_FAILED", error_message=str(exc), chapter=args.chapter
            )
        except Exception as log_exc:
            logger.warning("failed to log failed tool call: %s", log_exc)


if __name__ == "__main__":
    import sys
    if sys.platform == "win32":
        enable_windows_utf8_stdio()
    main()
