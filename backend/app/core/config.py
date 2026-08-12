from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+asyncpg://botalka:botalka@localhost:5433/botalka"
    redis_url: str = "redis://localhost:6380/0"

    telegram_bot_token: str = ""
    telegram_bot_username: str = ""

    jwt_secret: str = "change-me"
    jwt_algorithm: str = "HS256"
    session_days: int = 30

    cors_origins: str = "http://localhost:3000"
    # включать на любом публичном адресе (туннель, прод) — там всегда https
    cookie_secure: bool = False

    # ОПАСНО: включает вход без Telegram по одной кнопке. Только для локальной
    # разработки, когда домен для виджета ещё не настроен. В проде — строго False.
    dev_login: bool = False

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


settings = Settings()
