from __future__ import annotations

from typing import Optional

from app.schemas import APIBridgeConfig
from app.services.api_bridge_service import APIBridgeError, call_chat_completion


def build_enhanced_chapter_brief(
    memory_text: str,
    user_description: str,
    api_bridge: APIBridgeConfig,
    use_api_context: bool = True,
) -> str:
    memory_text = (memory_text or "").strip()
    user_description = user_description.strip()

    if use_api_context and api_bridge.enabled:
        system_prompt = (
            "你是小说章节策划助手。根据已有剧情记忆和作者给出的章节意图，"
            "输出“章节描述”，要求包含：本章目标、关键冲突、人物心理变化、场景推进、伏笔。"
            "输出中文纯文本，不要分点编号。"
        )
        user_prompt = (
            f"已有剧情记忆：\n{memory_text[:7000] if memory_text else '（暂无）'}\n\n"
            f"作者当前章节意图：\n{user_description}\n\n"
            "请整合为可直接给本地写作模型的章节描述。"
        )
        try:
            return call_chat_completion(
                config=api_bridge,
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                temperature=0.7,
                max_tokens=1000,
            )
        except APIBridgeError:
            pass

    if memory_text:
        return f"已有剧情记忆：\n{memory_text}\n\n当前章节目标：\n{user_description}"
    return user_description


def build_chapter_prompt(
    chapter_title: str,
    chapter_brief: str,
    target_words: int,
) -> str:
    return (
        "你是一名擅长中文长篇小说创作的作家。\n"
        "请依据给定章节描述，写出完整章节正文。\n"
        f"章节标题：{chapter_title}\n"
        f"目标字数：{target_words}（允许上下浮动 10%）\n"
        "写作要求：叙事连贯、人物行为动机清晰、场景细节具体、语言风格统一。\n"
        "请直接输出正文，不要解释。\n\n"
        f"章节描述：\n{chapter_brief}\n\n"
        "章节正文：\n"
    )


def build_standalone_prompt(outline: str, memory_text: Optional[str], target_words: int) -> str:
    memory_block = memory_text.strip() if memory_text else "（暂无）"
    return (
        "你是一名中文小说创作模型。\n"
        "请根据大纲和记忆信息写出章节正文。\n"
        f"目标字数：{target_words}（允许上下浮动 10%）\n"
        "要求：风格统一、情节递进、人物心理充分、避免流水账。\n\n"
        f"历史记忆：\n{memory_block}\n\n"
        f"章节大纲：\n{outline.strip()}\n\n"
        "正文：\n"
    )
