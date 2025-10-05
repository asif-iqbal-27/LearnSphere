from pydantic import BaseModel
from typing import List, Optional


class DocumentInfo(BaseModel):
    class_name: str
    subject: str
    version: str
    collection_name: str
    file_path: str


class ChatMessage(BaseModel):
    role: str   # "user" or "assistant"
    content: str


class ChatRequest(BaseModel):
    query: str
    collection_name: str
    history: Optional[List[ChatMessage]] = []  # 👈 added


class ChatResponse(BaseModel):
    response: str
    sources: List[str]
    images: Optional[List[str]] = []


class DocumentUploadResponse(BaseModel):
    message: str
    collection_name: str
    class_name: str
    subject: str
    version: str


class DocumentListResponse(BaseModel):
    documents: List[DocumentInfo]
