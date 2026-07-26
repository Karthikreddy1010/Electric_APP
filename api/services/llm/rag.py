"""
Phase 2 — Scoped RAG Service.

Retrieval-Augmented Generation engine restricted ONLY to:
  - Tariff documentation & utility rate schedules
  - State energy policies & environmental regulations
  - Frequently Asked Questions (FAQ)

STRICT PROHIBITION: RAG embeddings are NEVER queried or injected during
customer bill calculations. Bill numbers come ONLY from AnalyticsResult.

Phase 2 provides an in-memory TF-IDF vector search fallback.
Production pgvector / Qdrant adapters are interface-ready but require
Phase 3 infrastructure deployment.
"""
import math
import logging
import re
from typing import List, Dict, Any, Optional
from collections import Counter

logger = logging.getLogger(__name__)


class RAGDocument:
    """A knowledge base document with category and content."""

    def __init__(self, doc_id: str, category: str, title: str, content: str):
        self.doc_id = doc_id
        self.category = category  # "tariff" | "policy" | "faq"
        self.title = title
        self.content = content


# ── In-Memory TF-IDF Vector Search ────────────────────────────────────────

def _tokenize(text: str) -> List[str]:
    """Simple whitespace + punctuation tokenizer."""
    return re.findall(r'\b\w+\b', text.lower())


def _cosine_similarity(vec_a: Dict[str, float], vec_b: Dict[str, float]) -> float:
    """Cosine similarity between two sparse term-frequency vectors."""
    common_keys = set(vec_a.keys()) & set(vec_b.keys())
    if not common_keys:
        return 0.0
    dot = sum(vec_a[k] * vec_b[k] for k in common_keys)
    mag_a = math.sqrt(sum(v * v for v in vec_a.values()))
    mag_b = math.sqrt(sum(v * v for v in vec_b.values()))
    if mag_a == 0 or mag_b == 0:
        return 0.0
    return dot / (mag_a * mag_b)


class RAGService:
    """
    In-memory vector search engine for tariff/policy/FAQ documents.
    Uses TF-IDF cosine similarity as a lightweight Phase 2 implementation.
    """

    ALLOWED_CATEGORIES = {"tariff", "policy", "faq"}

    def __init__(self):
        self._documents: List[RAGDocument] = []
        self._vectors: List[Dict[str, float]] = []
        self._seed_default_documents()

    def _seed_default_documents(self):
        """Load built-in tariff and FAQ knowledge base entries."""
        defaults = [
            RAGDocument(
                "tariff-pseg-rs",
                "tariff",
                "PSE&G Residential Rate Schedule (RS)",
                "PSE&G Rate Schedule RS applies to residential customers. "
                "Includes a monthly customer charge of $8.24, BGS supply rate, "
                "distribution charge, societal benefits charge (SBC), "
                "non-utility generation (NUG) charge, and NJ state sales tax at 6.625%."
            ),
            RAGDocument(
                "tariff-tou",
                "tariff",
                "Time-of-Use Rate Structures",
                "Time-of-Use (TOU) rates charge different prices based on time of day. "
                "Peak hours typically run 8 AM to 8 PM weekdays. Off-peak hours offer "
                "lower rates, incentivizing load shifting to reduce bills."
            ),
            RAGDocument(
                "policy-nj-clean-energy",
                "policy",
                "New Jersey Clean Energy Act",
                "The NJ Clean Energy Act mandates 50% renewable energy by 2030 and "
                "100% clean energy by 2050. Utilities must offer net metering for solar "
                "installations and community solar programs."
            ),
            RAGDocument(
                "faq-bill-components",
                "faq",
                "Understanding Your Electric Bill Components",
                "Your electric bill consists of supply charges (energy generation), "
                "delivery charges (transmission and distribution), fixed customer charges, "
                "and applicable taxes. Supply charges are market-driven and fluctuate with "
                "wholesale energy auction prices."
            ),
            RAGDocument(
                "faq-reduce-bill",
                "faq",
                "How to Reduce Your Electricity Bill",
                "Key strategies include shifting consumption to off-peak hours, "
                "upgrading to ENERGY STAR appliances, adjusting thermostat setpoints, "
                "reducing phantom loads from standby electronics, and considering "
                "solar panel installation for net metering credits."
            ),
        ]
        for doc in defaults:
            self.add_document(doc)

    def add_document(self, doc: RAGDocument) -> None:
        """Index a document into the knowledge base."""
        if doc.category not in self.ALLOWED_CATEGORIES:
            logger.warning(
                f"RAGService: rejected document '{doc.doc_id}' — "
                f"category '{doc.category}' is not in allowed set"
            )
            return

        self._documents.append(doc)
        tokens = _tokenize(doc.title + " " + doc.content)
        tf = Counter(tokens)
        total = len(tokens) or 1
        vec = {term: count / total for term, count in tf.items()}
        self._vectors.append(vec)

    def query(self, query_text: str, top_k: int = 3) -> List[Dict[str, Any]]:
        """
        Retrieve the top-k most relevant documents for a query.
        Returns list of {doc_id, category, title, content, score}.
        """
        if not self._documents or not query_text:
            return []

        tokens = _tokenize(query_text)
        tf = Counter(tokens)
        total = len(tokens) or 1
        query_vec = {term: count / total for term, count in tf.items()}

        scored = []
        for i, doc_vec in enumerate(self._vectors):
            score = _cosine_similarity(query_vec, doc_vec)
            if score > 0.0:
                scored.append((score, i))

        scored.sort(key=lambda x: x[0], reverse=True)

        results = []
        for score, idx in scored[:top_k]:
            doc = self._documents[idx]
            results.append({
                "doc_id": doc.doc_id,
                "category": doc.category,
                "title": doc.title,
                "content": doc.content,
                "score": round(score, 4)
            })
        return results

    def query_text(self, query_text: str, top_k: int = 3) -> str:
        """
        Convenience method returning concatenated text from top-k results.
        Ready to be injected as rag_context into PromptRequest.
        """
        results = self.query(query_text, top_k=top_k)
        if not results:
            return ""
        segments = []
        for r in results:
            segments.append(f"[{r['category'].upper()}] {r['title']}\n{r['content']}")
        return "\n\n---\n\n".join(segments)


# Global singleton
rag_service = RAGService()
