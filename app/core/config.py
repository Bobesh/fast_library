import os
from typing import Optional


class Settings:
    def __init__(self):
        self.app_name = "Knihovna API"
        self.version = "1.0.0"
        self.debug = os.getenv("DEBUG", "true").lower() == "true"

    def db_host(self) -> str:
        return os.getenv("DB_HOST", "localhost")

    def db_port(self) -> int:
        return int(os.getenv("DB_PORT", "5432"))

    def db_name(self) -> str:
        return os.getenv("DB_NAME", "knihovna")

    def db_user(self) -> str:
        return os.getenv("DB_USER", "knihovna")

    def db_password(self) -> str:
        return os.getenv("DB_PASSWORD", "heslo123")

    def app_host(self) -> str:
        return os.getenv("APP_HOST", "0.0.0.0")

    def app_port(self) -> int:
        return int(os.getenv("APP_PORT", "8000"))


settings = Settings()