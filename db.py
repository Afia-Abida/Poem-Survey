import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.pool import NullPool  # <--- Import this

# Base class for models
Base = declarative_base()

def get_engine():
    DATABASE_URL = os.getenv("DATABASE_URL")

    if not DATABASE_URL:
        raise RuntimeError("DATABASE_URL is not set")

    # For Vercel/Serverless, we MUST use NullPool to avoid "Device Busy" errors
    return create_engine(
        DATABASE_URL,
        poolclass=NullPool, # <--- This is the fix
        pool_pre_ping=True
    )

def get_db():
    engine = get_engine()
    SessionLocal = sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=engine
    )

    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
        # Explicitly dispose the engine to clean up the connection immediately
        engine.dispose()