"""JSON 文件存储"""
import json
from pathlib import Path
from typing import Any

from money_get.config import TRADES_FILE


def load_json(path: Path) -> list:
    """加载 JSON 文件"""
    if not path.exists():
        return []
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json(path: Path, data: list) -> None:
    """保存 JSON 文件"""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def append_json(path: Path, item: dict) -> None:
    """追加 JSON 记录"""
    data = load_json(path)
    data.append(item)
    save_json(path, data)
