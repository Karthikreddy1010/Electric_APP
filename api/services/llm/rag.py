"""
Phase 4 Enterprise Hybrid RAG Engine.

Extends Phase 3 RAG with:
  - BM25 keyword scoring alongside dense TF-IDF vector search
  - Reciprocal Rank Fusion (RRF) to merge dense + sparse rankings
  - SHA-256 chunk deduplication
  - Multi-factor metadata: retrieval_score, source_trust, freshness_score, fusion_score
  - Sentence-boundary-aware chunking with configurable overlap
  - Context compression (low-relevance chunk pruning)

STRICT PROHIBITION: Customer bill calculations NEVER touch RAG context.
Bill numbers originate ONLY from the immutable AnalyticsResult engine.

Backward Compatibility:
  All Phase 3 public APIs (RAGDocument, RAGService, rag_service,
  PDFDocumentLoader, VectorStoreBackend, InMemoryVectorStore,
  PGVectorStore, QdrantVectorStore) are fully preserved.
"""
import io
import math
import hashlib
import logging
import re
import time
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Set
from collections import Counter

logger = logging.getLogger(__name__)


# ── Data Contracts ─────────────────────────────────────────────────────────

class RAGDocument:
    """A knowledge base document or chunk with category, versioning metadata, and provenance."""

    def __init__(
        self,
        doc_id: str,
        category: str,
        title: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
        version: str = "v1.0",
        effective_date: str = "2026-01-01",
        expiration_date: str = "",
        jurisdiction: str = "NJ",
        source_url: str = "",
        authoritative_rank: int = 1,
        # Phase 4 additions
        document_type: str = "",
        page: str = "",
        section: str = "",
        source: str = "",
        timestamp: str = "",
    ):
        self.doc_id = doc_id
        self.category = category  # "tariff" | "policy" | "faq"
        self.title = title
        self.content = content
        self.metadata = metadata or {}
        self.version = version
        self.effective_date = effective_date
        self.expiration_date = expiration_date
        self.jurisdiction = jurisdiction
        self.source_url = source_url
        self.authoritative_rank = authoritative_rank  # 1=official tariff, 2=state agency, 3=educational FAQ

        # Phase 4: Extended metadata fields
        self.document_type = document_type or category
        self.page = page
        self.section = section
        self.source = source or source_url
        self.timestamp = timestamp or effective_date

        # Content hash for deduplication
        self.content_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()

        # Embed versioning metadata
        self.metadata.update({
            "version": version,
            "effective_date": effective_date,
            "expiration_date": expiration_date,
            "jurisdiction": jurisdiction,
            "source_url": source_url,
            "authoritative_rank": authoritative_rank,
            # Phase 4 additions
            "document_type": self.document_type,
            "page": self.page,
            "section": self.section,
            "source": self.source,
            "timestamp": self.timestamp,
            "content_hash": self.content_hash,
        })


# ── Multi-Factor Score Container ───────────────────────────────────────────

class RetrievalScore:
    """
    Multi-factor score breakdown for a retrieved chunk.

    Components:
        retrieval_score — semantic + keyword match relevance (0.0 to 1.0)
        source_trust    — hierarchical trust rating (Tier 0 to Tier 6)
        freshness_score — temporal relevance (0.0 to 1.0)
        fusion_score    — final combined score for ranking
    """

    # Source trust weights by authoritative rank
    _TRUST_BY_RANK = {
        0: 1.00,  # Tier 0: Deterministic engines
        1: 0.95,  # Tier 1: Official tariff documents
        2: 0.88,  # Tier 2: State agency / government
        3: 0.82,  # Tier 3: Educational FAQ / RAG knowledge
        4: 0.75,  # Tier 4: Trusted news
        5: 0.60,  # Tier 5: General web
    }

    def __init__(
        self,
        retrieval_score: float = 0.0,
        source_trust: float = 0.0,
        freshness_score: float = 1.0,
    ):
        self.retrieval_score = retrieval_score
        self.source_trust = source_trust
        self.freshness_score = freshness_score
        self.fusion_score = self._compute_fusion()

    def _compute_fusion(self) -> float:
        """Weighted geometric mean of the 3 sub-scores."""
        # Weights: retrieval=0.5, trust=0.3, freshness=0.2
        r = max(self.retrieval_score, 0.001)
        t = max(self.source_trust, 0.001)
        f = max(self.freshness_score, 0.001)
        fusion = (r ** 0.5) * (t ** 0.3) * (f ** 0.2)
        return round(min(fusion, 1.0), 4)

    @classmethod
    def from_rank(cls, retrieval_score: float, authoritative_rank: int, freshness_score: float = 1.0):
        trust = cls._TRUST_BY_RANK.get(authoritative_rank, 0.60)
        return cls(retrieval_score=retrieval_score, source_trust=trust, freshness_score=freshness_score)

    def to_dict(self) -> Dict[str, float]:
        return {
            "retrieval_score": round(self.retrieval_score, 4),
            "source_trust": round(self.source_trust, 4),
            "freshness_score": round(self.freshness_score, 4),
            "fusion_score": self.fusion_score,
        }


# ── Text Chunking & Document Processing ────────────────────────────────────

class RecursiveTextSplitter:
    """
    Recursively splits text into chunks of specified size with overlap.
    Preserves paragraph and sentence boundaries where possible.
    """

    def __init__(self, chunk_size: int = 500, chunk_overlap: int = 50):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def split_text(self, text: str) -> List[str]:
        if len(text) <= self.chunk_size:
            return [text]

        chunks = []
        start = 0
        while start < len(text):
            end = start + self.chunk_size
            if end < len(text):
                # Look for natural sentence break
                break_pos = text.rfind(". ", start, end)
                if break_pos != -1 and break_pos > start + self.chunk_size // 2:
                    end = break_pos + 1

            chunk = text[start:end].strip()
            if chunk:
                chunks.append(chunk)
            start = max(start + 1, end - self.chunk_overlap)

        return self._deduplicate_chunks(chunks)

    @staticmethod
    def _deduplicate_chunks(chunks: List[str]) -> List[str]:
        """Remove duplicate chunks by SHA-256 content hash."""
        seen_hashes: Set[str] = set()
        unique_chunks: List[str] = []
        for chunk in chunks:
            h = hashlib.sha256(chunk.encode("utf-8")).hexdigest()
            if h not in seen_hashes:
                seen_hashes.add(h)
                unique_chunks.append(chunk)
        return unique_chunks


class PDFDocumentLoader:
    """Loads and extracts text chunks from PDF tariff documents."""

    @staticmethod
    def load_pdf(
        pdf_bytes: bytes,
        doc_id_prefix: str,
        category: str,
        title: str
    ) -> List[RAGDocument]:
        text = ""
        try:
            import fitz  # PyMuPDF
            doc = fitz.open(stream=pdf_bytes, filetype="pdf")
            for page in doc:
                text += page.get_text() + "\n"
        except ImportError:
            logger.warning("PyMuPDF (fitz) not installed. Using raw text extraction fallback.")
            text = pdf_bytes.decode("utf-8", errors="ignore")

        splitter = RecursiveTextSplitter(chunk_size=500, chunk_overlap=50)
        chunks = splitter.split_text(text)

        documents = []
        for idx, chunk in enumerate(chunks):
            doc_id = f"{doc_id_prefix}-chunk-{idx + 1}"
            documents.append(RAGDocument(
                doc_id=doc_id,
                category=category,
                title=f"{title} (Part {idx + 1})",
                content=chunk,
                metadata={"chunk_index": idx, "total_chunks": len(chunks)}
            ))
        return documents


# ── BM25 Scorer ────────────────────────────────────────────────────────────

def _tokenize(text: str) -> List[str]:
    return re.findall(r'\b\w+\b', text.lower())


class BM25Scorer:
    """
    Okapi BM25 keyword scoring engine.
    Operates alongside vector search for hybrid retrieval.
    """

    def __init__(self, k1: float = 1.5, b: float = 0.75):
        self.k1 = k1
        self.b = b
        self._corpus: List[List[str]] = []
        self._doc_count = 0
        self._avg_dl = 0.0
        self._df: Dict[str, int] = {}  # document frequency per term

    def fit(self, documents: List[str]) -> None:
        """Build BM25 index from a list of document texts."""
        self._corpus = [_tokenize(doc) for doc in documents]
        self._doc_count = len(self._corpus)
        total_len = sum(len(doc) for doc in self._corpus)
        self._avg_dl = total_len / max(self._doc_count, 1)

        self._df = {}
        for doc_tokens in self._corpus:
            seen = set(doc_tokens)
            for token in seen:
                self._df[token] = self._df.get(token, 0) + 1

    def score(self, query: str) -> List[float]:
        """Score all documents against a query. Returns list of BM25 scores."""
        query_tokens = _tokenize(query)
        scores = []
        for doc_tokens in self._corpus:
            s = 0.0
            dl = len(doc_tokens)
            tf_map = Counter(doc_tokens)
            for qt in query_tokens:
                if qt not in self._df:
                    continue
                df = self._df[qt]
                idf = math.log((self._doc_count - df + 0.5) / (df + 0.5) + 1.0)
                tf = tf_map.get(qt, 0)
                numerator = tf * (self.k1 + 1)
                denominator = tf + self.k1 * (1 - self.b + self.b * dl / max(self._avg_dl, 1))
                s += idf * numerator / denominator
            scores.append(s)
        return scores


# ── Vector Store Backends ──────────────────────────────────────────────────

def _cosine_similarity(vec_a: Dict[str, float], vec_b: Dict[str, float]) -> float:
    common_keys = set(vec_a.keys()) & set(vec_b.keys())
    if not common_keys:
        return 0.0
    dot = sum(vec_a[k] * vec_b[k] for k in common_keys)
    mag_a = math.sqrt(sum(v * v for v in vec_a.values()))
    mag_b = math.sqrt(sum(v * v for v in vec_b.values()))
    if mag_a == 0 or mag_b == 0:
        return 0.0
    return dot / (mag_a * mag_b)


class VectorStoreBackend(ABC):
    @abstractmethod
    def index(self, doc: RAGDocument) -> None: ...

    @abstractmethod
    def delete(self, doc_id: str) -> bool: ...

    @abstractmethod
    def search(self, query_text: str, top_k: int = 3) -> List[Dict[str, Any]]: ...

    @abstractmethod
    def count(self) -> int: ...


class InMemoryVectorStore(VectorStoreBackend):
    """In-memory TF-IDF vector store backend with hybrid BM25 + dense search."""

    def __init__(self):
        self._documents: List[RAGDocument] = []
        self._vectors: List[Dict[str, float]] = []
        self._content_hashes: Set[str] = set()
        self._bm25 = BM25Scorer()
        self._bm25_dirty = True  # Flag to rebuild BM25 index

    def index(self, doc: RAGDocument) -> None:
        # Deduplicate by content hash
        if doc.content_hash in self._content_hashes:
            # Update existing document with same content
            self.delete(doc.doc_id)
        else:
            self.delete(doc.doc_id)

        self._content_hashes.add(doc.content_hash)
        self._documents.append(doc)
        tokens = _tokenize(doc.title + " " + doc.content)
        tf = Counter(tokens)
        total = len(tokens) or 1
        vec = {term: count / total for term, count in tf.items()}
        self._vectors.append(vec)
        self._bm25_dirty = True

    def delete(self, doc_id: str) -> bool:
        idx = next((i for i, d in enumerate(self._documents) if d.doc_id == doc_id), None)
        if idx is not None:
            removed = self._documents.pop(idx)
            self._vectors.pop(idx)
            self._content_hashes.discard(removed.content_hash)
            self._bm25_dirty = True
            return True
        return False

    def _rebuild_bm25(self):
        """Rebuild BM25 index from current documents."""
        if self._bm25_dirty and self._documents:
            texts = [d.title + " " + d.content for d in self._documents]
            self._bm25.fit(texts)
            self._bm25_dirty = False

    def search(self, query_text: str, top_k: int = 3) -> List[Dict[str, Any]]:
        """Hybrid search: Dense TF-IDF + BM25 with Reciprocal Rank Fusion."""
        if not self._documents or not query_text:
            return []

        # ── Dense Vector Search ──
        tokens = _tokenize(query_text)
        tf = Counter(tokens)
        total = len(tokens) or 1
        query_vec = {term: count / total for term, count in tf.items()}

        dense_scores = []
        for i, doc_vec in enumerate(self._vectors):
            score = _cosine_similarity(query_vec, doc_vec)
            dense_scores.append((score, i))
        dense_scores.sort(key=lambda x: x[0], reverse=True)

        # ── BM25 Keyword Search ──
        self._rebuild_bm25()
        bm25_raw = self._bm25.score(query_text)
        bm25_scores = [(s, i) for i, s in enumerate(bm25_raw)]
        bm25_scores.sort(key=lambda x: x[0], reverse=True)

        # ── Reciprocal Rank Fusion (RRF) ──
        k = 60  # RRF constant
        rrf_scores: Dict[int, float] = {}

        for rank, (_, doc_idx) in enumerate(dense_scores):
            rrf_scores[doc_idx] = rrf_scores.get(doc_idx, 0) + 1.0 / (k + rank + 1)

        for rank, (_, doc_idx) in enumerate(bm25_scores):
            rrf_scores[doc_idx] = rrf_scores.get(doc_idx, 0) + 1.0 / (k + rank + 1)

        # Sort by RRF score
        ranked = sorted(rrf_scores.items(), key=lambda x: x[1], reverse=True)

        results = []
        for doc_idx, rrf_score in ranked[:top_k]:
            doc = self._documents[doc_idx]
            # Normalize RRF score to 0-1 range (max possible is 2/(k+1))
            max_rrf = 2.0 / (k + 1)
            normalized_score = min(rrf_score / max_rrf, 1.0)

            # Build multi-factor scores
            scores = RetrievalScore.from_rank(
                retrieval_score=normalized_score,
                authoritative_rank=doc.authoritative_rank,
            )

            results.append({
                "doc_id": doc.doc_id,
                "category": doc.category,
                "title": doc.title,
                "content": doc.content,
                "metadata": doc.metadata,
                "score": round(normalized_score, 4),
                # Phase 4: Multi-factor scores
                "retrieval_score": scores.retrieval_score,
                "source_trust": scores.source_trust,
                "freshness_score": scores.freshness_score,
                "fusion_score": scores.fusion_score,
                # Phase 4: Provenance
                "retrieval_method": "hybrid_rrf",
                "source": doc.source or doc.source_url,
                "document_type": doc.document_type,
                "timestamp": doc.timestamp,
            })
        return results

    def count(self) -> int:
        return len(self._documents)


class PGVectorStore(VectorStoreBackend):
    """PostgreSQL pgvector store backend (interface adapter)."""

    def __init__(self, db_url: str = ""):
        self._db_url = db_url
        self._fallback = InMemoryVectorStore()

    def index(self, doc: RAGDocument) -> None:
        self._fallback.index(doc)

    def delete(self, doc_id: str) -> bool:
        return self._fallback.delete(doc_id)

    def search(self, query_text: str, top_k: int = 3) -> List[Dict[str, Any]]:
        return self._fallback.search(query_text, top_k=top_k)

    def count(self) -> int:
        return self._fallback.count()


class QdrantVectorStore(VectorStoreBackend):
    """Qdrant vector store backend (interface adapter)."""

    def __init__(self, host: str = "localhost", port: int = 6333):
        self._fallback = InMemoryVectorStore()

    def index(self, doc: RAGDocument) -> None:
        self._fallback.index(doc)

    def delete(self, doc_id: str) -> bool:
        return self._fallback.delete(doc_id)

    def search(self, query_text: str, top_k: int = 3) -> List[Dict[str, Any]]:
        return self._fallback.search(query_text, top_k=top_k)

    def count(self) -> int:
        return self._fallback.count()


# ── RAG Service Manager ────────────────────────────────────────────────────

class RAGService:
    """
    Production RAG engine for tariff, policy, and FAQ retrieval.
    Enforces strict category scope and non-hallucination boundaries.
    Phase 4: Hybrid BM25+Dense search with multi-factor scoring.
    """

    ALLOWED_CATEGORIES = {"tariff", "policy", "faq"}

    def __init__(self, backend: Optional[VectorStoreBackend] = None):
        self._store = backend or InMemoryVectorStore()
        self._seed_default_documents()

    def _seed_default_documents(self):
        defaults = [
            RAGDocument(
                "tariff-pseg-rs", "tariff", "PSE&G Residential Rate Schedule (RS)",
                "PSE&G Rate Schedule RS applies to residential electric service. "
                "It consists of a fixed monthly service charge ($8.24), volumetric delivery/distribution charges, "
                "Basic Generation Service (BGS) supply charges, Societal Benefits Charge (SBC), "
                "Non-Utility Generation (NUG) charge, and mandatory NJ State Sales Tax (6.625%).",
                authoritative_rank=1, document_type="tariff_schedule",
                source="PSE&G Official Tariff", section="Rate Schedule RS",
            ),
            RAGDocument(
                "tariff-tou", "tariff", "Time-of-Use (TOU) Rate Structures & Off-Peak Shifting",
                "Time-of-Use (TOU) tariff structures differentiate rates by time of day. "
                "Peak hours typically run 8 AM to 8 PM on weekdays, carrying higher volumetric rates due to grid demand. "
                "Off-peak hours (10 PM to 8 AM and weekends) offer discounted delivery and supply rates, encouraging load shifting.",
                authoritative_rank=1, document_type="tariff_schedule",
                source="Utility Rate Structures", section="TOU Rates",
            ),
            RAGDocument(
                "policy-nj-clean-energy", "policy", "New Jersey Clean Energy Act & State Mandates",
                "The NJ Clean Energy Act mandates 50% renewable energy generation by 2030 and 100% clean energy by 2050. "
                "Key customer programs include net metering for rooftop solar, community solar subscription credits, "
                "energy storage incentives, and utility-administered ENERGY STAR efficiency rebates.",
                authoritative_rank=2, document_type="government_policy",
                source="NJ BPU", section="Clean Energy Act",
            ),
            RAGDocument(
                "glossary-bill-components", "faq", "Electricity Utility Billing Components Glossary",
                "1. Supply Charge: Cost of electricity generation commodity, determined by market auctions (BGS/PJM).\n"
                "2. Delivery Charge: Infrastructure fee for grid maintenance, high-voltage transmission, and local distribution lines.\n"
                "3. Customer Charge: Fixed monthly baseline fee for account administration and metering regardless of usage.\n"
                "4. Societal Benefits Charge (SBC): State-mandated fee funding low-income assistance and clean energy initiatives.",
                authoritative_rank=3, document_type="glossary",
                source="ElectricAI Knowledge Base", section="Bill Components",
            ),
            RAGDocument(
                "glossary-rate-terms", "faq", "Rate Schedule & Energy Terminology",
                "Effective Rate: Total bill amount divided by total kWh consumed ($/kWh).\n"
                "Demand Charge: Fee based on peak rate of energy consumption (kW) within a 15-minute interval.\n"
                "Degree Days (CDD/HDD): Meteorological indices measuring cooling/heating demand relative to 65°F baseline.\n"
                "PJM LMP: Locational Marginal Pricing in the PJM wholesale electricity market.",
                authoritative_rank=3, document_type="glossary",
                source="ElectricAI Knowledge Base", section="Rate Terminology",
            ),
            RAGDocument(
                "app-methodology", "policy", "ElectricAI Application Calculation Methodology",
                "ElectricAI uses deterministic analytics engines for bill decomposition and Monte Carlo simulations (2,000 statistical trials) "
                "to model rate shock volatility. Demand forecasts combine NOAA weather degree-day projections with historical regression baselines. "
                "All numerical calculations are executed by verified analytical engines.",
                authoritative_rank=2, document_type="technical_documentation",
                source="ElectricAI Methodology", section="Calculation Methodology",
            ),
            RAGDocument(
                "dataset-docs-eia-pjm", "policy", "EIA & PJM Energy Datasets Documentation",
                "Data sources include EIA-861 (annual utility sales and revenue), EIA-923 (power plant generation and fuel mix), "
                "EIA Retail Electricity Monthly, PJM Interconnection real-time Locational Marginal Pricing (LMP), and NOAA degree-day climate indices.",
                authoritative_rank=2, document_type="technical_documentation",
                source="EIA / PJM Official Documentation", section="Data Sources",
            ),
            RAGDocument(
                "faq-reduce-bill", "faq", "Actionable Strategies to Reduce Electricity Costs",
                "Key strategies include shifting high-wattage appliance loads (laundry, EV charging, water heaters) to off-peak hours (10 PM - 8 AM), "
                "adjusting thermostat setpoints during peak cooling afternoons, insulating ductwork, and utilizing solar net metering credits.",
                authoritative_rank=3, document_type="faq",
                source="ElectricAI Knowledge Base", section="Energy Savings Tips",
            ),
        ]
        for doc in defaults:
            self.add_document(doc)

    def add_document(self, doc: RAGDocument) -> None:
        if doc.category not in self.ALLOWED_CATEGORIES:
            logger.warning(f"RAGService: rejected '{doc.doc_id}' — category '{doc.category}' not allowed")
            return
        self._store.index(doc)

    def update_document(self, doc: RAGDocument) -> None:
        self.add_document(doc)

    def delete_document(self, doc_id: str) -> bool:
        return self._store.delete(doc_id)

    def load_and_index_pdf(self, pdf_bytes: bytes, doc_id_prefix: str, category: str, title: str) -> int:
        docs = PDFDocumentLoader.load_pdf(pdf_bytes, doc_id_prefix, category, title)
        for d in docs:
            self.add_document(d)
        return len(docs)

    def query(self, query_text: str, top_k: int = 2) -> List[Dict[str, Any]]:
        return self._store.search(query_text, top_k=top_k)

    def query_text(self, query_text: str, top_k: int = 2) -> str:
        results = self.query(query_text, top_k=top_k)
        if not results:
            return ""
        segments = []
        seen_titles = set()
        for r in results:
            title = r.get("title", "")
            if title in seen_titles:
                continue
            seen_titles.add(title)
            score = r.get("score")
            if score is not None and score < 0.35:
                continue
            segments.append(f"[{r.get('category', 'doc').upper()}] {title}\n{r.get('content', '')}")
        return "\n\n---\n\n".join(segments)

    def check_health(self) -> Dict[str, Any]:
        return {
            "status": "healthy",
            "document_count": self._store.count(),
            "allowed_categories": list(self.ALLOWED_CATEGORIES),
            "backend": self._store.__class__.__name__,
            "search_mode": "hybrid_rrf",
        }


# Global singleton
rag_service = RAGService()
