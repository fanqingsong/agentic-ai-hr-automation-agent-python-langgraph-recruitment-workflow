"""
Configuration Management with Multi-LLM Support
"""

import os
from pathlib import Path
from dotenv import load_dotenv
from typing import Optional

# Load environment variables
load_dotenv()


class Config:
    """Application configuration with multi-LLM provider support"""

    # ========================================================================
    # LLM CONFIGURATION
    # ========================================================================

    # LLM Provider (openai, azure, anthropic, gemini, ollama)
    LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "openai").lower()

    # OpenAI Configuration
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    OPENAI_MODEL: str = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

    # Azure OpenAI Configuration
    AZURE_OPENAI_API_KEY: str = os.getenv("AZURE_OPENAI_API_KEY", "")
    AZURE_OPENAI_ENDPOINT: str = os.getenv("AZURE_OPENAI_ENDPOINT", "")
    AZURE_OPENAI_DEPLOYMENT: str = os.getenv("AZURE_OPENAI_DEPLOYMENT", "")
    AZURE_OPENAI_MODEL: str = os.getenv("AZURE_OPENAI_MODEL", "gpt-4o-mini")
    AZURE_OPENAI_API_VERSION: str = os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-15-preview")

    # Anthropic Configuration
    ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY", "")
    ANTHROPIC_MODEL: str = os.getenv("ANTHROPIC_MODEL", "claude-3-5-sonnet-20241022")

    # Google Gemini Configuration
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY", "")
    GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-2.5-pro")

    # Ollama Configuration (Local models)
    OLLAMA_MODEL: str = os.getenv("OLLAMA_MODEL", "qwen3:8b")
    OLLAMA_BASE_URL: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")

    # LLM Temperature Settings
    EXTRACTION_TEMP: float = float(os.getenv("EXTRACTION_TEMP", "0.2"))
    SUMMARY_TEMP: float = float(os.getenv("SUMMARY_TEMP", "0.5"))
    EVALUATION_TEMP: float = float(os.getenv("EVALUATION_TEMP", "0.4"))


    # LlamaCloud
    LLAMA_CLOUD_API_KEY: str = os.getenv("LLAMA_CLOUD_API_KEY", "")

    # ========================================================================
    # GOOGLE CONFIGURATION
    # ========================================================================
    # Cleaner(Modern) — pathlib(Recommended)
    BASE_DIR = Path(__file__).resolve().parent.parent
    # ========================================================================
    # MINIO CONFIGURATION (对象存储)
    # ========================================================================

    # MinIO Configuration
    MINIO_ENDPOINT: str = os.getenv("MINIO_ENDPOINT", "localhost:9000")
    MINIO_ACCESS_KEY: str = os.getenv("MINIO_ACCESS_KEY", "minioadmin")
    MINIO_SECRET_KEY: str = os.getenv("MINIO_SECRET_KEY", "minioadmin123")
    MINIO_BUCKET: str = os.getenv("MINIO_BUCKET", "cv-uploads")
    MINIO_SECURE: bool = os.getenv("MINIO_SECURE", "false").lower() == "true"


    # ========================================================================
    # POSTGRESQL CONFIGURATION (用户认证数据库)
    # ========================================================================

    POSTGRES_SERVER: str = os.getenv("POSTGRES_SERVER", "localhost:5432")
    POSTGRES_USER: str = os.getenv("POSTGRES_USER", "hr_user")
    POSTGRES_PASSWORD: str = os.getenv("POSTGRES_PASSWORD", "hr_pass")
    POSTGRES_DB: str = os.getenv("POSTGRES_DB", "hr_users")

    @property
    def DATABASE_URL(self) -> str:
        """Generate SQLAlchemy database URL"""
        return f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_SERVER}/{self.POSTGRES_DB}"


    # ========================================================================
    # SECURITY CONFIGURATION (JWT 认证)
    # ========================================================================

    SECRET_KEY: str = os.getenv("SECRET_KEY", "your-secret-key-change-in-production")
    ALGORITHM: str = os.getenv("ALGORITHM", "HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))


    # ========================================================================
    # FASTAPI CONFIGURATION
    # ========================================================================

    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "8000"))
    RELOAD: bool = os.getenv("RELOAD", "false").lower() == "true"
    DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"
    WORKERS: int = int(os.getenv("WORKERS", "4"))

    # ========================================================================
    # HELPER METHODS
    # ========================================================================

    @classmethod
    def get_llm_api_key(cls) -> Optional[str]:
        """
        Get API key for current LLM provider

        Returns:
            API key string or None
        """
        provider = cls.LLM_PROVIDER.lower()

        if provider == "openai":
            return cls.OPENAI_API_KEY
        elif provider == "azure":
            return cls.AZURE_OPENAI_API_KEY
        elif provider == "anthropic":
            return cls.ANTHROPIC_API_KEY
        elif provider == "gemini":
            return cls.GEMINI_API_KEY
        elif provider in ["ollama"]:
            return None  # No API key needed
        else:
            return None

    @classmethod
    def get_llm_model(cls) -> str:
        """
        Get model name for current LLM provider

        Returns:
            Model name string
        """
        provider = cls.LLM_PROVIDER.lower()

        if provider == "openai":
            return cls.OPENAI_MODEL
        elif provider == "azure":
            return cls.AZURE_OPENAI_MODEL
        elif provider == "anthropic":
            return cls.ANTHROPIC_MODEL
        elif provider == "gemini":
            return cls.GEMINI_MODEL
        elif provider == "ollama":
            return cls.OLLAMA_MODEL
        else:
            return ""

    @classmethod
    def validate(cls) -> bool:
        """Validate required configuration"""
        required_fields = []

        # Add provider-specific validation
        if cls.LLM_PROVIDER == "openai":
            required_fields.append(("OPENAI_API_KEY", cls.OPENAI_API_KEY))
        elif cls.LLM_PROVIDER == "azure":
            required_fields.append(("AZURE_OPENAI_API_KEY", cls.AZURE_OPENAI_API_KEY))
            required_fields.append(("AZURE_OPENAI_ENDPOINT", cls.AZURE_OPENAI_ENDPOINT))
            required_fields.append(("AZURE_OPENAI_DEPLOYMENT", cls.AZURE_OPENAI_DEPLOYMENT))
        elif cls.LLM_PROVIDER == "anthropic":
            required_fields.append(("ANTHROPIC_API_KEY", cls.ANTHROPIC_API_KEY))
        elif cls.LLM_PROVIDER == "gemini":
            required_fields.append(("GEMINI_API_KEY", cls.GEMINI_API_KEY))

        # Google services are now optional - only validate if credentials exist
        if os.path.exists(cls.GOOGLE_CREDENTIALS_PATH):
            if not cls.GOOGLE_SHEET_ID:
                import warnings
                warnings.warn("GOOGLE_SHEET_ID not set. Results will not be saved to Sheets.")
        else:
            import warnings
            warnings.warn(f"Google credentials not found at {cls.GOOGLE_CREDENTIALS_PATH}. Google Drive and Sheets integration disabled.")

        missing = [name for name, value in required_fields if not value]

        if missing:
            raise ValueError(f"Missing required configuration: {', '.join(missing)}")

        return True

    @classmethod
    def get_provider_info(cls) -> dict:
        """Get current LLM provider information"""
        return {
            "provider": cls.LLM_PROVIDER,
            "model": cls.get_llm_model(),
            "has_api_key": bool(cls.get_llm_api_key()),
        }


# Validate configuration on import (with warning instead of error)
try:
    Config.validate()
    print(f"✅ Configuration validated - Using {Config.LLM_PROVIDER} with {Config.get_llm_model()}")
except ValueError as e:
    import warnings
    warnings.warn(f"Configuration validation failed: {e}")