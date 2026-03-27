# Generic imports
import math
import os
import json
import re
from collections import Counter

# Specific imports
import chromadb
from sentence_transformers import SentenceTransformer

# Custom imports
from log.logger import mLogError, mLogInfo
from entities.utils.files import mGetConfigProperty, mGetAssetsDir


class BM25Scorer:
    """Lightweight BM25 scorer operating on an in-memory perk corpus."""

    _TOKENIZE_RE = re.compile(r'[a-z0-9]+')

    def __init__(self, corpus: dict[str, str], k1: float = 1.5, b: float = 0.75):
        """
        Args:
            corpus: mapping of perk name -> description text.
            k1: BM25 term-frequency saturation parameter.
            b: BM25 length-normalization parameter.
        """
        self._k1 = k1
        self._b = b
        self._names: list[str] = list(corpus.keys())
        # Tokenize every document
        self._docs: list[list[str]] = [self._tokenize(d) for d in corpus.values()]
        self._doc_lens: list[int] = [len(d) for d in self._docs]
        self._avgdl: float = sum(self._doc_lens) / max(len(self._docs), 1)
        self._N: int = len(self._docs)
        # Build IDF: how many docs contain each term
        self._df: dict[str, int] = Counter()
        for doc in self._docs:
            for term in set(doc):
                self._df[term] += 1

    @classmethod
    def _tokenize(cls, text: str) -> list[str]:
        """Lowercase + split on non-alphanumeric."""
        return cls._TOKENIZE_RE.findall(text.lower())

    def _idf(self, term: str) -> float:
        df = self._df.get(term, 0)
        return math.log((self._N - df + 0.5) / (df + 0.5) + 1.0)

    def _score_doc(self, query_terms: list[str], doc_idx: int) -> float:
        tf_map = Counter(self._docs[doc_idx])
        dl = self._doc_lens[doc_idx]
        score = 0.0
        for qt in query_terms:
            tf = tf_map.get(qt, 0)
            if tf == 0:
                continue
            idf = self._idf(qt)
            numerator = tf * (self._k1 + 1)
            denominator = tf + self._k1 * (1 - self._b + self._b * dl / self._avgdl)
            score += idf * numerator / denominator
        return score

    def rank(self, query: str, blacklist: set[str] | None = None, top_k: int = 20) -> list[str]:
        """Return perk names ranked by BM25 relevance to *query*."""
        query_terms = self._tokenize(query)
        scored: list[tuple[float, str]] = []
        for idx, name in enumerate(self._names):
            if blacklist and name in blacklist:
                continue
            s = self._score_doc(query_terms, idx)
            if s > 0:
                scored.append((s, name))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [name for _, name in scored[:top_k]]


class DBDRagPipeline:

    def __init__(self):
        self._llm_perk_path = os.path.join(mGetAssetsDir(), "dbd", "llm_perk.json")
        self._collection_name = "perk_synergies"
        self._chroma_dir = os.path.join(mGetAssetsDir(), "dbd", "chroma_db")
        os.makedirs(self._chroma_dir, exist_ok=True)
        
        # Initialize Persistent ChromaDB
        self._chroma_client = chromadb.PersistentClient(path=self._chroma_dir)
        self._collection = None
        self._model = None
        self._bm25: BM25Scorer | None = None
        mLogInfo("DBDRagPipeline initialized")

    @property
    def model(self):
        if self._model is None:
            mLogInfo("Loading sentence-transformers model (all-MiniLM-L6-v2)...")
            self._model = SentenceTransformer("all-MiniLM-L6-v2")
            mLogInfo("Model loaded successfully")
        return self._model

    def init_llm_perk_data(self, perks_data: list[dict]):
        """Creates llm_perk.json with only names and descriptions."""
        if os.path.exists(self._llm_perk_path):
            return

        mLogInfo("Creating llm_perk.json for RAG pipeline...")
        llm_perks = {}
        for perk in perks_data:
            name = perk.get('name')
            description = perk.get('main_effect', '')
            if name:
                llm_perks[name] = description

        with open(self._llm_perk_path, 'w', encoding='utf-8') as f:
            json.dump(llm_perks, f, indent=4)
        mLogInfo(f"Wrote {len(llm_perks)} perks to {self._llm_perk_path}")

    def init_chromadb(self):
        """Initializes ChromaDB collection and populates it if empty."""
        try:
            self._collection = self._chroma_client.get_collection(name=self._collection_name)
        except Exception:
            self._collection = self._chroma_client.create_collection(
                name=self._collection_name, 
                metadata={"hnsw:space": "cosine"}
            )
            
        if not os.path.exists(self._llm_perk_path):
            mLogError("llm_perk.json not found! Cannot populate ChromaDB.")
            return

        with open(self._llm_perk_path, 'r', encoding='utf-8') as f:
            llm_perks = json.load(f)

        # Always build/rebuild the BM25 scorer from the corpus
        if self._bm25 is None:
            mLogInfo("Building BM25 scorer from perk corpus...")
            self._bm25 = BM25Scorer(llm_perks)
            mLogInfo("BM25 scorer ready")

        if self._collection.count() > 0:
            mLogInfo("ChromaDB collection already populated")
            return

        names = list(llm_perks.keys())
        descriptions = list(llm_perks.values())

        mLogInfo(f"Embedding {len(names)} perks...")
        embeddings = self.model.encode(descriptions).tolist()

        # Generate metadata dict list for where filtering later
        metadatas = [{"name": n} for n in names]

        self._collection.add(
            ids=names,
            embeddings=embeddings,
            metadatas=metadatas,
            documents=descriptions
        )
        mLogInfo("ChromaDB collection populated successfully")

    def retrieve_similar_perks(self, target_desc: str, blacklist: list[str] = None, top_k: int = 20) -> list[str]:
        """Queries ChromaDB for similar perks, returning a list of names."""
        if not self._collection:
            self.init_chromadb()
            
        mLogInfo(f"Querying ChromaDB for {top_k} similar perks...")
        target_embedding = self.model.encode([target_desc]).tolist()
        
        where_clause = None
        if blacklist and len(blacklist) > 0:
            where_clause = {"name": {"$nin": blacklist}}

        results = self._collection.query(
            query_embeddings=target_embedding,
            n_results=top_k,
            where=where_clause
        )
        
        # results["ids"] is a list of lists.
        if results and results["ids"] and len(results["ids"]) > 0:
            return results["ids"][0]
        return []

    # ------------------------------------------------------------------
    # Hybrid retrieval (Semantic + BM25 + RRF)
    # ------------------------------------------------------------------

    @staticmethod
    def _reciprocal_rank_fusion(ranked_lists: list[list[str]], k: int = 60) -> list[str]:
        """Merge multiple ranked lists using Reciprocal Rank Fusion.

        For each document *d* that appears in any list:
            score(d) = sum( 1 / (k + rank_i(d))  for each list i where d appears )

        A higher score means more lists agree the document is relevant.
        """
        scores: dict[str, float] = {}
        for ranked in ranked_lists:
            for rank, name in enumerate(ranked, start=1):
                scores[name] = scores.get(name, 0.0) + 1.0 / (k + rank)
        # Sort descending by fused score
        return sorted(scores, key=scores.get, reverse=True)

    def retrieve_hybrid(
        self,
        target_desc: str,
        blacklist: list[str] | None = None,
        top_k: int = 20,
    ) -> list[str]:
        """Hybrid retrieval: fuse semantic (ChromaDB) + keyword (BM25) results via RRF."""
        # --- Semantic leg ---
        semantic_results = self.retrieve_similar_perks(target_desc, blacklist=blacklist, top_k=top_k)

        # --- BM25 leg ---
        bm25_results: list[str] = []
        if self._bm25 is not None:
            blacklist_set = set(blacklist) if blacklist else None
            bm25_results = self._bm25.rank(target_desc, blacklist=blacklist_set, top_k=top_k)
            mLogInfo(f"BM25 returned {len(bm25_results)} results")
        else:
            mLogInfo("BM25 scorer not initialized — falling back to semantic-only")

        # --- Fuse ---
        if not bm25_results:
            return semantic_results

        fused = self._reciprocal_rank_fusion([semantic_results, bm25_results])
        mLogInfo(f"RRF fused {len(fused)} unique perks from semantic ({len(semantic_results)}) + BM25 ({len(bm25_results)})")
        return fused[:top_k]

    def clear_rag_data(self):
        """Clears llm_perk.json and ChromaDB collection."""
        if os.path.exists(self._llm_perk_path):
            os.remove(self._llm_perk_path)
            mLogInfo("Deleted llm_perk.json")
            
        try:
            self._chroma_client.delete_collection(self._collection_name)
            mLogInfo(f"Deleted collection {self._collection_name}")
            self._collection = None
        except Exception as e:
            mLogError(f"Error deleting collection: {e}")
        self._bm25 = None

# Global singleton
_rag_pipeline = None

def get_rag_pipeline() -> DBDRagPipeline:
    global _rag_pipeline
    if _rag_pipeline is None:
        _rag_pipeline = DBDRagPipeline()
    return _rag_pipeline
