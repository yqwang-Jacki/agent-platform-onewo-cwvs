from pydantic_settings import BaseSettings

# CloudBase PostgreSQL 生产数据库 - 硬编码，不受环境变量覆盖
_PG_DATABASE_URL = "postgresql://agent_platform:Workbuddy-test-key1@172.17.0.11:5432/postgres"


class Settings(BaseSettings):
    PROJECT_NAME: str = "Agent发布平台"
    API_V1_STR: str = "/api/v1"

    @property
    def DATABASE_URL(self) -> str:
        """Always use PostgreSQL. Ignore any SQLite env var injected by CloudBase."""
        return _PG_DATABASE_URL

    @property
    def SQLALCHEMY_DATABASE_URI(self) -> str:
        return self.DATABASE_URL

    # JWT
    SECRET_KEY: str = "change-me-in-production-use-openssl-rand-hex-32"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 120
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # CORS
    BACKEND_CORS_ORIGINS: list[str] = ["*"]

    # Share link base URL (H5 chat page)
    SHARE_BASE_URL: str = ""

    # Agent API proxy timeout (seconds)
    AGENT_PROXY_TIMEOUT: int = 60

    model_config = {"case_sensitive": True, "extra": "ignore"}


settings = Settings()
