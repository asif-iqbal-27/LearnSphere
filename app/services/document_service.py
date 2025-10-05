import os
import json
from pathlib import Path
from typing import List
from app.core.settings import settings
from app.core.database import qdrant_db
from app.services.ocr_service import ocr_service
from app.services.embedding_service import embedding_service
from app.schemas.document import DocumentInfo

class DocumentService:
    def __init__(self):
        self.upload_dir = Path(settings.UPLOAD_DIR)
        self.upload_dir.mkdir(parents=True, exist_ok=True)
        self.metadata_file = self.upload_dir / "documents_metadata.json"
    
    def load_metadata(self) -> List[dict]:
        """Load document metadata from file"""
        if self.metadata_file.exists():
            with open(self.metadata_file, 'r') as f:
                return json.load(f)
        return []
    
    def save_metadata(self, metadata: List[dict]):
        """Save document metadata to file"""
        with open(self.metadata_file, 'w') as f:
            json.dump(metadata, f, indent=2)
    
    def document_exists(self, class_name: str, subject: str, version: str) -> bool:
        """Check if document already exists"""
        metadata = self.load_metadata()
        for doc in metadata:
            if (doc["class_name"] == class_name and 
                doc["subject"] == subject and 
                doc["version"] == version):
                return True
        return False
    
    def generate_collection_name(self, class_name: str, subject: str, version: str) -> str:
        """Generate unique collection name"""
        return f"{class_name}_{subject}_{version}".lower().replace(" ", "_")
    
    def process_document(self, file_path: str, class_name: str, subject: str, version: str) -> dict:
        """Process uploaded document"""
        try:
            # Check if document already exists
            if self.document_exists(class_name, subject, version):
                raise ValueError("Document with same class, subject, and version already exists")
            
            # Generate collection name
            collection_name = self.generate_collection_name(class_name, subject, version)
            
            # Create output folder
            output_folder = self.upload_dir / collection_name
            output_folder.mkdir(parents=True, exist_ok=True)
            
            # Process PDF with OCR
            markdown_content, image_paths, markdown_path = ocr_service.process_pdf(
                file_path, output_folder
            )
            
            # Split text into chunks with associated images
            chunk_data = embedding_service.split_text_with_images(markdown_content, image_paths)
            
            # Create embeddings
            chunk_texts = [chunk["text"] for chunk in chunk_data]
            embeddings = embedding_service.create_embeddings(chunk_texts)
            
            # Create Qdrant collection
            qdrant_db.create_collection(collection_name)
            
            # Prepare data for vector storage
            vectors = embeddings
            payloads = []
            ids = []
            
            for i, (chunk, embedding) in enumerate(zip(chunk_data, embeddings)):
                payload = {
                    "text": chunk["text"],
                    "images": chunk["images"],
                    "source": f"{class_name}_{subject}_{version}",
                    "chunk_id": chunk["chunk_id"],
                    "page_info": f"Chunk {i+1}"
                }
                payloads.append(payload)
                ids.append(i)
            
            # Insert vectors into Qdrant
            success = qdrant_db.insert_vectors(collection_name, vectors, payloads, ids)
            
            if not success:
                raise Exception("Failed to insert vectors into database")
            
            # Save document metadata
            doc_info = {
                "class_name": class_name,
                "subject": subject,
                "version": version,
                "collection_name": collection_name,
                "file_path": file_path,
                "markdown_path": markdown_path,
                "image_paths": image_paths,
                "chunks_count": len(chunk_data)
            }
            
            metadata = self.load_metadata()
            metadata.append(doc_info)
            self.save_metadata(metadata)
            
            return {
                "message": "Document processed successfully",
                "collection_name": collection_name,
                "class_name": class_name,
                "subject": subject,
                "version": version
            }
            
        except Exception as e:
            print(f"Error processing document: {e}")
            raise e
    
    def get_all_documents(self) -> List[DocumentInfo]:
        """Get all processed documents"""
        try:
            metadata = self.load_metadata()
            documents = []
            
            for doc in metadata:
                doc_info = DocumentInfo(
                    class_name=doc["class_name"],
                    subject=doc["subject"],
                    version=doc["version"],
                    collection_name=doc["collection_name"],
                    file_path=doc["file_path"]
                )
                documents.append(doc_info)
            
            return documents
            
        except Exception as e:
            print(f"Error getting documents: {e}")
            return []
    
    def delete_document(self, collection_name: str) -> bool:
        """Delete document and its data"""
        try:
            # Remove from metadata
            metadata = self.load_metadata()
            metadata = [doc for doc in metadata if doc["collection_name"] != collection_name]
            self.save_metadata(metadata)
            
            # Note: Qdrant collection deletion would be added here if needed
            # self.qdrant_db.delete_collection(collection_name)
            
            return True
            
        except Exception as e:
            print(f"Error deleting document: {e}")
            return False

document_service = DocumentService()