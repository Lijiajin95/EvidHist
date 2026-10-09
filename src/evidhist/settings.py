from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="EVIDHIST_", extra="ignore")

    # Local test credentials; deployments must provide their own database URL.
    database_url: SecretStr = SecretStr(
        "postgresql+psycopg://evidhist:evidhist@127.0.0.1:55432/evidhist_test"
    )
