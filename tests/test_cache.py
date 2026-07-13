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
