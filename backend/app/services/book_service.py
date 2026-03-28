from __future__ import annotations

import re
from pathlib import Path
from typing import Optional

from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models import Book, Chapter


def _book_dir(book_id: int) -> Path:
    path = settings.books_root / f"book_{book_id}"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _word_count(text: str) -> int:
    cleaned = re.sub(r"\s+", "", text)
    return len(cleaned)


def _chapter_file_path(chapter: Chapter) -> Path:
    book_dir = _book_dir(chapter.book_id)
    return book_dir / f"{chapter.order_index:04d}_{chapter.id}.md"


def _sync_chapter_file(chapter: Chapter) -> None:
    file_path = _chapter_file_path(chapter)
    file_path.write_text(chapter.content or "", encoding="utf-8")
    chapter.file_path = str(file_path)
    chapter.word_count = _word_count(chapter.content or "")


def list_books(db: Session) -> list[Book]:
    stmt: Select[tuple[Book]] = select(Book).order_by(Book.updated_at.desc(), Book.id.desc())
    return list(db.scalars(stmt).all())


def create_book(db: Session, title: str, description: Optional[str] = None, model_path: Optional[str] = None) -> Book:
    book = Book(title=title.strip(), description=description, model_path=model_path)
    db.add(book)
    db.commit()
    db.refresh(book)
    _book_dir(book.id)
    return book


def get_book(db: Session, book_id: int) -> Optional[Book]:
    return db.get(Book, book_id)


def update_book(
    db: Session,
    book: Book,
    title: Optional[str] = None,
    description: Optional[str] = None,
    model_path: Optional[str] = None,
) -> Book:
    if title is not None:
        book.title = title.strip()
    if description is not None:
        book.description = description
    if model_path is not None:
        book.model_path = model_path
    db.add(book)
    db.commit()
    db.refresh(book)
    return book


def delete_book(db: Session, book: Book) -> None:
    db.delete(book)
    db.commit()


def list_chapters(db: Session, book_id: int) -> list[Chapter]:
    stmt: Select[tuple[Chapter]] = (
        select(Chapter)
        .where(Chapter.book_id == book_id)
        .order_by(Chapter.order_index.asc(), Chapter.id.asc())
    )
    return list(db.scalars(stmt).all())


def create_chapter(db: Session, book_id: int, title: str, description: Optional[str], order_index: Optional[int]) -> Chapter:
    if order_index is None:
        stmt = select(func.max(Chapter.order_index)).where(Chapter.book_id == book_id)
        max_order = db.scalar(stmt) or 0
        order_index = int(max_order) + 1
    chapter = Chapter(
        book_id=book_id,
        title=title.strip(),
        description=description,
        order_index=order_index,
        content="",
    )
    db.add(chapter)
    db.commit()
    db.refresh(chapter)
    _sync_chapter_file(chapter)
    db.add(chapter)
    db.commit()
    db.refresh(chapter)
    return chapter


def get_chapter(db: Session, chapter_id: int) -> Optional[Chapter]:
    return db.get(Chapter, chapter_id)


def update_chapter(
    db: Session,
    chapter: Chapter,
    title: Optional[str] = None,
    description: Optional[str] = None,
    content: Optional[str] = None,
    order_index: Optional[int] = None,
    status: Optional[str] = None,
) -> Chapter:
    if title is not None:
        chapter.title = title.strip()
    if description is not None:
        chapter.description = description
    if content is not None:
        chapter.content = content
    if order_index is not None:
        chapter.order_index = order_index
    if status is not None:
        chapter.status = status
    _sync_chapter_file(chapter)
    db.add(chapter)
    db.commit()
    db.refresh(chapter)
    return chapter


def chapter_memory_context(db: Session, book_id: int, chapter_id: int, max_chars: int = 6000) -> str:
    chapters = list_chapters(db, book_id)
    previous = [c for c in chapters if c.id != chapter_id and (c.content or "").strip()]
    if not previous:
        return ""
    combined: list[str] = []
    total = 0
    for chapter in reversed(previous):
        snippet = (chapter.content or "").strip()
        if not snippet:
            continue
        piece = f"【{chapter.title}】\n{snippet[-2200:]}"
        piece_len = len(piece)
        if total + piece_len > max_chars:
            break
        combined.append(piece)
        total += piece_len
    return "\n\n".join(reversed(combined))
