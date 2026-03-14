import psycopg
from langgraph.checkpoint.postgres import PostgresSaver
from config.settings import settings


def get_checkpointer() -> PostgresSaver:
    """Return a PostgresSaver connected to the configured DATABASE_URL."""
    conn = psycopg.connect(settings.database_url)
    saver = PostgresSaver(conn)
    saver.setup()   # creates checkpoint tables if they don't exist
    return saver
