"""
In-Memory 3-Way Partitioning QuickSort (Dutch National Flag) Service.
Handles identical structuring values in O(n) linear time with multi-attribute comparators.
"""

import time
from typing import Any, Callable, Dict, List


class QuickSortLedgerService:
    @staticmethod
    def _create_comparator(
        sort_criteria: List[Dict[str, str]],
    ) -> Callable[[Dict, Dict], int]:
        def comparator(a: Dict[str, Any], b: Dict[str, Any]) -> int:
            for rule in sort_criteria:
                key = rule["key"]
                direction = rule.get("direction", "asc").lower()

                val_a = a.get(key, 0)
                val_b = b.get(key, 0)

                if val_a is None:
                    val_a = 0
                if val_b is None:
                    val_b = 0

                if val_a < val_b:
                    return -1 if direction == "asc" else 1
                elif val_a > val_b:
                    return 1 if direction == "asc" else -1
            return 0

        return comparator

    @classmethod
    def _quicksort_3way(
        cls, arr: List[Dict], low: int, high: int, cmp: Callable, stats: Dict[str, int]
    ) -> None:
        while low < high:
            # Fallback to insertion sort for small partitions
            if high - low <= 16:
                for i in range(low + 1, high + 1):
                    key_item = arr[i]
                    j = i - 1
                    while j >= low:
                        stats["comparisons"] += 1
                        if cmp(arr[j], key_item) > 0:
                            arr[j + 1] = arr[j]
                            stats["swaps"] += 1
                            j -= 1
                        else:
                            break
                    arr[j + 1] = key_item
                break

            # Median-of-three pivot selection
            mid = low + (high - low) // 2
            if cmp(arr[low], arr[mid]) > 0:
                arr[low], arr[mid] = arr[mid], arr[low]
            if cmp(arr[low], arr[high]) > 0:
                arr[low], arr[high] = arr[high], arr[low]
            if cmp(arr[mid], arr[high]) > 0:
                arr[mid], arr[high] = arr[high], arr[mid]
            arr[low], arr[mid] = arr[mid], arr[low]
            pivot = arr[low]

            lt = low
            gt = high
            i = low + 1

            while i <= gt:
                stats["comparisons"] += 1
                c = cmp(arr[i], pivot)
                if c < 0:
                    arr[lt], arr[i] = arr[i], arr[lt]
                    stats["swaps"] += 1
                    lt += 1
                    i += 1
                elif c > 0:
                    arr[i], arr[gt] = arr[gt], arr[i]
                    stats["swaps"] += 1
                    gt -= 1
                else:
                    stats["duplicate_pivots"] += 1
                    i += 1

            # Tail call optimization: recurse on smaller partition
            if (lt - 1 - low) < (high - (gt + 1)):
                cls._quicksort_3way(arr, low, lt - 1, cmp, stats)
                low = gt + 1
            else:
                cls._quicksort_3way(arr, gt + 1, high, cmp, stats)
                high = lt - 1

    @classmethod
    def sort(
        cls, records: List[Dict[str, Any]], criteria: List[Dict[str, str]]
    ) -> Dict[str, Any]:
        data = list(records)
        stats = {"comparisons": 0, "swaps": 0, "duplicate_pivots": 0}
        cmp = cls._create_comparator(criteria)

        start = time.perf_counter()
        if len(data) > 1:
            cls._quicksort_3way(data, 0, len(data) - 1, cmp, stats)
        duration_ms = round((time.perf_counter() - start) * 1000, 3)

        return {
            "sorted_records": data,
            "duration_ms": duration_ms,
            "element_count": len(data),
            "comparisons": stats["comparisons"],
            "swaps": stats["swaps"],
            "duplicate_pivots": stats["duplicate_pivots"],
        }
