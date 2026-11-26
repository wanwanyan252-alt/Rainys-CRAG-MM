"""Validate and optionally train a 4-bit LoRA adapter for P5 multimodal SFT."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import random
import re
from typing import Any


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [
        json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def validate_config(config: dict[str, Any], repo_root: Path) -> dict[str, Any]:
    required = [
        "model_name_or_path", "train_file", "eval_file", "output_dir",
        "lora_target_modules",
    ]
    missing = [key for key in required if key not in config]
    if missing:
        raise SystemExit(f"Missing config keys: {missing}")
    train_path = repo_root / config["train_file"]
    eval_path = repo_root / config["eval_file"]
    train_records = read_jsonl(train_path)
    eval_records = read_jsonl(eval_path)
    if not train_records or not eval_records:
        raise SystemExit("Train and eval JSONL files must be non-empty")
    for record in train_records[:20] + eval_records[:20]:
        image = repo_root / record["image"]
        if not image.is_file():
            raise SystemExit(f"Missing image: {image}")
        if record["messages"][-1]["role"] != "assistant":
            raise SystemExit(f"Invalid message target: {record['id']}")
    return {
        "train_path": train_path,
        "eval_path": eval_path,
        "train_records": train_records,
        "eval_records": eval_records,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument(
        "--smoke-test",
        action="store_true",
        help="Load the model and execute exactly one training step.",
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        help="Resume from the latest complete checkpoint in output_dir.",
    )
    args = parser.parse_args()
    repo_root = Path(__file__).resolve().parents[1]
    config = json.loads(args.config.read_text(encoding="utf-8"))
    validated = validate_config(config, repo_root)
    summary = {
        "model": config["model_name_or_path"],
        "train_records": len(validated["train_records"]),
        "eval_records": len(validated["eval_records"]),
        "output_dir": config["output_dir"],
        "load_in_4bit": config.get("load_in_4bit", True),
        "lora_r": config.get("lora_r", 16),
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    if args.dry_run:
        print("P5 QLoRA dry-run validation passed; no model was loaded.")
        return 0

    import torch
    from datasets import Dataset
    from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training
    from PIL import Image
    from transformers import (
        AutoProcessor,
        BitsAndBytesConfig,
        MllamaForConditionalGeneration,
        Trainer,
        TrainingArguments,
        set_seed,
    )

    set_seed(int(config.get("seed", 2026)))
    random.seed(int(config.get("seed", 2026)))
    compute_dtype = torch.bfloat16 if config.get("bf16", True) else torch.float16
    quantization = BitsAndBytesConfig(
        load_in_4bit=bool(config.get("load_in_4bit", True)),
        bnb_4bit_quant_type=config.get("bnb_4bit_quant_type", "nf4"),
        bnb_4bit_use_double_quant=bool(
            config.get("bnb_4bit_use_double_quant", True)
        ),
        bnb_4bit_compute_dtype=compute_dtype,
    )
    model = MllamaForConditionalGeneration.from_pretrained(
        config["model_name_or_path"],
        quantization_config=quantization,
        torch_dtype=compute_dtype,
        device_map="auto",
    )
    processor = AutoProcessor.from_pretrained(config["model_name_or_path"])
    model = prepare_model_for_kbit_training(
        model,
        use_gradient_checkpointing=bool(config.get("gradient_checkpointing", True)),
    )
    lora = LoraConfig(
        r=int(config.get("lora_r", 16)),
        lora_alpha=int(config.get("lora_alpha", 32)),
        lora_dropout=float(config.get("lora_dropout", 0.05)),
        target_modules=config["lora_target_modules"],
        bias="none",
        task_type="CAUSAL_LM",
    )
    model = get_peft_model(model, lora)
    if config.get("freeze_vision_encoder", True):
        for name, parameter in model.named_parameters():
            if "vision_model" in name:
                parameter.requires_grad = False
    model.config.use_cache = False

    class MultimodalCollator:
        def __call__(self, records: list[dict[str, Any]]) -> dict[str, Any]:
            texts = []
            images = []
            prompt_lengths = []
            for record in records:
                source_messages = record["messages"]
                messages = []
                for message in source_messages:
                    content = []
                    for item in message["content"]:
                        if item["type"] == "image":
                            content.append({"type": "image"})
                        else:
                            content.append({"type": "text", "text": item["text"]})
                    messages.append({"role": message["role"], "content": content})
                texts.append(
                    processor.apply_chat_template(
                        messages, tokenize=False, add_generation_prompt=False
                    )
                )
                prompt_ids = processor.tokenizer.apply_chat_template(
                    messages[:-1], tokenize=True, add_generation_prompt=True
                )
                prompt_lengths.append(len(prompt_ids))
                with Image.open(repo_root / record["image"]) as image:
                    images.append(image.convert("RGB"))
            batch = processor(
                text=texts,
                images=images,
                return_tensors="pt",
                padding=True,
                truncation=True,
                max_length=int(config.get("max_length", 4096)),
            )
            labels = batch["input_ids"].clone()
            pad_id = processor.tokenizer.pad_token_id
            if pad_id is not None:
                labels[labels == pad_id] = -100
            for row, prompt_length in enumerate(prompt_lengths):
                labels[row, : min(prompt_length, labels.shape[1])] = -100
            batch["labels"] = labels
            return batch

    train_records = validated["train_records"][:1] if args.smoke_test else validated["train_records"]
    eval_records = validated["eval_records"][:1] if args.smoke_test else validated["eval_records"]
    train_dataset = Dataset.from_list(train_records)
    eval_dataset = Dataset.from_list(eval_records)
    output_dir = repo_root / config["output_dir"]
    if args.smoke_test:
        output_dir = output_dir.parent / (output_dir.name + "_smoke")
    final_adapter = output_dir / "final_adapter"
    if args.resume and (final_adapter / "adapter_config.json").is_file():
        print(f"Final adapter already exists: {final_adapter}; nothing to resume.")
        return 0
    training_args = TrainingArguments(
        output_dir=str(output_dir),
        num_train_epochs=float(config.get("num_train_epochs", 2)),
        learning_rate=float(config.get("learning_rate", 2e-4)),
        weight_decay=float(config.get("weight_decay", 0.01)),
        warmup_ratio=float(config.get("warmup_ratio", 0.05)),
        per_device_train_batch_size=int(config.get("per_device_train_batch_size", 1)),
        per_device_eval_batch_size=int(config.get("per_device_eval_batch_size", 1)),
        gradient_accumulation_steps=int(config.get("gradient_accumulation_steps", 16)),
        gradient_checkpointing=bool(config.get("gradient_checkpointing", True)),
        bf16=bool(config.get("bf16", True)),
        logging_steps=int(config.get("logging_steps", 5)),
        eval_strategy="no" if args.smoke_test else "steps",
        eval_steps=int(config.get("eval_steps", 50)),
        save_strategy="no" if args.smoke_test else "steps",
        save_steps=int(config.get("save_steps", 50)),
        save_total_limit=int(config.get("save_total_limit", 2)),
        report_to=config.get("report_to", "none"),
        remove_unused_columns=False,
        seed=int(config.get("seed", 2026)),
        max_steps=1 if args.smoke_test else -1,
    )
    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=train_dataset,
        eval_dataset=eval_dataset,
        data_collator=MultimodalCollator(),
    )
    resume_checkpoint = None
    if args.resume:
        checkpoints = []
        for path in output_dir.glob("checkpoint-*"):
            match = re.fullmatch(r"checkpoint-(\d+)", path.name)
            if match and (path / "trainer_state.json").is_file():
                checkpoints.append((int(match.group(1)), path))
        if checkpoints:
            resume_checkpoint = str(max(checkpoints)[1])
            print(f"Resuming P5 QLoRA from {resume_checkpoint}")
        else:
            print("No complete checkpoint found; starting P5 QLoRA from step 0.")
    trainer.train(resume_from_checkpoint=resume_checkpoint)
    if args.smoke_test:
        peak_gib = torch.cuda.max_memory_allocated() / 1024**3
        print(f"P5 QLoRA smoke test passed; peak allocated GPU memory: {peak_gib:.2f} GiB")
        return 0
    trainer.save_model(str(final_adapter))
    processor.save_pretrained(str(final_adapter))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
