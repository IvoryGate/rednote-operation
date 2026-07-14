from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel
from pydantic_settings import BaseSettings, SettingsConfigDict


class AppConfig(BaseModel):
    name: str = "RedNote Operation"
    version: str = "0.1.0"
    debug: bool = True
    log_level: str = "INFO"


class DatabaseConfig(BaseModel):
    url: str = "sqlite:///database/rednote.db"
    echo: bool = False


class BrowserConfig(BaseModel):
    headless: bool = False
    slow_mo: int = 100
    user_data_dir: str = "./.browser-data"
    timeout: int = 30000


class CrawlConfig(BaseModel):
    """Anti-bot pacing for crawl scripts (no proxy/IP pool)."""

    min_interval_seconds: float = 2.0
    max_interval_seconds: float = 60.0
    backoff_factor: float = 2.0
    jitter_seconds: float = 0.5


class PathsConfig(BaseModel):
    data: str = "./data"
    logs: str = "./logs"
    exports: str = "./exports"


class KnowledgeConfig(BaseModel):
    base_path: str = "./knowledge"
    auto_index: bool = True


class ScheduleConfig(BaseModel):
    timezone: str = "Asia/Shanghai"
    default_interval_hours: int = 6


class Config(BaseSettings):
    model_config = SettingsConfigDict(extra="ignore")

    app: AppConfig = AppConfig()
    database: DatabaseConfig = DatabaseConfig()
    browser: BrowserConfig = BrowserConfig()
    crawl: CrawlConfig = CrawlConfig()
    paths: PathsConfig = PathsConfig()
    knowledge: KnowledgeConfig = KnowledgeConfig()
    schedule: ScheduleConfig = ScheduleConfig()

    @classmethod
    def from_yaml(cls, path: str | Path = "config/config.yaml") -> "Config":
        config_path = Path(path)
        if not config_path.exists():
            return cls()
        with open(config_path) as f:
            data: dict[str, Any] = yaml.safe_load(f) or {}
        return cls.model_validate(data, strict=False)


def load_config(path: str | Path = "config/config.yaml") -> Config:
    """Load config from YAML, falling back to defaults when the file is absent."""
    return Config.from_yaml(path)


config = load_config()
