import openai
import re
from typing import List, Tuple
from langchain.text_splitter import RecursiveCharacterTextSplitter
from app.core.settings import settings

class EmbeddingService:
    def __init__(self):
        self.client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=settings.CHUNK_SIZE,
            chunk_overlap=settings.CHUNK_OVERLAP,
            length_function=len,
        )
    
    def extract_image_references(self, text: str) -> List[str]:
        """Extract image paths from markdown text"""
        # Pattern to match ![Image](path) format
        image_pattern = r'!\[.*?\]\(([^)]+)\)'
        return re.findall(image_pattern, text)
    
    def split_text_with_images(self, markdown_content: str, image_paths: List[str]) -> List[dict]:
        """Split text into chunks and associate with relevant images"""
        chunks = self.text_splitter.split_text(markdown_content)
        
        chunk_data = []
        for i, chunk in enumerate(chunks):
            # Extract image references from this chunk
            chunk_images = self.extract_image_references(chunk)
            
            # If no images in chunk, check if this chunk is near images in the full content
            if not chunk_images:
                # Simple heuristic: associate images that appear near this chunk
                chunk_start = markdown_content.find(chunk[:50])  # Find chunk position
                
                # Look for images within a reasonable distance (e.g., 500 chars before/after)
                nearby_images = []
                for img_path in image_paths:
                    img_ref = f"![Image]({img_path})"
                    img_pos = markdown_content.find(img_ref)
                    if img_pos != -1 and abs(img_pos - chunk_start) < 1000:
                        nearby_images.append(img_path)
                
                chunk_images = nearby_images
            
            chunk_data.append({
                "text": chunk,
                "images": chunk_images,
                "chunk_id": i
            })
        
        return chunk_data
    
    def create_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Create embeddings for a list of texts"""
        try:
            if not texts:
                raise ValueError("No texts provided for embedding")
            
            # Filter out empty texts
            valid_texts = [text.strip() for text in texts if text.strip()]
            
            if not valid_texts:
                raise ValueError("No valid texts after filtering empty strings")
            
            print(f"Creating embeddings for {len(valid_texts)} texts")
            
            # Create embeddings in batches to avoid API limits
            batch_size = 100
            all_embeddings = []
            
            for i in range(0, len(valid_texts), batch_size):
                batch_texts = valid_texts[i:i + batch_size]
                
                response = self.client.embeddings.create(
                    model="text-embedding-3-small",
                    input=batch_texts
                )
                
                batch_embeddings = [embedding.embedding for embedding in response.data]
                all_embeddings.extend(batch_embeddings)
            
            print(f"Successfully created {len(all_embeddings)} embeddings")
            
            # Validate embedding dimensions
            if all_embeddings:
                embedding_dim = len(all_embeddings[0])
                print(f"Embedding dimension: {embedding_dim}")
                
                # Check if all embeddings have same dimension
                for i, emb in enumerate(all_embeddings):
                    if len(emb) != embedding_dim:
                        raise ValueError(f"Embedding {i} has dimension {len(emb)}, expected {embedding_dim}")
            
            return all_embeddings
            
        except Exception as e:
            print(f"Error creating embeddings: {e}")
            print(f"Text count: {len(texts) if texts else 0}")
            if texts:
                print(f"First text preview: {texts[0][:100]}...")
            raise e
    
    def create_single_embedding(self, text: str) -> List[float]:
        """Create embedding for a single text"""
        return self.create_embeddings([text])[0]

embedding_service = EmbeddingService()