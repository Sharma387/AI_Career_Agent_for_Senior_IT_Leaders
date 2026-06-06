"""
Database base module providing async session context manager.
"""

from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import async_session_factory


async def get_async_session_context() -> AsyncGenerator[AsyncSession, None]:
    """
    Async context manager for database sessions.
    Provides the same dependency pattern as get_db() but for direct usage.
    """
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise