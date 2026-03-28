from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.schemas import (
    BookCreate,
    BookOut,
    BookUpdate,
    ChapterCreate,
    ChapterOut,
    ChapterUpdate,
)
from app.services.book_service import (
    create_book,
    create_chapter,
    delete_book,
    get_book,
    get_chapter,
    list_books,
    list_chapters,
    update_book,
    update_chapter,
)

router = APIRouter(prefix="/books", tags=["books"])


@router.get("", response_model=list[BookOut])
def api_list_books(db: Session = Depends(get_db)):
    return list_books(db)


@router.post("", response_model=BookOut)
def api_create_book(payload: BookCreate, db: Session = Depends(get_db)):
    if not payload.title.strip():
        raise HTTPException(status_code=400, detail="书名不能为空")
    return create_book(
        db,
        title=payload.title,
        description=payload.description,
        model_path=payload.model_path,
    )


@router.get("/{book_id}", response_model=BookOut)
def api_get_book(book_id: int, db: Session = Depends(get_db)):
    book = get_book(db, book_id)
    if not book:
        raise HTTPException(status_code=404, detail="书籍不存在")
    return book


@router.patch("/{book_id}", response_model=BookOut)
def api_update_book(book_id: int, payload: BookUpdate, db: Session = Depends(get_db)):
    book = get_book(db, book_id)
    if not book:
        raise HTTPException(status_code=404, detail="书籍不存在")
    return update_book(
        db,
        book,
        title=payload.title,
        description=payload.description,
        model_path=payload.model_path,
    )


@router.delete("/{book_id}")
def api_delete_book(book_id: int, db: Session = Depends(get_db)):
    book = get_book(db, book_id)
    if not book:
        raise HTTPException(status_code=404, detail="书籍不存在")
    delete_book(db, book)
    return {"ok": True}


@router.get("/{book_id}/chapters", response_model=list[ChapterOut])
def api_list_chapters(book_id: int, db: Session = Depends(get_db)):
    book = get_book(db, book_id)
    if not book:
        raise HTTPException(status_code=404, detail="书籍不存在")
    return list_chapters(db, book_id)


@router.post("/{book_id}/chapters", response_model=ChapterOut)
def api_create_chapter(book_id: int, payload: ChapterCreate, db: Session = Depends(get_db)):
    book = get_book(db, book_id)
    if not book:
        raise HTTPException(status_code=404, detail="书籍不存在")
    if not payload.title.strip():
        raise HTTPException(status_code=400, detail="章节名不能为空")
    return create_chapter(
        db,
        book_id=book_id,
        title=payload.title,
        description=payload.description,
        order_index=payload.order_index,
    )


@router.get("/chapters/{chapter_id}", response_model=ChapterOut)
def api_get_chapter(chapter_id: int, db: Session = Depends(get_db)):
    chapter = get_chapter(db, chapter_id)
    if not chapter:
        raise HTTPException(status_code=404, detail="章节不存在")
    return chapter


@router.patch("/chapters/{chapter_id}", response_model=ChapterOut)
def api_update_chapter(chapter_id: int, payload: ChapterUpdate, db: Session = Depends(get_db)):
    chapter = get_chapter(db, chapter_id)
    if not chapter:
        raise HTTPException(status_code=404, detail="章节不存在")
    return update_chapter(
        db,
        chapter,
        title=payload.title,
        description=payload.description,
        content=payload.content,
        order_index=payload.order_index,
        status=payload.status,
    )

