# Generic imports
import os
import json

# Specific imports
import chromadb
from sentence_transformers import SentenceTransformer

# Custom imports
from log.logger import mLogError, mLogInfo
from entities.utils.files import mGetConfigProperty, mGetAssetsDir

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
            
        if self._collection.count() > 0:
            mLogInfo("ChromaDB collection already populated")
            return

        mLogInfo("Populating ChromaDB collection...")
        if not os.path.exists(self._llm_perk_path):
            mLogError("llm_perk.json not found! Cannot populate ChromaDB.")
            return

        with open(self._llm_perk_path, 'r', encoding='utf-8') as f:
            llm_perks = json.load(f)

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

# Global singleton
_rag_pipeline = None

def get_rag_pipeline() -> DBDRagPipeline:
    global _rag_pipeline
    if _rag_pipeline is None:
        _rag_pipeline = DBDRagPipeline()
    return _rag_pipeline
