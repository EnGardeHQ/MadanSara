"""
Shared database integration with En Garde PostgreSQL.

This module provides connection pooling and session management for the
shared En Garde PostgreSQL database used by all microservices.
"""

import os
from typing import Generator, Optional
from sqlalchemy import create_engine, event, pool
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import QueuePool
import logging

logger = logging.getLogger(__name__)

# Shared database URL - all microservices connect to En Garde's PostgreSQL
ENGARDE_DATABASE_URL = os.getenv(
    "ENGARDE_DATABASE_URL",
    os.getenv("DATABASE_PUBLIC_URL", "postgresql://postgres:password@localhost:5432/engarde")
)

# Connection pool settings optimized for Railway
POOL_SIZE = int(os.getenv("DB_POOL_SIZE", "5"))
MAX_OVERFLOW = int(os.getenv("DB_MAX_OVERFLOW", "10"))
POOL_TIMEOUT = int(os.getenv("DB_POOL_TIMEOUT", "30"))
POOL_RECYCLE = int(os.getenv("DB_POOL_RECYCLE", "3600"))  # 1 hour

# Create engine with connection pooling
engine = create_engine(
    ENGARDE_DATABASE_URL,
    poolclass=QueuePool,
    pool_size=POOL_SIZE,
    max_overflow=MAX_OVERFLOW,
    pool_timeout=POOL_TIMEOUT,
    pool_pre_ping=True,  # Verify connections before using
    pool_recycle=POOL_RECYCLE,
    echo=os.getenv("SQL_ECHO", "false").lower() == "true",
    connect_args={
        "connect_timeout": 10,
        "options": "-c timezone=utc",
    }
)

# Create session factory
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
    expire_on_commit=False,
)

# Base class for models
Base = declarative_base()


# Event listeners for connection management
@event.listens_for(engine, "connect")
def receive_connect(dbapi_conn, connection_record):
    """Set connection parameters on new connections."""
    logger.debug("New database connection established")


@event.listens_for(engine, "checkout")
def receive_checkout(dbapi_conn, connection_record, connection_proxy):
    """Verify connection health on checkout."""
    logger.debug("Connection checked out from pool")


@event.listens_for(engine, "checkin")
def receive_checkin(dbapi_conn, connection_record):
    """Log connection checkin."""
    logger.debug("Connection checked back into pool")


def get_db() -> Generator[Session, None, None]:
    """
    Dependency function for FastAPI to get database sessions.

    Yields:
        Session: SQLAlchemy database session

    Example:
        @app.get("/items")
        def get_items(db: Session = Depends(get_db)):
            return db.query(Item).all()
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_db_session() -> Session:
    """
    Get a database session for non-FastAPI contexts.

    Returns:
        Session: SQLAlchemy database session

    Note:
        Caller is responsible for closing the session.

    Example:
        db = get_db_session()
        try:
            items = db.query(Item).all()
        finally:
            db.close()
    """
    return SessionLocal()


def init_db() -> None:
    """
    Initialize database tables.

    Creates all tables defined in models if they don't exist.
    Should be called on application startup.
    """
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize database tables: {e}")
        raise


def check_db_connection() -> bool:
    """
    Check if database connection is healthy.

    Returns:
        bool: True if connection is healthy, False otherwise

    Example:
        if not check_db_connection():
            logger.error("Database is unreachable")
    """
    try:
        with engine.connect() as conn:
            conn.execute("SELECT 1")
        logger.info("Database connection healthy")
        return True
    except Exception as e:
        logger.error(f"Database connection failed: {e}")
        return False


def get_db_stats() -> dict:
    """
    Get database connection pool statistics.

    Returns:
        dict: Connection pool statistics

    Example:
        stats = get_db_stats()
        print(f"Active connections: {stats['checked_out']}")
    """
    pool = engine.pool
    return {
        "pool_size": pool.size(),
        "checked_out": pool.checkedout(),
        "overflow": pool.overflow(),
        "checked_in": pool.checkedin(),
        "total_connections": pool.size() + pool.overflow(),
    }


class DatabaseManager:
    """
    Context manager for database sessions.

    Provides automatic session management with commit/rollback.

    Example:
        with DatabaseManager() as db:
            item = Item(name="test")
            db.add(item)
            # Automatically commits on success, rolls back on error
    """

    def __init__(self):
        self.db: Optional[Session] = None

    def __enter__(self) -> Session:
        """Enter context manager."""
        self.db = SessionLocal()
        return self.db

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit context manager with automatic commit/rollback."""
        if exc_type is not None:
            # Exception occurred, rollback
            if self.db:
                self.db.rollback()
                logger.error(f"Transaction rolled back due to: {exc_val}")
        else:
            # Success, commit
            if self.db:
                self.db.commit()
                logger.debug("Transaction committed successfully")

        # Always close the session
        if self.db:
            self.db.close()


# Convenience alias
db_session = DatabaseManager


def execute_raw_sql(sql: str, params: Optional[dict] = None) -> list:
    """
    Execute raw SQL query.

    Args:
        sql: SQL query string
        params: Optional query parameters

    Returns:
        list: Query results

    Warning:
        Use with caution. Prefer ORM queries for safety.

    Example:
        results = execute_raw_sql(
            "SELECT * FROM items WHERE category = :cat",
            {"cat": "electronics"}
        )
    """
    with engine.connect() as conn:
        result = conn.execute(sql, params or {})
        return result.fetchall()


# Export commonly used items
__all__ = [
    "engine",
    "SessionLocal",
    "Base",
    "get_db",
    "get_db_session",
    "init_db",
    "check_db_connection",
    "get_db_stats",
    "DatabaseManager",
    "db_session",
    "execute_raw_sql",
]
