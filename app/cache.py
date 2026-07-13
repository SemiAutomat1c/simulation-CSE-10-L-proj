"""In-memory LRU cache helper."""

from __future__ import annotations

import threading
from collections import OrderedDict
from typing import Any


class LRUCache:
    """Thread-safe LRU cache backed by OrderedDict.

    - ``get`` moves the key to the most-recent end and tracks hits/misses.
    - ``set`` inserts or updates a key; when over capacity, the least-recent
      key is evicted via ``popitem(last=False)``.
    """

    def __init__(self, maxsize: int = 128) -> None:
        if maxsize < 1:
            raise ValueError("maxsize must be >= 1")
        self.maxsize = maxsize
        self.hits = 0
        self.misses = 0
        self._data: OrderedDict[Any, Any] = OrderedDict()
        self._lock = threading.RLock()

    def get(self, key: Any) -> Any | None:
        with self._lock:
            if key not in self._data:
                self.misses += 1
                return None
            self._data.move_to_end(key)
            self.hits += 1
            return self._data[key]

    def set(self, key: Any, value: Any) -> None:
        with self._lock:
            if key in self._data:
                self._data.move_to_end(key)
                self._data[key] = value
            else:
                self._data[key] = value
                if len(self._data) > self.maxsize:
                    self._data.popitem(last=False)

    def clear(self) -> None:
        with self._lock:
            self._data.clear()
            self.hits = 0
            self.misses = 0

    def __len__(self) -> int:
        with self._lock:
            return len(self._data)
