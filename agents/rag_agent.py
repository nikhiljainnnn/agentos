"""
RAG Agent: Hybrid retrieval (ChromaDB dense search) with re-ranking.

FIX: self.embedder.encode() is CPU-bound and blocks the async event loop.
     All encode() calls are now wrapped in asyncio.to_thread() so the
     event loop stays free during embedding computation.
"""

import asyncio
import hashlib
import time
from functools import partial
from typing import Any, Dict, List, Optional

import chromadb
import structlog
from sentence_transformers import SentenceTransformer
from langchain.text_splitter import RecursiveCharacterTextSplitter

from gateway.config import get_settings

logger = structlog.get_logger(__name__)
settings = get_settings()


class RAGAgent:
    def __init__(self):
        self.embedder = SentenceTransformer(settings.embedding_model)
        self.chroma = chromadb.HttpClient(
            host=settings.chroma_host,
            port=settings.chroma_port,
        )
        self.splitter = RecursiveCharacterTextSplitter(
            chunk_size=settings.chunk_size,
            chunk_overlap=settings.chunk_overlap,
            separators=["\n\n", "\n", ".", " "],
        )
        self._collections: Dict[str, chromadb.Collection] = {}

    def _get_collection(self, namespace: str) -> chromadb.Collection:
        if namespace not in self._collections:
            self._collections[namespace] = self.chroma.get_or_create_collection(
                name=f"agentos_{namespace}",
                metadata={"hnsw:space": "cosine"},
            )
        return self._collections[namespace]

    async def _embed(self, texts: list[str] | str) -> list:
        """
        Non-blocking embed. Offloads CPU-bound SentenceTransformer.encode()
        to a ThreadPoolExecutor via asyncio.to_thread() so the event loop
        stays responsive during encoding (which can take 50-500ms per batch).
        """
        if isinstance(texts, str):
            texts = [texts]
        result = await asyncio.to_thread(self.embedder.encode, texts)
        return result.tolist()

    async def ingest(
        self,
        title: str,
        content: str,
        metadata: Dict[str, Any] = {},
        namespace: str = "default",
    ) -> Dict[str, Any]:
        """Chunk, embed (non-blocking), and upsert into ChromaDB."""
        t0 = time.monotonic()
        chunks = self.splitter.split_text(content)
        collection = self._get_collection(namespace)

        # Embed all chunks in one batched non-blocking call
        embeddings = await self._embed(chunks)

        ids, docs, metas = [], [], []
        for i, chunk in enumerate(chunks):
            chunk_id = hashlib.md5(f"{title}:{i}:{chunk[:50]}".encode()).hexdigest()
            ids.append(chunk_id)
            docs.append(chunk)
            metas.append({**metadata, "title": title, "chunk_index": i})

        # ChromaDB upsert is synchronous — run in thread too
        await asyncio.to_thread(
            collection.upsert,
            ids=ids,
            embeddings=embeddings,
            documents=docs,
            metadatas=metas,
        )

        latency = (time.monotonic() - t0) * 1000
        logger.info(
            "rag_ingest",
            title=title,
            chunks=len(chunks),
            latency_ms=round(latency, 1),
        )
        return {"title": title, "chunk_count": len(chunks), "namespace": namespace}

    async def retrieve(
        self,
        query: str,
        namespace: str = "default",
        top_k: int = 5,
        score_threshold: float = 0.4,
    ) -> tuple[List[Dict[str, Any]], float]:
        """
        Retrieve relevant chunks. Returns (contexts, latency_ms).
        Both embed() and ChromaDB query run off the event loop.
        """
        t0 = time.monotonic()
        collection = self._get_collection(namespace)

        # Non-blocking embed of the query string
        query_embeddings = await self._embed(query)  # returns [[...]]

        # ChromaDB query is synchronous — run in thread
        results = await asyncio.to_thread(
            collection.query,
            query_embeddings=query_embeddings,
            n_results=top_k,
            include=["documents", "metadatas", "distances"],
        )

        contexts = []
        if results["documents"]:
            for doc, meta, dist in zip(
                results["documents"][0],
                results["metadatas"][0],
                results["distances"][0],
            ):
                score = 1 - dist  # cosine distance → similarity
                if score >= score_threshold:
                    contexts.append({
                        "content": doc,
                        "metadata": meta,
                        "score": round(score, 4),
                    })

        contexts.sort(key=lambda x: x["score"], reverse=True)
        latency = (time.monotonic() - t0) * 1000

        logger.info(
            "rag_retrieve",
            query=query[:50],
            results=len(contexts),
            latency_ms=round(latency, 1),
        )
        return contexts, latency

    def format_context(self, contexts: List[Dict]) -> str:
        if not contexts:
            return "No relevant context found in knowledge base."
        lines = ["## Retrieved Context\n"]
        for i, ctx in enumerate(contexts, 1):
            title = ctx["metadata"].get("title", "Unknown")
            lines.append(f"**[{i}] {title}** (relevance: {ctx['score']:.2f})")
            lines.append(ctx["content"])
            lines.append("")
        return "\n".join(lines)


_rag_agent: Optional[RAGAgent] = None


def get_rag_agent() -> RAGAgent:
    global _rag_agent
    if _rag_agent is None:
        _rag_agent = RAGAgent()
    return _rag_agent
