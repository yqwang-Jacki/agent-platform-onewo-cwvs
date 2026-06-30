from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    PROJECT_NAME: str = "Agent发布平台"
    API_V1_STR: str = "/api/v1"

    # Database - CloudBase PostgreSQL（生产环境）
    # 格式: postgresql://{user}:{password}@{host}:5432/{dbname}
    DATABASE_URL: str = "postgresql://postgres:CHANGE_ME@postgres-8ymmqqw6.postgres.ap-shanghai.tencentcdb.com:5432/postgres"
    POSTGRES_SERVER: str = "localhost"
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "postgres"
    POSTGRES_DB: str = "agent_platform"

    @property
    def SQLALCHEMY_DATABASE_URI(self) -> str:
        if self.DATABASE_URL:
            return self.DATABASE_URL
        return (
            f"postgresql://"
            f"{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_SERVER}:5432/{self.POSTGRES_DB}"
        )

    # JWT
    SECRET_KEY: str = "change-me-in-production-use-openssl-rand-hex-32"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 120   # 2h
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # CORS
    BACKEND_CORS_ORIGINS: list[str] = ["*"]

    # Share link base URL (H5 chat page)
    SHARE_BASE_URL: str = ""

    # Agent API proxy timeout (seconds)
    AGENT_PROXY_TIMEOUT: int = 60

    model_config = {"env_file": ".env", "case_sensitive": True, "extra": "ignore"}


settings = Settings()
