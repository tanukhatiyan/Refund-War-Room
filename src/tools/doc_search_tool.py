"""
Refund War Room - Document Search Tool.
Performs deterministic keyword and relevance search over policy and ticket documents.
All retrieved documents are tagged as untrusted/tainted.
"""
import json
import math
import re
from pathlib import Path
from typing import List, Dict, Any, Optional

from src.config import DOCS_PATH


def _tokenize(text: str) -> List[str]:
    return [w.lower() for w in re.findall(r"\b\w{2,}\b", text)]


class DocumentSearchEngine:
    def __init__(self, docs_path: Path = DOCS_PATH):
        self.docs_path = docs_path
        self.docs: List[Dict[str, Any]] = []
        self._load_docs()

    def _load_docs(self):
        if Path(self.docs_path).exists():
            with open(self.docs_path, "r", encoding="utf-8") as f:
                self.docs = json.load(f)
        else:
            from src.data.documents import DOCUMENTS
            self.docs = DOCUMENTS

    def search(self, query: str, top_k: int = 3, category: Optional[str] = None) -> List[Dict[str, Any]]:
        query_tokens = _tokenize(query)
        if not query_tokens:
            return []

        scores: List[tuple[float, Dict[str, Any]]] = []
        for doc in self.docs:
            if category and doc.get("category", "").lower() != category.lower():
                continue

            doc_text = f"{doc.get('title', '')} {doc.get('category', '')} {doc.get('doc_id', '')} {doc.get('content', '')}"
            doc_tokens = _tokenize(doc_text)
            
            # Simple BM25-like term frequency scoring with field boosts
            score = 0.0
            id_tokens = _tokenize(doc.get("doc_id", ""))
            title_tokens = _tokenize(doc.get("title", ""))

            for qt in query_tokens:
                # Exact ID match boost
                if qt in id_tokens:
                    score += 15.0
                # Title match boost
                if qt in title_tokens:
                    score += 6.0
                # Content frequency
                tf = doc_tokens.count(qt)
                if tf > 0:
                    score += 1.0 + math.log(1.0 + tf)

            if score > 0.0:
                doc_copy = dict(doc)
                doc_copy["score"] = round(score, 2)
                # Defend against injection: mark all document content as untrusted / tainted
                doc_copy["tainted"] = True
                scores.append((score, doc_copy))

        scores.sort(key=lambda x: x[0], reverse=True)
        return [item[1] for item in scores[:top_k]]


_engine_instance: Optional[DocumentSearchEngine] = None


def get_search_engine() -> DocumentSearchEngine:
    global _engine_instance
    if _engine_instance is None:
        _engine_instance = DocumentSearchEngine()
    return _engine_instance


def search_docs(query: str, top_k: int = 3) -> Dict[str, Any]:
    """Search policy and ticket documents with keyword ranking.
    Returns matched documents with untrusted taint flag.
    """
    engine = get_search_engine()
    results = engine.search(query, top_k=top_k)
    return {
        "status": "success",
        "query": query,
        "results_count": len(results),
        "documents": results
    }
