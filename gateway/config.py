from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import AnyHttpUrl
from typing import List


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # App
    environment: str = "development"
    log_level: str = "INFO"
    cors_origins: List[str] = ["http://localhost:5173"]
    max_concurrent_sessions: int = 100
    rate_limit_per_minute: int = 60

    # Auth
    secret_key: str
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 1440

    # DB
    database_url: str
    redis_url: str = "redis://localhost:6379/0"

    # LLM
    azure_openai_api_key: str = ""
    azure_openai_endpoint: str = ""
    azure_openai_deployment_name: str = "gpt-4o"
    azure_openai_api_version: str = "2024-08-01-preview"
    anthropic_api_key: str = ""
    google_api_key: str = ""

    # Observability
    langchain_tracing_v2: bool = True
    langchain_api_key: str = ""
    langchain_project: str = "agentos"

    # Search
    tavily_api_key: str = ""

    # Kafka
    kafka_bootstrap_servers: str = "localhost:9092"
    kafka_topic_agent_events: str = "agent-events"
    kafka_topic_eval_results: str = "eval-results"

    # RAG
    chroma_host: str = "localhost"
    chroma_port: int = 8001
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    chunk_size: int = 512
    chunk_overlap: int = 64

    # Code Exec
    code_exec_timeout: int = 30
    code_exec_max_memory_mb: int = 256


@lru_cache
def get_settings() -> Settings:
    return Settings()
