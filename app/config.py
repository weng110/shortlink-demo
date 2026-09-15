from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """全局配置，可通过环境变量 / .env 覆盖。"""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "ShortLink Demo"
    version: str = "1.0.0"

    # 数据库 / 缓存
    database_url: str = "mysql+pymysql://root:root@localhost:3306/shortlink?charset=utf8mb4"
    redis_url: str = "redis://localhost:6379/0"

    # 短链缓存 TTL（秒）
    cache_ttl: int = 86400

    # 限流：每个 IP 每分钟最多请求数
    rate_limit_per_min: int = 60

    # 点击计数落库定时任务（秒）
    sync_interval: float = 10.0
    sync_task_enabled: bool = True


settings = Settings()
