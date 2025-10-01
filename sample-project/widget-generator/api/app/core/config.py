import os
from dotenv import load_dotenv
load_dotenv()

from pydantic_settings import BaseSettings

import json

class Settings(BaseSettings):
    CELERY_BROKER_URL: str = "redis://localhost:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/0"
    OPENAI_API_KEY: str
    DATASOURCES_API_ENDPOINTS: list[str] = []
    DATASOURCE_AUTH_HEADERS: dict = {}
    WIDGET_GENERATION_COUNT: int = 3

    def __init__(self, **values):
        super().__init__(**values)
        endpoints = os.getenv("DATASOURCES_API_ENDPOINTS", "[]")
        try:
            self.DATASOURCES_API_ENDPOINTS = json.loads(endpoints)
        except Exception:
            self.DATASOURCES_API_ENDPOINTS = []
        headers = os.getenv("DATASOURCE_AUTH_HEADERS", "{}")
        try:
            self.DATASOURCE_AUTH_HEADERS = json.loads(headers)
        except Exception:
            self.DATASOURCE_AUTH_HEADERS = {}
        try:
            self.WIDGET_GENERATION_COUNT = int(os.getenv("WIDGET_GENERATION_COUNT", "3"))
        except Exception:
            self.WIDGET_GENERATION_COUNT = 3

settings = Settings()
