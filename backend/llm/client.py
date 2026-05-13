"""OpenAI client singletons.

One sync, one async — we use both. Async is for /api/rank where embedding
and tag extraction fire in parallel; sync is for the offline scripts that
batch-embed venues.
"""

from __future__ import annotations

from functools import lru_cache

from openai import AsyncOpenAI, OpenAI
from pydantic_settings import BaseSettings, SettingsConfigDict


class OpenAISettings(BaseSettings):
    openai_api_key: str = ""
    openai_embed_model: str = "text-embedding-3-small"
    openai_chat_model: str = "gpt-4o-mini"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


@lru_cache(maxsize=1)
def openai_settings() -> OpenAISettings:
    return OpenAISettings()


@lru_cache(maxsize=1)
def async_client() -> AsyncOpenAI:
    return AsyncOpenAI(api_key=openai_settings().openai_api_key)


@lru_cache(maxsize=1)
def sync_client() -> OpenAI:
    return OpenAI(api_key=openai_settings().openai_api_key)


def has_key() -> bool:
    return bool(openai_settings().openai_api_key)
