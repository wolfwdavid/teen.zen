import psycopg2
from psycopg2.extras import RealDictCursor

PG_URL = "postgresql://postgres.fhlzwwemtcedasigzcyz:6fB3%2Fbvv%23K7t9VX@aws-0-us-west-2.pooler.supabase.com:5432/postgres"

def get_db_connection():
    """Get a PostgreSQL connection with dict cursor."""
    conn = psycopg2.connect(PG_URL)
    conn.autocommit = True
    return conn

def dict_cursor(conn):
    """Get a cursor that returns dicts."""
    return conn.cursor(cursor_factory=RealDictCursor)
