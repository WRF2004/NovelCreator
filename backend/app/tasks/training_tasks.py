from __future__ import annotations

import shlex
import subprocess
import sys
import threading
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from threading import Lock
from typing import Optional

from sqlalchemy.orm import Session

from app.db.database import SessionLocal
from app.models import DatasetRecord, TrainingJob
from app.schemas import APIBridgeConfig
from app.services.dataset_service import build_dataset_from_txt_folder
from app.services.model_service import register_model
from app.services.path_service import ensure_dir, slugify


class TrainingInterruptedError(RuntimeError):
    pass


@dataclass
class JobRuntimeState:
    lock: Lock = field(default_factory=Lock)
    thread: Optional[threading.Thread] = None
    process: Optional[subprocess.Popen] = None
    interrupt_requested: bool = False
    params: dict = field(default_factory=dict)


_RUNTIME_LOCK = Lock()
_RUNTIME_STATES: dict[int, JobRuntimeState] = {}


def _get_runtime_state(job_id: int) -> JobRuntimeState:
    with _RUNTIME_LOCK:
        state = _RUNTIME_STATES.get(job_id)
        if state is None:
            state = JobRuntimeState()
            _RUNTIME_STATES[job_id] = state
        return state


def _append_log(job: TrainingJob, message: str) -> None:
    now = datetime.now().strftime("%H:%M:%S")
    job.logs = f"{job.logs}\n[{now}] {message}".strip()


def _update_job(
    db: Session,
    job: TrainingJob,
    *,
    status: Optional[str] = None,
    progress: Optional[float] = None,
    log: Optional[str] = None,
    error: Optional[str] = None,
    dataset_path: Optional[str] = None,
    model_run_dir: Optional[str] = None,
) -> None:
    if status is not None:
        job.status = status
    if progress is not None:
        job.progress = max(0.0, min(1.0, progress))
    if log:
        _append_log(job, log)
    if error is not None:
        job.error_message = error
    if dataset_path is not None:
        job.dataset_path = dataset_path
    if model_run_dir is not None:
        job.model_run_dir = model_run_dir
    db.add(job)
    db.commit()
    db.refresh(job)


def _is_interrupted(job_id: int) -> bool:
    state = _get_runtime_state(job_id)
    with state.lock:
        return state.interrupt_requested


def _raise_if_interrupted(job_id: int) -> None:
    if _is_interrupted(job_id):
        raise TrainingInterruptedError("训练已被用户中断")


def _safe_terminate_process(process: subprocess.Popen) -> None:
    if process.poll() is not None:
        return
    try:
        process.terminate()
        process.wait(timeout=8)
    except subprocess.TimeoutExpired:
        process.kill()
        try:
            process.wait(timeout=4)
        except subprocess.TimeoutExpired:
            pass


def request_interrupt(job_id: int) -> bool:
    state = _get_runtime_state(job_id)
    with state.lock:
        thread = state.thread
        process = state.process
        state.interrupt_requested = True

    running = bool(thread and thread.is_alive())
    if process is not None:
        _safe_terminate_process(process)
    return running


def is_job_running(job_id: int) -> bool:
    state = _get_runtime_state(job_id)
    with state.lock:
        return bool(state.thread and state.thread.is_alive())


def cache_params(job_id: int, params: dict) -> None:
    state = _get_runtime_state(job_id)
    with state.lock:
        state.params = dict(params)


def get_cached_params(job_id: int) -> Optional[dict]:
    state = _get_runtime_state(job_id)
    with state.lock:
        if not state.params:
            return None
        return dict(state.params)


def _normalize_params(raw_params: dict) -> dict:
    defaults = {
        "max_samples_per_book": 120,
        "chunk_min_chars": 600,
        "chunk_max_chars": 1600,
        "epochs": 1,
        "batch_size": 1,
        "grad_accumulation_steps": 8,
        "learning_rate": 2e-4,
        "lora_r": 16,
        "lora_alpha": 32,
        "lora_dropout": 0.05,
        "max_seq_length": 1024,
        "dataset_name": None,
        "model_name": None,
    }
    params = {**defaults, **dict(raw_params)}
    bridge = params.get("api_bridge")
    if isinstance(bridge, APIBridgeConfig):
        pass
    elif isinstance(bridge, dict):
        params["api_bridge"] = APIBridgeConfig(**bridge)
    else:
        params["api_bridge"] = APIBridgeConfig()
    return params


def _resolve_dataset_for_job(db: Session, job: TrainingJob, params: dict, resume_mode: bool) -> tuple[Path, int]:
    if resume_mode and job.dataset_path:
        path = Path(job.dataset_path).expanduser().resolve()
        if path.exists():
            sample_count = 0
            if job.dataset:
                sample_count = job.dataset.samples
            else:
                with path.open("r", encoding="utf-8", errors="ignore") as f:
                    sample_count = sum(1 for _ in f)
            _update_job(
                db,
                job,
                status="training",
                progress=max(job.progress, 0.35),
                log=f"复用已生成数据集: {path}",
            )
            return path, sample_count

    _raise_if_interrupted(job.id)
    _update_job(db, job, status="preparing_dataset", progress=max(job.progress, 0.02), log="开始生成训练数据集...")
    ds_result = build_dataset_from_txt_folder(
        source_folder=params["source_folder"],
        output_dir=params["dataset_output_dir"],
        dataset_name=params.get("dataset_name"),
        max_samples_per_book=params["max_samples_per_book"],
        chunk_min_chars=params["chunk_min_chars"],
        chunk_max_chars=params["chunk_max_chars"],
        api_bridge=params["api_bridge"],
    )
    dataset_record = DatasetRecord(
        name=ds_result.dataset_name,
        path=str(ds_result.dataset_file),
        source_folder=str(Path(params["source_folder"]).resolve()),
        samples=ds_result.sample_count,
    )
    db.add(dataset_record)
    db.commit()
    db.refresh(dataset_record)

    job.dataset_id = dataset_record.id
    _update_job(
        db,
        job,
        status="training",
        progress=max(job.progress, 0.35),
        log=f"数据集生成完成，共 {ds_result.sample_count} 条样本。",
        dataset_path=str(ds_result.dataset_file),
    )
    return ds_result.dataset_file, ds_result.sample_count


def _resolve_model_dir_for_job(job: TrainingJob, params: dict, resume_mode: bool) -> Path:
    if resume_mode and job.model_run_dir:
        path = Path(job.model_run_dir).expanduser().resolve()
        path.mkdir(parents=True, exist_ok=True)
        return path

    model_root = ensure_dir(params["model_output_dir"])
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    model_name = slugify(params.get("model_name") or f"lora_{Path(params['source_folder']).name}_{timestamp}")
    path = model_root / model_name
    path.mkdir(parents=True, exist_ok=True)
    return path


def _find_latest_checkpoint(model_dir: Path) -> Optional[Path]:
    checkpoint_root = model_dir / "checkpoints"
    if not checkpoint_root.exists():
        return None
    checkpoints = [p for p in checkpoint_root.glob("checkpoint-*") if p.is_dir()]
    if not checkpoints:
        return None

    def step_key(path: Path) -> int:
        name = path.name
        if "-" not in name:
            return -1
        suffix = name.split("-", 1)[1]
        return int(suffix) if suffix.isdigit() else -1

    return sorted(checkpoints, key=step_key)[-1]


def _build_training_command(params: dict, dataset_path: Path, model_dir: Path, resume_mode: bool) -> list[str]:
    script_path = Path(__file__).resolve().parents[2] / "scripts" / "train_lora.py"
    cmd = [
        sys.executable,
        str(script_path),
        "--base-model-path",
        params["base_model_path"],
        "--dataset-path",
        str(dataset_path),
        "--output-dir",
        str(model_dir),
        "--epochs",
        str(params["epochs"]),
        "--batch-size",
        str(params["batch_size"]),
        "--grad-accumulation-steps",
        str(params["grad_accumulation_steps"]),
        "--learning-rate",
        str(params["learning_rate"]),
        "--lora-r",
        str(params["lora_r"]),
        "--lora-alpha",
        str(params["lora_alpha"]),
        "--lora-dropout",
        str(params["lora_dropout"]),
        "--max-seq-length",
        str(params["max_seq_length"]),
    ]
    if resume_mode:
        checkpoint = _find_latest_checkpoint(model_dir)
        if checkpoint is not None:
            cmd.extend(["--resume-from-checkpoint", str(checkpoint)])
    return cmd


def _run_training_pipeline(job_id: int, raw_params: dict, resume_mode: bool = False) -> None:
    db = SessionLocal()
    state = _get_runtime_state(job_id)
    params = _normalize_params(raw_params)
    try:
        job = db.get(TrainingJob, job_id)
        if not job:
            return

        _raise_if_interrupted(job_id)
        mode_text = "恢复训练" if resume_mode else "开始训练"
        _update_job(
            db,
            job,
            status="resuming" if resume_mode else "preparing_dataset",
            progress=max(job.progress, 0.01),
            log=f"{mode_text}流程启动",
            error=None,
        )

        dataset_path, _sample_count = _resolve_dataset_for_job(db, job, params, resume_mode=resume_mode)
        _raise_if_interrupted(job_id)

        model_dir = _resolve_model_dir_for_job(job, params, resume_mode=resume_mode)
        _update_job(db, job, model_run_dir=str(model_dir))

        cmd = _build_training_command(params, dataset_path=dataset_path, model_dir=model_dir, resume_mode=resume_mode)
        _update_job(db, job, status="training", log=f"执行训练命令: {shlex.join(cmd)}")

        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True,
            bufsize=1,
        )
        with state.lock:
            state.process = process

        assert process.stdout is not None
        for line in process.stdout:
            line = line.rstrip()
            if _is_interrupted(job_id):
                _safe_terminate_process(process)
                break
            if not line:
                continue
            if line.startswith("PROGRESS="):
                try:
                    pct = float(line.split("=", 1)[1])
                    _update_job(db, job, progress=max(job.progress, 0.35 + pct * 0.6))
                except ValueError:
                    pass
                continue
            _update_job(db, job, log=line)

        code = process.wait()
        with state.lock:
            state.process = None

        _raise_if_interrupted(job_id)
        if code != 0:
            raise RuntimeError(f"训练脚本退出码 {code}")

        model_name = Path(model_dir).name
        model_record = register_model(
            db,
            model_path=str(model_dir),
            name=model_name,
            base_model_path=str(Path(params["base_model_path"]).resolve()),
        )
        job.model_id = model_record.id
        _update_job(
            db,
            job,
            status="completed",
            progress=1.0,
            log=f"训练完成。模型已保存到 {model_dir}",
            error=None,
        )
    except TrainingInterruptedError:
        job = db.get(TrainingJob, job_id)
        if job:
            _update_job(
                db,
                job,
                status="interrupted",
                progress=job.progress,
                log="训练已中断，可稍后点击恢复继续。",
            )
    except Exception as exc:  # noqa: BLE001
        job = db.get(TrainingJob, job_id)
        if job:
            _update_job(
                db,
                job,
                status="failed",
                progress=job.progress,
                error=str(exc),
                log=f"训练失败: {exc}",
            )
    finally:
        with state.lock:
            state.process = None
            state.thread = None
        db.close()


def start_training_async(job_id: int, params: dict, resume_mode: bool = False) -> bool:
    state = _get_runtime_state(job_id)
    normalized = _normalize_params(params)
    with state.lock:
        if state.thread and state.thread.is_alive():
            return False
        state.interrupt_requested = False
        state.params = dict(normalized)

    thread = threading.Thread(
        target=_run_training_pipeline,
        args=(job_id, normalized, resume_mode),
        daemon=True,
    )
    with state.lock:
        state.thread = thread
    thread.start()
    return True

