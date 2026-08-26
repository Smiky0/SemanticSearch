"""Database session management."""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session


DATABASE_URL = "postgresql://localhost/myapp"


def get_database_url() -> str:
    """Get the configured database URL."""
    return DATABASE_URL


def create_database_engine(url: str = None):
    """Create a new database engine."""
    if url is None:
        url = get_database_url()
    return create_engine(url)


def get_session(engine) -> Session:
    """Get a new database session."""
    SessionLocal = sessionmaker(bind=engine)
    return SessionLocal()


def init_database():
    """Initialize the database connection."""
    engine = create_database_engine()
    session = get_session(engine)
    return engine, session
