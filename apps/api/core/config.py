from typing import Optional
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Core settings loaded from environment variables or .env file."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    API_HOST: str = Field(default="0.0.0.0", description="API host bind address")
    API_PORT: int = Field(default=8000, description="API port")
    API_ENV: str = Field(default="development", description="Application environment")
    DATABASE_URL: str = Field(
        default="postgresql+asyncpg://postgres:postgres@localhost:5432/recoverai",
        description="PostgreSQL async database connection URL",
    )

    # Razorpay Test Mode Configuration
    RAZORPAY_KEY_ID: Optional[str] = Field(
        default=None,
        description="Razorpay Test Key ID (must begin with rzp_test_)",
    )
    RAZORPAY_KEY_SECRET: Optional[str] = Field(
        default=None,
        description="Razorpay Test Key Secret",
    )
    RAZORPAY_WEBHOOK_SECRET: Optional[str] = Field(
        default=None,
        description="Razorpay Webhook Secret for HMAC-SHA256 signature verification",
    )
    RAZORPAY_ENV: str = Field(
        default="test",
        description="Razorpay environment mode (strictly 'test' only)",
    )

    @field_validator("RAZORPAY_KEY_ID")
    @classmethod
    def validate_razorpay_key_id(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v.strip():
            key = v.strip()
            if key.lower().startswith("rzp_live"):
                raise ValueError(
                    "SecurityError: Live Razorpay credentials (rzp_live_...) are strictly prohibited. "
                    "Only test credentials (rzp_test_...) are permitted."
                )
            if not key.lower().startswith("rzp_test"):
                raise ValueError(
                    f"SecurityError: Invalid Razorpay Key ID prefix. Must strictly begin with 'rzp_test_'."
                )
            return key
        return None

    @field_validator("RAZORPAY_ENV")
    @classmethod
    def validate_razorpay_env(cls, v: str) -> str:
        env_val = v.strip().lower() if v else "test"
        if env_val != "test":
            raise ValueError(
                f"SecurityError: Execution environment '{v}' is prohibited. Only 'test' mode is permitted in RecoverAI."
            )
        return "test"


settings = Settings()

