"""Application configuration from environment variables."""
from pydantic_settings import BaseSettings
from typing import List, Literal


class Settings(BaseSettings):
    """Application settings loaded from environment."""

    # Neo4j
    neo4j_uri: str = "bolt://localhost:7687"
    neo4j_user: str = "neo4j"
    neo4j_password: str = "recommend_neo4j_2024"
    neo4j_database: str = "neo4j"

    # Server
    backend_host: str = "0.0.0.0"
    backend_port: int = 8000

    # CORS
    cors_origins: str = "http://localhost:3000,http://localhost:5173"

    # NLP / Query Parser
    # Options: "rule" (default, no API key needed) | "gemini" | "openai"
    query_parser: Literal["rule", "gemini", "openai"] = "rule"
    gemini_api_key: str = ""
    openai_api_key: str = ""
    gemini_model: str = "gemini-1.5-flash"  # fast + cheap; use gemini-1.5-pro for accuracy

    @property
    def cors_origins_list(self) -> List[str]:
        return [origin.strip() for origin in self.cors_origins.split(",")]

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()
