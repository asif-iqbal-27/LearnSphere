import openai
from typing import List, Tuple
from app.core.settings import settings
from app.core.database import qdrant_db
from app.services.embedding_service import embedding_service

API_BASE_URL = "http://localhost:8000"  # Update if your FastAPI runs elsewhere


def normalize_image_path(img: str, collection_name: str) -> str:
    """
    Convert OCR image names to full URLs.
    Assumes all actual images are .png
    """
    img = img.replace("\\", "/")
    base_name = img.split(".")[0]  # e.g., img-9.jpeg -> img-9
    img_filename = f"{base_name}.png"
    return f"{API_BASE_URL}/uploads/{collection_name}/images/{img_filename}"


class ChatService:
    def __init__(self):
        self.client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)

    def retrieve_relevant_chunks(self, query: str, collection_name: str, limit: int = 5) -> List[dict]:
        """Retrieve relevant chunks from vector database"""
        try:
            query_embedding = embedding_service.create_single_embedding(query)
            search_results = qdrant_db.search_vectors(
                collection_name=collection_name,
                query_vector=query_embedding,
                limit=limit
            )

            relevant_chunks = []
            for result in search_results:
                chunk_info = {
                    "text": result.payload.get("text", ""),
                    "images": result.payload.get("images", []),
                    "score": result.score,
                    "source": result.payload.get("source", "")
                }
                relevant_chunks.append(chunk_info)

            return relevant_chunks

        except Exception as e:
            print(f"Error retrieving chunks: {e}")
            return []

    def generate_response(self, query: str, relevant_chunks: List[dict], collection_name: str, history: List[dict]) -> Tuple[str, List[str], List[str]]:
        """Generate response using GPT-4o-mini with retrieved context and chat history"""
        try:
            # Build context from chunks
            context = "\n\n".join([
                f"Context {i+1}: {chunk['text']}"
                for i, chunk in enumerate(relevant_chunks)
            ])

            # Collect and normalize images
            all_images = []
            for chunk in relevant_chunks:
                for img in chunk.get("images", []):
                    all_images.append(normalize_image_path(img, collection_name))
            unique_images = list(set(all_images))

            # Collect sources
            sources = [chunk.get("source", "") for chunk in relevant_chunks]
            unique_sources = list(set(filter(None, sources)))

            # System prompt
            system_prompt = """You are an educational assistant. 
            Always answer based ONLY on the provided context and chat history. 
            If the context/history doesn't contain enough information, say so clearly.
            Be concise, accurate, and helpful in your responses.
            Do not make up information that is not in the context/history."""

            # Build message list
            messages = [{"role": "system", "content": system_prompt}]

            # Add history (last 10 messages only)
            for h in history[-10:]:
                if h["role"] in ["user", "assistant"]:
                    messages.append({"role": h["role"], "content": h["content"]})

            # Add current user query (with retrieved context)
            user_prompt = f"""
            Context:
            {context}

            Question: {query}
            """
            messages.append({"role": "user", "content": user_prompt})

            # Generate response
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=messages,
                temperature=0.1,
                max_tokens=1500
            )

            answer = response.choices[0].message.content

            return answer, unique_sources, unique_images

        except Exception as e:
            print(f"Error generating response: {e}")
            return f"Error generating response: {str(e)}", [], []

    def chat(self, query: str, collection_name: str, history: List[dict] = None) -> dict:
        """Main chat function with optional history"""
        try:
            if not qdrant_db.collection_exists(collection_name):
                return {
                    "response": "The requested document collection does not exist. Please upload the document first.",
                    "sources": [],
                    "images": []
                }

            relevant_chunks = self.retrieve_relevant_chunks(query, collection_name)

            if not relevant_chunks:
                return {
                    "response": "I couldn't find relevant information in the document to answer your question.",
                    "sources": [],
                    "images": []
                }

            response, sources, images = self.generate_response(
                query, relevant_chunks, collection_name, history or []
            )

            return {
                "response": response,
                "sources": sources,
                "images": images
            }

        except Exception as e:
            print(f"Error in chat service: {e}")
            return {
                "response": f"An error occurred while processing your request: {str(e)}",
                "sources": [],
                "images": []
            }


chat_service = ChatService()
