from __future__ import annotations

import hashlib
import json
import os
import time
import threading
from pathlib import Path
from typing import Any, Callable, Optional

from config.logger import get_logger

logger = get_logger("ResponseCache")

class ResponseCache:
    """
    Expanded file-based response cache + In-memory request coalescing (debouncing).
    Prevents duplicate LLM calls for identical concurrent or recent requests.
    Supports namespacing for Planners, Routers, etc.
    """
    _instance = None
    _lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(ResponseCache, cls).__new__(cls)
                cls._instance._initialized = False
            return cls._instance

    def __init__(self, cache_dir: str | Path = ".cache/responses", ttl_seconds: int = 3600):
        if not self._initialized:
            self.cache_dir = Path(cache_dir)
            self.ttl_seconds = ttl_seconds
            self.cache_dir.mkdir(parents=True, exist_ok=True)
            self._in_flight: dict[str, dict[str, Any]] = {}
            self._in_flight_lock = threading.Lock()
            self._initialized = True

    def _hash_key(self, namespace: str, payload: dict[str, Any]) -> str:
        serialized = json.dumps(
            {"namespace": namespace, "payload": payload},
            sort_keys=True,
            ensure_ascii=False,
        )
        return hashlib.sha256(serialized.encode("utf-8")).hexdigest()

    def _path_for_key(self, cache_key: str) -> Path:
        return self.cache_dir / f"{cache_key}.json"

    def get_or_compute(self, namespace: str, payload: dict[str, Any], compute_fn: Callable[[], Any]) -> Any:
        cache_key = self._hash_key(namespace, payload)
        path = self._path_for_key(cache_key)

        # 1. Check file cache
        cached_result = self._get_from_disk(path)
        if cached_result is not None:
            logger.debug(f"[{namespace}] Cache HIT")
            return cached_result

        # 2. Check in-flight (Debounce/Coalesce)
        event = None
        is_leader = False
        
        with self._in_flight_lock:
            if cache_key in self._in_flight:
                logger.debug(f"[{namespace}] Coalescing request - waiting for in-flight execution...")
                in_flight_data = self._in_flight[cache_key]
                if 'result' in in_flight_data:
                    return in_flight_data['result']
                event = in_flight_data['event']
            else:
                event = threading.Event()
                self._in_flight[cache_key] = {'event': event}
                is_leader = True

        if not is_leader and event is not None:
            # We are waiting for another thread
            event.wait()
            with self._in_flight_lock:
                 if cache_key in self._in_flight and 'result' in self._in_flight[cache_key]:
                      return self._in_flight[cache_key]['result']
            # If we woke up but there's no result, computation failed. Fall through to compute anyway.

        # We are the leader thread (or fallback), compute
        try:
            logger.debug(f"[{namespace}] Cache MISS - Computing...")
            result = compute_fn()
            
            # Save and unblock
            self._save_to_disk(path, namespace, payload, result)
            with self._in_flight_lock:
                if cache_key in self._in_flight:
                    self._in_flight[cache_key]['result'] = result
                    self._in_flight[cache_key]['event'].set()
                    
            return result
            
        except Exception as e:
            with self._in_flight_lock:
                if cache_key in self._in_flight:
                    self._in_flight[cache_key]['event'].set() # Unblock waiters, they will retry or fail
                    del self._in_flight[cache_key]
            raise

    def _get_from_disk(self, path: Path) -> Optional[Any]:
        if not path.exists():
            return None
        try:
            with path.open("r", encoding="utf-8") as f:
                data = json.load(f)
            created_at = data.get("created_at", 0)
            if time.time() - created_at > self.ttl_seconds:
                try: path.unlink(missing_ok=True)
                except OSError: pass
                return None
            return data.get("value")
        except (json.JSONDecodeError, OSError):
            return None

    def _save_to_disk(self, path: Path, namespace: str, payload: dict[str, Any], value: Any) -> None:
        data = {
            "created_at": time.time(),
            "namespace": namespace,
            "payload": payload,
            "value": value,
        }
        try:
            with path.open("w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except OSError:
            pass

    def delete(self, namespace: str, payload: dict[str, Any]) -> None:
        cache_key = self._hash_key(namespace, payload)
        path = self._path_for_key(cache_key)
        try: path.unlink(missing_ok=True)
        except OSError: pass

    def clear(self) -> None:
        for p in self.cache_dir.glob("*.json"):
            try: p.unlink()
            except OSError: pass

response_cache = ResponseCache()
