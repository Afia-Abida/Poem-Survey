import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.pool import NullPool

Base = declarative_base()

# 1. Create the engine ONCE at the module level
# This helps Vercel reuse the engine object across warm starts
DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    # This will show up in Vercel logs if the Env Var is missing
    raise RuntimeError("DATABASE_URL is not set in Environment Variables")

# Make sure your URL starts with mysql+pymysql://
engine = create_engine(
    DATABASE_URL,
    poolclass=NullPool,
    # This timeout helps prevent the "busy" error by giving up 
    # and retrying rather than locking the socket
    connect_args={"connect_timeout": 10}
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

def get_db():
    db = SessionLocal()
    try:
        yield db
    except Exception as e:
        print(f"Database error: {e}")
        raise
    finally:
        db.close()