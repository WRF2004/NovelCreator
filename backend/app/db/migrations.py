from __future__ import annotations

from sqlalchemy import text

from app.db.database import engine


def _has_column(table_name: str, column_name: str) -> bool:
    with engine.connect() as conn:
        rows = conn.exec_driver_sql(f"PRAGMA table_info({table_name})").fetchall()
    return any(str(row[1]) == column_name for row in rows)


def _add_column_if_missing(table_name: str, column_name: str, column_sql: str) -> None:
    if _has_column(table_name, column_name):
        return
    with engine.begin() as conn:
        conn.execute(text(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_sql}"))


def run_migrations() -> None:
    # training_jobs 控制字段，用于中断/恢复能力
    _add_column_if_missing("training_jobs", "params_json", "TEXT")
    _add_column_if_missing("training_jobs", "dataset_path", "VARCHAR(1024)")
    _add_column_if_missing("training_jobs", "model_run_dir", "VARCHAR(1024)")

