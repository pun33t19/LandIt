from pydantic_settings import BaseSettings
from functools import lru_cache

# base settings is inbuilt pydantic class that helps in fetching properties from .env files
class Settings(BaseSettings):
    # LLM
    openai_api_key: str = ""
    anthropic_api_key: str = ""
    llm_model: str = "gpt-4o"
    embedding_model: str = "text-embedding-3-small"

    # Job Search
    jsearch_api_key: str = ""

    # Supabase
    supabase_url: str = ""
    supabase_anon_key: str = ""
    supabase_service_role_key: str = ""

    # Pinecone
    pinecone_api_key: str = ""
    pinecone_index_name: str = "resume-jobs"

    # Redis
    redis_url: str = "redis://localhost:6379"

    # App
    app_env: str = "development"
    allowed_origins: str = "http://localhost:3000"

    class Config:
        env_file = ".env"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    return Settings()
