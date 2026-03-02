from langgraph.checkpoint.postgres import PostgresSaver
from config.settings import settings


def get_checkpointer() -> PostgresSaver:
    """Return a PostgresSaver checkpointer using the configured DATABASE_URL."""
    # TODO: Create and return a PostgresSaver connected to settings.database_url
    # Example:
    #   conn = psycopg2.connect(settings.database_url)
    #   return PostgresSaver(conn)
    pass
