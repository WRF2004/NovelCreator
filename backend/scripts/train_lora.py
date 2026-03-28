from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Iterable

import torch
from datasets import load_dataset
from peft import LoraConfig, TaskType, get_peft_model, prepare_model_for_kbit_training
from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    BitsAndBytesConfig,
    DataCollatorForLanguageModeling,
    Trainer,
    TrainerCallback,
    TrainingArguments,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="QLoRA training for local novel model")
    parser.add_argument("--base-model-path", required=True)
    parser.add_argument("--dataset-path", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--epochs", type=int, default=1)
    parser.add_argument("--batch-size", type=int, default=1)
    parser.add_argument("--grad-accumulation-steps", type=int, default=8)
    parser.add_argument("--learning-rate", type=float, default=2e-4)
    parser.add_argument("--lora-r", type=int, default=16)
    parser.add_argument("--lora-alpha", type=int, default=32)
    parser.add_argument("--lora-dropout", type=float, default=0.05)
    parser.add_argument("--max-seq-length", type=int, default=1024)
    parser.add_argument("--resume-from-checkpoint", type=str, default="")
    return parser.parse_args()


def find_linear_target_modules(model) -> list[str]:
    linear_names: set[str] = set()
    candidate_keywords = {
        "q_proj",
        "k_proj",
        "v_proj",
        "o_proj",
        "gate_proj",
        "up_proj",
        "down_proj",
        "wq",
        "wk",
        "wv",
        "wo",
    }
    for name, module in model.named_modules():
        if module.__class__.__name__.lower() not in {"linear", "linear4bit", "linear8bitlt"}:
            continue
        parts = name.split(".")
        leaf = parts[-1]
        if leaf in candidate_keywords or any(k in leaf for k in candidate_keywords):
            linear_names.add(leaf)

    if not linear_names:
        # 回退常见模块名
        return ["q_proj", "k_proj", "v_proj", "o_proj"]
    return sorted(linear_names)


def build_prompt(instruction: str, writing_input: str, output: str) -> str:
    return (
        "### 写作任务\n"
        f"{instruction.strip()}\n\n"
        "### 情节补充\n"
        f"{writing_input.strip()}\n\n"
        "### 正文\n"
        f"{output.strip()}"
    )


class ProgressCallback(TrainerCallback):
    def on_step_end(self, args, state, control, **kwargs):  # noqa: ANN001, ANN201
        if state.max_steps and state.max_steps > 0:
            progress = state.global_step / state.max_steps
            print(f"PROGRESS={progress:.4f}", flush=True)


def main() -> None:
    args = parse_args()
    output_dir = Path(args.output_dir).expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    dtype = torch.float16 if torch.cuda.is_available() else torch.float32
    quant_config = None
    if torch.cuda.is_available():
        try:
            quant_config = BitsAndBytesConfig(
                load_in_4bit=True,
                bnb_4bit_quant_type="nf4",
                bnb_4bit_use_double_quant=True,
                bnb_4bit_compute_dtype=torch.float16,
            )
        except Exception as exc:  # noqa: BLE001
            print(f"警告: 4bit 量化配置失败，将回退常规加载。原因: {exc}", flush=True)
            quant_config = None

    tokenizer = AutoTokenizer.from_pretrained(args.base_model_path, trust_remote_code=True, use_fast=False)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    model_kwargs = dict(
        trust_remote_code=True,
        torch_dtype=dtype,
        device_map="auto" if torch.cuda.is_available() else None,
    )
    if quant_config is not None:
        model_kwargs["quantization_config"] = quant_config

    model = AutoModelForCausalLM.from_pretrained(
        args.base_model_path,
        **model_kwargs,
    )
    if torch.cuda.is_available() and quant_config is not None:
        model = prepare_model_for_kbit_training(model)

    target_modules = find_linear_target_modules(model)
    lora_config = LoraConfig(
        task_type=TaskType.CAUSAL_LM,
        r=args.lora_r,
        lora_alpha=args.lora_alpha,
        lora_dropout=args.lora_dropout,
        bias="none",
        target_modules=target_modules,
    )
    model = get_peft_model(model, lora_config)
    model.print_trainable_parameters()

    dataset = load_dataset("json", data_files=str(Path(args.dataset_path).resolve()), split="train")
    original_size = len(dataset)
    if original_size == 0:
        raise RuntimeError("dataset is empty")

    def format_row(row: dict) -> dict:
        text = build_prompt(
            instruction=str(row.get("instruction", "")),
            writing_input=str(row.get("input", "")),
            output=str(row.get("output", "")),
        )
        return {"text": text}

    dataset = dataset.map(format_row, remove_columns=dataset.column_names)

    def tokenize_row(row: dict) -> dict:
        tokenized = tokenizer(
            row["text"],
            max_length=args.max_seq_length,
            truncation=True,
            padding=False,
        )
        tokenized["labels"] = tokenized["input_ids"].copy()
        return tokenized

    tokenized_dataset = dataset.map(tokenize_row, remove_columns=dataset.column_names)

    train_args = TrainingArguments(
        output_dir=str(output_dir / "checkpoints"),
        num_train_epochs=args.epochs,
        per_device_train_batch_size=args.batch_size,
        gradient_accumulation_steps=args.grad_accumulation_steps,
        learning_rate=args.learning_rate,
        logging_steps=10,
        save_strategy="epoch",
        report_to="none",
        remove_unused_columns=False,
        fp16=torch.cuda.is_available(),
        bf16=False,
        dataloader_num_workers=0,
    )

    trainer = Trainer(
        model=model,
        args=train_args,
        train_dataset=tokenized_dataset,
        tokenizer=tokenizer,
        data_collator=DataCollatorForLanguageModeling(tokenizer=tokenizer, mlm=False),
        callbacks=[ProgressCallback()],
    )
    resume_checkpoint = args.resume_from_checkpoint.strip()
    if resume_checkpoint:
        trainer.train(resume_from_checkpoint=resume_checkpoint)
    else:
        trainer.train()
    print("PROGRESS=1.0000", flush=True)

    model.save_pretrained(str(output_dir))
    tokenizer.save_pretrained(str(output_dir))

    metadata = {
        "base_model_path": str(Path(args.base_model_path).resolve()),
        "dataset_path": str(Path(args.dataset_path).resolve()),
        "samples": original_size,
        "epochs": args.epochs,
        "batch_size": args.batch_size,
        "grad_accumulation_steps": args.grad_accumulation_steps,
        "learning_rate": args.learning_rate,
        "lora": {
            "r": args.lora_r,
            "alpha": args.lora_alpha,
            "dropout": args.lora_dropout,
            "target_modules": target_modules,
        },
        "max_seq_length": args.max_seq_length,
    }
    (output_dir / "training_meta.json").write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"训练完成，模型已保存到: {output_dir}", flush=True)


if __name__ == "__main__":
    main()
