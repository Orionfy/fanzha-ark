import json
import os
from datetime import datetime
from typing import List, Dict, Any

DATA_FILE = os.path.join(os.path.dirname(__file__), "messages.json")

def _load() -> List[Dict[str, Any]]:
    if not os.path.exists(DATA_FILE):
        return []
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def _save(data: List[Dict[str, Any]]):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def get_all() -> List[Dict[str, Any]]:
    return _load()

def get_by_id(msg_id: int) -> Dict[str, Any] | None:
    for msg in _load():
        if msg["id"] == msg_id:
            return msg
    return None

def create(content: str, mood: str = "未知") -> Dict[str, Any]:
    data = _load()
    new_id = max([m["id"] for m in data], default=0) + 1
    new_msg = {
        "id": new_id,
        "content": content,
        "mood": mood,
        "created_at": datetime.now().isoformat()
    }
    data.append(new_msg)
    _save(data)
    return new_msg