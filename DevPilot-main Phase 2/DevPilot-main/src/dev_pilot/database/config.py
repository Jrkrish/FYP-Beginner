"""
Database Configuration Module

Provides database connection, session management, and configuration.
"""

import os
from typing import AsyncGenerator, Optional
from contextlib import asynccontextmanager

from sqlalchemy import create_engine, MetaData
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import sessionmaker, Session, DeclarativeBase
from sqlalchemy.pool import NullPool, QueuePool
from loguru import logger


# Naming convention for constraints
convention = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    """Base class for all database models."""
    
    metadata = MetaData(naming_convention=convention)


class DatabaseConfig:
    """Database configuration settings."""
    
    def __init__(
        self,
        host: str = "localhost",
        port: int = 5432,
        database: str = "devpilot",
        username: str = "devpilot",
        password: str = "",
        driver: str = "postgresql+asyncpg",
        sync_driver: str = "postgresql+psycopg2",
        pool_size: int = 5,
        max_overflow: int = 10,
        echo: bool = False,
    ):
        self.host = host
        self.port = port
        self.database = database
        self.username = username
        self.password = password
        self.driver = driver
        self.sync_driver = sync_driver
        self.pool_size = pool_size
        self.max_overflow = max_overflow
        self.echo = echo
    
    @classmethod
    def from_env(cls) -> "DatabaseConfig":
        """Create config from environment variables."""
        return cls(
            host=os.getenv("DB_HOST", "localhost"),
            port=int(os.getenv("DB_PORT", "5432")),
            database=os.getenv("DB_NAME", "devpilot"),
            username=os.getenv("DB_USER", "devpilot"),
            password=os.getenv("DB_PASSWORD", ""),
            echo=os.getenv("DB_ECHO", "false").lower() == "true",
        )
    
    @property
    def async_url(self) -> str:
        """Get async database URL."""
        return f"{self.driver}://{self.username}:{self.password}@{self.host}:{self.port}/{self.database}"
    
    @property
    def sync_url(self) -> str:
        """Get sync database URL."""
        return f"{self.sync_driver}://{self.username}:{self.password}@{self.host}:{self.port}/{self.database}"
    
    @property
    def sqlite_url(self) -> str:
        """Get SQLite URL for testing/development."""
        return "sqlite+aiosqlite:///./devpilot.db"
    
    @property
    def sqlite_sync_url(self) -> str:
        """Get sync SQLite URL."""
        return "sqlite:///./devpilot.db"


class DatabaseManager:
    """
    Manages database connections and sessions.
    
    Supports both async and sync operations.
    """
    
    def __init__(self, config: Optional[DatabaseConfig] = None, use_sqlite: bool = True):
        """
        Initialize database manager.
        
        Args:
            config: Database configuration
            use_sqlite: Use SQLite instead of PostgreSQL (for dev/testing)
        """
        self.config = config or DatabaseConfig.from_env()
        self.use_sqlite = use_sqlite
        
        self._async_engine = None
        self._sync_engine = None
        self._async_session_factory = None
        self._sync_session_factory = None
    
    def _get_url(self, async_mode: bool = True) -> str:
        """Get appropriate database URL."""
        if self.use_sqlite:
            return self.config.sqlite_url if async_mode else self.config.sqlite_sync_url
        return self.config.async_url if async_mode else self.config.sync_url
    
    @property
    def async_engine(self):
        """Get or create async engine."""
        if self._async_engine is None:
            url = self._get_url(async_mode=True)
            
            # SQLite doesn't support connection pooling the same way
            if self.use_sqlite:
                self._async_engine = create_async_engine(
                    url,
                    echo=self.config.echo,
                    poolclass=NullPool,
                )
            else:
                self._async_engine = create_async_engine(
                    url,
                    echo=self.config.echo,
                    pool_size=self.config.pool_size,
                    max_overflow=self.config.max_overflow,
                )
        
        return self._async_engine
    
    @property
    def sync_engine(self):
        """Get or create sync engine."""
        if self._sync_engine is None:
            url = self._get_url(async_mode=False)
            
            if self.use_sqlite:
                self._sync_engine = create_engine(
                    url,
                    echo=self.config.echo,
                )
            else:
                self._sync_engine = create_engine(
                    url,
                    echo=self.config.echo,
                    pool_size=self.config.pool_size,
                    max_overflow=self.config.max_overflow,
                )
        
        return self._sync_engine
    
    @property
    def async_session_factory(self) -> async_sessionmaker[AsyncSession]:
        """Get async session factory."""
        if self._async_session_factory is None:
            self._async_session_factory = async_sessionmaker(
                bind=self.async_engine,
                class_=AsyncSession,
                expire_on_commit=False,
                autoflush=False,
            )
        return self._async_session_factory
    
    @property
    def sync_session_factory(self) -> sessionmaker[Session]:
        """Get sync session factory."""
        if self._sync_session_factory is None:
            self._sync_session_factory = sessionmaker(
                bind=self.sync_engine,
                expire_on_commit=False,
                autoflush=False,
            )
        return self._sync_session_factory
    
    async def create_tables(self) -> None:
        """Create all tables in the database."""
        async with self.async_engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Database tables created")
    
    async def drop_tables(self) -> None:
        """Drop all tables in the database."""
        async with self.async_engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
        logger.info("Database tables dropped")
    
    @asynccontextmanager
    async def session(self) -> AsyncGenerator[AsyncSession, None]:
        """
        Get an async database session.
        
        Usage:
            async with db.session() as session:
                # do stuff
        """
        session = self.async_session_factory()
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
    
    def sync_session(self) -> Session:
        """Get a sync database session."""
        return self.sync_session_factory()
    
    async def close(self) -> None:
        """Close database connections."""
        if self._async_engine:
            await self._async_engine.dispose()
            self._async_engine = None
        
        if self._sync_engine:
            self._sync_engine.dispose()
            self._sync_engine = None
        
        logger.info("Database connections closed")


# Global database manager instance
_db_manager: Optional[DatabaseManager] = None


def get_db_manager(
    config: Optional[DatabaseConfig] = None,
    use_sqlite: bool = True,
) -> DatabaseManager:
    """
    Get or create the global database manager.
    
    Args:
        config: Database configuration
        use_sqlite: Use SQLite for development
        
    Returns:
        DatabaseManager instance
    """
    global _db_manager
    
    if _db_manager is None:
        _db_manager = DatabaseManager(config, use_sqlite)
    
    return _db_manager


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency for getting database session in FastAPI.
    
    Usage in FastAPI:
        @app.get("/items")
        async def get_items(session: AsyncSession = Depends(get_session)):
            ...
    """
    db = get_db_manager()
    async with db.session() as session:
        yield session
