"""
backend.repositories.base_repository — Abstract base repository for async database CRUD operations.
"""
from __future__ import annotations

from typing import Generic, TypeVar, Type, Optional, List, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete

T = TypeVar("T")


class BaseRepository(Generic[T]):
    """Generic async repository interface enforcing standard CRUD contracts."""

    def __init__(self, model_class: Type[T], session: AsyncSession) -> None:
        self.model_class = model_class
        self.session = session

    async def get_by_id(self, entity_id: Any) -> Optional[T]:
        """Fetch a single record by primary key."""
        result = await self.session.execute(
            select(self.model_class).where(self.model_class.id == entity_id)
        )
        return result.scalars().first()

    async def list_all(self, limit: int = 100) -> List[T]:
        """List records with limit."""
        result = await self.session.execute(
            select(self.model_class).limit(limit)
        )
        return list(result.scalars().all())

    async def add(self, entity: T) -> T:
        """Persist a new entity instance."""
        self.session.add(entity)
        await self.session.flush()
        return entity

    async def delete_by_id(self, entity_id: Any) -> bool:
        """Delete a record by primary key."""
        result = await self.session.execute(
            delete(self.model_class).where(self.model_class.id == entity_id)
        )
        return result.rowcount > 0
