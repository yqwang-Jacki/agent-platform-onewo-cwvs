import os
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    PROJECT_NAME: str = "Agent发布平台"
    API_V1_STR: str = "/api/v1"

    # 优先读环境变量 DATABASE_URL；如果未设或指向不可达的 PG 内网地址，回退到 SQLite
    @property
    def DATABASE_URL(self) -> str:
        env_url = os.environ.get("DATABASE_URL", "")
        # 如果环境变量指向 PG 内网地址但容器没 VPC，会超时卡死
        # 检测到内网 PG 地址就回退 SQLite，保证服务可用
        if "172.17.0.11" in env_url:
            return "sqlite:////app/data/agent_platform.db"
        if env_url:
            return env_url
        return "sqlite:////app/data/agent_platform.db"

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
