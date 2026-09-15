"""应用配置中心（pydantic-settings）。"""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "JuDouProject"
    debug: bool = False
    api_prefix: str = "/api/v1"

    database_url: str = "postgresql+asyncpg://judou:judou@localhost:5432/judou"
    redis_url: str = "redis://localhost:6379/0"

    jwt_secret: str = "dev-secret-change-me-not-for-production-0123456789"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 7 * 24 * 60

    wechat_appid: str = ""
    wechat_secret: str = ""
    amap_key: str = ""

    # 管理端密钥（X-Admin-Key 请求头）；未配置时管理 API 一律拒绝
    admin_key: str = ""

    # 上传文件根目录（容器内路径；部署时挂载卷持久化）
    uploads_dir: str = "uploads"

    @property
    def wechat_enabled(self) -> bool:
        """微信登录可用性：appid + secret 均已配置。"""
        return bool(self.wechat_appid and self.wechat_secret)


@lru_cache
def get_settings() -> Settings:
    return Settings()
