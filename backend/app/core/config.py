from functools import lru_cache
from typing import List, Optional, Union
from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Centralized application settings loaded from environment and .env file."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    APP_NAME: str = Field(default="Tender Intelligence Platform API")
    APP_ENV: str = Field(default="development")  # development, staging, production
    DEBUG: bool = Field(default=False)

    # Database
    DATABASE_URL: str = Field(
        default="postgresql+asyncpg://tender_app:tender_dev_secret_2026@127.0.0.1:5433/tender_platform",
        description="Async PostgreSQL connection URI",
    )

    # JWT Authentication
    JWT_SECRET_KEY: str = Field(
        ...,
        description="High-entropy secret key for JWT signing",
    )
    JWT_ALGORITHM: str = Field(default="HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=60)
    REFRESH_TOKEN_EXPIRE_DAYS: int = Field(default=7)

    # CORS
    FRONTEND_ORIGINS: Union[str, List[str]] = Field(
        default=["http://localhost:5173", "http://127.0.0.1:5173"]
    )

    # Local Protected File Storage
    UPLOAD_DIR: str = Field(default="./uploads")
    TENDER_DOWNLOAD_DIR: str = Field(
        default="../downloads",
        description="Local directory for saving downloaded public tender documents and attachments",
    )
    MAX_UPLOAD_SIZE_MB: int = Field(default=25)

    # Document Processing & OCR
    TESSERACT_CMD: Optional[str] = Field(
        default=None,
        description="Optional absolute path to tesseract binary (e.g. C:\\Program Files\\Tesseract-OCR\\tesseract.exe on Windows)",
    )

    # ChromaDB & Embeddings
    CHROMA_PERSIST_DIRECTORY: str = Field(default="./data/chroma")
    CHROMA_COLLECTION_NAME: str = Field(default="tender_documents")
    CHROMA_COMPANY_COLLECTION_NAME: str = Field(default="company_documents")
    EMBEDDING_PROVIDER: str = Field(
        default="default",
        description="Embedding model provider: 'default' (ChromaDB onnx mini-lm), 'mock', or 'huggingface'",
    )
    CHUNK_SIZE: int = Field(default=1000)
    CHUNK_OVERLAP: int = Field(default=200)

    # Phase 4 - Gemini AI & Compliance Orchestration
    GEMINI_API_KEY: Optional[str] = Field(default=None, description="Google Gemini API Key")
    GEMINI_MODEL: str = Field(default="gemini-2.5-flash", description="Gemini model identifier")
    GEMINI_TIMEOUT_SECONDS: int = Field(default=30)
    GEMINI_MAX_RETRIES: int = Field(default=3)
    RULE_ENGINE_VERSION: str = Field(default="1.0.0")
    HYBRID_SEARCH_SEMANTIC_WEIGHT: float = Field(default=0.6)
    HYBRID_SEARCH_LEXICAL_WEIGHT: float = Field(default=0.4)

    # Phase 9 & 10 - Proactive Deadline Alert Scheduler
    DEADLINE_ALERT_ENABLED: bool = Field(
        default=True,
        description="Enable automatic periodic background deadline alert evaluation",
    )
    DEADLINE_ALERT_INTERVAL_SECONDS: int = Field(
        default=300,
        description="Interval in seconds between automated deadline scan ticks",
    )

    # Phase 11 - Automated Government Tender Ingestion
    INGESTION_ENABLED: bool = Field(
        default=True,
        description="Enable automated background government tender ingestion",
    )
    INGESTION_INTERVAL_SECONDS: int = Field(
        default=3600,
        description="Interval in seconds between automated tender ingestion cycles",
    )
    INGESTION_BATCH_SIZE: int = Field(
        default=50,
        description="Max tenders to fetch per portal per ingestion tick",
    )
    GEM_API_KEY: Optional[str] = Field(
        default=None,
        description="Optional GeM procurement developer partner API key",
    )
    CPPP_API_KEY: Optional[str] = Field(
        default=None,
        description="Optional CPPP enterprise integration credentials",
    )

    # Phase 11 - TenderKart Client API Ingestion (Third-Party Provider)
    TENDERKART_ENABLED: bool = Field(
        default=True,
        description="Enable TenderKart third-party tender data ingestion connector",
    )
    TENDERKART_API_KEY: Optional[str] = Field(
        default=None,
        description="TenderKart Client API Key (X-API-Key or Authorization: Bearer)",
    )
    TENDERKART_BASE_URL: str = Field(
        default="https://tenderkart.in/api/v1/client",
        description="TenderKart Client API base URL",
    )
    TENDERKART_DEFAULT_FILTER_ID: Optional[str] = Field(
        default=None,
        description="Default saved filter ID for targeted ingestion; if None, uses the first active filter from /filters",
    )
    TENDERKART_FULL_SEARCH_ENABLED: bool = Field(
        default=False,
        description="Enable optional full corpus search if supported",
    )
    TENDERKART_DOWNLOAD_DOCS: bool = Field(
        default=False,
        description="Enable automatic document attachment download via /documents/{id}",
    )

    # Phase 11 - Apify Actor Ingestion (foxlabs/india-government-tenders)
    APIFY_ENABLED: bool = Field(
        default=True,
        description="Enable Apify Actor government tender ingestion connector",
    )
    APIFY_API_TOKEN: Optional[str] = Field(
        default=None,
        description="Apify API Token for running actors and accessing datasets",
    )
    APIFY_ACTOR_ID: str = Field(
        default="foxlabs~india-government-tenders",
        description="Apify actor ID or username/actor-name",
    )
    APIFY_MAX_RESULTS: int = Field(
        default=5,
        description="Default max tender results to fetch per run (capped for cost safety)",
    )
    APIFY_MODE: str = Field(
        default="list",
        description="Actor extraction mode: 'list' (fast summary) or 'list_detail'",
    )
    APIFY_DATE_PRESET: str = Field(
        default="last_7_days",
        description="Date range preset for tender discovery",
    )

    # Document Retrieval & SSRF Protection
    MAX_DOCUMENT_DOWNLOAD_BYTES: int = Field(
        default=50 * 1024 * 1024,
        description="Maximum allowed tender PDF download size in bytes (50 MB)",
    )
    ALLOWED_DOCUMENT_DOMAINS: List[str] = Field(
        default=["gov.in", "nic.in", "tenderkart.in", "apify.com"],
        description="Allowed official domain suffixes for secure document retrieval",
    )

    @field_validator("FRONTEND_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        return v

    @model_validator(mode="after")
    def validate_production_settings(self) -> "Settings":
        """Ensure production environments do not use default or insecure values."""
        if self.APP_ENV == "production":
            if self.DEBUG:
                raise ValueError("DEBUG mode must be False in production environment")
            if len(self.JWT_SECRET_KEY) < 32:
                raise ValueError("JWT_SECRET_KEY must be at least 32 characters long in production")
            if "tender_dev_secret" in self.DATABASE_URL or "dev_" in self.JWT_SECRET_KEY.lower():
                raise ValueError("Insecure development credentials detected in production configuration")
        return self


@lru_cache()
def get_settings() -> Settings:
    """Cached factory function returning application settings."""
    return Settings()
