from typing import Any

from fastapi import Depends, HTTPException, status
from sqlalchemy import select, and_, delete, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.schema import Table

from ..database import init_db
from ..logger import logger


async def add_to_db(model, db: AsyncSession):
    try:
        db.add(model)
        await db.commit()
        await db.refresh(model)
    except Exception as e:
        await db.rollback()
        logger.error(f'Error occurred while adding {model} to db')
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail=f"Internal server error during adding model: {str(e)}")


async def refresh_data_in_db(model, db: AsyncSession):
    try:
        await db.commit()
        await db.refresh(model)
    except Exception as e:
        await db.rollback()
        logger.error(f'Error occurred while refreshing {model} in db')
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail=f"Internal server error during model refreshing: {str(e)}")


async def delete_from_db(model, db: AsyncSession):
    try:
        await db.delete(model)
        await db.commit()
    except Exception as e:
        await db.rollback()
        logger.error(f'Error occurred while deleting {model} from db')
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail=f"Internal server error during model deletion: {str(e)}")


async def get_by_filter(model, db: AsyncSession, **filters: Any) -> Any | None:
    try:
        query = select(model).filter_by(**filters)
        result = await db.execute(query)

        return result.scalars().first()
    except Exception as e:
        logger.error(f'Error occurred while fetching {model.__name__} by filter {filters}: {str(e)}')
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail=f"Internal server error during model fetching: {str(e)}")


async def get_with_pagination(model, db: AsyncSession, limit: int = 10, offset: int = 0):
    try:
        query = select(model).limit(limit).offset(offset)
        result = await db.execute(query)
        items = result.scalars().all()

        return items
    except Exception as e:
        logger.error(f'Error occurred while pagination for {model.__name__}: {str(e)}')
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail=f"Internal server error during model fetching: {str(e)}")


async def get_table_record_by_filter(table: Table, db: AsyncSession, **filters: Any) -> Any | None:
    try:
        conditions = [table.c[key] == value for key, value in filters.items()]

        query = select(table).where(and_(*conditions))
        result = await db.execute(query)

        return result.mappings().first()

    except Exception as e:
        logger.error(f"Error fetching from table {table.name} with filters {filters}: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail=f"Internal server error during data fetching: {str(e)}")


async def update_table_record_by_filter(table: Table, values: dict[str, Any], db: AsyncSession,
                                        **filters: Any) -> bool:
    try:
        conditions = [table.c[key] == value for key, value in filters.items()]

        query = update(table).where(and_(*conditions)).values(**values)

        await db.execute(query)
        await db.commit()

        return True
    except Exception as e:
        await db.rollback()
        logger.error(f"Error updating table {table.name} with values {values}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error during data update: {str(e)}")


async def delete_table_record_by_filter(table: Table, db: AsyncSession, **filters: Any) -> bool:
    try:
        conditions = [table.c[key] == value for key, value in filters.items()]

        query = delete(table).where(and_(*conditions))

        await db.execute(query)
        await db.commit()

        return True
    except Exception as e:
        await db.rollback()
        logger.error(f"Error deleting from table {table.name}: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail=f"Internal server error during data deletion: {str(e)}")


async def insert_table_record(table: Table, data: dict[str, Any], db: AsyncSession) -> bool:
    try:
        query = table.insert().values(**data)

        await db.execute(query)
        await db.commit()

        return True
    except Exception as e:
        await db.rollback()
        logger.error(f"Error inserting into table {table.name} with data {data}: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail=f"Internal server error during data insertion: {str(e)}")