"""Configuration management for PLA Agent SDK."""
from typing import Optional, Any
from pydantic import Field, model_validator
from pydantic_settings import BaseSettings
from urllib.parse import urlparse


class Config(BaseSettings):
    """Application configuration using Pydantic BaseSettings."""

    # Anthropic API
    ANTHROPIC_API_KEY: str = Field(..., description="Anthropic API key (required)")

    # Database configuration
    DATABASE_URL: Optional[str] = Field(None, description="PostgreSQL connection URL")
    DB_HOST: str = Field("localhost", description="Database host")
    DB_NAME: str = Field("pla_leadership", description="Database name")
    DB_USER: Optional[str] = Field(None, description="Database user")
    DB_PASSWORD: Optional[str] = Field(None, description="Database password")
    DB_PORT: int = Field(5432, description="Database port")

    # Agent configuration
    MAX_ITERATIONS: int = Field(10, description="Maximum agentic loop iterations")
    MODEL_NAME: str = Field("claude-sonnet-4-5-20250929", description="Claude model to use")
    LOG_LEVEL: str = Field("INFO", description="Logging level")

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": True,
    }

    @model_validator(mode='before')
    @classmethod
    def parse_database_url(cls, data: Any) -> Any:
        """Parse DATABASE_URL and populate DB fields if provided."""
        if isinstance(data, dict):
            database_url = data.get('DATABASE_URL')
            if database_url:
                parsed = urlparse(database_url)
                # Only set fields if they're not already explicitly provided
                if parsed.hostname and not data.get('DB_HOST'):
                    data['DB_HOST'] = parsed.hostname
                if parsed.path and not data.get('DB_NAME'):
                    data['DB_NAME'] = parsed.path.lstrip('/')
                if parsed.username and not data.get('DB_USER'):
                    data['DB_USER'] = parsed.username
                if parsed.password and not data.get('DB_PASSWORD'):
                    data['DB_PASSWORD'] = parsed.password
                if parsed.port and not data.get('DB_PORT'):
                    data['DB_PORT'] = parsed.port
        return data

    def get_db_connection_string(self) -> str:
        """Get PostgreSQL connection string."""
        if self.DATABASE_URL:
            return self.DATABASE_URL
        return f"postgresql://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"

    def validate_db_credentials(self, require_db: bool = False) -> None:
        """
        Validate database credentials.

        Args:
            require_db: If True, raise error if credentials missing

        Raises:
            ValueError: If require_db=True and credentials are missing
        """
        if require_db and not (self.DB_USER and self.DB_PASSWORD):
            raise ValueError(
                "Database credentials are required but not found.\n\n"
                "Please add to your .env file either:\n"
                "  DATABASE_URL=postgresql://user:pass@host:port/dbname\n\n"
                "Or individual variables:\n"
                "  DB_USER=your_user\n"
                "  DB_PASSWORD=your_password\n"
                "  DB_HOST=localhost\n"
                "  DB_NAME=pla_leadership\n"
                "  DB_PORT=5432"
            )



# Global configuration instance
CONFIG = Config()
