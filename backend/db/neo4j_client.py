"""Neo4j driver singleton.

The driver is thread-safe and pooled internally — we hold one instance
for the lifetime of the process and hand out sessions on request.
"""

from __future__ import annotations

from contextlib import contextmanager
from functools import lru_cache
from typing import Iterator

from neo4j import Driver, GraphDatabase, Session
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    neo4j_uri: str = "bolt://localhost:7687"
    neo4j_user: str = "neo4j"
    neo4j_password: str = "password"
    neo4j_database: str = "neo4j"
    user_id: str = "u_alex"
    allowed_origin: str = "http://localhost:5173"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


@lru_cache(maxsize=1)
def settings() -> Settings:
    return Settings()


@lru_cache(maxsize=1)
def driver() -> Driver:
    s = settings()
    return GraphDatabase.driver(s.neo4j_uri, auth=(s.neo4j_user, s.neo4j_password))


@contextmanager
def session() -> Iterator[Session]:
    s = settings()
    with driver().session(database=s.neo4j_database) as sess:
        yield sess


def close() -> None:
    """Call on app shutdown so the connection pool drains cleanly."""
    if driver.cache_info().currsize > 0:
        driver().close()
        driver.cache_clear()
