from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class AppBaseModel(BaseModel):
    model_config = ConfigDict(protected_namespaces=())


class APIBridgeConfig(AppBaseModel):
    enabled: bool = False
    base_url: Optional[str] = None
    api_key: Optional[str] = None
    model: Optional[str] = None


class DatasetOut(AppBaseModel):
    id: int
    name: str
    path: str
    source_folder: str
    samples: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True, protected_namespaces=())


class LocalModelOut(AppBaseModel):
    id: int
    name: str
    path: str
    base_model_path: Optional[str]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True, protected_namespaces=())


class LocalModelRegister(AppBaseModel):
    name: str
    path: str
    base_model_path: Optional[str] = None


class TrainingStartRequest(AppBaseModel):
    source_folder: str = Field(..., description="作者 txt 文件夹")
    base_model_path: str = Field(..., description="本地基础模型路径")
    dataset_output_dir: str = Field(..., description="数据集输出目录")
    model_output_dir: str = Field(..., description="训练后模型输出目录")
    dataset_name: Optional[str] = None
    model_name: Optional[str] = None
    max_samples_per_book: int = 120
    chunk_min_chars: int = 600
    chunk_max_chars: int = 1600
    epochs: int = 1
    batch_size: int = 1
    grad_accumulation_steps: int = 8
    learning_rate: float = 2e-4
    lora_r: int = 16
    lora_alpha: int = 32
    lora_dropout: float = 0.05
    max_seq_length: int = 1024
    api_bridge: APIBridgeConfig = Field(default_factory=APIBridgeConfig)


class TrainingJobOut(AppBaseModel):
    id: int
    source_folder: str
    base_model_path: str
    dataset_output_dir: str
    model_output_dir: str
    status: str
    progress: float
    logs: str
    error_message: Optional[str]
    dataset_id: Optional[int]
    model_id: Optional[int]
    created_at: datetime
    updated_at: Optional[datetime]

    model_config = ConfigDict(from_attributes=True, protected_namespaces=())


class BookCreate(AppBaseModel):
    title: str
    description: Optional[str] = None
    model_path: Optional[str] = None


class BookUpdate(AppBaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    model_path: Optional[str] = None


class BookOut(AppBaseModel):
    id: int
    title: str
    description: Optional[str]
    model_path: Optional[str]
    created_at: datetime
    updated_at: Optional[datetime]

    model_config = ConfigDict(from_attributes=True, protected_namespaces=())


class ChapterCreate(AppBaseModel):
    title: str
    description: Optional[str] = None
    order_index: Optional[int] = None


class ChapterUpdate(AppBaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    content: Optional[str] = None
    order_index: Optional[int] = None
    status: Optional[str] = None


class ChapterOut(AppBaseModel):
    id: int
    book_id: int
    title: str
    description: Optional[str]
    content: str
    file_path: Optional[str]
    order_index: int
    word_count: int
    status: str
    created_at: datetime
    updated_at: Optional[datetime]

    model_config = ConfigDict(from_attributes=True, protected_namespaces=())


class GenerateChapterRequest(AppBaseModel):
    book_id: int
    chapter_id: int
    model_path: Optional[str] = None
    user_description: str
    target_words: int = Field(default=2400, ge=1500, le=3200)
    temperature: float = 0.85
    top_p: float = 0.9
    max_new_tokens: int = 2600
    use_api_context: bool = True
    api_bridge: APIBridgeConfig = Field(default_factory=APIBridgeConfig)


class GenerateStandaloneRequest(AppBaseModel):
    model_path: str
    outline: str
    memory_text: Optional[str] = None
    target_words: int = Field(default=2200, ge=1200, le=3200)
    temperature: float = 0.85
    top_p: float = 0.9
    max_new_tokens: int = 2600
    use_api_context: bool = True
    api_bridge: APIBridgeConfig = Field(default_factory=APIBridgeConfig)


class GenerationResponse(AppBaseModel):
    prompt: str
    generated_text: str
    used_model_path: str
