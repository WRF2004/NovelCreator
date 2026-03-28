from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.schemas import (
    GenerateChapterRequest,
    GenerateStandaloneRequest,
    GenerationResponse,
)
from app.services.book_service import chapter_memory_context, get_book, get_chapter, update_chapter
from app.services.generation_service import (
    build_chapter_prompt,
    build_enhanced_chapter_brief,
    build_standalone_prompt,
)
from app.services.llm_service import generate_text
from app.services.path_service import require_existing_path

router = APIRouter(prefix="/generation", tags=["generation"])


@router.post("/chapter", response_model=GenerationResponse)
def generate_chapter(payload: GenerateChapterRequest, db: Session = Depends(get_db)):
    book = get_book(db, payload.book_id)
    if not book:
        raise HTTPException(status_code=404, detail="书籍不存在")
    chapter = get_chapter(db, payload.chapter_id)
    if not chapter or chapter.book_id != book.id:
        raise HTTPException(status_code=404, detail="章节不存在")

    model_path = payload.model_path or book.model_path
    if not model_path:
        raise HTTPException(status_code=400, detail="未指定模型路径，请在书籍中设置或请求中传入")

    try:
        model_path = str(require_existing_path(model_path))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    memory_text = chapter_memory_context(db, book_id=book.id, chapter_id=chapter.id, max_chars=7000)
    chapter_brief = build_enhanced_chapter_brief(
        memory_text=memory_text,
        user_description=payload.user_description,
        api_bridge=payload.api_bridge,
        use_api_context=payload.use_api_context,
    )
    prompt = build_chapter_prompt(
        chapter_title=chapter.title,
        chapter_brief=chapter_brief,
        target_words=payload.target_words,
    )
    generated = generate_text(
        model_path=model_path,
        prompt=prompt,
        max_new_tokens=payload.max_new_tokens,
        temperature=payload.temperature,
        top_p=payload.top_p,
    )
    update_chapter(
        db,
        chapter,
        description=payload.user_description,
        content=generated,
        status="generated",
    )
    return GenerationResponse(prompt=prompt, generated_text=generated, used_model_path=model_path)


@router.post("/standalone", response_model=GenerationResponse)
def generate_standalone(payload: GenerateStandaloneRequest):
    try:
        model_path = str(require_existing_path(payload.model_path))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    outline = payload.outline.strip()
    if not outline:
        raise HTTPException(status_code=400, detail="大纲不能为空")

    enhanced_outline = build_enhanced_chapter_brief(
        memory_text=(payload.memory_text or ""),
        user_description=outline,
        api_bridge=payload.api_bridge,
        use_api_context=payload.use_api_context,
    )
    prompt = build_standalone_prompt(
        outline=enhanced_outline,
        memory_text=payload.memory_text,
        target_words=payload.target_words,
    )
    generated = generate_text(
        model_path=model_path,
        prompt=prompt,
        max_new_tokens=payload.max_new_tokens,
        temperature=payload.temperature,
        top_p=payload.top_p,
    )
    return GenerationResponse(prompt=prompt, generated_text=generated, used_model_path=model_path)


@router.get("/health")
def generation_health():
    return {"ok": True, "module": "generation"}

