from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.models import DatasetRecord, LocalModel, TrainingJob
from app.schemas import DatasetOut, LocalModelOut, LocalModelRegister, TrainingJobOut, TrainingStartRequest
from app.services.path_service import require_existing_dir, require_existing_path
from app.tasks.training_tasks import (
    get_cached_params,
    is_job_running,
    request_interrupt,
    start_training_async,
)

router = APIRouter(prefix="/training", tags=["training"])


TERMINAL_STATUS = {"completed", "failed", "interrupted", "cancelled"}
RUNNING_STATUS = {"queued", "preparing_dataset", "resuming", "training", "interrupting"}
RESUMABLE_STATUS = {"interrupted", "failed"}


def _append_log(job: TrainingJob, message: str) -> None:
    now = datetime.now().strftime("%H:%M:%S")
    job.logs = f"{job.logs}\n[{now}] {message}".strip()


def _load_job_params(job: TrainingJob) -> Optional[dict]:
    if not job.params_json:
        return None
    try:
        payload = json.loads(job.params_json)
        if isinstance(payload, dict):
            return payload
    except json.JSONDecodeError:
        return None
    return None


@router.post("/start", response_model=TrainingJobOut)
def start_training(payload: TrainingStartRequest, db: Session = Depends(get_db)):
    try:
        source_folder = str(require_existing_dir(payload.source_folder))
        base_model_path = str(require_existing_path(payload.base_model_path))
        dataset_output_dir = str(Path(payload.dataset_output_dir).expanduser().resolve())
        model_output_dir = str(Path(payload.model_output_dir).expanduser().resolve())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    params = payload.model_dump()
    params["source_folder"] = source_folder
    params["base_model_path"] = base_model_path
    params["dataset_output_dir"] = dataset_output_dir
    params["model_output_dir"] = model_output_dir

    job = TrainingJob(
        source_folder=source_folder,
        base_model_path=base_model_path,
        dataset_output_dir=dataset_output_dir,
        model_output_dir=model_output_dir,
        status="queued",
        progress=0.0,
        logs="",
        params_json=json.dumps(params, ensure_ascii=False),
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    started = start_training_async(job.id, params=params, resume_mode=False)
    if not started:
        raise HTTPException(status_code=409, detail="训练任务启动失败，任务可能正在运行")
    return job


@router.post("/jobs/{job_id}/interrupt", response_model=TrainingJobOut)
def interrupt_training_job(job_id: int, db: Session = Depends(get_db)):
    job = db.get(TrainingJob, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="训练任务不存在")
    if job.status in TERMINAL_STATUS:
        raise HTTPException(status_code=400, detail=f"当前状态为 {job.status}，无法中断")

    running = request_interrupt(job_id)
    _append_log(job, "收到中断请求，正在停止训练进程...")
    if running:
        job.status = "interrupting"
    else:
        job.status = "interrupted"
        _append_log(job, "任务已中断。")
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


@router.post("/jobs/{job_id}/resume", response_model=TrainingJobOut)
def resume_training_job(job_id: int, db: Session = Depends(get_db)):
    job = db.get(TrainingJob, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="训练任务不存在")
    if is_job_running(job_id):
        raise HTTPException(status_code=409, detail="任务仍在运行中，不能恢复")
    if job.status not in RESUMABLE_STATUS:
        raise HTTPException(status_code=400, detail=f"当前状态为 {job.status}，不可恢复")

    params = get_cached_params(job_id) or _load_job_params(job)
    if not params:
        raise HTTPException(status_code=400, detail="缺少训练参数，无法恢复该任务")

    started = start_training_async(job.id, params=params, resume_mode=True)
    if not started:
        raise HTTPException(status_code=409, detail="恢复任务启动失败，任务可能正在运行")

    job.status = "resuming"
    job.error_message = None
    _append_log(job, "收到恢复请求，正在尝试从 checkpoint 继续训练。")
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


@router.get("/jobs", response_model=list[TrainingJobOut])
def list_training_jobs(db: Session = Depends(get_db)):
    stmt = select(TrainingJob).order_by(TrainingJob.created_at.desc(), TrainingJob.id.desc())
    return list(db.scalars(stmt).all())


@router.get("/jobs/{job_id}", response_model=TrainingJobOut)
def get_training_job(job_id: int, db: Session = Depends(get_db)):
    job = db.get(TrainingJob, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="训练任务不存在")
    return job


@router.get("/datasets", response_model=list[DatasetOut])
def list_datasets(db: Session = Depends(get_db)):
    stmt = select(DatasetRecord).order_by(DatasetRecord.created_at.desc(), DatasetRecord.id.desc())
    return list(db.scalars(stmt).all())


@router.get("/models", response_model=list[LocalModelOut])
def list_models(db: Session = Depends(get_db)):
    stmt = select(LocalModel).order_by(LocalModel.created_at.desc(), LocalModel.id.desc())
    return list(db.scalars(stmt).all())


@router.post("/models/register", response_model=LocalModelOut)
def register_existing_model(payload: LocalModelRegister, db: Session = Depends(get_db)):
    path = str(require_existing_path(payload.path))
    existing = db.scalar(select(LocalModel).where(LocalModel.path == path))
    if existing:
        return existing
    model = LocalModel(
        name=payload.name,
        path=path,
        base_model_path=payload.base_model_path,
    )
    db.add(model)
    db.commit()
    db.refresh(model)
    return model

