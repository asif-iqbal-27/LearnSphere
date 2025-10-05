from fastapi import APIRouter, HTTPException, Depends
from app.schemas.document import ChatRequest, ChatResponse
from app.services.chat_service import chat_service
from app.core.dependencies import get_qdrant_client

router = APIRouter()

@router.post("/chat", response_model=ChatResponse)
async def chat_with_document(
    request: ChatRequest,
    qdrant_client=Depends(get_qdrant_client)
):
    """
    Chat with a document using RAG.
    Accepts query, collection_name, and optional history (last 5–10 messages).
    Returns assistant response with sources and images if available.
    """
    try:
        # Validate request
        if not request.query.strip():
            raise HTTPException(status_code=400, detail="Query cannot be empty")
        
        if not request.collection_name.strip():
            raise HTTPException(status_code=400, detail="Collection name cannot be empty")
        
        # Pass history to chat service (default: empty list)
        result = chat_service.chat(
            query=request.query,
            collection_name=request.collection_name,
            history=request.history or []
        )
        
        return ChatResponse(
            response=result["response"],
            sources=result["sources"],
            images=result.get("images", [])
        )
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Chat error: {str(e)}")


@router.get("/collections")
async def get_collections(qdrant_client=Depends(get_qdrant_client)):
    """Get all available collections for chatting"""
    try:
        collections = qdrant_client.get_collections()
        collection_names = [col.name for col in collections]
        return {"collections": collection_names}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting collections: {str(e)}")
