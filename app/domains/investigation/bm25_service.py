"""
Production BM25 Probabilistic Ranking Engine for Forensic Evidence Discovery.
"""

import math
import re
import time
from typing import Any, Dict, List, Set

STOP_WORDS: Set[str] = {
    "a",
    "an",
    "the",
    "and",
    "or",
    "in",
    "on",
    "at",
    "to",
    "for",
    "of",
    "with",
    "by",
    "from",
    "as",
    "is",
    "was",
    "are",
    "were",
    "been",
    "be",
    "have",
    "has",
    "had",
    "that",
    "this",
    "these",
    "those",
    "it",
    "its",
    "they",
    "their",
}

TOKEN_PATTERN = re.compile(r"[a-z0-9_#-]{2,}")


class BM25SearchService:
    def __init__(self, k1: float = 1.25, b: float = 0.75):
        self.k1 = k1
        self.b = b
        self.documents: List[Dict[str, Any]] = []
        self.doc_lengths: List[int] = []
        self.avgdl: float = 0.0
        self.corpus_size: int = 0
        self.inverted_index: Dict[str, Dict[int, int]] = {}
        self.doc_term_frequencies: List[Dict[str, int]] = []

    def set_parameters(self, k1: float, b: float) -> None:
        self.k1 = max(0.1, float(k1))
        self.b = max(0.01, min(1.0, float(b)))

    @staticmethod
    def tokenize(text: str) -> List[str]:
        if not text:
            return []
        tokens = TOKEN_PATTERN.findall(text.lower())
        return [t for t in tokens if t not in STOP_WORDS]

    def index_corpus(self, docs: List[Dict[str, Any]]) -> None:
        self.documents = docs
        self.corpus_size = len(docs)
        self.doc_lengths = []
        self.inverted_index = {}
        self.doc_term_frequencies = []

        total_length = 0

        for idx, doc in enumerate(docs):
            full_text = f"{doc.get('title', '')} {doc.get('content', '')} {doc.get('category', '')}"
            tokens = self.tokenize(full_text)
            doc_len = len(tokens)
            self.doc_lengths.append(doc_len)
            total_length += doc_len

            tf_map: Dict[str, int] = {}
            for token in tokens:
                tf_map[token] = tf_map.get(token, 0) + 1
            self.doc_term_frequencies.append(tf_map)

            for term, count in tf_map.items():
                if term not in self.inverted_index:
                    self.inverted_index[term] = {}
                self.inverted_index[term][idx] = count

        self.avgdl = total_length / self.corpus_size if self.corpus_size > 0 else 0.0

    def compute_idf(self, term: str) -> float:
        postings = self.inverted_index.get(term, {})
        n_q = len(postings)
        numerator = self.corpus_size - n_q + 0.5
        denominator = n_q + 0.5
        return math.log((numerator / denominator) + 1.0)

    def search(self, query: str, top_k: int = 20) -> Dict[str, Any]:
        start_time = time.perf_counter()
        query_terms = self.tokenize(query)

        if not query_terms or self.corpus_size == 0:
            return {
                "results": [],
                "query_terms": query_terms,
                "latency_ms": round((time.perf_counter() - start_time) * 1000, 3),
                "total_indexed": self.corpus_size,
            }

        scores: Dict[int, float] = {}
        score_breakdowns: Dict[int, List[Dict[str, Any]]] = {}

        for term in query_terms:
            idf = self.compute_idf(term)
            postings = self.inverted_index.get(term, {})

            for doc_idx, tf in postings.items():
                doc_len = self.doc_lengths[doc_idx]
                len_norm = 1.0 - self.b + self.b * (doc_len / (self.avgdl or 1.0))
                term_score = idf * ((tf * (self.k1 + 1.0)) / (tf + self.k1 * len_norm))

                scores[doc_idx] = scores.get(doc_idx, 0.0) + term_score

                if doc_idx not in score_breakdowns:
                    score_breakdowns[doc_idx] = []
                score_breakdowns[doc_idx].append(
                    {
                        "term": term,
                        "tf": tf,
                        "idf": round(idf, 3),
                        "term_score": round(term_score, 3),
                    }
                )

        # Rank by score descending
        ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)[:top_k]

        results = []
        for doc_idx, score in ranked:
            doc = self.documents[doc_idx]
            results.append(
                {
                    "document": doc,
                    "score": round(score, 3),
                    "confidence_pct": min(
                        100, round((score / (len(query_terms) * 4.0)) * 100)
                    ),
                    "breakdown": score_breakdowns.get(doc_idx, []),
                }
            )

        return {
            "results": results,
            "query_terms": query_terms,
            "latency_ms": round((time.perf_counter() - start_time) * 1000, 3),
            "total_indexed": self.corpus_size,
            "avgdl": round(self.avgdl, 1),
        }
