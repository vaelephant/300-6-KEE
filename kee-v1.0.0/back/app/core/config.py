from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Knowledge Evolution Engine"
    database_url: str = "sqlite+pysqlite:///./data/kee.db"
    cors_origins: str = "http://localhost:3030,http://127.0.0.1:3030,http://localhost:3000,http://127.0.0.1:3000"
    upload_dir: str = "./uploads"
    llm_base_url: str = ""
    llm_api_key: str = ""
    llm_model: str = ""
    neo4j_uri: str = ""
    neo4j_user: str = "neo4j"
    neo4j_password: str = ""
    embedding_provider: str = "local"
    embedding_model: str = "BAAI/bge-m3"
    embedding_base_url: str = ""
    embedding_api_key: str = ""
    reranker_model: str = "BAAI/bge-reranker-v2-m3"
    redis_url: str = "redis://localhost:6379/0"
    enable_neo4j_sync: bool = False
    knowledge_decay_days: int = 180
    # MCP plugin: empty base = in-process RuntimeService; set base to call HTTP API
    kee_api_base: str = ""
    kee_api_key: str = ""
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
