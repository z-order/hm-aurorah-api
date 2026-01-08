"""
Database configuration and session management
"""

from collections.abc import AsyncGenerator

from sqlalchemy import Table
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlmodel import SQLModel

from app.core.config import settings

# Convert postgresql:// to postgresql+asyncpg://
POSTGRES_URL = settings.postgres_url.replace("postgresql://", "postgresql+asyncpg://")

# Create async engine
engine = create_async_engine(
    POSTGRES_URL,
    echo=True if settings.ENVIRONMENT == "development" else False,  # Log SQL queries
    future=True,  # Use async/await syntax
    pool_pre_ping=True,  # Ping before using a connection
    pool_size=10,  # Keep 10 connections open
    max_overflow=20,  # Allow 20 extra connections
    pool_timeout=30,  # Wait 30s for connection
    pool_recycle=1800,  # Recycle connections every 30 minutes
    connect_args={
        "timeout": 10,  # Connection timeout
        "command_timeout": 60,  # Command timeout
        "server_settings": {"search_path": "auth, lang, public"},  # Schema search path
    },
)

# Create async session maker
AsyncSessionMaker = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


async def get_db() -> AsyncGenerator[AsyncSession]:
    """
    Dependency for getting async database sessions
    """
    async with AsyncSessionMaker() as session:
        try:
            yield session
            # Don't auto-commit - let routes decide
            # await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db() -> None:
    """
    Initialize database - create all tables
    Note: In multi-worker deployments, this should be run once before starting workers
    to avoid race conditions. The checkfirst=True prevents errors if tables exist.
    """
    async with engine.begin() as conn:
        # Import all models here to ensure they are registered with SQLModel
        from app.models.chatbot_message import ChatbotMessage
        from app.models.chatbot_task import ChatbotTask

        _ = (
            ChatbotTask,
            ChatbotMessage,
        )  # Reference to prevent auto-removal by mypy or pyright

        # Create only specific tables (others managed by SQL scripts)
        tables_to_create: list[Table] = [
            ChatbotTask.__table__,  # type: ignore[misc]
            ChatbotMessage.__table__,  # type: ignore[misc]
        ]

        if tables_to_create:
            await conn.run_sync(
                lambda sync_conn: SQLModel.metadata.create_all(
                    sync_conn,
                    tables=tables_to_create,
                    checkfirst=True,
                )
            )


async def check_db_health() -> bool:
    """Health check for database connection"""
    try:
        from sqlalchemy import text

        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False
