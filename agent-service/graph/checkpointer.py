import psycopg
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from config.settings import settings


async def get_checkpointer() -> AsyncPostgresSaver:
    """Return an AsyncPostgresSaver connected to the configured DATABASE_URL."""
    conn = await psycopg.AsyncConnection.connect(
        settings.database_url, autocommit=True, prepare_threshold=0
    )
    saver = AsyncPostgresSaver(conn)
    await saver.setup()
    return saver
