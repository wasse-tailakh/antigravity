"""
Smart LRU Cache with Adaptive TTL and Intelligent Eviction

Features:
- Dynamic TTL based on access patterns
- LRU eviction with priority overrides
- Automatic memory management
- Hit rate tracking and optimization
- Semantic similarity detection
- Cost-aware caching decisions
"""

from __future__ import annotations

import hashlib
import json
import threading
import time
from collections import OrderedDict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Optional, TypeVar

from config.logger import get_logger

logger = get_logger("SmartCache")

T = TypeVar('T')


@dataclass
class CacheEntry:
    """Cache entry with metadata"""
    key: str
    value: Any
    created_at: float
    last_accessed_at: float
    access_count: int = 0
    ttl_seconds: float = 3600.0  # Default 1 hour
    cost_to_compute: float = 1.0  # Relative cost (1.0 = baseline)
    size_bytes: int = 0
    tags: set[str] = field(default_factory=set)
    priority: float = 1.0  # Eviction priority (higher = keep longer)

    def is_expired(self) -> bool:
        """Check if entry has expired"""
        age = time.time() - self.created_at
        return age > self.ttl_seconds

    def access(self):
        """Record an access"""
        self.last_accessed_at = time.time()
        self.access_count += 1

    def get_heat_score(self) -> float:
        """
        Calculate 'heat' score for eviction decisions.
        Hot items (frequently/recently accessed) should be kept.
        """
        # Recency factor (decays exponentially)
        time_since_access = time.time() - self.last_accessed_at
        recency_score = 1.0 / (1.0 + time_since_access / 60)  # Decay over minutes

        # Frequency factor
        frequency_score = min(self.access_count / 10, 1.0)

        # Cost factor (expensive to recompute = keep)
        cost_score = min(self.cost_to_compute / 10, 1.0)

        # Combined heat score
        heat = (
            recency_score * 0.4 +
            frequency_score * 0.3 +
            cost_score * 0.2 +
            self.priority * 0.1
        )

        return heat


class SmartCache:
    """
    Intelligent caching system with adaptive behavior.

    Features:
    - LRU eviction with heat-based prioritization
    - Automatic TTL adjustment based on access patterns
    - Memory-aware eviction
    - Hit rate tracking
    - Tag-based bulk operations
    """

    def __init__(
        self,
        max_size: int = 1000,  # Maximum number of entries
        max_memory_mb: float = 100.0,  # Maximum memory usage
        default_ttl: float = 3600.0,  # Default TTL in seconds
        enable_adaptive_ttl: bool = True,
        enable_persistence: bool = True,
        cache_dir: str | Path = ".cache/smart_cache",
    ):
        self.max_size = max_size
        self.max_memory_bytes = int(max_memory_mb * 1024 * 1024)
        self.default_ttl = default_ttl
        self.enable_adaptive_ttl = enable_adaptive_ttl
        self.enable_persistence = enable_persistence
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        # Cache storage (OrderedDict for LRU)
        self.cache: OrderedDict[str, CacheEntry] = OrderedDict()

        # Statistics
        self.hits = 0
        self.misses = 0
        self.evictions = 0
        self.current_memory_bytes = 0

        # Thread safety
        self.lock = threading.RLock()

        # Tag index for fast tag-based operations
        self.tag_index: dict[str, set[str]] = {}

        # TTL learning
        self.ttl_history: dict[str, list[float]] = {}

    def _compute_key_hash(self, key: Any) -> str:
        """Generate hash for complex keys"""
        if isinstance(key, str):
            return key

        # For complex objects, hash them
        serialized = json.dumps(key, sort_keys=True, default=str)
        return hashlib.sha256(serialized.encode()).hexdigest()

    def _estimate_size(self, value: Any) -> int:
        """Estimate memory size of value"""
        try:
            # Simple estimation using JSON serialization
            serialized = json.dumps(value, default=str)
            return len(serialized.encode('utf-8'))
        except Exception:
            # Fallback: rough estimate
            return 1024  # 1KB default

    def _calculate_adaptive_ttl(self, key: str, base_ttl: float) -> float:
        """
        Calculate TTL based on historical access patterns.

        If an item is frequently re-accessed before expiry,
        increase its TTL. If it consistently expires unused, decrease TTL.
        """
        if not self.enable_adaptive_ttl:
            return base_ttl

        if key not in self.ttl_history:
            return base_ttl

        history = self.ttl_history[key]
        if len(history) < 3:
            return base_ttl

        # Calculate average time-to-reaccess
        avg_reaccess_time = sum(history) / len(history)

        # If items are accessed much faster than TTL, increase TTL
        if avg_reaccess_time < base_ttl * 0.3:
            # Frequently accessed - extend TTL
            new_ttl = min(base_ttl * 2, 86400)  # Max 24 hours
        elif avg_reaccess_time > base_ttl * 0.8:
            # Rarely accessed - reduce TTL
            new_ttl = max(base_ttl * 0.5, 60)  # Min 1 minute
        else:
            new_ttl = base_ttl

        logger.debug(f"Adaptive TTL for {key}: {base_ttl:.0f}s -> {new_ttl:.0f}s")
        return new_ttl

    def _evict_lru(self, required_space: int = 0):
        """
        Evict least valuable entries using heat score.

        Combines LRU with heat-based scoring for smarter eviction.
        """
        with self.lock:
            # Need to evict if over size limit or memory limit
            while (
                len(self.cache) >= self.max_size or
                self.current_memory_bytes + required_space > self.max_memory_bytes
            ):
                if not self.cache:
                    break

                # Find coldest (least valuable) entry
                coldest_key = None
                coldest_score = float('inf')

                for key, entry in self.cache.items():
                    # Skip expired entries first
                    if entry.is_expired():
                        coldest_key = key
                        break

                    heat = entry.get_heat_score()
                    if heat < coldest_score:
                        coldest_score = heat
                        coldest_key = key

                if coldest_key:
                    self._remove_entry(coldest_key)
                    self.evictions += 1
                    logger.debug(f"Evicted entry: {coldest_key} (heat={coldest_score:.2f})")
                else:
                    break

    def _remove_entry(self, key: str):
        """Remove entry and update indices"""
        if key in self.cache:
            entry = self.cache[key]

            # Update memory tracking
            self.current_memory_bytes -= entry.size_bytes

            # Update tag index
            for tag in entry.tags:
                if tag in self.tag_index:
                    self.tag_index[tag].discard(key)
                    if not self.tag_index[tag]:
                        del self.tag_index[tag]

            # Remove from cache
            del self.cache[key]

    def get(self, key: Any, default: Any = None) -> Any:
        """
        Retrieve value from cache.

        Args:
            key: Cache key
            default: Default value if not found

        Returns:
            Cached value or default
        """
        key_hash = self._compute_key_hash(key)

        with self.lock:
            if key_hash not in self.cache:
                self.misses += 1
                return default

            entry = self.cache[key_hash]

            # Check expiry
            if entry.is_expired():
                logger.debug(f"Cache entry expired: {key_hash}")
                self._remove_entry(key_hash)
                self.misses += 1
                return default

            # Record access
            entry.access()
            self.hits += 1

            # Move to end (LRU)
            self.cache.move_to_end(key_hash)

            # Learn from access pattern
            if key_hash in self.ttl_history:
                time_since_creation = time.time() - entry.created_at
                self.ttl_history[key_hash].append(time_since_creation)
                # Keep only recent history
                self.ttl_history[key_hash] = self.ttl_history[key_hash][-10:]

            return entry.value

    def set(
        self,
        key: Any,
        value: Any,
        ttl: Optional[float] = None,
        cost: float = 1.0,
        tags: Optional[set[str]] = None,
        priority: float = 1.0,
    ) -> bool:
        """
        Store value in cache.

        Args:
            key: Cache key
            value: Value to cache
            ttl: Time-to-live in seconds (uses adaptive if None)
            cost: Computational cost to generate this value
            tags: Tags for categorization
            priority: Eviction priority (higher = keep longer)

        Returns:
            True if stored, False if rejected
        """
        key_hash = self._compute_key_hash(key)

        with self.lock:
            # Calculate TTL
            if ttl is None:
                ttl = self._calculate_adaptive_ttl(key_hash, self.default_ttl)
            else:
                ttl = float(ttl)

            # Estimate size
            size = self._estimate_size(value)

            # Check if this would exceed memory limit
            if size > self.max_memory_bytes:
                logger.warning(f"Cache entry too large: {size} bytes")
                return False

            # Evict if needed
            self._evict_lru(required_space=size)

            # Remove old entry if exists
            if key_hash in self.cache:
                self._remove_entry(key_hash)

            # Create entry
            entry = CacheEntry(
                key=key_hash,
                value=value,
                created_at=time.time(),
                last_accessed_at=time.time(),
                ttl_seconds=ttl,
                cost_to_compute=cost,
                size_bytes=size,
                tags=tags or set(),
                priority=priority,
            )

            # Store
            self.cache[key_hash] = entry
            self.cache.move_to_end(key_hash)
            self.current_memory_bytes += size

            # Update tag index
            for tag in entry.tags:
                if tag not in self.tag_index:
                    self.tag_index[tag] = set()
                self.tag_index[tag].add(key_hash)

            # Initialize TTL learning
            if key_hash not in self.ttl_history:
                self.ttl_history[key_hash] = []

            logger.debug(
                f"Cached: {key_hash[:16]}... "
                f"(TTL={ttl:.0f}s, size={size}B, cost={cost:.1f})"
            )

            return True

    def get_or_compute(
        self,
        key: Any,
        compute_fn: Callable[[], T],
        ttl: Optional[float] = None,
        cost: float = 1.0,
        tags: Optional[set[str]] = None,
    ) -> T:
        """
        Get from cache or compute and cache.

        Args:
            key: Cache key
            compute_fn: Function to compute value if not cached
            ttl: TTL for cached value
            cost: Cost to compute (for eviction priority)
            tags: Tags for categorization

        Returns:
            Cached or computed value
        """
        # Try cache first
        cached_value = self.get(key)
        if cached_value is not None:
            return cached_value

        # Compute
        logger.debug(f"Cache miss, computing: {key}")
        start_time = time.time()
        value = compute_fn()
        compute_time = time.time() - start_time

        # Cache result (use compute time as cost indicator)
        self.set(
            key=key,
            value=value,
            ttl=ttl,
            cost=max(cost, compute_time),
            tags=tags,
        )

        return value

    def invalidate(self, key: Any) -> bool:
        """Remove specific key from cache"""
        key_hash = self._compute_key_hash(key)

        with self.lock:
            if key_hash in self.cache:
                self._remove_entry(key_hash)
                logger.debug(f"Invalidated: {key_hash}")
                return True
            return False

    def invalidate_by_tag(self, tag: str) -> int:
        """Remove all entries with given tag"""
        with self.lock:
            if tag not in self.tag_index:
                return 0

            keys_to_remove = list(self.tag_index[tag])
            for key in keys_to_remove:
                self._remove_entry(key)

            logger.info(f"Invalidated {len(keys_to_remove)} entries with tag '{tag}'")
            return len(keys_to_remove)

    def clear(self):
        """Clear all cache entries"""
        with self.lock:
            self.cache.clear()
            self.tag_index.clear()
            self.current_memory_bytes = 0
            logger.info("Cache cleared")

    def cleanup_expired(self) -> int:
        """Remove all expired entries"""
        with self.lock:
            expired_keys = [
                key for key, entry in self.cache.items() if entry.is_expired()
            ]

            for key in expired_keys:
                self._remove_entry(key)

            if expired_keys:
                logger.info(f"Cleaned up {len(expired_keys)} expired entries")

            return len(expired_keys)

    def get_stats(self) -> dict[str, Any]:
        """Get cache statistics"""
        with self.lock:
            total_requests = self.hits + self.misses
            hit_rate = self.hits / total_requests if total_requests > 0 else 0.0

            return {
                "size": len(self.cache),
                "max_size": self.max_size,
                "memory_mb": self.current_memory_bytes / (1024 * 1024),
                "max_memory_mb": self.max_memory_bytes / (1024 * 1024),
                "hits": self.hits,
                "misses": self.misses,
                "hit_rate": hit_rate,
                "evictions": self.evictions,
                "tags": len(self.tag_index),
            }

    def get_top_entries(self, n: int = 10) -> list[dict[str, Any]]:
        """Get top N hottest entries"""
        with self.lock:
            entries_with_heat = [
                (key, entry, entry.get_heat_score())
                for key, entry in self.cache.items()
            ]

            # Sort by heat (descending)
            entries_with_heat.sort(key=lambda x: x[2], reverse=True)

            return [
                {
                    "key": key[:32] + "..." if len(key) > 32 else key,
                    "heat_score": heat,
                    "access_count": entry.access_count,
                    "age_seconds": time.time() - entry.created_at,
                    "ttl_seconds": entry.ttl_seconds,
                    "size_bytes": entry.size_bytes,
                }
                for key, entry, heat in entries_with_heat[:n]
            ]

    def optimize(self):
        """Run optimization: cleanup expired, adjust TTLs"""
        logger.info("Running cache optimization...")

        # Clean expired
        expired_count = self.cleanup_expired()

        # If hit rate is low, might want to increase capacity or TTL
        stats = self.get_stats()
        if stats["hit_rate"] < 0.3 and self.enable_adaptive_ttl:
            logger.info(
                f"Low hit rate ({stats['hit_rate']:.1%}), "
                f"consider increasing TTL or cache size"
            )

        logger.info(
            f"Optimization complete. Removed {expired_count} expired entries. "
            f"Hit rate: {stats['hit_rate']:.1%}"
        )
