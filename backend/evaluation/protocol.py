import json
from pathlib import Path
from typing import Any


def load_config(path: Path) -> dict[str, Any]:
    with Path(path).open(encoding="utf-8") as handle:
        config = json.load(handle)
    validate_seed_separation(config)
    return config


def split_seeds(config: dict[str, Any], split: str) -> set[int]:
    value = config["splits"][split]
    if split == "train":
        return set(value["normal_seeds"])
    return {int(run["seed"]) for run in value["runs"]}


def validate_seed_separation(config: dict[str, Any]) -> None:
    train = split_seeds(config, "train")
    validation = split_seeds(config, "validation")
    test = split_seeds(config, "test")
    if train & validation or train & test or validation & test:
        raise ValueError("Train, validation, and test seeds must not overlap")
    if len(train) < 2:
        raise ValueError("Evaluation requires multiple independent normal training runs")
