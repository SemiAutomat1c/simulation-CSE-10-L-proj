import threading
import unittest

from app.cache import LRUCache


class LRUCacheTests(unittest.TestCase):
    def test_evicts_oldest(self) -> None:
        c = LRUCache(maxsize=2)
        c.set("a", 1)
        c.set("b", 2)
        c.set("c", 3)
        self.assertIsNone(c.get("a"))
        self.assertEqual(c.get("b"), 2)
        self.assertEqual(c.get("c"), 3)
        self.assertEqual(c.misses, 1)
        self.assertEqual(c.hits, 2)

    def test_get_refreshes_recency(self) -> None:
        c = LRUCache(maxsize=2)
        c.set("a", 1)
        c.set("b", 2)
        c.get("a")
        c.set("c", 3)
        self.assertEqual(c.get("a"), 1)
        self.assertIsNone(c.get("b"))

    def test_concurrent_get_set_does_not_raise(self) -> None:
        """Smoke test that locked get/set survive concurrent access."""
        c = LRUCache(maxsize=32)
        errors: list[BaseException] = []

        def writer(start: int) -> None:
            try:
                for i in range(start, start + 40):
                    c.set(i % 20, i)
                    c.get(i % 20)
            except BaseException as exc:  # pragma: no cover - failure path
                errors.append(exc)

        threads = [threading.Thread(target=writer, args=(n * 40,)) for n in range(4)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        self.assertEqual(errors, [])
        self.assertGreater(c.hits + c.misses, 0)
