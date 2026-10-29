"""DynamicMCP System Configuration using Pydantic Settings."""

from pathlib import Path
from typing import Optional, Any
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Global configuration settings for DynamicMCP."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    # Nebius Token Factory / Cloud credentials
    nebius_api_key: str = Field(default="mock-key", alias="NEBIUS_API_KEY")
    nebius_project_id: str = Field(default="project_dynamicmcp", alias="NEBIUS_PROJECT_ID")
    nebius_token_factory_url: str = Field(
        default="https://api.studio.nebius.ai/v1", alias="NEBIUS_TOKEN_FACTORY_URL"
    )
    nebius_jobs_api_url: str = Field(
        default="https://api.nebius.ai/v1/jobs", alias="NEBIUS_JOBS_API_URL"
    )

    # Model identifiers
    nano_model: str = Field(
        default="nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B", alias="NEBIUS_NANO_MODEL"
    )
    ultra_model: str = Field(
        default="nvidia/Nemotron-3-Ultra-550b-a55b", alias="NEBIUS_ULTRA_MODEL"
    )

    # Local Storage & Database
    db_path: Path = Field(
        default=Path("~/.dynamicmcp/skills.db").expanduser(), alias="DYNAMICMCP_DB_PATH"
    )
    cache_dir: Path = Field(
        default=Path("~/.dynamicmcp/cache").expanduser(), alias="DYNAMICMCP_CACHE_DIR"
    )
    log_level: str = Field(default="INFO", alias="DYNAMICMCP_LOG_LEVEL")

    # NVIDIA OpenShell & Sandboxing
    openshell_enabled: bool = Field(default=True, alias="OPENSHELL_ENABLED")
    openshell_binary_path: str = Field(
        default="/usr/local/bin/openshell", alias="OPENSHELL_BINARY_PATH"
    )
    nemoclaw_policy_dir: Path = Field(
        default=Path("./policies"), alias="NEMOCLAW_POLICY_DIR"
    )

    # Hermes Agent Integration
    hermes_config_path: Path = Field(
        default=Path("~/.hermes/config.yaml").expanduser(), alias="HERMES_CONFIG_PATH"
    )
    hermes_reload_endpoint: str = Field(
        default="http://127.0.0.1:8765/reload-mcp", alias="HERMES_RELOAD_ENDPOINT"
    )

    # Testing & Offline execution mode
    offline_mode: bool = Field(default=False, alias="DYNAMICMCP_OFFLINE_MODE")

    @field_validator("db_path", "cache_dir", "nemoclaw_policy_dir", "hermes_config_path", mode="before")
    @classmethod
    def expand_paths(cls, v: Any) -> Path:
        if isinstance(v, (str, Path)):
            return Path(v).expanduser().resolve()
        return v

    def ensure_directories(self) -> None:
        """Ensure necessary storage directories exist on disk."""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        (self.cache_dir / "specs").mkdir(parents=True, exist_ok=True)
        (self.cache_dir / "code").mkdir(parents=True, exist_ok=True)
        (self.cache_dir / "policies").mkdir(parents=True, exist_ok=True)
        (self.cache_dir / "logs").mkdir(parents=True, exist_ok=True)
        self.nemoclaw_policy_dir.mkdir(parents=True, exist_ok=True)


# Global singleton instance
settings = Settings()
