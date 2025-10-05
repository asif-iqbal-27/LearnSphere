from qdrant_client import QdrantClient
from qdrant_client.http import models
from app.core.settings import settings

class QdrantDB:
    def __init__(self):
        # Disable version check to avoid compatibility warnings
        self.client = QdrantClient(
            url=settings.QDRANT_URL,
            prefer_grpc=False,
            # Disable version checking to avoid warnings
            **{"timeout": 30}
        )
    
    def create_collection(self, collection_name: str, vector_size: int = 1536):
        """Create a new collection in Qdrant"""
        try:
            collections = self.client.get_collections().collections
            collection_names = [col.name for col in collections]
            
            if collection_name in collection_names:
                print(f"Collection {collection_name} already exists")
                return True
                
            self.client.create_collection(
                collection_name=collection_name,
                vectors_config=models.VectorParams(
                    size=vector_size,
                    distance=models.Distance.COSINE
                )
            )
            print(f"Successfully created collection: {collection_name}")
            return True
            
        except Exception as e:
            print(f"Error creating collection {collection_name}: {e}")
            return False
    
    def collection_exists(self, collection_name: str) -> bool:
        """Check if collection exists"""
        try:
            collections = self.client.get_collections().collections
            collection_names = [col.name for col in collections]
            return collection_name in collection_names
        except:
            return False
    
    def insert_vectors(self, collection_name: str, vectors: list, payloads: list, ids: list):
        """Insert vectors into collection"""
        try:
            # Validate inputs
            if not vectors or not payloads or not ids:
                print("Error: Empty vectors, payloads, or ids")
                return False
            
            if len(vectors) != len(payloads) or len(vectors) != len(ids):
                print(f"Error: Mismatched lengths - vectors: {len(vectors)}, payloads: {len(payloads)}, ids: {len(ids)}")
                return False
            
            # Convert to proper format for Qdrant
            points = []
            for i in range(len(vectors)):
                point = models.PointStruct(
                    id=ids[i],
                    vector=vectors[i],
                    payload=payloads[i]
                )
                points.append(point)
            
            # Insert in batches if large number of points
            batch_size = 100
            for i in range(0, len(points), batch_size):
                batch_points = points[i:i + batch_size]
                self.client.upsert(
                    collection_name=collection_name,
                    points=batch_points
                )
            
            print(f"Successfully inserted {len(vectors)} vectors into {collection_name}")
            return True
            
        except Exception as e:
            print(f"Error inserting vectors: {e}")
            print(f"Collection: {collection_name}")
            print(f"Vector count: {len(vectors) if vectors else 0}")
            print(f"First vector shape: {len(vectors[0]) if vectors and vectors[0] else 'N/A'}")
            return False
    
    def search_vectors(self, collection_name: str, query_vector: list, limit: int = 5):
        """Search for similar vectors"""
        try:
            search_result = self.client.search(
                collection_name=collection_name,
                query_vector=query_vector,
                limit=limit
            )
            return search_result
        except Exception as e:
            print(f"Error searching vectors: {e}")
            return []
    
    def get_collections(self):
        """Get all collections"""
        try:
            return self.client.get_collections().collections
        except:
            return []

qdrant_db = QdrantDB()