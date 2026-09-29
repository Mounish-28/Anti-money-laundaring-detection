"""
Robin Hood Hash Table with Open Addressing and Probe Sequence Length (PSL) Optimization.
Provides constant-time O(1) account verification and sanctions list matching.
"""

import time
from typing import Any, Dict, List, Optional


def fast_hash64(key: str, seed: int = 0x517CC1B7) -> int:
    h1 = seed ^ len(key)
    h2 = seed

    for ch in key:
        c = ord(ch)
        h1 = (h1 ^ c) * 0x5F356495 & 0xFFFFFFFF
        h2 = (h2 ^ (c << 5)) * 0x85EBCA6B & 0xFFFFFFFF
        h1 = ((h1 << 13) | (h1 >> 19)) & 0xFFFFFFFF
        h2 = ((h2 << 17) | (h2 >> 15)) & 0xFFFFFFFF

    h1 = (h1 ^ (h1 >> 16)) * 0x85EBCA6B & 0xFFFFFFFF
    h1 ^= h1 >> 13
    h2 = (h2 ^ (h2 >> 16)) * 0xC2B2AE35 & 0xFFFFFFFF
    h2 ^= h2 >> 16

    return (h1 ^ h2) & 0xFFFFFFFF


class RobinHoodHashTable:
    def __init__(self, initial_capacity: int = 64, max_load_factor: float = 0.85):
        self.capacity = self._next_power_of_two(initial_capacity)
        self.max_load_factor = max_load_factor
        self.size = 0
        self.buckets: List[Optional[Dict[str, Any]]] = [None] * self.capacity
        self.max_psl = 0
        self.total_collisions = 0

    @staticmethod
    def _next_power_of_two(n: int) -> int:
        p = 1
        while p < n:
            p <<= 1
        return max(16, p)

    def insert(self, key: str, value: Any) -> bool:
        if (self.size + 1) / self.capacity > self.max_load_factor:
            self._resize(self.capacity * 2)

        hash_val = fast_hash64(key)
        entry = {
            "key": str(key),
            "value": value,
            "hash": hash_val,
            "psl": 0,
        }

        index = hash_val & (self.capacity - 1)

        while True:
            current = self.buckets[index]

            if current is None:
                self.buckets[index] = entry
                self.size += 1
                if entry["psl"] > self.max_psl:
                    self.max_psl = entry["psl"]
                return True

            if current["key"] == entry["key"]:
                current["value"] = value
                return False

            self.total_collisions += 1

            # Robin Hood condition: swap if incoming has longer probe distance
            if entry["psl"] > current["psl"]:
                self.buckets[index] = entry
                entry = current
                if entry["psl"] > self.max_psl:
                    self.max_psl = entry["psl"]

            entry["psl"] += 1
            index = (index + 1) & (self.capacity - 1)

    def lookup(self, key: str) -> Dict[str, Any]:
        start = time.perf_counter()
        hash_val = fast_hash64(key)
        index = hash_val & (self.capacity - 1)
        probe = 0

        while probe <= self.max_psl:
            current = self.buckets[index]

            # Early termination when bucket PSL < current probe
            if current is None or current["psl"] < probe:
                latency_micros = round((time.perf_counter() - start) * 1_000_000, 2)
                return {
                    "found": False,
                    "probes": probe + 1,
                    "bucket_index": index,
                    "latency_micros": latency_micros,
                }

            if current["key"] == str(key):
                latency_micros = round((time.perf_counter() - start) * 1_000_000, 2)
                return {
                    "found": True,
                    "value": current["value"],
                    "psl": current["psl"],
                    "probes": probe + 1,
                    "bucket_index": index,
                    "hash": current["hash"],
                    "latency_micros": latency_micros,
                }

            probe += 1
            index = (index + 1) & (self.capacity - 1)

        latency_micros = round((time.perf_counter() - start) * 1_000_000, 2)
        return {
            "found": False,
            "probes": probe,
            "bucket_index": index,
            "latency_micros": latency_micros,
        }

    def _resize(self, new_capacity: int) -> None:
        old_buckets = self.buckets
        self.capacity = new_capacity
        self.buckets = [None] * self.capacity
        self.size = 0
        self.max_psl = 0

        for entry in old_buckets:
            if entry is not None:
                self.insert(entry["key"], entry["value"])
