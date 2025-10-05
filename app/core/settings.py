import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

class Settings:
    MISTRAL_API_KEY: str = os.getenv("MISTRAL_API_KEY")
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY")
    QDRANT_URL: str = os.getenv("QDRANT_URL", "http://localhost:6333")
    QDRANT_HOST: str = os.getenv("QDRANT_HOST", "localhost")
    QDRANT_PORT: int = int(os.getenv("QDRANT_PORT", "6333"))
    UPLOAD_DIR: str = os.getenv("UPLOAD_DIR", "./uploads")
    CHUNK_SIZE: int = int(os.getenv("CHUNK_SIZE", "1000"))
    CHUNK_OVERLAP: int = int(os.getenv("CHUNK_OVERLAP", "200"))

    def __init__(self):
        Path(self.UPLOAD_DIR).mkdir(parents=True, exist_ok=True)

settings = Settings()
