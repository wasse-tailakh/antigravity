from __future__ import annotations

import hashlib
import json
import os
import time
from pathlib import Path
from typing import Any


class TaskCache:
    """
    Tiny file-based cache.
    Good enough for MVP and much cheaper than repeated LLM planning.
    """

    def __init__(self, cache_dir: str | Path = ".cache/tasks", ttl_seconds: int = 3600) -> None:
        self.cache_dir = Path(cache_dir)
        self.ttl_seconds = ttl_seconds
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _hash_key(self, namespace: str, payload: dict[str, Any]) -> str:
        serialized = json.dumps(
            {"namespace": namespace, "payload": payload},
            sort_keys=True,
            ensure_ascii=False,
        )
        return hashlib.sha256(serialized.encode("utf-8")).hexdigest()

    def _path_for_key(self, cache_key: str) -> Path:
        return self.cache_dir / f"{cache_key}.json"

    def get(self, namespace: str, payload: dict[str, Any]) -> Any | None:
        cache_key = self._hash_key(namespace, payload)
        path = self._path_for_key(cache_key)

        if not path.exists():
            return None

        try:
            with path.open("r", encoding="utf-8") as f:
                data = json.load(f)

            created_at = data.get("created_at", 0)
            if time.time() - created_at > self.ttl_seconds:
                try:
                    path.unlink(missing_ok=True)
                except OSError:
                    pass
                return None

            return data.get("value")
        except (json.JSONDecodeError, OSError):
            return None

    def set(self, namespace: str, payload: dict[str, Any], value: Any) -> None:
        cache_key = self._hash_key(namespace, payload)
        path = self._path_for_key(cache_key)

        data = {
            "created_at": time.time(),
            "namespace": namespace,
            "payload": payload,
            "value": value,
        }

        with path.open("w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def delete(self, namespace: str, payload: dict[str, Any]) -> None:
        cache_key = self._hash_key(namespace, payload)
        path = self._path_for_key(cache_key)
        try:
            path.unlink(missing_ok=True)
        except OSError:
            pass

    def clear(self) -> None:
        for p in self.cache_dir.glob("*.json"):
            try:
                p.unlink()
            except OSError:
                pass
