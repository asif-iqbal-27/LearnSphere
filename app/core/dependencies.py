# app/core/dependencies.py
from qdrant_client import QdrantClient
from app.core.settings import settings

def get_qdrant_client() -> QdrantClient:
    return QdrantClient(url=settings.QDRANT_URL)
