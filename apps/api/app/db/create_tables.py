import asyncio

from app.db.base import Base
from app.db.session import engine
from app.db import models  # noqa: F401  # ensure models are imported


async def create_all_tables() -> None:
    """
    Create all database tables defined on the SQLAlchemy Base metadata.

    This is intended as a simple dev-only helper. In a more mature setup,
    Alembic migrations should be used instead.
    """
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


def main() -> None:
    asyncio.run(create_all_tables())
    print("Database tables created successfully.")


if __name__ == "__main__":
    main()
