import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "8000"))
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "info")
    API_TITLE: str = os.getenv("API_TITLE", "AI-Powered Lead Management & Analysis Service")
    API_VERSION: str = os.getenv("API_VERSION", "1.1.0")

    # AI Configuration
    # Options: "none" (rules only), "gemini", "openai", "ollama"
    AI_PROVIDER: str = os.getenv("AI_PROVIDER", "none").lower()
    
    # API Keys & Endpoints
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")
    
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    OPENAI_MODEL: str = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    
    OLLAMA_BASE_URL: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    OLLAMA_MODEL: str = os.getenv("OLLAMA_MODEL", "llama3.2")
    
    # Reliability Settings
    AI_TIMEOUT_SECONDS: float = float(os.getenv("AI_TIMEOUT_SECONDS", "8.0"))
    AI_MAX_RETRIES: int = int(os.getenv("AI_MAX_RETRIES", "2"))
    AI_RETRY_DELAY_SECONDS: float = float(os.getenv("AI_RETRY_DELAY_SECONDS", "1.0"))

settings = Settings()
