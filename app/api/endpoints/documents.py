import os
import shutil
import json
from pathlib import Path
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from app.schemas.document import DocumentUploadResponse, DocumentListResponse
from app.services.document_service import document_service
from app.core.dependencies import get_qdrant_client
from app.core.settings import settings

router = APIRouter()

# Path to metadata JSON
METADATA_FILE = Path(settings.UPLOAD_DIR) / "documents_metadata.json"
METADATA_FILE.parent.mkdir(exist_ok=True, parents=True)

# --- Helper functions for metadata ---
def load_metadata():
    if METADATA_FILE.exists():
        with open(METADATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

def save_metadata(data):
    with open(METADATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

# --- Filename parser ---
def parse_filename(filename: str) -> tuple:
    """Parse filename to extract class, subject, version"""
    try:
        name_without_ext = filename.replace(".pdf", "")
        parts = name_without_ext.split("_")
        if len(parts) >= 3:
            class_name = parts[0]
            subject = parts[1]
            version = "_".join(parts[2:])
            return class_name, subject, version
        else:
            raise ValueError("Filename format should be: class_subject_version.pdf")
    except Exception as e:
        raise ValueError(f"Invalid filename format: {str(e)}")

# --- Add document endpoint ---
@router.post("/add_document", response_model=DocumentUploadResponse)
async def add_document(file: UploadFile = File(...), qdrant_client=Depends(get_qdrant_client)):
    try:
        if not file.filename.endswith(".pdf"):
            raise HTTPException(status_code=400, detail="Only PDF files are allowed")

        # Parse filename
        try:
            class_name, subject, version = parse_filename(file.filename)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))

        # Check if document exists
        if document_service.document_exists(class_name, subject, version):
            raise HTTPException(
                status_code=400,
                detail="Document with same class, subject, and version already exists",
            )

        # Save uploaded file temporarily
        upload_path = Path("temp_uploads")
        upload_path.mkdir(exist_ok=True)
        file_path = upload_path / file.filename
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        # Process document
        try:
            result = document_service.process_document(
                str(file_path), class_name, subject, version
            )

            # Ensure 'file_path' exists
            if 'file_path' not in result:
                result['file_path'] = str(file_path)

            # Update document_metadata.json
            metadata = load_metadata()
            metadata.append(result)
            save_metadata(metadata)

            # Clean up temp file
            os.remove(file_path)

            return DocumentUploadResponse(**result)

        except Exception as e:
            if file_path.exists():
                os.remove(file_path)
            raise HTTPException(status_code=500, detail=str(e))

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")

# --- Get documents ---
@router.get("/documents", response_model=DocumentListResponse)
async def get_documents(qdrant_client=Depends(get_qdrant_client)):
    try:
        documents = document_service.get_all_documents()
        return DocumentListResponse(documents=documents)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving documents: {str(e)}")

# --- Delete document/collection ---
@router.delete("/{collection_name}")
async def delete_collection(collection_name: str, qdrant_client=Depends(get_qdrant_client)):
    try:
        # Delete collection from Qdrant
        qdrant_client.delete_collection(collection_name=collection_name)

        # Remove uploaded markdown/images
        collection_dir = os.path.join(settings.UPLOAD_DIR, collection_name)
        if os.path.exists(collection_dir):
            shutil.rmtree(collection_dir)

        # Remove from metadata JSON
        metadata = load_metadata()
        metadata = [d for d in metadata if d["collection_name"] != collection_name]
        save_metadata(metadata)

        return {"message": f"Collection '{collection_name}' deleted successfully!"}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Delete failed: {str(e)}")

# --- Debug Qdrant collections ---
@router.get("/debug/qdrant")
async def debug_qdrant(qdrant_client=Depends(get_qdrant_client)):
    collections_response = qdrant_client.get_collections()
    collection_names = [col.name for col in collections_response.collections]
    return {
        "qdrant_url": settings.QDRANT_URL,
        "collections_count": len(collection_names),
        "collections": collection_names,
    }
