"""
Configuration settings for the Knowledge Base Chatbot
"""
import os
from pathlib import Path

# Base directory
BASE_DIR = Path(__file__).parent.absolute()

# Database
DATABASE_PATH = BASE_DIR / "data" / "chatbot.db"

# File uploads
UPLOAD_FOLDER = BASE_DIR / "uploads"
ALLOWED_EXTENSIONS = {'pdf', 'docx', 'doc', 'csv', 'txt', 'xlsx', 'xls'}
MAX_CONTENT_LENGTH = 50 * 1024 * 1024  # 50 MB max file size

# Vector store
VECTOR_STORE_PATH = BASE_DIR / "data" / "vector_store"

# Ollama settings
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
DEFAULT_MODEL = os.getenv("DEFAULT_MODEL", "llama3.2:1b")

# Model default parameters
DEFAULT_MODEL_PARAMS = {
    "temperature": 0.7,
    "context_length": 4096,
    "top_p": 0.9,
    "top_k": 40,
}

# Embeddings model (for sentence-transformers)
EMBEDDING_MODEL = "all-MiniLM-L6-v2"

# Chunk settings for document processing
CHUNK_SIZE = 500  # tokens
CHUNK_OVERLAP = 50  # tokens

# Search settings
SIMILARITY_THRESHOLD = 0.25  # Balanced threshold for finding relevant content
TOP_K_RESULTS = 3  # Reduced to top 3 for higher precision and specificity

# Admin credentials (change in production!)
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "admin123")

# Flask secret key
SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-change-in-production")

# API settings
API_KEY_LENGTH = 32
RATE_LIMIT_PER_MINUTE = 60

# Create necessary directories
def init_directories():
    """Create necessary directories if they don't exist"""
    directories = [
        BASE_DIR / "data",
        UPLOAD_FOLDER,
        VECTOR_STORE_PATH,
    ]
    for directory in directories:
        directory.mkdir(parents=True, exist_ok=True)
