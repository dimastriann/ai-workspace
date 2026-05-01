"""
AI Workspace API — Embedding Service

Generates vector embeddings for document chunks using OpenAI or local fallback.
"""

from typing import List

from langchain_openai import OpenAIEmbeddings
# from langchain_huggingface import HuggingFaceEmbeddings # Optional local fallback

from app.config import settings


class EmbeddingService:
    def __init__(self):
        self._openai_embeddings = OpenAIEmbeddings(
            openai_api_key=settings.openai_api_key,
            model=settings.embedding_model,
        )
        
        # In a real future phase, we would initialize local embeddings here 
        # if settings.llm_provider == "local" or openai_api_key is missing.
        self._local_embeddings = None 

    async def embed_query(self, text: str) -> List[float]:
        """Generate an embedding for a single string."""
        if settings.openai_api_key:
            return await self._openai_embeddings.aembed_query(text)
        else:
            # Fallback placeholder
            raise ValueError("OpenAI API Key is required for embeddings in this stage.")

    async def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for multiple strings (chunks)."""
        if settings.openai_api_key:
            return await self._openai_embeddings.aembed_documents(texts)
        else:
            # Fallback placeholder
            raise ValueError("OpenAI API Key is required for embeddings in this stage.")


# Singleton instance
embedding_service = EmbeddingService()
