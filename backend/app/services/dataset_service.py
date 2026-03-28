from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable, Optional

from app.schemas import APIBridgeConfig
from app.services.api_bridge_service import APIBridgeError, call_chat_completion
from app.services.path_service import ensure_dir, require_existing_dir, slugify


@dataclass
class DatasetBuildResult:
    dataset_name: str
    dataset_dir: Path
    dataset_file: Path
    sample_count: int


def _read_txt(path: Path) -> str:
    encodings = ["utf-8", "utf-16", "gb18030", "gbk", "big5"]
    for encoding in encodings:
        try:
            return path.read_text(encoding=encoding)
        except UnicodeDecodeError:
            continue
    return path.read_bytes().decode("utf-8", errors="ignore")


def _clean_text(text: str) -> str:
    text = text.replace("\r\n", "\n")
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _split_chunks(text: str, chunk_min_chars: int, chunk_max_chars: int) -> list[str]:
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    chunks: list[str] = []
    current = []
    current_len = 0

    for para in paragraphs:
        para_len = len(para)
        if para_len > chunk_max_chars:
            # 超长段落按句号粗切
            pieces = re.split(r"(?<=[。！？!?])", para)
            for piece in pieces:
                piece = piece.strip()
                if not piece:
                    continue
                if current_len + len(piece) > chunk_max_chars and current:
                    chunks.append("".join(current).strip())
                    current = []
                    current_len = 0
                current.append(piece)
                current_len += len(piece)
            continue

        if current_len + para_len > chunk_max_chars and current:
            chunks.append("\n\n".join(current).strip())
            current = []
            current_len = 0

        current.append(para)
        current_len += para_len

        if current_len >= chunk_min_chars:
            chunks.append("\n\n".join(current).strip())
            current = []
            current_len = 0

    if current:
        chunks.append("\n\n".join(current).strip())
    return [c for c in chunks if len(c) >= min(120, chunk_min_chars // 2)]


def _parse_instruction_output(text: str) -> tuple[str, str]:
    # 优先解析 JSON，再回退到纯文本
    json_match = re.search(r"\{.*\}", text, flags=re.DOTALL)
    if json_match:
        try:
            payload = json.loads(json_match.group(0))
            instruction = str(payload.get("instruction", "")).strip()
            writing_input = str(payload.get("input", "")).strip()
            if instruction:
                return instruction, writing_input
        except json.JSONDecodeError:
            pass
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if len(lines) >= 2:
        return lines[0], "\n".join(lines[1:])
    return "根据设定续写下一段，保持原文风格与叙事节奏。", ""


def _build_sample(
    chunk: str,
    book_title: str,
    api_bridge: APIBridgeConfig,
) -> dict[str, str]:
    default_instruction = f"模仿《{book_title}》的文风，按给定情节说明写出小说正文。"
    default_input = "请突出人物心理、场景细节和叙事连贯性。"

    if api_bridge.enabled:
        system_prompt = (
            "你是小说训练数据构造助手。根据给定作品片段，返回 JSON："
            '{"instruction":"...","input":"..."}。'
            "instruction 是可用于训练的写作任务，input 是该任务的情节补充。"
            "不要输出除 JSON 之外的内容。"
        )
        user_prompt = f"作品名：{book_title}\n片段：\n{chunk[:2400]}"
        try:
            result = call_chat_completion(
                config=api_bridge,
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                temperature=0.4,
                max_tokens=300,
            )
            instruction, writing_input = _parse_instruction_output(result)
            return {
                "instruction": instruction or default_instruction,
                "input": writing_input or default_input,
                "output": chunk.strip(),
            }
        except APIBridgeError:
            # 回退本地模板
            pass

    return {
        "instruction": default_instruction,
        "input": default_input,
        "output": chunk.strip(),
    }


def _iter_txt_files(folder: Path) -> Iterable[Path]:
    for path in sorted(folder.glob("*.txt")):
        if path.is_file():
            yield path


def build_dataset_from_txt_folder(
    source_folder: str,
    output_dir: str,
    dataset_name: Optional[str],
    max_samples_per_book: int,
    chunk_min_chars: int,
    chunk_max_chars: int,
    api_bridge: APIBridgeConfig,
) -> DatasetBuildResult:
    source_dir = require_existing_dir(source_folder)
    out_root = ensure_dir(output_dir)

    txt_files = list(_iter_txt_files(source_dir))
    if not txt_files:
        raise ValueError(f"未在目录中找到 txt 文件: {source_dir}")

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    ds_name = slugify(dataset_name or f"dataset_{source_dir.name}_{timestamp}")
    dataset_dir = out_root / ds_name
    dataset_dir.mkdir(parents=True, exist_ok=True)
    dataset_file = dataset_dir / "train.jsonl"
    meta_file = dataset_dir / "meta.json"

    samples: list[dict[str, str]] = []
    for txt_path in txt_files:
        raw = _read_txt(txt_path)
        content = _clean_text(raw)
        if len(content) < 400:
            continue
        chunks = _split_chunks(content, chunk_min_chars=chunk_min_chars, chunk_max_chars=chunk_max_chars)
        chunks = chunks[:max_samples_per_book]
        for chunk in chunks:
            sample = _build_sample(chunk=chunk, book_title=txt_path.stem, api_bridge=api_bridge)
            samples.append(sample)

    if not samples:
        raise ValueError("无法从 txt 中生成训练样本，请检查文本内容是否为空。")

    with dataset_file.open("w", encoding="utf-8") as f:
        for row in samples:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")

    meta = {
        "dataset_name": ds_name,
        "source_folder": str(source_dir),
        "dataset_file": str(dataset_file),
        "sample_count": len(samples),
        "created_at": datetime.now().isoformat(),
        "chunk_min_chars": chunk_min_chars,
        "chunk_max_chars": chunk_max_chars,
    }
    meta_file.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")

    return DatasetBuildResult(
        dataset_name=ds_name,
        dataset_dir=dataset_dir,
        dataset_file=dataset_file,
        sample_count=len(samples),
    )
