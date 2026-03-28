from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from threading import Lock
from typing import Any


@dataclass
class LoadedModel:
    tokenizer: Any
    model: Any
    path: str


_MODEL_CACHE: dict[str, LoadedModel] = {}
_MODEL_LOCK = Lock()


def _resolve_model_path(model_path: str) -> Path:
    path = Path(model_path).expanduser().resolve()
    if not path.exists():
        raise ValueError(f"模型路径不存在: {path}")
    return path


def _load_base_model(path: Path):
    try:
        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer
    except ModuleNotFoundError as exc:
        raise RuntimeError("缺少推理依赖，请先安装 backend/requirements.txt") from exc

    dtype = torch.float16 if torch.cuda.is_available() else torch.float32
    tokenizer = AutoTokenizer.from_pretrained(path.as_posix(), trust_remote_code=True, use_fast=False)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
    model = AutoModelForCausalLM.from_pretrained(
        path.as_posix(),
        torch_dtype=dtype,
        trust_remote_code=True,
        device_map="auto" if torch.cuda.is_available() else None,
    )
    return tokenizer, model


def _load_model(path: Path) -> LoadedModel:
    adapter_config = path / "adapter_config.json"
    if adapter_config.exists():
        try:
            from peft import PeftModel
        except ModuleNotFoundError as exc:
            raise RuntimeError("检测到 LoRA 适配器，但缺少 peft 依赖，请安装 backend/requirements.txt") from exc

        payload = json.loads(adapter_config.read_text(encoding="utf-8"))
        base_model_path = payload.get("base_model_name_or_path")
        if not base_model_path:
            raise ValueError(f"LoRA 适配器缺少 base_model_name_or_path: {path}")
        base_path = Path(base_model_path).expanduser().resolve()
        tokenizer, base_model = _load_base_model(base_path)
        model = PeftModel.from_pretrained(base_model, path.as_posix())
        model.eval()
        return LoadedModel(tokenizer=tokenizer, model=model, path=str(path))

    tokenizer, model = _load_base_model(path)
    model.eval()
    return LoadedModel(tokenizer=tokenizer, model=model, path=str(path))


def get_or_load_model(model_path: str) -> LoadedModel:
    resolved = str(_resolve_model_path(model_path))
    with _MODEL_LOCK:
        if resolved in _MODEL_CACHE:
            return _MODEL_CACHE[resolved]
        loaded = _load_model(Path(resolved))
        _MODEL_CACHE[resolved] = loaded
        return loaded


def generate_text(
    model_path: str,
    prompt: str,
    max_new_tokens: int = 2600,
    temperature: float = 0.85,
    top_p: float = 0.9,
) -> str:
    try:
        import torch
    except ModuleNotFoundError as exc:
        raise RuntimeError("缺少 torch 依赖，请先安装 backend/requirements.txt") from exc

    loaded = get_or_load_model(model_path)
    tokenizer = loaded.tokenizer
    model = loaded.model

    inputs = tokenizer(prompt, return_tensors="pt")
    if torch.cuda.is_available():
        inputs = {k: v.to(model.device) for k, v in inputs.items()}

    with torch.no_grad():
        output_ids = model.generate(
            **inputs,
            do_sample=True,
            temperature=temperature,
            top_p=top_p,
            max_new_tokens=max_new_tokens,
            repetition_penalty=1.05,
            eos_token_id=tokenizer.eos_token_id,
            pad_token_id=tokenizer.pad_token_id,
        )
    generated = tokenizer.decode(output_ids[0][inputs["input_ids"].shape[-1] :], skip_special_tokens=True)
    return generated.strip()
