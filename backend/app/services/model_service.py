from __future__ import annotations

from pathlib import Path
from typing import Optional

from sqlalchemy import Select, select
from sqlalchemy.orm import Session

from app.models import LocalModel


def list_models(db: Session) -> list[LocalModel]:
    stmt: Select[tuple[LocalModel]] = select(LocalModel).order_by(LocalModel.created_at.desc(), LocalModel.id.desc())
    return list(db.scalars(stmt).all())


def get_model_by_path(db: Session, path: str) -> Optional[LocalModel]:
    stmt = select(LocalModel).where(LocalModel.path == path)
    return db.scalar(stmt)


def register_model(
    db: Session,
    model_path: str,
    name: Optional[str] = None,
    base_model_path: Optional[str] = None,
) -> LocalModel:
    resolved = str(Path(model_path).expanduser().resolve())
    existing = get_model_by_path(db, resolved)
    if existing:
        return existing
    model = LocalModel(
        name=name or Path(resolved).name,
        path=resolved,
        base_model_path=base_model_path,
    )
    db.add(model)
    db.commit()
    db.refresh(model)
    return model
