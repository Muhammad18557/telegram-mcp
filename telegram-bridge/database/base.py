"""
Database configuration and session management.

Provides a SQLAlchemy engine and session factory with connection pooling.
"""

import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session
from sqlalchemy.pool import QueuePool

from database.models import Base

# Get database path
STORE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "store")
os.makedirs(STORE_DIR, exist_ok=True)
DB_PATH = os.path.join(STORE_DIR, "messages.db")

# Create engine with connection pooling
engine = create_engine(
    f"sqlite:///{DB_PATH}",
    connect_args={"check_same_thread": False},  # Needed for SQLite
    poolclass=QueuePool,
    pool_size=5,
    max_overflow=10,
    pool_timeout=30,
    pool_recycle=3600,
)

# Create session factory
SessionFactory = sessionmaker(bind=engine)
Session = scoped_session(SessionFactory)


def init_db():
    """Initialize the database schema."""
    Base.metadata.create_all(engine)


def get_session():
    """Get a database session from the pool."""
    return Session()